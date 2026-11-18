@echo off
cd /d "%~dp0"
set "PYTHON_EXE=%LKYW_PYTHON_EXE%"
if not defined PYTHON_EXE set "PYTHON_EXE=D:\Miniconda\envs\layolo_traffic_dev\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" Integration_Hub\auth.py
pause
