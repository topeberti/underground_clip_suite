# Video Generator

Crea automáticamente el **borrador de un vídeo musical / lyric edit** (AMV): le das una canción, su letra con los tiempos y tu biblioteca de clips, y el programa genera una línea de tiempo para **DaVinci Resolve** con un clip distinto en cada frase de la letra. Tú solo tienes que pulir el resultado.

## Cómo funciona y qué necesitas

> **Video Generator NO crea el vídeo final.** Crea un **borrador de línea de tiempo** (archivo `.fcpxml`). Para convertirlo en un vídeo necesitas **DaVinci Resolve** (gratuito): lo abres allí, añades la canción y los subtítulos, retocas lo que quieras y exportas.
>
> - Resolve **no necesita estar abierto** mientras generas la línea de tiempo; solo lo usas después.
> - Con otros editores (Premiere, Final Cut, Kdenlive…) **no está probado**. Solo se garantiza DaVinci Resolve.

```
Tus clips + canción + letra  →  Video Generator  →  archivo .fcpxml  →  DaVinci Resolve  →  vídeo final
```

## ¿Qué hace?

1. **Etiqueta tus clips** con inteligencia artificial (modelo CLIP): detecta qué aparece en cada clip y cuánta energía tiene (*energic*, *sad* o *neutral*).
2. **Sincroniza la letra** con la canción: pulsas una tecla al inicio de cada frase y escribes el texto. Se guarda un archivo `.srt`.
3. **Genera la línea de tiempo** (`.fcpxml`) eligiendo clips al azar según el ambiente (vibe) que quieras, cortando en cada frase de la letra.
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
| 5 | [Crear el vídeo](tutoriales/05-crear-video.md) | Generar y abrir en DaVinci Resolve |
| 6 | [Gestionar la biblioteca](tutoriales/06-gestionar-biblioteca.md) | Borrar clips, series, estadísticas |
| 7 | [Subir a redes](tutoriales/07-subir-a-redes.md) | TikTok / Instagram (experimental) |
| 8 | [Problemas frecuentes](tutoriales/08-problemas-frecuentes.md) | Si algo falla |
| 9 | [Línea de comandos](tutoriales/09-linea-de-comandos.md) | Para usuarios avanzados |

Índice completo: [tutoriales/README.md](tutoriales/README.md).

## Requisitos

- Windows 10 u 11
- Python 3.10 o superior
- DaVinci Resolve 18 o superior (la versión gratuita sirve)
- ~5 GB de disco libre para la instalación (sin contar tus clips)
- Opcional: tarjeta NVIDIA (etiquetado mucho más rápido) y ffmpeg (solo para subir a redes)

## Documentación técnica

- [SETUP.md](SETUP.md): referencia de instalación (manual y automática)
- [ARCHITECTURE.md](ARCHITECTURE.md): cómo funciona por dentro
- [docs/](docs/): base de datos, sistema de vibes, formato SRT
