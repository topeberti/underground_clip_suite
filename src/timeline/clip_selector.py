import random
from pathlib import Path

from rich.console import Console

from src.db import db_manager

console = Console()

MIN_SPEED = 0.5  # clips can be slowed to at most 50% — below this, skip the clip


def select_clips(
    db_path: Path,
    vibe: str,
    lyric_blocks: list[dict],
    song_duration_sec: float,
    same_anime: bool = False,
) -> list[dict]:
    primary = db_manager.query_clips(db_path, vibe)
    secondary = db_manager.query_clips(db_path, "neutral")

    if not primary and not secondary:
        raise RuntimeError(
            f"No clips in database for vibe '{vibe}'. Run `tag` first."
        )

    all_clips = primary + secondary
    all_weights = [1.0] * len(primary) + [0.4] * len(secondary)

    if same_anime:
        animes = list({Path(c["path"]).parent.name for c in all_clips})
        if not animes:
            raise RuntimeError("No anime folders found in clip paths.")
        chosen_anime = random.choice(animes)
        filtered = [
            (c, w) for c, w in zip(all_clips, all_weights)
            if Path(c["path"]).parent.name == chosen_anime
        ]
        all_clips, all_weights = [c for c, _ in filtered], [w for _, w in filtered]
        console.print(f"  [dim]Same-anime mode: [bold]{chosen_anime}[/bold][/dim]")

    # Build cut points: always start at 0, then each lyric block start.
    # Lyric block END is irrelevant — clips run from one cut point to the next.
    cut_points = [0.0]
    for block in lyric_blocks:
        t = block["start_ms"] / 1000.0
        if t > cut_points[-1]:
            cut_points.append(t)

    result: list[dict] = []
    last_path: str | None = None

    for i, timeline_start in enumerate(cut_points):
        needed_duration = (
            cut_points[i + 1] if i + 1 < len(cut_points) else song_duration_sec
        ) - timeline_start

        if needed_duration <= 0:
            continue

        # Only consider clips that can cover the segment at or above MIN_SPEED.
        # A clip is usable if: clip_duration >= needed_duration * MIN_SPEED
        min_clip_dur = needed_duration * MIN_SPEED
        usable = [
            (c, w) for c, w in zip(all_clips, all_weights)
            if c["duration_sec"] >= min_clip_dur
        ]
        if not usable:
            raise RuntimeError(
                f"No clip long enough for a {needed_duration:.1f}s segment "
                f"(need at least {min_clip_dur:.1f}s at {MIN_SPEED:.0%} speed). "
                "Add more/longer clips to the database."
            )

        pop, weights = zip(*usable)

        clip = random.choices(pop, weights=weights, k=1)[0]
        if clip["path"] == last_path and len(pop) > 1:
            clip = random.choices(pop, weights=weights, k=1)[0]

        if clip["duration_sec"] >= needed_duration:
            clip_start = random.uniform(0.0, clip["duration_sec"] - needed_duration)
            speed = 1.0
        else:
            # Clip is shorter than needed — slow it down to fill the segment.
            clip_start = 0.0
            speed = clip["duration_sec"] / needed_duration

        result.append({
            "path": clip["path"],
            "timeline_start_sec": timeline_start,
            "clip_start_sec": clip_start,
            "duration_sec": needed_duration,
            "speed": speed,
        })
        last_path = clip["path"]

    return result
