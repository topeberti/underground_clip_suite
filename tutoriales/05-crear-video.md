# 5. Crear el vídeo con DaVinci Resolve

El programa monta los vídeos y deja preparado un **script para DaVinci Resolve**. En Resolve haces **un solo clic** y él crea cada línea de tiempo y exporta los `.mp4` terminados: en vertical (1080×1920), con la canción y la letra incrustada como subtítulos.

Necesitas tener hecho antes:

- ✅ Clips etiquetados ([tutorial 3](03-etiquetar-clips.md)).
- ✅ Una canción (`.mp3`, `.wav`…) y su archivo `.srt` ([tutorial 4](04-sincronizar-letras.md)).
- ✅ DaVinci Resolve instalado ([tutorial 1](01-instalacion.md)). La versión gratuita sirve.

---

## Parte 1 (solo la primera vez): la plantilla en Resolve

El estilo de los subtítulos (tipo de letra, tamaño, posición) no se puede poner desde un script, así que se copia de una **línea de tiempo plantilla** que preparas una vez.

1. Abre DaVinci Resolve y crea un proyecto para tus vídeos de TikTok (o usa uno que ya tengas).
2. En el **Media Pool**, clic derecho → **Timelines → Create New Timeline…**
   - **Timeline Name:** `videogen_template` (escríbelo exactamente así).
   - Desmarca **Use Project Settings**. En la pestaña **Format** pon **1080 × 1920** y **30** fps.
3. Abre esa línea de tiempo. Clic derecho en la cabecera de pistas → **Add Subtitle Track**.
4. Arrastra un **Subtitle** (Effects → Titles → Subtitles) a esa pista.
5. Selecciónalo y en el **Inspector**, pestaña **Track**, aplica el preset **Subtitle 1** (o el estilo que quieras para todos tus vídeos).
6. Deja ese subtítulo ahí: el script lo borra de cada copia, pero el estilo se conserva.

> Si cambias el estilo de la plantilla, cambia en todos los vídeos que hagas después.
>
> **Ojo:** el script pone la escala de imagen del proyecto en *Scale full frame with crop*. Si en el mismo proyecto tienes líneas de tiempo horizontales que usan los ajustes del proyecto, también se recortarán. Usa un proyecto solo para estos vídeos.

---

## Parte 2: Generar los vídeos en el programa

1. Abre el programa (`iniciar.bat`) y ve a la pestaña **Build**.
2. Rellena los campos:

| Campo | Qué poner |
|---|---|
| **Song** | La canción. Pulsa **Browse** y elígela |
| **Lyrics (.srt)** | El archivo de letra con tiempos |
| **Vibe** | `Any` = todos los clips · `energic` = clips intensos · `sad` = clips calmados. Con un vibe elegido también entran clips `neutral`, con menos probabilidad |
| **FPS** | Déjalo en **30** (igual que la plantilla) |
| **Project name** | Nombre base de los vídeos, sin los símbolos `\ / : * ? " < > \|` |
| **Timelines** | Cuántas versiones distintas generar (cada una con clips al azar diferentes) |
| **Output folder** | Dónde guardar los archivos auxiliares. Vacío = carpeta `timelines` junto a la canción |
| **Restrict each edit to a single anime** | Marcada: cada vídeo usa clips de **una sola serie** (elegida al azar). Requiere la estructura `anime\<Serie>` ([tutorial 2](02-organizar-clips.md)) y suficientes clips por serie |

3. Pulsa **Build**. Al terminar aparece **Done**.

### Qué hace el programa por dentro

- Hace **un corte en cada inicio de frase** de la letra y elige para cada tramo un clip al azar **lo bastante largo** (nunca ralentiza clips: Resolve no permite cambiar la velocidad desde un script).
- Evita repetir el mismo clip dos veces seguidas. En modo "Same anime" no repite ningún clip.
- Mide cada clip: si trae **bandas negras dentro de la imagen** (por ejemplo *Arcane*), calcula el zoom justo para quitarlas.
- Parte en **dos líneas** las frases de más de 20 letras para que quepan en vertical. Tu `.srt` original no se toca.
- Guarda el script `videogen_build` en el menú de scripts de Resolve. **Cada Build lo sustituye**, así que ejecútalo en Resolve antes de generar otra canción.

---

## Parte 3: Un clic en Resolve

1. En Resolve, abre el proyecto que tiene la plantilla `videogen_template`.
2. Menú **Workspace → Scripts → videogen_build**. (Si no aparece, cierra y vuelve a abrir Resolve.)
3. Espera. El script:
   - crea una línea de tiempo por cada versión (copia de la plantilla),
   - pone los subtítulos, los clips (rellenando la pantalla vertical) y la canción,
   - y manda a exportar todos los vídeos.
4. Los `.mp4` aparecen en la carpeta **`videos`** junto a la canción, listos para la pestaña **Upload** ([tutorial 7](07-subir-a-redes.md)).

> Nunca sobrescribe vídeos de un Build anterior: si `videos\tema_1.mp4` ya existe, el nuevo se llamará distinto. Pero si ejecutas **el mismo** script dos veces, la segunda vez sí reemplaza los vídeos de la primera.

### Retocar a mano

Las líneas de tiempo se quedan en el proyecto. Si quieres cambiar algo (un clip, un efecto…), ábrela, retócala y vuelve a exportarla desde la página **Deliver**.

### Exportar con tus propios ajustes (opcional)

Por defecto exporta en H.264 `.mp4` 1080×1920 con la letra incrustada. Si quieres otros ajustes, configúralos en **Deliver** y guárdalos como preset con el nombre **`videogen_tiktok`**: el script lo usará automáticamente.

---

## Método manual (sin script)

El programa también guarda un `.fcpxml` por versión en la carpeta de salida. Puedes importarlo con **File → Import → Timeline…** y añadir a mano la canción y la letra (**File → Import → Subtitle…**). No incluye el formato vertical ni el zoom.

---

## Consejos para mejores resultados

- **Genera varias versiones** (Timelines = 5) y quédate con la mejor.
- **Más clips = más variedad.** Con pocos clips verás repeticiones.
- **Clips largos ayudan:** como no se ralentizan clips, cada frase necesita un clip al menos igual de largo. Si la última frase acaba mucho antes que la canción, el final necesita un clip muy largo y el Build fallará: recorta la canción o añade una frase al final del `.srt`.

Siguiente → [6. Gestionar la biblioteca](06-gestionar-biblioteca.md) · [7. Subir a redes](07-subir-a-redes.md)
