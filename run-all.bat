@echo off
setlocal
echo Starting Chirp in two windows...
start "Chirp Backend" cmd /k "%~dp0run-backend.bat"
start "Chirp Frontend" cmd /k "%~dp0run-frontend.bat"

echo.
echo  Backend docs : http://localhost:8000/docs
echo  App          : http://localhost:3000
echo.
echo Both windows stay open. Close them (or press Ctrl+C) to stop the servers.
timeout /t 3 >nul
endlocal
