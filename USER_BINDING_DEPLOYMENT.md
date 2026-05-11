# 用户绑定与信号隔离 - 部署和测试指南

## 功能概述

本功能实现了多用户云端交易系统的本地客户端绑定机制：

- **云端**（99服务器）运行QuantDinger，有多个注册用户
- **每个用户**在自己的电脑上运行本地交易客户端
- **本地客户端**通过API Key连接云端WebSocket服务
- **信号隔离**：用户A的客户端只接收用户A的交易信号，用户B的客户端只接收用户B的信号

## 已完成的工作

### 1. 数据库层 ✅
- 在 `backend_api_python/migrations/init.sql` 中添加了 `qd_api_keys` 表
- 支持API Key的生成、验证、过期管理

### 2. 后端服务层 ✅
- 创建了 `app/services/api_key_manager.py` - API Key管理服务
  - 生成安全的API Key（格式：`qd_` + 64字符十六进制）
  - SHA256哈希存储，不存储明文
  - 验证API Key并返回用户信息
  - 支持停用和删除API Key

- 修改了 `app/services/websocket_signal.py`
  - `register_client` 方法：验证API Key并存储用户信息到client_metadata
  - `broadcast_signal` 方法：添加 `target_user_id` 参数实现用户隔离

### 3. API路由层 ✅
- 在 `app/routes/user.py` 中添加了4个API Key管理接口：
  - `POST /api/user/api-key/create` - 创建新API Key
  - `GET /api/user/api-key/list` - 列出用户的所有API Key
  - `POST /api/user/api-key/revoke` - 停用API Key
  - `DELETE /api/user/api-key/delete` - 删除API Key

### 4. 本地客户端层 ✅
- 创建了 `quantdinger-local-client/src/core/api_client.py` - HTTP API客户端
  - 用户登录认证
  - API Key创建和管理
  
- 修改了 `quantdinger-local-client/src/gui/app.py`
  - 添加用户名和密码输入框
  - 添加"登录并获取API Key"按钮
  - 登录后自动创建API Key并填入配置
  - 分离HTTP API地址和WebSocket地址配置

## 部署步骤

### 步骤1：更新数据库

在99服务器上执行数据库迁移：

```bash
# 连接到PostgreSQL数据库
psql -U your_username -d your_database

# 执行迁移脚本（如果qd_api_keys表不存在）
\i backend_api_python/migrations/init.sql
```

或者手动创建表：

```sql
CREATE TABLE IF NOT EXISTS qd_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES qd_users(id) ON DELETE CASCADE,
    api_key TEXT NOT NULL UNIQUE,
    key_name VARCHAR(100) DEFAULT 'Default',
    description TEXT DEFAULT '',
    active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON qd_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_api_key ON qd_api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON qd_api_keys(active);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires ON qd_api_keys(expires_at) WHERE expires_at IS NOT NULL;
```

### 步骤2：重启后端服务

```bash
# 在99服务器上
cd /path/to/QuantDinger/backend_api_python

# 如果使用systemd
sudo systemctl restart quantdinger-backend

# 或者手动重启
pkill -f "python.*run.py"
nohup python run.py > logs/backend.log 2>&1 &
```

### 步骤3：测试API Key功能

使用curl测试API：

```bash
# 1. 登录获取token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "trader01", "password": "your_password"}'

# 假设返回的token是: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 2. 创建API Key
curl -X POST http://localhost:5000/api/user/api-key/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -d '{
    "key_name": "TestKey",
    "description": "Testing",
    "expires_days": 365
  }'

# 应该返回：
# {
#   "code": 1,
#   "msg": "API Key创建成功，请妥善保存（只显示一次）",
#   "data": {
#     "api_key": "qd_xxxxxxxxxxxxxxxx...",
#     "key_info": {...}
#   }
# }

# 3. 列出API Keys
curl -X GET http://localhost:5000/api/user/api-key/list \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 步骤4：运行端到端测试

```bash
# 在项目根目录
cd d:\www\workai\QuantDinger

# 运行测试脚本
python test_e2e_user_isolation.py
```

预期输出：
```
================================================================================
开始端到端测试：用户信号隔离
================================================================================

[步骤 1] 查找测试用户...
✓ 找到用户A: trader01 (ID: 2)
✓ 找到用户B: testuser (ID: 3)

[步骤 2] 为用户生成API Key...
✓ 用户A API Key: qd_a1b2c3d4e5f6...
✓ 用户B API Key: qd_f6e5d4c3b2a1...

[步骤 3] 初始化WebSocket Hub...
✓ WebSocket Hub已初始化

[步骤 4] 模拟客户端连接...
✓ 客户端A已注册 (用户: trader01)
✓ 客户端B已注册 (用户: testuser)
✓ 当前活跃连接数: 2

[步骤 5] 发送信号给用户A...
✓ 测试通过：只有用户A的客户端收到了信号

[步骤 6] 发送信号给用户B...
✓ 测试通过：只有用户B的客户端收到了信号

[步骤 7] 发送广播信号（所有用户）...
✓ 测试通过：所有客户端都收到了广播信号

================================================================================
✅ 所有测试通过！
================================================================================
```

### 步骤5：使用本地客户端测试

1. **启动本地客户端**：
   ```bash
   cd quantdinger-local-client
   python src/main.py
   ```

2. **配置连接**：
   - 云端地址：`http://你的99服务器IP:5000/api`
   - 用户名：`trader01`
   - 密码：`******`
   - 点击"🔑 登录并获取API Key"

3. **验证**：
   - 系统会自动创建API Key并填入
   - WS地址：`ws://你的99服务器IP:8765/ws`
   - 选择券商类型（simulation/mt5/ibkr）
   - 点击"💾 保存配置"
   - 点击"▶ 启动"

4. **测试信号接收**：
   - 在后端触发一个属于trader01的交易信号
   - 验证只有trader01的客户端收到信号
   - 用testuser登录另一个客户端，验证不会收到trader01的信号

## 工作流程图

```
用户操作流程：
┌─────────────┐
│  用户登录    │ ← 输入用户名和密码
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 获取Token   │ ← POST /api/auth/login
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 创建API Key │ ← POST /api/user/api-key/create
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 保存配置    │ ← API Key自动填入
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 连接WS      │ ← ws://server:8765/ws?api_key=xxx
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 接收信号    │ ← 只接收该用户的信号
└─────────────┘

信号路由流程：
┌──────────────┐
│ 策略生成信号  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ 确定目标用户  │ ← 从信号中提取user_id
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ broadcast_signal()   │
│ target_user_id = X   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ 遍历所有客户端        │
│ if client.user_id == │
│    target_user_id:   │
│   发送信号            │
└──────────────────────┘
```

## 安全注意事项

1. **API Key只在创建时显示一次**，之后无法查看完整Key
2. **API Key存储在数据库中时使用SHA256哈希**，即使数据库泄露也无法还原
3. **建议定期更换API Key**（停用旧Key，创建新Key）
4. **不要将API Key提交到版本控制系统**
5. **生产环境建议使用HTTPS/WSS**加密传输

## 故障排查

### 问题1：登录失败
- 检查用户名和密码是否正确
- 检查后端服务是否正常运行
- 查看后端日志：`tail -f logs/backend.log`

### 问题2：API Key创建失败
- 检查用户是否有权限
- 检查数据库连接是否正常
- 查看后端错误日志

### 问题3：WebSocket连接失败
- 检查防火墙是否开放8765端口
- 检查API Key是否正确
- 检查WebSocket服务是否运行

### 问题4：收不到信号
- 检查信号是否正确指定了target_user_id
- 检查客户端是否使用正确的API Key连接
- 查看WebSocket服务端日志

## 下一步工作

- [ ] 在前端用户管理界面添加API Key管理功能
- [ ] 添加API Key使用统计和监控
- [ ] 实现API Key自动轮换机制
- [ ] 添加IP白名单限制
- [ ] 实现更细粒度的权限控制
