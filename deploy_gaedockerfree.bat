@echo off
echo ============================================================================
echo   DESPLIEGUE CLOUD EXPRESS PETROFLOW -- GOOGLE APP ENGINE
echo ============================================================================
echo.

set "ROOT_DIR=%~dp0"
set PROJECT_ID=petroflow-beta

echo [1/4] Compilando Frontend React localmente...
cd /d "%ROOT_DIR%frontend"
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: Falló la compilación. Asegúrate de haber instalado Node.js.
    pause
    exit /b 1
)

echo.
echo [2/4] Consolidando archivos compilados para GCP...
if not exist "%ROOT_DIR%backend\static" mkdir "%ROOT_DIR%backend\static"
xcopy "%ROOT_DIR%frontend\build\*.*" "%ROOT_DIR%backend\static\" /E /Y /I

echo.
echo [3/4] Configurando Google Cloud CLI...
call gcloud config set project %PROJECT_ID%

echo.
echo [4/4] Subiendo aplicación a Google Cloud (App Engine)...
cd /d "%ROOT_DIR%backend"
call gcloud app deploy app.yaml --quiet

echo.
echo ============================================================================
echo   ¡DESPLIEGUE FINALIZADO!
echo   Tu versión Cloud de PetroFlow está en línea.
echo   Mírala en tu navegador con: gcloud app browse
echo ============================================================================
pause
