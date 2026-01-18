@echo off
title AI Storyboard Pro v2.0 - Startup

echo ============================================
echo      AI Storyboard Pro v2.0
echo      AI Smart Storyboard System
echo ============================================
echo.

cd /d "%~dp0"

REM Check and kill process on port 7861
echo [1/4] Checking port 7861...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":7861.*LISTENING"') do (
    echo        Found process (PID: %%a)
    echo        Killing...
    taskkill /PID %%a /F >nul 2>&1
)
echo        Port 7861 cleared

echo.
echo [2/4] Checking dependencies...
pip show gradio >nul 2>&1
if %errorlevel% neq 0 (
    echo        Installing dependencies...
    pip install -r requirements.txt
) else (
    echo        Dependencies OK
)

echo.
echo [3/4] Checking configuration...
if not exist ".env" (
    echo        No configuration found.
    echo        Running setup wizard...
    echo.
    python setup_wizard.py
    if %errorlevel% neq 0 (
        echo.
        echo        Setup failed or cancelled.
        echo        Please create .env from .env.example
        pause
        exit /b 1
    )
) else (
    echo        Configuration OK
)

echo.
echo [4/4] Starting server...
echo.
echo ============================================
echo    Server URL: http://localhost:7861
echo    Press Ctrl+C to stop
echo ============================================
echo.

python app.py

pause
