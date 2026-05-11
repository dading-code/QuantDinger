#!/bin/bash
# 快速配置代理脚本 - 解决yfinance限流和Binance网络问题

set -e

echo "========================================="
echo "QuantDinger 代理配置助手"
echo "========================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "backend_api_python/.env" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

ENV_FILE="backend_api_python/.env"

# 显示当前代理配置
echo "📋 当前代理配置："
grep -E "^PROXY_URL=" "$ENV_FILE" || echo "   PROXY_URL= (未配置)"
echo ""

# 询问用户选择
echo "请选择配置方式："
echo "1. 使用现有代理服务（需要代理地址）"
echo "2. 在服务器上安装TinyProxy（HTTP代理）"
echo "3. 在服务器上安装Shadowsocks（SOCKS5代理）"
echo "4. 仅优化超时设置（不配置代理）"
echo "5. 取消"
echo ""

read -p "请输入选项 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "请输入代理地址："
        echo "示例格式："
        echo "  SOCKS5: socks5h://user:pass@host:port"
        echo "  HTTP:   http://user:pass@host:port"
        echo "  HTTPS:  https://user:pass@host:port"
        echo ""
        read -p "代理地址: " proxy_url
        
        if [ -z "$proxy_url" ]; then
            echo "❌ 代理地址不能为空"
            exit 1
        fi
        
        # 更新.env文件
        if grep -q "^PROXY_URL=" "$ENV_FILE"; then
            sed -i "s|^PROXY_URL=.*|PROXY_URL=$proxy_url|" "$ENV_FILE"
        else
            echo "" >> "$ENV_FILE"
            echo "# Proxy Configuration" >> "$ENV_FILE"
            echo "PROXY_URL=$proxy_url" >> "$ENV_FILE"
        fi
        
        echo "✅ 代理配置已更新: $proxy_url"
        ;;
        
    2)
        echo ""
        echo "🔧 安装TinyProxy..."
        
        # 检测系统类型
        if command -v yum &> /dev/null; then
            echo "检测到CentOS/RHEL系统"
            yum install -y tinyproxy
        elif command -v apt-get &> /dev/null; then
            echo "检测到Debian/Ubuntu系统"
            apt-get update && apt-get install -y tinyproxy
        else
            echo "❌ 不支持的系统"
            exit 1
        fi
        
        # 生成随机密码
        PASSWORD=$(openssl rand -base64 12 | tr -d '/+=' | head -c 12)
        
        # 配置TinyProxy
        cat > /etc/tinyproxy/tinyproxy.conf << EOF
Port 8888
Listen 127.0.0.1
Allow 127.0.0.1
BasicAuth quantdinger $PASSWORD
ViaProxyName "tinyproxy"
EOF
        
        # 启动服务
        systemctl enable tinyproxy
        systemctl start tinyproxy
        
        # 更新.env
        PROXY_URL="http://quantdinger:$PASSWORD@127.0.0.1:8888"
        if grep -q "^PROXY_URL=" "$ENV_FILE"; then
            sed -i "s|^PROXY_URL=.*|PROXY_URL=$PROXY_URL|" "$ENV_FILE"
        else
            echo "" >> "$ENV_FILE"
            echo "# TinyProxy Configuration" >> "$ENV_FILE"
            echo "PROXY_URL=$PROXY_URL" >> "$ENV_FILE"
        fi
        
        echo "✅ TinyProxy已安装并配置"
        echo "📝 代理地址: $PROXY_URL"
        echo "⚠️  请保存好密码: $PASSWORD"
        ;;
        
    3)
        echo ""
        echo "🔧 安装Shadowsocks-libev..."
        
        # 检测系统类型
        if command -v yum &> /dev/null; then
            echo "检测到CentOS/RHEL系统"
            yum install -y shadowsocks-libev
        elif command -v apt-get &> /dev/null; then
            echo "检测到Debian/Ubuntu系统"
            apt-get update && apt-get install -y shadowsocks-libev
        else
            echo "❌ 不支持的系统"
            exit 1
        fi
        
        # 生成随机密码
        PASSWORD=$(openssl rand -base64 16 | tr -d '/+=')
        
        # 配置Shadowsocks
        cat > /etc/shadowsocks-libev/config.json << EOF
{
    "server": "0.0.0.0",
    "server_port": 8388,
    "local_address": "127.0.0.1",
    "local_port": 1080,
    "password": "$PASSWORD",
    "timeout": 300,
    "method": "aes-256-gcm",
    "fast_open": false
}
EOF
        
        # 启动服务
        systemctl enable shadowsocks-libev
        systemctl start shadowsocks-libev
        
        # 更新.env
        PROXY_URL="socks5h://127.0.0.1:1080"
        if grep -q "^PROXY_URL=" "$ENV_FILE"; then
            sed -i "s|^PROXY_URL=.*|PROXY_URL=$PROXY_URL|" "$ENV_FILE"
        else
            echo "" >> "$ENV_FILE"
            echo "# Shadowsocks Configuration" >> "$ENV_FILE"
            echo "PROXY_URL=$PROXY_URL" >> "$ENV_FILE"
        fi
        
        echo "✅ Shadowsocks已安装并配置"
        echo "📝 代理地址: $PROXY_URL"
        echo "⚠️  请保存好密码: $PASSWORD"
        ;;
        
    4)
        echo ""
        echo "🔧 优化超时设置..."
        
        # 添加或更新超时配置
        cat >> "$ENV_FILE" << 'EOF'

# Optimized Timeout Settings
YFINANCE_TIMEOUT=10
CCXT_TIMEOUT=5000
DATA_SOURCE_TIMEOUT=15
FINNHUB_TIMEOUT=8
TIINGO_TIMEOUT=8
AKSHARE_TIMEOUT=10
EOF
        
        echo "✅ 超时设置已优化"
        echo "   YFINANCE_TIMEOUT=10秒"
        echo "   CCXT_TIMEOUT=5秒"
        echo "   DATA_SOURCE_TIMEOUT=15秒"
        ;;
        
    5)
        echo "已取消"
        exit 0
        ;;
        
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "配置完成！"
echo "========================================="
echo ""
echo "下一步操作："
echo "1. 重启backend服务: podman restart backend"
echo "2. 查看日志确认: podman logs -f backend | grep -i proxy"
echo "3. 测试接口: curl http://localhost:5000/api/market/kline?symbol=XAUUSD&timeframe=1D&limit=5"
echo ""

# 询问是否立即重启
read -p "是否立即重启backend服务？(y/n): " restart_choice
if [ "$restart_choice" = "y" ] || [ "$restart_choice" = "Y" ]; then
    echo "🔄 重启backend服务..."
    podman restart backend
    echo "✅ Backend已重启"
    echo ""
    echo "查看日志（按Ctrl+C退出）："
    podman logs -f backend
fi
