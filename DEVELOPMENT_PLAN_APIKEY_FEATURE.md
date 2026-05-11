# QuantDinger 本地客户端绑定功能 - 开发计划

##  需求概述

### 业务背景
QuantDinger采用"云端大脑 + 本地执行"架构，支持多用户云端服务。MT5、IBKR等交易所需要在用户本地电脑运行，因此需要：
- 用户在云端获取API Key
- 下载本地客户端连接云端WebSocket
- 本地客户端接收属于该用户的交易信号
- 在本地执行MT5/IBKR交易

### 核心需求
1. **用户绑定**：每个用户通过API Key绑定本地客户端
2. **信号隔离**：用户A的客户端只接收用户A的信号
3. **状态显示**：在交易所管理页面显示本地客户端的WebSocket连接状态
4. **一键获取**：在交易所管理页面为MT5/IBKR交易所提供"获取API Key"按钮

---

## 🎯 功能模块设计

### 模块1：API Key管理（后端已完成✅）
**文件位置**：`backend_api_python/app/routes/user.py`

已实现的API接口：
- `POST /api/user/api-key/create` - 创建API Key
- `GET /api/user/api-key/list` - 查询API Key列表
- `POST /api/user/api-key/revoke` - 停用API Key
- `DELETE /api/user/api-key/delete` - 删除API Key

### 模块2：WebSocket用户隔离（后端已完成✅）
**文件位置**：`backend_api_python/app/services/websocket_signal.py`

已实现功能：
- 客户端注册时验证API Key并存储用户信息
- 信号广播时根据`target_user_id`过滤接收者

### 模块3：本地客户端（后端已完成✅）
**文件位置**：`quantdinger-local-client/`

已实现功能：
- 用户登录界面
- 自动获取API Key
- WebSocket连接和信号接收

---

##  需要开发的新功能

### 新功能1：交易所管理页面 - API Key按钮和状态显示

#### 前端实现（QuantDinger-Vue项目）

**位置**：`D:\www\workai\QuantDinger-Vue\src\views\user\` 目录下的交易所管理页面

**需求说明**：
1. 在交易所列表中，针对MT5、IBKR类型的交易所添加操作按钮
2. 显示WebSocket连接状态（已连接/未连接）
3. 提供"获取API Key"功能（弹窗显示Key并提示下载客户端）
4. 不影响其他交易所类型（Binance、Bybit等）

#### 具体开发任务

##### 任务1.1：创建API Key管理组件
**文件**：`src/components/ApiKeyModal.vue`

**功能**：
```vue
<template>
  <div class="apikey-manager">
    <!-- API Key列表 -->
    <a-table :dataSource="apiKeys" :columns="columns">
      <!-- 表格列：密钥名称、前缀、状态、创建时间、操作 -->
    </a-table>
    
    <!-- 创建API Key按钮 -->
    <a-button type="primary" @click="showCreateModal">
      创建新API Key
    </a-button>
  </div>
</template>
```

**API调用**：
- 获取列表：`GET /api/user/api-key/list`
- 创建Key：`POST /api/user/api-key/create`
- 停用Key：`POST /api/user/api-key/revoke`

##### 任务1.2：交易所列表增强
**文件**：找到交易所管理页面（可能是`ExchangeList.vue`或`Credentials.vue`）

**修改内容**：
1. 在交易所列表表格中添加"本地客户端"列
2. 针对MT5、IBKR交易所显示：
   - WebSocket连接状态图标（绿色=已连接，灰色=未连接）
   - "获取API Key"按钮（首次创建）或"查看Key"按钮
   - "下载客户端"按钮（链接到下载页面）

**代码示例**：
```vue
<template>
  <a-table :dataSource="exchanges" :columns="columns">
    <!-- 本地客户端列 -->
    <template #localClient="{ record }">
      <!-- 只对MT5和IBKR显示 -->
      <div v-if="isLocalBroker(record.exchange_id)">
        <!-- WebSocket状态 -->
        <a-badge :status="wsStatus(record.id)" :text="wsStatusText(record.id)" />
        
        <!-- 操作按钮 -->
        <a-space>
          <a-button size="small" @click="handleGetApiKey(record)">
            {{ record.hasApiKey ? '查看Key' : '获取Key' }}
          </a-button>
          <a-button size="small" @click="handleDownloadClient">
            下载客户端
          </a-button>
        </a-space>
      </div>
      <!-- 其他交易所显示"-" -->
      <span v-else>-</span>
    </template>
  </a-table>
</template>

<script>
export default {
  methods: {
    isLocalBroker(exchangeId) {
      return ['mt5', 'ibkr'].includes(exchangeId.toLowerCase())
    },
    wsStatus(credentialId) {
      // 调用后端API获取WebSocket连接状态
      return this.wsConnections[credentialId]?.connected ? 'success' : 'default'
    },
    async handleGetApiKey(record) {
      // 调用创建或获取API Key
      const response = await this.$http.post('/api/user/api-key/create', {
        key_name: `${record.exchange_id}-${Date.now()}`,
        description: `用于${record.name}`,
        expires_days: 365
      })
      
      if (response.data.code === 1) {
        // 显示API Key弹窗
        this.showApiKeyModal(response.data.data.api_key)
      }
    }
  }
}
</script>
```

##### 任务1.3：WebSocket连接状态API
**后端新增接口**：`backend_api_python/app/routes/websocket.py`

```python
from flask import Blueprint, jsonify, g
from app.utils.auth import login_required
from app.services.websocket_signal import get_signal_hub

websocket_bp = Blueprint('websocket', __name__)

@websocket_bp.route('/client-status', methods=['GET'])
@login_required
def get_client_status():
    """
    获取当前用户本地客户端的WebSocket连接状态
    
    返回：
    {
        "code": 1,
        "data": {
            "connected": true,
            "client_id": "xxx",
            "connected_at": "2024-01-01T00:00:00",
            "last_heartbeat": "2024-01-01T00:05:00",
            "ip_address": "1.2.3.4"
        }
    }
    """
    try:
        user_id = g.user_id
        hub = get_signal_hub()
        
        # 查找该用户的所有客户端连接
        user_clients = []
        for client_id, metadata in hub.client_metadata.items():
            if metadata.get('user_id') == user_id:
                user_clients.append({
                    'client_id': client_id,
                    'username': metadata.get('username'),
                    'connected_at': metadata.get('connected_at'),
                    'last_heartbeat': metadata.get('last_heartbeat'),
                    'ip_address': metadata.get('ip_address')
                })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'total_clients': len(user_clients),
                'clients': user_clients
            }
        })
    except Exception as e:
        from app.utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"get_client_status failed: {e}")
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500
```

##### 任务1.4：API Key弹窗组件
**文件**：`src/components/ApiKeyModal.vue`

**功能**：
```vue
<template>
  <a-modal
    :visible="visible"
    title="API Key 获取成功"
    :footer="null"
    @cancel="handleClose"
    width="600px"
  >
    <a-alert
      type="warning"
      message="⚠️ 重要提示：API Key只在创建时显示一次，请妥善保存！"
      show-icon
      style="margin-bottom: 16px"
    />

    <a-form layout="vertical">
      <a-form-item label="API Key">
        <a-input-group compact>
          <a-input
            :value="apiKey"
            readonly
            style="width: calc(100% - 100px)"
          />
          <a-button @click="copyApiKey">复制</a-button>
        </a-input-group>
      </a-form-item>

      <a-divider />

      <h3>📥 下一步：下载本地客户端</h3>
      <a-steps :current="currentStep" direction="vertical" size="small">
        <a-step title="下载客户端">
          <a-button
            type="primary"
            block
            icon="download"
            @click="handleDownload"
            style="margin-top: 8px"
          >
            下载 Windows 客户端
          </a-button>
        </a-step>
        <a-step title="配置连接">
          <p>1. 运行客户端程序</p>
          <p>2. 填入云端地址：<code>{{ cloudApiUrl }}</code></p>
          <p>3. 粘贴API Key</p>
          <p>4. 点击"启动"按钮</p>
        </a-step>
        <a-step title="开始接收信号">
          <p>客户端将自动连接云端，接收您的交易信号</p>
        </a-step>
      </a-steps>
    </a-form>
  </a-modal>
</template>

<script>
export default {
  name: 'ApiKeyModal',
  data() {
    return {
      visible: false,
      apiKey: '',
      currentStep: 0,
      cloudApiUrl: 'http://39.105.150.99:8888/api',
      wsUrl: 'ws://39.105.150.99:8888/ws'
    }
  },
  methods: {
    show(apiKey) {
      this.apiKey = apiKey
      this.visible = true
      this.currentStep = 0
    },
    handleClose() {
      this.visible = false
      this.$emit('close')
    },
    copyApiKey() {
      navigator.clipboard.writeText(this.apiKey).then(() => {
        this.$message.success('API Key已复制到剪贴板')
      }).catch(() => {
        this.$message.error('复制失败')
      })
    },
    handleDownload() {
      // 下载链接（根据实际情况修改）
      const downloadUrl = '/downloads/quantdinger-client.zip'
      window.open(downloadUrl, '_blank')
    }
  }
}
</script>

<style scoped>
code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
}
</style>
```

---

### 新功能2：后端WebSocket状态查询接口

#### 任务2.1：添加WebSocket状态路由
**文件**：`backend_api_python/app/routes/websocket.py`（新建）

```python
"""
WebSocket Status API Routes

Provides endpoints for checking WebSocket client connection status.
"""

from flask import Blueprint, jsonify, g
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

websocket_bp = Blueprint('websocket', __name__)


@websocket_bp.route('/client-status', methods=['GET'])
@login_required
def get_client_status():
    """
    获取当前用户本地客户端的WebSocket连接状态
    
    返回示例：
    {
        "code": 1,
        "msg": "success",
        "data": {
            "total_clients": 1,
            "clients": [
                {
                    "client_id": "uuid-xxx",
                    "username": "trader01",
                    "connected_at": "2024-01-01T00:00:00",
                    "last_heartbeat": "2024-01-01T00:05:00",
                    "ip_address": "1.2.3.4"
                }
            ]
        }
    }
    """
    try:
        user_id = g.user_id
        
        # 获取WebSocket Hub实例
        from app.services.websocket_signal import WebSocketSignalHub
        hub = WebSocketSignalHub.get_instance()
        
        if not hub:
            return jsonify({
                'code': 1,
                'msg': 'success',
                'data': {
                    'total_clients': 0,
                    'clients': []
                }
            })
        
        # 查找该用户的所有客户端连接
        user_clients = []
        for client_id, metadata in hub.client_metadata.items():
            if metadata.get('user_id') == user_id:
                user_clients.append({
                    'client_id': client_id,
                    'username': metadata.get('username'),
                    'connected_at': metadata.get('connected_at'),
                    'last_heartbeat': metadata.get('last_heartbeat'),
                    'ip_address': metadata.get('ip_address')
                })
        
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': {
                'total_clients': len(user_clients),
                'clients': user_clients
            }
        })
    except Exception as e:
        logger.error(f"get_client_status failed: {e}")
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500


@websocket_bp.route('/is-connected', methods=['GET'])
@login_required
def is_client_connected():
    """
    简化的连接状态检查（只返回是否连接）
    
    返回示例：
    {
        "code": 1,
        "data": {
            "connected": true,
            "client_count": 1
        }
    }
    """
    try:
        user_id = g.user_id
        
        from app.services.websocket_signal import WebSocketSignalHub
        hub = WebSocketSignalHub.get_instance()
        
        if not hub:
            return jsonify({
                'code': 1,
                'data': {
                    'connected': False,
                    'client_count': 0
                }
            })
        
        # 统计该用户的活跃连接数
        connected_count = sum(
            1 for metadata in hub.client_metadata.values()
            if metadata.get('user_id') == user_id
        )
        
        return jsonify({
            'code': 1,
            'data': {
                'connected': connected_count > 0,
                'client_count': connected_count
            }
        })
    except Exception as e:
        logger.error(f"is_client_connected failed: {e}")
        return jsonify({'code': 0, 'msg': str(e), 'data': None}), 500
```

#### 任务2.2：注册路由
**文件**：`backend_api_python/app/__init__.py`

在适当位置添加：
```python
# 注册WebSocket状态路由
from app.routes.websocket import websocket_bp
app.register_blueprint(websocket_bp, url_prefix='/api/websocket')
```

---

### 新功能3：前端路由和菜单

#### 任务3.1：找到交易所管理页面
**步骤**：
```bash
cd D:\www\workai\QuantDinger-Vue

# 搜索交易所管理相关组件
grep -r "交易所" src/views/
# 或搜索exchange相关
grep -r "exchange" src/views/ --include="*.vue"
# 或搜索credential相关
grep -r "credential" src/views/ --include="*.vue"
```

**可能的文件位置**：
- `src/views/user/ExchangeManage.vue`
- `src/views/user/Credentials.vue`
- `src/views/user/ExchangeList.vue`
- `src/views/account/ExchangeAccount.vue`

#### 任务3.2：修改交易所管理页面
找到交易所管理页面后，添加以下功能：

**完整修改示例**：

```vue
<template>
  <div class="exchange-manage">
    <!-- 现有表格 -->
    <a-table
      :dataSource="exchangeList"
      :columns="columns"
      :loading="loading"
      rowKey="id"
    >
      <!-- 本地客户端列 -->
      <template #localClient="{ record }">
        <div v-if="isLocalBroker(record.exchange_id)">
          <!-- WebSocket状态 -->
          <div style="margin-bottom: 8px">
            <a-badge
              :status="getClientStatus(record.id) ? 'success' : 'default'"
              :text="getClientStatus(record.id) ? '已连接' : '未连接'"
            />
          </div>
          
          <!-- 操作按钮 -->
          <a-space>
            <a-button
              size="small"
              type="primary"
              icon="key"
              @click="handleGetApiKey(record)"
            >
              {{ hasApiKey(record) ? '查看Key' : '获取Key' }}
            </a-button>
            <a-button
              size="small"
              icon="download"
              @click="handleDownloadClient"
            >
              下载客户端
            </a-button>
          </a-space>
        </div>
        <span v-else>-</span>
      </template>
    </a-table>
    
    <!-- API Key弹窗 -->
    <api-key-modal ref="apiKeyModal" />
  </div>
</template>

<script>
import ApiKeyModal from '@/components/ApiKeyModal.vue'

export default {
  name: 'ExchangeManage',
  components: {
    ApiKeyModal
  },
  data() {
    return {
      loading: false,
      exchangeList: [],
      wsConnected: false,
      apiKeyList: []
    }
  },
  computed: {
    columns() {
      return [
        // ... 现有列
        {
          title: '本地客户端',
          key: 'localClient',
          width: 250,
          scopedSlots: { customRender: 'localClient' }
        }
      ]
    }
  },
  mounted() {
    this.fetchExchangeList()
    this.fetchApiKeyList()
    this.checkWsStatus()
    
    // 每30秒刷新一次WebSocket状态
    this.wsStatusTimer = setInterval(() => {
      this.checkWsStatus()
    }, 30000)
  },
  beforeDestroy() {
    if (this.wsStatusTimer) {
      clearInterval(this.wsStatusTimer)
    }
  },
  methods: {
    // 判断是否为本地交易所
    isLocalBroker(exchangeId) {
      return ['mt5', 'ibkr'].includes(exchangeId?.toLowerCase())
    },
    
    // 获取交易所列表
    async fetchExchangeList() {
      this.loading = true
      try {
        const response = await this.$http.get('/api/credentials/list')
        if (response.data.code === 1) {
          this.exchangeList = response.data.data.list || []
        }
      } catch (error) {
        this.$message.error('获取交易所列表失败')
      } finally {
        this.loading = false
      }
    },
    
    // 获取API Key列表
    async fetchApiKeyList() {
      try {
        const response = await this.$http.get('/api/user/api-key/list')
        if (response.data.code === 1) {
          this.apiKeyList = response.data.data.keys || []
        }
      } catch (error) {
        console.error('获取API Key列表失败', error)
      }
    },
    
    // 检查WebSocket状态
    async checkWsStatus() {
      try {
        const response = await this.$http.get('/api/websocket/is-connected')
        if (response.data.code === 1) {
          this.wsConnected = response.data.data.connected
        }
      } catch (error) {
        console.error('获取WebSocket状态失败', error)
      }
    },
    
    // 判断交易所是否有API Key
    hasApiKey(record) {
      return this.apiKeyList.length > 0
    },
    
    // 获取客户端状态
    getClientStatus(credentialId) {
      // 简化版：只要有连接就显示已连接
      return this.wsConnected
    },
    
    // 获取API Key
    async handleGetApiKey(record) {
      try {
        const response = await this.$http.post('/api/user/api-key/create', {
          key_name: `${record.exchange_id || 'local'}-${Date.now()}`,
          description: `用于${record.name || '本地交易'}`,
          expires_days: 365
        })
        
        if (response.data.code === 1) {
          this.$refs.apiKeyModal.show(response.data.data.api_key)
          this.fetchApiKeyList()
        } else {
          this.$message.error(response.data.msg || '创建失败')
        }
      } catch (error) {
        this.$message.error('网络错误')
      }
    },
    
    // 下载客户端
    handleDownloadClient() {
      // 下载链接（根据实际情况修改）
      const downloadUrl = '/downloads/quantdinger-client.zip'
      window.open(downloadUrl, '_blank')
    }
  }
}
</script>
```

#### 任务3.3：在交易所管理页面引入组件
```javascript
import ApiKeyModal from '@/components/ApiKeyModal.vue'

export default {
  components: {
    ApiKeyModal
  },
  // ...
}
```

在`<template>`中添加：
```vue
<api-key-modal ref="apiKeyModal" />
```

---

##  详细开发步骤

### 阶段1：后端开发（1-2小时）

#### 步骤1：创建WebSocket状态查询接口
```bash
# 在Windows PowerShell中执行
cd D:\www\workai\QuantDinger

# 创建新文件
New-Item -Path "backend_api_python\app\routes\websocket.py" -ItemType File -Force

# 编辑文件，添加任务2.1中的代码
```

#### 步骤2：注册路由
编辑 `backend_api_python/app/__init__.py`：
```python
# 找到路由注册区域，添加：
from app.routes.websocket import websocket_bp
app.register_blueprint(websocket_bp, url_prefix='/api/websocket')
```

#### 步骤3：测试后端API
```bash
cd backend_api_python
python run.py

# 在另一个终端测试（需要登录token）
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5000/api/websocket/client-status
```

---

### 阶段2：前端开发（3-4小时）

#### 步骤1：找到交易所管理页面
```bash
cd D:\www\workai\QuantDinger-Vue

# 搜索交易所管理相关组件
Get-ChildItem -Recurse -Filter "*.vue" | Select-String "交易所"
# 或
Get-ChildItem -Recurse -Filter "*.vue" | Select-String "exchange"
```

#### 步骤2：创建API Key弹窗组件
```bash
cd D:\www\workai\QuantDinger-Vue
New-Item -Path "src\components\ApiKeyModal.vue" -ItemType File -Force
```

将任务1.4中的完整代码粘贴到文件中。

#### 步骤3：修改交易所管理页面
找到交易所管理页面后：
1. 添加"本地客户端"列
2. 添加WebSocket状态显示
3. 添加"获取API Key"按钮
4. 引入ApiKeyModal组件

参考任务3.2中的完整代码示例。

#### 步骤4：本地测试
```bash
cd D:\www\workai\QuantDinger-Vue
npm run serve
```

访问 `http://localhost:8080` 查看效果。

---

### 阶段3：测试和调试（1-2小时）

#### 测试清单：
1. ✅ MT5交易所显示"获取API Key"按钮
2. ✅ IBKR交易所显示"获取API Key"按钮
3. ✅ Binance交易所不显示该按钮
4. ✅ 点击"获取Key"后正确创建并显示API Key
5. ✅ API Key可以复制到剪贴板
6. ✅ 下载客户端按钮正常工作
7. ✅ WebSocket状态正确显示（已连接/未连接）
8. ✅ 本地客户端连接后，状态更新为"已连接"

---

##  交付物清单

### 后端修改
- [ ] `backend_api_python/app/routes/websocket.py` - WebSocket状态查询接口（新建）
- [ ] `backend_api_python/app/__init__.py` - 注册新路由（修改）

### 前端修改
- [ ] `src/components/ApiKeyModal.vue` - API Key弹窗组件（新建）
- [ ] `src/views/user/ExchangeManage.vue` - 交易所管理页面（修改，文件名可能不同）
- [ ] `src/router/modules/user.js` - 路由配置（可选）

---

## ⚠️ 注意事项

1. **安全性**：
   - API Key只在创建时显示一次
   - 前端不存储完整API Key
   - 使用HTTPS/WSS加密传输

2. **兼容性**：
   - 不影响现有交易所功能
   - 只对MT5、IBKR显示本地客户端功能
   - 向后兼容旧版本

3. **用户体验**：
   - 提供清晰的引导流程
   - 复制按钮提升易用性
   - 状态反馈及时准确

4. **部署**：
   - 前端需要构建后部署到99服务器
   - 后端需要重启服务
   - 客户端下载链接需要配置

---

##  验收标准

1. 用户在交易所管理页面看到MT5/IBKR的"获取API Key"按钮
2. 点击后成功创建API Key并显示完整Key
3. 可以一键复制API Key
4. 显示下载客户端的引导
5. WebSocket连接状态正确显示
6. 其他交易所类型不受影响
7. 本地客户端可以成功连接并接收信号

---

##  常见问题

### Q1: 找不到交易所管理页面？
**解决方案**：
```bash
# 搜索所有包含"交易所"的Vue文件
Get-ChildItem -Recurse -Filter "*.vue" | Select-String "交易所"

# 搜索所有包含"credential"的Vue文件
Get-ChildItem -Recurse -Filter "*.vue" | Select-String "credential"

# 查看路由配置
Get-Content src\router\modules\user.js
```

### Q2: WebSocket状态不更新？
**解决方案**：
- 检查后端服务是否正常运行
- 检查WebSocket Hub是否正确初始化
- 查看浏览器控制台是否有错误
- 确认API接口返回正确数据

### Q3: API Key创建失败？
**解决方案**：
- 检查用户是否已登录
- 检查数据库中`qd_api_keys`表是否存在
- 查看后端日志是否有错误信息
- 确认`g.user_id`正确获取

### Q4: 前端构建失败？
**解决方案**：
```bash
# 清除缓存并重新安装依赖
Remove-Item -Recurse -Force node_modules
npm install

# 重新构建
npm run build
```

---

**预计开发时间**：6-8小时  
**难度等级**：⭐⭐⭐（中等）  
**关键路径**：找到交易所管理页面 → 修改表格 → 创建弹窗组件 → 后端API → 测试

---

## 📞 联系方式

如遇问题，请查阅：
- 后端API文档：`backend_api_python/`
- 前端项目：`D:\www\workai\QuantDinger-Vue`
- 本地客户端：`quantdinger-local-client/`

**计划创建时间**：2026-05-11
