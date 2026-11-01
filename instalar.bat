@echo off
setlocal
cd /d "%~dp0"
title Video Generator - Instalacion

echo ==============================================
echo   Video Generator - Instalacion automatica
echo ==============================================
echo.

rem --- 1. Buscar Python 3.10 o superior ---------------------------------
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if %errorlevel%==0 set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if %errorlevel%==0 set "PY=python"
)
if not defined PY (
    echo [ERROR] No se ha encontrado Python 3.10 o superior.
    echo.
    echo  1. Descargalo de https://www.python.org/downloads/ ^(recomendado: 3.11 o 3.12^)
    echo  2. En el instalador, marca la casilla "Add python.exe to PATH".
    echo  3. Cuando termine, cierra esta ventana y vuelve a ejecutar instalar.bat
    echo.
    pause
    exit /b 1
)
echo [1/6] Python encontrado:
%PY% --version

rem --- 2. Crear el entorno virtual --------------------------------------
if not exist "venv\Scripts\python.exe" (
    echo [2/6] Creando entorno virtual ^(carpeta venv^)...
    %PY% -m venv venv
    if errorlevel 1 goto :fail
) else (
    echo [2/6] El entorno virtual ya existe, se reutiliza.
)
set "VPY=%~dp0venv\Scripts\python.exe"
"%VPY%" -m pip install --upgrade pip >nul 2>&1

rem --- 3. PyTorch (GPU NVIDIA si existe, si no CPU) ----------------------
nvidia-smi >nul 2>&1
if %errorlevel%==0 (
    echo [3/6] Tarjeta NVIDIA detectada: instalando PyTorch con GPU ^(descarga grande, ~2.5 GB^)...
    "%VPY%" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
) else (
    echo [3/6] No se detecta tarjeta NVIDIA: instalando PyTorch para CPU...
    "%VPY%" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)
if errorlevel 1 goto :fail

rem --- 4. Resto de dependencias -----------------------------------------
echo [4/6] Instalando el resto de dependencias...
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

rem --- 5. Modelo de etiquetado (CLIP) -----------------------------------
echo [5/6] Descargando el modelo de etiquetado CLIP ^(~350 MB, solo la primera vez^)...
"%VPY%" -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')"
if errorlevel 1 goto :fail

rem --- 6. Base de datos --------------------------------------------------
echo [6/6] Creando la base de datos de clips...
"%VPY%" src\main.py init-db
if errorlevel 1 goto :fail

echo.
echo ==============================================
echo   Instalacion completada con exito.
echo   Para usar el programa, haz doble clic en iniciar.bat
echo ==============================================
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] La instalacion ha fallado. Revisa los mensajes de arriba.
echo Consulta tutoriales\08-problemas-frecuentes.md o vuelve a ejecutar instalar.bat
echo ^(es seguro repetirlo: continuara donde se quedo^).
echo.
pause
exit /b 1
