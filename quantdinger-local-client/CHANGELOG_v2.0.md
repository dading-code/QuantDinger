# QuantDinger 本地客户端 v2.0 - API Key模式

## 📋 版本更新说明

### ✅ 主要变更

**从"登录模式"改为"API Key模式"**

---

## 🔴 之前的问题（v1.0）

### Session冲突
- ❌ 桌面客户端和网页端使用相同的JWT Token认证
- ❌ 当桌面客户端登录时，会生成新Token，导致网页端被踢出
- ❌ 用户需要在两个地方分别登录，体验差
- ❌ 多端无法共存

---

## ✅ 新的解决方案（v2.0）

### API Key认证
- ✅ **用户在Web管理后台获取API Key**
  - 路径：个人中心 → 交易所配置 → 获取Key按钮
  - API Key只在创建时显示一次，需妥善保存
  
- ✅ **桌面客户端只需配置API Key**
  - 无需用户名/密码登录
  - 直接粘贴API Key到客户端
  - 避免Session冲突
  
- ✅ **多端共存**
  - 网页端可以正常使用
  - 桌面客户端可以同时运行
  - 互不干扰

---

## 🎯 使用方法

### 步骤1：在Web后台获取API Key

1. 登录QuantDinger Web管理后台
2. 进入**个人中心**
3. 切换到**交易所配置**标签页
4. 找到MT5或IBKR交易所账户
5. 点击**"获取Key"**按钮
6. 复制显示的API Key（只显示一次！）

### 步骤2：配置桌面客户端

1. 打开QuantDinger本地客户端
2. 填入以下信息：
   - **云端地址**：`http://39.105.150.99:8888/api`（默认已填）
   - **WS 地址**：`ws://39.105.150.99:8888/ws`（默认已填）
   - **API 密钥**：粘贴从Web后台复制的API Key
   - **券商类型**：选择 `simulation` / `mt5` / `ibkr`
3. 点击**"💾 保存配置"**

### 步骤3：启动客户端

1. 点击**"▶ 启动"**按钮
2. 客户端将自动连接WebSocket
3. 开始接收交易信号并在本地执行

---

## 📊 UI界面变化

### v1.0（旧版）
```
┌─────────────────────────────────────┐
│ 配置设置                             │
├─────────────────────────────────────┤
│ 云端地址: [___________________]     │
│ 用户名:   [___________________]     │
│ 密码:     [___________________]     │
│          [🔑 登录并获取API Key]     │
│ ─────────────────────────────────── │
│ API 密钥: [___________________] 🔒  │
│ WS 地址:  [___________________]     │
│ 券商类型: [simulation ▼] [💾 保存]  │
└─────────────────────────────────────┘
```

### v2.0（新版）
```
┌─────────────────────────────────────┐
│ 配置设置                             │
├─────────────────────────────────────┤
│ 云端地址: [___________________]     │
│ WS 地址:  [___________________]     │
│ API 密钥: [___________________]     │
│ 💡 提示：请在Web管理后台获取API Key  │
│ ─────────────────────────────────── │
│ 券商类型: [simulation ▼] [💾 保存]  │
└─────────────────────────────────────┘
```

**主要变化**：
- ❌ 移除：用户名输入框
- ❌ 移除：密码输入框
- ❌ 移除：登录按钮
- ✅ 简化：API Key可直接编辑（不再只读）
- ✅ 新增：帮助提示文本

---

## 🔧 技术实现

### 代码修改

#### 1. 移除CloudAPIClient依赖
```python
# 删除导入
from src.core.api_client import CloudAPIClient  # ❌ 已删除

# 删除初始化
self.cloud_api: Optional[CloudAPIClient] = None  # ❌ 已删除
```

#### 2. 简化配置管理
```python
# _load_config() - 只加载必要配置
def _load_config(self):
    self.api_key_var.set(self.config_mgr.get('api_key', ''))
    self.cloud_url_var.set(self.config_mgr.get('cloud_api_url', '...'))
    self.ws_url_var.set(self.config_mgr.get('cloud_url', '...'))
    self.broker_var.set(self.config_mgr.get('broker', 'simulation'))

# _save_config() - 只保存必要配置
def _save_config(self):
    self.config_mgr.set('api_key', self.api_key_var.get())
    self.config_mgr.set('cloud_api_url', self.cloud_url_var.get())
    self.config_mgr.set('cloud_url', self.ws_url_var.get())
    self.config_mgr.set('broker', self.broker_var.get())
```

#### 3. 删除登录方法
```python
# ❌ 完全删除 _login_and_get_key() 方法（79行代码）
```

#### 4. 更新错误提示
```python
# 修改前
if not api_key:
    messagebox.showerror("错误", "请先登录并获取 API 密钥")

# 修改后
if not api_key:
    messagebox.showerror("错误", "请先在Web管理后台获取API Key并填入配置")
```

---

## 📝 配置文件变化

### config.json（v1.0）
```json
{
  "username": "testuser",
  "password": "encrypted_password",
  "api_key": "qd_ak_xxxx",
  "cloud_api_url": "http://39.105.150.99:8888/api",
  "cloud_url": "ws://39.105.150.99:8888/ws",
  "broker": "simulation"
}
```

### config.json（v2.0）
```json
{
  "api_key": "qd_ak_xxxx",
  "cloud_api_url": "http://39.105.150.99:8888/api",
  "cloud_url": "ws://39.105.150.99:8888/ws",
  "broker": "simulation"
}
```

**注意**：升级后，旧的`username`和`password`字段将被忽略。

---

## 🚀 部署建议

### 对于现有用户

如果用户已经在使用v1.0版本：

1. **备份配置文件**：`config.json`
2. **下载新版本**：覆盖安装v2.0
3. **重新配置**：
   - 从Web后台获取API Key
   - 填入新的配置界面
   - 保存并启动

### 对于新用户

直接使用v2.0版本，按照上述"使用方法"配置即可。

---

## ✅ 优势总结

| 特性 | v1.0（登录模式） | v2.0（API Key模式） |
|------|-----------------|-------------------|
| **Session冲突** | ❌ 存在 | ✅ 无冲突 |
| **多端共存** | ❌ 不支持 | ✅ 支持 |
| **用户体验** | ⚠️ 需要两次登录 | ✅ 一次配置即可 |
| **安全性** | ⚠️ 密码存储风险 | ✅ 只存储API Key |
| **代码复杂度** | ⚠️ 较复杂 | ✅ 更简洁 |
| **维护成本** | ⚠️ 较高 | ✅ 更低 |

---

## 📞 技术支持

如有问题，请查看：
- Web管理后台：http://39.105.150.99:8888
- API文档：`BACKEND_API_DOCUMENTATION.md`
- 开发计划：`DEVELOPMENT_PLAN_APIKEY_FEATURE.md`

---

**版本**: v2.0  
**更新日期**: 2026-05-11  
**架构决策**: API Key替代登录，解决多端Session冲突
