"""
MT5 Observer 数据源（WebSocket MCP 拉取）

架构:
  QuantDinger --[mcp_request]--> WebSocket:8765 --> MT5 Observer --[MCP工具]--> MT5 终端

QuantDinger 仅通过 WebSocket 向本地 Observer 发起 MCP 拉取请求，
不依赖任何远程 Server HTTP API。
"""
from typing import Dict, List, Any, Optional
import time

from app.data_sources.base import BaseDataSource
from app.data_providers.mt5_server import get_mt5_server_provider
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MT5BridgeDataSource(BaseDataSource):
    """通过本地 Observer WebSocket MCP 获取 MT5 行情/K线。"""

    name = "mt5_observer_ws"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.cache_ttl = self.config.get("cache_ttl", 5)
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, float] = {}
        self._provider = get_mt5_server_provider()
        logger.info("MT5 Observer WebSocket MCP data source initialized (pull-only)")

    def _get_cached(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        if time.time() - self._cache_time.get(key, 0) >= self.cache_ttl:
            self._cache.pop(key, None)
            self._cache_time.pop(key, None)
            return None
        return self._cache[key]

    def _set_cache(self, key: str, data: Any) -> None:
        self._cache[key] = data
        self._cache_time[key] = time.time()

    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None,
        after_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        cache_key = f"kline_{symbol}_{timeframe}_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        klines = self._provider.get_kline(symbol, timeframe, limit) or []
        if klines:
            klines = self.filter_and_limit(
                klines,
                limit,
                before_time=before_time,
                after_time=after_time,
            )
            self._set_cache(cache_key, klines)
            logger.info("[Observer MCP] kline ok %s %s (%d bars)", symbol, timeframe, len(klines))
        else:
            logger.warning("[Observer MCP] kline empty %s %s", symbol, timeframe)
        return klines

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        cache_key = f"ticker_{symbol}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        result = self._provider.get_price(symbol)
        if result and result.get("last", 0) > 0:
            ticker = {
                "last": result.get("last", 0),
                "bid": result.get("bid", result.get("last", 0)),
                "ask": result.get("ask", result.get("last", 0)),
                "change": result.get("change", 0),
                "changePercent": result.get("changePercent", 0),
                "previousClose": result.get("previousClose", 0),
                "symbol": symbol,
                "source": "MT5 Observer MCP",
            }
            self._set_cache(cache_key, ticker)
            logger.info("[Observer MCP] ticker ok %s price=%s", symbol, ticker["last"])
            return ticker

        logger.warning("[Observer MCP] ticker failed %s", symbol)
        return {"last": 0, "symbol": symbol}

    def get_batch_klines(
        self,
        symbols: List[str],
        timeframe: str,
        limit: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return {symbol: self.get_kline(symbol, timeframe, limit) for symbol in symbols}

    def health_check(self) -> bool:
        try:
            from app.data_providers.mt5_server import is_mt5_server_available
            return is_mt5_server_available()
        except Exception as e:
            logger.error("MT5 Observer health check failed: %s", e)
            return False
