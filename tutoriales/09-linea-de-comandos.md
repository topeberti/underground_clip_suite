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
| `build ...` | Genera líneas de tiempo `.fcpxml` |
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

## Opciones de `upload-batch`

`--platforms` (tiktok instagram), `--delay` (10 s), `--privacy` (public / followers / private), `--skip-normalize`, `--dry-run`, `--config`.

Más detalle técnico en [ARCHITECTURE.md](../ARCHITECTURE.md) y [docs/](../docs/).
