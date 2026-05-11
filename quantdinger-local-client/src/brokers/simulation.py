"""
Simulation Broker for Testing

Simulates trade execution without real money.
Useful for testing and development.
"""

import asyncio
import random
from datetime import datetime
from typing import Dict, Any, Optional

from .base import BaseBroker


class SimulationBroker(BaseBroker):
    """
    Simulation broker that mimics real trading behavior.
    
    Features:
    - Simulated order execution with realistic delays
    - Random slippage and spread
    - Position tracking
    - P&L calculation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Simulation parameters
        self.initial_balance = self.config.get('initial_balance', 10000.0)
        self.account_balance = self.initial_balance
        self.equity = self.initial_balance
        
        # Simulation settings
        self.execution_delay = self.config.get('execution_delay', 0.5)  # seconds
        self.slippage_pct = self.config.get('slippage_pct', 0.001)  # 0.1%
        self.spread_pct = self.config.get('spread_pct', 0.0005)  # 0.05%
        
        # Price simulation
        self.base_prices = {}
        
        print(f"SimulationBroker initialized:")
        print(f"  Initial balance: ${self.initial_balance:,.2f}")
        print(f"  Execution delay: {self.execution_delay}s")
        print(f"  Slippage: {self.slippage_pct*100:.2f}%")
    
    async def connect(self) -> bool:
        """Connect to simulated broker."""
        print("🔗 Connecting to simulation broker...")
        await asyncio.sleep(0.5)  # Simulate connection delay
        
        self.connected = True
        print("✓ Simulation broker connected")
        return True
    
    async def disconnect(self):
        """Disconnect from simulated broker."""
        print("🔌 Disconnecting from simulation broker...")
        self.connected = False
        print("✓ Simulation broker disconnected")
    
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
        Place a simulated order.
        
        Simulates:
        - Execution delay
        - Slippage
        - Spread
        - Commission
        """
        if not self.connected:
            return {
                'status': 'error',
                'error': 'Not connected to broker'
            }
        
        print(f"\n📝 Placing order: {side.upper()} {amount} {symbol}")
        
        # Simulate execution delay
        await asyncio.sleep(self.execution_delay)
        
        # Get or simulate current price
        if price is None:
            price = await self._get_simulated_price(symbol)
        
        # Apply slippage
        slippage = price * self.slippage_pct * random.uniform(-1, 1)
        executed_price = price + slippage
        
        # Apply spread (buy higher, sell lower)
        spread = executed_price * self.spread_pct
        if side.lower() == 'buy':
            executed_price += spread
        else:
            executed_price -= spread
        
        # Calculate commission (0.01% per trade)
        commission = amount * executed_price * 0.0001
        
        # Create order result
        order_id = f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        
        trade_result = {
            'order_id': order_id,
            'status': 'filled',
            'symbol': symbol,
            'side': side.lower(),
            'requested_amount': amount,
            'executed_amount': amount,
            'requested_price': price,
            'executed_price': round(executed_price, 5),
            'slippage': round(slippage, 5),
            'spread': round(spread, 5),
            'commission': round(commission, 2),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now().isoformat(),
            'execution_time': self.execution_delay,
        }
        
        # Update position
        await self._update_position(symbol, side.lower(), amount, executed_price)
        
        # Record trade
        self.trades_history.append(trade_result)
        
        print(f"✓ Order filled: {order_id}")
        print(f"  Price: ${executed_price:.5f} (slippage: ${slippage:.5f})")
        print(f"  Commission: ${commission:.2f}")
        
        return trade_result
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close an existing position."""
        if symbol not in self.positions:
            return {
                'status': 'error',
                'error': f'No open position for {symbol}'
            }
        
        position = self.positions[symbol]
        side = 'sell' if position['side'] == 'buy' else 'buy'
        amount = position['amount']
        
        print(f"\n🔄 Closing position: {symbol}")
        
        # Close at current market price
        result = await self.place_order(symbol, side, amount)
        
        # Calculate P&L
        pnl = await self._calculate_pnl(symbol, result['executed_price'])
        
        close_result = {
            **result,
            'action': 'close',
            'pnl': pnl,
            'position_closed': True,
        }
        
        # Remove position
        del self.positions[symbol]
        
        print(f"✓ Position closed. P&L: ${pnl:.2f}")
        
        return close_result
    
    async def get_balance(self) -> float:
        """Get account balance."""
        return self.account_balance
    
    async def get_positions(self) -> Dict[str, Any]:
        """Get current open positions."""
        return self.positions.copy()
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get simulated symbol information."""
        price = await self._get_simulated_price(symbol)
        
        return {
            'symbol': symbol,
            'bid': round(price * (1 - self.spread_pct/2), 5),
            'ask': round(price * (1 + self.spread_pct/2), 5),
            'spread': round(price * self.spread_pct, 5),
            'last_price': round(price, 5),
            'timestamp': datetime.now().isoformat(),
        }
    
    async def _get_simulated_price(self, symbol: str) -> float:
        """Get or generate simulated price."""
        if symbol not in self.base_prices:
            # Initialize with realistic base prices
            base_prices = {
                'EURUSD': 1.0850,
                'GBPUSD': 1.2650,
                'USDJPY': 149.50,
                'AAPL': 175.50,
                'MSFT': 380.25,
                'GOOGL': 140.75,
                'BTCUSD': 43500.00,
                'ETHUSD': 2280.00,
            }
            self.base_prices[symbol] = base_prices.get(symbol, 100.0)
        
        # Add small random movement
        movement = self.base_prices[symbol] * random.uniform(-0.001, 0.001)
        self.base_prices[symbol] += movement
        
        return self.base_prices[symbol]
    
    async def _update_position(self, symbol: str, side: str, amount: float, price: float):
        """Update position after order execution."""
        if symbol in self.positions:
            existing = self.positions[symbol]
            
            if existing['side'] == side:
                # Increase position
                total_amount = existing['amount'] + amount
                avg_price = ((existing['amount'] * existing['entry_price']) + 
                           (amount * price)) / total_amount
                
                self.positions[symbol] = {
                    'symbol': symbol,
                    'side': side,
                    'amount': total_amount,
                    'entry_price': avg_price,
                    'current_price': price,
                    'unrealized_pnl': 0.0,
                    'opened_at': existing['opened_at'],
                    'updated_at': datetime.now().isoformat(),
                }
            else:
                # Reduce or reverse position
                if amount >= existing['amount']:
                    # Close and reverse
                    remaining = amount - existing['amount']
                    if remaining > 0:
                        self.positions[symbol] = {
                            'symbol': symbol,
                            'side': side,
                            'amount': remaining,
                            'entry_price': price,
                            'current_price': price,
                            'unrealized_pnl': 0.0,
                            'opened_at': datetime.now().isoformat(),
                            'updated_at': datetime.now().isoformat(),
                        }
                    else:
                        del self.positions[symbol]
                else:
                    # Partial close
                    existing['amount'] -= amount
                    existing['updated_at'] = datetime.now().isoformat()
        else:
            # New position
            self.positions[symbol] = {
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'entry_price': price,
                'current_price': price,
                'unrealized_pnl': 0.0,
                'opened_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
    
    async def _calculate_pnl(self, symbol: str, exit_price: float) -> float:
        """Calculate profit/loss for closing a position."""
        if symbol not in self.positions:
            return 0.0
        
        position = self.positions[symbol]
        entry_price = position['entry_price']
        amount = position['amount']
        
        if position['side'] == 'buy':
            pnl = (exit_price - entry_price) * amount
        else:
            pnl = (entry_price - exit_price) * amount
        
        # Update balance
        self.account_balance += pnl
        
        return pnl
