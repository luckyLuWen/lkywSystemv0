@echo off
setlocal

set "REPO_DIR=%~dp0"
set "TARGET_DIR=%REPO_DIR%Integration_Hub"

set "PYTHON_EXE=%LKYW_PYTHON_EXE%"
if defined PYTHON_EXE goto python_ready

set "PYTHON_EXE=D:\CondaEnvs\yolov11_traffic_dev\python.exe"
if exist "%PYTHON_EXE%" goto python_ready

for /f "delims=" %%I in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%I"
    goto python_ready
)

echo [ERROR] Python executable not found.
echo         Set LKYW_PYTHON_EXE or install python into PATH.
pause
exit /b 1

:python_ready

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python executable not found at: "%PYTHON_EXE%"
    pause
    exit /b 1
)

cd /d "%TARGET_DIR%"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not find directory: "%TARGET_DIR%"
    pause
    exit /b 1
)

set "PYTHONIOENCODING=utf-8"
if not defined REDIS_URL set "REDIS_URL=redis://127.0.0.1:6379/0"
if not defined INTEGRATION_HUB_PORT set "INTEGRATION_HUB_PORT=18701"

echo Starting LKYW Integration Hub...
echo Working Dir: %CD%
echo Python:     %PYTHON_EXE%
echo Redis:      %REDIS_URL%
echo Port:       %INTEGRATION_HUB_PORT%
echo.

"%PYTHON_EXE%" server.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [RUN TIME ERROR] Integration Hub stopped with exit code %ERRORLEVEL%
    pause
)

endlocal
