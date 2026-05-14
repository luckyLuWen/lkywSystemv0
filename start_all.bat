@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ===========================
:: 协同响应系统 - 一键启动脚本
:: ===========================

set "REPO_DIR=%~dp0"
set "FRONTEND_DIR=%REPO_DIR%Collaborative_Response"
set "BACKEND_DIR=%REPO_DIR%Collaborative_Response\backend\command_center"

echo [INFO] 协同响应系统 - 一键启动
echo.
echo 前端目录: %FRONTEND_DIR%
echo 后端目录: %BACKEND_DIR%
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
for /f "tokens=*" %%I in ('python --version') do echo [OK] %%I

:: 检查 npm 依赖
echo.
echo [SETUP] 检查 npm 依赖...
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo [INSTALL] 安装前端依赖 (仅首次)...
    call npm install
) else (
    echo [OK] 前端依赖已就位
)

:: 检查 Python 依赖
echo.
echo [SETUP] 检查 Python 依赖...
cd /d "%BACKEND_DIR%"
if exist "requirements.txt" (
    python -m pip list | find "streamlit" >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INSTALL] 安装后端依赖...
        python -m pip install -q -r requirements.txt
    ) else (
        echo [OK] 后端依赖已就位
    )
)

:: 启动后端
echo.
echo [START] 启动后端服务 (Streamlit 应用)...
cd /d "%BACKEND_DIR%"
start "Collaborative_Response - Backend" cmd /k ^
    "title Collaborative Response Backend & python -m streamlit run app_2d.py --server.port 8501 --server.headless false"

:: 等待后端初始化
timeout /t 3 /nobreak

:: 启动前端
echo [START] 启动前端服务 (Vue DevServer)...
cd /d "%FRONTEND_DIR%"
start "Collaborative_Response - Frontend" cmd /k ^
    "title Collaborative Response Frontend & npm run dev"

:: 提示信息
echo.
echo ===== 启动完成 =====
echo 前端 DevServer: http://127.0.0.1:5174
echo 后端 Streamlit:  http://127.0.0.1:8501
echo.
echo 提示: 关闭任意窗口后需手动关闭另一个窗口
echo.

endlocal
pause
