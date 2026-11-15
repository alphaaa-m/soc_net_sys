@echo off
setlocal
title Chirp Backend (FastAPI)
cd /d "%~dp0backend"

if not exist ".env" (
  echo.
  echo [!] backend\.env is missing.
  echo     Copy backend\.env.example to backend\.env and fill in DATABASE_URL / SECRET_KEY.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creating the Python 3.13 environment...
  where uv >nul 2>nul
  if not errorlevel 1 (
    uv sync --python 3.13
  ) else (
    python -m uv sync --python 3.13
  )
  if errorlevel 1 (
    echo.
    echo [!] Could not create the environment. Install uv and try again:
    echo     pip install uv
    echo.
    pause
    exit /b 1
  )
)

echo [db] Applying migrations...
".venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 (
  echo.
  echo [!] Migrations failed. Is PostgreSQL running and DATABASE_URL correct?
  echo.
  pause
  exit /b 1
)

echo.
echo  Chirp API  -^>  http://localhost:8000/docs
echo  Health     -^>  http://localhost:8000/health
echo  Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

if errorlevel 1 pause
endlocal
