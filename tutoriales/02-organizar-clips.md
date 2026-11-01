# 2. Organizar los clips (¡importante!)

La forma en que ordenes tus carpetas **antes de etiquetar** decide si funcionan bien dos cosas:

- El modo **"un solo anime por vídeo"** (Same anime).
- Poder **borrar una serie entera** de la biblioteca.

Dedica 10 minutos a esto y te ahorrarás repetirlo todo después.

---

## La estructura recomendada

Crea **una carpeta principal llamada exactamente `anime`** (en minúsculas) y dentro **una carpeta por cada serie o película**. Dentro de cada serie puedes poner los clips tal cual o en las subcarpetas que quieras.

```
D:\MisClips\
└── anime\                          ← se debe llamar exactamente "anime"
    ├── Naruto\                     ← una carpeta por serie
    │   ├── pelea_01.mp4
    │   ├── pelea_02.mp4
    │   └── Temporada2\             ← subcarpetas dentro de la serie: sin problema
    │       └── pelea_03.mp4
    ├── OnePiece\
    │   ├── ep300_clip.mp4
    │   └── ep301_clip.mp4
    └── AttackOnTitan\
        └── ...
```

Dónde está `D:\MisClips` es cosa tuya (puede ser un disco externo, ver reglas abajo). Lo que importa es que **justo dentro de `anime` haya una carpeta por serie**.

### Cómo lo interpreta el programa

> El nombre de la serie es **la carpeta que está directamente dentro de `anime`**, sin importar a qué profundidad esté el clip.

| Ruta del clip | Serie detectada |
|---|---|
| `D:\MisClips\anime\Naruto\pelea_01.mp4` | Naruto |
| `D:\MisClips\anime\Naruto\Temporada2\pelea_03.mp4` | Naruto |
| `D:\MisClips\anime\OnePiece\ep300_clip.mp4` | OnePiece |

### Ejemplos incorrectos

| Estructura | Problema |
|---|---|
| `D:\MisClips\Naruto\pelea.mp4` | Falta la carpeta `anime`. Los clips se etiquetan y valen para vídeos normales, pero **no funciona** "Same anime" |
| `D:\MisClips\Anime Clips\Naruto\pelea.mp4` | La carpeta no se llama `anime` (debe ser exactamente ese nombre) |
| `D:\MisClips\anime\pelea.mp4` | El clip está suelto dentro de `anime`, sin carpeta de serie |
| `D:\MisClips\anime\Naruto\...` y `D:\Otros\anime\Naruto\...` | Mezcla de ubicaciones: funciona, pero será un lío de gestionar |

---

## ¿Y si no uso anime?

Puedes usar cualquier tipo de vídeo (paisajes, ciudad, películas…). Para eso:

- Pon los clips en **cualquier carpeta**; se etiquetarán igual.
- Simplemente **no actives** la casilla "Restrict each edit to a single anime" al crear el vídeo.
- Si quieres seguir pudiendo usar "Same anime" con tus colecciones, llama a la carpeta de cada colección dentro de una carpeta `anime` igualmente (por ejemplo `anime\MisPaisajes\`). Es solo una convención de nombres.

---

## Reglas de oro

1. **No muevas ni renombres los clips ni las carpetas después de etiquetarlos.**
   La base de datos guarda la ruta exacta de cada archivo (por ejemplo `D:\MisClips\anime\Naruto\pelea_01.mp4`). Si cambias algo, el programa no encontrará el clip y DaVinci Resolve mostrará "Media Offline".
   *Si tienes que moverlos:* bórralos de la biblioteca ([tutorial 6](06-gestionar-biblioteca.md)) y vuelve a etiquetar la carpeta nueva.

2. **Elige una ubicación definitiva** (por ejemplo un disco secundario) antes de etiquetar. Si es un disco externo, comprueba que siempre se monte con la **misma letra** (`D:`, `E:`…).

3. **No hace falta separar los clips por ambiente** (triste / enérgico). El programa lo calcula solo analizando el movimiento.

4. **Un clip = una escena.** Mejor clips ya cortados de **3 a 30 segundos**. Un vídeo de 24 minutos entero se trata como un solo clip y no sirve bien para el montaje.

5. **Duración mínima útil: unos 2–3 segundos.** Cada frase de la letra necesita un clip; si una frase dura 8 s, solo valen clips de al menos 4 s (se pueden ralentizar hasta la mitad de velocidad, no más). Los clips demasiado cortos se descartan para esas frases.

6. **Formatos admitidos:** `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` (mayúsculas o minúsculas da igual). Otros archivos de la carpeta se ignoran.

7. **Nombres de carpeta sencillos.** Funcionan los espacios y los acentos, pero los nombres cortos y sin símbolos raros evitan problemas. El nombre de la serie es el que verás al buscar o borrar, así que ponle uno reconocible (`Naruto`, no `NRT_v2_final`).

8. **Cantidad:** cuantos más clips, más variedad. Para que el modo "Same anime" funcione, **cada serie necesita clips suficientes para cubrir todas las frases sin repetir ninguno** (por ejemplo, una canción con 40 frases necesita al menos 40 clips adecuados de esa serie).

---

## Cómo añadir series nuevas más adelante

1. Crea la carpeta nueva dentro de `anime\` (por ejemplo `anime\Bleach\`) y mete los clips.
2. Vuelve a la pestaña **Library** y etiqueta **solo esa carpeta nueva** (o toda `anime`: los clips ya etiquetados se saltan automáticamente).

Siguiente paso → [3. Etiquetar los clips](03-etiquetar-clips.md)
