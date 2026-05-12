#!/usr/bin/env python3
"""Quick check - verify API key exists and module import works"""
import os
import sys

# Load DATABASE_URL
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

print("=" * 70)
print("Quick Diagnostic Check")
print("=" * 70)

# Check 1: Import modules
print("\n[1] Module imports...")
try:
    from app.utils.credential_crypto import decrypt_credential_blob
    print("  ✓ credential_crypto imported")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

try:
    from app.services.api_key_manager import APIKeyService
    print("  ✓ api_key_manager imported")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    sys.exit(1)

# Check 2: Query API keys
print("\n[2] Checking API keys in database...")
try:
    from app.utils.db import get_db_connection
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, key_name, LEFT(api_key, 12) as api_key_prefix, credential_id, active
            FROM qd_api_keys
            WHERE user_id = 1
            ORDER BY id
        """)
        keys = cur.fetchall()
        cur.close()
        
        if keys:
            print(f"  Found {len(keys)} API key(s):")
            for key in keys:
                print(f"    ID={key['id']}, Name={key['key_name']}, "
                      f"Key={key['api_key_prefix']}..., "
                      f"Credential={key['credential_id']}, "
                      f"Active={key['active']}")
        else:
            print("  ✗ No API keys found for user 1")
            
except Exception as e:
    print(f"   Database query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check 3: Try to validate API key 5
print("\n[3] Testing API key validation (ID=5)...")
try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT api_key FROM qd_api_keys WHERE id = 5")
        result = cur.fetchone()
        cur.close()
        
        if result:
            api_key = result['api_key']
            print(f"  API Key from DB: {api_key[:20]}...")
            
            user_info = APIKeyService.validate_api_key(api_key)
            
            if user_info:
                print(f"  ✓ Validation successful!")
                print(f"    User ID: {user_info['user_id']}")
                print(f"    Username: {user_info['username']}")
                print(f"    Credential ID: {user_info.get('credential_id')}")
            else:
                print("  ✗ Validation returned None")
                print("  → This means the API key is invalid or inactive")
        else:
            print("  ✗ API Key ID 5 not found")
            
except Exception as e:
    print(f"  ✗ Test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
