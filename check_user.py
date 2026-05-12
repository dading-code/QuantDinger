#!/usr/bin/env python3
from app.utils.db import get_db_connection

with get_db_connection() as db:
    cur = db.cursor()
    
    # 查询用户
    cur.execute('SELECT id, username FROM qd_users LIMIT 1')
    row = cur.fetchone()
    
    if row:
        print(f"User: {row['username']}, ID: {row['id']}")
    else:
        print("No users found")
    
    cur.close()
