#!/usr/bin/env python3
import os, sys

if not os.getenv('DATABASE_URL'):
    with open('/app/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                break

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

print("=== API Key 检查 ===")
with get_db_connection() as conn:
    cur = conn.cursor()
    
    print("\n[1] API Keys 列表:")
    cur.execute("SELECT id, user_id, key_name, (api_key IS NOT NULL) as has_key, credential_id, active FROM qd_api_keys WHERE user_id=1 ORDER BY id DESC")
    rows = cur.fetchall()
    for r in rows:
        print(f"  ID={r['id']}, Name={r['key_name']}, HasKey={r['has_key']}, CredID={r['credential_id']}, Active={r['active']}")
    
    print("\n[2] 交易所凭证:")
    cur.execute("SELECT id, user_id, name, exchange_id, api_key_hint FROM qd_exchange_credentials WHERE user_id=1 ORDER BY id DESC")
    rows = cur.fetchall()
    for r in rows:
        print(f"  ID={r['id']}, Name={r['name']}, Exchange={r['exchange_id']}, Hint={r['api_key_hint']}")
    
    cur.close()
