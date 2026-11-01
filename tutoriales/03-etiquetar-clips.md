# 3. Etiquetar los clips

Etiquetar es dejar que la IA **mire cada clip una vez** y apunte en la base de datos:

- **Etiquetas** de lo que ve (fuego, ciudad de noche, lluvia, multitud…).
- **Energía** (de 0 a 1), calculada a partir del movimiento y los cambios de brillo.
- **Vibe**, según la energía:

| Energía | Vibe | Significado |
|---|---|---|
| 0.6 o más | `energic` | Movimiento, intensidad |
| 0.4 a 0.6 | `neutral` | Versátil (se usa con cualquier vibe, con menos peso) |
| 0.4 o menos | `sad` | Calmado, melancólico |

Esto se hace **una sola vez por clip**. Después, crear vídeos es rápido.

> Antes de empezar: ¿tienes ya los clips ordenados como en [2. Organizar los clips](02-organizar-clips.md)?

---

## Paso a paso

1. Abre el programa con **`iniciar.bat`**.
2. Pestaña **Dashboard**. Si pone *"Database not initialized yet"*, pulsa **Initialize DB**. (Normalmente `iniciar.bat` ya lo hace por ti.)
3. Ve a la pestaña **Library**.
4. En **"Folder of video clips"** pulsa **Browse** y elige la carpeta a etiquetar:
   - Para todo de una vez, elige la carpeta que contiene `anime` (por ejemplo `D:\MisClips`) o la propia `anime`.
   - Para una serie nueva, elige solo su carpeta (por ejemplo `D:\MisClips\anime\Bleach`).
   
   En el selector, navega con doble clic sobre las carpetas y pulsa **Select this folder**.
5. Pulsa **Start tagging**.
6. Verás una barra de progreso y un registro con cada clip:
   - `Tagged nombre.mp4 vibe=energic energy=0.71 tags=[...]` → clip listo.
   - `skip nombre.mp4` → ya estaba etiquetado, se salta.
   - `warning nombre.mp4: ...` → ese clip falló (archivo dañado o formato raro); los demás continúan.
7. Cuando termine, ve a **Dashboard → Refresh** para ver el total de clips, las horas de vídeo y el reparto por vibe.

> La primera vez, el programa carga el modelo de IA y puede tardar medio minuto en mostrar el primer clip. Es normal.

---

## ¿Cuánto tarda?

Depende de tu equipo y de la duración de los clips. Orientativo para clips de ~10 s:

| Equipo | Velocidad aproximada |
|---|---|
| Con tarjeta NVIDIA | 1–3 clips por segundo |
| Solo CPU | 1 clip cada 1–3 segundos |

Para 1000 clips: de 10–20 minutos (GPU) a 1 hora (CPU). Puedes dejarlo trabajando y hacer otra cosa, pero evita usar el PC para tareas pesadas a la vez (juegos, render).

---

## Cosas que debes saber

- **Es seguro interrumpir.** Cierra la ventana negra cuando quieras; al volver a pulsar **Start tagging** con la misma carpeta, se saltan los clips ya hechos y continúa.
- **Las carpetas se recorren enteras**, incluidas las subcarpetas.
- **Casilla "Re-tag clips already in the database"**: vuelve a analizar también los clips que ya estaban. Úsala solo si cambiaste la lista de etiquetas del programa o quieres rehacer todo. Normalmente déjala desmarcada.
- **No se modifican tus vídeos.** El programa solo los lee.
- **Si mueves o renombras clips después**, la base de datos se queda con rutas que ya no existen. Mira [6. Gestionar la biblioteca](06-gestionar-biblioteca.md).

---

## Comprobar el resultado

En la pestaña **Library**, bajo **Clips**:

- Escribe en el buscador parte de una ruta (por ejemplo `Naruto`) para filtrar.
- Usa el desplegable de vibe (`energic`, `sad`, `neutral`) para ver cuántos clips hay de cada tipo.
- Cada fila muestra ruta, vibe, energía, duración y etiquetas.

**Consejo:** para tener variedad con cualquier vibe, procura tener clips de los tres tipos. Si casi todos son `energic`, un vídeo `sad` tendrá pocos clips donde elegir.

Siguiente paso → [4. Sincronizar la letra](04-sincronizar-letras.md)
