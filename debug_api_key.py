#!/usr/bin/env python3
"""Debug API key - check what's actually stored"""
import os
import sys
import hashlib

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
print("API Key Debug")
print("=" * 70)

# Test API key from user
test_key = 'b711e1df464bd180f55efe18835d302dc9156071edc242ff8d3c3aab4aacff69'
print(f"\nTest API Key: {test_key[:20]}...")
print(f"Length: {len(test_key)}")

# Check if it starts with qd_ (the expected format)
print(f"Starts with 'qd_': {test_key.startswith('qd_')}")

# Hash it
api_key_hash = hashlib.sha256(test_key.encode()).hexdigest()
print(f"\nHashed value: {api_key_hash[:20]}...")

# Query database
from app.utils.db import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    print("\n[1] Checking qd_api_keys table:")
    cur.execute("""
        SELECT id, key_name, api_key, LEFT(api_key, 20) as prefix, LENGTH(api_key) as key_length
        FROM qd_api_keys
        WHERE id = 5
    """)
    result = cur.fetchone()
    
    if result:
        print(f"  ID: {result['id']}")
        print(f"  Name: {result['key_name']}")
        print(f"  Stored Key: {result['prefix']}...")
        print(f"  Key Length: {result['key_length']}")
        
        # Check if the stored key matches our test key or its hash
        stored_key = result['api_key']
        test_key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        
        if stored_key == test_key:
            print("  ✓ Stored key MATCHES the test key directly")
            print("  → Database stores PLAINTEXT (should be hashed!)")
        elif stored_key == test_key_hash:
            print("  ✓ Stored key MATCHES the hashed test key")
            print("  → Database stores HASH (correct!)")
        else:
            print("  ✗ No match")
            print(f"    Stored: {stored_key[:20]}...")
            print(f"    Test:   {test_key[:20]}...")
            print(f"    Hashed: {test_key_hash[:20]}...")
    else:
        print("  ✗ API Key ID 5 not found")
    
    print("\n[2] Trying validation with test key:")
    from app.services.api_key_manager import APIKeyService
    
    user_info = APIKeyService.validate_api_key(test_key)
    if user_info:
        print(f"  ✓ Validation successful")
        print(f"    User: {user_info['username']}")
    else:
        print("  ✗ Validation failed")
    
    cur.close()

print("\n" + "=" * 70)
