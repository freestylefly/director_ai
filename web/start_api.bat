@echo off
chcp 65001 >nul 2>&1
title AI Storyboard Pro v2.2 - API Server

echo ============================================
echo  AI Storyboard Pro v2.2 API Server
echo ============================================
echo.

cd /d "%~dp0"

REM 默认端口
set PORT=8000

REM 从 .env 读取端口配置
if exist ".env" (
    for /f "tokens=1,2 delims==" %%a in ('findstr /i "API_PORT" .env 2^>nul') do (
        set PORT=%%b
    )
)

REM 检测并关闭占用端口的进程
echo [1/3] 检测端口 %PORT%...
set FOUND_PID=
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%PORT%.*LISTENING"') do (
    set FOUND_PID=%%a
)

if defined FOUND_PID (
    echo        发现占用进程 (PID: %FOUND_PID%)
    echo        正在关闭...
    taskkill /PID %FOUND_PID% /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo        已关闭进程
    ) else (
        echo        关闭失败，请手动结束进程
    )
    timeout /t 2 /nobreak >nul
) else (
    echo        端口 %PORT% 空闲
)

echo.
echo [2/3] 检测配置...
if not exist ".env" (
    echo        未找到配置文件
    echo        运行配置向导...
    echo.
    python setup_wizard.py
    if %errorlevel% neq 0 (
        echo.
        echo        配置失败或取消
        echo        请从 .env.example 创建 .env
        pause
        exit /b 1
    )
) else (
    echo        配置已就绪
)

echo.
echo [3/3] 启动 API 服务器...
echo.
echo ============================================
echo    API 文档: http://localhost:%PORT%/docs
echo    ReDoc: http://localhost:%PORT%/redoc
echo    按 Ctrl+C 停止服务
echo ============================================
echo.

python api_server.py

pause
