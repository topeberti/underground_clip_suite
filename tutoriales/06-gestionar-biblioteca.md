# 6. Gestionar la biblioteca de clips

Todo esto se hace en las pestañas **Dashboard** y **Library**.

## Ver estadísticas

**Dashboard → Refresh** muestra: total de clips, horas totales de vídeo, clips por vibe y reparto de energía (baja / media / alta).

## Buscar y revisar clips

**Library → Clips**:

- Escribe en **Search path…** parte de una ruta o nombre.
- Filtra por vibe con el desplegable.
- Usa **← Prev / Next →** para paginar.

## Quitar un clip concreto

En la tabla de clips, pulsa el botón rojo **Remove** al final de la fila. Solo se quita de la base de datos; **el archivo de vídeo no se toca**.

## Quitar una serie entera

Útil si ya no quieres usar una serie, o si moviste su carpeta y debes re-etiquetarla.

1. **Library → Remove an anime**.
2. Escribe el nombre (o parte) y pulsa **Preview**. Verás cuántos clips coinciden y sus rutas.
   > Coincide con **cualquier parte de la ruta**: `Naruto` también quitaría `Naruto Shippuden` y una carpeta `D:\Naruto_fans\...`. Revisa siempre la lista.
3. Para quitarlos solo de la biblioteca, pulsa **Remove**.
4. La casilla **"Also delete the video files from disk (irreversible)"** además **borra los archivos del disco para siempre**. Déjala desmarcada si no estás completamente seguro.

## Mover los clips a otro sitio (disco nuevo, otra carpeta)

La base de datos guarda rutas exactas, así que tras mover los clips:

1. Borra de la biblioteca los clips antiguos (**Remove an anime** con el nombre de la serie, **sin** marcar borrar archivos).
2. Etiqueta la carpeta en su nueva ubicación ([tutorial 3](03-etiquetar-clips.md)).

## Rehacer el etiquetado de un clip o carpeta

- Un clip: pulsa **Re-tag** en su fila de la tabla (o usa el comando `retag`, ver [línea de comandos](09-linea-de-comandos.md)).
- Una carpeta entera: **Library → Re-tag clips already in the database** + **Start tagging**.

## Copia de seguridad

Toda tu biblioteca es un único archivo: `clips_db\clips.db`. Cópialo a un lugar seguro de vez en cuando. Para empezar de cero, cierra el programa, borra ese archivo y ejecuta `iniciar.bat` (se crea uno vacío).
