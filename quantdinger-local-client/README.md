# QuantDinger Local Trade Client

一个独立的图形化本地交易客户端，用于接收QuantDinger云端信号并执行交易。

## 🚀 特性

- ✅ **图形化界面** - 直观的GUI，无需命令行操作
- ✅ **实时状态监控** - WebSocket连接状态、信号计数、交易统计
- ✅ **配置管理** - API Key、云端URL、券商类型一键配置
- ✅ **实时日志** - 彩色日志显示，支持导出
- ✅ **信号监控** - 实时显示收到的交易信号
- ✅ **多券商支持** - MT5、IBKR、模拟模式
- ✅ **自动重连** - 网络断开后自动重连
- ✅ **轻量级** - 仅依赖Python标准库 + websockets

## 📦 安装

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/quantdinger-local-client.git
cd quantdinger-local-client
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. （可选）安装券商SDK

```bash
# MT5支持（仅Windows）
pip install MetaTrader5

# IBKR支持
pip install ib_insync
```

## 🎯 使用方法

### 方式1: 图形界面（推荐）

```bash
python gui_client.py
```

启动后：
1. 填写API Key和云端URL
2. 选择券商类型（simulation/mt5/ibkr）
3. 点击"Save Config"保存配置
4. 点击"▶ Start"开始接收信号

### 方式2: 命令行模式

```bash
# 测试模式（只接收信号）
python test_websocket_client.py --api-key YOUR_KEY --url ws://localhost:8765/ws

# 模拟交易模式
python local_trade_executor.py --api-key YOUR_KEY --broker simulation

# MT5实盘模式
python local_trade_executor.py --api-key YOUR_KEY --broker mt5

# IBKR模式
python local_trade_executor.py --api-key YOUR_KEY --broker ibkr
```

## 🏗️ 项目结构

```
quantdinger-local-client/
├── main.py                      # ⭐ 主入口
├── src/                         # 源代码
│   ├── core/                    # 核心模块
│   │   ├── signal_client.py     # WebSocket客户端
│   │   └── config.py            # 配置管理
│   ├── gui/                     # 图形界面
│   │   └── app.py               # GUI应用
│   ├── brokers/                 # 券商集成（待扩展）
│   └── utils/                   # 工具函数
├── config/                      # 配置文件
├── requirements.txt             # 依赖
└── start.bat / start.sh         # 启动脚本
```

详细结构说明见 [STRUCTURE.md](STRUCTURE.md)

## 🔧 配置说明

### GUI配置

在图形界面中直接填写：
- **API Key**: QuantDinger云端的API密钥
- **Cloud URL**: WebSocket服务器地址（默认：ws://localhost:8765/ws）
- **Broker**: 券商类型（simulation/mt5/ibkr）

配置文件会自动保存为 `gui_config.json`

### 命令行配置

编辑 `config/example_config.json`：

```json
{
  "api_key": "your-api-key-here",
  "cloud_url": "ws://localhost:8765/ws",
  "broker": "simulation",
  "risk_management": {
    "max_position_size": 0.02,
    "max_daily_loss": 0.05,
    "max_open_positions": 5,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04
  }
}
```

## 📊 界面预览

```
┌─────────────────────────────────────────────────────┐
│  QuantDinger Local Trade Executor                   │
├─────────────────────────────────────────────────────┤
│ Configuration                                       │
│ API Key:    [********************************]      │
│ Cloud URL:  [ws://localhost:8765/ws     ]      │
│ Broker:     [simulation ▼]          [Save Config]  │
├─────────────────────────────────────────────────────┤
│ Connection Status                                   │
│ ● Connected    Signals: 5    Trades: 2             │
├─────────────────────────────────────────────────────┤
│ [▶ Start] [⏹ Stop] [🗑 Clear Logs] [💾 Export]    │
├──────────────────────┬──────────────────────────────┤
│ Recent Signals       │ Logs                         │
│ ┌──────────────────┐ │ ┌──────────────────────────┐ │
│ │ 10:30 | Strat1   │ │ │ [10:30:15] Connected!    │ │
│ │ 10:31 | Strat2   │ │ │ [10:30:16] Auth OK       │ │
│ │ 10:32 | Strat1   │ │ │ [10:31:00] Signal #1     │ │
│ └──────────────────┘ │ └──────────────────────────┘ │
└──────────────────────┴──────────────────────────────┘
```

## 🔌 与QuantDinger云端集成

### 第1步：启动云端WebSocket服务

在QuantDinger后端服务器上：

```bash
cd backend_api_python
python start_websocket_server.py
```

### 第2步：启动本地客户端

```bash
python gui_client.py
```

填写配置并点击"Start"即可开始接收信号！

## 🛡️ 安全建议

- ✅ 使用强API密钥（至少32字符）
- ✅ 生产环境使用WSS加密（wss://）
- ✅ 不要共享API密钥
- ✅ 先在模拟模式测试
- ✅ 设置合理的风险管理参数

## 📝 依赖说明

### 必需依赖
- `websockets` - WebSocket客户端库

### 可选依赖
- `MetaTrader5` - MT5交易支持（仅Windows）
- `ib_insync` - IBKR交易支持

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [QuantDinger主项目](https://github.com/yourusername/QuantDinger)
- [详细文档](docs/CLOUD_LOCAL_ARCHITECTURE_CN.md)
- [快速开始指南](QUICKSTART_CLOUD_LOCAL.md)
