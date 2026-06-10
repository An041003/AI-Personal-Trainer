@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"

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
    exit /b 1
)

if not exist "%BACKEND_DIR%\.env" (
    echo [ERROR] backend\.env does not exist.
    exit /b 1
)

pushd "%BACKEND_DIR%"
"%BACKEND_PY%" manage.py run_daily_automation %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
