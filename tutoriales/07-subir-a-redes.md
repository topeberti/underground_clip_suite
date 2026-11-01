# 7. Subir vídeos a TikTok e Instagram (opcional, avanzado)

> ⚠️ **Función experimental.** La subida a **Instagram nunca se ha probado con éxito** y puede que no funcione. La de TikTok tampoco está garantizada, y las condiciones de ambas plataformas cambian. Úsala bajo tu responsabilidad, empieza siempre con *Dry run* y, si falla, sube los vídeos a mano.

> Esta parte **no es necesaria** para crear vídeos. Requiere crear aplicaciones de desarrollador en TikTok y Meta, lo que implica aprobaciones por su parte que pueden tardar y cuyas condiciones cambian. Si solo quieres exportar y subir a mano, sáltatela.

La pestaña **Upload** sube de golpe todos los `.mp4` de una carpeta (tus renders de DaVinci Resolve) con el mismo texto y hashtags. Antes normaliza el audio con ffmpeg para que TikTok los agrupe bajo el mismo sonido original.

## Requisitos previos

| Para | Necesitas |
|---|---|
| Ambas | **ffmpeg** instalado (`winget install ffmpeg`, ver [instalación](01-instalacion.md)) |
| TikTok | Cuenta en <https://developers.tiktok.com>, una app con el permiso (`scope`) `video.upload` aprobado. Apúntate el **Client Key** y **Client Secret** |
| Instagram | Cuenta **Business o Creator**, una app en <https://developers.facebook.com> con el producto **Instagram Graph API**. Apúntate el **App ID** y **App Secret** |
| Instagram | **ngrok** (<https://ngrok.com>, cuenta gratuita): Instagram necesita descargar el vídeo desde una dirección pública, y el programa abre un túnel temporal. Instala ngrok y ejecuta una vez `ngrok config add-authtoken TU_TOKEN` |

En ambas apps debes registrar como dirección de redirección (redirect URI): `http://localhost:8080/callback`

## Paso 1: Crear el archivo de credenciales

1. En la carpeta `config`, copia `upload_config.json.example` y llama a la copia `upload_config.json`.
2. Ábrelo con el Bloc de notas y sustituye `YOUR_TIKTOK_CLIENT_KEY`, `YOUR_TIKTOK_CLIENT_SECRET`, `YOUR_META_APP_ID` y `YOUR_META_APP_SECRET` por tus datos. **No toques** los demás campos vacíos: se rellenan solos.

> Este archivo contiene secretos. Está en `.gitignore`, así que no se sube a GitHub. **Nunca lo compartas.**

## Paso 2: Autenticarte (una vez)

1. Pestaña **Upload → Accounts**.
2. Pulsa **Authenticate TikTok** y/o **Authenticate Instagram**.
3. Se abre el navegador para que inicies sesión y des permiso. Al terminar, el programa guarda los tokens.
4. El estado cambia a autenticado. Los tokens caducan; si caducan, repite este paso.

## Paso 3: Subir

1. **Folder with exported .mp4 files**: la carpeta con tus renders.
2. **Caption**: texto y hashtags (el mismo para todos), p. ej. `Mi edit #fyp #amv`.
3. Marca las plataformas, la privacidad (`public` / `followers` / `private`) y el retraso entre subidas (10 s por defecto, para no saturar).
4. **Deja marcado "Dry run (no uploads)" la primera vez:** simula todo sin subir nada, para comprobar que lo ves bien.
5. Desmarca *Dry run* y pulsa **Start** para subir de verdad.

Abajo, **Recent uploads** muestra el historial (también guardado en `output\upload_log.jsonl`).
