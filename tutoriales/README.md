# Tutoriales de Video Generator

Guías paso a paso, pensadas para quien **nunca ha usado una terminal**. Sigue el orden la primera vez.

## Ruta rápida

```
Instalar  →  Organizar clips  →  Etiquetar  →  Sincronizar letra  →  Crear vídeo  →  Abrir en DaVinci Resolve
  (1 vez)        (1 vez)          (1 vez por     (1 por canción)     (cuantas veces
                                   pack nuevo)                          quieras)
```

## Índice

| # | Tutorial | Cuándo lo necesitas |
|---|----------|---------------------|
| 1 | [Instalación](01-instalacion.md) | La primera vez |
| 2 | [Organizar los clips](02-organizar-clips.md) | **Antes de etiquetar.** Si lo haces mal, hay que repetir el etiquetado |
| 3 | [Etiquetar los clips](03-etiquetar-clips.md) | Cada vez que añadas clips nuevos |
| 4 | [Sincronizar la letra](04-sincronizar-letras.md) | Una vez por canción (si no tienes ya un `.srt`) |
| 5 | [Crear el vídeo](05-crear-video.md) | Para generar las líneas de tiempo |
| 6 | [Gestionar la biblioteca](06-gestionar-biblioteca.md) | Borrar clips o series, ver estadísticas |
| 7 | [Subir a redes](07-subir-a-redes.md) | Opcional y experimental (Instagram sin probar) |
| 8 | [Problemas frecuentes](08-problemas-frecuentes.md) | Si algo falla |
| 9 | [Línea de comandos](09-linea-de-comandos.md) | Usuarios avanzados |

## Glosario rápido

- **Clip**: un archivo de vídeo corto de tu colección (una escena, una pelea, un paisaje…).
- **Etiquetar**: dejar que la IA analice cada clip y lo guarde en la base de datos con sus etiquetas y su nivel de energía.
- **Base de datos (DB)**: el archivo `clips_db\clips.db` donde se guarda la lista de clips analizados.
- **Vibe**: el ambiente de un clip: `energic` (movimiento e intensidad), `sad` (calmado, melancólico) o `neutral`.
- **SRT**: archivo de texto con la letra y los tiempos de cada frase.
- **FCPXML**: el archivo que genera el programa; DaVinci Resolve lo importa como una línea de tiempo ya montada.
- **Línea de tiempo (timeline)**: la secuencia de clips ordenados que verás en DaVinci Resolve.
