#!/usr/bin/env python3
"""Check trading signals in database"""
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
        
        # Count total signals
        cur.execute("SELECT COUNT(*) as count FROM qd_trading_signals")
        count = cur.fetchone()["count"]
        print(f"Total signals in DB: {count}")
        
        # Get recent 5 signals
        cur.execute("""
            SELECT symbol, action, price, created_at 
            FROM qd_trading_signals 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent = cur.fetchall()
        print("\nRecent 5 signals:")
        for s in recent:
            sym = s["symbol"]
            act = s["action"]
            prc = s["price"]
            crt = s["created_at"]
            print(f"  {sym}: {act} @ {prc} at {crt}")
        
        cur.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
