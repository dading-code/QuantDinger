"""
智能数据路由器 - 分布式 Desktop 数据路由与缓存

核心原则（参考 AI_Trading_Monitor）：
1. 共享数据（按品种）全局缓存，避免重复采集
2. 私有数据（按账户）严格隔离
3. 智能路由：优先选择最近活跃的 Desktop
4. 快速失败：超时立即切换到下一台 Desktop
5. 支持几百个 Desktop 客户端连接

适用场景：
- Server 只有一个，Desktop 有几百个
- 当某个 Desktop 断开时，自动从其他 Desktop 拉取数据
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.services.websocket_signal import get_signal_hub

logger = logging.getLogger(__name__)


class SmartDataRouter:
    """智能数据路由器 - 管理 Desktop 选择和缓存"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 🟢 共享数据缓存（按品种）
        # 结构：{symbol: {data_type: {"data": ..., "timestamp": ..., "ttl": ...}}}
        self.shared_cache: Dict[str, Dict[str, dict]] = {}
        
        # 🔴 私有数据缓存（按账户）
        # 结构：{account_id: {data_type: {"data": ..., "timestamp": ...}}}
        self.private_cache: Dict[str, Dict[str, dict]] = {}
        
        # 默认 TTL（秒）
        self.default_ttl = {
            "klines": 300,           # K线数据 5 分钟
            "ticker": 30,            # 实时价格 30 秒
            "indicators": 60,        # 技术指标 1 分钟
            "market_depth": 10,      # 市场深度 10 秒
            "account_info": 30,      # 账户信息 30 秒
            "positions": 10,         # 持仓信息 10 秒
        }
        
        self._initialized = True
    
    def _get_active_desktops(self) -> List[str]:
        """获取所有在线的 Desktop 账户 ID，按最后心跳时间排序（最近活跃优先）"""
        hub = get_signal_hub()
        return hub.get_online_accounts()
    
    def _is_cache_valid(self, cache_entry: dict, data_type: str) -> bool:
        """检查缓存是否有效"""
        if not cache_entry:
            return False
        
        timestamp = cache_entry.get("timestamp", 0)
        ttl = cache_entry.get("ttl", self.default_ttl.get(data_type, 300))
        
        current_time = datetime.now().timestamp()
        return (current_time - timestamp) < ttl
    
    def get_shared_data(self, symbol: str, data_type: str) -> Optional[dict]:
        """
        获取共享数据（按品种）
        如果缓存有效则直接返回，否则返回 None 触发采集
        """
        if symbol not in self.shared_cache:
            return None
        
        if data_type not in self.shared_cache[symbol]:
            return None
        
        cache_entry = self.shared_cache[symbol][data_type]
        
        if self._is_cache_valid(cache_entry, data_type):
            logger.debug(f"✅ [缓存命中] {symbol}/{data_type}")
            return cache_entry["data"]
        else:
            logger.debug(f"⏰ [缓存过期] {symbol}/{data_type}")
            return None
    
    def set_shared_data(self, symbol: str, data_type: str, data: dict, source_account: str = ""):
        """设置共享数据（按品种）"""
        if symbol not in self.shared_cache:
            self.shared_cache[symbol] = {}
        
        self.shared_cache[symbol][data_type] = {
            "data": data,
            "timestamp": datetime.now().timestamp(),
            "ttl": self.default_ttl.get(data_type, 300),
            "source_account": source_account
        }
        logger.info(f"💾 [缓存更新] {symbol}/{data_type} | 来源={source_account}")
    
    async def fetch_with_fallback(self, tool_name: str, params: dict, data_type: str, symbol: str = "") -> Optional[dict]:
        """
        带降级策略的数据采集（核心方法）
        
        流程：
        1. 检查缓存（仅共享数据）
        2. 获取在线 Desktop 列表
        3. 依次尝试每台 Desktop，失败则切换到下一台
        4. 更新缓存（如果成功）
        
        Args:
            tool_name: MCP 工具名称
            params: 请求参数
            data_type: 数据类型（用于缓存）
            symbol: 交易品种（用于缓存键）
        
        Returns:
            数据或 None
        """
        logger.info(f"🔍 [智能路由] tool_name={tool_name} | symbol={symbol}")
        
        # 步骤 1：检查缓存（仅共享数据）
        if symbol and data_type in ["klines", "ticker", "indicators"]:
            cached_data = self.get_shared_data(symbol, data_type)
            if cached_data is not None:
                logger.info(f"✅ [缓存命中] 直接返回")
                return cached_data
        
        # 步骤 2：获取在线 Desktop 列表
        active_desktops = self._get_active_desktops()
        
        if not active_desktops:
            logger.warning(f"⚠️ [无可用 Desktop] 所有 Desktop 均离线")
            return None
        
        logger.info(f"🎯 [找到 {len(active_desktops)} 台在线 Desktop]")
        
        # 步骤 3：依次尝试每台 Desktop
        hub = get_signal_hub()
        
        for i, account_id in enumerate(active_desktops):
            try:
                logger.info(f"📡 [尝试 {i+1}/{len(active_desktops)}] Desktop={account_id}")
                
                # 发送 MCP 请求
                result = await hub.request_mcp(
                    tool_name=tool_name,
                    params=params,
                    account_id=account_id,
                    timeout=10
                )
                
                if result and result.get("success"):
                    data = result.get("data", {})
                    
                    # 步骤 4：更新缓存
                    if symbol and data_type in ["klines", "ticker", "indicators"]:
                        self.set_shared_data(symbol, data_type, data, source_account=account_id)
                    elif account_id:
                        # 私有数据缓存
                        if account_id not in self.private_cache:
                            self.private_cache[account_id] = {}
                        self.private_cache[account_id][data_type] = {
                            "data": data,
                            "timestamp": datetime.now().timestamp(),
                            "ttl": self.default_ttl.get(data_type, 30)
                        }
                    
                    logger.info(f"✅ [采集成功] Desktop={account_id}")
                    return data
                else:
                    error_msg = result.get("error", "Unknown error") if result else "No response"
                    logger.warning(f"⚠️ [Desktop {account_id} 失败] {error_msg}")
                    
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ [Desktop {account_id} 超时]")
            except Exception as e:
                logger.error(f"❌ [Desktop {account_id} 异常] {e}")
        
        # 所有 Desktop 都失败
        logger.error(f"❌ [采集失败] 所有 {len(active_desktops)} 台 Desktop 均失败")
        return None
    
    def get_desktop_health(self) -> List[dict]:
        """获取所有 Desktop 的健康状态"""
        hub = get_signal_hub()
        desktop_health = []
        current_time = datetime.now().timestamp()
        
        for account_id in hub.get_online_accounts():
            # 从客户端元数据获取心跳时间
            last_heartbeat = 0
            for meta in hub.client_metadata.values():
                if meta.get('broker_account_id') == account_id:
                    last_heartbeat = meta.get('last_heartbeat', 0)
                    break
            
            time_since_heartbeat = current_time - last_heartbeat
            
            # 健康状态判断
            if time_since_heartbeat < 30:
                health_status = "excellent"
            elif time_since_heartbeat < 60:
                health_status = "good"
            elif time_since_heartbeat < 90:
                health_status = "warning"
            else:
                health_status = "critical"
            
            desktop_health.append({
                "account_id": account_id,
                "last_heartbeat": last_heartbeat,
                "time_since_heartbeat": round(time_since_heartbeat, 1),
                "health_status": health_status,
                "is_active": time_since_heartbeat < 90
            })
        
        # 按最后心跳时间降序排序
        desktop_health.sort(key=lambda x: x["last_heartbeat"], reverse=True)
        
        return desktop_health


# 全局单例
smart_router = SmartDataRouter()