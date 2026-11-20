"""
src/timeline/build_runner.py — Shared build pipeline used by both the CLI and the web UI.
"""

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from src.lyrics.srt_parser import parse_srt
from src.timeline import beat_detector, clip_selector, fcpxml_builder, image_selector, resolve_script

EDIT_TYPES = ("anime", "pinterest")


@dataclass
class BuildResult:
    timelines: list[str]
    fcpxml_paths: list[Path]   # anime edits only; image edits have none
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
    edit_type: str = "anime",
    pinterest_dir: Path | None = None,
    beats_per_image: float | None = 1,
) -> BuildResult:
    """Build `count` timelines and the Resolve script that assembles and renders them.

    edit_type "anime": one video clip per lyric segment from the clip database.
    edit_type "pinterest": per segment, a random image category from pinterest_dir shown as
    a fast sequence of stills at native size, changing every `beats_per_image` beats of the
    song (one of image_selector.BEATS_PER_IMAGE), or every ≤ 0.5 s when None.
    Raises RuntimeError/Exception on failure."""
    if edit_type not in EDIT_TYPES:
        raise RuntimeError(f"Unknown edit type '{edit_type}'. Use one of: {', '.join(EDIT_TYPES)}.")
    images = edit_type == "pinterest"
    if images and beats_per_image is not None and beats_per_image not in image_selector.BEATS_PER_IMAGE:
        raise RuntimeError(
            f"Beats per image must be one of {image_selector.BEATS_PER_IMAGE} (or none for 0.5 s)."
        )
    pinterest_dir = pinterest_dir or image_selector.DEFAULT_MEDIA_DIR
    render_dir = song.parent / "videos"
    console.print(f"[bold]Building {count} {edit_type} timeline(s):[/bold] {name}")
    console.print(f"  Song:       {song}")
    console.print(f"  Lyrics:     {lyrics}")
    if images:
        pace = f"{beats_per_image:g} beat(s) per image" if beats_per_image else f"{image_selector.MAX_IMAGE_SEC:g} s per image"
        console.print(f"  Images:     {pinterest_dir}  |  {pace}  |  FPS: {fps}")
    else:
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

    image_changes = None
    if images and beats_per_image:
        image_changes = image_selector.beat_grid(
            beat_data["beat_times"], beat_data["bpm"], beat_data["duration_sec"], beats_per_image,
        )

    saved_paths: list[Path] = []
    builds: list[dict] = []
    timeline_names = _timeline_names(name, count, render_dir)
    for i, timeline_name in enumerate(timeline_names):
        label = f"[{i + 1}/{count}] " if count > 1 else ""

        if images:
            console.print(f"[dim]{label}Selecting images…[/dim]")
            sequence, categories = image_selector.select_images(
                pinterest_dir, srt_blocks, beat_data["duration_sec"], fps, beat_times=image_changes,
            )
            console.print(f"  {label}{len(sequence)} images, categories: {', '.join(categories)}")
            builds.append({"name": timeline_name, "clips": sequence})
            continue

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

    paths = {c["path"] for b in builds for c in b["clips"]}
    if images:
        # Resolve can't trim stills, so the script places a short clip of each image.
        console.print(f"[dim]Preparing {len(paths)} image clip(s)…[/dim]")
        longest = max(c["duration_sec"] for b in builds for c in b["clips"])
        clip_of = image_selector.still_clips(paths, pinterest_dir, fps, min_sec=longest)
        for b in builds:
            b["clips"] = [{**c, "path": clip_of[c["path"]]} for c in b["clips"]]
        zooms = dict.fromkeys(clip_of.values(), 1.0)   # never resized
    else:
        console.print("[dim]Measuring clip framing…[/dim]")
        zooms = {path: resolve_script.measure_zoom(path) for path in paths}

    render_dir.mkdir(parents=True, exist_ok=True)
    srt_path = resolve_script.write_wrapped_srt(srt_blocks, output_dir / f"{name}_subtitles.srt")
    script_path = resolve_script.scripts_dir() / f"{resolve_script.SCRIPT_NAME}.lua"
    resolve_script.write_lua(
        builds, song, srt_path, render_dir, zooms, script_path,
        scaling="centerCrop" if images else "scaleToCrop",
    )
    console.print(f"  Resolve script: [cyan]{script_path}[/cyan]")

    return BuildResult(timeline_names, saved_paths, script_path, render_dir)
