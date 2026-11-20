# 9. Línea de comandos (usuarios avanzados)

Todo lo que hace la interfaz web se puede hacer desde la terminal. Abre una terminal **en la carpeta del programa** (barra de direcciones del explorador → `cmd` → Enter) y usa el Python del entorno:

```bat
venv\Scripts\python src\main.py <comando> [opciones]
```

Para evitar escribir `venv\Scripts\python` cada vez: `venv\Scripts\activate` y después `python src\main.py ...`. Ayuda de cualquier comando: `python src\main.py <comando> --help`.

| Comando | Para qué |
|---|---|
| `init-db` | Crea la base de datos (seguro repetirlo) |
| `serve [--port N] [--no-browser]` | Abre la interfaz web |
| `tag --folder RUTA [--force]` | Etiqueta una carpeta |
| `retag --path ARCHIVO` | Re-etiqueta un clip |
| `remove-clip --path ARCHIVO` | Quita un clip de la base de datos |
| `remove-anime --name TEXTO [--dry-run] [--delete-files]` | Quita todos los clips cuya ruta contenga TEXTO |
| `stats` | Estadísticas de la biblioteca |
| `lyric-sync AUDIO [-o SALIDA.srt] [--countdown N]` | Sincroniza letras en la terminal (solo Windows) |
| `build ...` | Genera los montajes (`.fcpxml`) y el script `videogen_build` de Resolve |
| `setup-upload [--platform tiktok\|instagram\|all]` | Autentica para subir |
| `upload-batch --folder RUTA --caption "..."` | Sube en lote |
| `upload-status [--last N]` | Historial de subidas |

## Ejemplos

```bat
python src\main.py tag --folder "D:\MisClips\anime"

python src\main.py build --song "D:\Musica\tema.mp3" --lyrics "D:\Musica\tema.srt" ^
  --vibe energic --fps 30 --name tema_v1 --count 5 --same-anime

python src\main.py remove-anime --name "Naruto" --dry-run
```

## Opciones de `build`

| Opción | Por defecto | Descripción |
|---|---|---|
| `--song` | (obligatoria) | Canción |
| `--lyrics` | (obligatoria) | Archivo `.srt` |
| `--vibe` | todos | `energic` o `sad` |
| `--fps` | 30 | FPS de la línea de tiempo |
| `--name` | `video_project` | Nombre del proyecto |
| `--count` | 1 | Cuántas variantes generar |
| `--output-dir` | `output\` | Dónde guardar los `.fcpxml` (nota: la interfaz web usa por defecto `timelines` junto a la canción) |
| `--same-anime` | no | Una sola serie por montaje |
| `--edit-type` | `anime` | `anime` (clips de vídeo) o `pinterest` (imágenes por categoría) |
| `--pinterest-dir` | `C:\Users\berti\Documents\Video\pinterest\media` | Carpeta de imágenes, una subcarpeta por categoría (solo `pinterest`) |
| `--beats-per-image` | 1 | Solo `pinterest`: beats por imagen (`0.125`, `0.25`, `0.5`, `1`, `2`, `4`), o `0` para 0,5 s fijos |

Ejemplo de edit de Pinterest, una imagen cada medio beat:

```bat
python src\main.py build --song "D:\Musica\tema.mp3" --lyrics "D:\Musica\tema.srt" ^
  --edit-type pinterest --beats-per-image 0.5 --name tema_pin --count 3
```

## Descargar imágenes de pines y tableros (`pin-download`)

Baja todas las imágenes de uno o varios pines o tableros enteros a su resolución original. `--category azul` las guarda en `pinterest\media\azul` (o en `--media-dir`), y `--out` elige una carpeta exacta.

```bat
python src\main.py pin-download "https://pinterest.com/usuario/mi-tablero/" "https://pin.it/abc" --category azul
```

## Opciones de `upload-batch`

`--platforms` (tiktok instagram), `--delay` (10 s), `--privacy` (public / followers / private), `--skip-normalize`, `--dry-run`, `--config`.

Más detalle técnico en [ARCHITECTURE.md](../ARCHITECTURE.md) y [docs/](../docs/).
