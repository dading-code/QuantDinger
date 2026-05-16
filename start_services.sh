#!/bin/bash
#
# QuantDinger 服务启动脚本
# 自动启动后端 API 服务和 WebSocket 信号服务
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend_api_python"
LOG_DIR="/var/log"

echo "=========================================="
echo "  QuantDinger 服务启动脚本"
echo "=========================================="

# 检查虚拟环境
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "❌ 错误: 虚拟环境不存在 ($BACKEND_DIR/.venv)"
    echo "请先运行: cd $BACKEND_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source "$BACKEND_DIR/.venv/bin/activate"

# 加载环境变量
echo "🔧 加载环境变量..."
if [ -f "$BACKEND_DIR/.env" ]; then
    set -a
    source "$BACKEND_DIR/.env"
    set +a
    echo "✅ 环境变量已加载"
else
    echo "⚠️  警告: .env 文件不存在 ($BACKEND_DIR/.env)"
fi

# 停止旧进程
echo "🛑 检查并停止旧进程..."
pkill -f "gunicorn.*run:app" 2>/dev/null || true
pkill -f "python.*start_ws_server.py" 2>/dev/null || true
sleep 2

# 启动 Gunicorn 后端服务
echo " 启动后端 API 服务 (端口 5000)..."
cd "$SCRIPT_DIR"
nohup gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 8 \
    --worker-class gevent \
    --timeout 120 \
    --access-logfile "$LOG_DIR/quantdinger-backend.log" \
    --error-logfile "$LOG_DIR/quantdinger-backend.log" \
    run:app > "$LOG_DIR/quantdinger-backend.log" 2>&1 &

BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端服务就绪
echo "⏳ 等待后端服务就绪..."
sleep 3

# 启动 WebSocket 信号服务
echo "🚀 启动 WebSocket 信号服务 (端口 8765)..."
cd "$SCRIPT_DIR"
nohup python start_ws_server.py > "$LOG_DIR/quantdinger-websocket.log" 2>&1 &

WS_PID=$!
echo "✅ WebSocket 服务已启动 (PID: $WS_PID)"

# 保存 PID 文件
echo "$BACKEND_PID" > "$SCRIPT_DIR/backend.pid"
echo "$WS_PID" > "$SCRIPT_DIR/websocket.pid"

echo ""
echo "=========================================="
echo "  ✅ 所有服务已启动完成！"
echo "=========================================="
echo ""
echo "📊 服务状态："
echo "   • 后端 API:   http://39.105.150.99:5000 (PID: $BACKEND_PID)"
echo "   • WebSocket:  ws://39.105.150.99:8765  (PID: $WS_PID)"
echo "   • Nginx 代理: http://39.105.150.99:8888"
echo ""
echo "📝 日志文件："
echo "   • 后端日志:   $LOG_DIR/quantdinger-backend.log"
echo "   • WebSocket:  $LOG_DIR/quantdinger-websocket.log"
echo ""
echo " 停止服务："
echo "   bash stop_services.sh"
echo ""
