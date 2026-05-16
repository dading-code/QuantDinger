"""
数据源模块自定义异常
"""


class UnsupportedMarketError(Exception):
    """不支持的市场类型异常"""

    def __init__(self, market: str, message: str = None):
        self.market = market
        self.message = message or f"Unsupported market type: {market}"
        super().__init__(self.message)


class DataSourceError(Exception):
    """数据源通用错误"""

    def __init__(self, message: str, source: str = None):
        self.source = source
        self.message = message
        super().__init__(self.message)


class RateLimitError(Exception):
    """请求频率限制错误"""

    def __init__(self, message: str = "Rate limit exceeded"):
        self.message = message
        super().__init__(self.message)


class CircuitBreakerOpenError(Exception):
    """熔断器开启错误"""

    def __init__(self, message: str = "Circuit breaker is open"):
        self.message = message
        super().__init__(self.message)
