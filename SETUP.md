# Guía de instalación (referencia)

> ¿No eres técnico? Sigue mejor el tutorial paso a paso: [tutoriales/01-instalacion.md](tutoriales/01-instalacion.md).

## Requisitos

| Requisito | Detalle |
|---|---|
| Sistema | Windows 10 / 11 |
| Python | 3.10 o superior (recomendado 3.11 o 3.12). Marcar **Add python.exe to PATH** al instalar |
| DaVinci Resolve | 18+ (la versión gratuita funciona). Solo se usa para **importar** el `.fcpxml` |
| Disco | ~5 GB libres para el programa y el modelo de IA |
| ffmpeg | Opcional: solo para subir a TikTok / Instagram |
| GPU NVIDIA | Opcional: acelera mucho el etiquetado |

> No hace falta configurar la API de scripting de DaVinci Resolve ni tener Resolve abierto para generar las líneas de tiempo.

## Instalación automática (recomendada)

1. Descarga el repositorio y descomprímelo (o `git clone`).
2. Doble clic en **`instalar.bat`**. Hace, en orden:
   1. Busca Python 3.10+.
   2. Crea el entorno virtual en la carpeta `venv\`.
   3. Instala PyTorch (versión GPU si detecta una NVIDIA, si no versión CPU).
   4. Instala el resto de dependencias de `requirements.txt`.
   5. **Descarga el modelo de etiquetado** (OpenCLIP `ViT-B-32`, ~350 MB).
   6. Crea la base de datos `clips_db\clips.db`.
3. Doble clic en **`iniciar.bat`** para abrir la interfaz web (http://127.0.0.1:8000).

Es seguro volver a ejecutar `instalar.bat` si algo se interrumpe.

## Instalación manual

```powershell
python -m venv venv
venv\Scripts\activate

# PyTorch: elige UNA de las dos
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121   # con GPU NVIDIA (comprueba con nvidia-smi)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu     # sin GPU

pip install -r requirements.txt

# Descargar el modelo de etiquetado (opcional: si no, se descarga solo la primera vez que etiquetes)
python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')"

python src/main.py init-db
python src/main.py serve
```

## El modelo de etiquetado

- Es **OpenCLIP ViT-B-32 con pesos de OpenAI**; se descarga automáticamente de internet (~350 MB) y se guarda en la caché del usuario (dentro de `%USERPROFILE%\.cache`). Solo se descarga una vez.
- Usa la GPU automáticamente si PyTorch la detecta; si no, usa la CPU (más lento pero funciona).
- Las etiquetas candidatas están en `src/tagger/constants.py`.

## Dónde se guarda todo

| Qué | Dónde |
|---|---|
| Base de datos de clips | `clips_db\clips.db` |
| Líneas de tiempo (CLI) | `output\` |
| Líneas de tiempo (interfaz web) | carpeta `timelines` junto a la canción (o la que elijas) |
| Credenciales de subida | `config\upload_config.json` (nunca se sube a git) |
| Registro de subidas | `output\upload_log.jsonl` |

## Formatos soportados

- Vídeo: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- Audio: `.mp3`, `.wav`, `.flac`, `.m4a`, `.aac`, `.ogg`

## ffmpeg (solo para subir a redes)

```powershell
winget install ffmpeg
```

Cierra y vuelve a abrir la terminal después. Comprueba con `ffmpeg -version`.

## Siguientes pasos

1. [Organizar los clips](tutoriales/02-organizar-clips.md)
2. [Etiquetarlos](tutoriales/03-etiquetar-clips.md)
3. [Crear tu primer vídeo](tutoriales/05-crear-video.md)

Los comandos de terminal están en [tutoriales/09-linea-de-comandos.md](tutoriales/09-linea-de-comandos.md).
