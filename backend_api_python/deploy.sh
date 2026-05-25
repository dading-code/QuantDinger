#!/bin/bash
# QuantDinger Backend API 部署脚本 (Linux)

set -e

echo "=========================================="
echo "QuantDinger Backend API 部署"
echo "=========================================="

# 配置变量
APP_DIR="/opt/quantdinger/backend_api_python"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="quantdinger-backend"

# 1. 创建应用目录
echo "📁 创建应用目录..."
sudo mkdir -p $APP_DIR
cd $APP_DIR

# 2. 复制代码
echo "📦 复制代码..."
sudo cp -r /path/to/QuantDinger/backend_api_python/* $APP_DIR/

# 3. 创建虚拟环境
echo "🐍 创建 Python 虚拟环境..."
sudo python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# 4. 安装依赖
echo "📥 安装依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. 配置环境变量
echo "⚙️  配置环境变量..."
if [ ! -f .env ]; then
    sudo cp .env.example .env
    echo "请编辑 .env 文件并设置正确的配置"
    exit 1
fi

# 6. 创建 systemd 服务
echo "🔧 创建 systemd 服务..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=QuantDinger Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
echo "🚀 启动服务..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

# 8. 检查状态
echo "✅ 检查服务状态..."
sudo systemctl status $SERVICE_NAME

echo ""
echo "=========================================="
echo "部署完成!"
echo "=========================================="
echo "服务地址: http://localhost:5000"
echo "查看日志: sudo journalctl -u $SERVICE_NAME -f"
echo "重启服务: sudo systemctl restart $SERVICE_NAME"
echo "停止服务: sudo systemctl stop $SERVICE_NAME"
