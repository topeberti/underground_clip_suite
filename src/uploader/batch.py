"""
src/uploader/batch.py — Batch upload orchestrator.

Coordinates ffmpeg audio normalization, platform uploaders, progress display,
and JSONL result logging.
"""

import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.uploader.auth import AuthExpiredError, load_config
from src.uploader.tiktok import TikTokUploader, UploadResult

LOG_PATH = Path(__file__).parent.parent.parent / "output" / "upload_log.jsonl"


# ---------------------------------------------------------------------------
# Audio normalization via ffmpeg
# ---------------------------------------------------------------------------

def normalize_audio(files: list[Path], dest_dir: Path) -> list[Path]:
    """Re-encode audio track of each file to identical AAC specs. Fast — video stream is copied."""
    if not shutil.which("ffmpeg"):
        return files  # caller checks and warns

    normalized = []
    for src in files:
        dst = dest_dir / src.name
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
                str(dst),
            ],
            capture_output=True,
            timeout=300,
        )
        if result.returncode == 0:
            normalized.append(dst)
        else:
            # Fall back to original if ffmpeg fails on this file
            normalized.append(src)
    return normalized


# ---------------------------------------------------------------------------
# JSONL logging
# ---------------------------------------------------------------------------

def _log_result(result: UploadResult, batch_id: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": result.timestamp or datetime.now().isoformat(),
        "batch_id": batch_id,
        "file": result.file_path.name,
        "platform": result.platform,
        "status": result.status,
    }
    if result.publish_id:
        entry["publish_id"] = result.publish_id
    if result.error_code:
        entry["error_code"] = result.error_code
    if result.error_message:
        entry["error_message"] = result.error_message
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Main batch runner
# ---------------------------------------------------------------------------

def run_batch(
    folder: Path,
    caption: str,
    platforms: list[str],
    delay: int,
    privacy: str,
    skip_normalize: bool,
    dry_run: bool,
    config_path: Path,
    console: Console,
    on_progress=None,
) -> list[UploadResult]:

    mp4_files = sorted(folder.glob("*.mp4"))
    if not mp4_files:
        console.print(f"[yellow]No .mp4 files found in {folder}[/yellow]")
        return []

    # Resolve "all" shorthand
    resolved_platforms = _resolve_platforms(platforms)

    if dry_run:
        console.print(f"\n[bold]Dry run — would upload {len(mp4_files)} file(s):[/bold]")
        console.print(f"  Caption:   {caption}")
        console.print(f"  Platforms: {', '.join(resolved_platforms)}")
        console.print(f"  Privacy:   {privacy}")
        console.print(f"  Normalize: {not skip_normalize}\n")
        for f in mp4_files:
            console.print(f"  [cyan]{f.name}[/cyan]")
        return []

    batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    console.print(f"\n[bold]Batch upload[/bold] — {len(mp4_files)} file(s) × {len(resolved_platforms)} platform(s)")
    console.print(f"  Caption:  {caption}")
    console.print(f"  Batch ID: [dim]{batch_id}[/dim]\n")

    # Audio normalization
    tmp_dir = None
    upload_files = mp4_files
    if not skip_normalize:
        if not shutil.which("ffmpeg"):
            console.print(
                "[yellow]ffmpeg not found on PATH — skipping audio normalization.[/yellow]\n"
                "[dim]Install with: choco install ffmpeg[/dim]\n"
            )
        else:
            console.print("[dim]Normalizing audio (ffmpeg)…[/dim]")
            tmp_dir = Path(tempfile.mkdtemp(prefix="uploader_"))
            upload_files = normalize_audio(mp4_files, tmp_dir)
            console.print(f"  Normalized {len(upload_files)} file(s) → temp folder\n")

    # Load config and build uploaders
    try:
        config = load_config(config_path)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        _cleanup(tmp_dir)
        return []

    uploaders = {}
    if "tiktok" in resolved_platforms:
        try:
            uploaders["tiktok"] = TikTokUploader(config, config_path)
        except AuthExpiredError as exc:
            console.print(f"[red]TikTok auth error: {exc}[/red]")

    ngrok_server = None
    ngrok_base_url = ""
    if "instagram" in resolved_platforms:
        from src.uploader.instagram import InstagramUploader
        from src.uploader.ngrok_server import NgrokServer
        try:
            uploaders["instagram"] = InstagramUploader(config, config_path)
            ngrok_server = NgrokServer()
            serve_folder = tmp_dir if tmp_dir else folder
            console.print("[dim]Starting ngrok tunnel for Instagram…[/dim]")
            ngrok_base_url = ngrok_server.start(serve_folder)
            console.print(f"  Tunnel: [cyan]{ngrok_base_url}[/cyan]\n")
        except FileNotFoundError as exc:
            console.print(f"[yellow]{exc}[/yellow]")
            uploaders.pop("instagram", None)
        except AuthExpiredError as exc:
            console.print(f"[red]Instagram auth error: {exc}[/red]")
            uploaders.pop("instagram", None)

    if not uploaders:
        console.print("[red]No platforms available to upload to. Aborting.[/red]")
        _cleanup(tmp_dir, ngrok_server)
        return []

    # Upload loop
    results: list[UploadResult] = []
    total_ops = len(upload_files) * len(uploaders)
    op_num = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Uploading…", total=total_ops)

        for i, (src_file, upload_file) in enumerate(zip(mp4_files, upload_files)):
            for platform, uploader in uploaders.items():
                progress.update(
                    task,
                    description=f"[cyan]{src_file.name}[/cyan] → {platform}",
                )

                if platform == "tiktok":
                    result = uploader.upload_video(upload_file, caption, privacy)
                    result.file_path = src_file  # log original name
                elif platform == "instagram":
                    public_url = f"{ngrok_base_url}/{upload_file.name}"
                    result = uploader.upload_reel(upload_file, caption, public_url)
                    result.file_path = src_file

                results.append(result)
                _log_result(result, batch_id)
                progress.advance(task)
                op_num += 1
                if on_progress:
                    on_progress(op_num, total_ops)

                # Delay between uploads (skip after last)
                if op_num < total_ops:
                    time.sleep(delay)

    _cleanup(tmp_dir, ngrok_server)

    # Summary table
    _print_summary(results, console)
    return results


def _resolve_platforms(platforms: list[str]) -> list[str]:
    if "all" in platforms:
        return ["tiktok", "instagram"]
    valid = {"tiktok", "instagram"}
    return [p for p in platforms if p in valid] or ["tiktok", "instagram"]


def _print_summary(results: list[UploadResult], console: Console) -> None:
    table = Table(title="Upload Summary", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Platform")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    for r in results:
        status_display = "[green]success[/green]" if r.status == "success" else "[red]failed[/red]"
        detail = r.publish_id if r.status == "success" else f"{r.error_code}: {r.error_message}"
        table.add_row(r.file_path.name, r.platform, status_display, detail)

    console.print(table)

    successes = sum(1 for r in results if r.status == "success")
    console.print(
        f"\n[bold]Done:[/bold] {successes}/{len(results)} uploads succeeded. "
        f"Log: [cyan]{LOG_PATH}[/cyan]"
    )
    if successes == len(results):
        console.print(
            "\n[dim]Audio grouping note: TikTok and Instagram will automatically group your videos "
            "under the same 'original sound' when they detect matching audio fingerprints. "
            "This typically appears within a few minutes of the uploads processing.[/dim]"
        )


def _cleanup(tmp_dir: Path | None, ngrok_server=None) -> None:
    if ngrok_server:
        try:
            ngrok_server.stop()
        except Exception:
            pass
    if tmp_dir and tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Upload log reader (for upload-status command)
# ---------------------------------------------------------------------------

def read_log(log_path: Path = LOG_PATH, last_n: int = 20) -> list[dict]:
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries[-last_n:]
