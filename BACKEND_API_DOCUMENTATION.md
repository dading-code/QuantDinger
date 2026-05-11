# 本地客户端绑定功能 - 后端API文档

## 📋 概述

本文档描述了QuantDinger本地客户端绑定功能的后端API接口。这些接口支持：
- 用户通过API Key认证连接WebSocket
- 在交易所管理页面显示本地客户端连接状态
- 为MT5/IBKR等需要本地执行的交易所提供一键获取API Key功能

---

## 🔑 API Key管理接口

### 1. 创建API Key

**接口**: `POST /api/user/api-key/create`

**认证**: 需要登录 (`@login_required`)

**请求体**:
```json
{
  "key_name": "LocalClient",
  "description": "本地交易客户端",
  "expires_days": 365
}
```

**响应示例**:
```json
{
  "code": 1,
  "msg": "API Key创建成功，请妥善保存（只显示一次）",
  "data": {
    "api_key": "qd_ak_xxxxxxxxxxxxxxxxxxxx",
    "key_name": "LocalClient",
    "description": "本地交易客户端",
    "expires_at": "2025-01-01T00:00:00",
    "created_at": "2024-01-01T00:00:00"
  }
}
```

**说明**: 
- `api_key`只在创建时返回一次，后续无法查询明文
- 数据库中存储的是SHA256哈希值

---

### 2. 获取API Key列表

**接口**: `GET /api/user/api-key/list`

**认证**: 需要登录

**响应示例**:
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "keys": [
      {
        "id": 1,
        "key_name": "LocalClient",
        "description": "本地交易客户端",
        "active": true,
        "expires_at": "2025-01-01T00:00:00",
        "last_used_at": "2024-01-01T12:00:00",
        "created_at": "2024-01-01T00:00:00"
      }
    ],
    "total": 1
  }
}
```

---

### 3. 停用API Key

**接口**: `POST /api/user/api-key/revoke`

**认证**: 需要登录

**请求体**:
```json
{
  "key_id": 1
}
```

**响应示例**:
```json
{
  "code": 1,
  "msg": "API Key已停用",
  "data": null
}
```

---

### 4. 删除API Key

**接口**: `DELETE /api/user/api-key/delete`

**认证**: 需要登录

**请求体**:
```json
{
  "key_id": 1
}
```

**响应示例**:
```json
{
  "code": 1,
  "msg": "API Key已删除",
  "data": null
}
```

---

## 🌐 WebSocket状态接口

### 5. 获取当前用户的WebSocket客户端状态

**接口**: `GET /api/websocket/client-status`

**认证**: 需要登录

**响应示例**:
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "total_clients": 1,
    "clients": [
      {
        "client_id": "uuid-xxx",
        "username": "trader01",
        "email": "user@example.com",
        "connected_at": "2024-01-01T00:00:00+00:00",
        "last_heartbeat": 1704067200.0,
        "ip_address": "1.2.3.4"
      }
    ]
  }
}
```

**说明**:
- 返回当前用户所有活跃的WebSocket客户端连接
- 可用于前端显示"本地客户端已连接"状态

---

### 6. 简化的连接状态检查

**接口**: `GET /api/websocket/is-connected`

**认证**: 需要登录

**响应示例**:
```json
{
  "code": 1,
  "data": {
    "connected": true,
    "client_count": 1
  }
}
```

**说明**:
- 适用于前端快速轮询，减少数据传输量
- 只返回是否连接和连接数

---

### 7. 列出所有WebSocket客户端（仅管理员）

**接口**: `GET /api/websocket/clients`

**认证**: 需要管理员权限

**响应示例**:
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "total": 5,
    "clients": [
      {
        "client_id": "uuid-1",
        "user_id": 2,
        "username": "trader01",
        "email": "user1@example.com",
        "connected_at": "2024-01-01T00:00:00+00:00",
        "last_heartbeat": 1704067200.0,
        "ip_address": "1.2.3.4"
      },
      ...
    ]
  }
}
```

---

## 🏦 交易所相关接口

### 8. 判断交易所是否需要本地执行

**接口**: `GET /api/credentials/is-local-broker?exchange_id=mt5`

**认证**: 需要登录

**查询参数**:
- `exchange_id`: 交易所标识（如 'mt5', 'ibkr', 'binance'）

**响应示例**:
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "exchange_id": "mt5",
    "is_local": true,
    "requires_client": true,
    "client_download_url": "/download/local-client",
    "client_name": "QuantDinger Local Client",
    "description": "需要下载本地客户端以接收交易信号并执行"
  }
}
```

**说明**:
- 用于前端判断是否显示"获取API Key"按钮
- MT5和IBKR返回`is_local: true`

---

### 9. 获取所有需要本地执行的交易所列表

**接口**: `GET /api/credentials/local-brokers/list`

**认证**: 需要登录

**响应示例**:
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "brokers": [
      {
        "exchange_id": "mt5",
        "name": "MetaTrader 5",
        "requires_client": true,
        "description": "外汇/差价合约交易平台",
        "icon": "mt5"
      },
      {
        "exchange_id": "ibkr",
        "name": "Interactive Brokers",
        "requires_client": true,
        "description": "美股/全球股票交易平台",
        "icon": "ibkr"
      }
    ],
    "total": 2
  }
}
```

---

## 🔄 WebSocket信号推送机制

### 信号广播流程

1. **策略触发信号** → `SignalNotifier.notify_signal()`
2. **保存到数据库** → `qd_strategy_notifications`表
3. **WebSocket广播** → `_broadcast_via_websocket()`
   - 从策略中获取`user_id`
   - 调用`WebSocketSignalHub.broadcast_signal(target_user_id=user_id)`
   - 只发送给属于该用户的客户端

### 用户隔离机制

- WebSocket连接时验证API Key，获取用户信息
- 在`client_metadata`中存储`user_id`
- 广播信号时根据`target_user_id`过滤客户端
- 确保用户A的客户端只接收用户A的信号

---

## 📊 数据库表结构

### qd_api_keys表

```sql
CREATE TABLE qd_api_keys (
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

CREATE INDEX idx_api_keys_user_id ON qd_api_keys(user_id);
CREATE INDEX idx_api_keys_api_key ON qd_api_keys(api_key);
CREATE INDEX idx_api_keys_active ON qd_api_keys(active);
```

---

## 🧪 测试建议

### 1. API Key创建测试

```bash
curl -X POST http://localhost:5000/api/user/api-key/create \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key_name": "TestClient",
    "description": "测试客户端",
    "expires_days": 30
  }'
```

### 2. WebSocket连接测试

```python
import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8765/ws"
    async with websockets.connect(uri) as ws:
        # 发送认证消息
        await ws.send('{"api_key": "qd_ak_xxx"}')
        
        # 接收欢迎消息
        response = await ws.recv()
        print(f"Connected: {response}")

asyncio.run(test_ws())
```

### 3. 信号隔离测试

参考 `test_e2e_user_isolation.py` 脚本

---

## 📝 前端集成指南

### 在交易所管理页面添加功能

#### 1. 判断是否为本地交易所

```javascript
// 在加载交易所列表后，对每个交易所进行检查
async function checkIfLocalBroker(exchangeId) {
  const response = await fetch(`/api/credentials/is-local-broker?exchange_id=${exchangeId}`);
  const data = await response.json();
  
  if (data.code === 1 && data.data.is_local) {
    // 显示"获取API Key"按钮和连接状态
    showGetApiKeyButton(exchangeId);
    startConnectionStatusPolling();
  }
}
```

#### 2. 获取API Key

```javascript
async function getApiKey() {
  const response = await fetch('/api/user/api-key/create', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      key_name: 'LocalClient',
      description: '本地交易客户端',
      expires_days: 365
    })
  });
  
  const data = await response.json();
  if (data.code === 1) {
    // 显示API Key给用户（只显示一次）
    showApiKeyModal(data.data.api_key);
  }
}
```

#### 3. 轮询WebSocket连接状态

```javascript
// 每5秒检查一次连接状态
setInterval(async () => {
  const response = await fetch('/api/websocket/is-connected', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  if (data.code === 1) {
    updateConnectionStatus(data.data.connected, data.data.client_count);
  }
}, 5000);
```

---

## 🔒 安全注意事项

1. **API Key存储**: 数据库中只存储SHA256哈希，不存储明文
2. **API Key显示**: 创建时只显示一次，后续无法查询明文
3. **过期时间**: 建议设置合理的过期时间（默认365天）
4. **停用机制**: 发现异常可立即停用API Key
5. **用户隔离**: WebSocket信号严格隔离，防止跨用户泄露

---

## 🚀 部署检查清单

- [ ] 数据库迁移已执行（`qd_api_keys`表已创建）
- [ ] WebSocket服务器已启动（端口8765或自定义）
- [ ] Flask路由已注册（`websocket_bp`、`credentials_bp`扩展）
- [ ] SignalNotifier已集成WebSocket广播
- [ ] API Key管理服务已初始化
- [ ] 防火墙开放WebSocket端口
- [ ] HTTPS/WSS配置完成（生产环境）

---

## 📞 技术支持

如有问题，请参考：
- `DEVELOPMENT_PLAN_APIKEY_FEATURE.md` - 完整开发计划
- `USER_BINDING_DEPLOYMENT.md` - 部署指南
- `test_e2e_user_isolation.py` - 端到端测试脚本
