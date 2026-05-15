#!/bin/bash
# Completely flush all iptables rules
echo "=== Resetting iptables ==="

# Set default policies to ACCEPT
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

# Flush all rules
iptables -F
iptables -X

echo "=== iptables reset complete ==="
echo "Current rules:"
iptables -L -n -v | head -20

echo ""
echo "Testing local connection..."
curl -s --max-time 3 http://127.0.0.1:5000/api/health || echo "Still failing"
