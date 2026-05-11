#!/bin/bash
# QuantDinger 本地交易客户端 - Linux/Mac 启动脚本

echo "========================================"
echo "QuantDinger 本地交易客户端"
echo "========================================"
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    echo "请从 https://www.python.org/ 安装 Python 3.8+"
    exit 1
fi

echo "✓ 已找到 Python!"
echo ""

# 检查 websockets 是否安装
if ! python3 -c "import websockets" &> /dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
    echo "✓ 依赖安装成功!"
    echo ""
fi

echo "正在启动图形界面..."
echo ""
python3 main.py
