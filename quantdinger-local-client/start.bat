@echo off
REM QuantDinger 本地交易客户端 - Windows 启动脚本

echo ========================================
echo QuantDinger 本地交易客户端
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python 或不在 PATH 中
    echo 请从 https://www.python.org/ 安装 Python 3.8+
    pause
    exit /b 1
)

echo ✓ 已找到 Python!
echo.

REM 检查 websockets 是否安装
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖安装失败
        pause
        exit /b 1
    )
    echo ✓ 依赖安装成功!
    echo.
)

echo 正在启动图形界面...
echo.
python main.py

pause
