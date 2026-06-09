@echo off
setlocal

:: 1. Setup paths
set "REPO_DIR=%~dp0"
set "MODEL_PATH=%REPO_DIR%Real-time_Detection\runs\detect\lkyw_fire_detection\weights\best.pt"
set "TARGET_DIR=%REPO_DIR%Real-time_Detection\web_app\backend"

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

:: 4. Check if Model exists
if not exist "%MODEL_PATH%" (
    echo [ERROR] Model file not found at: "%MODEL_PATH%"
    pause
    exit /b 1
)

:: 5. Change directory
cd /d "%TARGET_DIR%"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not find directory: "%TARGET_DIR%"
    pause
    exit /b 1
)

:: 6. Set Environment Variables
set "PYTHONIOENCODING=utf-8"
:: Passing the model path as an environment variable (optional, if app.py uses it)
set "YOLO11N_MODEL_PATH=%MODEL_PATH%"

:: 7. Execution
echo Starting ZBY Real-time Detection Backend...
echo Working Dir: %CD%
echo Python:     %PYTHON_EXE%
echo Model:      %MODEL_PATH%
echo.

"%PYTHON_EXE%" app.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [RUN TIME ERROR] Backend stopped with exit code %ERRORLEVEL%
    pause
)

endlocal
