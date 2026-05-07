@echo off
setlocal
title Contrarian 10-Bagger Engine
cd /d "%~dp0"

echo.
echo ============================================
echo   Contrarian 10-Bagger Engine
echo   Ranked speculative research, not advice
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set "PY=python"
    ) else (
        echo Python was not found on this computer.
        echo Install Python from https://www.python.org/downloads/windows/
        echo Then double-click this file again.
        echo.
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating the local app environment...
    %PY% -m venv .venv
    if errorlevel 1 (
        echo Could not create the local app environment.
        pause
        exit /b 1
    )
)

echo Installing or updating the app packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip -q
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo Package installation failed.
    pause
    exit /b 1
)

echo.
echo Opening saved research workspace...
call ".venv\Scripts\python.exe" "main.py" --quick
if errorlevel 1 (
    echo Startup check failed.
    pause
    exit /b 1
)

echo.
echo Opening Contrarian 10-Bagger Engine...
echo Keep this window open while you use the dashboard.
call ".venv\Scripts\python.exe" -m streamlit run "app\dashboard.py"

pause
