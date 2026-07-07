@echo off
chcp 65001 >nul
echo ========================================
echo   E9 智能化薪资核算系统 - 本地启动
echo   (纯本地运行，不需要 Docker)
echo ========================================
echo.

echo [1/4] 检查 PostgreSQL 服务...
sc query postgresql-x64-15 | find "RUNNING" >nul
if %errorlevel% neq 0 (
    echo PostgreSQL 服务未运行，正在启动...
    net start postgresql-x64-15
    timeout /t 2 /nobreak >nul
) else (
    echo PostgreSQL 服务已在运行 (端口 5432)
)
echo.

echo [2/4] 检查/初始化管理员账号...
cd /d %~dp0backend
call venv\Scripts\activate.bat
python init_admin.py 2>nul
echo.

echo [3/4] 启动后端服务 (端口 8010)...
start "E9-Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload"
timeout /t 3 /nobreak >nul

echo [4/4] 启动前端服务 (端口 5180)...
start "E9-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo   后端地址: http://localhost:8010
echo   前端地址: http://localhost:5180
echo   API文档:  http://localhost:8010/docs
echo   默认账号: admin / admin123
echo.
echo   数据库: 本地 PostgreSQL 端口 5432
echo   数据库名: e9_salary (独立库，不影响其他系统)
echo.
echo   正在打开浏览器...
start http://localhost:5180
echo.
pause
