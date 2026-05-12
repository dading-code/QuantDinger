#!/usr/bin/env python3
"""Bind API key to exchange credential to fix WebSocket auth"""
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
        print("Fix: Bind API Key to Exchange Credential")
        print("=" * 70)
        
        # Get the first active API key
        cur.execute("""
            SELECT id, key_name, api_key, credential_id
            FROM qd_api_keys
            WHERE user_id = 1 AND active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        api_key = cur.fetchone()
        
        if not api_key:
            print("❌ No active API keys found!")
            sys.exit(1)
        
        print(f"\n📌 API Key to bind:")
        print(f"  ID: {api_key['id']}")
        print(f"  Name: {api_key['key_name']}")
        print(f"  Key: {api_key['api_key'][:12]}...")
        print(f"  Current Credential ID: {api_key['credential_id']}")
        
        # Get the MT5 credential
        cur.execute("""
            SELECT id, exchange_id, name, api_key_hint
            FROM qd_exchange_credentials
            WHERE user_id = 1 AND exchange_id = 'mt5'
            ORDER BY id ASC
            LIMIT 1
        """)
        credential = cur.fetchone()
        
        if not credential:
            print(" No MT5 credential found!")
            sys.exit(1)
        
        print(f"\n📌 MT5 Credential:")
        print(f"  ID: {credential['id']}")
        print(f"  Exchange: {credential['exchange_id']}")
        print(f"  Name: {credential['name']}")
        print(f"  API Key Hint: {credential['api_key_hint']}")
        
        # Bind them
        print(f"\n🔧 Binding API Key {api_key['id']} to Credential {credential['id']}...")
        
        cur.execute("""
            UPDATE qd_api_keys
            SET credential_id = %s, updated_at = NOW()
            WHERE id = %s
        """, (credential['id'], api_key['id']))
        
        conn.commit()
        
        print("✅ API Key bound successfully!")
        
        # Verify
        cur.execute("""
            SELECT ak.id, ak.key_name, ak.credential_id, ec.exchange_id, ec.api_key_hint
            FROM qd_api_keys ak
            LEFT JOIN qd_exchange_credentials ec ON ec.id = ak.credential_id
            WHERE ak.id = %s
        """, (api_key['id'],))
        
        result = cur.fetchone()
        print(f"\n✅ Verification:")
        print(f"  API Key ID: {result['id']}")
        print(f"  Name: {result['key_name']}")
        print(f"  Credential ID: {result['credential_id']}")
        print(f"  Exchange: {result['exchange_id']}")
        print(f"  Account: {result['api_key_hint']}")
        
        print("\n" + "=" * 70)
        print("💡 NEXT STEPS:")
        print("=" * 70)
        print("""
✅ API Key is now bound to MT5 credential!

Now you need to:
1. Use this API Key in your local client:
   API Key: {}
   
2. Restart your local client
3. The WebSocket connection should now succeed!
4. Go to Web UI and START the strategy (ID: 10)
5. You should start receiving trading signals

The bound account is: {}
This should match the broker_account_id your client sends (602966)
""".format(result['api_key'][:20] + '...', result['api_key_hint']))
        
        cur.close()
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
