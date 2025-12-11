@echo off
setlocal ENABLEEXTENSIONS

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

set "VENV_DIR=%PROJECT_DIR%.venv"
set "VENV_ACTIVATE=%VENV_DIR%\Scripts\activate.bat"

if not exist "%VENV_ACTIVATE%" (
    echo [INFO] Creando entorno virtual en %VENV_DIR%.
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        exit /b 1
    )
)

call "%VENV_ACTIVATE%"
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual.
    exit /b 1
)

echo [INFO] Instalando dependencias requeridas...
pip install --upgrade pip >nul
pip install -r "%PROJECT_DIR%requirements.txt"
if errorlevel 1 (
    echo [ERROR] Fallo al instalar dependencias.
    exit /b 1
)

echo [INFO] Iniciando servidor Flask en modo depuracion.
flask --app app --debug run

endlocal
