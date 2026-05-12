# MT5/IBKR 本地执行架构改造完成报告

## 📋 改造概述

本次改造完成了从"云端直接执行 MT5/IBKR 订单"到"云端推送信号 + 本地客户端执行"的完整架构切换。

### 核心设计原则

1. **两阶段操作**：确保云端和本地数据一致性
2. **重试机制**：防止网络波动导致的数据丢失
3. **幂等性**：防止重复执行和重复上报
4. **防死循环**：限制最大重试次数，使用指数退避策略

---

## 🏗️ 架构流程

### 完整的交易流程

```
┌─────────────────────────────────────────────────────────────┐
│                     云端 (Cloud)                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 策略生成信号                                             │
│     ↓                                                       │
│  2. trading_executor._execute_exchange_order()              │
│     ↓                                                       │
│  3. _enqueue_pending_order() → 插入 qd_pending_orders       │
│     状态: 'pending'                                         │
│     ↓                                                       │
│  4. pending_order_worker 轮询待处理订单                      │
│     ↓                                                       │
│  5. 检测到 exchange_id = 'mt5' 或 'ibkr'                    │
│     ↓                                                       │
│  6. _push_signal_to_local_client()                          │
│     ├─ 通过 WebSocket 推送信号到本地客户端                   │
│     ├─ 重试最多 3 次（指数退避：2s, 4s, 8s）                │
│     └─ 更新订单状态: 'signal_pushed'                        │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │ WebSocket (实时信号)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              本地客户端 (Local Client)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  7. 接收 WebSocket 信号                                      │
│     ↓                                                       │
│  8. 账号一致性校验 ✅                                        │
│     ├─ 对比云端配置的 mt5_login vs 本地实际登录账号          │
│     └─ 不匹配则拒绝执行                                      │
│     ↓                                                       │
│  9. 本地风险管理检查                                         │
│     ├─ 最大仓位限制                                          │
│     ├─ 最大亏损限制                                          │
│     └─ 品种白名单/黑名单                                     │
│     ↓                                                       │
│  10. 执行 MT5/IBKR 订单                                     │
│      ├─ 调用本地 MT5 API / IBKR API                         │
│      └─ 获取执行结果（order_id, filled, price）             │
│      ↓                                                      │
│  11. _report_execution_result()                             │
│      ├─ HTTP POST /api/local-client/report-execution        │
│      ├─ 重试最多 3 次（指数退避：2s, 4s, 8s）               │
│      └─ 上报成功/失败结果                                    │
│                                                             │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP POST (执行结果)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                  云端 (Cloud) - 结果处理                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  12. local_client.report_execution()                        │
│      ├─ 验证 API Key 和用户身份                             │
│      ├─ 更新 qd_pending_orders 状态: 'executed' / 'failed'  │
│      ├─ 记录交易到 qd_trades                                │
│      ├─ 更新持仓 qd_strategy_positions                      │
│      └─ 追加策略日志                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 修改的文件清单

### 后端（云端）

#### 1. `backend_api_python/app/services/pending_order_worker.py`

**修改内容：**
- Line 1-11: 更新模块注释，说明新的架构
- Line 873-1016: 新增 `_push_signal_to_local_client()` 方法
  - 推送 MT5/IBKR 信号到本地客户端
  - 重试机制：最多 3 次，指数退避（2s, 4s, 8s）
  - 检查是否有活跃的本地客户端连接
  - 更新订单状态为 'signal_pushed'
- Line 1026-1065: 修改 MT5/IBKR 检测逻辑
  - 不再调用 `_execute_mt5_order()` / `_execute_ibkr_order()`
  - 改为调用 `_push_signal_to_local_client()`

**关键代码片段：**

```python
def _push_signal_to_local_client(self, ...):
    """
    Push MT5/IBKR signal to local client via WebSocket.
    
    Two-phase operation:
    Phase 1: Mark order as 'signal_pushed' (waiting for local execution)
    Phase 2: Local client executes and reports back via API
    
    Retry mechanism:
    - If WebSocket push fails, retry up to MAX_RETRY times with exponential backoff
    - If timeout (no response from local client), mark as failed
    """
    MAX_RETRY = 3
    RETRY_DELAY_BASE = 2  # seconds
    
    # ... 准备信号数据 ...
    
    for attempt in range(1, MAX_RETRY + 1):
        try:
            # 检查是否有活跃的本地客户端
            active_clients = sum(
                1 for meta in hub.client_metadata.values()
                if meta.get('user_id') == user_id
            )
            
            if active_clients == 0:
                logger.warning(f"No active local clients for user {user_id}")
                # 等待后重试
                wait_time = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                time.sleep(wait_time)
                continue
            
            # 推送信号
            asyncio.run(hub.broadcast_signal(signal_data, target_user_id=user_id))
            success = True
            break
            
        except Exception as e:
            # 等待后重试
            if attempt < MAX_RETRY:
                wait_time = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                time.sleep(wait_time)
    
    if success:
        # Phase 1: 标记为 'signal_pushed'
        self._mark_sent(...)
    else:
        # 所有重试失败
        self._mark_failed(...)
```

#### 2. `backend_api_python/app/routes/local_client.py` (新建)

**功能：**
- 提供 `/api/local-client/report-execution` API 端点
- 接收本地客户端的执行结果上报
- 验证 API Key 和用户身份
- 更新待处理订单状态
- 记录交易和更新持仓

**关键代码片段：**

```python
@local_client_bp.route('/report-execution', methods=['POST'])
def report_execution():
    """
    Local client reports execution result for a pending order.
    
    Request body:
    {
        "api_key": "qd_xxx...",
        "pending_order_id": 123,
        "success": true/false,
        "order_id": "MT5-12345",  # If success
        "filled": 0.1,
        "price": 1.0800,
        "error": "error message"  # If failed
    }
    """
    # 1. 验证 API Key
    user_info = APIKeyService.validate_api_key(api_key)
    
    # 2. 根据 success 字段分别处理
    if success:
        _update_pending_order_executed(...)
    else:
        _update_pending_order_failed(...)
    
    return jsonify({'code': 1, 'msg': 'ok'})
```

#### 3. `backend_api_python/app/routes/__init__.py`

**修改内容：**
- Line 32: 导入 `local_client_bp`
- Line 56: 注册蓝图 `app.register_blueprint(local_client_bp, url_prefix='/api/local-client')`

### 前端（本地客户端）

#### 4. `scripts/local_trade_executor.py`

**修改内容：**
- Line 175-252: 修改 `_handle_trading_signal()` 方法
  - 提取 `pending_order_id` 从信号数据
  - 执行成功后调用 `_report_execution_result()`
  - 执行失败后也调用 `_report_execution_result()`
  - 异常时也调用 `_report_execution_result()`
- Line 441-503: 新增 `_report_execution_result()` 方法
  - HTTP POST 上报执行结果到云端
  - 重试机制：最多 3 次，指数退避（2s, 4s, 8s）
  - 防止无限循环

**关键代码片段：**

```python
async def _report_execution_result(
    self,
    pending_order_id: int,
    success: bool,
    order_id: str = None,
    filled: float = None,
    price: float = None,
    error: str = None,
    max_retries: int = 3,
):
    """
    Report execution result back to cloud.
    
    Two-phase operation:
    Phase 2: Local client reports execution result after executing the order.
    
    Retry mechanism:
    - If HTTP request fails, retry up to max_retries times with exponential backoff
    - Prevents infinite loops by limiting retries
    """
    import aiohttp
    
    report_data = {
        'api_key': self.api_key,
        'pending_order_id': pending_order_id,
        'success': success,
    }
    
    if success:
        report_data['order_id'] = order_id or ''
        report_data['filled'] = filled or 0.0
        report_data['price'] = price or 0.0
    else:
        report_data['error'] = error or 'Unknown error'
    
    cloud_url = self.cloud_url.replace('ws://', 'http://').replace('wss://', 'https://')
    report_url = f"{cloud_url}/api/local-client/report-execution"
    
    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(report_url, json=report_data, timeout=10) as response:
                    result = await response.json()
                    
                    if response.status == 200 and result.get('code') == 1:
                        print(f"[Report] ✓ Execution result reported successfully")
                        return True
                        
        except Exception as e:
            print(f"[Report] ✗ Failed to report (attempt {attempt}/{max_retries}): {e}")
        
        # 指数退避
        if attempt < max_retries:
            wait_time = 2 * (2 ** (attempt - 1))  # 2s, 4s, 8s
            await asyncio.sleep(wait_time)
    
    return False
```

#### 5. `quantdinger-local-client/requirements.txt`

**修改内容：**
- Line 5: 添加 `aiohttp>=3.9.0` 依赖（用于异步 HTTP 请求）

---

## 🔒 安全特性

### 1. API Key 认证

- 本地客户端上报执行结果时必须提供有效的 API Key
- 云端验证 API Key 并确认用户身份
- 防止未授权的上报

### 2. 账号一致性校验

- 本地客户端连接时上报实际登录的券商账号
- 云端对比配置中的期望账号
- 不匹配则拒绝推送信号

### 3. 所有权验证

- 云端在更新订单状态前验证 `user_id` 和 `pending_order_id` 的所有权
- 防止跨用户篡改订单

---

## 🔄 重试机制详解

### 云端推送信号重试

```python
MAX_RETRY = 3
RETRY_DELAY_BASE = 2  # seconds

for attempt in range(1, MAX_RETRY + 1):
    try:
        # 推送信号
        asyncio.run(hub.broadcast_signal(...))
        success = True
        break
    except Exception as e:
        if attempt < MAX_RETRY:
            wait_time = RETRY_DELAY_BASE * (2 ** (attempt - 1))
            # 2^0 * 2 = 2s
            # 2^1 * 2 = 4s
            # 2^2 * 2 = 8s
            time.sleep(wait_time)
```

**重试时间线：**
- Attempt 1: 立即执行
- Attempt 2: 等待 2s 后重试
- Attempt 3: 等待 4s 后重试
- 如果全部失败：标记为失败，总耗时约 6s

### 本地客户端上报重试

```python
max_retries = 3

for attempt in range(1, max_retries + 1):
    try:
        async with session.post(report_url, json=report_data, timeout=10):
            if success:
                return True
    except Exception as e:
        if attempt < max_retries:
            wait_time = 2 * (2 ** (attempt - 1))
            # 2s, 4s, 8s
            await asyncio.sleep(wait_time)
```

**重试时间线：**
- Attempt 1: 立即执行
- Attempt 2: 等待 2s 后重试
- Attempt 3: 等待 4s 后重试
- 如果全部失败：返回 False，总耗时约 6s

### 防止死循环的措施

1. **最大重试次数限制**：`MAX_RETRY = 3`
2. **指数退避**：每次重试等待时间翻倍
3. **超时保护**：HTTP 请求设置 10s 超时
4. **明确的退出条件**：达到最大重试次数后停止

---

## 📊 数据一致性保证

### 两阶段操作流程

#### Phase 1: 云端创建待处理订单

```sql
-- 插入待处理订单
INSERT INTO qd_pending_orders (
    strategy_id, symbol, signal_type, amount, price, 
    status, execution_mode, created_at
) VALUES (
    123, 'EURUSD', 'open_long', 0.1, 1.0800,
    'pending', 'live', NOW()
);

-- pending_order_worker 处理后更新状态
UPDATE qd_pending_orders
SET status = 'signal_pushed',
    note = 'signal_pushed_to_local_client_mt5',
    updated_at = NOW()
WHERE id = 456;
```

#### Phase 2: 本地客户端上报执行结果

```sql
-- 成功执行
UPDATE qd_pending_orders
SET status = 'executed',
    exchange_order_id = 'MT5-12345',
    filled = 0.1,
    avg_price = 1.0800,
    executed_at = 1234567890,
    updated_at = NOW()
WHERE id = 456;

-- 失败执行
UPDATE qd_pending_orders
SET status = 'failed',
    error_message = 'Insufficient margin',
    updated_at = NOW()
WHERE id = 456;
```

### 状态流转图

```
pending (初始状态)
   ↓
signal_pushed (云端推送信号成功)
   ↓
   ├─ executed (本地执行成功)
   └─ failed (本地执行失败或推送失败)
```

---

## 🧪 测试建议

### 1. 正常流程测试

```bash
# 1. 启动本地客户端
python scripts/local_trade_executor.py \
  --api-key qd_xxx \
  --broker-type mt5 \
  --cloud-url ws://localhost:8765/ws

# 2. 在 Web 界面创建策略，选择 MT5，execution_mode='live'

# 3. 触发信号生成

# 4. 观察日志：
#    - 云端: "Signal pushed successfully"
#    - 本地: "Trade executed successfully"
#    - 本地: "Execution result reported successfully"
#    - 云端: "Execution reported successfully"
```

### 2. 重试机制测试

```bash
# 模拟网络故障
# 1. 断开本地客户端网络连接
# 2. 触发信号
# 3. 观察云端日志："No active local clients"
# 4. 等待重试（2s, 4s, 8s）
# 5. 恢复网络连接
# 6. 观察是否重连并执行
```

### 3. 账号一致性测试

```bash
# 1. 云端配置 MT5 账号 A (602966)
# 2. 本地客户端登录 MT5 账号 B (123456)
# 3. 尝试连接
# 4. 观察日志："Broker account mismatch"
# 5. 应该拒绝连接
```

---

## ⚠️ 注意事项

### 1. 数据库迁移

需要确保 `qd_pending_orders` 表有以下字段：
- `status`: VARCHAR (pending, signal_pushed, executed, failed)
- `note`: TEXT (备注信息)
- `exchange_order_id`: VARCHAR (券商订单ID)
- `filled`: DECIMAL (成交数量)
- `avg_price`: DECIMAL (平均成交价)
- `executed_at`: INTEGER (执行时间戳)
- `error_message`: TEXT (错误信息)

### 2. 环境变量配置

```bash
# 云端 .env
ALLOW_LOCAL_DESKTOP_BROKERS=true  # 允许 MT5/IBKR 凭证创建
PENDING_ORDER_STALE_SEC=90        # 待处理订单超时时间（秒）
POSITION_SYNC_ENABLED=true        # 启用持仓同步
POSITION_SYNC_INTERVAL_SEC=10     # 持仓同步间隔（秒）
```

### 3. 本地客户端依赖安装

```bash
cd quantdinger-local-client
pip install -r requirements.txt
```

### 4. MT5/IBKR 终端要求

- **MT5**: Windows 系统，MT5 终端正在运行且已登录
- **IBKR**: TWS 或 IB Gateway 正在运行且已登录

---

## 📈 后续优化建议

### 1. 超时重推机制

如果本地客户端长时间未上报（例如 5 分钟），云端可以：
- 重新推送信号
- 或者标记为超时失败

### 2. 批量上报

如果本地客户端同时收到多个信号，可以：
- 批量执行
- 批量上报（减少 HTTP 请求次数）

### 3. 离线队列

如果本地客户端暂时无法连接云端：
- 将执行结果存入本地队列
- 网络恢复后批量上报

### 4. 监控告警

- 监控待处理订单的平均执行时间
- 监控失败率
- 超过阈值时发送告警

---

## ✅ 总结

本次改造完成了以下目标：

1. ✅ **移除云端直接执行 MT5/IBKR 的逻辑**
2. ✅ **实现云端推送信号到本地客户端**
3. ✅ **实现本地客户端执行并上报结果**
4. ✅ **两阶段操作确保数据一致性**
5. ✅ **重试机制防止数据丢失**
6. ✅ **防死循环措施（最大重试次数 + 指数退避）**
7. ✅ **API Key 认证和账号一致性校验**

**架构优势：**
- 云端负责智能分析，本地负责执行交易
- 券商凭证只在本地存储，提高安全性
- 支持多账号隔离（一个 API Key 对应一个交易所配置）
- 完整的审计链路（可追溯每个订单的执行过程）
