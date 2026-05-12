#!/usr/bin/env python3
"""
WebSocket Connection Test Script
Tests the WebSocket connection to QuantDinger Cloud server.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError
except ImportError:
    print("❌ websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


async def test_websocket_connection():
    """Test WebSocket connection and authentication."""
    
    # Configuration
    ws_url = "ws://39.105.150.99:8888/ws"
    api_key = "test_api_key_12345"  # Use a test key
    
    print("=" * 60)
    print("WebSocket Connection Test")
    print("=" * 60)
    print(f"Target URL: {ws_url}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    try:
        print("[1/4] Attempting to connect...")
        async with websockets.connect(ws_url) as websocket:
            print("✓ [1/4] TCP connection established")
            
            # Send authentication
            print("[2/4] Sending authentication...")
            auth_message = {
                'api_key': api_key,
                'client_type': 'test_client',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            await websocket.send(json.dumps(auth_message))
            print("✓ [2/4] Authentication message sent")
            
            # Wait for response
            print("[3/4] Waiting for server response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(response)
                
                msg_type = data.get('type', 'unknown')
                if msg_type == 'connection_established':
                    print("✓ [3/4] Authentication successful!")
                    print(f"    Client ID: {data.get('client_id', 'N/A')}")
                    
                    # Send a test ping
                    print("[4/4] Testing bidirectional communication...")
                    await websocket.send(json.dumps({'type': 'ping'}))
                    pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    pong_data = json.loads(pong_response)
                    
                    if pong_data.get('type') == 'pong':
                        print("✓ [4/4] Ping-Pong test passed!")
                        print()
                        print("=" * 60)
                        print("✅ ALL TESTS PASSED - WebSocket is working correctly!")
                        print("=" * 60)
                        return True
                    else:
                        print(f"⚠️ Unexpected pong response: {pong_data}")
                        return False
                        
                elif msg_type == 'error':
                    print(f"❌ [3/4] Authentication failed: {data.get('message', 'Unknown error')}")
                    return False
                else:
                    print(f"⚠️ [3/4] Unexpected response type: {msg_type}")
                    print(f"    Response: {data}")
                    return False
                    
            except asyncio.TimeoutError:
                print("❌ [3/4] Timeout waiting for server response")
                return False
                
    except ConnectionRefusedError as e:
        print(f"❌ Connection refused: {e}")
        print("\nPossible causes:")
        print("  1. Server is not running")
        print("  2. Firewall blocking port 8888")
        print("  3. Nginx not configured for WebSocket")
        return False
        
    except Exception as e:
        print(f"❌ Connection error: {type(e).__name__}: {e}")
        
        # Check if it's an HTTP response instead of WebSocket upgrade
        error_str = str(e)
        if "HTTP 200" in error_str or "HTTP 101" not in error_str:
            print("\n🔍 Diagnosis:")
            print("  Server returned HTTP 200 instead of HTTP 101 (WebSocket Upgrade)")
            print("  This means Nginx is NOT configured for WebSocket proxy!")
            print("\n💡 Solution:")
            print("  Add WebSocket configuration to Nginx:")
            print("  location /ws {")
            print("      proxy_pass http://websocket_server;")
            print("      proxy_http_version 1.1;")
            print("      proxy_set_header Upgrade $http_upgrade;")
            print("      proxy_set_header Connection \"upgrade\";")
            print("  }")
        return False


def main():
    """Main entry point."""
    try:
        result = asyncio.run(test_websocket_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
