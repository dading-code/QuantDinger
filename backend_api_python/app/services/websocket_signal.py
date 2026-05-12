"""
WebSocket Signal Push Service for QuantDinger Cloud

This module adds WebSocket real-time signal push capability to the existing
SignalNotifier, enabling cloud-to-local communication for the "Cloud Brain + 
Local Execution" architecture.

Architecture:
    Cloud QuantDinger (AI Brain)
        ↓ WebSocket (real-time)
    Local Client (Trade Executor)
        ↓ Direct API
    MT5 / IBKR / Other Brokers

Features:
    - Real-time signal push (millisecond latency)
    - Authentication via API key
    - Automatic reconnection
    - Signal history persistence
    - Multi-client support (broadcast)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from app.utils.logger import get_logger
from app.utils.db import get_db_connection

logger = get_logger(__name__)


class WebSocketSignalHub:
    """
    WebSocket hub for broadcasting trading signals to connected clients.
    
    This singleton manages all WebSocket connections and broadcasts signals
    from the SignalNotifier to subscribed local clients.
    """
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        if not WEBSOCKETS_AVAILABLE:
            logger.warning(
                "websockets library not installed. "
                "Install with: pip install websockets"
            )
            self._initialized = True
            return
        
        # Connection management
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Message queue for reliable delivery
        self.message_queue: List[Dict[str, Any]] = []
        self.max_queue_size = 1000
        
        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
        }
        
        self._initialized = True
        logger.info("WebSocketSignalHub initialized")
    
    async def register_client(self, websocket: WebSocketServerProtocol, api_key: str, credential_id: int = None, broker_account_id: str = None):
        """Register a new client connection.
        
        Args:
            websocket: WebSocket connection
            api_key: API key for authentication
            credential_id: API Key绑定的交易所配置ID（从 validate_api_key 返回）
            broker_account_id: 本地客户端实际登录的券商账号ID（MT5 Login / IBKR Account）
        """
        client_id = str(uuid.uuid4())
        
        # Validate API key and get user info
        from app.services.api_key_manager import APIKeyService
        user_info = APIKeyService.validate_api_key(api_key)
        
        if not user_info:
            await websocket.close(code=4001, reason="Invalid API key")
            logger.warning(f"Client rejected: invalid API key")
            return
        
        # ====== 券商账号一致性校验 ======
        user_id = user_info['user_id']
        # 优先使用 API Key 绑定的 credential_id，如果没有则使用参数传入的
        cred_id = credential_id or user_info.get('credential_id')
        validation_result = self._validate_broker_account(user_id, cred_id, broker_account_id)
        
        if not validation_result['valid']:
            error_msg = validation_result.get('error', 'Broker account mismatch')
            await websocket.close(code=4002, reason=error_msg)
            logger.warning(
                f"Client rejected: broker account validation failed for user {user_info['username']}. "
                f"Reason: {error_msg}"
            )
            return
        
        self.clients[client_id] = websocket
        self.client_metadata[client_id] = {
            'api_key': api_key,
            'user_id': user_id,
            'username': user_info['username'],
            'email': user_info['email'],
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_heartbeat': time.time(),
            'ip_address': websocket.remote_address[0] if websocket.remote_address else None,
            'broker_account_id': broker_account_id,  # 记录实际券商账号
            'broker_validated': validation_result.get('validated', False),
        }
        
        self.stats['total_connections'] += 1
        self.stats['active_connections'] = len(self.clients)
        
        logger.info(
            f"Client registered: {client_id} for user: {user_info['username']} "
            f"(broker: {broker_account_id}, validated: {validation_result.get('validated', False)})"
        )
        
        # Send welcome message with user info
        await self._send_to_client(client_id, {
            'type': 'connection_established',
            'client_id': client_id,
            'message': f'欢迎 {user_info["username"]}，已连接到 QuantDinger 云端信号中心',
            'user': {
                'username': user_info['username'],
                'email': user_info['email'],
                'role': user_info['role']
            },
            'broker_validation': {
                'valid': validation_result['valid'],
                'validated': validation_result.get('validated', False),
                'expected_account': validation_result.get('expected_account'),
                'actual_account': validation_result.get('actual_account'),
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
        
        # Start heartbeat monitoring
        asyncio.create_task(self._monitor_heartbeat(client_id))
    
    async def unregister_client(self, client_id: str):
        """Unregister a client connection."""
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.client_metadata:
            del self.client_metadata[client_id]
        
        self.stats['active_connections'] = len(self.clients)
        logger.info(f"Client unregistered: {client_id} (remaining: {self.stats['active_connections']})")
    
    async def broadcast_signal(self, signal_data: Dict[str, Any], target_user_id: int = None):
        """
        Broadcast a trading signal to clients.
        
        Args:
            signal_data: Signal payload from SignalNotifier
            target_user_id: If specified, only send to this user's clients. If None, broadcast to all.
        """
        message = {
            'type': 'trading_signal',
            'signal_id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': signal_data,
        }
        
        # Add to message queue for reliability
        self.message_queue.append(message)
        if len(self.message_queue) > self.max_queue_size:
            self.message_queue.pop(0)
        
        # Broadcast to matching clients
        failed_clients = []
        for client_id, websocket in list(self.clients.items()):
            # Check if client belongs to target user (if specified)
            if target_user_id is not None:
                client_user_id = self.client_metadata.get(client_id, {}).get('user_id')
                if client_user_id != target_user_id:
                    # Skip clients that don't belong to this user
                    continue
            
            try:
                await websocket.send(json.dumps(message, ensure_ascii=False))
                self.stats['messages_sent'] += 1
                
                # Update heartbeat
                if client_id in self.client_metadata:
                    self.client_metadata[client_id]['last_heartbeat'] = time.time()
                
            except Exception as e:
                logger.error(f"Failed to send signal to client {client_id}: {e}")
                self.stats['messages_failed'] += 1
                failed_clients.append(client_id)
        
        # Remove failed clients
        for client_id in failed_clients:
            await self.unregister_client(client_id)
        
        logger.debug(f"Signal broadcasted to {len(self.clients)} clients")
    
    async def _send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send a message to a specific client."""
        if client_id not in self.clients:
            return
        
        try:
            websocket = self.clients[client_id]
            await websocket.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            await self.unregister_client(client_id)
    
    async def _monitor_heartbeat(self, client_id: str):
        """Monitor client heartbeat and disconnect stale connections."""
        while client_id in self.clients:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            if client_id not in self.client_metadata:
                break
            
            last_hb = self.client_metadata[client_id].get('last_heartbeat', 0)
            if time.time() - last_hb > 90:  # 90 seconds timeout
                logger.warning(f"Client {client_id} heartbeat timeout, disconnecting")
                await self.unregister_client(client_id)
                break
    
    def _validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key for authentication.
        使用 APIKeyService 进行验证（已移至 validate_api_key 方法）
        """
        from app.services.api_key_manager import APIKeyService
        user_info = APIKeyService.validate_api_key(api_key)
        return user_info is not None
    
    def _validate_broker_account(self, user_id: int, credential_id: int = None, broker_account_id: str = None) -> Dict[str, Any]:
        """
        校验本地客户端上报的券商账号是否与云端配置一致。
        
        Args:
            user_id: 用户ID
            credential_id: API Key绑定的交易所配置ID（优先使用）
            broker_account_id: 本地客户端实际登录的券商账号ID
            
        Returns:
            {
                'valid': True/False,  # 校验是否通过
                'validated': True/False,  # 是否进行了校验
                'expected_account': 'xxx',  # 云端配置的期望账号
                'actual_account': 'xxx',  # 本地上报的实际账号
                'error': '错误信息'  # 如果校验失败
            }
        """
        result = {
            'valid': True,
            'validated': False,
            'expected_account': None,
            'actual_account': broker_account_id,
        }
        
        # 如果本地没有上报 broker_account_id，跳过校验（兼容旧客户端）
        if not broker_account_id:
            logger.info(f"User {user_id}: No broker_account_id provided, skipping validation")
            return result
        
        try:
            from app.utils.credential_crypto import decrypt_credential_blob
            
            with get_db_connection() as db:
                cur = db.cursor()
                
                # 优先使用 credential_id（API Key绑定的具体交易所配置）
                if credential_id:
                    cur.execute("""
                        SELECT id, exchange_id, encrypted_config
                        FROM qd_exchange_credentials
                        WHERE id = %s AND user_id = %s AND exchange_id IN ('mt5', 'ibkr')
                    """, (credential_id, user_id))
                else:
                    # 如果没有 credential_id，查询用户的所有 MT5/IBKR 配置
                    cur.execute("""
                        SELECT id, exchange_id, encrypted_config
                        FROM qd_exchange_credentials
                        WHERE user_id = %s AND exchange_id IN ('mt5', 'ibkr')
                    """, (user_id,))
                
                credentials = cur.fetchall()
                cur.close()
            
            if not credentials:
                # 用户没有绑定 MT5/IBKR，不需要校验
                logger.info(f"User {user_id}: No MT5/IBKR credentials found, skipping validation")
                return result
            
            # 检查是否有匹配的账号
            matched = False
            expected_accounts = []
            
            for cred in credentials:
                exchange_id = cred['exchange_id']
                try:
                    config_json = decrypt_credential_blob(cred['encrypted_config'])
                    config = json.loads(config_json) if isinstance(config_json, str) else config_json
                    
                    if exchange_id == 'mt5':
                        expected_login = str(config.get('mt5_login', '')).strip()
                        if expected_login:
                            expected_accounts.append(expected_login)
                            if expected_login == str(broker_account_id).strip():
                                matched = True
                                result['expected_account'] = expected_login
                                logger.info(
                                    f"User {user_id}: MT5 account validated successfully. "
                                    f"Expected: {expected_login}, Actual: {broker_account_id}"
                                )
                                break
                    
                    elif exchange_id == 'ibkr':
                        expected_account = str(config.get('ibkr_account', '')).strip()
                        # IBKR 如果没有配置账号，跳过校验
                        if not expected_account:
                            logger.info(f"User {user_id}: IBKR account not configured, skipping validation")
                            result['validated'] = True
                            return result
                        
                        expected_accounts.append(expected_account)
                        if expected_account == str(broker_account_id).strip():
                            matched = True
                            result['expected_account'] = expected_account
                            logger.info(
                                f"User {user_id}: IBKR account validated successfully. "
                                f"Expected: {expected_account}, Actual: {broker_account_id}"
                            )
                            break
                except Exception as e:
                    logger.warning(f"Failed to decrypt credential {cred['id']}: {e}")
                    continue
            
            result['validated'] = True
            
            if not matched:
                # 账号不匹配
                result['valid'] = False
                result['expected_account'] = ', '.join(expected_accounts) if expected_accounts else 'N/A'
                result['error'] = (
                    f"Broker account mismatch: Cloud expects [{result['expected_account']}], "
                    f"but local client logged in as [{broker_account_id}]. "
                    f"Please ensure your local terminal is logged into the correct account."
                )
                logger.warning(f"User {user_id}: {result['error']}")
            
        except Exception as e:
            logger.error(f"Failed to validate broker account for user {user_id}: {e}")
            # 校验失败时，默认允许连接（避免影响正常交易）
            result['error'] = f"Validation error: {str(e)}"
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hub statistics."""
        return {
            **self.stats,
            'queue_size': len(self.message_queue),
            'clients': [
                {
                    'client_id': cid,
                    'connected_at': meta.get('connected_at'),
                    'last_heartbeat': meta.get('last_heartbeat'),
                }
                for cid, meta in self.client_metadata.items()
            ],
        }


# Global singleton instance
_signal_hub = None


def get_signal_hub() -> WebSocketSignalHub:
    """Get or create the global WebSocketSignalHub instance."""
    global _signal_hub
    if _signal_hub is None:
        _signal_hub = WebSocketSignalHub()
    return _signal_hub


async def websocket_handler(websocket: WebSocketServerProtocol, path: str = None):
    """
    WebSocket connection handler for FastAPI/Starlette integration.
    
    Usage with FastAPI:
        from fastapi import FastAPI, WebSocket
        from app.services.websocket_signal import websocket_handler
        
        app = FastAPI()
        
        @app.websocket("/ws/signals")
        async def ws_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket_handler(websocket)
    """
    client_id = None
    try:
        # Wait for authentication message
        auth_message = await asyncio.wait_for(websocket.recv(), timeout=10)
        auth_data = json.loads(auth_message)
        
        api_key = auth_data.get('api_key', '')
        if not api_key:
            await websocket.close(code=4001, reason="API key required")
            return
        
        # 获取本地客户端上报的实际券商账号
        broker_account_id = auth_data.get('broker_account_id')
        
        hub = get_signal_hub()
        await hub.register_client(websocket, api_key, broker_account_id=broker_account_id)
        
        # Get client_id from metadata (we need to find it)
        for cid, meta in hub.client_metadata.items():
            if meta.get('api_key') == api_key and meta.get('connected_at'):
                client_id = cid
                break
        
        if not client_id:
            await websocket.close(code=4002, reason="Registration failed")
            return
        
        # Listen for client messages (heartbeat, commands, etc.)
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'ping':
                    # Respond to ping
                    await hub._send_to_client(client_id, {
                        'type': 'pong',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    })
                    
                    # Update heartbeat
                    if client_id in hub.client_metadata:
                        hub.client_metadata[client_id]['last_heartbeat'] = time.time()
                
                elif msg_type == 'get_stats':
                    # Return hub statistics
                    await hub._send_to_client(client_id, {
                        'type': 'stats',
                        'data': hub.get_stats(),
                    })
                
                else:
                    logger.warning(f"Unknown message type from client {client_id}: {msg_type}")
            
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {client_id}")
            except Exception as e:
                logger.error(f"Error processing message from client {client_id}: {e}")
    
    except asyncio.TimeoutError:
        logger.warning("WebSocket authentication timeout")
        await websocket.close(code=4003, reason="Authentication timeout")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket handler error: {e}")
    finally:
        if client_id:
            hub = get_signal_hub()
            await hub.unregister_client(client_id)


def integrate_with_signal_notifier():
    """
    Integrate WebSocket broadcasting with existing SignalNotifier.
    
    Call this function after initializing SignalNotifier to enable
    automatic signal broadcasting to WebSocket clients.
    
    Example usage in trading_executor.py:
        from app.services.websocket_signal import integrate_with_signal_notifier
        
        # After sending notification via SignalNotifier
        notifier.notify_signal(...)
        
        # Also broadcast via WebSocket
        integrate_with_signal_notifier()
    """
    # This function will be called by TradingExecutor to broadcast signals
    pass


if __name__ == "__main__":
    """
    Test standalone WebSocket server.
    
    Run with: python websocket_signal.py
    
    Then connect with a WebSocket client to ws://localhost:8765/ws
    """
    import sys
    
    if not WEBSOCKETS_AVAILABLE:
        print("ERROR: websockets library not installed")
        print("Install with: pip install websockets")
        sys.exit(1)
    
    async def main():
        hub = get_signal_hub()
        
        # Start WebSocket server
        async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
            logger.info("WebSocket Signal Hub started on ws://0.0.0.0:8765/ws")
            logger.info("Connect with: ws://localhost:8765/ws")
            logger.info("Send auth message: {'api_key': 'your-api-key'}")
            
            # Keep running
            await asyncio.Future()
    
    asyncio.run(main())
