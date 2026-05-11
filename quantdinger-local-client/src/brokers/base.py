"""
Base Broker Interface

Abstract base class for all broker implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseBroker(ABC):
    """
    Abstract base class for broker integrations.
    
    All broker implementations (MT5, IBKR, Simulation) must inherit from this class.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize broker.
        
        Args:
            config: Broker-specific configuration
        """
        self.config = config or {}
        self.connected = False
        self.account_balance = 0.0
        self.positions = {}
        self.trades_history = []
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Disconnect from broker."""
        pass
    
    @abstractmethod
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
        Place an order.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD', 'AAPL')
            side: 'buy' or 'sell'
            amount: Order size/quantity
            order_type: 'market', 'limit', 'stop'
            price: Limit/stop price (for non-market orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order result with status and details
        """
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close an existing position.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Close result with status and details
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """
        Get account balance.
        
        Returns:
            Current account balance
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> Dict[str, Any]:
        """
        Get current open positions.
        
        Returns:
            Dictionary of open positions
        """
        pass
    
    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get symbol information (price, spread, etc.).
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Symbol information
        """
        pass
    
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        return self.connected
    
    def get_trade_history(self) -> list:
        """Get trade history."""
        return self.trades_history.copy()
