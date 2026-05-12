# API Key 绑定交易所配置的安全设计

## 核心设计理念

**API Key → Credential（交易所配置）→ 券商账号**

### 为什么这样设计？

1. **一个 API Key 只对应一个交易所账号**
   - 避免混淆：用户可能有多个 MT5 账号、IBKR 账号等
   - 精确控制：每个 API Key 只能驱动对应的交易账号

2. **云端通过 API Key 直接知道应该校验哪个券商账号**
   - API Key 绑定了 `credential_id`
   - `credential_id` 指向具体的交易所配置（包含 mt5_login、ibkr_account 等）
   - 本地客户端连接时上报实际登录的账号
   - 云端对比两者是否一致

3. **防止账号错配导致的风险**
   - 如果用户在云端绑定了 MT5 账号 A（602966）
   - 但本地客户端登录的是 MT5 账号 B（123456）
   - 云端会拒绝推送信号，防止错误交易

---

## 数据流程

### 1. 用户创建 API Key

```
前端界面：
  - 选择要绑定的交易所配置（MT5/IBKR/币安等）
  - 输入 API Key 名称和描述
  - 点击"生成 API Key"

后端处理：
  POST /api/user/api-key/create
  {
    "key_name": "MT5主账号",
    "description": "用于MT5自动交易",
    "credential_id": 123  // 绑定的交易所配置ID
  }

数据库存储：
  qd_api_keys:
    - user_id: 1
    - credential_id: 123  ← 关键：绑定到具体交易所配置
    - api_key: "qd_xxx..." (哈希存储)
```

### 2. 本地客户端连接 WebSocket

```python
# 本地客户端代码
from src.core.signal_client import SignalClient

# 获取当前 MT5 实际登录的账号
mt5_login = get_mt5_account_info()['login']  # 例如：602966

# 创建 SignalClient，传入实际账号
client = SignalClient(
    api_key="qd_xxx...",
    cloud_url="wss://your-domain.com/ws/signals",
    broker_account_id=str(mt5_login)  # 上报实际账号
)

# 连接时发送认证消息
{
    "type": "auth",
    "api_key": "qd_xxx...",
    "broker_account_id": "602966"  # 本地上报的实际账号
}
```

### 3. 云端校验流程

```python
# websocket_signal.py - register_client()

# Step 1: 验证 API Key
user_info = APIKeyService.validate_api_key(api_key)
# 返回：
# {
#     'user_id': 1,
#     'username': 'testuser',
#     'credential_id': 123,  ← API Key 绑定的交易所配置ID
#     'credential': {
#         'id': 123,
#         'exchange_id': 'mt5',
#         'config': {
#             'mt5_login': '602966',  ← 云端配置的期望账号
#             'mt5_server': 'Exness-MT5Trial7'
#         }
#     }
# }

# Step 2: 校验券商账号一致性
validation_result = _validate_broker_account(
    user_id=1,
    credential_id=123,  # 使用 API Key 绑定的 credential_id
    broker_account_id="602966"  # 本地上报的实际账号
)

# 查询数据库获取云端配置的期望账号
SELECT encrypted_config FROM qd_exchange_credentials 
WHERE id = 123 AND user_id = 1

# 解密后得到：mt5_login = "602966"

# Step 3: 对比
if expected_login == actual_login:
    ✅ 校验通过，允许连接
else:
    ❌ 校验失败，拒绝连接
    错误信息："Broker account mismatch: Cloud expects [602966], 
              but local client logged in as [123456]"
```

---

## 数据库表结构

### qd_api_keys（API Key 表）

```sql
CREATE TABLE qd_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id),
    credential_id INTEGER REFERENCES qd_exchange_credentials(id), -- 🔑 关键字段
    api_key TEXT NOT NULL UNIQUE,  -- 哈希存储
    key_name VARCHAR(100),
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### qd_exchange_credentials（交易所配置表）

```sql
CREATE TABLE qd_exchange_credentials (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id),
    exchange_id VARCHAR(50) NOT NULL,  -- 'mt5', 'ibkr', 'binance' 等
    encrypted_config TEXT NOT NULL,  -- 加密的配置（包含 mt5_login 等）
    created_at TIMESTAMP DEFAULT NOW()
);
```

**关系：**
- 一个用户可以有多个交易所配置（多个 MT5 账号、IBKR 账号等）
- 一个 API Key 绑定到一个交易所配置
- 通过 `credential_id` 建立关联

---

## 安全优势

### 1. 防止账号错配

**场景：**
- 用户在 Web 后台绑定了 MT5 账号 A（602966）
- 生成了 API Key，绑定到该配置
- 本地客户端不小心登录了 MT5 账号 B（123456）

**结果：**
- 云端校验发现账号不匹配
- 拒绝推送信号
- 日志记录：`User testuser: Broker account mismatch...`
- 用户收到错误提示，需要切换到正确的账号

### 2. 多账号隔离

**场景：**
- 用户有 3 个 MT5 账号（个人、家庭、公司）
- 为每个账号生成独立的 API Key
- 每个 API Key 只能驱动对应的账号

**结果：**
- 策略 A 使用 API Key 1 → 只能交易个人账号
- 策略 B 使用 API Key 2 → 只能交易家庭账号
- 策略 C 使用 API Key 3 → 只能交易公司账号
- 完全隔离，互不干扰

### 3. 审计追踪

**场景：**
- 发生异常交易
- 需要追溯是哪个 API Key、哪个账号执行的

**结果：**
- 通过 `qd_api_keys` 表可以查到：
  - 哪个用户
  - 哪个 API Key
  - 绑定的哪个交易所配置
  - 最后使用时间
- 完整的审计链路

---

## 实现文件清单

### 后端

1. **数据库迁移**
   - `backend_api_python/migrations/init.sql`
     - `qd_api_keys` 表添加 `credential_id` 字段

2. **API Key 管理**
   - `backend_api_python/app/services/api_key_manager.py`
     - `create_api_key()` 支持 `credential_id` 参数
     - `validate_api_key()` 返回 `credential_id` 和 `credential` 信息
     - `get_user_api_keys()` 返回 `credential_id`

3. **WebSocket 校验**
   - `backend_api_python/app/services/websocket_signal.py`
     - `register_client()` 接收 `credential_id` 参数
     - `_validate_broker_account()` 优先使用 `credential_id` 定位配置
     - 对比云端配置和本地上报的账号

4. **API 路由**
   - `backend_api_python/app/routes/user.py`
     - `/api/user/api-key/create` 支持 `credential_id` 参数

### 前端（待实现）

需要在 API Key 管理界面添加：
1. 创建 API Key 时显示交易所配置下拉列表
2. 用户选择要绑定的交易所配置
3. 显示已创建的 API Key 对应的交易所信息

---

## 兼容性说明

### 旧客户端兼容

如果本地客户端没有上报 `broker_account_id`：
- 云端跳过校验（`validated: false`）
- 允许连接（向后兼容）
- 日志记录：`No broker_account_id provided, skipping validation`

### 旧 API Key 兼容

如果 API Key 没有绑定 `credential_id`（NULL）：
- 云端查询用户的所有 MT5/IBKR 配置
- 尝试匹配任意一个配置
- 只要有一个匹配就通过校验
- 建议用户重新生成 API Key 并绑定具体配置

---

## 最佳实践

### 1. 为用户推荐的工作流程

```
1. 在 Web 后台绑定 MT5 账号
   ↓
2. 进入"API Key 管理"页面
   ↓
3. 点击"创建 API Key"
   ↓
4. 选择要绑定的交易所配置（例如：MT5-602966）
   ↓
5. 复制生成的 API Key
   ↓
6. 在本地客户端配置中粘贴 API Key
   ↓
7. 确保 MT5 终端已登录正确的账号（602966）
   ↓
8. 启动本地客户端
   ↓
9. 检查连接状态：✅ 已连接 + ✅ 账号校验通过
```

### 2. 为开发者推荐的测试流程

```python
# 测试 1：正常情况
api_key = create_api_key(user_id=1, credential_id=123)
connect_websocket(api_key, broker_account_id="602966")
# ✅ 应该成功

# 测试 2：账号不匹配
connect_websocket(api_key, broker_account_id="123456")
# ❌ 应该失败，错误："Broker account mismatch"

# 测试 3：未上报账号（兼容旧客户端）
connect_websocket(api_key)
# ✅ 应该成功，但 validated=false
```

---

## 常见问题

### Q1: 如果用户有多个 MT5 账号，怎么办？

**A:** 为每个 MT5 账号生成独立的 API Key：
- API Key 1 → 绑定 MT5 账号 A（602966）
- API Key 2 → 绑定 MT5 账号 B（123456）
- 本地客户端根据要交易的账号选择对应的 API Key

### Q2: 如果用户更换了 MT5 账号，怎么办？

**A:** 
1. 在 Web 后台更新交易所配置（修改 mt5_login）
2. 重新生成 API Key（或者继续使用旧的，因为 credential_id 不变）
3. 本地客户端切换到新账号后重新连接

### Q3: 如果不绑定 credential_id 会怎样？

**A:** 
- API Key 仍然有效
- 云端会查询用户的所有 MT5/IBKR 配置
- 只要本地上报的账号匹配任意一个配置就通过
- **安全性降低**，建议始终绑定 credential_id

### Q4: IBKR 账号如何校验？

**A:** 与 MT5 类似：
- 云端配置：`ibkr_account` 字段
- 本地上报：`broker_account_id` 参数
- 校验逻辑相同

### Q5: 为什么需要本地客户端？云端不能直接执行交易吗？

**A:** **这是架构设计的核心决策：**

#### 技术限制
- **MT5 (MetaTrader 5)**：
  - 只能在 Windows 上运行
  - 需要 MT5 终端程序 (`terminal64.exe`) 正在运行
  - Python 库 `MetaTrader5` 不支持 Linux/Mac
  
- **IBKR (Interactive Brokers)**：
  - 需要 TWS (Trader Workstation) 或 IB Gateway 在本地运行
  - 涉及复杂的会话管理和认证
  - 云端容器无法访问用户的桌面应用

#### 安全考虑
- 券商账号密码不应该存储在云端
- 本地执行确保私钥/密码只在用户机器上
- 符合金融行业的最佳实践（交易执行在受控环境）

#### 架构优势
```
云端 (Cloud):
  ✅ 策略计算、AI 分析、数据聚合
  ✅ 信号生成、WebSocket 推送
  ❌ 无法直接执行 MT5/IBKR 订单

本地客户端 (Local):
  ✅ 接收云端信号
  ✅ 账号一致性校验
  ✅ 调用本地 MT5/IBKR API
  ✅ 执行实际交易订单
  ✅ 风险管理最后一道防线
```

**总结：QuantDinger 采用混合架构，云端负责智能分析，本地负责执行交易。本地客户端是必须的，不是可选的。**

---

## 总结

这个设计实现了**真正的端到端账号一致性校验**：

1. **API Key 绑定交易所配置** → 明确知道应该用哪个账号
2. **本地客户端上报实际账号** → 透明化当前状态
3. **云端实时校验** → 防止账号错配
4. **完整的审计链路** → 可追溯、可调试

这是一个**生产级别的安全设计**，能够有效防止因账号错配导致的交易风险。
