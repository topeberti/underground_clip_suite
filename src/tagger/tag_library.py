from pathlib import Path

from rich.console import Console
from rich.progress import track

from src.db import db_manager
from src.tagger import clip_tagger, energy_scorer
from src.tagger.constants import CANDIDATE_TAGS, VIDEO_EXTENSIONS

console = Console()


def assign_vibe(energy_score: float) -> str:
    if energy_score >= 0.6:
        return "energic"
    if energy_score <= 0.4:
        return "sad"
    return "neutral"


def tag_single_clip(path: Path, db_path: Path, console: Console = console) -> None:
    db_manager.delete_clip(db_path, str(path))
    tags, duration_sec, fps, width, height = clip_tagger.tag_clip(path)
    energy = energy_scorer.score_clip(path)
    vibe = assign_vibe(energy)
    db_manager.insert_clip(
        db_path, str(path), duration_sec, fps, tags, energy, vibe, width, height
    )
    console.print(f"[green]Tagged[/green] {path.name}  vibe=[bold]{vibe}[/bold]  energy={energy:.2f}  tags={tags[:4]}")


def tag_folder(
    folder: Path,
    db_path: Path,
    force: bool = False,
    console: Console = console,
    on_progress=None,
) -> None:
    """Tag all clips in a folder. `on_progress(done, total)` replaces the rich progress bar when given."""
    clips = [p for p in folder.rglob("*") if p.suffix.lower() in VIDEO_EXTENSIONS]
    if not clips:
        console.print(f"[yellow]No video files found in {folder}[/yellow]")
        return

    iterator = clips if on_progress else track(clips, description="Tagging clips…", console=console)
    for i, clip_path in enumerate(iterator):
        if on_progress:
            on_progress(i, len(clips))
        if not force and db_manager.clip_exists(db_path, str(clip_path)):
            console.print(f"  [dim]skip[/dim] {clip_path.name}")
            continue
        try:
            tag_single_clip(clip_path, db_path, console)
        except Exception as exc:
            console.print(f"  [red]warning[/red] {clip_path.name}: {exc}")
    if on_progress:
        on_progress(len(clips), len(clips))
