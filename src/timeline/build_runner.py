"""
src/timeline/build_runner.py — Shared build pipeline used by both the CLI and the web UI.
"""

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from src.lyrics.srt_parser import parse_srt
from src.timeline import beat_detector, clip_selector, fcpxml_builder, resolve_script


@dataclass
class BuildResult:
    fcpxml_paths: list[Path]
    script_path: Path   # the Lua script installed in Resolve's Scripts menu
    render_dir: Path    # where Resolve renders the videos


def _timeline_names(name: str, count: int, render_dir: Path) -> list[str]:
    """Timeline names whose renders won't overwrite videos already in render_dir."""
    names: list[str] = []
    i = 1
    while len(names) < count:
        candidate = f"{name}_{i}" if count > 1 or i > 1 else name
        if not (render_dir / f"{candidate}.mp4").exists():
            names.append(candidate)
        i += 1
    return names


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
) -> BuildResult:
    """Build `count` timelines and the Resolve script that assembles and renders them.
    Raises RuntimeError/Exception on failure."""
    render_dir = song.parent / "videos"
    console.print(f"[bold]Building {count} timeline(s):[/bold] {name}")
    console.print(f"  Song:       {song}")
    console.print(f"  Lyrics:     {lyrics}")
    console.print(f"  Vibe:       {vibe or 'any'}  |  FPS: {fps}  |  Same anime: {same_anime}")
    console.print(f"  Output dir: {output_dir}")
    console.print(f"  Videos to:  {render_dir}")

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
    builds: list[dict] = []
    for i, timeline_name in enumerate(_timeline_names(name, count, render_dir)):
        label = f"[{i + 1}/{count}] " if count > 1 else ""

        console.print(f"[dim]{label}Selecting clips…[/dim]")
        # No slow-motion: the Resolve script can't set clip speed.
        clips_sequence = clip_selector.select_clips(
            db_path, vibe, srt_blocks, beat_data["duration_sec"], same_anime=same_anime, min_speed=1.0,
        )
        console.print(f"  {label}{len(clips_sequence)} clips selected.")

        console.print(f"[dim]{label}Building FCPXML…[/dim]")
        fcpxml_path = fcpxml_builder.build_fcpxml(
            timeline_name, clips_sequence, fps, beat_data["duration_sec"], output_dir
        )
        saved_paths.append(fcpxml_path)
        builds.append({"name": timeline_name, "clips": clips_sequence})
        console.print(f"  {label}Saved: [cyan]{fcpxml_path}[/cyan]")

    console.print("[dim]Measuring clip framing…[/dim]")
    zooms = {
        path: resolve_script.measure_zoom(path)
        for path in {c["path"] for b in builds for c in b["clips"]}
    }

    render_dir.mkdir(parents=True, exist_ok=True)
    srt_path = resolve_script.write_wrapped_srt(srt_blocks, output_dir / f"{name}_subtitles.srt")
    script_path = resolve_script.scripts_dir() / f"{resolve_script.SCRIPT_NAME}.lua"
    resolve_script.write_lua(builds, song, srt_path, render_dir, zooms, script_path)
    console.print(f"  Resolve script: [cyan]{script_path}[/cyan]")

    return BuildResult(saved_paths, script_path, render_dir)
