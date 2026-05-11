# 项目结构说明

## 📁 目录结构

```
quantdinger-local-client/
│
├── 📄 main.py                      # ⭐ 主入口文件
├── 📄 README.md                    # 项目说明文档
├── 📄 QUICKSTART_CN.md             # 快速开始指南
├── 📄 LICENSE                      # 许可证
├── 📄 .gitignore                   # Git忽略配置
│
├── 📦 requirements.txt             # Python依赖
│
├── 🚀 start.bat                    # Windows启动脚本
├── 🚀 start.sh                     # Linux/Mac启动脚本
│
├── 📂 src/                         # ⭐ 源代码目录
│   ├── 📄 __init__.py              # 包初始化
│   │
│   ├── 📂 core/                    # 核心模块
│   │   ├── 📄 __init__.py
│   │   ├── 📄 signal_client.py     # WebSocket信号客户端
│   │   └── 📄 config.py            # 配置管理器
│   │
│   ├── 📂 gui/                     # 图形界面
│   │   ├── 📄 __init__.py
│   │   └── 📄 app.py               # GUI主应用
│   │
│   ├── 📂 brokers/                 # 券商集成（待扩展）
│   │   ├── 📄 __init__.py
│   │   ├── 📄 mt5.py               # MT5交易执行
│   │   └── 📄 ibkr.py              # IBKR交易执行
│   │
│   └── 📂 utils/                   # 工具函数
│       ├── 📄 __init__.py
│       ├── 📄 logger.py            # 日志工具
│       └── 📄 validators.py        # 数据验证
│
├── 📂 config/                      # 配置文件目录
│   └── 📄 example_config.json      # 配置示例
│
└── 📂 logs/                        # 日志目录（运行时生成）
```

---

## 🎯 设计理念

### 1️⃣ **模块化设计**

代码按功能划分为清晰的模块：

- **core/** - 核心业务逻辑（WebSocket、配置）
- **gui/** - 用户界面
- **brokers/** - 券商集成
- **utils/** - 通用工具

### 2️⃣ **单一职责**

每个模块只负责一个明确的功能：

- `signal_client.py` - 只处理WebSocket连接和信号接收
- `config.py` - 只管理配置加载和保存
- `app.py` - 只负责GUI展示和用户交互

### 3️⃣ **易于扩展**

新增功能只需在对应模块添加文件：

```python
# 例如：添加新的券商支持
src/brokers/binance.py    # Binance集成
src/brokers/okx.py        # OKX集成
```

---

## 📝 核心模块说明

### main.py
**作用**: 应用程序入口点  
**功能**: 
- 初始化并启动GUI应用
- 设置Python路径

**使用**:
```bash
python main.py
```

---

### src/core/signal_client.py
**作用**: WebSocket信号客户端  
**功能**:
- 连接到QuantDinger云端
- 接收实时交易信号
- 自动重连机制
- 回调函数支持

**关键类**:
```python
class SignalClient:
    def __init__(api_key, cloud_url, on_signal, ...)
    async def connect()           # 连接服务器
    async def disconnect()        # 断开连接
    def get_stats()               # 获取统计信息
```

**使用示例**:
```python
client = SignalClient(
    api_key="your-key",
    cloud_url="ws://localhost:8765/ws",
    on_signal=lambda sig: print("收到信号:", sig)
)
await client.connect()
```

---

### src/core/config.py
**作用**: 配置管理器  
**功能**:
- 加载/保存JSON配置文件
- 支持嵌套配置（点号访问）
- 配置验证
- 默认值管理

**关键类**:
```python
class ConfigManager:
    def load()                    # 加载配置
    def save()                    # 保存配置
    def get(key)                  # 获取配置值
    def set(key, value)           # 设置配置值
    def validate()                # 验证配置
```

**使用示例**:
```python
config = ConfigManager("config.json")
api_key = config.get('api_key')
config.set('broker', 'mt5')
config.save()
```

---

### src/gui/app.py
**作用**: GUI主应用  
**功能**:
- 创建图形界面
- 显示连接状态
- 监控交易信号
- 查看和管理日志
- 配置管理

**关键类**:
```python
class QuantDingerApp:
    def __init__()                # 初始化应用
    def run()                     # 运行应用
    def _create_ui()              # 创建界面组件
    def _start_client()           # 启动客户端
    def _stop_client()            # 停止客户端
```

---

## 🔧 如何扩展

### 添加新的券商支持

1. 在 `src/brokers/` 创建新文件：

```python
# src/brokers/binance.py
class BinanceBroker:
    def __init__(self, api_key, secret):
        ...
    
    def place_order(self, symbol, side, amount):
        ...
```

2. 在 `src/brokers/__init__.py` 导出：

```python
from .binance import BinanceBroker
```

3. 在GUI中添加选项：

```python
# src/gui/app.py
combo = ttk.Combobox(
    values=['simulation', 'mt5', 'ibkr', 'binance']
)
```

---

### 添加新的UI组件

1. 在 `src/gui/` 创建新模块：

```python
# src/gui/dashboard.py
class DashboardFrame(ttk.Frame):
    def __init__(self, parent):
        ...
```

2. 在主应用中导入并使用：

```python
# src/gui/app.py
from .dashboard import DashboardFrame

dashboard = DashboardFrame(main_frame)
dashboard.grid(...)
```

---

### 添加工具函数

1. 在 `src/utils/` 创建新文件：

```python
# src/utils/validators.py
def validate_symbol(symbol: str) -> bool:
    return bool(symbol and len(symbol) > 0)
```

2. 在其他模块中导入使用：

```python
from src.utils.validators import validate_symbol
```

---

## 📊 代码组织原则

### ✅ 好的做法

1. **每个文件不超过500行** - 保持代码可读性
2. **每个类有明确的职责** - 单一职责原则
3. **使用类型提示** - 提高代码可维护性
4. **编写文档字符串** - 方便理解和使用
5. **错误处理完善** - 提供友好的错误信息

### ❌ 避免的做法

1. ~~所有代码写在一个文件~~ - 难以维护
2. ~~全局变量滥用~~ - 导致状态混乱
3. ~~硬编码配置~~ - 缺乏灵活性
4. ~~缺少注释~~ - 他人难以理解
5. ~~异常不处理~~ - 程序容易崩溃

---

## 🚀 快速上手

### 1. 查看项目结构

```bash
tree -L 3
```

### 2. 运行应用

```bash
python main.py
```

### 3. 修改配置

编辑 `config.json` 或在GUI中修改

### 4. 查看日志

日志实时显示在GUI的Logs面板中

---

## 📞 需要帮助？

- 📖 阅读各模块的文档字符串
- 🔍 查看示例代码
- 💬 提交Issue讨论

---

这种结构让代码**清晰、易维护、易扩展**！🎉
