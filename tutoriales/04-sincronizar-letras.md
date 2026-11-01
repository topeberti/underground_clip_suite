# 4. Sincronizar la letra (crear el archivo .srt)

El programa **corta de clip en clip cada vez que empieza una frase de la letra**. Para eso necesita un archivo `.srt` con el momento exacto en que empieza cada frase.

Tienes dos opciones:

- **A.** Crearlo aquí mismo, "tocando" una tecla al ritmo de la canción (abajo).
- **B.** Usar un `.srt` que ya tengas (de Subtitle Edit, de YouTube, etc.). Salta al [tutorial 5](05-crear-video.md).

---

## Opción A: Lyric Sync (en el navegador)

Ten a mano la **letra de la canción** para copiarla o leerla.

### Paso 1: Cargar la canción

1. Abre el programa (`iniciar.bat`) y ve a la pestaña **Lyric Sync**.
2. En **Audio file** pulsa **Browse** y elige tu canción (`.mp3`, `.wav`, `.flac`, `.m4a`, `.ogg` o `.aac`).
3. Pulsa **Load**. Aparece un reproductor: puedes darle al play para comprobar que suena.

### Paso 2: Fase de "tap" (marcar los tiempos)

Aquí marcas **cuándo empieza cada frase**.

1. En **1 · Tap phase**, deja la cuenta atrás en 3 segundos (o cámbiala) y pulsa **Start**.
2. Tras la cuenta atrás empieza la canción. **Pulsa la barra espaciadora justo cuando empiece cada frase** de la letra.
3. Teclas útiles:

| Tecla | Acción |
|---|---|
| `Espacio` | Marcar el inicio de una frase |
| `Retroceso` | Deshacer la última marca (si te equivocaste) |
| `R` | Reiniciar desde el principio |
| `Q` | Parar antes de que acabe la canción |

4. El instante `00:00` se marca solo; no hace falta pulsar al empezar.
5. Cuando la canción termine (o pulses `Q`), pasa a la siguiente fase.

> **Truco:** no busques precisión perfecta. Pulsa **un pelín antes** de la frase mejor que después. Y puedes repetir (`R`) cuantas veces quieras.
>
> **Frases largas o instrumentales:** si hay un solo largo sin letra, pulsa también ahí; luego lo dejarás vacío en la fase 2 y ese tramo se omite (el clip anterior se mantiene).

### Paso 3: Asignar el texto

En **2 · Assign lyrics** aparece una fila por cada marca:

1. Pulsa el botón de reproducir de la fila para escuchar ese fragmento.
2. **Escribe (o pega) la frase** que se oye.
3. Pulsa `Enter` para saltar a la siguiente.
4. **Deja vacía** la fila de un tramo sin letra para omitirlo.

### Paso 4: Guardar

1. En **Save as** escribe dónde guardarlo. Recomendado: la misma carpeta que la canción, con el mismo nombre y terminado en `.srt` (por ejemplo `D:\Musica\mitema.srt`). Debe acabar en `.srt` y la carpeta debe existir.
2. Pulsa **Save .srt**.
3. Opcional: **Use in Build →** rellena automáticamente los campos de la pestaña Build con esta canción y este `.srt`.

---

## Qué importa para el resultado

- **Cada marca = un cambio de clip.** Si marcas cada palabra, tendrás cortes muy rápidos; si marcas solo cada verso, cortes más lentos. Ajusta a tu gusto.
- **Los tiempos de inicio son lo único que cuenta** para el montaje; el texto sirve luego como subtítulos en DaVinci Resolve.
- Si una frase dura mucho (por ejemplo 12 s), necesita clips de al menos la mitad de esa duración. Añade más marcas intermedias o tendrás errores de "clip demasiado corto" (ver [Problemas frecuentes](08-problemas-frecuentes.md)).

---

## Opción B: usar un .srt existente

Cualquier `.srt` estándar funciona. Si tu letra tiene tiempos, solo asegúrate de que:

- El archivo termina en `.srt`.
- Cada bloque tiene texto (los bloques vacíos se ignoran).

Programa gratuito recomendado para crearlos a mano: [Subtitle Edit](https://www.nikse.dk/subtitleedit).

Siguiente paso → [5. Crear el vídeo](05-crear-video.md)
