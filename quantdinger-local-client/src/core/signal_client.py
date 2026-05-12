"""
WebSocket Signal Client

Handles WebSocket connection to QuantDinger Cloud and receives trading signals.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)


class SignalClient:
    """
    WebSocket client for receiving trading signals from QuantDinger Cloud.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Authentication with API key
    - Signal validation and filtering
    - Callback-based signal handling
    """
    
    def __init__(
        self,
        api_key: str,
        cloud_url: str = "ws://localhost:8765/ws",
        on_signal: Optional[Callable] = None,
        on_connect: Optional[Callable] = None,
        on_disconnect: Optional[Callable] = None,
        on_error: Optional[Callable] = None,  # 新增：错误回调
        broker_account_id: Optional[str] = None,  # 新增：券商实际账号ID
    ):
        """
        Initialize the signal client.
        
        Args:
            api_key: QuantDinger Cloud API key
            cloud_url: WebSocket server URL
            on_signal: Callback function when signal received
            on_connect: Callback function when connected
            on_disconnect: Callback function when disconnected
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library not installed. "
                "Install with: pip install websockets"
            )
        
        self.api_key = api_key
        self.cloud_url = cloud_url
        self.on_signal = on_signal
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_error = on_error  # 错误回调
        self.broker_account_id = broker_account_id  # 券商实际账号ID
        
        # State
        self.connected = False
        self.websocket: Optional[Any] = None
        self.stop_event = asyncio.Event()
        
        # Statistics
        self.signal_count = 0
        self.message_count = 0
        
        # Reconnection settings
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300
        
        logger.info(f"SignalClient initialized: url={cloud_url}")
    
    async def connect(self):
        """Connect to WebSocket server with automatic reconnection."""
        while not self.stop_event.is_set():
            try:
                logger.info(f"Connecting to {self.cloud_url}...")
                
                async with websockets.connect(self.cloud_url) as websocket:
                    self.websocket = websocket
                    logger.info("✓ TCP Connection established!")
                    
                    # Authenticate
                    logger.info(" Starting authentication...")
                    await self._authenticate(websocket)
                    
                    # Listen for messages
                    await self._message_loop(websocket)
            
            except (ConnectionClosed, ConnectionClosedError) as e:
                error_msg = f"❌ Connection closed unexpectedly"
                logger.warning(error_msg)
                logger.warning(f"   Code: {e.code}")
                logger.warning(f"   Reason: {e.reason}")
                logger.warning(f"   Exception type: {type(e).__name__}")
                
                full_error = f"WebSocket连接关闭: code={e.code}, reason={e.reason}"
                if self.on_error:
                    try:
                        self.on_error(full_error)
                    except:
                        pass
                self._handle_disconnect()
            
            except Exception as e:
                logger.error(f"Connection error: {e}")
                error_msg = f"WebSocket连接错误: {str(e)}"
                if self.on_error:
                    try:
                        self.on_error(error_msg)
                    except:
                        pass
                self._handle_disconnect()
            
            # Reconnect with exponential backoff
            if not self.stop_event.is_set():
                delay = min(self.reconnect_delay, self.max_reconnect_delay)
                logger.info(f"Reconnecting in {delay}s...")
                await asyncio.sleep(delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    async def _authenticate(self, websocket):
        """Send authentication message."""
        auth_message = {
            'api_key': self.api_key,
            'client_type': 'signal_client',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'broker_account_id': self.broker_account_id,  # 上报实际券商账号
        }
        
        # Log authentication details (mask API key for security)
        api_key_display = self.api_key[:8] + "..." + self.api_key[-4:] if len(self.api_key) > 12 else "***"
        logger.info(f"📤 Sending auth - API Key: {api_key_display}, Broker: {self.broker_account_id}")
        logger.info(f"   Full auth message: {json.dumps(auth_message)}")
        
        await websocket.send(json.dumps(auth_message))
        logger.info("✓ Auth message sent, waiting for response...")
        
        # Wait for confirmation
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            logger.info(f"📥 Received response: {json.dumps(data)}")
            
            if data.get('type') == 'connection_established':
                logger.info(f"✓ Authentication successful (Client ID: {data.get('client_id')})")
                self.connected = True
                self.reconnect_delay = 5  # Reset delay
                
                if self.on_connect:
                    self.on_connect(data)
            else:
                error_msg = f"❌ Authentication failed: {data}"
                logger.error(error_msg)
                raise Exception(error_msg)
        except asyncio.TimeoutError:
            error_msg = " Authentication timeout - no response from server"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def _message_loop(self, websocket):
        """Main message processing loop."""
        logger.info("Waiting for signals...")
        
        async for message in websocket:
            if self.stop_event.is_set():
                break
            
            self.message_count += 1
            
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'trading_signal':
                    await self._handle_signal(data)
                
                elif msg_type == 'pong':
                    # Heartbeat response
                    pass
                
                else:
                    logger.debug(f"Unknown message type: {msg_type}")
            
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
            except Exception as e:
                logger.error(f"Message processing error: {e}")
    
    async def _handle_signal(self, signal_data: Dict[str, Any]):
        """Handle incoming trading signal."""
        self.signal_count += 1
        
        signal = signal_data.get('data', {})
        signal_id = signal_data.get('signal_id', 'N/A')
        
        logger.info(
            f"📊 Signal #{self.signal_count}: "
            f"{signal.get('strategy_name')} - "
            f"{signal.get('symbol')} - "
            f"{signal.get('signal_type')}"
        )
        
        # Call user callback
        if self.on_signal:
            try:
                if asyncio.iscoroutinefunction(self.on_signal):
                    await self.on_signal(signal_data)
                else:
                    self.on_signal(signal_data)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")
    
    def _handle_disconnect(self):
        """Handle disconnection."""
        self.connected = False
        self.websocket = None
        
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                logger.error(f"Disconnect callback error: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket server."""
        logger.info("Disconnecting...")
        self.stop_event.set()
        
        if self.websocket:
            await self.websocket.close()
        
        self.connected = False
        logger.info("Disconnected")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            'connected': self.connected,
            'signal_count': self.signal_count,
            'message_count': self.message_count,
        }
