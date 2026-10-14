"""
Clip selector — assigns a video clip to each timeline segment defined by lyric block boundaries.

Timeline model
--------------
Cut points are placed at t=0 and at the start of every lyric block.  Each segment
runs from one cut point to the next (or to the end of the song).  The selector picks
one clip per segment; the clip is trimmed or slightly slowed (down to MIN_SPEED) to
fill the exact segment duration.

Vibe weighting
--------------
Clips tagged with the requested vibe get weight 1.0; clips tagged "neutral" get 0.4
and act as a fallback pool so segments are never left empty.

same-anime mode
---------------
When same_anime=True the selector constrains all clips to a single anime folder.
It tries animes in random order and picks the first one that can cover every segment
with a *different* clip (no repetition).  If no anime has enough unique clips it
raises RuntimeError rather than silently reusing footage.
"""

import random
from pathlib import Path

from rich.console import Console

from src.db import db_manager

console = Console()

MIN_SPEED = 0.5  # clips can be slowed to at most 50% — below this, skip the clip


def _can_fill_without_repetition(
    clips: list[dict], cut_points: list[float], song_duration_sec: float
) -> bool:
    """Return True if every segment can be assigned a unique clip from *clips*.

    Uses a greedy simulation: for each segment in chronological order it picks the
    first available clip that meets the minimum duration constraint and marks it used.
    False-negatives are possible in adversarial orderings but not in practice.
    """
    used: set[str] = set()
    for i, timeline_start in enumerate(cut_points):
        needed = (
            cut_points[i + 1] if i + 1 < len(cut_points) else song_duration_sec
        ) - timeline_start
        if needed <= 0:
            continue
        available = [
            c for c in clips
            if c["path"] not in used and c["duration_sec"] >= needed * MIN_SPEED
        ]
        if not available:
            return False
        used.add(available[0]["path"])
    return True


def select_clips(
    db_path: Path,
    vibe: str | None,
    lyric_blocks: list[dict],
    song_duration_sec: float,
    same_anime: bool = False,
) -> list[dict]:
    """Select one clip per timeline segment and return a ready-to-render clip list.

    Parameters
    ----------
    db_path:
        Path to the clips SQLite database.
    vibe:
        Primary vibe tag to query (e.g. "sad", "hype"), or None to draw from
        all clips regardless of vibe.
    lyric_blocks:
        List of lyric block dicts, each with at least ``start_ms`` (int).
    song_duration_sec:
        Total song length; used to compute the duration of the last segment.
    same_anime:
        If True, restrict all clips to a single anime and enforce no-repetition.

    Returns
    -------
    list[dict]
        One entry per segment::

            {
                "path":               str,   # absolute path to the source clip
                "timeline_start_sec": float, # when this clip starts in the video
                "clip_start_sec":     float, # seek offset inside the source file
                "duration_sec":       float, # how long the clip plays (wall-clock)
                "speed":              float, # playback speed (1.0 = normal)
            }

    Raises
    ------
    RuntimeError
        If the database has no matching clips, if a segment cannot be filled, or
        (in same_anime mode) if no single anime has enough unique clips.
    """
    if vibe is None:
        all_clips = db_manager.query_clips(db_path, None)
        if not all_clips:
            raise RuntimeError("No clips in database. Run `tag` first.")
        all_weights = [1.0] * len(all_clips)
    else:
        primary = db_manager.query_clips(db_path, vibe)
        secondary = db_manager.query_clips(db_path, "neutral")

        if not primary and not secondary:
            raise RuntimeError(
                f"No clips in database for vibe '{vibe}'. Run `tag` first."
            )

        all_clips = primary + secondary
        all_weights = [1.0] * len(primary) + [0.4] * len(secondary)

    # Cut points are built before anime selection so _can_fill_without_repetition
    # can use them during the feasibility check.
    # Minimum gap between cut points — prevents sub-frame first segments when
    # an SRT file starts its first lyric at 1–33 ms instead of exactly 0.
    MIN_CUT_GAP = 0.1  # seconds

    cut_points = [0.0]
    for block in lyric_blocks:
        t = block["start_ms"] / 1000.0
        if t - cut_points[-1] >= MIN_CUT_GAP:
            cut_points.append(t)

    no_repeat = False  # True only when same_anime succeeds — drives used_paths logic below

    if same_anime:
        def _anime_name(clip_path: str) -> str | None:
            """Extract the anime folder name from a path like …/anime/<name>/…"""
            parts = Path(clip_path).parts
            for i, part in enumerate(parts):
                if part.lower() == "anime" and i + 1 < len(parts):
                    return parts[i + 1]
            return None

        animes = list({name for c in all_clips if (name := _anime_name(c["path"])) is not None})
        if not animes:
            raise RuntimeError("No anime folders found in clip paths.")

        random.shuffle(animes)
        chosen_anime = None
        for candidate in animes:
            filtered = [
                (c, w) for c, w in zip(all_clips, all_weights)
                if _anime_name(c["path"]) == candidate
            ]
            candidate_clips = [c for c, _ in filtered]
            if _can_fill_without_repetition(candidate_clips, cut_points, song_duration_sec):
                chosen_anime = candidate
                all_clips = candidate_clips
                all_weights = [w for _, w in filtered]
                no_repeat = True
                break

        if chosen_anime is None:
            raise RuntimeError(
                "No single anime has enough clips to fill all segments without repetition. "
                "Add more clips or run without --same-anime."
            )

        console.print(f"  [dim]Same-anime mode: [bold]{chosen_anime}[/bold][/dim]")

    result: list[dict] = []
    used_paths: set[str] = set()
    last_path: str | None = None

    for i, timeline_start in enumerate(cut_points):
        needed_duration = (
            cut_points[i + 1] if i + 1 < len(cut_points) else song_duration_sec
        ) - timeline_start

        if needed_duration <= 0:
            continue

        min_clip_dur = needed_duration * MIN_SPEED
        usable = [
            (c, w) for c, w in zip(all_clips, all_weights)
            if c["duration_sec"] >= min_clip_dur
            and (not no_repeat or c["path"] not in used_paths)
        ]
        if not usable:
            raise RuntimeError(
                f"No clip long enough for a {needed_duration:.1f}s segment "
                f"(need at least {min_clip_dur:.1f}s at {MIN_SPEED:.0%} speed). "
                "Add more/longer clips to the database."
            )

        pop, weights = zip(*usable)

        clip = random.choices(pop, weights=weights, k=1)[0]
        # Single retry to avoid placing the same clip back-to-back.
        if clip["path"] == last_path and len(pop) > 1:
            clip = random.choices(pop, weights=weights, k=1)[0]

        if no_repeat:
            used_paths.add(clip["path"])

        if clip["duration_sec"] >= needed_duration:
            clip_start = random.uniform(0.0, clip["duration_sec"] - needed_duration)
            speed = 1.0
        else:
            # Clip is shorter than needed — slow it down to fill the segment exactly.
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
