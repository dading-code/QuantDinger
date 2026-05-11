# 快速开始指南

## 🚀 3分钟快速启动

### Windows用户

**方式1: 双击启动（最简单）**
```
双击 start.bat
```

**方式2: 命令行启动**
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动GUI客户端
python gui_client.py
```

### Mac/Linux用户

```bash
# 1. 赋予执行权限
chmod +x start.sh

# 2. 运行启动脚本
./start.sh

# 或者手动启动
pip3 install -r requirements.txt
python3 gui_client.py
```

---

## 📝 使用步骤

### 第1步：配置连接信息

启动GUI后，填写以下信息：

1. **API Key**: 从QuantDinger云端获取的API密钥
2. **Cloud URL**: WebSocket服务器地址
   - 本地测试：`ws://localhost:8765/ws`
   - 生产环境：`wss://your-domain.com/api/agent/v1/ws/signals`
3. **Broker**: 选择券商类型
   - `simulation` - 模拟模式（推荐先测试）
   - `mt5` - MetaTrader 5
   - `ibkr` - Interactive Brokers

点击 **"Save Config"** 保存配置。

### 第2步：启动接收信号

点击 **"▶ Start"** 按钮开始接收信号。

状态栏会显示：
- 🔴 红色 = 未连接
- 🟢 绿色 = 已连接

### 第3步：监控交易

- **Recent Signals**: 显示最近收到的信号
- **Logs**: 显示详细日志
- **Signals Received**: 累计收到的信号数
- **Trades Executed**: 累计执行的交易数

---

## 🔧 常见问题

### Q1: 提示 "websockets library not installed"

**解决**:
```bash
pip install websockets
```

### Q2: 连接失败 "Connection refused"

**原因**: 云端WebSocket服务未启动

**解决**:
在QuantDinger服务器上运行：
```bash
cd backend_api_python
python start_websocket_server.py
```

### Q3: API Key认证失败

**原因**: API Key不正确或已过期

**解决**:
1. 检查API Key是否正确
2. 联系管理员确认API Key有效
3. 确保API Key有WebSocket访问权限

### Q4: MT5连接失败

**原因**: MT5终端未启动或未登录

**解决**:
1. 启动MT5终端
2. 登录交易账户
3. 确认MetaTrader5库已安装：`pip install MetaTrader5`

### Q5: IBKR连接失败

**原因**: TWS或IB Gateway未启动

**解决**:
1. 启动TWS或IB Gateway
2. 启用API访问（端口7497或4002）
3. 确认ib_insync库已安装：`pip install ib_insync`

---

## 📊 界面说明

```
┌─────────────────────────────────────────────┐
│ Configuration (配置区域)                     │
│ • API Key: 输入API密钥                       │
│ • Cloud URL: WebSocket地址                   │
│ • Broker: 选择券商类型                       │
│ • [Save Config]: 保存配置                    │
├─────────────────────────────────────────────┤
│ Connection Status (连接状态)                  │
│ • ● Connected/Disconnected                   │
│ • Signals Received: 信号计数                 │
│ • Trades Executed: 交易计数                  │
├─────────────────────────────────────────────┤
│ Control Buttons (控制按钮)                    │
│ • [▶ Start]: 启动接收信号                    │
│ • [⏹ Stop]: 停止接收                         │
│ • [🗑 Clear Logs]: 清空日志                   │
│ • [💾 Export Logs]: 导出日志                  │
├──────────────────┬──────────────────────────┤
│ Recent Signals   │ Logs (日志)               │
│ (最近信号列表)    │ • 实时显示日志             │
│ • 时间           │ • 支持滚动查看             │
│ • 策略名称       │ • 支持导出为文件           │
│ • 交易对         │                           │
│ • 信号类型       │                           │
└──────────────────┴──────────────────────────┘
```

---

## 🛡️ 安全提示

1. **保护API Key**: 不要分享给他人
2. **先用模拟模式**: 熟悉后再用实盘
3. **设置风控参数**: 限制最大仓位和亏损
4. **定期检查日志**: 监控交易执行情况
5. **使用WSS加密**: 生产环境务必使用加密连接

---

## 📞 需要帮助？

- 📖 查看完整文档: [README.md](README.md)
- 🐛 报告问题: GitHub Issues
- 💬 讨论交流: GitHub Discussions

祝你交易顺利！🚀
