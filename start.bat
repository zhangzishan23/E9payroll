@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   E9 智能化薪资核算系统 - 本地启动
echo   (纯本地运行，不需要 Docker)
echo ========================================
echo.

set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "BACKEND_PORT=8010"
set "FRONTEND_PORT=5180"

echo [1/5] 检查 PostgreSQL 服务...
sc query postgresql-x64-15 | find "RUNNING" >nul
if %errorlevel% neq 0 (
    echo PostgreSQL 服务未运行，正在启动...
    net start postgresql-x64-15
    timeout /t 2 /nobreak >nul
) else (
    echo PostgreSQL 服务已在运行 (端口 5432)
)
echo.

echo [2/5] 检查后端虚拟环境 (.venv)...
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo 虚拟环境不存在，正在创建...
    cd /d "%BACKEND_DIR%"
    python -m venv "%VENV_DIR%"
    echo 正在安装后端依赖...
    "%VENV_DIR%\Scripts\pip.exe" install -r requirements.txt
) else (
    echo 虚拟环境已就绪
    if not exist "%VENV_DIR%\Scripts\uvicorn.exe" (
        echo 依赖不完整，正在重新安装...
        "%VENV_DIR%\Scripts\pip.exe" install -r requirements.txt
    )
)
echo.

echo [3/5] 检查/初始化管理员账号...
cd /d "%BACKEND_DIR%"
"%VENV_DIR%\Scripts\python.exe" init_admin.py
echo.

echo [4/5] 检查前端依赖...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo node_modules 不存在，正在安装前端依赖...
    cd /d "%FRONTEND_DIR%"
    npm install
) else (
    echo 前端依赖已就绪
)
echo.

echo [5/5] 启动服务...
netstat -ano | findstr ":%BACKEND_PORT% " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo 后端端口 %BACKEND_PORT% 已被占用，跳过后端启动
) else (
    echo 正在启动后端服务 (端口 %BACKEND_PORT%)...
    start "E9-Backend" cmd /k "cd /d %BACKEND_DIR% && %VENV_DIR%\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
    timeout /t 3 /nobreak >nul
)

netstat -ano | findstr ":%FRONTEND_PORT% " | findstr "LISTENING" >nul
if %errorlevel% equ 0 (
    echo 前端端口 %FRONTEND_PORT% 已被占用，跳过前端启动
) else (
    echo 正在启动前端服务 (端口 %FRONTEND_PORT%)...
    start "E9-Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"
    timeout /t 3 /nobreak >nul
)

echo.
echo ========================================
echo   正在获取本机局域网IP...
echo ========================================
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    for /f "tokens=1" %%b in ("%%a") do set "LAN_IP=%%b"
)
if defined LAN_IP (
    echo   局域网IP: %LAN_IP%
) else (
    set "LAN_IP=localhost"
    echo   未检测到局域网IP，使用localhost
)
echo.
echo ========================================
echo   启动完成！
echo ========================================
echo   本机访问:
echo     前端地址: http://localhost:%FRONTEND_PORT%/e9salary/
echo     后端地址: http://localhost:%BACKEND_PORT%
echo     API文档:  http://localhost:%BACKEND_PORT%/e9salary/docs
echo.
if not "%LAN_IP%"=="localhost" (
echo   局域网访问（其他人电脑用这个地址）:
echo     前端地址: http://%LAN_IP%:%FRONTEND_PORT%/e9salary/
echo     后端地址: http://%LAN_IP%:%BACKEND_PORT%
echo.
)
echo   默认账号: admin / admin123
echo.
echo   数据库: 本地 PostgreSQL 端口 5432
echo   数据库名: e9_salary (独立库，不影响其他系统)
echo.
echo   正在打开浏览器...
start http://localhost:%FRONTEND_PORT%/e9salary/
echo.
pause
