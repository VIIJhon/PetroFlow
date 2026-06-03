@echo off
REM PetroFlow Enterprise v3.0 - Unified Mode (SPA served by FastAPI)
REM Author: Antigravity AI
REM This script compiles the React frontend and starts the FastAPI backend to serve both the API and the SPA on a single port.

echo ============================================================================
echo   PETROFLOW ENTERPRISE v3.0 - UNIFIED SERVER STARTUP
echo   (FastAPI Backend + React SPA on Port 8000)
echo ============================================================================
echo.

set "ROOT_DIR=%~dp0"

echo [1/2] Compiling React Frontend for Production (with optimizations)...
cd /d "%ROOT_DIR%frontend"
call npm install
set GENERATE_SOURCEMAP=false
set DISABLE_ESLINT_PLUGIN=true
call npm run build


if not exist "%ROOT_DIR%frontend\build\index.html" (
    echo.
    echo ERROR: Failed to build the React application. 
    echo Please make sure Node.js and NPM are installed and in your system PATH.
    pause
    exit /b 1
)
echo OK: React Frontend compiled successfully to /build.

echo.
echo [2/2] Starting Unified FastAPI Server (Port 8000)...
cd /d "%ROOT_DIR%backend"

echo.
echo ============================================================================
echo   PETROFLOW UNIFIED SERVICES LAUNCHED SUCCESSFULLY!
echo ============================================================================
echo.
echo   - PetroFlow Application: http://localhost:8000
echo   - API Documentation:     http://localhost:8000/api/docs
echo.
echo   Note: Please leave this terminal open.
echo ============================================================================
echo.

..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
