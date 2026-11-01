# 8. Problemas frecuentes

## Instalación

### "No se ha encontrado Python 3.10 o superior" al ejecutar `instalar.bat`
Instala Python desde <https://www.python.org/downloads/> y marca **"Add python.exe to PATH"**. Si ya lo instalaste sin marcarla: ejecuta de nuevo el instalador de Python → **Modify/Repair** → marca la casilla. Después **cierra y vuelve a abrir** `instalar.bat`.

### Windows dice "Windows protegió su PC"
Pulsa **Más información → Ejecutar de todas formas**. Los `.bat` son texto plano; puedes revisarlos con el Bloc de notas.

### La instalación se queda parada o falla al descargar
Es una descarga grande (~3 GB). Revisa tu conexión y vuelve a ejecutar `instalar.bat`: continúa donde se quedó. Si falla con un error de "Could not find a version" de torch, tu Python es demasiado nuevo o antiguo para sus paquetes: instala **Python 3.11 o 3.12**, borra la carpeta `venv` y vuelve a ejecutar.

### Antivirus bloquea algo
Añade la carpeta del programa a las excepciones del antivirus, o revisa que no estés en una ruta protegida.

### `iniciar.bat`: "Todavia no esta instalado"
Falta la carpeta `venv`: ejecuta `instalar.bat` primero.

---

## Al abrir el programa

### Se cierra la ventana negra enseguida
Abre una ventana de terminal en la carpeta (barra de direcciones del explorador → escribe `cmd` → Enter) y ejecuta `iniciar.bat` desde ahí para ver el error.

### El navegador no se abre
Abre tú `http://127.0.0.1:8000`.

### "Address already in use" / puerto 8000 ocupado
Hay otra copia abierta o otro programa usando el puerto. Cierra la otra ventana negra, o usa otro puerto desde la terminal: `venv\Scripts\python src\main.py serve --port 8001`.

### "Database not initialized"
En **Dashboard** pulsa **Initialize DB**.

---

## Etiquetado

### El primer clip tarda mucho
Se está cargando el modelo de IA (y si el paso 5 del instalador falló, descargándolo). Espera; los siguientes van más rápido.

### Va muy lento
Sin tarjeta NVIDIA usa la CPU. Es normal. Para comprobar si usa la GPU, abre una terminal en la carpeta y ejecuta `venv\Scripts\python -c "import torch; print(torch.cuda.is_available())"`: `True` = GPU activa. Si tienes NVIDIA y sale `False`, actualiza los drivers y borra `venv` para reinstalar.

### `warning nombre.mp4: ...` en el registro
Ese archivo está dañado o no se puede leer. Los demás siguen. Prueba a abrirlo en un reproductor; si falla ahí, está corrupto.

### "No video files found"
La carpeta elegida no contiene vídeos `.mp4 .mov .avi .mkv .webm`, o elegiste una carpeta vacía.

---

## Crear el vídeo

### Error "No clips in database ... Run `tag` first"
La biblioteca está vacía o no tiene clips del vibe elegido. Etiqueta tus clips ([tutorial 3](03-etiquetar-clips.md)) o prueba con vibe `Any`.

### Error "segment too long" / no hay clip para un tramo
Hay una frase tan larga que ningún clip llega al 50% de su duración. Soluciones: añade más marcas intermedias a la letra, añade clips más largos, o prueba con vibe `Any`.

### Error "No single anime has enough clips..."
Modo "Single anime" activo, pero ninguna serie tiene clips suficientes para cubrir todos los tramos sin repetir. Añade más clips a las series, o desmarca la casilla.

### Error "No anime folders found in clip paths"
Marcaste "Single anime" pero tus clips no están en `...\anime\<Serie>\...`. Mira [tutorial 2](02-organizar-clips.md).

### Todos los clips son parecidos
Tienes pocos clips de ese vibe. Añade más variedad o usa vibe `Any`.

---

## DaVinci Resolve

### "Media Offline"
Resolve no encuentra los clips. Causas: moviste/renombraste los archivos, cambió la letra del disco o el disco externo no está conectado. Reconecta el disco o vuelve a poner los clips en su sitio, y en Resolve: clic derecho en los clips → **Relink Selected Clips…** y apunta a la carpeta correcta. Si cambiaste de sitio la colección, re-etiqueta ([tutorial 6](06-gestionar-biblioteca.md)) y genera una línea de tiempo nueva.

### El vídeo va más rápido/lento que la canción
El FPS de la línea de tiempo no coincide con el elegido al generar. Genera de nuevo con el mismo FPS del proyecto de Resolve.

### No encuentro la opción de importar
**File → Import → Timeline…** (algunas versiones: *Import Timeline → Import AAF, EDL, XML…*). Elige el `.fcpxml`.

### La canción o los subtítulos no vienen en la línea de tiempo
Es lo esperado: se añaden a mano (pasos 6 y 7 del [tutorial 5](05-crear-video.md)).

---

## Lyric Sync

### No suena el audio / no se carga
Comprueba que el formato sea `.mp3 .wav .flac .m4a .ogg .aac` y que la ruta exista. Prueba otro navegador (Chrome, Edge, Firefox).

### Las marcas con la barra espaciadora no funcionan
Haz clic primero en la página (fuera de cuadros de texto) y comprueba que estés en la pestaña **Lyric Sync** durante la fase de tap.

---

## Subir a redes

Los errores de subida dependen mucho de las condiciones de TikTok y Meta. Consulta el registro (**Upload → Recent uploads**) y, si el error es de autenticación, repite **Authenticate**. Más detalles en [tutorial 7](07-subir-a-redes.md).

---

¿Sigues atascado? Abre un *issue* en el repositorio de GitHub incluyendo el mensaje de error completo de la ventana negra.
