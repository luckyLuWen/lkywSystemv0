@echo off
chcp 65001 >nul

:: ═══════════════════════════════════════════════════════════════
::  协同响应系统 — 一键启动脚本
::  后端: Flask (端口 5001)  +  前端: Vite (端口 5173)
:: ═══════════════════════════════════════════════════════════════

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend\command_center"
set "FRONTEND_DIR=%ROOT%."

:: ── 解析 Python ─────────────────────────────────────────────
set "PYTHON_EXE=%LKYW_PYTHON_EXE%"
if defined PYTHON_EXE goto :python_ready

set "PYTHON_EXE=D:\CondaEnvs\yolov11_traffic_dev\python.exe"
if exist "%PYTHON_EXE%" goto :python_ready

for /f "delims=" %%I in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%I"
    goto :python_ready
)

echo [ERROR] 找不到 Python，请设置 LKYW_PYTHON_EXE 环境变量
pause
exit /b 1

:python_ready
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python 路径不存在: "%PYTHON_EXE%"
    pause
    exit /b 1
)

:: ── 启动后端 ────────────────────────────────────────────────
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║          协同响应系统 — 一键启动                           ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo [1/2] 启动指挥后端 (端口 5001)...
cd /d "%BACKEND_DIR%"
start "🔧 协同响应指挥后端" cmd /k ""%PYTHON_EXE%" server.py"

:: ── 等待后端预热 ────────────────────────────────────────────
echo        等待后端初始化 (3s)...
timeout /t 3 >nul

:: ── 启动前端 ────────────────────────────────────────────────
echo [2/2] 启动前端开发服务器 (端口 5173)...
cd /d "%FRONTEND_DIR%"
start "🎨 协同响应前端" cmd /k "npx vite --port 5173 --host"

:: ── 等待前端就绪后打开浏览器 ─────────────────────────────────
echo        等待前端编译 (5s)...
timeout /t 5 >nul
start "" http://localhost:5173

:: ── 完成 ────────────────────────────────────────────────────
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              ✅ 协同响应系统启动完成！                     ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo    📡 指挥后端:    http://localhost:5001
echo       健康检查:    http://localhost:5001/api/health
echo       服务管理:    http://localhost:5001/api/services
echo.
echo    🎨 协同响应前端: http://localhost:5173
echo.
echo    📊 协同调度平台: 在前端页面中点击"启动服务"一键拉起
echo                     (Streamlit, 端口 8501)
echo.
echo ════════════════════════════════════════════════════════════
echo   关闭方式: 分别关闭"指挥后端"和"前端"两个终端窗口即可
echo ════════════════════════════════════════════════════════════
echo.
pause
