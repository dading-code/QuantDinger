#!/usr/bin/env python3
"""Debug WebSocket connection with detailed logging."""

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


async def debug_websocket():
    """Debug WebSocket connection step by step."""
    
    ws_url = "ws://39.105.150.99:8888/ws"
    # 使用用户实际配置的 API Key（从截图看到有值，但被隐藏了）
    # 这里先尝试连接，看服务器的响应
    api_key = "your_actual_api_key_here"  # 替换为实际的 API Key
    
    print("=" * 70)
    print("WebSocket Debug Script")
    print("=" * 70)
    print(f"Target: {ws_url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    try:
        print("[Step 1] Connecting to WebSocket server...")
        websocket = await websockets.connect(ws_url)
        print("✓ TCP connection established")
        print(f"  WebSocket object: {websocket}")
        print(f"  WebSocket URI: {websocket.remote_address}")
        print()
        
        print("[Step 2] Sending authentication message...")
        auth_message = {
            'api_key': api_key,
            'client_type': 'debug_client',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'broker_account_id': '602966',  # 从截图看到的 MT5 账号
        }
        print(f"  Message: {json.dumps(auth_message, indent=2)}")
        await websocket.send(json.dumps(auth_message))
        print("✓ Authentication message sent")
        print()
        
        print("[Step 3] Waiting for server response...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            print(f"✓ Received response:")
            print(f"  Type: {data.get('type', 'unknown')}")
            print(f"  Full response: {json.dumps(data, indent=2)}")
            
            if data.get('type') == 'connection_established':
                print("\n✅ SUCCESS: WebSocket connection established!")
                print(f"  Client ID: {data.get('client_id')}")
                return True
            elif data.get('type') == 'error':
                print(f"\n ERROR: {data.get('message', 'Unknown error')}")
                return False
            else:
                print(f"\n⚠️  Unexpected response type: {data.get('type')}")
                return False
                
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for response")
            print("  Server did not respond within 10 seconds")
            return False
            
    except ConnectionClosed as e:
        print(f"❌ Connection closed: {e}")
        print(f"  Code: {e.code}")
        print(f"  Reason: {e.reason}")
        print()
        print("Possible causes:")
        print("  1. Server rejected the connection (check API key)")
        print("  2. Server crashed after accepting connection")
        print("  3. Nginx proxy closed the connection")
        return False
        
    except Exception as e:
        print(f"❌ Connection error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await websocket.close()
        except:
            pass


def main():
    """Main entry point."""
    print()
    print("⚠️  IMPORTANT: Replace 'your_actual_api_key_here' with your real API key!")
    print("   You can get it from: Web管理后台 → 个人中心 → 交易所配置")
    print()
    
    confirm = input("Do you want to continue? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("Aborted.")
        sys.exit(0)
    
    print()
    result = asyncio.run(debug_websocket())
    
    if result:
        print("\n✅ Debug completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Debug failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
