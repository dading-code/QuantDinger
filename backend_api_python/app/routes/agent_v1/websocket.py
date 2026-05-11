"""
WebSocket Signal API Routes for Flask

Integrates WebSocket signal broadcasting into the existing Agent Gateway API.
Note: Flask doesn't natively support WebSockets. We use a separate async server.
"""

from flask import Blueprint, jsonify, request
from app.services.websocket_signal import get_signal_hub
from app.utils.logger import get_logger

logger = get_logger(__name__)

websocket_bp = Blueprint("websocket", __name__)


@websocket_bp.route("/stats", methods=["GET"])
def get_websocket_stats():
    """Get WebSocket hub statistics."""
    try:
        hub = get_signal_hub()
        return jsonify({
            "success": True,
            "data": hub.get_stats(),
        }), 200
    except Exception as e:
        logger.error(f"Failed to get WebSocket stats: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@websocket_bp.route("/broadcast/test", methods=["POST"])
def test_broadcast():
    """
    Test broadcast endpoint - sends a test signal to all connected clients.
    
    Useful for testing WebSocket connectivity without running actual strategies.
    
    Query params:
        api_key: str (optional) - API key for authentication
    
    Example:
        curl -X POST "http://localhost:5000/api/agent/v1/ws/broadcast/test?api_key=test-key"
    """
    try:
        import asyncio
        
        hub = get_signal_hub()
        
        test_signal = {
            "strategy_id": 999,
            "strategy_name": "Test Strategy",
            "symbol": "BTC/USDT",
            "signal_type": "open_long",
            "price": 50000.0,
            "stake_amount": 0.05,
            "direction": "long",
            "timestamp": "2024-01-01T00:00:00Z",
            "test_mode": True,
        }
        
        # Run async broadcast in sync context
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(hub.broadcast_signal(test_signal))
        finally:
            loop.close()
        
        return jsonify({
            "success": True,
            "message": "Test signal broadcasted",
            "active_clients": hub.stats['active_connections'],
        }), 200
    
    except Exception as e:
        logger.error(f"Failed to broadcast test signal: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


def register(app):
    """Register WebSocket blueprint."""
    app.register_blueprint(websocket_bp, url_prefix="/api/agent/v1/ws")
    logger.info("WebSocket API routes registered at /api/agent/v1/ws")
