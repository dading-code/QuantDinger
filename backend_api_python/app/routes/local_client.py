"""
Local Client Execution Report API

Allows local clients to report back execution results for MT5/IBKR orders.
"""

from flask import Blueprint, request, jsonify, g
from app.utils.logger import get_logger
from app.utils.db import get_db_connection
import json
import time

logger = get_logger(__name__)

local_client_bp = Blueprint('local_client', __name__)


@local_client_bp.route('/report-execution', methods=['POST'])
def report_execution():
    """
    Local client reports execution result for a pending order.
    
    Request body:
    {
        "api_key": "qd_xxx...",  # For authentication
        "pending_order_id": 123,  # The pending order ID from cloud
        "success": true/false,
        "order_id": "MT5-12345",  # Exchange order ID (if success)
        "filled": 0.1,  # Filled amount
        "price": 1.0800,  # Average fill price
        "error": "error message"  # If failed
    }
    
    Response:
    {
        "code": 1,
        "msg": "ok",
        "data": null
    }
    """
    try:
        data = request.get_json() or {}
        
        # Authenticate via API key
        api_key = data.get('api_key', '').strip()
        if not api_key:
            return jsonify({
                'code': 0,
                'msg': 'API key required',
                'data': None
            }), 400
        
        from app.services.api_key_manager import APIKeyService
        user_info = APIKeyService.validate_api_key(api_key)
        
        if not user_info:
            return jsonify({
                'code': 0,
                'msg': 'Invalid API key',
                'data': None
            }), 401
        
        user_id = user_info['user_id']
        pending_order_id = data.get('pending_order_id')
        
        if not pending_order_id:
            return jsonify({
                'code': 0,
                'msg': 'pending_order_id required',
                'data': None
            }), 400
        
        pending_order_id = int(pending_order_id)
        success = data.get('success', False)
        
        logger.info(
            f"Local client execution report: user={user_id} "
            f"pending_id={pending_order_id} success={success}"
        )
        
        if success:
            # Successful execution
            order_id = str(data.get('order_id') or '')
            filled = float(data.get('filled') or 0.0)
            price = float(data.get('price') or 0.0)
            
            if filled <= 0 or price <= 0:
                return jsonify({
                    'code': 0,
                    'msg': 'filled and price must be > 0 for successful execution',
                    'data': None
                }), 400
            
            # Update pending order status
            _update_pending_order_executed(
                pending_order_id=pending_order_id,
                user_id=user_id,
                exchange_order_id=order_id,
                filled=filled,
                avg_price=price,
            )
            
            logger.info(
                f"Execution reported successfully: pending_id={pending_order_id} "
                f"order_id={order_id} filled={filled} price={price}"
            )
            
            return jsonify({
                'code': 1,
                'msg': 'Execution reported successfully',
                'data': None
            })
        
        else:
            # Failed execution
            error = str(data.get('error') or 'Unknown error')
            
            # Mark pending order as failed
            _update_pending_order_failed(
                pending_order_id=pending_order_id,
                user_id=user_id,
                error=error,
            )
            
            logger.warning(
                f"Execution failed: pending_id={pending_order_id} error={error}"
            )
            
            return jsonify({
                'code': 1,
                'msg': 'Failure reported',
                'data': None
            })
    
    except Exception as e:
        logger.error(f"report_execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'code': 0,
            'msg': str(e),
            'data': None
        }), 500


def _update_pending_order_executed(
    pending_order_id: int,
    user_id: int,
    exchange_order_id: str,
    filled: float,
    avg_price: float,
):
    """
    Update pending order status to 'executed' and record trade.
    
    This is Phase 2 of the two-phase operation.
    """
    with get_db_connection() as db:
        cur = db.cursor()
        
        # Verify ownership and get order details
        cur.execute("""
            SELECT id, strategy_id, symbol, signal_type, amount, price, exchange_id
            FROM qd_pending_orders
            WHERE id = ? AND user_id = ?
        """, (pending_order_id, user_id))
        
        order = cur.fetchone()
        if not order:
            cur.close()
            raise ValueError(f"Pending order {pending_order_id} not found or not owned by user {user_id}")
        
        strategy_id = order['strategy_id']
        symbol = order['symbol']
        signal_type = order['signal_type']
        
        # Update pending order status
        executed_at = int(time.time())
        cur.execute("""
            UPDATE qd_pending_orders
            SET status = 'executed',
                exchange_order_id = ?,
                filled = ?,
                avg_price = ?,
                executed_at = ?,
                updated_at = NOW()
            WHERE id = ?
        """, (exchange_order_id, filled, avg_price, executed_at, pending_order_id))
        
        db.commit()
        cur.close()
    
    # Record trade in qd_trades table
    try:
        from app.services.live_trading.records import record_trade
        record_trade(
            strategy_id=strategy_id,
            symbol=symbol,
            trade_type=signal_type,
            price=avg_price,
            amount=filled,
            commission=0.0,  # MT5/IBKR commission calculation is complex
            commission_ccy="USD",
            profit=None,  # Will be calculated later
        )
        logger.info(f"Trade recorded: strategy={strategy_id} symbol={symbol} type={signal_type}")
    except Exception as e:
        logger.warning(f"Failed to record trade: {e}")
    
    # Update position
    try:
        from app.services.live_trading.records import apply_fill_to_local_position
        profit, pos = apply_fill_to_local_position(
            strategy_id=strategy_id,
            symbol=symbol,
            signal_type=signal_type,
            filled=filled,
            avg_price=avg_price,
        )
        logger.info(f"Position updated: strategy={strategy_id} symbol={symbol} profit={profit}")
    except Exception as e:
        logger.warning(f"Failed to update position: {e}")
    
    # Append strategy log
    try:
        from app.utils.strategy_runtime_logs import append_strategy_log
        append_strategy_log(
            strategy_id, "trade",
            f"Trade executed (local client): {signal_type} {symbol} filled={filled:.6f} @ {avg_price:.6f} order_id={exchange_order_id}"
        )
    except Exception as e:
        logger.warning(f"Failed to append strategy log: {e}")


def _update_pending_order_failed(
    pending_order_id: int,
    user_id: int,
    error: str,
):
    """
    Update pending order status to 'failed'.
    """
    with get_db_connection() as db:
        cur = db.cursor()
        
        # Verify ownership
        cur.execute("""
            SELECT id, strategy_id
            FROM qd_pending_orders
            WHERE id = ? AND user_id = ?
        """, (pending_order_id, user_id))
        
        order = cur.fetchone()
        if not order:
            cur.close()
            raise ValueError(f"Pending order {pending_order_id} not found or not owned by user {user_id}")
        
        strategy_id = order['strategy_id']
        
        # Update status
        cur.execute("""
            UPDATE qd_pending_orders
            SET status = 'failed',
                error_message = ?,
                updated_at = NOW()
            WHERE id = ?
        """, (error, pending_order_id))
        
        db.commit()
        cur.close()
    
    # Append strategy log
    try:
        from app.utils.strategy_runtime_logs import append_strategy_log
        append_strategy_log(
            strategy_id, "error",
            f"Trade failed (local client): {error}"
        )
    except Exception as e:
        logger.warning(f"Failed to append strategy log: {e}")
