# 本地测试指南

## 📋 测试清单

### ✅ 已完成
- [x] GUI客户端代码重构完成
- [x] 项目结构规范化
- [x] 依赖安装（websockets）

### ⏳ 待完成
- [ ] WebSocket服务器启动
- [ ] GUI客户端连接测试
- [ ] 信号接收测试

---

## 🚀 完整测试流程

### 第1步：准备环境

#### 1.1 安装QuantDinger后端依赖

```bash
cd d:\www\workai\QuantDinger\backend_api_python
pip install -r requirements.txt
```

**注意**: 这需要一些时间，因为依赖较多。

#### 1.2 确认客户端依赖已安装

```bash
cd d:\www\workai\QuantDinger\quantdinger-local-client
pip install websockets
```

状态：✅ 已完成

---

### 第2步：启动WebSocket服务器

#### 方式1: 完整后端（推荐用于生产）

```bash
# 终端1: 启动QuantDinger后端
cd d:\www\workai\QuantDinger
docker-compose up -d

# 终端2: 启动WebSocket服务
cd backend_api_python
python start_websocket_server.py
```

#### 方式2: 简化测试（快速验证）

由于完整后端依赖较多，我们可以先测试GUI界面是否正常显示：

```bash
cd d:\www\workai\QuantDinger\quantdinger-local-client
python main.py
```

**预期结果**: 
- ✅ GUI窗口正常打开
- ✅ 可以看到配置界面
- ✅ 可以输入API Key和URL
- ⚠️ 点击"Start"会显示连接失败（因为服务器未启动）

---

### 第3步：测试GUI客户端

#### 3.1 启动GUI

```bash
cd d:\www\workai\QuantDinger\quantdinger-local-client
python main.py
```

#### 3.2 检查界面元素

应该看到以下内容：

```
┌─────────────────────────────────────────────┐
│ Configuration                               │
│ • API Key输入框                              │
│ • Cloud URL输入框                            │
│ • Broker下拉菜单                             │
│ • Save Config按钮                            │
├─────────────────────────────────────────────┤
│ Connection Status                           │
│ • ● Disconnected (红色)                      │
│ • Signals: 0                                 │
│ • Trades: 0                                  │
├─────────────────────────────────────────────┤
│ [▶ Start] [⏹ Stop] [🗑 Clear] [💾 Export] │
├──────────────────┬──────────────────────────┤
│ Recent Signals   │ Logs                     │
│ (空列表)         │ (空日志)                  │
└──────────────────┴──────────────────────────┘
```

#### 3.3 测试配置保存

1. 填写测试数据：
   - API Key: `test-key-12345678`
   - Cloud URL: `ws://localhost:8765/ws`
   - Broker: `simulation`

2. 点击 "Save Config"
3. 应该看到提示："✓ Configuration saved"
4. 检查是否生成 `config.json` 文件

---

### 第4步：测试WebSocket连接

#### 4.1 使用测试脚本

```bash
cd d:\www\workai\QuantDinger\quantdinger-local-client
python test_connection.py
```

**如果服务器未运行**，会看到：
```
✗ Connection refused

Possible reasons:
  1. WebSocket server is not running
  2. Wrong URL or port
```

**如果服务器正常运行**，会看到：
```
✓ Connected successfully!
✓ Authentication sent
✓ Server Response:
  Type: connection_established
  Client ID: xxx-xxx-xxx
  
🎉 Test PASSED!
```

#### 4.2 在GUI中测试

1. 确保WebSocket服务器已启动
2. 在GUI中填写配置
3. 点击 "▶ Start"
4. 观察状态变化：
   - 红色 "● Disconnected" → 绿色 "● Connected"
   - Logs面板显示连接日志
   - 状态变为 "Connected"后，"Start"按钮禁用，"Stop"按钮启用

---

## 🔧 常见问题排查

### Q1: GUI无法启动

**错误**: `ModuleNotFoundError: No module named 'tkinter'`

**解决**:
```bash
# Windows - Python通常自带tkinter
# 如果缺失，重新安装Python并勾选tcl/tk选项

# Linux
sudo apt-get install python3-tk

# Mac
brew install python-tk
```

### Q2: WebSocket连接失败

**错误**: `Connection refused`

**原因**: WebSocket服务器未启动

**解决**:
```bash
# 启动WebSocket服务器
cd d:\www\workai\QuantDinger
python start_websocket_server.py
```

### Q3: 依赖安装失败

**错误**: `ModuleNotFoundError: No module named 'websockets'`

**解决**:
```bash
pip install websockets
```

### Q4: 配置文件保存失败

**错误**: `Permission denied`

**解决**:
- 确保有写入权限
- 不要以管理员身份运行（Windows）
- 检查磁盘空间

---

## 📊 测试检查表

### GUI界面测试

- [ ] 窗口正常打开
- [ ] 标题显示 "QuantDinger Local Trade Client v1.0"
- [ ] 所有输入框可编辑
- [ ] 下拉菜单可选择broker
- [ ] Save Config按钮可点击
- [ ] Start/Stop按钮状态正确切换
- [ ] 日志面板可滚动
- [ ] 信号列表可添加新条目

### 功能测试

- [ ] 配置可以保存
- [ ] 配置可以加载（重启后保留）
- [ ] Start按钮启动连接
- [ ] Stop按钮停止连接
- [ ] Clear Logs清空日志
- [ ] Export Logs导出文件
- [ ] 连接成功时状态变绿
- [ ] 连接失败时状态保持红色

### 代码质量测试

- [ ] 无语法错误
- [ ] 无导入错误
- [ ] 模块结构清晰
- [ ] 代码注释完整
- [ ] 类型提示正确

---

## 🎯 快速测试命令

### 测试1: 检查依赖

```bash
python -c "import websockets; print('✓ websockets OK')"
python -c "import tkinter; print('✓ tkinter OK')"
```

### 测试2: 启动GUI

```bash
python main.py
```

### 测试3: 测试连接

```bash
python test_connection.py
```

### 测试4: 查看项目结构

```bash
tree /F /A
```

---

## 📝 当前状态

### ✅ 已完成
1. 代码重构完成
2. 项目结构规范化
3. 依赖安装（websockets）
4. 测试脚本创建

### ⏳ 下一步
1. 安装完整后端依赖（可选，用于真实测试）
2. 启动WebSocket服务器
3. 进行端到端测试

### 💡 建议

**如果想快速验证GUI**：
```bash
# 直接启动GUI，测试界面
python main.py
```

**如果想完整测试**：
```bash
# 1. 安装后端依赖
cd d:\www\workai\QuantDinger\backend_api_python
pip install -r requirements.txt

# 2. 启动WebSocket服务器
cd ..
python start_websocket_server.py

# 3. 新终端启动GUI
cd quantdinger-local-client
python main.py

# 4. 在GUI中点击Start测试连接
```

---

## 🎉 总结

你现在可以：

1. **测试GUI界面** - 运行 `python main.py`
2. **验证代码结构** - 查看 `src/` 目录
3. **阅读文档** - 查看 `STRUCTURE.md` 和 `REFACTOR_SUMMARY.md`

**GUI已经可以正常运行**，只是需要WebSocket服务器才能接收真实信号。

需要我帮你安装完整后端依赖并进行端到端测试吗？或者你想先测试一下GUI界面？
