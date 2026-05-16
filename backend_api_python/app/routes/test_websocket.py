"""
临时测试路由 - 用于 WebSocket 信号推送测试
"""
from flask import Blueprint, jsonify, request
from app.services.websocket_signal import get_signal_hub
import asyncio

test_ws_bp = Blueprint('test_websocket', __name__, url_prefix='/api/test')


@test_ws_bp.route('/broadcast-signal', methods=['POST'])
def broadcast_test_signal():
    """
    广播一个测试信号到所有连接的 WebSocket 客户端
    
    POST /api/test/broadcast-signal
    Body: {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "price": 65432.10
    }
    """
    try:
        data = request.get_json() or {}
        
        # 构建测试信号
        signal_data = {
            'strategy_name': data.get('strategy_name', '测试策略 - WebSocket Test'),
            'symbol': data.get('symbol', 'BTCUSDT'),
            'action': data.get('action', 'BUY'),
            'price': float(data.get('price', 65432.10)),
            'quantity': float(data.get('quantity', 0.01)),
            'confidence': float(data.get('confidence', 0.85)),
            'indicators': data.get('indicators', {
                'MA_50': 64500.00,
                'MA_200': 63000.00,
                'RSI': 55.5
            }),
            'message': data.get('message', 'WebSocket 信号推送测试'),
            'timestamp': data.get('timestamp', None)
        }
        
        # 获取 WebSocket Hub
        hub = get_signal_hub()
        
        # 检查是否有连接的客户端
        client_count = len(hub.clients)
        
        if client_count == 0:
            return jsonify({
                'code': 0,
                'msg': 'No connected clients',
                'data': {
                    'connected_clients': client_count,
                    'signal': signal_data
                }
            }), 200
        
        # 广播信号（在同步上下文中调用异步方法）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(hub.broadcast_signal(signal_data))
            success = True
        except Exception as e:
            success = False
            error_msg = str(e)
        finally:
            loop.close()
        
        if success:
            return jsonify({
                'code': 1,
                'msg': f'Signal broadcasted to {client_count} clients',
                'data': {
                    'success': True,
                    'connected_clients': client_count,
                    'signal': signal_data
                }
            })
        else:
            return jsonify({
                'code': 0,
                'msg': f'Broadcast failed: {error_msg}',
                'data': {
                    'success': False,
                    'connected_clients': client_count,
                    'error': error_msg
                }
            }), 500
            
    except Exception as e:
        return jsonify({
            'code': 0,
            'msg': f'Error: {str(e)}',
            'data': None
        }), 500


@test_ws_bp.route('/clients', methods=['GET'])
def list_connected_clients():
    """列出所有已连接的 WebSocket 客户端"""
    try:
        hub = get_signal_hub()
        clients_info = []
        
        for client_id, metadata in hub.client_metadata.items():
            clients_info.append({
                'client_id': client_id,
                'user_id': metadata.get('user_id'),
                'username': metadata.get('username'),
                'connected_at': metadata.get('connected_at')
            })
        
        return jsonify({
            'code': 1,
            'msg': 'Success',
            'data': {
                'total_clients': len(clients_info),
                'clients': clients_info
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 0,
            'msg': f'Error: {str(e)}',
            'data': None
        }), 500
