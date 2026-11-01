# 1. Instalación

Tiempo estimado: **15 a 30 minutos** (casi todo es esperar descargas). Solo se hace una vez.

## Qué vas a necesitar

- Un PC con **Windows 10 u 11**.
- Conexión a internet (se descargan unos 3 GB).
- Unos **5 GB libres** en disco.
- **DaVinci Resolve** (la versión gratuita vale): <https://www.blackmagicdesign.com/products/davinciresolve>
- Tus clips de vídeo y la canción que quieras usar.

---

## Cómo encaja DaVinci Resolve

Video Generator **no exporta un vídeo terminado**: genera un borrador de línea de tiempo (`.fcpxml`) que se abre en **DaVinci Resolve**, donde añades la canción y los subtítulos, retocas y exportas. Por eso **necesitas Resolve instalado** para obtener el vídeo final (no hace falta tenerlo abierto mientras usas Video Generator). Otros editores no están probados.

## Paso 0: Instalar DaVinci Resolve

1. Descarga **DaVinci Resolve** (la versión **gratuita** es suficiente) desde <https://www.blackmagicdesign.com/products/davinciresolve>. Pide un formulario con tus datos antes de la descarga.
2. Instálalo (versión 18 o superior) y ábrelo una vez para completar su configuración inicial.
3. La versión gratuita sirve para todo este tutorial. Sus limitaciones (algunos efectos y opciones de exportación avanzadas) no afectan a importar la línea de tiempo.

---

## Paso 1: Instalar Python

Python es el lenguaje en el que está hecho el programa. Solo hay que instalarlo, no tendrás que programar nada.

1. Entra en <https://www.python.org/downloads/> y pulsa el botón amarillo de descarga (**recomendado: Python 3.11 o 3.12**; sirve cualquiera a partir de 3.10).
2. Abre el instalador descargado.
3. **MUY IMPORTANTE:** en la primera pantalla, marca la casilla de abajo **"Add python.exe to PATH"**.
4. Pulsa **Install Now** y espera a que termine.

> Si ya tienes Python instalado, comprueba que sea 3.10 o superior: pulsa la tecla Windows, escribe `cmd`, abre "Símbolo del sistema" y escribe `python --version`.

---

## Paso 2: Descargar Video Generator

**Opción fácil (sin Git):**

1. En la página del repositorio en GitHub, pulsa el botón verde **Code** y luego **Download ZIP**.
2. Haz clic derecho en el ZIP → **Extraer todo…**
3. Mueve la carpeta resultante a un sitio fijo y con ruta corta, por ejemplo `C:\VideoGenerator`.

> Evita carpetas como "Descargas" o el Escritorio: más tarde no querrás moverla. Evita también rutas muy largas.

**Opción Git (si ya lo usas):** `git clone <url-del-repositorio>`

---

## Paso 3: Ejecutar el instalador

1. Abre la carpeta del programa.
2. Haz **doble clic en `instalar.bat`**.
3. Si Windows muestra "Windows protegió su PC" (SmartScreen): pulsa **Más información → Ejecutar de todas formas**. El archivo es un simple texto con los pasos de instalación; puedes abrirlo con el Bloc de notas para comprobarlo.
4. Se abre una ventana negra con texto. **No la cierres.** Verás 6 pasos:

| Paso | Qué hace | Tiempo aprox. |
|---|---|---|
| 1/6 | Busca Python | segundos |
| 2/6 | Crea la carpeta `venv` (entorno privado del programa) | segundos |
| 3/6 | Instala PyTorch (la librería de IA). **La descarga más grande** | 3–15 min |
| 4/6 | Instala el resto de librerías | 2–5 min |
| 5/6 | **Descarga el modelo de etiquetado (CLIP)** | 1–3 min |
| 6/6 | Crea la base de datos vacía | segundos |

5. Al final verás **"Instalacion completada con exito"**. Pulsa una tecla para cerrar.

> Si ves un error, no pasa nada: vuelve a ejecutar `instalar.bat` (continúa donde se quedó) o mira [Problemas frecuentes](08-problemas-frecuentes.md).

### ¿Con tarjeta gráfica NVIDIA o sin ella?

El instalador lo detecta solo:

- **Con NVIDIA:** instala la versión con GPU. El etiquetado es **5–10 veces más rápido**.
- **Sin NVIDIA (o AMD / gráfica integrada):** usa la CPU. Funciona igual, solo es más lento al etiquetar (ver [Etiquetar](03-etiquetar-clips.md)).

### Sobre el modelo de etiquetado

El "cerebro" que reconoce qué hay en cada clip es **OpenCLIP (ViT-B-32)**. El instalador lo descarga en el paso 5 (~350 MB) y lo guarda en tu usuario de Windows. Se descarga **una sola vez**, y después funciona sin internet. No tienes que instalar nada más para el etiquetado.

---

## Paso 4: Abrir el programa

1. Haz **doble clic en `iniciar.bat`**.
2. Se abre tu navegador en `http://127.0.0.1:8000` con la interfaz de Video Generator (si no se abre, escribe esa dirección tú mismo).
3. **Deja abierta la ventana negra** mientras uses el programa. Para cerrarlo, cierra esa ventana.

Verás cinco pestañas: **Dashboard, Library, Lyric Sync, Build y Upload**.

> `127.0.0.1` significa "este mismo ordenador": nada se sube a internet y nadie más puede entrar.

---

## Paso 5 (solo si quieres subir a TikTok/Instagram): ffmpeg

No lo necesitas para crear vídeos. Solo para la función de subida (ver [Subir a redes](07-subir-a-redes.md)).

1. Pulsa la tecla Windows, escribe `cmd` y abre "Símbolo del sistema".
2. Escribe `winget install ffmpeg` y pulsa Enter.
3. Cierra y vuelve a abrir cualquier ventana de terminal / `iniciar.bat`.

---

## Instalación manual (usuarios avanzados)

Ver [SETUP.md](../SETUP.md#instalación-manual).

## Actualizar el programa más adelante

Descarga el ZIP nuevo y copia **encima** de tu carpeta, pero **conserva** tu carpeta `clips_db` (tu base de datos) y `venv`. Después ejecuta `instalar.bat` otra vez por si hay librerías nuevas.

---

**Siguiente:** [2. Organizar los clips](02-organizar-clips.md)
