# QuantDinger 线上部署检查清单

## ✅ 部署前检查

### 服务器环境
- [ ] Linux 服务器 (47.93.6.116) - 用于 Backend API
- [ ] Windows 服务器 - 用于 MT5 Observer (可与 Backend 同一台或分开)
- [ ] PostgreSQL 数据库已安装并运行
- [ ] Python 3.11+ 已安装
- [ ] Git 已安装

### 网络配置
- [ ] 防火墙开放端口:
  - [ ] 5000 (Backend API)
  - [ ] 8765 (WebSocket)
  - [ ] 5432 (PostgreSQL, 如需远程访问)
- [ ] SSL 证书配置 (可选,推荐生产环境使用 HTTPS)

---

## 📦 部署步骤

### 第一步: 部署 MT5 Observer (Windows)

1. **安装 MT5 终端**
   ```bash
   # 下载并安装 MetaTrader 5
   # 登录交易账户
   ```

2. **克隆代码**
   ```bash
   cd D:\www\workai\qd-ai\MT5_Observer
   git pull
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置 `src/config.json`**
   ```json
   {
     "websocket": {
       "url": "ws://localhost:8765/ws",
       "token": "observer-token"
     },
     "symbols": ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSD"],
     "timeframes": ["M1", "M5", "M15", "H1", "D1"]
   }
   ```

5. **启动 Observer**
   ```bash
   cd src
   python start_no_gui.py
   ```

6. **验证连接**
   - 查看日志确认 WebSocket 连接成功
   - 检查是否能获取 MT5 数据

---

### 第二步: 部署 Backend API (Linux)

1. **克隆代码**
   ```bash
   sudo mkdir -p /opt/quantdinger
   cd /opt/quantdinger
   git clone <repository_url> backend_api_python
   cd backend_api_python
   ```

2. **创建虚拟环境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **配置 `.env`**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   编辑以下配置:
   ```env
   # 数据库配置
   DATABASE_URL=postgresql://quantdinger:密码@47.93.6.116:5432/quantdinger
   
   # MT5 Bridge 配置
   ENABLE_MT5_BRIDGE=true
   MT5_OBSERVER_WS_URL=ws://localhost:8765/ws
   
   # AnythingLLM 配置
   LLM_PROVIDER=anythingllm
   ANYTHING_LLM_KEY=IW7XRVAN-46_KOB2O-SUIBZ0OC-ER5ASHXY
   ANYTHING_LLM_BASE_URL=http://101.201.67.41:3001
   ANYTHING_LLM_WORKSPACE=news-analysis
   ANYTHINGLLM_API_KEY=IW7XRVAN-46_KOB2O-SUIBZ0OC-ER5ASHXY
   ANYTHINGLLM_WORKSPACE_URL=http://101.201.67.41:3001/api/v1/workspace/news-analysis/chat
   
   # 其他配置
   SECRET_KEY=your-secret-key-here
   SINGLE_USER_MODE=true
   PYTHON_API_DEBUG=false  # 生产环境设为 false
   ```

5. **初始化数据库**
   ```bash
   python scripts/init_db.py
   ```

6. **测试运行**
   ```bash
   python run.py
   ```
   
   访问 `http://localhost:5000/health` 确认服务正常

7. **配置 systemd 服务**
   ```bash
   sudo nano /etc/systemd/system/quantdinger-backend.service
   ```
   
   添加以下内容:
   ```ini
   [Unit]
   Description=QuantDinger Backend API
   After=network.target postgresql.service
   
   [Service]
   Type=simple
   User=www-data
   Group=www-data
   WorkingDirectory=/opt/quantdinger/backend_api_python
   Environment="PATH=/opt/quantdinger/backend_api_python/venv/bin"
   ExecStart=/opt/quantdinger/backend_api_python/venv/bin/python run.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

8. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable quantdinger-backend
   sudo systemctl start quantdinger-backend
   ```

9. **检查状态**
   ```bash
   sudo systemctl status quantdinger-backend
   sudo journalctl -u quantdinger-backend -f
   ```

---

## 🔍 验证部署

### 1. 检查 Backend API
```bash
curl http://localhost:5000/health
```

预期响应:
```json
{"status": "ok", "timestamp": 1234567890}
```

### 2. 检查 WebSocket 连接
```bash
# 在服务器上执行
netstat -an | grep 8765
```

应该看到:
```
tcp  0  0 0.0.0.0:8765  0.0.0.0:*  LISTEN
```

### 3. 测试 MT5 数据获取
```bash
curl http://localhost:5000/api/market/price?market=Forex&symbol=XAUUSD
```

预期响应:
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "market": "Forex",
    "symbol": "XAUUSD",
    "price": 2345.67,
    "change": 12.34,
    "changePercent": 0.53
  }
}
```

### 4. 测试 AI 分析
```bash
# 先登录获取 token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "QuantDinger@2026!Secure"}'

# 使用 token 测试 AI 分析
curl -X POST http://localhost:5000/api/indicator/aiGenerate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "XAUUSD",
    "market": "Forex",
    "timeframe": "1D",
    "prompt": "Create a simple MA crossover strategy"
  }'
```

---

## 🚨 故障排查

### 问题 1: Backend API 无法启动
**检查**:
```bash
sudo journalctl -u quantdinger-backend -n 50
```

**常见原因**:
- 端口 5000 被占用
- 数据库连接失败
- 缺少依赖包

### 问题 2: MT5 Observer 连接失败
**检查**:
```bash
# Windows 上查看日志
type D:\www\workai\qd-ai\MT5_Observer\src\debug.log
```

**常见原因**:
- WebSocket URL 配置错误
- MT5 终端未运行
- 品种名称不匹配

### 问题 3: 数据获取超时
**检查后端日志**:
```bash
sudo journalctl -u quantdinger-backend -f | grep "timeout"
```

**解决方案**:
- 检查 MT5 Observer 是否正常运行
- 增加 WebSocket 超时时间
- 检查网络连接

---

## 📊 监控和维护

### 日志查看
```bash
# Backend API 日志
sudo journalctl -u quantdinger-backend -f

# MT5 Observer 日志 (Windows)
Get-Content D:\www\workai\qd-ai\MT5_Observer\src\debug.log -Wait -Tail 50
```

### 性能监控
```bash
# 检查 CPU 和内存使用
top -p $(pgrep -f "python run.py")

# 检查数据库连接
psql -U quantdinger -d quantdinger -c "SELECT count(*) FROM pg_stat_activity;"
```

### 备份策略
```bash
# 每日备份数据库
0 2 * * * pg_dump -U quantdinger quantdinger > /backup/quantdinger_$(date +\%Y\%m\%d).sql
```

---

## ✅ 部署完成确认

- [ ] Backend API 正常运行
- [ ] MT5 Observer 已连接
- [ ] WebSocket 通信正常
- [ ] 市场数据可以获取
- [ ] AI 分析功能正常
- [ ] 前端可以访问后端 API
- [ ] 日志监控已配置
- [ ] 自动重启已配置
- [ ] 备份策略已实施

---

## 📞 技术支持

如遇到问题,请检查:
1. 日志文件中的错误信息
2. 网络连接是否正常
3. 配置文件是否正确
4. 依赖服务是否运行

联系技术支持时请提供:
- 错误日志
- 配置文件(隐藏敏感信息)
- 系统环境信息
