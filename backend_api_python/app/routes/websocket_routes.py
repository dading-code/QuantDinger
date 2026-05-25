"""
WebSocket 路由 - 处理 MT5-Quant-Desktop 连接

核心设计：Server 向 Desktop 拉取数据模式
- 移除推送数据处理，只保留 Server 通过 MCP 请求拉取数据
- Desktop 主动连接 Server，Server 通过 WebSocket 发送 MCP 请求获取数据
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
import logging

from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws/v1", tags=["WebSocket"])


@router.websocket("/agent/{account_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    account_id: str,
    token: str = Query(None)
):
    """
    MT5-Quant-Desktop WebSocket 连接端点
    
    连接模式：Server 向 Desktop 拉取数据
    - Desktop 主动连接 Server（解决 NAT 穿透）
    - Server 通过 MCP 请求从 Desktop 获取 MT5 数据
    
    Args:
        account_id: 账户ID
        token: 认证令牌（可选）
    """
    logger.info(f"[WebSocket] 收到连接请求: account_id={account_id}")
    
    # 尝试建立连接（带防重复连接保护）
    success = await ws_manager.connect(websocket, account_id)
    if not success:
        return
    
    # 接受连接
    await websocket.accept()
    logger.info(f"[WebSocket] 连接已建立: account_id={account_id}")
    
    try:
        while True:
            # 接收消息（主要是 MCP 响应和心跳）
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
            # 处理心跳
            if msg_type == "heartbeat":
                ws_manager.update_heartbeat(account_id)
                logger.debug(f"[心跳] account_id={account_id}")
            
            # 处理 MCP 响应（Server 向 Desktop 拉取数据后的响应）
            elif msg_type == "mcp_response":
                request_id = message.get("request_id")
                if request_id:
                    ws_manager.handle_response(request_id, message)
                    logger.debug(f"[MCP响应] request_id={request_id[:12]}")
            
            # 未知消息类型
            else:
                logger.debug(f"[未知消息] type={msg_type}")
                
    except WebSocketDisconnect:
        logger.info(f"[WebSocket断开] account_id={account_id}")
        ws_manager.disconnect(account_id)
        
    except json.JSONDecodeError:
        logger.warning(f"[JSON解析失败] account_id={account_id}")
        ws_manager.disconnect(account_id)
        
    except Exception as e:
        logger.error(f"[WebSocket异常] account_id={account_id}, error={e}")
        ws_manager.disconnect(account_id)