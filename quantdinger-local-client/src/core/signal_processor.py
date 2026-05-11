"""
Signal Processor

Processes trading signals and executes trades through brokers.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.brokers.base import BaseBroker
from src.core.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class SignalProcessor:
    """
    Processes trading signals and manages trade execution.
    
    Workflow:
    1. Receive signal from WebSocket
    2. Validate signal format
    3. Check risk management rules
    4. Execute trade via broker
    5. Record trade result
    """
    
    def __init__(self, broker: BaseBroker, risk_manager: RiskManager):
        """
        Initialize signal processor.
        
        Args:
            broker: Broker instance for trade execution
            risk_manager: Risk manager for validation
        """
        self.broker = broker
        self.risk_manager = risk_manager
        
        # Statistics
        self.signals_received = 0
        self.signals_processed = 0
        self.trades_executed = 0
        self.trades_rejected = 0
        
        logger.info("SignalProcessor initialized")
    
    async def process_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming trading signal.
        
        Args:
            signal_data: Raw signal data from WebSocket
            
        Returns:
            Processing result with status and details
        """
        self.signals_received += 1
        
        try:
            # 1. Validate signal format
            if not self._validate_signal(signal_data):
                self.trades_rejected += 1
                return {
                    'status': 'rejected',
                    'reason': 'Invalid signal format',
                    'signal_id': signal_data.get('signal_id', 'unknown')
                }
            
            signal = signal_data.get('data', {})
            signal_id = signal_data.get('signal_id', 'unknown')
            
            logger.info(f"📊 Processing signal #{self.signals_received}: {signal_id}")
            
            # 2. Get account balance
            account_balance = await self.broker.get_balance()
            
            # 3. Risk management check
            allowed, reason = self.risk_manager.check_before_trade(signal, account_balance)
            
            if not allowed:
                self.trades_rejected += 1
                logger.warning(f"⚠️ Trade rejected: {reason}")
                
                return {
                    'status': 'rejected',
                    'reason': reason,
                    'signal_id': signal_id,
                    'risk_check': False
                }
            
            # 4. Execute trade
            trade_result = await self._execute_trade(signal, account_balance)
            
            # 5. Update risk manager
            self.risk_manager.update_after_trade(trade_result)
            
            self.signals_processed += 1
            self.trades_executed += 1
            
            logger.info(
                f"✓ Trade executed: {trade_result.get('order_id')} | "
                f"P&L: ${trade_result.get('pnl', 0):.2f}"
            )
            
            return {
                'status': 'executed',
                'signal_id': signal_id,
                'trade_result': trade_result,
                'risk_check': True
            }
        
        except Exception as e:
            logger.error(f"❌ Signal processing error: {e}", exc_info=True)
            
            return {
                'status': 'error',
                'reason': str(e),
                'signal_id': signal_data.get('signal_id', 'unknown')
            }
    
    def _validate_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Validate signal format and required fields.
        
        Args:
            signal_data: Signal data to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(signal_data, dict):
            return False
        
        signal = signal_data.get('data', {})
        
        # Required fields
        required_fields = ['symbol', 'signal_type', 'direction']
        
        for field in required_fields:
            if field not in signal or not signal[field]:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate signal type
        valid_signal_types = ['buy', 'sell', 'close', 'modify']
        if signal.get('signal_type') not in valid_signal_types:
            logger.warning(f"Invalid signal type: {signal.get('signal_type')}")
            return False
        
        # Validate direction
        valid_directions = ['buy', 'sell', 'long', 'short']
        if signal.get('direction') not in valid_directions:
            logger.warning(f"Invalid direction: {signal.get('direction')}")
            return False
        
        return True
    
    async def _execute_trade(self, signal: Dict[str, Any], account_balance: float) -> Dict[str, Any]:
        """
        Execute trade based on signal.
        
        Args:
            signal: Validated signal data
            account_balance: Current account balance
            
        Returns:
            Trade execution result
        """
        symbol = signal.get('symbol')
        signal_type = signal.get('signal_type', 'buy').lower()
        direction = signal.get('direction', 'buy').lower()
        stake_amount = signal.get('stake_amount', 0)
        
        # Normalize direction
        if direction in ['long']:
            side = 'buy'
        elif direction in ['short']:
            side = 'sell'
        else:
            side = direction
        
        logger.info(f"Executing trade: {side.upper()} {stake_amount} {symbol}")
        
        # Handle different signal types
        if signal_type == 'close':
            # Close existing position
            result = await self.broker.close_position(symbol)
        else:
            # Place new order
            result = await self.broker.place_order(
                symbol=symbol,
                side=side,
                amount=stake_amount,
                order_type='market',
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
            )
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get signal processing statistics."""
        return {
            'signals_received': self.signals_received,
            'signals_processed': self.signals_processed,
            'trades_executed': self.trades_executed,
            'trades_rejected': self.trades_rejected,
            'success_rate': (
                self.trades_executed / self.signals_received * 100
                if self.signals_received > 0 else 0
            ),
            'risk_summary': self.risk_manager.get_risk_summary(),
        }
