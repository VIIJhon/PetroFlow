@echo off
title PetroFlow Enterprise v3.0 - Full Stack
color 0A

echo.
echo  =========================================================
echo    PETROFLOW ENTERPRISE v3.0 — FULL STACK LAUNCHER
echo    Backend: FastAPI ^| Frontend: React ^| Port: 8000+3000
echo  =========================================================
echo.

:: Kill any previous instances
echo [1/3] Limpiando procesos anteriores...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" 2^>nul') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" 2^>nul') do taskkill /PID %%a /F >nul 2>&1
timeout /t 1 /nobreak >nul

:: Start Backend in a new window
echo [2/3] Iniciando Backend FastAPI en puerto 8000...
start "PetroFlow Backend :8000" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Wait for backend to be ready
echo      Esperando que el backend inicie...
timeout /t 4 /nobreak >nul

:: Start Frontend in a new window
echo [3/3] Iniciando Frontend React en puerto 3000...
start "PetroFlow Frontend :3000" cmd /k "cd /d %~dp0frontend && set GENERATE_SOURCEMAP=false && set BROWSER=none && npm start"

echo.
echo  =========================================================
echo    LISTO! Abre tu navegador en:
echo    http://localhost:3000
echo  =========================================================
echo.
echo  Cierra esta ventana cuando quieras detener los servidores
echo  o presiona cualquier tecla para salir.
pause >nul
