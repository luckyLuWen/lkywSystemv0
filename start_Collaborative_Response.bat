@echo off
setlocal

:: 1. Setup paths
set "REPO_DIR=%~dp0"
set "TARGET_DIR=%REPO_DIR%Collaborative_Response\backend\command_center"

:: 2. Resolve Python
set "PYTHON_EXE=%LKYW_PYTHON_EXE%"
if defined PYTHON_EXE goto python_ready

set "PYTHON_EXE=D:\Miniconda\envs\layolo_traffic_dev\python.exe"
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

:: 3. Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python executable not found at: "%PYTHON_EXE%"
    pause
    exit /b 1
)

:: 4. Change directory
cd /d "%TARGET_DIR%"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not find directory: "%TARGET_DIR%"
    pause
    exit /b 1
)

:: 5. Set Environment Variables
set "PYTHONIOENCODING=utf-8"

:: 6. Execution
echo Starting DH Collaborative Response Control Layer...
echo Working Dir: %CD%
echo Python Path: %PYTHON_EXE%
echo.

"%PYTHON_EXE%" server.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [RUN TIME ERROR] Server stopped with exit code %ERRORLEVEL%
    pause
)

endlocal
