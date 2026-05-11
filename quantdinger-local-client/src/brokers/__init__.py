"""Broker integration modules (MT5, IBKR, etc.)."""

from .base import BaseBroker
from .simulation import SimulationBroker

# MT5 and IBKR brokers (optional - require additional dependencies)
try:
    from .mt5 import MT5Broker
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    MT5Broker = None

try:
    from .ibkr import IBKRBroker
    IBKR_AVAILABLE = True
except ImportError:
    IBKR_AVAILABLE = False
    IBKRBroker = None

__all__ = [
    'BaseBroker', 
    'SimulationBroker',
    'MT5Broker',
    'IBKRBroker',
    'MT5_AVAILABLE',
    'IBKR_AVAILABLE',
]
