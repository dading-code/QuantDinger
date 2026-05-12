import sys
import os
sys.path.insert(0, "/app")

# Set DATABASE_URL if not set
if not os.getenv('DATABASE_URL'):
    # Use container network name for database
    os.environ['DATABASE_URL'] = 'postgresql://quantdinger:quantdinger123@quantdinger-db:5432/quantdinger'

from app.services.api_key_manager import APIKeyService

print("=" * 80)
print("Creating Test API Key...")
print("=" * 80)

result = APIKeyService.create_api_key(
    user_id=1,
    key_name="Test Local Executor",
    description="For testing local trade executor",
    expires_days=365
)

print(f"API Key: {result['api_key']}")
print(f"Key Name: {result['key_info']['key_name']}")
print(f"Created: {result['key_info']['created_at']}")
print("=" * 80)
print("\nIMPORTANT: Save this API key!")
print("=" * 80)
