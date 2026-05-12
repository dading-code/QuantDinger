#!/bin/bash
# Check backend health
echo "=== Backend Container Status ==="
podman ps --filter name=backend --format "Status={{.Status}} State={{.State}}"

echo ""
echo "=== Testing Health Endpoint (inside container) ==="
podman exec backend python3 -c "
import urllib.request
try:
    r = urllib.request.urlopen('http://localhost:5000/api/health')
    print(f'Health check: {r.status}')
except Exception as e:
    print(f'Health check FAILED: {e}')
"

echo ""
echo "=== Testing Health Endpoint (from host) ==="
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:5000/api/health || echo "FAILED"

echo ""
echo "=== Recent Error Logs ==="
podman logs --tail 100 backend 2>&1 | grep -i -E 'error|exception|traceback|critical|worker.*timeout|gunicorn.*fail' | tail -10
