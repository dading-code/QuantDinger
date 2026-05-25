"""
WebSocket 连接管理器 - 管理 MT5-Quant-Desktop 客户端连接

核心设计（拉取模式）：
1. 反向连接模式：Desktop 主动连接 Server（解决 NAT 穿透）
2. 多账户隔离：每个账户只能有一个活跃连接
3. Server 主动拉取：通过 MCP 请求从 Desktop 获取数据
4. 心跳保活：自动清理僵尸连接

参考：AI_Trading_Monitor_Server/core/connection_manager.py
"""
import asyncio
import json
import uuid
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # account_id -> WebSocket（一个账户只能有一个活跃连接）
        self.active_connections: Dict[str, WebSocket] = {}
        # 请求响应映射: request_id -> asyncio.Future
        self.pending_requests: Dict[str, asyncio.Future] = {}
        # 心跳追踪: account_id -> last_heartbeat_time
        self.last_heartbeat: Dict[str, float] = {}
        # 心跳超时时间（180秒）
        self.heartbeat_timeout = 180
        
        self._initialized = True
    
    async def connect(self, websocket: WebSocket, account_id: str) -> bool:
        """建立 WebSocket 连接（带防重复连接保护）"""
        if account_id in self.active_connections:
            last_hb_time = self.last_heartbeat.get(account_id, 0)
            current_time = datetime.now(timezone.utc).timestamp()
            time_since_last_hb = current_time - last_hb_time
            
            if time_since_last_hb > 60:
                logger.warning(f"[清理僵尸连接] Account {account_id} 超过 {time_since_last_hb:.0f}s 无心跳")
                self._cleanup_connection(account_id)
            else:
                await websocket.accept()
                await websocket.send_json({
                    "type": "error",
                    "code": "DUPLICATE_CONNECTION",
                    "message": f"账户 {account_id} 已有活跃连接"
                })
                await websocket.close(code=4001, reason="Duplicate connection")
                return False
        
        self.active_connections[account_id] = websocket
        self.last_heartbeat[account_id] = datetime.now(timezone.utc).timestamp()
        logger.info(f"[连接成功] account_id={account_id}")
        return True
    
    def disconnect(self, account_id: str):
        """断开 WebSocket 连接"""
        if account_id in self.active_connections:
            del self.active_connections[account_id]
        if account_id in self.last_heartbeat:
            del self.last_heartbeat[account_id]
        logger.info(f"[连接断开] account_id={account_id}")
    
    async def send_message(self, message: dict, account_id: str):
        """向指定账户发送消息"""
        if account_id not in self.active_connections:
            raise ConnectionError(f"No active connection for account: {account_id}")
        
        websocket = self.active_connections[account_id]
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"[发送失败] account={account_id}, error={e}")
            self.disconnect(account_id)
            raise
    
    async def request_mcp(self, tool_name: str, params: dict, account_id: str = None, timeout: int = 10) -> Optional[dict]:
        """
        向 Desktop 发送 MCP 请求并等待响应（核心拉取方法）
        
        Args:
            tool_name: MCP 工具名称
            params: 请求参数
            account_id: 目标账户（None 表示随机选择一个在线账户）
            timeout: 超时时间
        
        Returns:
            响应数据或 None
        """
        if not account_id:
            online_account