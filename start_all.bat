@echo off
title 应急救援数字孪生系统 - 一键启动
echo ============================================================
echo   应急救援数字孪生系统
echo   启动中...
echo ============================================================
echo.

set "ROOT=%~dp0"
set "PYTHON=%ROOT%Collaborative_Response\backend\command_center\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

echo [1/3] 启动协同响应指挥后端 (Flask:5001 + Streamlit:8501)
start "Flask-指挥后端" /min cmd /c "cd /d "%ROOT%Collaborative_Response\backend\command_center" && "%PYTHON%" server.py"

echo [2/3] 等待 Flask 就绪...
timeout /t 3 /nobreak >nul

echo [3/3] 启动主系统前端 (Vue:5173)
start "Vue-主系统前端" /min cmd /c "cd /d "%ROOT%vue-project_all" && npm run dev"

echo.
echo ============================================================
echo   所有服务已启动!
echo.
echo   主系统首页:   http://localhost:5173
echo   协同响应:     http://localhost:5173/coordination
echo   二维动态推演: http://localhost:5173/2d-deduction
echo   指挥后端API:  http://127.0.0.1:5001
echo   协同调度平台: http://127.0.0.1:8501
echo ============================================================
echo.
echo   按任意键打开主系统...
pause >nul
start http://localhost:5173
