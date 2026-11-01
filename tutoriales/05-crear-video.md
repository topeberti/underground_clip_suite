# 5. Crear el vídeo y abrirlo en DaVinci Resolve

> **Importante:** el programa **no genera un archivo de vídeo**. Genera archivos `.fcpxml` (borradores de línea de tiempo) que se abren en **DaVinci Resolve**; allí añades la canción y los subtítulos y exportas el vídeo final (Partes 2 y 3). Necesitas Resolve instalado ([tutorial 1](01-instalacion.md)).

Necesitas tener hecho antes:

- ✅ Clips etiquetados ([tutorial 3](03-etiquetar-clips.md)).
- ✅ Una canción (`.mp3`, `.wav`…) y su archivo `.srt` ([tutorial 4](04-sincronizar-letras.md)).

---

## Parte 1: Generar las líneas de tiempo

1. Abre el programa (`iniciar.bat`) y ve a la pestaña **Build**.
2. Rellena los campos:

| Campo | Qué poner |
|---|---|
| **Song** | La canción. Pulsa **Browse** y elígela |
| **Lyrics (.srt)** | El archivo de letra con tiempos |
| **Vibe** | `Any` = todos los clips · `energic` = clips intensos · `sad` = clips calmados. Con un vibe elegido también entran clips `neutral`, con menos probabilidad |
| **FPS** | Fotogramas por segundo. Déjalo en **30** salvo que tu proyecto de Resolve use otro (24, 25, 60…). Debe coincidir |
| **Project name** | Nombre del proyecto, sin los símbolos `\ / : * ? " < > \|` |
| **Timelines** | Cuántas versiones distintas generar de una vez (cada una con clips aleatorios diferentes). Prueba con 3–5 y elige la que más te guste |
| **Output folder** | Dónde guardar los archivos. Vacío = carpeta `timelines` junto a la canción |
| **Restrict each edit to a single anime** | Marcada: cada vídeo usa clips de **una sola serie** (elegida al azar). Requiere la estructura `anime\<Serie>` ([tutorial 2](02-organizar-clips.md)) y suficientes clips por serie |

3. Pulsa **Build**.
4. En unos segundos aparece **Done** con la lista de archivos `.fcpxml` creados.

> Cada vez que pulses Build saldrá un montaje distinto, porque los clips se eligen al azar. Si no te gusta, vuelve a generar.

### Qué hace el programa por dentro (para entender el resultado)

- Hace **un corte en cada inicio de frase** de la letra.
- Para cada tramo elige un clip al azar que dure lo suficiente (si es algo más corto, lo ralentiza hasta un mínimo del 50% de velocidad).
- Evita repetir el mismo clip dos veces seguidas. En modo "Same anime" no repite ningún clip.

---

## Parte 2: Abrir en DaVinci Resolve

1. Abre **DaVinci Resolve** y crea (o abre) un proyecto.
2. *(Recomendado)* Comprueba los ajustes: **File → Project Settings → Timeline frame rate** = el FPS que elegiste (ej. 30).
3. Menú **File → Import → Timeline…** (o **Import Timeline → Import AAF, EDL, XML…**).
4. Selecciona el archivo `.fcpxml` generado y confirma. En la ventana de opciones puedes dejar todo por defecto.
5. Aparece la línea de tiempo con todos los clips ya colocados.
6. **Añade la canción:** arrastra el archivo de audio desde el Media Pool (o desde el explorador de Windows) a una pista de audio, al principio (posición 00:00:00:00).
7. **Añade la letra como subtítulos:** **File → Import → Subtitle…** y elige tu `.srt`. Aparece una pista de subtítulos sincronizada.
8. Pulsa espacio para reproducir y ajusta lo que quieras: cambiar un clip, añadir efectos, transiciones, tipografía de los subtítulos…

> El programa te da un **borrador** muy avanzado, pero el toque final es tuyo.

### Si ves "Media Offline" (clips en rojo/sin imagen)

Resolve no encuentra los archivos. Casi siempre es porque moviste o renombraste los clips o cambió la letra del disco. Soluciones en [Problemas frecuentes](08-problemas-frecuentes.md#media-offline-en-davinci-resolve).

---

## Parte 3: Exportar

1. Ve a la página **Deliver** (abajo del todo).
2. Elige un preset (por ejemplo **YouTube 1080p**, o **H.264 Master**; para TikTok / Reels en vertical, cambia la resolución a 1080×1920 en la configuración de la línea de tiempo antes).
3. Elige carpeta y nombre, pulsa **Add to Render Queue** y luego **Render All**.

---

## Consejos para mejores resultados

- **Genera varias versiones** (Timelines = 5) y quédate con la mejor, o mezcla.
- **Más clips = más variedad.** Con pocos clips verás repeticiones.
- **Prueba los vibes:** un tema tranquilo con `sad`, uno potente con `energic`.
- Para vídeos verticales (TikTok), tus clips horizontales se verán con bandas o recortados según la configuración de Resolve: ajusta el escalado en el Inspector.

Siguiente → [6. Gestionar la biblioteca](06-gestionar-biblioteca.md) · [7. Subir a redes](07-subir-a-redes.md)
