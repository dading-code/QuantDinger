#!/bin/bash
# Check trading signals in database

DB_URL=$(podman exec backend cat /app/.env | grep DATABASE_URL | cut -d= -f2-)

podman exec -e DATABASE_URL="$DB_URL" backend python3 << 'PYEOF'
import os
from app.utils.db import get_db_connection

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
PYEOF
