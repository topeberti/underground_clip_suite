# Video Generator

Crea automáticamente **vídeos musicales / lyric edits** (AMV) verticales para TikTok: le das una canción, su letra con los tiempos y tu biblioteca de clips, y el programa monta un vídeo con un clip distinto en cada frase de la letra. **DaVinci Resolve** lo termina y lo exporta con un solo clic.

## Cómo funciona y qué necesitas

> **El vídeo final lo exporta DaVinci Resolve** (gratuito). Video Generator elige los clips y deja un script en el menú de Resolve (**Workspace → Scripts → videogen_build**). Un clic ahí crea las líneas de tiempo en vertical (1080×1920) con la canción y la letra como subtítulos, y exporta los `.mp4`.
>
> - Hay que preparar **una vez** una línea de tiempo plantilla en Resolve ([tutorial 5](tutoriales/05-crear-video.md)).
> - Resolve **no necesita estar abierto** mientras generas; solo lo usas después.
> - Con otros editores (Premiere, Final Cut, Kdenlive…) **no está probado**. Solo se garantiza DaVinci Resolve.

```
Tus clips + canción + letra  →  Video Generator  →  script de Resolve  →  1 clic en Resolve  →  vídeos .mp4
```

## ¿Qué hace?

1. **Etiqueta tus clips** con inteligencia artificial (modelo CLIP): detecta qué aparece en cada clip y cuánta energía tiene (*energic*, *sad* o *neutral*).
2. **Sincroniza la letra** con la canción: pulsas una tecla al inicio de cada frase y escribes el texto. Se guarda un archivo `.srt`.
3. **Monta los vídeos**: elige clips al azar según el ambiente (vibe) que quieras, cortando en cada frase de la letra, y prepara el script de Resolve que los encuadra en vertical, pone la letra y los exporta.
   - **Nuevo: edits con imágenes de Pinterest.** En vez de clips, cada frase se llena con una ráfaga de imágenes de una categoría (una carpeta), que cambian **al ritmo de la canción** y salen a su **tamaño real**, sin redimensionar ([tutorial 5](tutoriales/05-crear-video.md#edits-con-imágenes-de-pinterest)).
   - **Descarga de Pinterest:** pega el enlace de un pin o de un **tablero entero** en la pestaña **Pinterest** y se bajan todas sus imágenes a tamaño original, directamente a la carpeta de una categoría ([tutorial 5](tutoriales/05-crear-video.md#edits-con-imágenes-de-pinterest)).
4. **(Opcional y experimental)** Subida en lote a TikTok e Instagram Reels. La subida a Instagram no se ha probado con éxito todavía; no cuentes con ella.

Todo se maneja desde una **página web local** (solo en tu ordenador, no se sube nada a internet).

## Inicio rápido (Windows)

1. Instala **Python 3.10 o superior** desde [python.org](https://www.python.org/downloads/) marcando la casilla **"Add python.exe to PATH"**.
2. Descarga este repositorio (botón verde **Code → Download ZIP**) y descomprímelo.
3. Haz **doble clic en `instalar.bat`** y espera (la primera vez descarga ~3 GB y tarda de 5 a 20 minutos).
4. Haz **doble clic en `iniciar.bat`**: se abre el programa en tu navegador.
5. Sigue los tutoriales.

## Tutoriales (paso a paso, para no técnicos)

| # | Tutorial | Para qué |
|---|----------|----------|
| 1 | [Instalación](tutoriales/01-instalacion.md) | Instalar todo desde cero |
| 2 | [Organizar los clips](tutoriales/02-organizar-clips.md) | **Imprescindible**: cómo ordenar las carpetas |
| 3 | [Etiquetar los clips](tutoriales/03-etiquetar-clips.md) | Crear la base de datos |
| 4 | [Sincronizar la letra](tutoriales/04-sincronizar-letras.md) | Crear el `.srt` |
| 5 | [Crear el vídeo](tutoriales/05-crear-video.md) | Generar y exportar con un clic en DaVinci Resolve |
| 6 | [Gestionar la biblioteca](tutoriales/06-gestionar-biblioteca.md) | Borrar clips, series, estadísticas |
| 7 | [Subir a redes](tutoriales/07-subir-a-redes.md) | TikTok / Instagram (experimental) |
| 8 | [Problemas frecuentes](tutoriales/08-problemas-frecuentes.md) | Si algo falla |
| 9 | [Línea de comandos](tutoriales/09-linea-de-comandos.md) | Para usuarios avanzados |

Índice completo: [tutoriales/README.md](tutoriales/README.md).

## Requisitos

- Windows 10 u 11
- Python 3.10 o superior
- DaVinci Resolve (la versión gratuita sirve; probado con la 21.2)
- ~5 GB de disco libre para la instalación (sin contar tus clips)
- Opcional: tarjeta NVIDIA (etiquetado mucho más rápido) y ffmpeg (para los edits de Pinterest y para subir a redes)

## Documentación técnica

- [SETUP.md](SETUP.md): referencia de instalación (manual y automática)
- [ARCHITECTURE.md](ARCHITECTURE.md): cómo funciona por dentro
- [docs/resolve_automation.md](docs/resolve_automation.md): el script de Resolve y las limitaciones de su API
- [docs/](docs/): base de datos, sistema de vibes, formato SRT
