@echo off
TITLE NyayamGPT - Redis Server
cd /d "%~dp0"

REM Check if local Redis exists
IF EXIST "redis\redis-server.exe" (
    goto :RUN_REDIS
)

echo [INFO] Local Redis not found.
echo [INFO] Running setup script to download Redis for Windows...
powershell -ExecutionPolicy Bypass -File "scripts\setup_redis.ps1"

IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to download Redis.
    pause
    exit /b
)

:RUN_REDIS
echo.
echo ==========================================
echo   NyayamGPT Redis Server (Local Mode)
echo ==========================================
echo.
echo [INFO] Starting Redis Server...
echo [INFO] Port: 6379
echo.

REM Start Redis
"redis\redis-server.exe"

pause