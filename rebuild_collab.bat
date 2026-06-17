@echo off
cd /d "%~dp0Collaborative_Response"
echo Building collaborative-response...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo Build FAILED
    pause
    exit /b 1
)
echo.
echo Syncing to public...
xcopy /E /Y dist\* "%~dp0vue-project_all\public\collaborative-response\"
echo Done.
pause
