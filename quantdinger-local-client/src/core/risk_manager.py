"""
Risk Management Engine

Implements risk controls to protect trading capital.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Risk management engine that validates trades before execution.
    
    Checks:
    - Maximum position size
    - Daily loss limit
    - Maximum open positions
    - Symbol whitelist/blacklist
    - Trading hours
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk manager.
        
        Args:
            config: Risk management configuration
        """
        # Position sizing
        self.max_position_size = config.get('max_position_size', 0.1)  # 10% per trade
        self.max_position_value = config.get('max_position_value', None)  # Max $ value
        
        # Loss limits
        self.max_daily_loss = config.get('max_daily_loss', 0.05)  # 5% daily loss
        self.max_drawdown = config.get('max_drawdown', 0.15)  # 15% max drawdown
        
        # Position limits
        self.max_open_positions = config.get('max_open_positions', 5)
        self.max_positions_per_symbol = config.get('max_positions_per_symbol', 1)
        
        # Symbol filters
        self.symbol_whitelist = config.get('symbol_whitelist', [])
        self.symbol_blacklist = config.get('symbol_blacklist', [])
        
        # Trading hours (UTC)
        self.trading_hours_start = config.get('trading_hours_start', None)  # e.g., "09:30"
        self.trading_hours_end = config.get('trading_hours_end', None)  # e.g., "16:00"
        
        # State tracking
        self.daily_pnl = 0.0
        self.initial_balance = config.get('initial_balance', 10000.0)
        self.current_balance = self.initial_balance
        self.open_positions_count = 0
        self.positions_by_symbol = {}
        
        # Daily reset
        self.last_reset_date = date.today()
        
        logger.info("RiskManager initialized")
        logger.info(f"  Max position size: {self.max_position_size*100:.1f}%")
        logger.info(f"  Max daily loss: {self.max_daily_loss*100:.1f}%")
        logger.info(f"  Max open positions: {self.max_open_positions}")
    
    def check_before_trade(self, signal: Dict[str, Any], account_balance: float) -> tuple:
        """
        Check if a trade is allowed by risk rules.
        
        Args:
            signal: Trading signal data
            account_balance: Current account balance
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Reset daily stats if new day
        self._check_daily_reset()
        
        symbol = signal.get('symbol', '')
        stake_amount = signal.get('stake_amount', 0)
        direction = signal.get('direction', 'buy')
        
        # 1. Check symbol whitelist/blacklist
        if not self._check_symbol_filter(symbol):
            return False, f"Symbol {symbol} not allowed by filter"
        
        # 2. Check trading hours
        if not self._check_trading_hours():
            return False, "Outside trading hours"
        
        # 3. Check daily loss limit
        if not self._check_daily_loss(account_balance):
            return False, f"Daily loss limit reached: {self.daily_pnl:.2f}"
        
        # 4. Check maximum drawdown
        if not self._check_max_drawdown(account_balance):
            return False, "Maximum drawdown reached"
        
        # 5. Check position size
        if not self._check_position_size(stake_amount, account_balance):
            return False, f"Position size too large: {stake_amount}"
        
        # 6. Check maximum open positions
        if not self._check_max_positions():
            return False, f"Max open positions reached: {self.open_positions_count}"
        
        # 7. Check positions per symbol
        if not self._check_positions_per_symbol(symbol):
            return False, f"Already have position in {symbol}"
        
        return True, "OK"
    
    def update_after_trade(self, trade_result: Dict[str, Any]):
        """
        Update risk manager state after trade execution.
        
        Args:
            trade_result: Trade execution result
        """
        symbol = trade_result.get('symbol', '')
        side = trade_result.get('side', '')
        amount = trade_result.get('executed_amount', 0)
        pnl = trade_result.get('pnl', 0)
        
        # Update P&L
        if pnl != 0:
            self.daily_pnl += pnl
            self.current_balance += pnl
        
        # Update position count
        if trade_result.get('action') == 'close':
            self.open_positions_count -= 1
            self.positions_by_symbol[symbol] = self.positions_by_symbol.get(symbol, 1) - 1
        else:
            self.open_positions_count += 1
            self.positions_by_symbol[symbol] = self.positions_by_symbol.get(symbol, 0) + 1
        
        logger.info(
            f"Trade recorded: {symbol} {side} | "
            f"P&L: ${pnl:.2f} | Daily P&L: ${self.daily_pnl:.2f}"
        )
    
    def _check_daily_reset(self):
        """Reset daily statistics if new day."""
        today = date.today()
        if today != self.last_reset_date:
            logger.info(f"New trading day: resetting daily stats")
            self.daily_pnl = 0.0
            self.last_reset_date = today
    
    def _check_symbol_filter(self, symbol: str) -> bool:
        """Check symbol against whitelist/blacklist."""
        # Blacklist takes precedence
        if self.symbol_blacklist and symbol in self.symbol_blacklist:
            logger.warning(f"Symbol {symbol} is blacklisted")
            return False
        
        # If whitelist exists, symbol must be in it
        if self.symbol_whitelist and symbol not in self.symbol_whitelist:
            logger.warning(f"Symbol {symbol} not in whitelist")
            return False
        
        return True
    
    def _check_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        if not self.trading_hours_start or not self.trading_hours_end:
            return True  # No restrictions
        
        now = datetime.utcnow().time()
        start_time = datetime.strptime(self.trading_hours_start, "%H:%M").time()
        end_time = datetime.strptime(self.trading_hours_end, "%H:%M").time()
        
        return start_time <= now <= end_time
    
    def _check_daily_loss(self, account_balance: float) -> bool:
        """Check if daily loss limit is reached."""
        if self.daily_pnl < -(account_balance * self.max_daily_loss):
            logger.error(
                f"Daily loss limit reached: ${self.daily_pnl:.2f} "
                f"(limit: ${account_balance * self.max_daily_loss:.2f})"
            )
            return False
        
        return True
    
    def _check_max_drawdown(self, account_balance: float) -> bool:
        """Check if maximum drawdown is reached."""
        drawdown = (self.initial_balance - account_balance) / self.initial_balance
        
        if drawdown > self.max_drawdown:
            logger.error(
                f"Maximum drawdown reached: {drawdown*100:.2f}% "
                f"(limit: {self.max_drawdown*100:.2f}%)"
            )
            return False
        
        return True
    
    def _check_position_size(self, stake_amount: float, account_balance: float) -> bool:
        """Check if position size is within limits."""
        # Percentage-based limit
        position_pct = stake_amount / account_balance if account_balance > 0 else 0
        
        if position_pct > self.max_position_size:
            logger.warning(
                f"Position size too large: {position_pct*100:.2f}% "
                f"(limit: {self.max_position_size*100:.2f}%)"
            )
            return False
        
        # Value-based limit
        if self.max_position_value and stake_amount > self.max_position_value:
            logger.warning(
                f"Position value too large: ${stake_amount:.2f} "
                f"(limit: ${self.max_position_value:.2f})"
            )
            return False
        
        return True
    
    def _check_max_positions(self) -> bool:
        """Check if maximum open positions is reached."""
        if self.open_positions_count >= self.max_open_positions:
            logger.warning(
                f"Max open positions reached: {self.open_positions_count} "
                f"(limit: {self.max_open_positions})"
            )
            return False
        
        return True
    
    def _check_positions_per_symbol(self, symbol: str) -> bool:
        """Check if already have position in this symbol."""
        current_count = self.positions_by_symbol.get(symbol, 0)
        
        if current_count >= self.max_positions_per_symbol:
            logger.warning(f"Already have position in {symbol}")
            return False
        
        return True
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get current risk status summary."""
        return {
            'daily_pnl': self.daily_pnl,
            'current_balance': self.current_balance,
            'open_positions': self.open_positions_count,
            'max_positions': self.max_open_positions,
            'positions_by_symbol': self.positions_by_symbol.copy(),
            'last_reset_date': self.last_reset_date.isoformat(),
        }
