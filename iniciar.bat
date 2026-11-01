@echo off
setlocal
cd /d "%~dp0"
title Video Generator

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Todavia no esta instalado. Haz doble clic en instalar.bat primero.
    echo.
    pause
    exit /b 1
)

"venv\Scripts\python.exe" src\main.py init-db >nul 2>&1

echo Iniciando Video Generator...
echo Se abrira el navegador en http://127.0.0.1:8000
echo NO cierres esta ventana mientras uses el programa. Para salir, cierrala o pulsa Ctrl+C.
echo.
"venv\Scripts\python.exe" src\main.py serve
echo.
pause
