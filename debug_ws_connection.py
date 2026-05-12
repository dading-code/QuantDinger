#!/usr/bin/env python3
"""Monitor WebSocket connection attempts with detailed logging"""
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

if not os.getenv('SECRET_KEY'):
    try:
        with open('/app/.env', 'r') as f:
            for line in f:
                if line.startswith('SECRET_KEY='):
                    os.environ['SECRET_KEY'] = line.strip().split('=', 1)[1]
                    break
    except:
        pass

sys.path.insert(0, '/app')

from app.services.websocket_signal import WebSocketSignalHub
from app.services.api_key_manager import APIKeyService
import hashlib

print("=" * 70)
print("WebSocket Connection Debug")
print("=" * 70)

# Get all API keys for reference
from app.utils.db import get_db_connection

print("\n[1] All API Keys in Database:")
with get_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT id, key_name, active, credential_id
        FROM qd_api_keys
        WHERE user_id = 1
        ORDER BY id
    """)
    keys = cur.fetchall()
    
    for key in keys:
        print(f"  ID={key['id']}, Name={key['key_name']}, Active={key['active']}, "
              f"Credential={key['credential_id']}")
    cur.close()

# Test each API key
print("\n[2] Testing all API Keys:")
test_keys = [
    'b711e1df464bd180f55efe18835d302dc9156071edc242ff8d3c3aab4aacff69',
    # Add more if needed
]

for api_key in test_keys:
    print(f"\n  Testing: {api_key[:20]}...")
    user_info = APIKeyService.validate_api_key(api_key)
    
    if user_info:
        print(f"    ✓ Valid - User: {user_info['username']}")
        
        # Test broker validation
        hub = WebSocketSignalHub()
        result = hub._validate_broker_account(
            user_id=user_info['user_id'],
            credential_id=user_info.get('credential_id'),
            broker_account_id='602966'
        )
        
        if result['valid']:
            print(f"    ✓ Broker validation PASSED")
        else:
            print(f"    ✗ Broker validation FAILED: {result.get('error')}")
    else:
        print(f"    ✗ Invalid API Key")

print("\n" + "=" * 70)
print("Summary:")
print("=" * 70)
print("If all tests passed above, the server is ready.")
print("The issue might be:")
print("  1. Local client not sending the correct API Key")
print("  2. Broker account ID mismatch (not 602966)")
print("  3. Network/firewall issue")
print("\n👉 Please try connecting again and check the local client logs!")
print("=" * 70)
