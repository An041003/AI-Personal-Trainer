@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"

echo ========================================
echo AI Personal Trainer - Dev Runner
echo ========================================
echo.

echo [1/5] Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or Docker CLI is not available.
    echo Please start Docker Desktop first, then run this file again.
    pause
    exit /b 1
)

echo [2/5] Looking for backend virtual environment...
set "BACKEND_PY="
if exist "%ROOT%.venv-backend\Scripts\python.exe" set "BACKEND_PY=%ROOT%.venv-backend\Scripts\python.exe"
if not defined BACKEND_PY if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" set "BACKEND_PY=%BACKEND_DIR%\.venv\Scripts\python.exe"
if not defined BACKEND_PY if exist "%ROOT%.venv\Scripts\python.exe" set "BACKEND_PY=%ROOT%.venv\Scripts\python.exe"

if not defined BACKEND_PY (
    echo [ERROR] Backend virtual environment was not found.
    echo Expected one of:
    echo   %ROOT%.venv-backend\Scripts\python.exe
    echo   %BACKEND_DIR%\.venv\Scripts\python.exe
    echo   %ROOT%.venv\Scripts\python.exe
    pause
    exit /b 1
)
echo [OK] Using "%BACKEND_PY%"

echo [3/5] Checking backend .env...
if not exist "%BACKEND_DIR%\.env" (
    if exist "%BACKEND_DIR%\.env.example" (
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
        echo [INFO] Created backend\.env from backend\.env.example.
        echo [INFO] Add OPENAI_API_KEY later if you need AI-backed features.
    ) else (
        echo [ERROR] backend\.env does not exist and backend\.env.example was not found.
        pause
        exit /b 1
    )
) else (
    echo [OK] backend\.env exists.
)

echo [4/5] Checking Node/npm...
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found in PATH.
    echo Please install Node.js or open a terminal where npm is available.
    pause
    exit /b 1
)

echo [5/5] Starting servers...
echo.
echo Backend:  http://127.0.0.1:8000/api/docs/
echo Frontend: http://127.0.0.1:5173/
echo.

if exist "%ROOT%docker-compose.yml" (
    echo [INFO] docker-compose.yml found. Starting Docker services...
    docker compose -f "%ROOT%docker-compose.yml" up -d
    if errorlevel 1 (
        echo [ERROR] Could not start Docker services.
        pause
        exit /b 1
    )
) else if exist "%ROOT%compose.yml" (
    echo [INFO] compose.yml found. Starting Docker services...
    docker compose -f "%ROOT%compose.yml" up -d
    if errorlevel 1 (
        echo [ERROR] Could not start Docker services.
        pause
        exit /b 1
    )
)

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } exit 1"
if errorlevel 1 (
    start "AI Personal Trainer - Backend" cmd /k "pushd "%BACKEND_DIR%" && "%BACKEND_PY%" manage.py migrate --noinput && "%BACKEND_PY%" manage.py runserver 127.0.0.1:8000"
) else (
    echo [INFO] Port 8000 is already in use. Backend may already be running.
)

powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { exit 0 } exit 1"
if errorlevel 1 (
    start "AI Personal Trainer - Frontend" cmd /k "pushd "%FRONTEND_DIR%" && if not exist node_modules ( npm install || exit /b 1 ) && npm run dev -- --host 127.0.0.1 --port 5173"
) else (
    echo [INFO] Port 5173 is already in use. Frontend may already be running.
)

echo Startup finished.
echo If new terminal windows were opened, close them or press Ctrl+C inside each one to stop the servers.
echo.
if /I not "%AIPT_NO_PAUSE%"=="1" pause
exit /b 0
