#!/bin/bash
# 检查数据库API Key和凭证数据

echo "=========================================="
echo "Database Check - API Keys & Credentials"
echo "=========================================="

# Execute Python inside backend container
podman exec backend python3 - <<'EOF'
import os, sys

# Load DATABASE_URL
if not os.getenv('DATABASE_URL'):
    with open('/app/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                break

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    print("\n[1] Exchange Credentials (交易所凭证):")
    cur.execute("SELECT id, user_id, name, exchange_id, api_key_hint, created_at FROM qd_exchange_credentials ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        for row in rows:
            name = row['name'] if row['name'] else '空'
            hint = row['api_key_hint'] if row['api_key_hint'] else '空'
            print(f"  ID={row['id']}, User={row['user_id']}, Name='{name}', Exchange={row['exchange_id']}, Hint='{hint}'")
    else:
        print("  无数据")
    
    print("\n[2] API Keys (API密钥):")
    cur.execute("SELECT id, user_id, key_name, (api_key IS NOT NULL) as has_key, credential_id, active FROM qd_api_keys ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        for row in rows:
            print(f"  ID={row['id']}, User={row['user_id']}, Name='{row['key_name']}', HasKey={row['has_key']}, CredID={row['credential_id']}, Active={row['active']}")
    else:
        print("  无数据")
    
    cur.close()

print("\n==========================================")
EOF
