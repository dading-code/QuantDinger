"""
WebSocket Status API Routes

Provides endpoints for checking WebSocket client connection status.
Only for local brokers (MT5, IBKR) that use the local trade client.
"""

from flask import Blueprint, jsonify, g
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

websocket_bp = Blueprint('websocket', __name__)


@websocket_bp.route('/client-status', methods=['GET'])
@login_required
def get_client_status():
    """
    获取当前用户本地客户端的WebSocket连接状态
    
    返回示例：
    {
        "code": 1,
        "msg": "success",
        "data": {
            "total_clients": 1,
            "clients": [
                {
                    "client_id": "uuid-xxx",
                    "username": "trader01",
                    "connected_at": "2024-01-01T00:00:00",
                    "last_heartbeat": "2024-01-01T00:05:00",
                    "ip_address": "1.2.3.4"
                }
            ]
        }
    }
    """
    try:
        user_id = g.user_id
        
        # 获取WebSocket Hub实例
        try:
            from app.services.websocket_signal import WebSocketSignalHub
            hub = WebSocketSignalHub.get_instance()
        except Exception as e:
            logger.warning(f"Failed to get WebSocketSignalHub instance: {e}")
            hub = None
        
        if not hub:
            return jsonify({
                'code': 1,
                'msg': 'success',
                'data': {
                    'total_clients': 0,
                    'clients': []
                }
            })
        
        # 查找该用户的所有客户端连接
        user_clients = []
        for client_id, metadata in hub.client_metadata.items():
            if metadata.get('user_id') == user_id:
                user_clients.append({
                    'client_id': client_id,
                    'username': metadata.get('username'),
                    'email': metadata.get('email'),
                    'connected_at': metadata.get('connected_at'),
                    'last_heartbeat': metadata.get('last_heartbeat'),
                    'ip_address': metadata.get('ip_address')
                })
        
        logger.info(f"User {user_id} has {len(user_clients)} active WebSocket client(s)")
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'total_clients': len(user_clients),
                'clients': user_clients
            }
        })
    except Exception as e:
        logger.error(f"get_client_status failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@websocket_bp.route('/is-connected', methods=['GET'])
@login_required
def is_client_connected():
    """
    简化的连接状态检查（只返回是否连接）
    
    适用于前端快速轮询，减少数据传输量
    
    返回示例：
    {
        "code": 1,
        "data": {
            "connected": true,
            "client_count": 1
        }
    }
    """
    try:
        user_id = g.user_id
        
        # 获取WebSocket Hub实例
        try:
            from app.services.websocket_signal import WebSocketSignalHub
            hub = WebSocketSignalHub.get_instance()
        except Exception as e:
            logger.warning(f"Failed to get WebSocketSignalHub instance: {e}")
            hub = None
        
        if not hub:
            return jsonify({
                'code': 1,
                'data': {
                    'connected': False,
                    'client_count': 0
                }
            })
        
        # 统计该用户的活跃连接数
        connected_count = sum(
            1 for metadata in hub.client_metadata.values()
            if metadata.get('user_id') == user_id
        )
        
        return jsonify({
            'code': 1,
            'data': {
                'connected': connected_count > 0,
                'client_count': connected_count
            }
        })
    except Exception as e:
        logger.error(f"is_client_connected failed: {e}")
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@websocket_bp.route('/clients', methods=['GET'])
@login_required
def list_all_clients():
    """
    列出当前所有WebSocket客户端（仅管理员）
    
    返回示例：
    {
        "code": 1,
        "data": {
            "total": 5,
            "clients": [
                {
                    "client_id": "uuid-1",
                    "user_id": 2,
                    "username": "trader01",
                    "connected_at": "...",
                    "last_heartbeat": "...",
                    "ip_address": "1.2.3.4"
                },
                ...
            ]
        }
    }
    """
    try:
        from app.utils.auth import admin_required
        from functools import wraps
        
        # Check admin permission
        from app.utils.db import get_db_connection
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute("SELECT role FROM qd_users WHERE id = %s", (g.user_id,))
            user = cur.fetchone()
            cur.close()
            
            if not user or user['role'] != 'admin':
                return jsonify({
                    'code': 0,
                    'msg': 'Permission denied: admin only',
                    'data': None
                }), 403
        
        # 获取WebSocket Hub实例
        try:
            from app.services.websocket_signal import WebSocketSignalHub
            hub = WebSocketSignalHub.get_instance()
        except Exception as e:
            logger.warning(f"Failed to get WebSocketSignalHub instance: {e}")
            hub = None
        
        if not hub:
            return jsonify({
                'code': 1,
                'data': {
                    'total': 0,
                    'clients': []
                }
            })
        
        # 获取所有客户端
        all_clients = []
        for client_id, metadata in hub.client_metadata.items():
            all_clients.append({
                'client_id': client_id,
                'user_id': metadata.get('user_id'),
                'username': metadata.get('username'),
                'email': metadata.get('email'),
                'connected_at': metadata.get('connected_at'),
                'last_heartbeat': metadata.get('last_heartbeat'),
                'ip_address': metadata.get('ip_address')
            })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'total': len(all_clients),
                'clients': all_clients
            }
        })
    except Exception as e:
        logger.error(f"list_all_clients failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500
