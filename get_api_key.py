#!/usr/bin/env python3
"""Get the bound API key"""
import os
import sys

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

with get_db_connection() as conn:
    cur = conn.cursor()
    
    cur.execute("""
        SELECT ak.api_key, ak.key_name, ec.api_key_hint
        FROM qd_api_keys ak
        LEFT JOIN qd_exchange_credentials ec ON ec.id = ak.credential_id
        WHERE ak.id = 5
    """)
    
    result = cur.fetchone()
    
    print("=" * 70)
    print("✅ YOUR API KEY (Copy this!)")
    print("=" * 70)
    print()
    print(f"API Key: {result['api_key']}")
    print()
    print(f"Name: {result['key_name']}")
    print(f"Bound to: {result['api_key_hint']}")
    print()
    print("=" * 70)
    print("️  IMPORTANT: Copy this API Key and paste it in your local client!")
    print("=" * 70)
    
    cur.close()
