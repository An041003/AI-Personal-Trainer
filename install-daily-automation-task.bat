@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
set "TASK_NAME=AI Personal Trainer Daily Automation"
set "TASK_CMD=%ROOT%run-daily-automation.bat"

if not exist "%TASK_CMD%" (
    echo [ERROR] run-daily-automation.bat was not found.
    exit /b 1
)

schtasks /Create /TN "%TASK_NAME%" /SC DAILY /ST 07:00 /TR "\"%TASK_CMD%\"" /F
if errorlevel 1 (
    echo [ERROR] Could not register Windows Task Scheduler task.
    exit /b 1
)

echo [OK] Registered "%TASK_NAME%" to run daily at 07:00.
exit /b 0
