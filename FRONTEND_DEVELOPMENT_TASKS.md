# 本地客户端绑定功能 - 前端开发任务说明

## 📋 项目背景

QuantDinger采用"云端大脑 + 本地执行"架构。MT5、IBKR等交易所需要在用户本地电脑运行交易终端，因此需要：

### 用户只需下载轻量级本地客户端

**quantdinger-local-client** 是一个**独立的Python GUI程序**：
- ✅ **无需部署完整后端** - 只是一个客户端程序
- ✅ **通过WebSocket连接云端** - 接收交易信号
- ✅ **在本地执行交易** - 直接调用MT5/IBKR API
- ✅ **轻量级设计** - 只包含必要的功能模块

### 工作流程

1. 用户在云端获取API Key
2. **下载并安装本地客户端**（独立程序，无需配置服务器）
3. 客户端通过WebSocket连接云端
4. 接收属于该用户的交易信号
5. 在本地执行MT5/IBKR交易

---

## ✅ 后端已完成

所有后端API接口已开发完成并测试通过，包括：

- ✅ API Key管理（创建、查询、停用、删除）
- ✅ WebSocket状态查询
- ✅ 交易所类型判断（是否需要本地执行）
- ✅ 信号推送和用户隔离机制

**详细文档**: 
- `BACKEND_API_DOCUMENTATION.md` - API接口详细说明
- `BACKEND_DEVELOPMENT_COMPLETE.md` - 后端开发完成报告

---

## 🎯 前端需要实现的功能

### 功能1: 交易所管理页面增强

**位置**: 交易所管理列表页面

**需求**:
1. 在交易所列表中，对每个交易所检查是否为本地交易所（MT5、IBKR）
2. 对于本地交易所，显示：
   - WebSocket连接状态指示灯（绿色=已连接，红色=未连接）
   - "获取API Key"按钮
   - 客户端下载链接

**实现步骤**:

#### Step 1: 判断交易所类型

```javascript
// 在加载交易所列表后，对每个交易所进行检查
async function checkExchangeType(exchangeId) {
  const response = await fetch(
    `/api/credentials/is-local-broker?exchange_id=${exchangeId}`,
    {
      headers: {
        'Authorization': `Bearer ${getToken()}`
      }
    }
  );
  
  const data = await response.json();
  
  if (data.code === 1 && data.data.is_local) {
    // 这是本地交易所（MT5或IBKR）
    showLocalBrokerUI(exchangeId);
  }
}
```

#### Step 2: 显示连接状态

```javascript
// 每5秒轮询一次连接状态
async function pollConnectionStatus() {
  const response = await fetch('/api/websocket/is-connected', {
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
  
  const data = await response.json();
  
  if (data.code === 1) {
    updateConnectionIndicator(data.data.connected, data.data.client_count);
  }
}

// 启动轮询
setInterval(pollConnectionStatus, 5000);
```

#### Step 3: 获取API Key

```javascript
async function handleGetApiKey() {
  const response = await fetch('/api/user/api-key/create', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
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
    // 显示API Key弹窗（重要：只显示一次！）
    showApiKeyModal(data.data.api_key);
  } else {
    showError(data.msg);
  }
}
```

#### Step 4: UI设计建议

```vue
<template>
  <div class="exchange-card" v-for="exchange in exchanges" :key="exchange.id">
    <h3>{{ exchange.name }}</h3>
    
    <!-- 如果是本地交易所，显示额外信息 -->
    <div v-if="exchange.is_local" class="local-broker-info">
      <!-- 连接状态指示器 -->
      <div class="connection-status">
        <span 
          class="status-dot" 
          :class="{ connected: isConnected, disconnected: !isConnected }"
        ></span>
        <span class="status-text">
          {{ isConnected ? `已连接 (${clientCount}个客户端)` : '未连接' }}
        </span>
      </div>
      
      <!-- 获取API Key按钮 -->
      <button @click="handleGetApiKey" class="btn-primary">
        获取API Key
      </button>
      
      <!-- 客户端下载链接 -->
      <a href="/download/local-client" class="download-link">
        下载本地客户端
      </a>
      
      <!-- 提示信息 -->
      <div class="client-info">
        <small>
          💡 这是一个轻量级的独立程序，无需部署服务器<br/>
          安装后登录您的账户，即可自动连接并开始接收交易信号
        </small>
      </div>
    </div>
    
    <!-- 其他交易所配置... -->
  </div>
</template>

<style scoped>
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 5px;
}

.status-dot.connected {
  background-color: #52c41a; /* 绿色 */
}

.status-dot.disconnected {
  background-color: #ff4d4f; /* 红色 */
}

.local-broker-info {
  margin-top: 10px;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}
</style>
```

---

### 功能2: API Key显示弹窗

**需求**:
- 创建API Key后，以模态框形式显示给用户
- **重要提示**: API Key只显示一次，关闭后无法再次查看
- 提供"复制"按钮和"我已保存"确认按钮

**UI示例**:

```vue
<template>
  <el-dialog
    title="API Key 创建成功"
    :visible.sync="dialogVisible"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="api-key-warning">
      <el-alert
        title="重要提示"
        type="warning"
        :closable="false"
      >
        <p>⚠️ API Key 只会显示这一次，请妥善保存！</p>
        <p>关闭后将无法再次查看明文。</p>
      </el-alert>
    </div>
    
    <div class="api-key-display">
      <el-input
        v-model="apiKey"
        readonly
        style="margin-top: 15px;"
      >
        <template slot="append">
          <el-button @click="copyToClipboard">
            复制
          </el-button>
        </template>
      </el-input>
    </div>
    
    <div class="next-steps" style="margin-top: 20px;">
      <h4>下一步：</h4>
      <ol>
        <li><strong>下载本地客户端</strong> - 这是一个轻量级的独立程序，无需部署服务器</li>
        <li>安装后打开客户端</li>
        <li>输入您的用户名和密码登录</li>
        <li>客户端会自动获取API Key并连接云端</li>
        <li>开始接收交易信号并在本地执行MT5/IBKR交易</li>
      </ol>
      
      <div class="client-features" style="margin-top: 15px; padding: 10px; background-color: #f0f9ff; border-radius: 4px;">
        <h5 style="margin: 0 0 10px 0;">💡 客户端特点：</h5>
        <ul style="margin: 0; padding-left: 20px;">
          <li>✅ 独立的Python GUI程序</li>
          <li>✅ 无需部署完整后端</li>
          <li>✅ 通过WebSocket连接云端接收信号</li>
          <li>✅ 在本地直接执行MT5/IBKR交易</li>
          <li>✅ 轻量级设计，易于安装和使用</li>
        </ul>
      </div>
    </div>
    
    <span slot="footer" class="dialog-footer">
      <el-button type="primary" @click="dialogVisible = false">
        我已保存
      </el-button>
    </span>
  </el-dialog>
</template>

<script>
export default {
  data() {
    return {
      dialogVisible: false,
      apiKey: ''
    };
  },
  methods: {
    copyToClipboard() {
      navigator.clipboard.writeText(this.apiKey).then(() => {
        this.$message.success('已复制到剪贴板');
      });
    }
  }
};
</script>
```

---

### 功能3: API Key管理页面（可选）

**位置**: 个人中心 → API Key管理

**需求**:
- 列出当前用户的所有API Key
- 显示Key名称、描述、创建时间、过期时间、最后使用时间
- 支持停用和删除API Key

**API调用**:

```javascript
// 获取API Key列表
async function loadApiKeys() {
  const response = await fetch('/api/user/api-key/list', {
    headers: {
      'Authorization': `Bearer ${getToken()}`
    }
  });
  
  const data = await response.json();
  
  if (data.code === 1) {
    this.apiKeys = data.data.keys;
  }
}

// 停用API Key
async function revokeApiKey(keyId) {
  const response = await fetch('/api/user/api-key/revoke', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${getToken()}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      key_id: keyId
    })
  });
  
  const data = await response.json();
  
  if (data.code === 1) {
    this.$message.success('API Key已停用');
    this.loadApiKeys(); // 刷新列表
  }
}
```

---

## 📡 需要调用的API接口

### 1. 判断交易所类型

```
GET /api/credentials/is-local-broker?exchange_id=mt5
```

**响应**:
```json
{
  "code": 1,
  "data": {
    "exchange_id": "mt5",
    "is_local": true,
    "requires_client": true,
    "client_download_url": "/download/local-client",
    "description": "需要下载本地客户端以接收交易信号并执行"
  }
}
```

---

### 2. 获取API Key

```
POST /api/user/api-key/create
Content-Type: application/json
Authorization: Bearer YOUR_JWT_TOKEN

{
  "key_name": "LocalClient",
  "description": "本地交易客户端",
  "expires_days": 365
}
```

**响应**:
```json
{
  "code": 1,
  "msg": "API Key创建成功，请妥善保存（只显示一次）",
  "data": {
    "api_key": "qd_ak_xxxxxxxxxxxxxxxxxxxx",
    "key_name": "LocalClient",
    "expires_at": "2025-01-01T00:00:00"
  }
}
```

---

### 3. 检查WebSocket连接状态

```
GET /api/websocket/is-connected
Authorization: Bearer YOUR_JWT_TOKEN
```

**响应**:
```json
{
  "code": 1,
  "data": {
    "connected": true,
    "client_count": 1
  }
}
```

---

### 4. 获取详细连接信息

```
GET /api/websocket/client-status
Authorization: Bearer YOUR_JWT_TOKEN
```

**响应**:
```json
{
  "code": 1,
  "data": {
    "total_clients": 1,
    "clients": [
      {
        "client_id": "uuid-xxx",
        "username": "trader01",
        "connected_at": "2024-01-01T00:00:00+00:00",
        "last_heartbeat": 1704067200.0,
        "ip_address": "1.2.3.4"
      }
    ]
  }
}
```

---

### 5. 获取API Key列表

```
GET /api/user/api-key/list
Authorization: Bearer YOUR_JWT_TOKEN
```

**响应**:
```json
{
  "code": 1,
  "data": {
    "keys": [
      {
        "id": 1,
        "key_name": "LocalClient",
        "description": "本地交易客户端",
        "active": true,
        "expires_at": "2025-01-01T00:00:00",
        "created_at": "2024-01-01T00:00:00"
      }
    ],
    "total": 1
  }
}
```

---

## 🎨 UI/UX建议

### 1. 连接状态指示器

使用颜色编码：
- 🟢 绿色：已连接
- 🔴 红色：未连接
- 🟡 黄色：连接中

### 2. 获取API Key流程

```
用户点击"获取API Key"
    ↓
调用API创建Key
    ↓
显示模态框（包含API Key）
    ↓
用户复制并保存
    ↓
用户点击"我已保存"
    ↓
关闭模态框
    ↓
提示下载客户端
```

### 3. 错误处理

- API调用失败时显示友好错误消息
- 网络超时重试机制
- API Key复制成功后给予反馈

---

## 📝 开发清单

### 必须实现

- [ ] 交易所列表页面集成`is-local-broker`检查
- [ ] 为MT5/IBKR显示连接状态指示器
- [ ] 添加"获取API Key"按钮
- [ ] 实现API Key创建和显示弹窗
- [ ] 实现WebSocket连接状态轮询（每5秒）
- [ ] 添加客户端下载链接

### 可选实现

- [ ] API Key管理页面
- [ ] 连接历史图表
- [ ] 客户端版本检查
- [ ] 自动更新提示

---

## 🧪 测试要点

### 功能测试

1. **API Key创建**
   - 点击按钮能成功创建
   - API Key正确显示
   - 复制功能正常工作
   - 关闭后无法再次查看

2. **连接状态显示**
   - 客户端连接时显示绿色
   - 客户端断开时显示红色
   - 状态实时更新

3. **交易所类型判断**
   - MT5/IBKR显示为本地交易所
   - Binance/Bybit不显示额外UI

### 兼容性测试

- Chrome、Firefox、Safari、Edge
- 移动端浏览器（响应式设计）

---

## 📚 参考文档

1. **后端API文档**: `BACKEND_API_DOCUMENTATION.md`
   - 所有API接口的详细说明
   - 请求/响应示例
   - 错误码说明

2. **开发计划**: `DEVELOPMENT_PLAN_APIKEY_FEATURE.md`
   - 完整的功能设计
   - 代码示例
   - 架构图

3. **后端完成报告**: `BACKEND_DEVELOPMENT_COMPLETE.md`
   - 已实现的功能列表
   - 技术实现细节
   - 验收标准

---

## 💡 常见问题

### Q1: API Key丢失怎么办？

A: 用户可以删除旧的API Key，然后重新创建一个新的。

### Q2: 如何知道客户端是否已连接？

A: 前端每5秒调用`/api/websocket/is-connected`接口，根据返回的`connected`字段更新UI。

### Q3: 多个客户端可以同时连接吗？

A: 可以。一个用户可以有多个客户端同时连接，`client_count`会显示连接数。

### Q4: API Key会过期吗？

A: 是的，默认365天过期。创建时可以指定`expires_days`参数。

---

## 🚀 部署后验证

1. 访问交易所管理页面
2. 添加MT5或IBKR账户
3. 应该看到"获取API Key"按钮和连接状态
4. 点击按钮创建API Key
5. 下载并启动本地客户端
6. 输入API Key连接
7. 前端应显示"已连接"状态

---

## 📞 技术支持

如有问题，请联系后端开发团队或参考上述文档。

**前端开发预计时间**: 3-4小时
**优先级**: 高
