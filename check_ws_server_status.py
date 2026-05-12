#!/usr/bin/env python3
"""Check if WebSocket server (8765) is actually running and get its logs"""
import subprocess
import sys

# Check port 8765
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
result = s.connect_ex(('127.0.0.1', 8765))
if result == 0:
    print("✓ Port 8765 is LISTENING")
else:
    print(f"✗ Port 8765 is NOT listening (code: {result})")
    sys.exit(1)
s.close()

# Try to find the process running on port 8765
try:
    result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if ':8765' in line:
            print(f"\nProcess on port 8765:")
            print(line)
except:
    print("\nCould not check process (ss command not available)")

# Check backend container logs for websocket server
try:
    result = subprocess.run(
        ['podman', 'logs', 'backend'],
        capture_output=True,
        text=True
    )
    lines = result.stdout.split('\n')
    
    print("\nSearching for WebSocket server logs...")
    found = False
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['websocket signal server', 'starting websocket', '8765']):
            print(line)
            found = True
    
    if not found:
        print("No WebSocket server startup logs found!")
        print("\nLast 20 backend logs:")
        for line in lines[-20:]:
            print(line)
            
except Exception as e:
    print(f"Error checking logs: {e}")
