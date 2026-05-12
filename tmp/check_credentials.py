#!/usr/bin/env python3
"""检查API Key和凭证数据"""
import os
import sys
import json

if not os.getenv('DATABASE_URL'):
    with open('/app/.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
                break

sys.path.insert(0, '/app')
from app.utils.db import get_db_connection

print("=" * 70)
print("API Key & Credentials Check")
print("=" * 70)

with get_db_connection() as conn:
    cur = conn.cursor()
    
    # 1. Check credentials
    print("\n[1] Exchange Credentials:")
    cur.execute("""
        SELECT id, user_id, name, exchange_id, api_key_hint, created_at
        FROM qd_exchange_credentials
        WHERE user_id = 1
        ORDER BY id DESC
    """)
    creds = cur.fetchall()
    if creds:
        for c in creds:
            print(f"  ID={c['id']}, Name='{c['name']}', Exchange={c['exchange_id']}, Hint='{c['api_key_hint']}'")
    else:
        print("  No credentials found")
    
    # 2. Check API Keys
    print("\n[2] API Keys:")
    cur.execute("""
        SELECT id, user_id, key_name, api_key IS NOT NULL as has_key, 
               credential_id, active, created_at
        FROM qd_api_keys
        WHERE user_id = 1
        ORDER BY id DESC
    """)
    keys = cur.fetchall()
    if keys:
        for k in keys:
            key_preview = (k['api_key'][:20] + '...') if k['api_key'] and len(k.get('api_key', '')) > 20 else (k['api_key'] or 'NULL')
            print(f"  ID={k['id']}, Name='{k['key_name']}', HasKey={k['has_key']}, CredID={k['credential_id']}, Active={k['active']}")
            print(f"    Key={key_preview}")
    else:
        print("  No API Keys found")
    
    cur.close()

print("\n" + "=" * 70)
if not creds:
    print("PROBLEM: No exchange credentials found!")
    print("You need to add a broker account first")
elif not keys:
    print("PROBLEM: No API Keys found!")
    print("You need to generate an API Key")
else:
    print("Data exists, checking bindings...")
