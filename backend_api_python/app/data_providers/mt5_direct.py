"""
MT5 直接连接数据提供者

功能：
1. 直接连接 MT5 终端获取实时数据
2. 获取多周期 K 线数据
3. 获取技术指标
4. 获取市场深度(DOM)
5. 获取账户信息和持仓

注意：需要在 Windows 系统上运行，且需要安装 MT5 终端
"""
import os
import sys
import logging
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 延迟导入 MetaTrader5
mt5 = None

def _ensure_mt5():
    global mt5
    if mt5 is None:
        try:
            import MetaTrader5 as _mt5
            mt5 = _mt5
        except ImportError:
            logger.warning("MetaTrader5 not installed. MT5 features will be unavailable.")
            raise ImportError(
                "MetaTrader5 is not installed. Run: pip install MetaTrader5\n"
                "Note: This library only works on Windows with MT5 terminal installed."
            )
    return mt5

# 时间周期映射
TIMEFRAME_MAP = {
    "M1": 1,    # mt5.TIMEFRAME_M1
    "M5": 5,    # mt5.TIMEFRAME_M5
    "M15": 15,  # mt5.TIMEFRAME_M15
    "M30