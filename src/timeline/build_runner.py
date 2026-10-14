"""
src/timeline/build_runner.py — Shared build pipeline used by both the CLI and the web UI.
"""

from pathlib import Path

from rich.console import Console

from src.lyrics.srt_parser import parse_srt
from src.timeline import beat_detector, clip_selector, fcpxml_builder


def run_build(
    song: Path,
    lyrics: Path,
    vibe: str | None,
    fps: float,
    name: str,
    count: int,
    output_dir: Path,
    same_anime: bool,
    db_path: Path,
    console: Console,
) -> list[Path]:
    """Build `count` FCPXML timelines. Raises RuntimeError/Exception on failure."""
    console.print(f"[bold]Building {count} timeline(s):[/bold] {name}")
    console.print(f"  Song:       {song}")
    console.print(f"  Lyrics:     {lyrics}")
    console.print(f"  Vibe:       {vibe or 'any'}  |  FPS: {fps}  |  Same anime: {same_anime}")
    console.print(f"  Output dir: {output_dir}")

    console.print("[dim]Parsing lyrics…[/dim]")
    srt_blocks = parse_srt(lyrics)
    console.print(f"  {len(srt_blocks)} lyric blocks loaded.")

    console.print("[dim]Analyzing song…[/dim]")
    beat_data = beat_detector.analyze(song)
    console.print(
        f"  BPM: {beat_data['bpm']:.1f}  |  Duration: {beat_data['duration_sec']:.1f}s  |  "
        f"Beats: {len(beat_data['beat_times'])}"
    )

    saved_paths: list[Path] = []
    for i in range(count):
        label = f"[{i + 1}/{count}] " if count > 1 else ""
        timeline_name = f"{name}_{i + 1}" if count > 1 else name

        console.print(f"[dim]{label}Selecting clips…[/dim]")
        clips_sequence = clip_selector.select_clips(
            db_path, vibe, srt_blocks, beat_data["duration_sec"], same_anime=same_anime,
        )
        console.print(f"  {label}{len(clips_sequence)} clips selected.")

        console.print(f"[dim]{label}Building FCPXML…[/dim]")
        fcpxml_path = fcpxml_builder.build_fcpxml(
            timeline_name, clips_sequence, fps, beat_data["duration_sec"], output_dir
        )
        saved_paths.append(fcpxml_path)
        console.print(f"  {label}Saved: [cyan]{fcpxml_path}[/cyan]")

    return saved_paths
