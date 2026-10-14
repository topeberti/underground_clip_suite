"""
src/web/app.py — Local web UI (FastAPI). Binds to 127.0.0.1 only.

Run with:  python src/main.py serve     or     python -m src.web.app
"""

import json
import mimetypes
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.db import db_manager
from src.tagger.constants import VIDEO_EXTENSIONS
from src.web import fs, jobs

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "clips_db" / "clips.db"
OUTPUT_DIR = ROOT / "output"
UPLOAD_CONFIG = ROOT / "config" / "upload_config.json"
STATIC_DIR = Path(__file__).parent / "static"

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}

app = FastAPI(title="Video Generator")


# ---------------------------------------------------------------------------
# Guard: this app can delete files, so refuse anything that doesn't look like
# our own page talking to us (DNS rebinding / cross-site form posts).
# ---------------------------------------------------------------------------

def _hostname(hostport: str) -> str:
    if hostport.startswith("["):
        return hostport.split("]")[0] + "]"
    return hostport.rsplit(":", 1)[0] if ":" in hostport else hostport


@app.middleware("http")
async def local_only(request: Request, call_next):
    if _hostname(request.headers.get("host", "")) not in ALLOWED_HOSTS:
        return JSONResponse({"detail": "Forbidden host"}, status_code=403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and _hostname(origin.split("://", 1)[-1]) not in ALLOWED_HOSTS:
            return JSONResponse({"detail": "Forbidden origin"}, status_code=403)
        # JSON content-type forces a CORS preflight for cross-site callers.
        if "application/json" not in request.headers.get("content-type", ""):
            return JSONResponse({"detail": "JSON body required"}, status_code=415)
    return await call_next(request)


def _bad(msg: str, code: int = 400):
    raise HTTPException(status_code=code, detail=msg)


def _require_db() -> None:
    if not DB_PATH.exists():
        _bad("Database not initialized. Click 'Initialize DB' on the Dashboard first.")


def _existing(path: str, what: str, *, dir_: bool = False, exts: set[str] | None = None) -> Path:
    p = Path(path).expanduser()
    if not path or not (p.is_dir() if dir_ else p.is_file()):
        _bad(f"{what} not found: {path}")
    if exts and p.suffix.lower() not in exts:
        _bad(f"{what} must be one of: {', '.join(sorted(exts))}")
    return p


# ---------------------------------------------------------------------------
# DB / stats / library
# ---------------------------------------------------------------------------

@app.post("/api/db/init")
def init_db():
    db_manager.init_db(DB_PATH)
    return {"ok": True, "path": str(DB_PATH)}


@app.get("/api/stats")
def stats():
    if not DB_PATH.exists():
        return {"initialized": False}
    return {"initialized": True, **db_manager.get_stats(DB_PATH)}


@app.get("/api/clips")
def clips(search: str = "", vibe: str = "", offset: int = 0, limit: int = 50):
    _require_db()
    rows, total = db_manager.list_clips(
        DB_PATH, search, vibe or None, limit=max(1, min(limit, 200)), offset=max(0, offset)
    )
    return {"clips": rows, "total": total}


class PathBody(BaseModel):
    path: str


@app.delete("/api/clips")
def remove_clip(body: PathBody):
    _require_db()
    return {"deleted": db_manager.delete_clip(DB_PATH, body.path)}


@app.get("/api/anime/preview")
def anime_preview(name: str):
    _require_db()
    if not name.strip():
        _bad("Enter an anime name.")
    paths = db_manager.find_clips_by_anime(DB_PATH, name.strip())
    return {"count": len(paths), "paths": paths[:500]}


class RemoveAnimeBody(BaseModel):
    name: str
    delete_files: bool = False


@app.post("/api/anime/remove")
def anime_remove(body: RemoveAnimeBody):
    _require_db()
    name = body.name.strip()
    if not name:
        _bad("Enter an anime name.")  # empty LIKE pattern would match every clip
    paths = db_manager.find_clips_by_anime(DB_PATH, name)
    deleted = db_manager.delete_clips_by_anime(DB_PATH, name)
    removed = missing = 0
    if body.delete_files:
        for raw in paths:
            p = Path(raw)
            if p.exists():
                p.unlink()
                removed += 1
            else:
                missing += 1
    return {"deleted_from_db": deleted, "files_deleted": removed, "files_missing": missing}


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def _start(kind, title, fn, exclusive=False):
    try:
        job = jobs.start_job(kind, title, fn, exclusive=exclusive)
    except jobs.Busy as exc:
        _bad(str(exc), 409)
    return {"job_id": job.id}


@app.get("/api/jobs")
def list_jobs():
    return jobs.list_jobs()


@app.get("/api/jobs/{job_id}/events")
def job_events(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        _bad("Unknown job.", 404)
    return StreamingResponse(
        jobs.stream(job), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class TagBody(BaseModel):
    folder: str
    force: bool = False


@app.post("/api/jobs/tag")
def job_tag(body: TagBody):
    _require_db()
    folder = _existing(body.folder, "Folder", dir_=True)

    def fn(console, on_progress):
        from src.tagger import tag_library
        tag_library.tag_folder(folder, DB_PATH, force=body.force, console=console, on_progress=on_progress)

    return _start("tag", f"Tag {folder}", fn, exclusive=True)


@app.post("/api/jobs/retag")
def job_retag(body: PathBody):
    _require_db()
    path = _existing(body.path, "Clip", exts=VIDEO_EXTENSIONS)

    def fn(console, on_progress):
        from src.tagger import tag_library
        tag_library.tag_single_clip(path, DB_PATH, console)

    return _start("retag", f"Re-tag {path.name}", fn, exclusive=True)


class BuildBody(BaseModel):
    song: str
    lyrics: str
    vibe: str | None = None
    fps: float = 30.0
    name: str = "video_project"
    count: int = 1
    output_dir: str | None = None
    same_anime: bool = False


@app.post("/api/jobs/build")
def job_build(body: BuildBody):
    _require_db()
    song = _existing(body.song, "Song", exts=AUDIO_EXTS)
    lyrics = _existing(body.lyrics, "Lyrics file")
    if body.vibe not in (None, "", "energic", "sad"):
        _bad("Vibe must be 'energic', 'sad' or empty.")
    if body.count < 1:
        _bad("Count must be at least 1.")
    if body.fps <= 0:
        _bad("FPS must be positive.")
    name = body.name.strip()
    if not name or any(c in name for c in '\\/:*?"<>|'):
        _bad("Project name is empty or contains invalid characters.")
    out_dir = Path(body.output_dir).expanduser() if body.output_dir else song.parent / "timelines"

    def fn(console, on_progress):
        from src.timeline.build_runner import run_build
        paths = run_build(
            song, lyrics, body.vibe or None, body.fps, name, body.count,
            out_dir, body.same_anime, DB_PATH, console,
        )
        return {"files": [str(p) for p in paths], "song": song.name, "lyrics": lyrics.name}

    return _start("build", f"Build {name}", fn)


class UploadBody(BaseModel):
    folder: str
    caption: str
    platforms: list[str] = ["tiktok", "instagram"]
    delay: int = 10
    privacy: str = "public"
    skip_normalize: bool = False
    dry_run: bool = False


@app.post("/api/jobs/upload")
def job_upload(body: UploadBody):
    folder = _existing(body.folder, "Folder", dir_=True)
    if body.privacy not in ("public", "followers", "private"):
        _bad("Privacy must be public, followers or private.")
    if not body.caption.strip():
        _bad("Caption is required.")

    def fn(console, on_progress):
        from src.uploader.batch import run_batch
        results = run_batch(
            folder=folder, caption=body.caption, platforms=body.platforms, delay=max(0, body.delay),
            privacy=body.privacy, skip_normalize=body.skip_normalize, dry_run=body.dry_run,
            config_path=UPLOAD_CONFIG, console=console, on_progress=on_progress,
        )
        return {"uploaded": sum(1 for r in results if r.status == "success"), "total": len(results)}

    return _start("upload", f"Upload {folder.name}", fn)


class SetupUploadBody(BaseModel):
    platform: str = "all"


@app.post("/api/jobs/setup-upload")
def job_setup_upload(body: SetupUploadBody):
    if body.platform not in ("tiktok", "instagram", "all"):
        _bad("Platform must be tiktok, instagram or all.")

    def fn(console, on_progress):
        import shutil
        from src.uploader.auth import run_instagram_oauth, run_tiktok_oauth

        if not UPLOAD_CONFIG.exists():
            example = ROOT / "config" / "upload_config.json.example"
            if not example.exists():
                raise FileNotFoundError(f"Config file not found: {UPLOAD_CONFIG}")
            shutil.copy(example, UPLOAD_CONFIG)
            raise RuntimeError(
                f"Created {UPLOAD_CONFIG} from the example. Fill in your client_key/client_secret "
                "(or app_id/app_secret), then authenticate again."
            )
        log = console.print
        for target in (["tiktok", "instagram"] if body.platform == "all" else [body.platform]):
            log(f"Setting up {target}…")
            (run_tiktok_oauth if target == "tiktok" else run_instagram_oauth)(UPLOAD_CONFIG, log=log)

    return _start("setup-upload", f"Authenticate {body.platform}", fn)


@app.get("/api/upload/status")
def upload_status():
    """Token presence/expiry per platform. Secrets are never returned."""
    out = {"config_exists": UPLOAD_CONFIG.exists(), "tiktok": None, "instagram": None}
    if UPLOAD_CONFIG.exists():
        cfg = json.loads(UPLOAD_CONFIG.read_text(encoding="utf-8"))
        for plat in ("tiktok", "instagram"):
            c = cfg.get(plat, {})
            out[plat] = {"authenticated": bool(c.get("access_token")), "expires_at": c.get("expires_at", "")}
    return out


@app.get("/api/upload/log")
def upload_log(last: int = 50):
    from src.uploader.batch import read_log
    return read_log(last_n=max(1, min(last, 500)))


# ---------------------------------------------------------------------------
# Files: picker, audio streaming, srt save, fcpxml download
# ---------------------------------------------------------------------------

@app.get("/api/fs/list")
def fs_list(path: str = "", ext: str = ""):
    exts = {e if e.startswith(".") else f".{e}" for e in ext.lower().split(",") if e} or None
    try:
        return fs.list_dir(path, exts)
    except (FileNotFoundError, PermissionError) as exc:
        _bad(str(exc))


@app.get("/api/media")
def media(path: str, request: Request):
    """Stream an audio file with HTTP Range support (needed for seeking in <audio>)."""
    p = _existing(path, "Audio file", exts=AUDIO_EXTS)
    size = p.stat().st_size
    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    rng = request.headers.get("range")
    if not rng:
        return FileResponse(p, media_type=ctype, headers={"Accept-Ranges": "bytes"})

    try:
        start_s, end_s = rng.replace("bytes=", "").split("-", 1)
        start = int(start_s) if start_s else max(0, size - int(end_s))
        end = int(end_s) if end_s and start_s else size - 1
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    end = min(end, size - 1)
    if start > end or start >= size:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    with open(p, "rb") as f:
        f.seek(start)
        data = f.read(end - start + 1)
    return Response(
        data, status_code=206, media_type=ctype,
        headers={"Content-Range": f"bytes {start}-{end}/{size}", "Accept-Ranges": "bytes"},
    )


class SaveSrtBody(BaseModel):
    output_path: str
    entries: list[dict]


@app.post("/api/lyrics/save")
def lyrics_save(body: SaveSrtBody):
    from src.lyrics.srt_writer import write_srt
    out = Path(body.output_path).expanduser()
    if out.suffix.lower() != ".srt":
        _bad("Output file must end in .srt")
    if not out.parent.is_dir():
        _bad(f"Folder not found: {out.parent}")
    entries = []
    for i, e in enumerate((e for e in body.entries if str(e.get("text", "")).strip()), start=1):
        try:
            entries.append({
                "index": i, "start_ms": int(e["start_ms"]), "end_ms": int(e["end_ms"]),
                "text": str(e["text"]).strip(),
            })
        except (KeyError, ValueError, TypeError):
            _bad("Each entry needs start_ms, end_ms and text.")
    if not entries:
        _bad("No lyrics to save.")
    write_srt(entries, out)
    return {"path": str(out), "count": len(entries)}


@app.get("/api/download")
def download(path: str):
    p = Path(path).resolve()
    if p.suffix.lower() != ".fcpxml" or not p.is_file():
        _bad("Only generated .fcpxml files can be downloaded.", 404)
    return FileResponse(p, filename=p.name)


@app.get("/api/info")
def info():
    return {"output_dir": str(OUTPUT_DIR), "db_path": str(DB_PATH), "now": datetime.now().isoformat()}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def run(port: int = 8000, open_browser: bool = True) -> None:
    import uvicorn

    url = f"http://127.0.0.1:{port}"
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"Video Generator UI → {url}  (Ctrl+C to stop)")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    run()
