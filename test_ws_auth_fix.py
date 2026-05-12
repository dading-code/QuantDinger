#!/usr/bin/env python3
"""Test WebSocket authentication after fix"""
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

print("=" * 70)
print("Testing WebSocket Authentication Fix")
print("=" * 70)

# Test 1: Import the fixed module
print("\n[1] Testing module import...")
try:
    from app.utils.credential_crypto import decrypt_credential_blob
    print("  ✓ Import successful: app.utils.credential_crypto")
except ImportError as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Test API key validation
print("\n[2] Testing API key validation...")
try:
    from app.services.api_key_manager import APIKeyService
    from app.utils.db import get_db_connection
    
    test_api_key = 'b711e1df464bd180f55efe18835d302dc9156071edc242ff8d3c3aab4aacff69'
    user_info = APIKeyService.validate_api_key(test_api_key)
    
    if user_info:
        print(f"  ✓ API key validation successful")
        print(f"    User ID: {user_info['user_id']}")
        print(f"    Username: {user_info['username']}")
        print(f"    Credential ID: {user_info.get('credential_id')}")
    else:
        print("  ✗ API key validation returned None")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ API key validation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Test credential decryption
print("\n[3] Testing credential decryption...")
try:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT encrypted_config
            FROM qd_exchange_credentials
            WHERE id = 1
        """)
        result = cur.fetchone()
        cur.close()
        
        if result and result['encrypted_config']:
            decrypted = decrypt_credential_blob(result['encrypted_config'])
            config = json.loads(decrypted)
            print(f"  ✓ Credential decryption successful")
            print(f"    Config keys: {list(config.keys())}")
            
            # Check for MT5 login
            mt5_login = config.get('mt5_login', 'N/A')
            print(f"    MT5 Login: {mt5_login}")
        else:
            print("   No credential found")
except Exception as e:
    print(f"  ✗ Credential decryption failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test broker account validation
print("\n[4] Testing broker account validation...")
try:
    from app.services.websocket_signal import WebSocketSignalHub
    
    hub = WebSocketSignalHub()
    result = hub._validate_broker_account(
        user_id=user_info['user_id'],
        credential_id=user_info.get('credential_id'),
        broker_account_id='602966'
    )
    
    print(f"  ✓ Broker account validation completed")
    print(f"    Valid: {result['valid']}")
    print(f"    Validated: {result.get('validated')}")
    print(f"    Expected: {result.get('expected_account')}")
    print(f"    Actual: {result.get('actual_account')}")
    
    if result['valid']:
        print("  ✓ Validation PASSED - WebSocket connection should work!")
    else:
        print(f"  ✗ Validation FAILED: {result.get('error')}")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Broker account validation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ All tests passed! WebSocket authentication should work now.")
print("=" * 70)
