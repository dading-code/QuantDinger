#!/usr/bin/env python3
"""Check API Key and Credentials Data"""
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

print("=" * 70)
print("Database Check - API Keys & Credentials")
print("=" * 70)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    print("\n[1] qd_exchange_credentials (交易所凭证):")
    cur.execute("SELECT id, name, exchange_id, api_key_hint FROM qd_exchange_credentials WHERE user_id=1 ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(f"  ID={r['id']}, Name='{r['name']}', Exchange={r['exchange_id']}, Hint='{r['api_key_hint']}'")
    
    print("\n[2] qd_api_keys (API密钥):")
    cur.execute("SELECT id, key_name, credential_id, active, (api_key IS NOT NULL) as has_api_key FROM qd_api_keys WHERE user_id=1 ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    for r in rows:
        print(f"  ID={r['id']}, Name='{r['key_name']}', CredID={r['credential_id']}, Active={r['active']}, HasKey={r['has_api_key']}")
    
    cur.close()

print("\n" + "=" * 70)
