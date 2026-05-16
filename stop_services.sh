#!/bin/bash
#
# QuantDinger 服务停止脚本
# 停止后端 API 服务和 WebSocket 信号服务
#

echo "=========================================="
echo "  QuantDinger 服务停止脚本"
echo "=========================================="

# 停止 WebSocket 服务
echo "🛑 停止 WebSocket 服务..."
if [ -f "websocket.pid" ]; then
    PID=$(cat websocket.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ WebSocket 服务已停止 (PID: $PID)"
    else
        echo "⚠️  WebSocket 服务未运行 (PID: $PID)"
    fi
    rm -f websocket.pid
else
    echo " 未找到 WebSocket PID 文件，尝试通过进程名停止..."
    pkill -f "python.*start_ws_server.py" && echo "✅ WebSocket 服务已停止" || echo "⚠️  未找到 WebSocket 进程"
fi

# 停止后端服务
echo "🛑 停止后端 API 服务..."
if [ -f "backend.pid" ]; then
    PID=$(cat backend.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ 后端服务已停止 (PID: $PID)"
    else
        echo "⚠️  后端服务未运行 (PID: $PID)"
    fi
    rm -f backend.pid
else
    echo " 未找到后端 PID 文件，尝试通过进程名停止..."
    pkill -f "gunicorn.*run:app" && echo "✅ 后端服务已停止" || echo "⚠️  未找到后端进程"
fi

echo ""
echo "=========================================="
echo "  ✅ 所有服务已停止"
echo "=========================================="
echo ""
