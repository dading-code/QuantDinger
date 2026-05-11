"""
Interactive Brokers Broker Integration

Executes trades via Interactive Brokers TWS/Gateway.
Requires ib_insync library and running TWS/Gateway.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from ib_insync import IB, Stock, Forex, MarketOrder, LimitOrder, Trade
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False
    IB = None
    Stock = None
    Forex = None
    MarketOrder = None
    LimitOrder = None

from .base import BaseBroker

logger = logging.getLogger(__name__)


class IBKRBroker(BaseBroker):
    """
    Interactive Brokers broker integration.
    
    Features:
    - Direct TWS/Gateway integration
    - Stocks, Forex, Options support
    - Market and limit orders
    - Position management
    - Real-time market data
    
    Requirements:
    - ib_insync library installed
    - TWS or IB Gateway running
    - Valid IB account
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if not IB_AVAILABLE:
            raise ImportError(
                "ib_insync library not installed. "
                "Install with: pip install ib_insync"
            )
        
        super().__init__(config)
        
        # IB connection settings
        self.host = self.config.get('host', '127.0.0.1')
        self.port = self.config.get('port', 7497)  # 7497 for paper, 7496 for live
        self.client_id = self.config.get('client_id', 1)
        
        # IB client
        self.ib = None
        
        logger.info("IBKRBroker initialized")
        logger.info(f"  Host: {self.host}")
        logger.info(f"  Port: {self.port}")
        logger.info(f"  Client ID: {self.client_id}")
    
    async def connect(self) -> bool:
        """Connect to TWS/Gateway."""
        try:
            logger.info(f"🔗 Connecting to IB TWS/Gateway at {self.host}:{self.port}...")
            
            self.ib = IB()
            
            # Connect asynchronously
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id
            )
            
            self.connected = True
            
            # Get account info
            accounts = self.ib.managedAccounts()
            if accounts:
                account = accounts[0]
                
                # Get portfolio values
                portfolio = self.ib.portfolio(account)
                if portfolio:
                    total_value = sum(p.marketValue for p in portfolio)
                    self.account_balance = total_value
                
                logger.info(f"✓ IB connected successfully")
                logger.info(f"  Account: {account}")
                logger.info(f"  Portfolio value: ${total_value:,.2f}")
            else:
                logger.warning("No managed accounts found")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ IB connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from TWS/Gateway."""
        try:
            logger.info("🔌 Disconnecting from IB...")
            if self.ib:
                self.ib.disconnect()
            self.connected = False
            logger.info("✓ IB disconnected")
        except Exception as e:
            logger.error(f"IB disconnect error: {e}")
    
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
        Place an order via IB.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'EURUSD')
            side: 'buy' or 'sell'
            amount: Quantity (shares or units)
            order_type: 'market' or 'limit'
            price: Limit price (for limit orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order result with status and details
        """
        if not self.connected or not self.ib:
            return {
                'status': 'error',
                'error': 'Not connected to IB'
            }
        
        try:
            logger.info(f"📝 Placing IB order: {side.upper()} {amount} {symbol}")
            
            # Determine contract type
            if '-' in symbol or '/' in symbol:
                # Forex pair (e.g., EUR-USD)
                base_currency, quote_currency = symbol.replace('-', '/').split('/')
                contract = Forex(f'{base_currency}{quote_currency}')
            else:
                # Stock
                contract = Stock(symbol, 'SMART', 'USD')
            
            # Create order
            if order_type.lower() == 'market':
                order = MarketOrder(
                    'BUY' if side.lower() == 'buy' else 'SELL',
                    amount
                )
            elif order_type.lower() == 'limit':
                if not price:
                    raise ValueError("Price required for limit orders")
                order = LimitOrder(
                    'BUY' if side.lower() == 'buy' else 'SELL',
                    amount,
                    price
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Add optional parameters
            order.transmit = True
            order.outsideRth = True  # Allow trading outside regular hours
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            
            # Wait for order completion
            await self.ib.sleep(1)  # Give time for execution
            
            # Check order status
            if trade.orderStatus.status in ['Filled', 'Submitted']:
                fill_price = trade.orderStatus.avgFillPrice or 0
                filled_qty = trade.orderStatus.filled or 0
                
                logger.info(f"✓ Order placed: Status={trade.orderStatus.status}")
                logger.info(f"  Filled: {filled_qty} @ ${fill_price:.2f}")
                
                trade_result = {
                    'order_id': str(trade.order.orderId),
                    'status': trade.orderStatus.status.lower(),
                    'symbol': symbol,
                    'side': side.lower(),
                    'requested_amount': amount,
                    'executed_amount': filled_qty,
                    'price': fill_price,
                    'order_type': order_type,
                    'timestamp': datetime.now().isoformat(),
                    'commission': trade.orderStatus.commission or 0,
                }
                
                return trade_result
            else:
                error_msg = f"Order status: {trade.orderStatus.status}"
                logger.warning(f"⚠️ {error_msg}")
                return {
                    'status': 'pending',
                    'error': error_msg,
                    'order_id': str(trade.order.orderId)
                }
        
        except Exception as e:
            logger.error(f"❌ IB order error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close all positions for a symbol."""
        if not self.connected or not self.ib:
            return {
                'status': 'error',
                'error': 'Not connected to IB'
            }
        
        try:
            logger.info(f"🔄 Closing IB positions: {symbol}")
            
            # Get positions
            positions = self.ib.positions()
            
            target_positions = [p for p in positions if p.contract.symbol == symbol]
            
            if not target_positions:
                return {
                    'status': 'error',
                    'error': f'No open positions for {symbol}'
                }
            
            results = []
            total_pnl = 0.0
            
            for position in target_positions:
                # Close position
                qty = abs(position.position)
                side = 'SELL' if position.position > 0 else 'BUY'
                
                if '-' in symbol or '/' in symbol:
                    base_currency, quote_currency = symbol.replace('-', '/').split('/')
                    contract = Forex(f'{base_currency}{quote_currency}')
                else:
                    contract = Stock(symbol, 'SMART', 'USD')
                
                order = MarketOrder(side, qty)
                trade = self.ib.placeOrder(contract, order)
                
                await self.ib.sleep(1)
                
                pnl = position.unrealizedPNL
                total_pnl += pnl
                
                results.append({
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'pnl': pnl,
                    'status': 'closed'
                })
                
                logger.info(f"✓ Position closed: {qty} {symbol}, P&L: ${pnl:.2f}")
            
            return {
                'status': 'success',
                'action': 'close',
                'positions_closed': len(results),
                'total_pnl': total_pnl,
                'results': results,
            }
        
        except Exception as e:
            logger.error(f"❌ IB close position error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def get_balance(self) -> float:
        """Get account balance."""
        if not self.connected or not self.ib:
            return 0.0
        
        try:
            accounts = self.ib.managedAccounts()
            if accounts:
                account_summary = self.ib.accountSummary(accounts[0])
                net_liquidation = next(
                    (item.value for item in account_summary if item.tag == 'NetLiquidation'),
                    0
                )
                self.account_balance = float(net_liquidation)
                return self.account_balance
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
        
        return 0.0
    
    async def get_positions(self) -> Dict[str, Any]:
        """Get all open positions."""
        if not self.connected or not self.ib:
            return {}
        
        try:
            positions = self.ib.positions()
            
            result = {}
            for pos in positions:
                symbol = pos.contract.symbol
                result[symbol] = {
                    'symbol': symbol,
                    'quantity': pos.position,
                    'avg_cost': pos.avgCost,
                    'market_price': pos.marketPrice,
                    'market_value': pos.marketValue,
                    'unrealized_pnl': pos.unrealizedPNL,
                    'realized_pnl': pos.realizedPNL,
                }
            
            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {}
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information."""
        if not self.connected or not self.ib:
            return {}
        
        try:
            # Request market data
            if '-' in symbol or '/' in symbol:
                base_currency, quote_currency = symbol.replace('-', '/').split('/')
                contract = Forex(f'{base_currency}{quote_currency}')
            else:
                contract = Stock(symbol, 'SMART', 'USD')
            
            ticker = self.ib.reqMktData(contract)
            
            # Wait for data
            await self.ib.sleep(1)
            
            info = {
                'symbol': symbol,
                'bid': ticker.bid,
                'ask': ticker.ask,
                'last': ticker.last,
                'spread': ticker.ask - ticker.bid if ticker.ask and ticker.bid else 0,
                'volume': ticker.volume,
                'timestamp': datetime.now().isoformat(),
            }
            
            # Cancel market data
            self.ib.cancelMktData(contract)
            
            return info
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return {'error': str(e)}
