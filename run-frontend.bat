@echo off
setlocal
title Chirp Frontend (Next.js)
cd /d "%~dp0frontend"

if not exist "node_modules" (
  echo [setup] Installing frontend packages...
  call npm install --no-audit --no-fund
  if errorlevel 1 (
    echo.
    echo [!] npm install failed. Is Node.js installed?
    echo.
    pause
    exit /b 1
  )
)

if not exist ".env.local" (
  if exist ".env.example" copy /y ".env.example" ".env.local" >nul
)

echo.
echo  Chirp UI  -^>  http://localhost:3000
echo  Press Ctrl+C to stop.
echo.
call npm run dev -- -p 3000

if errorlevel 1 pause
endlocal
