#!/usr/bin/env python3
"""Check trading signals in database"""
import sys
sys.path.insert(0, '/app')

from app.utils.db import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # Count total signals
    cur.execute("SELECT COUNT(*) as count FROM qd_trading_signals")
    count = cur.fetchone()['count']
    print(f'Total signals in DB: {count}')
    
    # Get recent 5 signals
    cur.execute("""
        SELECT symbol, action, price, created_at 
        FROM qd_trading_signals 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    recent = cur.fetchall()
    print('\nRecent 5 signals:')
    for s in recent:
        print(f'  {s["symbol"]}: {s["action"]} @ {s["price"]} at {s["created_at"]}')
    
    cur.close()
