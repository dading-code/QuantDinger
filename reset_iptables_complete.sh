#!/bin/bash
# Completely reset iptables to fix "No route to host" issue

echo "=== Current iptables rules ==="
iptables -L -n -v | head -40

echo ""
echo "=== Resetting iptables ==="

# Set default policies to ACCEPT
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT  
iptables -P OUTPUT ACCEPT

# Flush all rules and delete all chains
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
iptables -t raw -F
iptables -t raw -X

echo "=== iptables reset complete ==="

echo ""
echo "=== Verify: No more CNI/DOCKER chains ==="
iptables -L -n | grep -E "CNI|DOCKER" || echo "No CNI/DOCKER chains found (good!)"

echo ""
echo "=== Test API connection ==="
curl -s --max-time 3 http://127.0.0.1:5000/api/health || echo "Still failing"
