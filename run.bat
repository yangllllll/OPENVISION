@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
    echo [信息] 安装依赖...
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\pip.exe install -r requirements.txt
)

echo [信息] 启动 OpenVision...
venv\Scripts\python.exe main.py
pause