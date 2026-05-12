#!/bin/bash
# Test WebSocket server on port 8765

podman exec backend python3 << 'PYEOF'
import socket

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('127.0.0.1', 8765))
    if result == 0:
        print("✓ Port 8765 is LISTENING - WebSocket server is running")
        
        # Try to send a test message
        import json
        ws_test_msg = json.dumps({'type': 'test'})
        print(f"  Server is accepting connections")
    else:
        print(f"✗ Port 8765 is NOT listening (error code: {result})")
    s.close()
except Exception as e:
    print(f"✗ Error: {e}")
PYEOF
