@echo off
title Drone Detection System - Starting...
echo ================================================
echo    Drone Detection System (Electron)
echo ================================================
echo.

REM Kill any existing processes on used ports
echo [1/3] Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Start frontend 
echo [2/3] Starting frontend server...
start /B cmd /c "cd /d "%~dp0\ui" && npm run dev"

REM Wait for frontend
echo [3/3] Waiting for servers to initialize...
timeout /t 3 /nobreak > nul

REM Start Electron (which will start the backend)
echo.
echo Opening Drone Detection window...
cd /d "%~dp0\ui\electron"
npx electron .

REM Cleanup message
echo.
echo App closed. Press any key to exit.
pause > nul
