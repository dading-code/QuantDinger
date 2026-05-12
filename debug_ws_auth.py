#!/usr/bin/env python3
"""Debug WebSocket authentication - check why connection is rejected"""
import os
import sys
import json

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
from app.utils.credential_crypto import decrypt_credential_blob

try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print("=" * 70)
        print("WebSocket Authentication Debug")
        print("=" * 70)
        
        # Check API Key
        print("\n[1] Checking API Key:")
        cur.execute("""
            SELECT id, key_name, api_key, credential_id, active
            FROM qd_api_keys
            WHERE api_key = 'b711e1df464bd180f55efe18835d302dc9156071edc242ff8d3c3aab4aacff69'
        """)
        api_key = cur.fetchone()
        
        if not api_key:
            print("  ✗ API Key NOT FOUND in database!")
            sys.exit(1)
        
        print(f"  ✓ API Key ID: {api_key['id']}")
        print(f"  ✓ Name: {api_key['key_name']}")
        print(f"  ✓ Active: {api_key['active']}")
        print(f"  ✓ Credential ID: {api_key['credential_id']}")
        
        if not api_key['credential_id']:
            print("  ✗ ERROR: API Key is NOT bound to any credential!")
            print("  → This is why WebSocket rejects the connection!")
            sys.exit(1)
        
        # Check Credential
        print("\n[2] Checking Exchange Credential:")
        cur.execute("""
            SELECT id, user_id, name, exchange_id, api_key_hint, encrypted_config
            FROM qd_exchange_credentials
            WHERE id = %s
        """, (api_key['credential_id'],))
        credential = cur.fetchone()
        
        if not credential:
            print(f"  ✗ Credential ID {api_key['credential_id']} NOT FOUND!")
            sys.exit(1)
        
        print(f"  ✓ Credential ID: {credential['id']}")
        print(f"  ✓ Exchange: {credential['exchange_id']}")
        print(f"  ✓ Name: {credential['name']}")
        print(f"  ✓ Account Hint: {credential['api_key_hint']}")
        
        # Decrypt and check account
        print("\n[3] Checking Account Match:")
        try:
            decrypted = decrypt_credential_blob(credential['encrypted_config'])
            config = json.loads(decrypted)
            print(f"  ✓ Decrypted config: {json.dumps(config, indent=2)}")
            
            # Check if it contains the broker account ID
            account_id = config.get('account', config.get('login', config.get('account_id', 'N/A')))
            print(f"\n  → Expected broker_account_id from client: 602966")
            print(f"  → Account in credential config: {account_id}")
            
            if str(account_id) == "602966":
                print("  ✓ Account MATCHES!")
            else:
                print("  ✗ Account MISMATCH!")
                print("  → This will cause WebSocket to reject the connection!")
        except Exception as e:
            print(f"  ✗ Failed to decrypt: {e}")
        
        print("\n" + "=" * 70)
        print("Summary:")
        print("=" * 70)
        print(f"API Key: {'✓ Valid' if api_key['active'] else '✗ Inactive'}")
        print(f"Binding: {'✓ Bound' if api_key['credential_id'] else '✗ NOT BOUND'}")
        print(f"Exchange: {credential['exchange_id']}")
        print(f"Account: {credential['api_key_hint']}")
        
        cur.close()

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
