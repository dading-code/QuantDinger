# MT5 Observer 部署指南

## 📋 前置要求

1. **Windows 服务器** (MT5 只能在 Windows 上运行)
2. **MetaTrader 5 终端** 已安装并登录
3. **Python 3.11+** 环境

## 🚀 部署步骤

### 1. 克隆代码

```bash
cd D:\www\workai\qd-ai\MT5_Observer
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 `config.json`

编辑 `src/config.json`:

```json
{
  "websocket": {
    "url": "ws://localhost:8765/ws",
    "token": "observer-token"
  },
  "symbols": ["XAUUSD", "EURUSD", "GBPUSD"],
  "timeframes": ["M1", "M5", "M15", "H1", "D1"]
}
```

### 4. 启动 Observer

```bash
cd src
python main.py
```

或使用无 GUI 模式:

```bash
python start_no_gui.py
```

### 5. 验证连接

检查日志中是否显示:
```
✅ WebSocket 连接成功
✅ MCP 处理器初始化完成
```

## 🔧 常见问题

### Q1: WebSocket 连接失败
**解决**: 确保 QuantDinger Backend API 已启动,WebSocket 服务运行在 8765 端口

### Q2: MT5 初始化失败
**解决**: 
- 确保 MT5 终端正在运行
- 检查账户是否已登录
- 确认品种名称正确 (如 XAUUSD vs XAU/USD)

### Q3: 数据获取超时
**解决**:
- 检查网络连接
- 增加 `config.json` 中的超时时间
- 查看 `debug.log` 获取详细错误信息

## 📊 监控

查看实时日志:
```bash
tail -f src/debug.log
```

检查 WebSocket 连接状态:
```bash
netstat -an | findstr "8765"
```

## 🔄 自动重启

使用 Windows 任务计划程序或第三方工具(如 NSSM)实现自动重启。

示例 NSSM 配置:
```bash
nssm install MT5Observer "D:\Python311\python.exe" "D:\www\workai\qd-ai\MT5_Observer\src\start_no_gui.py"
nssm set MT5Observer AppDirectory "D:\www\workai\qd-ai\MT5_Observer\src"
nssm set MT5Observer Restart SERVICE_RESTART_ON_FAILURE
```
