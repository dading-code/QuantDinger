#!/bin/bash
# Test API health
echo "=== Testing local API (direct) ==="
curl -s http://127.0.0.1:5000/api/health 2>&1 | head -5

echo ""
echo "=== Testing via Nginx (8888) ==="
curl -s http://39.105.150.99:8888/api/health 2>&1 | head -5
