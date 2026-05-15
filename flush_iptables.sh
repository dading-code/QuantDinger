#!/bin/bash
# Flush Podman CNI iptables rules
echo "=== Flushing iptables rules ==="

# Flush all custom chains
iptables -F CNI-ISOLATION-STAGE-1 2>/dev/null
iptables -F CNI-ISOLATION-STAGE-2 2>/dev/null
iptables -F DOCKER 2>/dev/null
iptables -F DOCKER-USER 2>/dev/null
iptables -F DOCKER-INGRESS 2>/dev/null

# Delete custom chains
iptables -X CNI-ISOLATION-STAGE-1 2>/dev/null
iptables -X CNI-ISOLATION-STAGE-2 2>/dev/null
iptables -X CNI-ISOLATION-STAGE-3 2>/dev/null
iptables -X DOCKER 2>/dev/null
iptables -X DOCKER-USER 2>/dev/null
iptables -X DOCKER-INGRESS 2>/dev/null

# Remove CNI rules from FORWARD chain
iptables -D FORWARD -j CNI-ISOLATION-STAGE-1 2>/dev/null
iptables -D FORWARD -j DOCKER-USER 2>/dev/null
iptables -D FORWARD -j DOCKER 2>/dev/null

echo "=== iptables rules flushed ==="
echo "Current FORWARD chain:"
iptables -L FORWARD -n -v | head -5

echo ""
echo "Testing local connection..."
curl -s --max-time 3 http://127.0.0.1:5000/api/health || echo "Still failing"
