#!/bin/bash
# Test WebSocket connection from inside backend container

echo "Testing WebSocket connection to port 8765..."
echo ""

podman exec backend python3 << 'PYEOF'
import asyncio
import json
import sys
from datetime import datetime, timezone

async def test_ws():
    try:
        import websockets
        
        # Connect to WebSocket server
        print("[1] Connecting to ws://127.0.0.1:8765/ws...")
        websocket = await websockets.connect("ws://127.0.0.1:8765/ws")
        print("✓ TCP connection established")
        
        # Send auth message with a test API key
        print("[2] Sending authentication...")
        auth_message = {
            'api_key': 'test_key_12345',
            'client_type': 'test_client',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'broker_account_id': '602966',
        }
        await websocket.send(json.dumps(auth_message))
        print("✓ Auth message sent")
        
        # Wait for response
        print("[3] Waiting for server response...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)
            print(f"✓ Received response:")
            print(f"  Type: {data.get('type')}")
            print(f"  Full: {json.dumps(data, indent=2)}")
        except asyncio.TimeoutError:
            print("✗ Timeout - no response from server")
        
        await websocket.close()
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        if hasattr(e, 'code'):
            print(f"  Code: {e.code}")
        if hasattr(e, 'reason'):
            print(f"  Reason: {e.reason}")

asyncio.run(test_ws())
PYEOF
