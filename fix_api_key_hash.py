#!/usr/bin/env python3
"""Fix API key - store hash instead of plaintext"""
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
print("Fixing API Key Storage")
print("=" * 70)

# The plaintext API key that user has
plaintext_key = 'b711e1df464bd180f55efe18835d302dc9156071edc242ff8d3c3aab4aacff69'

# Calculate hash
api_key_hash = hashlib.sha256(plaintext_key.encode()).hexdigest()

print(f"\nPlaintext API Key: {plaintext_key[:20]}...")
print(f"SHA256 Hash:       {api_key_hash[:20]}...")

from app.utils.db import get_db_connection

with get_db_connection() as conn:
    cur = conn.cursor()
    
    print("\n[1] Current state:")
    cur.execute("SELECT api_key FROM qd_api_keys WHERE id = 5")
    current = cur.fetchone()
    print(f"  Stored: {current['api_key'][:20]}...")
    
    print("\n[2] Updating to hashed value...")
    cur.execute("""
        UPDATE qd_api_keys
        SET api_key = %s
        WHERE id = 5
    """, (api_key_hash,))
    conn.commit()
    
    print("\n[3] Verifying update:")
    cur.execute("SELECT api_key FROM qd_api_keys WHERE id = 5")
    updated = cur.fetchone()
    print(f"  New:    {updated['api_key'][:20]}...")
    
    if updated['api_key'] == api_key_hash:
        print("  ✓ Update successful!")
    else:
        print("  ✗ Update failed!")
        sys.exit(1)
    
    cur.close()

print("\n[4] Testing validation:")
from app.services.api_key_manager import APIKeyService

user_info = APIKeyService.validate_api_key(plaintext_key)
if user_info:
    print(f"  ✓ Validation successful!")
    print(f"    User: {user_info['username']}")
    print(f"    User ID: {user_info['user_id']}")
    print(f"    Credential ID: {user_info.get('credential_id')}")
else:
    print("  ✗ Validation still failed!")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ API Key fix completed!")
print("=" * 70)
print("\nNow the user can use the SAME API key in local client:")
print(f"  {plaintext_key}")
print("=" * 70)
