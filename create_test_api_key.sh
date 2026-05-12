#!/bin/bash
# Create a test API key for user 1

podman exec backend python3 << 'EOF'
from app.services.api_key_manager import APIKeyService

# Create API key for user 1
result = APIKeyService.create_api_key(
    user_id=1,
    key_name="Test Local Client",
    description="API key for testing local trade executor",
    expires_days=365,
    credential_id=None  # Not bound to specific exchange
)

print("=" * 80)
print("API Key Created Successfully!")
print("=" * 80)
print(f"API Key: {result['api_key']}")
print(f"Key Name: {result['key_info']['key_name']}")
print(f"Description: {result['key_info']['description']}")
print(f"Created At: {result['key_info']['created_at']}")
print("=" * 80)
print("\nIMPORTANT: Save this API key! It will only be shown once.")
print("=" * 80)
EOF
