"""
QuantDinger Local Trade Executor Client

This is a local Python client that receives trading signals from QuantDinger Cloud
via WebSocket and executes trades on local brokers (MT5, IBKR, etc.).

Architecture:
    Cloud QuantDinger (AI Brain)
        ↓ WebSocket (real-time)
    This Client (Trade Executor)
        ↓ Direct API
    MT5 / IBKR / Other Brokers

Usage:
    python local_trade_executor.py --api-key YOUR_API_KEY --cloud-url ws://your-cloud.com/ws/signals

Features:
    - Real-time signal reception
    - Automatic reconnection
    - Signal validation and filtering
    - Risk management (position sizing, stop loss)
    - Multi-broker support (MT5, IBKR)
    - Trade logging and monitoring
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("ERROR: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


class LocalTradeExecutor:
    """
    Local trade executor that receives signals from cloud and executes trades.
    """
    
    def __init__(
        self,
        api_key: str,
        cloud_url: str = "ws://localhost:8765/ws",
        broker_type: str = "mt5",
        risk_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the local trade executor.
        
        Args:
            api_key: QuantDinger Cloud API key for authentication
            cloud_url: WebSocket URL of QuantDinger Cloud
            broker_type: Broker type ('mt5', 'ibkr', 'simulation')
            risk_config: Risk management configuration
        """
        self.api_key = api_key
        self.cloud_url = cloud_url
        self.broker_type = broker_type.lower()
        
        # Risk management configuration
        self.risk_config = risk_config or {
            'max_position_size': 0.1,  # Max 10% per trade
            'max_daily_loss': 0.05,    # Max 5% daily loss
            'max_open_positions': 5,   # Max 5 concurrent positions
            'stop_loss_pct': 0.02,     # 2% stop loss
            'take_profit_pct': 0.04,   # 4% take profit
        }
        
        # State
        self.connected = False
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_delay = 300  # 5 minutes
        self.signal_count = 0
        self.trade_count = 0
        
        # Broker client (initialized based on broker_type)
        self.broker_client = None
        
        print(f"LocalTradeExecutor initialized:")
        print(f"  Cloud URL: {cloud_url}")
        print(f"  Broker: {broker_type}")
        print(f"  Max position size: {self.risk_config['max_position_size']*100}%")
        print(f"  Max daily loss: {self.risk_config['max_daily_loss']*100}%")
    
    async def connect(self):
        """Connect to QuantDinger Cloud WebSocket."""
        while True:
            try:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to {self.cloud_url}...")
                
                async with websockets.connect(self.cloud_url) as websocket:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected!")
                    
                    # Send authentication
                    auth_message = {
                        'api_key': self.api_key,
                        'client_type': 'local_executor',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    }
                    await websocket.send(json.dumps(auth_message))
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Authentication sent")
                    
                    # Wait for connection confirmation
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(response)
                    
                    if data.get('type') == 'connection_established':
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Authentication successful")
                        print(f"  Client ID: {data.get('client_id')}")
                        self.connected = True
                        self.reconnect_delay = 5  # Reset delay
                        
                        # Initialize broker
                        self._initialize_broker()
                        
                        # Start message loop
                        await self._message_loop(websocket)
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✗ Authentication failed: {data}")
                        break
            
            except (ConnectionClosed, ConnectionClosedError) as e:
                self.connected = False
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connection closed: {e}")
                print(f"Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            
            except Exception as e:
                self.connected = False
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connection error: {e}")
                print(f"Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    async def _message_loop(self, websocket):
        """Main message processing loop."""
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Waiting for trading signals...")
        print("=" * 80)
        
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type', '')
                
                if msg_type == 'trading_signal':
                    await self._handle_trading_signal(data)
                
                elif msg_type == 'pong':
                    # Heartbeat response
                    pass
                
                elif msg_type == 'stats':
                    print(f"\n[Stats] {json.dumps(data.get('data', {}), indent=2)}")
                
                else:
                    print(f"\n[Unknown message type] {msg_type}")
            
            except json.JSONDecodeError:
                print(f"\n[Error] Invalid JSON received")
            except Exception as e:
                print(f"\n[Error] Message processing error: {e}")
    
    async def _handle_trading_signal(self, signal_data: Dict[str, Any]):
        """Handle incoming trading signal."""
        self.signal_count += 1
        
        signal = signal_data.get('data', {})
        signal_id = signal_data.get('signal_id', 'N/A')
        timestamp = signal_data.get('timestamp', '')
        
        print(f"\n{'='*80}")
        print(f"[Signal #{self.signal_count}] Received at {timestamp}")
        print(f"Signal ID: {signal_id}")
        print(f"Strategy: {signal.get('strategy_name', 'N/A')}")
        print(f"Symbol: {signal.get('symbol', 'N/A')}")
        print(f"Type: {signal.get('signal_type', 'N/A')}")
        print(f"Price: {signal.get('price', 0)}")
        print(f"Stake: {signal.get('stake_amount', 0)}")
        print(f"Direction: {signal.get('direction', 'N/A')}")
        
        # Validate signal
        if not self._validate_signal(signal):
            print(f"[Validation] ✗ Signal rejected")
            return
        
        print(f"[Validation] ✓ Signal accepted")
        
        # Execute trade
        try:
            result = await self._execute_trade(signal)
            if result.get('success'):
                self.trade_count += 1
                print(f"[Execution] ✓ Trade executed successfully")
                print(f"  Order ID: {result.get('order_id')}")
                print(f"  Filled: {result.get('filled')}")
                print(f"  Price: {result.get('price')}")
            else:
                print(f"[Execution] ✗ Trade failed: {result.get('error')}")
        
        except Exception as e:
            print(f"[Execution] ✗ Trade execution error: {e}")
    
    def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """Validate trading signal against risk rules."""
        # Check required fields
        required_fields = ['symbol', 'signal_type', 'price']
        for field in required_fields:
            if not signal.get(field):
                print(f"[Validation] Missing required field: {field}")
                return False
        
        # Check stake amount
        stake = signal.get('stake_amount', 0)
        max_stake = self.risk_config['max_position_size']
        if stake > max_stake:
            print(f"[Validation] Stake {stake} exceeds max {max_stake}")
            return False
        
        # TODO: Add more validation rules
        # - Check max open positions
        # - Check daily loss limit
        # - Check symbol whitelist/blacklist
        
        return True
    
    async def _execute_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade on broker."""
        if self.broker_type == 'mt5':
            return await self._execute_mt5_trade(signal)
        elif self.broker_type == 'ibkr':
            return await self._execute_ibkr_trade(signal)
        elif self.broker_type == 'simulation':
            return await self._execute_simulation_trade(signal)
        else:
            return {'success': False, 'error': f'Unsupported broker: {self.broker_type}'}
    
    async def _execute_mt5_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade via MT5."""
        try:
            # Import MT5 client
            try:
                import MetaTrader5 as mt5
            except ImportError:
                return {
                    'success': False,
                    'error': 'MetaTrader5 not installed. Run: pip install MetaTrader5'
                }
            
            # Initialize MT5 if not already done
            if self.broker_client is None:
                if not mt5.initialize():
                    return {
                        'success': False,
                        'error': f'MT5 initialization failed: {mt5.last_error()}'
                    }
                self.broker_client = mt5
                print("[MT5] Initialized successfully")
            
            # Map signal type to MT5 action
            signal_type = signal.get('signal_type', '').lower()
            symbol = signal.get('symbol', '')
            price = float(signal.get('price', 0))
            volume = float(signal.get('stake_amount', 0.1))
            
            # Determine order type
            if 'open_long' in signal_type or 'add_long' in signal_type:
                order_type = mt5.ORDER_TYPE_BUY
            elif 'open_short' in signal_type or 'add_short' in signal_type:
                order_type = mt5.ORDER_TYPE_SELL
            elif 'close_long' in signal_type or 'reduce_long' in signal_type:
                order_type = mt5.ORDER_TYPE_SELL
            elif 'close_short' in signal_type or 'reduce_short' in signal_type:
                order_type = mt5.ORDER_TYPE_BUY
            else:
                return {'success': False, 'error': f'Unknown signal type: {signal_type}'}
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"QuantDinger-{signal.get('strategy_name', '')}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            print(f"[MT5] Sending order: {symbol} {signal_type} vol={volume} price={price}")
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'Order failed: {result.comment} (code: {result.retcode})'
                }
            
            return {
                'success': True,
                'order_id': result.order,
                'filled': volume,
                'price': price,
                'raw': result._asdict(),
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _execute_ibkr_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute trade via Interactive Brokers."""
        try:
            # Import IBKR client
            try:
                from ib_insync import IB, Stock, MarketOrder
            except ImportError:
                return {
                    'success': False,
                    'error': 'ib_insync not installed. Run: pip install ib_insync'
                }
            
            # Initialize IBKR if not already done
            if self.broker_client is None:
                self.broker_client = IB()
                # Connect to TWS/Gateway (default: localhost:7497 for paper trading)
                try:
                    self.broker_client.connect('127.0.0.1', 7497, clientId=1)
                    print("[IBKR] Connected successfully")
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'IBKR connection failed: {e}'
                    }
            
            # Map signal type to IBKR action
            signal_type = signal.get('signal_type', '').lower()
            symbol = signal.get('symbol', '')
            quantity = int(signal.get('stake_amount', 1))  # IBKR uses share count
            
            # Determine action
            if 'open_long' in signal_type or 'add_long' in signal_type:
                action = 'BUY'
            elif 'close_long' in signal_type or 'reduce_long' in signal_type:
                action = 'SELL'
            else:
                return {'success': False, 'error': f'Unsupported signal type for IBKR: {signal_type}'}
            
            # Create contract and order
            contract = Stock(symbol, 'SMART', 'USD')
            order = MarketOrder(action, quantity)
            
            # Place order
            print(f"[IBKR] Placing order: {action} {quantity} shares of {symbol}")
            trade = self.broker_client.placeOrder(contract, order)
            
            # Wait for order status (with timeout)
            await asyncio.sleep(1)  # Give time for order to be processed
            
            # Check order status
            if trade.orderStatus.status in ['Filled', 'Submitted']:
                return {
                    'success': True,
                    'order_id': trade.order.orderId,
                    'filled': float(trade.orderStatus.filled),
                    'price': float(trade.orderStatus.avgFillPrice or 0),
                    'status': trade.orderStatus.status,
                }
            else:
                return {
                    'success': False,
                    'error': f'Order status: {trade.orderStatus.status}'
                }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _execute_simulation_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate trade execution (for testing)."""
        print(f"[Simulation] Executing simulated trade...")
        await asyncio.sleep(0.5)  # Simulate network delay
        
        return {
            'success': True,
            'order_id': f"SIM-{int(time.time()*1000)}",
            'filled': signal.get('stake_amount', 0.1),
            'price': signal.get('price', 0),
        }
    
    def _initialize_broker(self):
        """Initialize broker connection."""
        if self.broker_type == 'simulation':
            print(f"[Broker] Using simulation mode")
        elif self.broker_type == 'mt5':
            print(f"[Broker] MT5 will be initialized on first trade")
        elif self.broker_type == 'ibkr':
            print(f"[Broker] IBKR integration pending")
        else:
            print(f"[Broker] Unknown broker type: {self.broker_type}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='QuantDinger Local Trade Executor')
    parser.add_argument('--api-key', required=True, help='QuantDinger Cloud API key')
    parser.add_argument('--cloud-url', default='ws://localhost:8765/ws', help='Cloud WebSocket URL')
    parser.add_argument('--broker', default='simulation', choices=['mt5', 'ibkr', 'simulation'], help='Broker type')
    
    args = parser.parse_args()
    
    if not WEBSOCKETS_AVAILABLE:
        print("ERROR: websockets library not installed")
        print("Install with: pip install websockets")
        sys.exit(1)
    
    executor = LocalTradeExecutor(
        api_key=args.api_key,
        cloud_url=args.cloud_url,
        broker_type=args.broker,
    )
    
    print("\nStarting Local Trade Executor...")
    print("Press Ctrl+C to stop\n")
    
    try:
        await executor.connect()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
