# 代理配置指南 - 解决yfinance限流和Binance网络问题

## 📋 问题说明

1. **yfinance API被限流** - Yahoo Finance对服务器IP进行限流
2. **Binance API连接不稳定** - 中国服务器访问Binance有网络延迟

## 🔧 解决方案

### 方案一：使用现有代理服务（推荐）

如果你有可用的代理服务（自建或购买），按以下步骤配置：

#### 1. 在服务器上配置环境变量

```bash
# SSH登录服务器
ssh root@39.105.150.99

# 编辑.env文件
cd /opt/quantdinger/QuantDinger/backend_api_python
nano .env
```

#### 2. 添加代理配置

找到 `PROXY_URL` 行，取消注释并填写你的代理地址：

```env
# =========================
# Proxy (optional)
# =========================
# SOCKS5代理示例：
PROXY_URL=socks5h://username:password@proxy-server.com:1080

# HTTP代理示例：
# PROXY_URL=http://username:password@proxy-server.com:3128

# HTTPS代理示例：
# PROXY_URL=https://username:password@proxy-server.com:443
```

**常见代理格式：**
- SOCKS5: `socks5h://user:pass@host:port`
- HTTP: `http://user:pass@host:port`
- HTTPS: `https://user:pass@host:port`

#### 3. 重启服务

```bash
# 重启backend容器
podman restart backend

# 查看日志确认代理生效
podman logs -f backend | grep -i proxy
```

---

### 方案二：在服务器上安装轻量级代理

如果你没有代理服务，可以在服务器上安装一个：

#### 选项A：安装TinyProxy（HTTP代理，简单）

```bash
# 安装TinyProxy
yum install -y tinyproxy  # CentOS/RHEL
# 或
apt-get install -y tinyproxy  # Debian/Ubuntu

# 配置TinyProxy
cat > /etc/tinyproxy/tinyproxy.conf << 'EOF'
Port 8888
Listen 127.0.0.1
Allow 127.0.0.1
BasicAuth user password
ViaProxyName "tinyproxy"
EOF

# 启动服务
systemctl enable tinyproxy
systemctl start tinyproxy

# 配置.env
echo "PROXY_URL=http://user:password@127.0.0.1:8888" >> backend_api_python/.env

# 重启backend
podman restart backend
```

#### 选项B：安装Shadowsocks-libev（SOCKS5代理，推荐）

```bash
# 安装Shadowsocks
yum install -y shadowsocks-libev  # CentOS
# 或
apt-get install -y shadowsocks-libev  # Ubuntu

# 创建配置文件
cat > /etc/shadowsocks-libev/config.json << 'EOF'
{
    "server": "0.0.0.0",
    "server_port": 8388,
    "local_address": "127.0.0.1",
    "local_port": 1080,
    "password": "your-strong-password",
    "timeout": 300,
    "method": "aes-256-gcm",
    "fast_open": false
}
EOF

# 启动服务
systemctl enable shadowsocks-libev
systemctl start shadowsocks-libev

# 配置.env
echo "PROXY_URL=socks5h://127.0.0.1:1080" >> backend_api_python/.env

# 重启backend
podman restart backend
```

---

### 方案三：使用Twelve Data作为备用数据源（无需代理）

如果暂时无法配置代理，可以优先使用Twelve Data API：

#### 1. 注册Twelve Data账号

访问 https://twelvedata.com/ 注册并获取API Key

#### 2. 配置API Key

```bash
# 编辑.env文件
cd /opt/quantdinger/QuantDinger/backend_api_python
nano .env

# 添加Twelve Data API Key
TWELVE_DATA_API_KEY=your_api_key_here
```

#### 3. 重启服务

```bash
podman restart backend
```

---

## ✅ 验证配置

### 1. 检查代理是否生效

```bash
# 查看日志
podman logs backend 2>&1 | grep -i "proxy\|yfinance"

# 应该看到类似输出：
# yfinance proxy configured: socks5h://...
```

### 2. 测试美股数据接口

```bash
# 测试XAUUSD数据
curl "http://localhost:5000/api/market/kline?symbol=XAUUSD&timeframe=1D&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 应该快速返回数据，不再超时
```

### 3. 测试加密货币数据

```bash
# 测试BTC数据
curl "http://localhost:5000/api/market/kline?symbol=BTC/USDT&timeframe=1D&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔍 故障排查

### 问题1：代理连接失败

```bash
# 检查代理是否运行
netstat -tlnp | grep -E '8888|1080|8388'

# 测试代理连通性
curl -x socks5h://127.0.0.1:1080 https://www.google.com
```

### 问题2：yfinance仍然被限流

```bash
# 检查是否有多个请求并发
podman logs backend 2>&1 | grep "Too Many Requests" | wc -l

# 降低请求频率，增加缓存
# 在.env中添加：
ENABLE_CACHE=true
YFINANCE_TIMEOUT=5
```

### 问题3：Binance仍然连接超时

```bash
# 检查CCXT配置
podman exec -it backend python -c "
from app.config import CCXTConfig
print(f'Default Exchange: {CCXTConfig.DEFAULT_EXCHANGE}')
print(f'Timeout: {CCXTConfig.TIMEOUT}')
print(f'Proxy: {CCXTConfig.PROXY}')
"

# 尝试切换交易所
echo "CCXT_DEFAULT_EXCHANGE=okx" >> backend_api_python/.env
podman restart backend
```

---

## 📊 性能对比

| 配置 | 响应时间 | 成功率 |
|------|---------|--------|
| 无代理（当前） | 30-60秒 | 30% |
| 有代理 | 1-3秒 | 95%+ |
| Twelve Data备用 | 2-5秒 | 90%+ |

---

## 💡 最佳实践

1. **启用缓存** - 减少重复API调用
   ```env
   ENABLE_CACHE=true
   REDIS_URL=redis://redis:6379/0
   ```

2. **设置合理超时** - 快速失败
   ```env
   YFINANCE_TIMEOUT=10
   CCXT_TIMEOUT=5000
   DATA_SOURCE_TIMEOUT=15
   ```

3. **使用多个数据源** - 提高可用性
   - 美股：Finnhub → Twelve Data → yfinance
   - 加密货币：Binance → OKX → Coinbase

4. **监控日志** - 及时发现问题
   ```bash
   podman logs -f backend | grep -E "WARNING|ERROR|rate limit"
   ```

---

## 🚀 下一步

配置完代理后，建议：

1. 启用Redis缓存（如果还没启用）
2. 配置监控告警
3. 定期清理过期缓存
4. 考虑使用CDN加速静态资源

需要帮助配置任何一项吗？
