#!/bin/bash
cd /opt/quantdinger/QuantDinger/backend_api_python
source .venv/bin/activate

python3 << 'EOF'
import sys
sys.path.insert(0, '/opt/quantdinger/QuantDinger/backend_api_python')

from app.services.api_key_manager import APIKeyService

# Create a new API key for admin user (user_id=1)
result = APIKeyService.create_api_key(
    user_id=1,
    key_name='TestLocalClient',
    description='API key for testing local trade executor',
    expires_days=365
)

print("=" * 80)
print("NEW API KEY CREATED")
print("=" * 80)
print(f"API Key: {result['api_key']}")
print(f"Key Info:")
print(f"  ID: {result['key_info']['id']}")
print(f"  Name: {result['key_info']['key_name']}")
print(f"  Description: {result['key_info']['description']}")
print(f"  Active: {result['key_info']['active']}")
print(f"  Expires: {result['key_info']['expires_at']}")
print("=" * 80)
print("\nIMPORTANT: Save this API key! It will only be shown once.")
print("=" * 80)
EOF
