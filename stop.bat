@echo off
chcp 65001 >nul
echo ========================================
echo   E9 智能化薪资核算系统 - 停止服务
echo ========================================
echo.

echo 正在停止后端服务 (uvicorn)...
taskkill /f /fi "WINDOWTITLE eq E9-Backend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8010 ^| findstr LISTENING') do (
    echo 终止进程 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

echo 正在停止前端服务 (vite)...
taskkill /f /fi "WINDOWTITLE eq E9-Frontend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5180 ^| findstr LISTENING') do (
    echo 终止进程 PID: %%a
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo 服务已停止。
echo.
pause
