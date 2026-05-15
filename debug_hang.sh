#!/bin/bash
# Find out why the app is hanging
echo "=== 1. Check app initialization logs ==="
grep -E "Starting gunicorn|Listening at|Worker booting|Application startup|Database|Redis|Init" /var/log/quantdinger-backend.log | tail -20

echo ""
echo "=== 2. Check for any errors or warnings ==="
grep -E "ERROR|WARNING|Exception|Timeout|Failed" /var/log/quantdinger-backend.log | tail -20

echo ""
echo "=== 3. Check if Python process is hanging ==="
strace -p 3989169 -e trace=network -c 2>&1 | head -20 &
STRACE_PID=$!
sleep 3
kill $STRACE_PID 2>/dev/null
