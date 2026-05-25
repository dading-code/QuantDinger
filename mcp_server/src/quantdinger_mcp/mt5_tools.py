"""
MT5 MCP Tools - 移植自 AI_Trading_Monitor_MT5_Observer

提供完整的MT5数据采集能力，包括：
- K线数据获取
- 账户信息查询
- 持仓管理
- Tick数据获取
- 市场深度数据
- 交易历史查询
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Lazy import MetaTrader5 to allow other features to work without it installed
mt5 = None

def _ensure_mt5():
    global mt5
    if mt5 is None:
        try:
            import MetaTrader5 as _mt5
            mt5 = _mt5
        except ImportError:
            raise ImportError(
                "MetaTrader5 is not installed. Run: pip install MetaTrader5\n"
                "Note: This library only works on Windows with MT5 terminal installed."
            )
    return mt5

async def async_copy_rates_from_pos(symbol: str, timeframe, start_pos: int, count: int):
    """异步执行 MT5 copy_rates_from_pos，避免阻塞事件循环"""
    _ensure_mt5()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, 
        mt5.copy_rates_from_pos, 
        symbol, 
        timeframe, 
        start_pos, 
        count
    )

async def async_ensure_mt5_initialized(timeout: float = 5.0) -> bool:
    """异步确保 MT5 已初始化（带超时）"""
    _ensure_mt5()
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: mt5.initialize(timeout=int(timeout * 1000))),
            timeout=timeout + 1.0
        )
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning(f"MT5 初始化超时或失败: {e}")
        return False

def get_timeframe_map():
    """获取时间周期映射"""
    _ensure_mt5()
    return {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN": mt5.TIMEFRAME_MN1
    }

# ==================== MCP Tools ====================

async def mt5_get_account_info(params: dict) -> Dict[str, Any]:
    """获取MT5账户信息"""
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        info = mt5.account_info()
        if not info:
            return {"success": False, "error": "Failed to get account info from MT5"}
        
        return {
            "success": True,
            "data": {
                "login": info.login,
                "balance": float(info.balance),
                "equity": float(info.equity),
                "margin": float(info.margin),
                "free_margin": float(info.margin_free),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取账户信息失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_open_positions(params: dict) -> Dict[str, Any]:
    """获取当前所有持仓"""
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        symbol = params.get("symbol", None)
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        position_list = []
        if positions:
            for pos in positions:
                position_list.append({
                    "ticket": int(pos.ticket),
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": float(pos.volume),
                    "price_open": float(pos.price_open),
                    "price_current": float(pos.price_current),
                    "profit": float(pos.profit),
                    "swap": float(pos.swap),
                    "commission": float(pos.commission),
                    "sl": float(pos.sl),
                    "tp": float(pos.tp),
                    "time": datetime.fromtimestamp(pos.time).isoformat() if pos.time else None,
                    "comment": pos.comment
                })
        
        return {
            "success": True,
            "data": {
                "positions": position_list,
                "count": len(position_list),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取持仓失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_ohlc_data(params: dict) -> Dict[str, Any]:
    """获取OHLC K线数据"""
    symbol = params.get("symbol", "XAUUSD.c")
    timeframe_str = params.get("timeframe", "H1")
    count = min(params.get("count", 100), 1000)
    
    tf_map = get_timeframe_map()
    tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_H1)
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        rates = await async_copy_rates_from_pos(symbol, tf, 0, count)
        
        if rates is None or len(rates) == 0:
            return {"success": False, "error": f"No data available for {symbol} on {timeframe_str}"}
        
        candles = []
        for r in rates:
            candles.append({
                "time": int(r[0]),
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "volume": int(r[5])
            })
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "timeframe": timeframe_str,
                "count": len(candles),
                "candles": candles
            }
        }
    except Exception as e:
        logger.error(f"获取OHLC数据失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_market_data(params: dict) -> Dict[str, Any]:
    """获取市场数据（Tick + K线）"""
    symbol = params.get("symbol", "XAUUSD.c")
    timeframe_str = params.get("timeframe", "H1")
    count = params.get("count", 50)
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        tick = mt5.symbol_info_tick(symbol)
        tick_dict = {
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "last": float(tick.last),
            "volume": int(tick.volume),
            "time": int(tick.time)
        } if tick else {}
        
        tf_map = get_timeframe_map()
        tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_H1)
        
        rates = await async_copy_rates_from_pos(symbol, tf, 0, count)
        
        rates_list = [
            {"time": datetime.fromtimestamp(r[0]).isoformat(), "open": r[1], "high": r[2], 
             "low": r[3], "close": r[4], "volume": r[5]}
            for r in (rates or [])
        ]
        
        return {
            "success": True,
            "data": {
                "tick": tick_dict,
                "candles": rates_list,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取市场数据失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_trade_history(params: dict) -> Dict[str, Any]:
    """获取历史成交记录"""
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        days = params.get("days", 7)
        from_date = datetime.now() - timedelta(days=days)
        history = mt5.history_deals_get(from_date, datetime.now())
        
        if history:
            deals = []
            for h in history:
                if h.entry == 1:
                    deals.append({
                        "ticket": h.ticket,
                        "time": datetime.fromtimestamp(h.time).isoformat(),
                        "type": "BUY" if h.type == 0 else "SELL",
                        "symbol": h.symbol,
                        "volume": h.volume,
                        "price_open": getattr(h, "price_open", 0.0),
                        "price_close": getattr(h, "price_close", 0.0),
                        "profit": h.profit,
                        "swap": h.swap,
                        "commission": h.commission,
                        "comment": h.comment
                    })
            
            return {
                "success": True,
                "data": {
                    "count": len(deals),
                    "deals": deals,
                    "period_days": days
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "count": 0,
                    "deals": [],
                    "period_days": days
                }
            }
    except Exception as e:
        logger.error(f"获取交易历史失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_tick_data(params: dict) -> Dict[str, Any]:
    """获取Tick数据"""
    symbol = params.get("symbol", "XAUUSD.c")
    lookback_minutes = params.get("lookback_minutes", 5)
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        from_time = datetime.now() - timedelta(minutes=lookback_minutes)
        ticks = mt5.copy_ticks_from(symbol, from_time, 0, mt5.COPY_TICKS_ALL)
        
        if ticks is None or len(ticks) == 0:
            return {"success": False, "error": f"No tick data available for {symbol}"}
        
        import pandas as pd
        df = pd.DataFrame(ticks)
        
        tick_list = []
        for _, row in df.iterrows():
            tick_list.append({
                "time": int(row['time']),
                "bid": float(row['bid']),
                "ask": float(row['ask']),
                "last": float(row['last']),
                "volume": int(row['volume']),
                "flags": int(row['flags'])
            })
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "count": len(tick_list),
                "ticks": tick_list,
                "lookback_minutes": lookback_minutes
            }
        }
    except Exception as e:
        logger.error(f"获取Tick数据失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_market_depth(params: dict) -> Dict[str, Any]:
    """获取市场深度（DOM）数据"""
    symbol = params.get("symbol", "XAUUSD.c")
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        book = mt5.market_book_get(symbol)
        
        if not book:
            return {
                "success": True,
                "data": {
                    "symbol": symbol,
                    "depth": [],
                    "message": "No market depth data available"
                }
            }
        
        depth_list = []
        for item in book:
            depth_list.append({
                "price": float(item.price),
                "volume": float(item.volume),
                "type": str(item.type)
            })
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "depth": depth_list,
                "count": len(depth_list),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"获取市场深度失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_kronos_history(params: dict) -> Dict[str, Any]:
    """Kronos历史数据采集"""
    symbol = params.get("symbol", "XAUUSD.c")
    days = params.get("days", 7)
    timeframe_str = params.get("timeframe", "M15")
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        tf_map = get_timeframe_map()
        tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_M15)
        date_from = datetime.now() - timedelta(days=days)
        
        rates = mt5.copy_rates_range(symbol, tf, date_from, datetime.now())
        if rates is None or len(rates) == 0:
            return {"success": True, "data": {"samples": []}}
        
        klines = []
        for k in rates:
            klines.append({
                "time": int(k['time']),
                "open": float(k['open']),
                "high": float(k['high']),
                "low": float(k['low']),
                "close": float(k['close']),
                "volume": float(k['tick_volume']),
                "symbol": symbol,
                "timeframe": timeframe_str
            })
        
        return {"success": True, "data": {"samples": klines}}
    except Exception as e:
        logger.error(f"Kronos数据采集失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_symbols(params: dict) -> Dict[str, Any]:
    """获取可用交易品种列表"""
    group = params.get("group", "*")
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        symbols = mt5.symbols_get(group=group)
        if symbols is None:
            return {"success": True, "data": {"symbols": [], "count": 0}}
        
        result = []
        for s in symbols:
            result.append({
                "name": s.name,
                "description": s.description,
                "currency_base": s.currency_base,
                "currency_profit": s.currency_profit,
                "digits": s.digits,
                "point": s.point,
                "volume_min": s.volume_min,
                "volume_max": s.volume_max,
                "volume_step": s.volume_step,
            })
        
        return {
            "success": True,
            "data": {
                "symbols": result,
                "count": len(result)
            }
        }
    except Exception as e:
        logger.error(f"获取品种列表失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_pending_orders(params: dict) -> Dict[str, Any]:
    """获取挂单列表"""
    symbol = params.get("symbol", None)
    
    if not await async_ensure_mt5_initialized():
        return {"success": False, "error": "MT5 initialization failed"}
    
    try:
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()
        
        if orders is None:
            return {"success": True, "data": {"orders": [], "count": 0}}
        
        result = []
        for order in orders:
            order_type_map = {
                mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
                mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
                mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
                mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
            }
            
            result.append({
                "ticket": order.ticket,
                "symbol": order.symbol,
                "type": order_type_map.get(order.type, str(order.type)),
                "volume_initial": order.volume_initial,
                "volume_current": order.volume_current,
                "price_open": order.price_open,
                "sl": order.sl,
                "tp": order.tp,
                "magic": order.magic,
                "comment": order.comment,
                "time_setup": datetime.fromtimestamp(order.time_setup).isoformat(),
            })
        
        return {
            "success": True,
            "data": {
                "orders": result,
                "count": len(result)
            }
        }
    except Exception as e:
        logger.error(f"获取挂单失败: {e}")
        return {"success": False, "error": str(e)}

async def mt5_get_connection_status(params: dict) -> Dict[str, Any]:
    """获取MT5连接状态"""
    try:
        _ensure_mt5()
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        
        return {
            "success": True,
            "data": {
                "connected": terminal_info.connected if terminal_info else False,
                "terminal_running": terminal_info is not None,
                "account_login": account_info.login if account_info else None,
                "account_server": account_info.server if account_info else None,
                "trade_allowed": terminal_info.trade_allowed if terminal_info else False,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}