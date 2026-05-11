"""
MetaTrader 5 Broker Integration

Executes trades via MetaTrader 5 terminal.
Windows only - requires MT5 terminal installed.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from .base import BaseBroker

logger = logging.getLogger(__name__)


class MT5Broker(BaseBroker):
    """
    MetaTrader 5 broker integration.
    
    Features:
    - Direct MT5 terminal integration
    - Market and pending orders
    - Position management
    - Real-time price quotes
    - Account information
    
    Requirements:
    - Windows OS
    - MetaTrader 5 terminal installed
    - Valid broker account logged in
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not MT5_AVAILABLE:
            raise ImportError(
                "MetaTrader5 library not installed. "
                "Install with: pip install MetaTrader5 (Windows only)"
            )
        
        super().__init__(config)
        
        # MT5 configuration
        self.login = self.config.get('login', None)
        self.password = self.config.get('password', None)
        self.server = self.config.get('server', None)
        self.path = self.config.get('path', None)  # MT5 terminal path
        
        # Trading parameters
        self.magic_number = self.config.get('magic_number', 234000)
        self.deviation = self.config.get('deviation', 20)  # Points
        self.timeout = self.config.get('timeout', 60000)  # Milliseconds
        
        logger.info("MT5Broker initialized")
        if self.login:
            logger.info(f"  Login: {self.login}")
            logger.info(f"  Server: {self.server}")
    
    async def connect(self) -> bool:
        """Connect to MT5 terminal."""
        try:
            logger.info("🔗 Connecting to MT5 terminal...")
            
            # Initialize MT5
            if self.path:
                initialized = mt5.initialize(path=self.path)
            else:
                initialized = mt5.initialize()
            
            if not initialized:
                error_code = mt5.last_error()
                raise Exception(f"MT5 initialization failed: {error_code}")
            
            # Login if credentials provided
            if self.login and self.password and self.server:
                login_result = mt5.login(
                    login=self.login,
                    password=self.password,
                    server=self.server
                )
                
                if not login_result:
                    error_code = mt5.last_error()
                    raise Exception(f"MT5 login failed: {error_code}")
                
                logger.info(f"✓ Logged in to MT5: {self.login}")
            
            # Get account info
            account_info = mt5.account_info()
            if account_info:
                self.account_balance = account_info.balance
                self.connected = True
                
                logger.info(f"✓ MT5 connected successfully")
                logger.info(f"  Account: {account_info.login}")
                logger.info(f"  Balance: ${account_info.balance:.2f}")
                logger.info(f"  Equity: ${account_info.equity:.2f}")
                logger.info(f"  Leverage: 1:{account_info.leverage}")
            else:
                raise Exception("Failed to get account info")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ MT5 connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from MT5 terminal."""
        try:
            logger.info("🔌 Disconnecting from MT5...")
            mt5.shutdown()
            self.connected = False
            logger.info("✓ MT5 disconnected")
        except Exception as e:
            logger.error(f"MT5 disconnect error: {e}")
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = 'market',
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place an order via MT5.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            side: 'buy' or 'sell'
            amount: Lot size
            order_type: 'market', 'limit', 'stop'
            price: Entry price (for pending orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order result with ticket and status
        """
        if not self.connected:
            return {
                'status': 'error',
                'error': 'Not connected to MT5'
            }
        
        try:
            logger.info(f"📝 Placing MT5 order: {side.upper()} {amount} lots {symbol}")
            
            # Prepare order request
            if side.lower() == 'buy':
                action = mt5.ORDER_TYPE_BUY
                type_filling = mt5.ORDER_FILLING_IOC
            else:
                action = mt5.ORDER_TYPE_SELL
                type_filling = mt5.ORDER_FILLING_IOC
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": amount,
                "type": action,
                "type_filling": type_filling,
                "deviation": self.deviation,
                "magic": self.magic_number,
                "comment": "QuantDinger Signal",
                "type_time": mt5.ORDER_TIME_GTC,
            }
            
            # Add SL/TP if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Order failed: {result.comment} (code: {result.retcode})"
                logger.error(f"❌ {error_msg}")
                return {
                    'status': 'error',
                    'error': error_msg,
                    'retcode': result.retcode
                }
            
            # Success
            order_id = str(result.order)
            logger.info(f"✓ Order placed: Ticket #{order_id}")
            logger.info(f"  Price: {result.price:.5f}")
            logger.info(f"  Volume: {result.volume} lots")
            
            trade_result = {
                'order_id': order_id,
                'ticket': result.order,
                'status': 'filled',
                'symbol': symbol,
                'side': side.lower(),
                'volume': result.volume,
                'price': result.price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'commission': result.commission if hasattr(result, 'commission') else 0,
                'timestamp': datetime.now().isoformat(),
                'retcode': result.retcode,
                'comment': result.comment,
            }
            
            return trade_result
        
        except Exception as e:
            logger.error(f"❌ MT5 order error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close all positions for a symbol."""
        if not self.connected:
            return {
                'status': 'error',
                'error': 'Not connected to MT5'
            }
        
        try:
            logger.info(f"🔄 Closing MT5 positions: {symbol}")
            
            # Get open positions
            positions = mt5.positions_get(symbol=symbol)
            
            if not positions:
                return {
                    'status': 'error',
                    'error': f'No open positions for {symbol}'
                }
            
            results = []
            total_pnl = 0.0
            
            for position in positions:
                # Close position
                if position.type == mt5.POSITION_TYPE_BUY:
                    action = mt5.ORDER_TYPE_SELL
                else:
                    action = mt5.ORDER_TYPE_BUY
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": position.volume,
                    "type": action,
                    "position": position.ticket,
                    "deviation": self.deviation,
                    "magic": self.magic_number,
                    "comment": "QuantDinger Close",
                }
                
                result = mt5.order_send(request)
                
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    pnl = position.profit
                    total_pnl += pnl
                    
                    results.append({
                        'ticket': position.ticket,
                        'closed_ticket': result.order,
                        'pnl': pnl,
                        'status': 'closed'
                    })
                    
                    logger.info(f"✓ Position closed: Ticket #{position.ticket}, P&L: ${pnl:.2f}")
                else:
                    logger.error(f"❌ Failed to close position #{position.ticket}: {result.comment}")
            
            return {
                'status': 'success',
                'action': 'close',
                'positions_closed': len(results),
                'total_pnl': total_pnl,
                'results': results,
            }
        
        except Exception as e:
            logger.error(f"❌ MT5 close position error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def get_balance(self) -> float:
        """Get account balance."""
        if not self.connected:
            return 0.0
        
        account_info = mt5.account_info()
        if account_info:
            self.account_balance = account_info.balance
            return account_info.balance
        return 0.0
    
    async def get_positions(self) -> Dict[str, Any]:
        """Get all open positions."""
        if not self.connected:
            return {}
        
        positions = mt5.positions_get()
        if not positions:
            return {}
        
        result = {}
        for pos in positions:
            result[pos.symbol] = {
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'side': 'buy' if pos.type == mt5.POSITION_TYPE_BUY else 'sell',
                'volume': pos.volume,
                'entry_price': pos.price_open,
                'current_price': pos.price_current,
                'profit': pos.profit,
                'swap': pos.swap,
                'commission': pos.commission,
                'opened_at': datetime.fromtimestamp(pos.time).isoformat(),
            }
        
        return result
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information."""
        if not self.connected:
            return {}
        
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return {'error': f'Symbol {symbol} not found'}
        
        # Get tick
        tick = mt5.symbol_info_tick(symbol)
        
        return {
            'symbol': symbol,
            'bid': tick.bid if tick else 0,
            'ask': tick.ask if tick else 0,
            'spread': (tick.ask - tick.bid) if tick else 0,
            'last_price': tick.last if tick else 0,
            'point': symbol_info.point,
            'digits': symbol_info.digits,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'timestamp': datetime.now().isoformat(),
        }
