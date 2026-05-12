"""
Test WebSocket connection to cloud server
"""
import asyncio
import json
import websockets

async def test_connection():
    """Test WebSocket connection."""
    
    # Configuration
    api_key = "qd_test_key"  # Replace with your actual API key
    cloud_url = "ws://39.105.150.99:8765/ws"
    
    print("=" * 80)
    print("Testing WebSocket Connection to Cloud Server")
    print("=" * 80)
    print(f"Cloud URL: {cloud_url}")
    print(f"API Key: {api_key[:8]}...")
    print("=" * 80)
    
    try:
        print("\n[1/3] Connecting to WebSocket...")
        async with websockets.connect(cloud_url) as websocket:
            print("[1/3] ✓ Connected!")
            
            # Send authentication
            print("\n[2/3] Sending authentication...")
            auth_message = {
                'api_key': api_key,
                'broker_account_id': 'test_account',  # Test account ID
            }
            await websocket.send(json.dumps(auth_message))
            print("[2/3] ✓ Authentication sent")
            
            # Wait for response (timeout 5 seconds)
            print("\n[3/3] Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                
                print("[3/3] ✓ Response received!")
                print(f"\nResponse type: {data.get('type', 'N/A')}")
                
                if data.get('type') == 'connection_established':
                    print("\n✅ SUCCESS! Connection established successfully")
                    print(f"Message: {data.get('message', 'N/A')}")
                    
                    user_info = data.get('user', {})
                    if user_info:
                        print(f"Username: {user_info.get('username', 'N/A')}")
                        print(f"Email: {user_info.get('email', 'N/A')}")
                    
                    broker_validation = data.get('broker_validation', {})
                    if broker_validation:
                        print(f"\nBroker Validation:")
                        print(f"  Valid: {broker_validation.get('valid', 'N/A')}")
                        print(f"  Validated: {broker_validation.get('validated', 'N/A')}")
                        print(f"  Expected Account: {broker_validation.get('expected_account', 'N/A')}")
                        print(f"  Actual Account: {broker_validation.get('actual_account', 'N/A')}")
                        
                elif data.get('type') == 'error':
                    print(f"\n❌ ERROR: {data.get('message', 'Unknown error')}")
                else:
                    print(f"\n⚠️  Unexpected response type: {data.get('type')}")
                    print(f"Full response: {json.dumps(data, indent=2)}")
                    
            except asyncio.TimeoutError:
                print("[3/3] ⚠️  Timeout waiting for response")
                print("This might indicate:")
                print("  - Invalid API key")
                print("  - No active clients for this user")
                print("  - Server is not responding")
    
    except websockets.exceptions.ConnectionClosed as e:
        print(f"\n❌ Connection closed: {e}")
        print("\nPossible reasons:")
        print("  - Invalid API key (code 4001)")
        print("  - Broker account mismatch (code 4002)")
        print("  - Server rejected the connection")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        print("\nPossible reasons:")
        print("  - Server is not running")
        print("  - Network connectivity issue")
        print("  - Wrong URL or port")

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Please replace 'qd_test_key' with your actual API key")
    print("   You can get it from the Web UI: Settings → API Keys\n")
    
    input("Press Enter to continue with test (or Ctrl+C to cancel)...")
    
    asyncio.run(test_connection())
