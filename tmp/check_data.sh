#!/bin/bash
echo "=== 检查数据库 ==="
podman exec backend python3 << 'PYTHON_SCRIPT'
import os
import sys

if not os.getenv('DATABASE_URL'):
    with open('/app/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                break

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

print("=== 交易所凭证 ===")
with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials WHERE user_id=1 ORDER BY id DESC LIMIT 3")
    for r in cur.fetchall():
        print(f"  ID={r['id']}, Name='{r['name']}', Exchange={r['exchange_id']}, Hint='{r['api_key_hint']}'")
    
    print("\n=== API Keys ===")
    cur.execute("SELECT id, key_name, credential_id, active, (api_key IS NOT NULL) as has_key FROM qd_api_keys WHERE user_id=1 ORDER BY id DESC LIMIT 3")
    for r in cur.fetchall():
        print(f"  ID={r['id']}, Name='{r['key_name']}', CredID={r['credential_id']}, Active={r['active']}, HasKey={r['has_key']}")
    
    cur.close()
PYTHON_SCRIPT
