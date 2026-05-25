"""
MT5 Server 数据提供者 - 使用智能路由获取 MT5 数据

核心设计：
1. 使用智能数据路由器进行数据采集
2. 支持多 Desktop 客户端，自动选择最优客户端
3. 连接断开时自动切换到其他 Desktop
4. 全局缓存避免重复获取

数据类型支持：
- 实时价格
- K线数据
- 技术指标
- 市场深度(DOM)
- 账户信息和持仓
"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional, List

from app.core.smart_data_router import smart_router
from app.services.websocket_signal import get_background_loop

logger = logging.getLogger(__name__)

# QuantDinger 周期 -> MT5 Observer MCP 周期
_QD_TO_MT5_TIMEFRAME = {
    "1M": "M1", "1MIN": "M1", "1m": "M1",
    "5M": "M5", "5MIN": "M5", "5m": "M5",
    "15M": "M15", "15MIN": "M15", "15m": "M15",
    "30M": "M30", "30MIN": "M30", "30m": "M30",
    "1H": "H1", "1HOUR": "H1", "60M": "H1", "1h": "H1",
    "4H": "H4", "4HOUR": "H4", "4h": "H4",
    "1D": "D1", "1DAY": "D1", "1d": "D1", "D": "D1",
    "1W": "W1", "1WEEK": "W1", "1w": "W1",
    "1MONTH": "MN1", "1MO": "MN1",
}

# 符号映射表
SYMBOL_MAPPING = {
    "XAUUSD": "XAU/USD",
    "XAUUSD.C": "XAU/USD",
    "XAUUSD.c": "XAU/USD",
    "XAGUSD": "XAG/USD",
    "XAGUSD.C": "XAG/USD",
    "XAGUSD.c": "XAG/USD",
    "EURUSD": "EUR/USD",
    "EURUSD.C": "EUR/USD",
    "EURUSD.c": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "GBPUSD.C": "GBP/USD",
    "GBPUSD.c": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDJPY.C": "USD/JPY",
    "USDJPY.c": "USD/JPY",
    "AUDUSD": "AUD/USD",
    "AUDUSD.C": "AUD/USD",
    "AUDUSD.c": "AUD/USD",
    "USDCAD": "USD/CAD",
    "USDCAD.C": "USD/CAD",
    "USDCAD.c": "USD/CAD",
    "USDCHF": "USD/CHF",
    "USDCHF.C": "USD/CHF",
    "USDCHF.c": "USD/CHF",
    "NZDUSD": "NZD/USD",
    "NZDUSD.C": "NZD/USD",
    "NZDUSD.c": "NZD/USD",
}

REVERSE_SYMBOL_MAPPING = {v: k for k, v in SYMBOL_MAPPING.items()}


def normalize_symbol_to_mt5(symbol: str) -> str:
    """将 QuantDinger 符号转换为 MT5 终端符号（保留经纪商后缀如 .c）"""
    raw = str(symbol or "").strip()
    if not raw:
        return raw

    symbol_upper = raw.upper()
    if symbol_upper in REVERSE_SYMBOL_MAPPING:
        mt5_symbol = REVERSE_SYMBOL_MAPPING[symbol_upper]
    elif "/" in symbol_upper:
        mt5_symbol = symbol_upper.replace("/", "")
    else:
        mt5_symbol = raw

    # 多数经纪商使用 XAUUSD.c 等形式；可通过 MT5_SYMBOL_SUFFIX 覆盖（设为空则不加）
    suffix = os.getenv("MT5_SYMBOL_SUFFIX", ".c")
    if suffix and "." not in mt5_symbol:
        mt5_symbol = f"{mt5_symbol}{suffix}"
    return mt5_symbol


def _normalize_timeframe_to_mt5(timeframe: str) -> str:
    tf = str(timeframe or "D1").strip()
    return _QD_TO_MT5_TIMEFRAME.get(tf, _QD_TO_MT5_TIMEFRAME.get(tf.upper(), tf))


def _parse_mcp_candles(payload: Any) -> Optional[List[Dict[str, Any]]]:
    """将 Observer get_ohlc_data 返回结构转为 QuantDinger K 线列表。"""
    if payload is None:
        return None
    if isinstance(payload, list):
        candles = payload
    elif isinstance(payload, dict):
        candles = payload.get("candles") or payload.get("klines") or []
    else:
        return None

    if not candles:
        return None

    klines: List[Dict[str, Any]] = []
    for bar in candles:
        if not isinstance(bar, dict):
            continue
        ts = bar.get("time") or bar.get("timestamp")
        if ts is None:
            continue
        try:
            ts_int = int(ts)
        except (TypeError, ValueError):
            continue
        klines.append({
            "time": ts_int,
            "open": float(bar.get("open", 0) or 0),
            "high": float(bar.get("high", 0) or 0),
            "low": float(bar.get("low", 0) or 0),
            "close": float(bar.get("close", 0) or 0),
            "volume": float(bar.get("volume", bar.get("tick_volume", 0)) or 0),
        })
    return klines or None


def _parse_mcp_tick(payload: Any) -> Optional[Dict[str, Any]]:
    """将 Observer get_market_data 返回结构转为 ticker 字段。"""
    if not isinstance(payload, dict):
        return None

    tick = payload.get("tick") if isinstance(payload.get("tick"), dict) else payload
    if not isinstance(tick, dict):
        return None

    last = tick.get("last") or tick.get("price")
    if not last:
        bid = float(tick.get("bid", 0) or 0)
        ask = float(tick.get("ask", 0) or 0)
        last = (bid + ask) / 2 if bid and ask else bid or ask
    try:
        last_f = float(last or 0)
    except (TypeError, ValueError):
        return None
    if last_f <= 0:
        return None

    return {
        "last": last_f,
        "change": float(tick.get("change", 0) or 0),
        "changePercent": float(tick.get("changePercent", tick.get("change_pct", 0)) or 0),
        "previousClose": float(tick.get("previousClose", 0) or 0),
    }


def normalize_symbol_to_quantdinger(symbol: str) -> str:
    """将 MT5 符号转换为 QuantDinger 格式"""
    return SYMBOL_MAPPING.get(symbol.upper(), symbol)


def is_mt5_server_available() -> bool:
    """检查是否有在线的 MT5 Desktop 客户端"""
    desktop_health = smart_router.get_desktop_health()
    return len([d for d in desktop_health if d["is_active"]]) > 0


class MT5ServerProvider:
    """MT5 Server 数据提供者 - 使用智能路由"""
    
    def _run_async(self, coro, timeout: int = 15):
        """同步桥接：通过后台事件循环执行异步协程"""
        try:
            loop = get_background_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result(timeout=timeout)
        except Exception as e:
            logger.debug("MT5 async call failed: %s", e)
            return None
    
    def get_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时价格"""
        mt5_symbol = normalize_symbol_to_mt5(symbol)

        result = self._run_async(
            smart_router.fetch_with_fallback(
                tool_name="get_market_data",
                params={"symbol": mt5_symbol, "data_type": "tick"},
                data_type="ticker",
                symbol=symbol
            ),
            timeout=15
        )

        tick = _parse_mcp_tick(result)
        if tick:
            return {
                **tick,
                "symbol": symbol,
                "source": "MT5 Server"
            }
        return None

    def get_kline(self, symbol: str, timeframe: str, limit: int) -> Optional[List[Dict]]:
        """获取 K线数据"""
        mt5_symbol = normalize_symbol_to_mt5(symbol)
        mt5_tf = _normalize_timeframe_to_mt5(timeframe)

        result = self._run_async(
            smart_router.fetch_with_fallback(
                tool_name="get_ohlc_data",
                params={"symbol": mt5_symbol, "timeframe": mt5_tf, "count": limit},
                data_type="klines",
                symbol=symbol
            ),
            timeout=15
        )

        return _parse_mcp_candles(result)

    def get_indicators(self, symbol: str, timeframe: str = "M15") -> Optional[Dict[str, Any]]:
        """获取技术指标（Observer 无此工具，改由 Server 端本地 K 线计算）"""
        klines = self.get_kline(symbol, timeframe, 120)
        if not klines:
            return None
        try:
            from app.services.market_data_collector import get_market_data_collector
            return get_market_data_collector()._calculate_indicators(klines)
        except Exception as e:
            logger.debug("MT5 local indicator calc failed: %s", e)
            return None
    
    def get_market_depth(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取市场深度(DOM)"""
        mt5_symbol = normalize_symbol_to_mt5(symbol)
        
        result = self._run_async(
            smart_router.fetch_with_fallback(
                tool_name="get_market_depth",
                params={"symbol": mt5_symbol},
                data_type="market_depth",
                symbol=symbol
            ),
            timeout=10
        )
        
        if result:
            return result
        return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """获取账户信息"""
        result = self._run_async(
            smart_router.fetch_with_fallback(
                tool_name="get_account_info",
                params={},
                data_type="account_info"
            ),
            timeout=10
        )
        
        if result:
            return result
        return None
    
    def get_positions(self, symbol: str = "") -> Optional[Dict[str, Any]]:
        """获取持仓信息"""
        params = {}
        if symbol:
            params["symbol"] = normalize_symbol_to_mt5(symbol)
        
        result = self._run_async(
            smart_router.fetch_with_fallback(
                tool_name="get_open_positions",
                params=params,
                data_type="positions"
            ),
            timeout=10
        )
        
        if result:
            return result
        return None
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        if is_mt5_server_available():
            desktop_health = smart_router.get_desktop_health()
            active_count = len([d for d in desktop_health if d["is_active"]])
            return {
                "status": "healthy",
                "active_desktops": active_count,
                "total_desktops": len(desktop_health)
            }
        return {"status": "unhealthy", "error": "No active Desktop connections"}


def get_mt5_server_provider() -> MT5ServerProvider:
    """获取 MT5 Server 提供者实例"""
    return MT5ServerProvider()