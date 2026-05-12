#!/usr/bin/env python3
"""Check running strategies and WebSocket status"""
import os
import sys

# Set DATABASE_URL from environment or .env file
if not os.getenv('DATABASE_URL'):
    try:
        with open('/app/.env', 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                    break
    except:
        pass

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Count total strategies
        cur.execute("SELECT COUNT(*) as count FROM qd_strategies_trading")
        count = cur.fetchone()["count"]
        print(f"Total strategies in DB: {count}")
        
        # Get running strategies
        cur.execute("""
            SELECT id, user_id, strategy_name, status, execution_mode, symbol, timeframe
            FROM qd_strategies_trading 
            WHERE status = 'running'
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        running = cur.fetchall()
        print(f"\nRunning strategies ({len(running)}):")
        for s in running:
            sid = s["id"]
            uid = s["user_id"]
            name = s["strategy_name"]
            status = s["status"]
            mode = s["execution_mode"]
            sym = s["symbol"]
            tf = s["timeframe"]
            print(f"  ID:{sid} User:{uid} | {name} | {status} | {mode} | {sym} {tf}")
        
        # Check recent notifications (signals)
        cur.execute("""
            SELECT COUNT(*) as count FROM qd_strategy_notifications
        """)
        notif_count = cur.fetchone()["count"]
        print(f"\nTotal signal notifications: {notif_count}")
        
        # Get recent 5 notifications
        cur.execute("""
            SELECT strategy_id, symbol, signal_type, title, created_at 
            FROM qd_strategy_notifications 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_notifs = cur.fetchall()
        print("\nRecent 5 signal notifications:")
        for n in recent_notifs:
            sid = n["strategy_id"]
            sym = n["symbol"]
            sig = n["signal_type"]
            title = n["title"]
            crt = n["created_at"]
            print(f"  Strategy {sid}: {sym} {sig} - {title} at {crt}")
        
        cur.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
