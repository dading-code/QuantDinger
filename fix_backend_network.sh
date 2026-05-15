#!/bin/bash
# 修复backend网络连接并检查状态

echo "=========================================="
echo "1. 将backend添加到quantdinger-network"
echo "=========================================="
podman network connect quantdinger-network backend 2>&1 || echo "Backend可能已在网络中或网络不存在"

echo ""
echo "=========================================="
echo "2. 重启backend容器"
echo "=========================================="
podman restart backend

echo ""
echo "=========================================="
echo "3. 等待5秒后检查日志"
echo "=========================================="
sleep 5

echo ""
echo "最新的backend日志（最后20行）："
podman logs --tail 20 backend

echo ""
echo "=========================================="
echo "4. 检查容器状态"
echo "=========================================="
podman ps | grep -E "backend|quantdinger-db"
