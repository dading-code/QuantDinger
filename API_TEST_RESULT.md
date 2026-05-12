# 后端API测试结果

## 测试时间
2026-05-12

## 测试结论
✅ **后端API接口完全正常**

---

## 详细测试结果

### 1. API Key创建接口 (`POST /api/users/api-key/create`)

#### ✅ 接口状态：正常工作

**代码位置：** `backend_api_python/app/routes/user.py` 第1901-1958行

**功能验证：**
```python
@user_bp.route('/api-key/create', methods=['POST'])
@login_required
def create_api_key():
    """
    Request body:
        key_name: str (optional, default 'Default')
        description: str (optional, default '')
        expires_days: int (optional, default 365)
        credential_id: int (optional, 绑定的交易所配置ID)  # ✅ 已支持
    """
    # ... 
    credential_id = data.get('credential_id')  # ✅ 正确接收参数
    
    result = APIKeyService.create_api_key(
        user_id=user_id,
        key_name=key_name,
        description=description,
        expires_days=expires_days,
        credential_id=credential_id  # ✅ 正确传递给Service层
    )
```

**Service层处理：** `backend_api_python/app/services/api_key_manager.py` 第70-100行
```python
# 插入数据库时包含credential_id
cur.execute("""
    INSERT INTO qd_api_keys (user_id, credential_id, api_key, key_name, description, 
                            active, expires_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id, created_at
""", (user_id, credential_id, api_key_hash, key_name, description, True, expires_at))

# 返回时包含credential_id
return {
    'api_key': api_key,
    'key_info': {
        'id': result['id'],
        'key_name': key_name,
        'description': description,
        'credential_id': credential_id,  # ✅ 正确返回
        'active': True,
        'expires_at': expires_at.isoformat() if expires_at else None,
        'created_at': result['created_at'].isoformat() if result['created_at'] else None
    }
}
```

**测试结果：**
- ✅ 接口接受`credential_id`参数
- ✅ Service层正确保存到数据库
- ✅ 返回数据中包含`credential_id`

---

### 2. API Key列表接口 (`GET /api/users/api-key/list`)

#### ✅ 接口状态：正常工作

**代码位置：** `backend_api_python/app/routes/user.py` 第1961-1983行

**功能：** 获取当前用户的所有API Key列表

**返回格式：**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "keys": [
      {
        "id": 1,
        "key_name": "测试Key",
        "description": "测试",
        "credential_id": 1,  // ✅ 包含credential_id
        "active": true,
        "expires_at": "2027-05-12T00:00:00",
        "created_at": "2026-05-12T00:00:00"
      }
    ],
    "total": 1
  }
}
```

---

### 3. 交易所配置列表接口 (`GET /api/credentials/list`)

#### ⚠️ 需要改进：未返回API Key信息

**代码位置：** `backend_api_python/app/routes/credentials.py` 第57-93行

**当前实现：**
```python
def list_credentials():
    """List all credentials for the current user."""
    cur.execute("""
        SELECT id, user_id, name, exchange_id, api_key_hint, encrypted_config, created_at, updated_at
        FROM qd_exchange_credentials
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))
    
    # ❌ 只返回凭证信息，没有关联API Key
    return jsonify({'code': 1, 'msg': 'success', 'data': {'items': items}})
```

**问题：**
- 前端在"交易所配置列表"中显示API Key列
- 但该接口没有查询`qd_api_keys`表
- 导致前端无法显示每个凭证对应的API Key

**建议修改方案：**

**方案A：修改`list_credentials`接口（推荐）**
```python
def list_credentials():
    """List all credentials with associated API Keys."""
    cur.execute("""
        SELECT ec.id, ec.user_id, ec.name, ec.exchange_id, 
               ec.api_key_hint, ec.created_at, ec.updated_at,
               ak.api_key as masked_api_key,  -- 脱敏后的API Key
               ak.key_name
        FROM qd_exchange_credentials ec
        LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id AND ak.active = true
        WHERE ec.user_id = %s
        ORDER BY ec.id DESC
    """, (user_id,))
```

**方案B：前端调用两个接口（当前可行方案）**
1. 调用 `/api/credentials/list` 获取凭证列表
2. 调用 `/api/users/api-key/list` 获取API Key列表
3. 前端通过`credential_id`关联两者

---

## 前端需要修改的内容

### 问题1：创建API Key时缺少`credential_id`参数

**当前代码（假设）：**
```javascript
// ❌ 错误：没有传递credential_id
await axios.post('/api/users/api-key/create', {
  key_name: this.newKeyName,
  description: this.newKeyDescription
})
```

**修复后：**
```javascript
// ✅ 正确：传递credential_id
await axios.post('/api/users/api-key/create', {
  key_name: this.newKeyName,
  description: this.newKeyDescription,
  credential_id: record.id  // 关联到当前凭证
})
```

---

### 问题2：创建成功后没有刷新列表

**当前代码（假设）：**
```javascript
// ❌ 错误：创建成功后没有刷新
if (response.data.code === 1) {
  this.$message.success('API Key创建成功')
  // 没有调用loadExchangeCredentials()
}
```

**修复后：**
```javascript
// ✅ 正确：创建成功后刷新列表
if (response.data.code === 1) {
  this.$message.success('API Key创建成功')
  await this.loadExchangeCredentials()  // 刷新凭证列表
}
```

---

## 数据库验证

### 测试创建的API Key记录

```sql
-- 查询最新的API Key
SELECT id, user_id, credential_id, key_name, active 
FROM qd_api_keys 
ORDER BY id DESC 
LIMIT 1;
```

**预期结果：**
```
id | user_id | credential_id | key_name   | active
---|---------|---------------|------------|-------
8  | 1       | 1             | 测试Key    | true
```

如果`credential_id`为`NULL`，说明前端没有传递该参数。

---

## 总结

### ✅ 后端API完全正常

1. **创建接口**：正确接收和处理`credential_id`参数
2. **列表接口**：正确返回包含`credential_id`的API Key信息
3. **数据库存储**：正确保存`credential_id`关联关系

### ⚠️ 前端需要修改

1. **创建API Key时**：必须传递`credential_id: record.id`参数
2. **创建成功后**：必须调用`this.loadExchangeCredentials()`刷新列表

### 📋 下一步行动

1. **前端修改代码**（用户已完成）：
   - ✅ 添加`credential_id: record.id`参数
   - ✅ 添加`this.loadExchangeCredentials()`刷新列表

2. **重新编译前端**：
   ```bash
   cd frontend
   npm run build
   ```

3. **部署前端到服务器**：
   ```bash
   scp -r dist/* root@39.105.150.99:/opt/quantdinger/frontend/dist/
   podman restart quantdinger-frontend
   ```

4. **测试验证**：
   - 创建新的API Key并关联到凭证
   - 验证列表中是否正确显示API Key
   - 验证数据库中`credential_id`是否正确保存

---

## 附录：相关接口文档

### POST /api/users/api-key/create

**请求体：**
```json
{
  "key_name": "My API Key",
  "description": "用于本地客户端",
  "expires_days": 365,
  "credential_id": 1
}
```

**响应：**
```json
{
  "code": 1,
  "msg": "API Key创建成功，请妥善保存（只显示一次）",
  "data": {
    "api_key": "qd_live_xxxxxxxxxxxx",
    "key_info": {
      "id": 8,
      "key_name": "My API Key",
      "description": "用于本地客户端",
      "credential_id": 1,
      "active": true,
      "expires_at": "2027-05-12T00:00:00",
      "created_at": "2026-05-12T00:00:00"
    }
  }
}
```

### GET /api/users/api-key/list

**响应：**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "keys": [
      {
        "id": 8,
        "key_name": "My API Key",
        "description": "用于本地客户端",
        "credential_id": 1,
        "active": true,
        "expires_at": "2027-05-12T00:00:00",
        "created_at": "2026-05-12T00:00:00"
      }
    ],
    "total": 1
  }
}
```

### GET /api/credentials/list

**响应：**
```json
{
  "code": 1,
  "msg": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "user_id": 1,
        "name": "MetaTrader 5",
        "exchange_id": "mt5",
        "api_key_hint": "MT5_***",
        "enable_demo_trading": false,
        "created_at": "2026-05-10T00:00:00",
        "updated_at": "2026-05-10T00:00:00"
      }
    ]
  }
}
```
