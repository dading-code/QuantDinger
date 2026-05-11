# QuantDinger 云端大脑 + 本地执行架构指南

## 📖 概述

本指南介绍如何使用QuantDinger的**"云端大脑 + 本地执行"**架构，让你能够：

✅ **使用云端所有AI智能工具** - 策略生成、回测、优化、市场分析  
✅ **本地安全执行交易** - 交易密钥永不离开本地  
✅ **实时信号推送** - 毫秒级延迟接收交易信号  
✅ **支持多种券商** - MT5、IBKR、Binance等  

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────┐
│   Cloud QuantDinger (AI Brain)          │
│                                         │
│  • AI策略生成 & 优化                     │
│  • 市场数据分析                          │
│  • 技术指标计算                          │
│  • 信号生成引擎                          │
│         ↓ WebSocket (实时推送)           │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Local Trade Executor (客户端)         │
│                                         │
│  • 接收云端信号                          │
│  • 本地风控检查                          │
│  • 交易执行                              │
│         ↓ Direct API                    │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│   Broker (MT5 / IBKR / Binance)        │
│                                         │
│  • 真实交易执行                          │
│  • 持仓管理                              │
│  • 订单状态反馈                          │
└─────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 第一步：安装依赖

#### 云端服务器（QuantDinger Backend）

```bash
cd backend_api_python
pip install websockets
```

#### 本地客户端

```bash
pip install websockets MetaTrader5
```

> **注意**: MetaTrader5仅在Windows上可用。如果使用其他券商，安装对应的SDK。

---

### 第二步：启动云端WebSocket服务

#### 方法1: 独立运行（测试用）

```bash
cd backend_api_python
python app/services/websocket_signal.py
```

服务将启动在 `ws://localhost:8765/ws`

#### 方法2: 集成到FastAPI（生产环境）

WebSocket路由已自动集成到Agent Gateway API：

```
ws://your-domain.com/api/agent/v1/ws/signals
```

无需额外配置，启动QuantDinger后端即可。

---

### 第三步：运行本地交易客户端

#### 基本用法（模拟模式）

```bash
cd scripts
python local_trade_executor.py \
    --api-key your-api-key \
    --cloud-url ws://your-cloud.com/api/agent/v1/ws/signals \
    --broker simulation
```

#### MT5实盘交易

```bash
python local_trade_executor.py \
    --api-key your-api-key \
    --cloud-url ws://your-cloud.com/api/agent/v1/ws/signals \
    --broker mt5
```

> **前提条件**: 
> - Windows系统
> - 已安装MetaTrader 5终端
> - MT5终端已登录交易账号

#### IBKR实盘交易（待实现）

```bash
python local_trade_executor.py \
    --api-key your-api-key \
    --cloud-url ws://your-cloud.com/api/agent/v1/ws/signals \
    --broker ibkr
```

---

## 🔧 配置说明

### 云端配置

#### 1. API密钥认证

目前使用简单的API密钥验证。在生产环境中，建议：

- 在数据库中添加API密钥表
- 实现OAuth 2.0认证
- 添加IP白名单

示例数据库表结构：

```sql
CREATE TABLE qd_api_keys (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_api_key (api_key)
);
```

#### 2. 环境变量（可选）

```bash
# WebSocket配置
export WEBSOCKET_HOST=0.0.0.0
export WEBSOCKET_PORT=8765
export SIGNAL_NOTIFY_TIMEOUT_SEC=6
```

---

### 本地客户端配置

#### 风险管理配置

编辑 `scripts/local_trade_executor.py` 中的 `risk_config`:

```python
self.risk_config = {
    'max_position_size': 0.1,      # 单笔最大仓位（10%）
    'max_daily_loss': 0.05,        # 每日最大亏损（5%）
    'max_open_positions': 5,       # 最大持仓数量
    'stop_loss_pct': 0.02,         # 止损比例（2%）
    'take_profit_pct': 0.04,       # 止盈比例（4%）
}
```

#### MT5配置

确保MT5终端：
1. 已登录交易账号
2. 允许算法交易（Tools → Options → Expert Advisors → Allow automated trading）
3. 品种列表已加载

---

## 📊 信号格式

### WebSocket消息格式

#### 认证消息（客户端→云端）

```json
{
    "api_key": "your-api-key",
    "client_type": "local_executor",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

#### 交易信号（云端→客户端）

```json
{
    "type": "trading_signal",
    "signal_id": "uuid-xxxx-xxxx",
    "timestamp": "2024-01-01T00:00:00Z",
    "data": {
        "strategy_id": 123,
        "strategy_name": "双均线策略",
        "symbol": "BTC/USDT",
        "signal_type": "open_long",
        "price": 50000.0,
        "stake_amount": 0.05,
        "direction": "long",
        "pending_order_id": 456,
        "execution_mode": "signal",
        "notification_results": {
            "browser": {"ok": true, "error": ""},
            "telegram": {"ok": true, "error": ""}
        }
    }
}
```

#### 心跳消息

**客户端→云端**:
```json
{"type": "ping"}
```

**云端→客户端**:
```json
{
    "type": "pong",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 🎯 使用场景

### 场景1: 云端策略回测 + 本地实盘

1. 在云端使用QuantDinger的所有AI工具进行策略研发
2. 回测验证策略有效性
3. 启动策略，选择 `execution_mode='signal'`
4. 本地客户端接收信号并执行实盘交易

**优势**: 
- 策略研发在云端，享受强大算力
- 交易密钥在本地，安全性高
- 可以随时切换模拟/实盘

---

### 场景2: 多账户统一管理

1. 云端运行多个策略
2. 每个策略对应不同的本地客户端
3. 每个客户端连接不同的券商账户

**优势**:
- 集中管理所有策略
- 分散风险到多个账户
- 统一监控和日志

---

### 场景3: 跨券商套利

1. 云端监控多个市场的价差
2. 生成套利信号
3. 本地客户端同时在多个券商执行

**优势**:
- 低延迟执行
- 自动化套利
- 实时监控

---

## 🔍 监控和调试

### 查看WebSocket连接状态

```bash
curl http://your-cloud.com/api/agent/v1/ws/stats
```

响应示例：

```json
{
    "success": true,
    "data": {
        "total_connections": 10,
        "active_connections": 3,
        "messages_sent": 1234,
        "messages_failed": 0,
        "queue_size": 5,
        "clients": [
            {
                "client_id": "uuid-xxx",
                "connected_at": "2024-01-01T00:00:00Z",
                "last_heartbeat": 1704067200
            }
        ]
    }
}
```

### 测试WebSocket连接

```bash
curl -X POST "http://your-cloud.com/api/agent/v1/ws/broadcast/test?api_key=test-key"
```

这将向所有连接的客户端发送一个测试信号。

---

### 本地客户端日志

本地客户端会输出详细的执行日志：

```
[12:30:45] Connecting to ws://localhost:8765/ws...
[12:30:45] Connected!
[12:30:45] Authentication sent
[12:30:45] ✓ Authentication successful
  Client ID: uuid-xxx
[12:30:45] Waiting for trading signals...
================================================================================

================================================================================
[Signal #1] Received at 2024-01-01T12:30:50Z
Signal ID: signal-uuid-xxx
Strategy: 双均线策略
Symbol: BTC/USDT
Type: open_long
Price: 50000.0
Stake: 0.05
Direction: long
[Validation] ✓ Signal accepted
[MT5] Sending order: BTC/USDT open_long vol=0.05 price=50000.0
[Execution] ✓ Trade executed successfully
  Order ID: 123456789
  Filled: 0.05
  Price: 50000.0
```

---

## 🛡️ 安全建议

### 1. API密钥管理

- ✅ 使用强随机密钥（至少32字符）
- ✅ 定期轮换密钥
- ❌ 不要硬编码密钥
- ❌ 不要在代码仓库中提交密钥

### 2. 网络加密

- ✅ 生产环境使用WSS（WebSocket Secure）
- ✅ 配置SSL证书
- ❌ 不要在公网使用明文WS

### 3. 访问控制

- ✅ 实施IP白名单
- ✅ 限制API密钥权限
- ✅ 记录所有连接日志
- ❌ 不要共享API密钥

### 4. 风险控制

- ✅ 设置单笔最大仓位
- ✅ 设置每日最大亏损
- ✅ 实施止损机制
- ❌ 不要无限放大杠杆

---

## 🐛 常见问题

### Q1: WebSocket连接失败

**症状**: `ConnectionRefusedError`

**解决**:
1. 检查云端服务是否启动
2. 检查防火墙设置
3. 验证URL是否正确

```bash
# 测试端口连通性
telnet your-cloud.com 8765
```

---

### Q2: 认证失败

**症状**: `Authentication failed`

**解决**:
1. 检查API密钥是否正确
2. 确认密钥未过期
3. 查看云端日志

---

### Q3: MT5初始化失败

**症状**: `MT5 initialization failed`

**解决**:
1. 确认MT5终端已安装
2. 确认MT5终端正在运行
3. 确认已登录交易账号
4. 检查Python版本（仅支持64位）

```python
import MetaTrader5 as mt5
if not mt5.initialize():
    print(f"Error: {mt5.last_error()}")
```

---

### Q4: 信号延迟过高

**症状**: 信号接收延迟超过1秒

**解决**:
1. 检查网络连接质量
2. 降低云端负载
3. 优化数据库查询
4. 考虑使用CDN加速

---

## 📈 性能优化

### 1. 消息队列优化

当前使用内存队列，适合小规模部署。大规模部署建议使用：

- Redis Pub/Sub
- RabbitMQ
- Kafka

### 2. 并发处理

当前使用asyncio单线程。高并发场景可以：

- 使用uvloop替代默认事件循环
- 增加worker进程数
- 使用负载均衡

### 3. 数据库优化

- 为`qd_pending_orders`表添加索引
- 定期清理历史数据
- 使用读写分离

---

## 🔮 未来规划

### 阶段2: 增强功能

- [ ] 双向通信（客户端可请求策略调整）
- [ ] 信号回放（历史信号重放测试）
- [ ] 多语言客户端（JavaScript、Go、Rust）
- [ ] Web Dashboard可视化

### 阶段3: EA/MQL5插件

- [ ] MT5 EA插件开发
- [ ] 一键导入策略
- [ ] 可视化回测

### 阶段4: 高级风控

- [ ] 动态仓位调整
- [ ] 相关性分析
- [ ] 黑天鹅防护

---

## 📞 技术支持

如有问题，请：

1. 查看日志文件
2. 搜索GitHub Issues
3. 提交新的Issue（包含详细错误信息）

---

## 📄 许可证

本项目遵循MIT许可证。详见LICENSE文件。

---

**祝你交易顺利！🚀**
