@echo off
chcp 65001 >nul
setlocal

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend\vue-frontend"
set "BACKEND_URL=http://127.0.0.1:5000"
set "FRONTEND_URL=http://127.0.0.1:3000"
set "RTMP_URL=rtmp://127.0.0.1:1935/live"

title 两客一危交通事故检测系统 - 启动器

echo.
echo ============================================================
echo   两客一危交通事故检测系统 - Windows 启动脚本
echo ============================================================
echo.

if not exist "%BACKEND_DIR%\app.py" (
  echo [ERROR] 未找到后端入口: "%BACKEND_DIR%\app.py"
  goto :fail
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [ERROR] 未找到前端工程: "%FRONTEND_DIR%\package.json"
  goto :fail
)

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 python。请先安装 Python 或激活 Conda 环境。
  goto :fail
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 npm。请先安装 Node.js。
  goto :fail
)

echo [1/3] 启动实时检测后端: %BACKEND_URL%
start "LKYW Realtime Detection Backend" /D "%BACKEND_DIR%" cmd /k "python app.py"

echo [2/3] 检查并启动 Vue 前端: %FRONTEND_URL%
if not exist "%FRONTEND_DIR%\node_modules" (
  echo [INFO] 未发现 node_modules，将在前端窗口中执行 npm install。
  start "LKYW Realtime Detection Frontend" /D "%FRONTEND_DIR%" cmd /k "call npm install && call npm run dev -- --host 0.0.0.0"
) else (
  start "LKYW Realtime Detection Frontend" /D "%FRONTEND_DIR%" cmd /k "call npm run dev -- --host 0.0.0.0"
)

echo [3/3] 等待服务启动并打开浏览器...
timeout /t 5 /nobreak >nul
start "" "%FRONTEND_URL%"

echo.
echo ============================================================
echo   启动命令已发出
echo ============================================================
echo   后端地址: %BACKEND_URL%
echo   前端地址: %FRONTEND_URL%
echo   默认推流: %RTMP_URL%
echo.
echo   如果后端窗口提示缺少依赖，请先在当前 Conda 环境中执行:
echo     pip install -r "%BACKEND_DIR%\requirements.txt"
echo.
echo   如果需要 RTMP 实时检测，请确认 OBS 或 RTMP 服务正在推流到:
echo     %RTMP_URL%
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo 启动失败。请根据上面的错误信息检查环境。
echo.
pause
exit /b 1
