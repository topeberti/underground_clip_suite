"""
src/main.py — CLI entry point

Commands:
  init-db      Initialize the SQLite database
  tag          Tag a folder of video clips and add to DB
  retag        Force re-tag a single clip
  remove-clip  Remove a clip from the DB by path
  remove-anime Remove all clips from a specific anime (DB only or DB + disk)
  stats        Show DB statistics
  lyric-sync   Tap-along lyric syncer — creates a .srt file from an audio file
  build        Build a DaVinci Resolve project
  serve        Start the local web UI

Usage examples:
  python src/main.py init-db
  python src/main.py tag --folder "D:/VideoPacka/Pack01"
  python src/main.py lyric-sync "D:/track.mp3"
  python src/main.py build --song "D:/track.mp3" --lyrics "D:/track.srt" --vibe energic --fps 30 --name "my_edit_v1"
  python src/main.py remove-anime --name "Naruto" --dry-run
  python src/main.py remove-anime --name "Naruto"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer
from rich.console import Console
from rich.table import Table

from src.lyrics.srt_parser import parse_srt
from src.db import db_manager
from src.tagger import tag_library
from src.timeline import beat_detector, clip_selector, fcpxml_builder

app = typer.Typer(help="Video Generator — automated Resolve project builder")
console = Console()

DB_PATH = Path(__file__).parent.parent / "clips_db" / "clips.db"


@app.command()
def init_db():
    """Initialize the SQLite clip database."""
    db_manager.init_db(DB_PATH)
    console.print(f"[green]Database initialized at {DB_PATH}[/green]")


@app.command()
def tag(
    folder: Path = typer.Option(..., help="Folder of video files to tag"),
    force: bool = typer.Option(False, help="Re-tag clips already in DB"),
):
    """Tag all video clips in a folder and add them to the database."""
    if not folder.exists():
        console.print(f"[red]Folder not found: {folder}[/red]")
        raise typer.Exit(1)
    tag_library.tag_folder(folder, DB_PATH, force=force)


@app.command()
def retag(
    path: Path = typer.Option(..., help="Path to video file to re-tag"),
):
    """Force re-tag a single clip."""
    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    tag_library.tag_single_clip(path, DB_PATH)


@app.command()
def remove_clip(
    path: Path = typer.Option(..., help="Path of clip to remove from DB"),
):
    """Remove a clip from the database."""
    deleted = db_manager.delete_clip(DB_PATH, str(path))
    if deleted:
        console.print(f"[green]Removed {path} from database.[/green]")
    else:
        console.print(f"[yellow]Clip not found in database: {path}[/yellow]")


@app.command()
def remove_anime(
    name: str = typer.Option(..., help="Anime name (or part of it) to match against clip paths"),
    dry_run: bool = typer.Option(False, help="Preview matching clips without deleting"),
    delete_files: bool = typer.Option(False, help="Also delete the video files from disk (irreversible)"),
):
    """Remove all clips from a specific anime from the database (and optionally from disk)."""
    paths = db_manager.find_clips_by_anime(DB_PATH, name)

    if not paths:
        console.print(f"[yellow]No clips found matching '{name}'.[/yellow]")
        return

    console.print(f"[bold]{len(paths)} clip(s) match '{name}':[/bold]")
    for p in paths:
        console.print(f"  [dim]{p}[/dim]")

    if dry_run:
        console.print("[yellow]Dry run — nothing deleted.[/yellow]")
        return

    action = "Delete from DB and disk" if delete_files else "Remove from DB"
    typer.confirm(f"\n{action} for all {len(paths)} clip(s)?", abort=True)

    deleted = db_manager.delete_clips_by_anime(DB_PATH, name)
    console.print(f"[green]Removed {deleted} clip(s) from database.[/green]")

    if delete_files:
        removed, missing = 0, 0
        for raw in paths:
            p = Path(raw)
            if p.exists():
                p.unlink()
                removed += 1
            else:
                missing += 1
        console.print(f"[green]Deleted {removed} file(s) from disk.[/green]")
        if missing:
            console.print(f"[yellow]{missing} file(s) were already missing from disk.[/yellow]")


@app.command()
def stats():
    """Show database statistics."""
    s = db_manager.get_stats(DB_PATH)

    table = Table(title="Clip Database Stats")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total clips", str(s["total"]))
    table.add_row("Total hours", f"{s['total_hours']:.2f} h")

    for vibe, count in s["by_vibe"].items():
        table.add_row(f"  vibe: {vibe}", str(count))

    hist = s["energy_histogram"]
    table.add_row("Energy: low  (≤0.4)", str(hist["low"]))
    table.add_row("Energy: mid  (0.4–0.6)", str(hist["mid"]))
    table.add_row("Energy: high (≥0.6)", str(hist["high"]))

    console.print(table)


@app.command()
def lyric_sync(
    audio: Path = typer.Argument(..., help="Audio file (mp3/wav/flac)"),
    output: Path = typer.Option(None, "-o", "--output",
        help="Output .srt path (default: <audio>.srt next to the audio file)"),
    countdown: int = typer.Option(3, help="Seconds of countdown before playback starts"),
):
    """Tap-along lyric syncer — play audio, mark timestamps with SPACE, assign lyrics, write .srt."""
    if not audio.exists():
        console.print(f"[red]Audio file not found: {audio}[/red]")
        raise typer.Exit(1)
    from src.lyrics.lyric_syncer import run
    run(audio, output, countdown)


@app.command()
def build(
    song: Path = typer.Option(..., help="Path to song file (.mp3/.wav)"),
    lyrics: Path = typer.Option(..., help="Path to .srt lyrics file"),
    vibe: str = typer.Option(None, help="Vibe filter: 'energic' or 'sad'. Omit to use all clips."),
    fps: float = typer.Option(30.0, help="Timeline FPS"),
    name: str = typer.Option("video_project", help="Project name in Resolve"),
    count: int = typer.Option(1, help="Number of timelines to generate"),
    output_dir: Path = typer.Option(None, help="Output folder for FCPXML files"),
    same_anime: bool = typer.Option(False, help="Restrict all clips in an edit to the same anime"),
):
    """Build one or more DaVinci Resolve project scaffolds."""
    if not song.exists():
        console.print(f"[red]Song file not found: {song}[/red]")
        raise typer.Exit(1)
    if not lyrics.exists():
        console.print(f"[red]Lyrics file not found: {lyrics}[/red]")
        raise typer.Exit(1)
    if vibe is not None and vibe not in ("energic", "sad"):
        console.print(f"[red]Invalid vibe '{vibe}'. Must be 'energic' or 'sad' (or omit for all clips).[/red]")
        raise typer.Exit(1)
    if count < 1:
        console.print("[red]--count must be at least 1.[/red]")
        raise typer.Exit(1)

    resolved_output_dir = output_dir if output_dir is not None else Path(__file__).parent.parent / "output"

    from src.timeline.build_runner import run_build
    try:
        saved_paths = run_build(
            song, lyrics, vibe, fps, name, count, resolved_output_dir, same_anime, DB_PATH, console
        )
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        import traceback
        console.print(traceback.format_exc())
        raise typer.Exit(1)

    console.print(f"\n[green bold]Done![/green bold] {len(saved_paths)} timeline(s) saved to [cyan]{resolved_output_dir}[/cyan]")
    console.print("\n[bold]Next steps in DaVinci Resolve:[/bold]")
    console.print("  1. File → Import Timeline → Import AAF, EDL, XML…  → select the .fcpxml file(s)")
    console.print(f"  2. Drag [cyan]{song.name}[/cyan] onto the audio track")
    console.print(f"  3. File → Import → Subtitles → select [cyan]{lyrics.name}[/cyan]")


DEFAULT_UPLOAD_CONFIG = Path(__file__).parent.parent / "config" / "upload_config.json"


@app.command()
def upload_batch(
    folder: Path = typer.Option(..., help="Folder containing exported .mp4 files"),
    caption: str = typer.Option(..., help="Caption (with hashtags) applied to all uploads"),
    platforms: list[str] = typer.Option(["tiktok", "instagram"], help="Platforms: tiktok, instagram, or all"),
    delay: int = typer.Option(10, help="Seconds to wait between individual uploads"),
    privacy: str = typer.Option("public", help="Privacy: public / followers / private"),
    skip_normalize: bool = typer.Option(False, help="Skip ffmpeg audio normalization"),
    dry_run: bool = typer.Option(False, help="Preview what would be uploaded without making API calls"),
    config: Path = typer.Option(None, help="Path to upload_config.json"),
):
    """
    Bulk-upload all .mp4 files in a folder to TikTok and/or Instagram Reels.

    All videos get the same caption and hashtags. Audio is normalized via ffmpeg
    before upload so TikTok groups them under the same 'original sound' page.

    Note: TikTok's API does not accept a music_id for custom sounds — grouping
    happens automatically when TikTok detects matching audio fingerprints across uploads.
    """
    if not folder.exists() or not folder.is_dir():
        console.print(f"[red]Folder not found: {folder}[/red]")
        raise typer.Exit(1)
    if privacy not in ("public", "followers", "private"):
        console.print("[red]--privacy must be: public, followers, or private[/red]")
        raise typer.Exit(1)

    config_path = config if config is not None else DEFAULT_UPLOAD_CONFIG

    from src.uploader.batch import run_batch
    run_batch(
        folder=folder,
        caption=caption,
        platforms=platforms,
        delay=delay,
        privacy=privacy,
        skip_normalize=skip_normalize,
        dry_run=dry_run,
        config_path=config_path,
        console=console,
    )


@app.command()
def setup_upload(
    platform: str = typer.Option("all", help="Platform to authenticate: tiktok, instagram, or all"),
    config: Path = typer.Option(None, help="Path to upload_config.json"),
):
    """
    Authenticate with TikTok and/or Instagram for uploading.

    Opens a browser OAuth flow, captures the token, and saves it to the config file.
    Run this once before using upload-batch.

    Prerequisites:
      TikTok:    Create an app at developers.tiktok.com with video.upload scope approved.
      Instagram: Create a Meta app at developers.facebook.com with Instagram Graph API product.
                 Your Instagram account must be a Business or Creator account.
    """
    config_path = config if config is not None else DEFAULT_UPLOAD_CONFIG

    if not config_path.exists():
        import shutil
        example = Path(__file__).parent.parent / "config" / "upload_config.json.example"
        if example.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(example, config_path)
            console.print(f"[dim]Created config from example: {config_path}[/dim]")
            console.print("[yellow]Fill in your client_key / client_secret before proceeding.[/yellow]")
            raise typer.Exit(0)
        console.print(f"[red]Config file not found: {config_path}[/red]")
        raise typer.Exit(1)

    from src.uploader.auth import run_tiktok_oauth, run_instagram_oauth

    targets = ["tiktok", "instagram"] if platform == "all" else [platform]
    for target in targets:
        console.print(f"\n[bold]Setting up {target}…[/bold]")
        try:
            if target == "tiktok":
                run_tiktok_oauth(config_path)
            elif target == "instagram":
                run_instagram_oauth(config_path)
            else:
                console.print(f"[red]Unknown platform '{target}'. Use: tiktok, instagram, or all[/red]")
        except (ValueError, RuntimeError, TimeoutError) as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)


@app.command()
def upload_status(
    log: Path = typer.Option(None, help="Path to upload_log.jsonl"),
    last: int = typer.Option(20, help="Number of most recent entries to show"),
):
    """Show results from recent upload batches."""
    from src.uploader.batch import read_log, LOG_PATH
    log_path = log if log is not None else LOG_PATH
    entries = read_log(log_path, last_n=last)
    if not entries:
        console.print("[yellow]No upload log entries found.[/yellow]")
        return

    table = Table(title=f"Last {len(entries)} uploads", show_lines=True)
    table.add_column("Timestamp", style="dim")
    table.add_column("Batch ID", style="dim")
    table.add_column("File", style="cyan")
    table.add_column("Platform")
    table.add_column("Status")
    table.add_column("Details", style="dim")

    for e in entries:
        status_display = "[green]success[/green]" if e.get("status") == "success" else "[red]failed[/red]"
        detail = e.get("publish_id", "") or f"{e.get('error_code', '')} {e.get('error_message', '')}".strip()
        table.add_row(
            e.get("timestamp", "")[:19],
            e.get("batch_id", ""),
            e.get("file", ""),
            e.get("platform", ""),
            status_display,
            detail,
        )
    console.print(table)


@app.command()
def serve(
    port: int = typer.Option(8000, help="Port to listen on"),
    no_browser: bool = typer.Option(False, help="Do not open the browser automatically"),
):
    """Start the local web UI."""
    from src.web.app import run
    run(port=port, open_browser=not no_browser)


if __name__ == "__main__":
    app()
