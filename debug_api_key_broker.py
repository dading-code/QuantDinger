#!/usr/bin/env python3
"""Debug API key and broker account matching"""
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

try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print("=" * 70)
        print("API Key & Broker Account Debug")
        print("=" * 70)
        
        # Get all API keys for user 1
        cur.execute("""
            SELECT id, key_name, api_key, credential_id, active, created_at
            FROM qd_api_keys
            WHERE user_id = 1 AND active = TRUE
            ORDER BY created_at DESC
        """)
        api_keys = cur.fetchall()
        
        print(f"\n📌 User 1 Active API Keys ({len(api_keys)}):")
        for ak in api_keys:
            ak_id = ak["id"]
            ak_name = ak["key_name"]
            ak_key = ak["api_key"]
            cred_id = ak["credential_id"]
            
            # Show first 12 chars of API key for verification
            key_display = ak_key[:12] + "..." if ak_key else "N/A"
            print(f"\n  API Key ID: {ak_id}")
            print(f"    Name: {ak_name}")
            print(f"    Key: {key_display}")
            print(f"    Credential ID: {cred_id}")
            
            if cred_id:
                # Get exchange credential details
                cur.execute("""
                    SELECT id, exchange_id, name, api_key_hint
                    FROM qd_exchange_credentials
                    WHERE id = %s
                """, (cred_id,))
                cred = cur.fetchone()
                if cred:
                    print(f"    Exchange: {cred['exchange_id']} - {cred['name']}")
                    print(f"    API Key Hint: {cred['api_key_hint']}")
                    
                    # Check if encrypted config contains broker account
                    cur.execute("""
                        SELECT encrypted_config
                        FROM qd_exchange_credentials
                        WHERE id = %s
                    """, (cred_id,))
                    enc_row = cur.fetchone()
                    if enc_row and enc_row["encrypted_config"]:
                        enc_conf = enc_row["encrypted_config"]
                        # Try to find account number in encrypted config
                        if "602966" in enc_conf or "6029" in enc_conf:
                            print(f"    ⚠️  Encrypted config contains '602966' pattern")
                        print(f"    Config length: {len(enc_conf)} chars")
                else:
                    print(f"    ⚠️  Credential ID {cred_id} not found!")
            else:
                print(f"    ⚠️  No credential bound!")
        
        # Check the exchange credentials directly
        print("\n" + "=" * 70)
        print("Exchange Credentials:")
        print("=" * 70)
        
        cur.execute("""
            SELECT id, user_id, exchange_id, name, api_key_hint
            FROM qd_exchange_credentials
            WHERE user_id = 1
            ORDER BY id DESC
        """)
        creds = cur.fetchall()
        
        for c in creds:
            print(f"\n  Credential ID: {c['id']}")
            print(f"    Exchange: {c['exchange_id']}")
            print(f"    Name: {c['name']}")
            print(f"    API Key Hint: {c['api_key_hint']}")
        
        print("\n" + "=" * 70)
        print("💡 DIAGNOSIS:")
        print("=" * 70)
        print("""
The WebSocket connection is being rejected because:
1. Client sends broker_account_id = '602966' (MT5 account number)
2. But the API key validation checks if this matches the bound credential
3. If there's a mismatch, connection is closed with code 4002

Possible issues:
- API key is not bound to any credential (credential_id = NULL)
- Credential's encrypted_config doesn't contain account '602966'
- The broker_account_id sent by client doesn't match what's in DB

NEXT STEPS:
1. Check your local client config - what broker_account_id is it sending?
2. Verify the API key you're using matches one shown above
3. If credential_id is NULL, you need to bind the API key to an exchange config
""")
        
        cur.close()
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
