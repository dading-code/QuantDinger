#!/usr/bin/env python3
"""Check Gunicorn binding configuration"""
import os
import socket

print("=" * 70)
print("Gunicorn Binding Configuration Check")
print("=" * 70)

# Check environment variables
print("\n[1] Environment Variables:")
print(f"  PYTHON_API_HOST: {os.getenv('PYTHON_API_HOST', 'NOT SET')}")
print(f"  PYTHON_API_PORT: {os.getenv('PYTHON_API_PORT', 'NOT SET')}")

# Check gunicorn_config.py
print("\n[2] Gunicorn Config File:")
try:
    with open('/app/gunicorn_config.py', 'r') as f:
        for line in f:
            if 'bind' in line.lower() and not line.strip().startswith('#'):
                print(f"  {line.strip()}")
except Exception as e:
    print(f"  Error reading config: {e}")

# Check actual listening ports
print("\n[3] Listening Ports:")
try:
    import subprocess
    result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if '5000' in line:
            print(f"  {line.strip()}")
except Exception as e:
    print(f"  Error checking ports: {e}")

# Check Gunicorn process
print("\n[4] Gunicorn Process:")
try:
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'gunicorn' in line.lower() and 'grep' not in line.lower():
            print(f"  {line.strip()}")
except Exception as e:
    print(f"  Error checking processes: {e}")

# Test binding
print("\n[5] Test Socket Binding:")
for host in ['0.0.0.0', '127.0.0.1', 'localhost']:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, 5000))
        if result == 0:
            print(f"  ✓ {host}:5000 - REACHABLE")
        else:
            print(f"  ✗ {host}:5000 - UNREACHABLE (error: {result})")
        sock.close()
    except Exception as e:
        print(f"  ? {host}:5000 - ERROR: {e}")

print("\n" + "=" * 70)
print("Recommended fix:")
print("  If PYTHON_API_HOST is 0.0.0.0 but listening on 127.0.0.1:")
print("  1. Check if gunicorn_config.py is being loaded")
print("  2. Restart backend with: podman restart backend")
print("  3. Verify with: podman exec backend netstat -tlnp | grep 5000")
print("=" * 70)
