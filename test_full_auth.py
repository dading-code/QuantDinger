#!/usr/bin/env python3
"""Test full WebSocket authentication flow"""
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

# Load SECRET_KEY
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

print("=" * 70)
print("Full WebSocket Authentication Test")
print("=" * 70)

# Test 1: API Key validation
print("\n[1] Testing API key validation...")
from app.services.api_key_manager import APIKeyService

test_api_key = 'b711e1df464bd180f55efe18835d302dc9156071edc242ff8d3c3aab4aacff69'
user_info = APIKeyService.validate_api_key(test_api_key)

if not user_info:
    print("  ✗ API key validation failed")
    sys.exit(1)

print(f"  ✓ API key validated")
print(f"    User: {user_info['username']}")
print(f"    User ID: {user_info['user_id']}")
print(f"    Credential ID: {user_info.get('credential_id')}")

# Test 2: Broker account validation
print("\n[2] Testing broker account validation...")
from app.services.websocket_signal import WebSocketSignalHub

hub = WebSocketSignalHub()
validation_result = hub._validate_broker_account(
    user_id=user_info['user_id'],
    credential_id=user_info.get('credential_id'),
    broker_account_id='602966'
)

print(f"  ✓ Validation completed")
print(f"    Valid: {validation_result['valid']}")
print(f"    Validated: {validation_result.get('validated')}")
print(f"    Expected Account: {validation_result.get('expected_account')}")
print(f"    Actual Account: {validation_result.get('actual_account')}")

if validation_result['valid']:
    print("  ✓ Broker account validation PASSED!")
else:
    print(f"   Validation failed: {validation_result.get('error')}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ All tests passed!")
print("=" * 70)
print("\n✨ WebSocket connection should now work properly!")
print("   The user can connect with API Key:")
print(f"   {test_api_key}")
print("=" * 70)
