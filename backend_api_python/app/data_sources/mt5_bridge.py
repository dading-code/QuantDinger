"""
MT5 Bridge 数据源
从 AI Trading Monitor Server 获取 MT5 实时数据

架构:
MT5 Observer -> WebSocket -> AI_Trading_Monitor_Server -> HTTP API -> QuantDinger
"""
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import time

from app.data_sources.base import BaseDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MT5BridgeDataSource(BaseDataSource):
    """
    MT5 Bridge 数据源
    
    从 AI Trading Monitor Server 的 QuantDinger API 获取 MT5 数据
    """
    
    name = "mt5_bridge"
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 MT5 Bridge 数据源
        
        Args:
            config: 配置字典，包含:
                - server_url: Server API 地址 (默认: http://101.201.67.41:8000)
                - timeout: 请求超时时间 (默认: 10秒)
                - cache_ttl: 缓存时间（秒，默认: 5秒）
        """
        self.config = config or {}
        self.server_url = self.config.get('server_url', 'http://101.201.67.41:8000')
        self.timeout = self.config.get('timeout', 10)
        self.cache_ttl = self.config.get('cache_ttl', 5)
        
        # 缓存
        self._cache = {}
        self._cache_time = {}
        
        logger.info(f"MT5 Bridge DataSource 初始化完成")
        logger.info(f"Server URL: {self.server_url}")
        logger.info(f"Timeout: {self.timeout}s, Cache TTL: {self.cache_ttl}s")
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self._cache:
            cache_time = self._cache_time.get(key, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self._cache[key]
            else:
                # 缓存过期，删除
                del self._cache[key]
                del self._cache_time[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """设置缓存数据"""
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
        """
        获取K线数据
        
        Args:
            symbol: 交易对符号 (如 XAUUSD)
            timeframe: 时间周期 (1m, 5m, 15m, 30m, 1H, 4H, 1D, 1W)
            limit: 数据条数
            before_time: 获取此时间之前的数据（Unix时间戳，秒）
            after_time: 可选，仅保留 time >= after_time 的 K 线
            
        Returns:
            K线数据列表
        """
        try:
            # 检查缓存
            cache_key = f"kline_{symbol}_{timeframe}_{limit}"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                logger.debug(f"使用缓存数据: {cache_key}")
                return cached_data
            
            # 调用 Server API
            url = f"{self.server_url}/api/v1/market/quantdinger/{symbol}"
            
            params = {
                'timeframe': timeframe,
                'limit': limit
            }
            
            if before_time:
                params['before_time'] = before_time
            if after_time:
                params['after_time'] = after_time
            
            logger.info(f"请求 K线数据: {url}, params={params}")
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析响应
            klines = []
            if 'klines' in data and data['klines']:
                for kline_data in data['klines']:
                    kline = self.format_kline(
                        timestamp=kline_data['time'],
                        open_price=kline_data['open'],
                        high=kline_data['high'],
                        low=kline_data['low'],
                        close=kline_data['close'],
                        volume=kline_data.get('volume', 0)
                    )
                    klines.append(kline)
            
            # 应用过滤和限制
            klines = self.filter_and_limit(
                klines, 
                limit, 
                before_time=before_time,
                after_time=after_time
            )
            
            # 缓存结果
            self._set_cache(cache_key, klines)
            
            logger.info(f"成功获取 {len(klines)} 条 K线数据: {symbol} {timeframe}")
            return klines
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求 K线数据失败: {symbol} {timeframe}, 错误: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"处理 K线数据失败: {symbol} {timeframe}, 错误: {str(e)}", exc_info=True)
            return []
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取最新行情数据
        
        Args:
            symbol: 交易对符号
            
        Returns:
            行情数据字典，格式: {'last': float, 'bid': float, 'ask': float, ...}
        """
        try:
            # 检查缓存
            cache_key = f"ticker_{symbol}"
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                return cached_data
            
            # 调用 Server API
            url = f"{self.server_url}/api/v1/market/quantdinger/{symbol}"
            
            logger.info(f"请求行情数据: {url}")
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # 解析响应
            ticker = {
                'last': data.get('price', 0),
                'bid': data.get('bid', data.get('price', 0)),
                'ask': data.get('ask', data.get('price', 0)),
                'timestamp': data.get('timestamp', int(time.time()))
            }
            
            # 添加技术指标
            if 'indicators' in data:
                indicators = data['indicators']
                ticker.update({
                    'rsi': indicators.get('RSI'),
                    'macd': indicators.get('MACD'),
                    'macd_signal': indicators.get('MACD_Signal'),
                    'bollinger_upper': indicators.get('Bollinger_Upper'),
                    'bollinger_lower': indicators.get('Bollinger_Lower'),
                    'atr': indicators.get('ATR'),
                })
            
            # 缓存结果
            self._set_cache(cache_key, ticker)
            
            logger.info(f"成功获取行情数据: {symbol}, price={ticker['last']}")
            return ticker
            
        except requests.exceptions.RequestException as e:
            logger.error(f"请求行情数据失败: {symbol}, 错误: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"处理行情数据失败: {symbol}, 错误: {str(e)}", exc_info=True)
            return {}
    
    def get_batch_klines(
        self,
        symbols: List[str],
        timeframe: str,
        limit: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量获取多个品种的K线数据
        
        Args:
            symbols: 交易对符号列表
            timeframe: 时间周期
            limit: 每个品种的数据条数
            
        Returns:
            字典，key为symbol，value为K线数据列表
        """
        try:
            # 调用批量API
            url = f"{self.server_url}/api/v1/market/quantdinger/batch"
            
            payload = {
                'symbols': symbols,
                'timeframe': timeframe,
                'limit': limit
            }
            
            logger.info(f"批量请求 K线数据: {url}, symbols={symbols}")
            
            response = requests.post(url, json=payload, timeout=self.timeout * len(symbols))
            response.raise_for_status()
            
            data = response.json()
            
            result = {}
            if 'data' in data:
                for symbol, symbol_data in data['data'].items():
                    klines = []
                    if 'klines' in symbol_data and symbol_data['klines']:
                        for kline_data in symbol_data['klines']:
                            kline = self.format_kline(
                                timestamp=kline_data['time'],
                                open_price=kline_data['open'],
                                high=kline_data['high'],
                                low=kline_data['low'],
                                close=kline_data['close'],
                                volume=kline_data.get('volume', 0)
                            )
                            klines.append(kline)
                    result[symbol] = klines
            
            logger.info(f"成功批量获取 {len(result)} 个品种的K线数据")
            return result
            
        except Exception as e:
            logger.error(f"批量获取K线数据失败: {str(e)}", exc_info=True)
            return {}
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            True 如果服务正常，False 否则
        """
        try:
            url = f"{self.server_url}/health"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MT5 Bridge 健康检查失败: {str(e)}")
            return False
