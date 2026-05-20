@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ===========================
:: 协同响应系统 - 一键启动脚本
:: ===========================

set "REPO_DIR=%~dp0"
set "MAIN_APP_DIR=%REPO_DIR%vue-project_all"
set "BACKEND_DIR=%REPO_DIR%Collaborative_Response\backend\command_center"

echo [INFO] 协同响应系统 - 一键启动
echo.
echo 主应用目录: %MAIN_APP_DIR%
echo 后端目录:   %BACKEND_DIR%
echo.

:: 检查 Node.js
echo [CHECK] 检测 Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js 未安装或不在 PATH 中
    pause
    exit /b 1
)
for /f "tokens=*" %%I in ('node --version') do echo [OK] Node.js %%I

:: 检查 Python
echo [CHECK] 检测 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 未安装或不在 PATH 中
    pause
    exit /b 1
)
for /f "tokens=*" %%I in ('python --version 2^>^&1') do echo [OK] %%I

:: 检查主应用 npm 依赖
echo.
echo [SETUP] 检查主应用 npm 依赖...
cd /d "%MAIN_APP_DIR%"
if not exist "node_modules" (
    echo [INSTALL] 安装主应用依赖 (仅首次，可能较慢)...
    call npm install
) else (
    echo [OK] 主应用依赖已就位
)

:: 检查 Python 依赖
echo.
echo [SETUP] 检查 Python 依赖...
cd /d "%BACKEND_DIR%"
if exist "requirements.txt" (
    python -m pip list 2>nul | find "streamlit" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INSTALL] 安装后端依赖...
        python -m pip install -q -r requirements.txt
    ) else (
        echo [OK] 后端依赖已就位
    )
)

:: ── 智能检测端口 ───────────────────────────────────────────────
set "BACKEND_RUNNING=0"
set "FRONTEND_RUNNING=0"

echo.
echo [DETECT] 检测服务状态...

:: 检测后端 5001
curl -s http://127.0.0.1:5001/api/health 2>nul | find "ok" >nul
if %errorlevel% equ 0 (
    echo [OK] 后端已在运行 (端口 5001)
    set "BACKEND_RUNNING=1"
) else (
    echo [--] 后端未运行
)

:: 检测前端 5173
curl -s http://127.0.0.1:5173 2>nul | find "app" >nul
if %errorlevel% equ 0 (
    echo [OK] 前端已在运行 (端口 5173)
    set "FRONTEND_RUNNING=1"
) else (
    echo [--] 前端未运行
)

:: ── 启动后端 ──────────────────────────────────────────────────
if %BACKEND_RUNNING% equ 1 (
    echo.
    echo [1/3] 后端已运行, 跳过启动
) else (
    echo.
    echo [1/3] 启动后端服务 (端口 5001)...
    cd /d "%BACKEND_DIR%"
    start "协同响应-指挥后端" cmd /k ^
        "title 协同响应指挥后端 && python server.py"
    echo       等待后端初始化 (3s)...
    timeout /t 3 /nobreak >nul
)

:: ── 启动前端 ──────────────────────────────────────────────────
if %FRONTEND_RUNNING% equ 1 (
    echo.
    echo [2/3] 前端已运行, 跳过启动
) else (
    echo.
    echo [2/3] 启动主应用前端 (端口 5173)...
    cd /d "%MAIN_APP_DIR%"
    start "协同响应-前端" cmd /k ^
        "title 协同响应前端 && npx vite --port 5173 --host"
    echo       等待前端编译 (6s)...
    timeout /t 6 /nobreak >nul
)

:: ── 打开浏览器 ────────────────────────────────────────────────
echo.
echo [3/3] 打开协同响应面板...
start "" http://localhost:5173/coordination

:: ── 完成 ──────────────────────────────────────────────────────
echo.
echo ===== 启动完成 =====
echo.
echo   协同响应面板:   http://localhost:5173/coordination
echo   指挥后端 API:   http://127.0.0.1:5001
echo   健康检查:       http://127.0.0.1:5001/api/health
echo   协同调度平台:   http://127.0.0.1:8501
echo.
echo   关闭方式: 关闭 "协同响应-指挥后端" 和 "协同响应-前端" 两个窗口
echo.

endlocal
pause
