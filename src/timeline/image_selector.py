"""
Image selector — fills each lyric segment with a fast sequence of still images.

Media layout: <media_dir>/<category>/<image files>. For every segment (same cut points
as the clip selector) one category is drawn (see _category_order), and the segment is cut into images
drawn at random from that category: on the song's beats (beat_grid), or evenly at most
max_image_sec each without beat sync. Images may repeat, but never twice in a row (also
across segment boundaries).

All times are whole timeline frames expressed in seconds, so the Resolve script's
frame targets land exactly on each image boundary.

Resolve ignores startFrame/endFrame for stills and places each one at its default still
duration (5 s), so still_clips() turns every used image into a short H.264 clip at the
timeline fps and the image's native size (cropped to the visible frame), and the script
cuts those like any video.
"""

import math
import random
import shutil
import subprocess
from pathlib import Path

from src.timeline.clip_selector import build_cut_points

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
MAX_IMAGE_SEC = 0.5     # fixed-length mode (no beat sync)
MIN_IMAGE_FRAMES = 3    # beat cuts closer than this to a lyric cut are skipped: no flashes
BEATS_PER_IMAGE = (0.125, 0.25, 0.5, 1, 2, 4)
DEFAULT_MEDIA_DIR = Path(r"C:\Users\berti\Documents\Video\pinterest\media")
# Used when ffmpeg isn't on PATH: the copy bundled with Subtitle Edit.
FALLBACK_FFMPEG = Path(r"C:\Users\berti\Documents\Video\subtitle\ffmpeg\ffmpeg.exe")
STILL_CLIP_MIN_SEC = 1.0   # clips are at least this long, and longer than any image slot


def list_categories(media_dir: Path) -> dict[str, list[str]]:
    """Category folder name → image paths. Folders with fewer than 2 images are skipped:
    they can't avoid showing the same image back-to-back."""
    if not media_dir.is_dir():
        raise RuntimeError(f"Image folder not found: {media_dir}")
    categories = {}
    for folder in sorted(p for p in media_dir.iterdir() if p.is_dir()):
        images = sorted(
            str(p) for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if len(images) >= 2:
            categories[folder.name] = images
    if not categories:
        raise RuntimeError(
            f"No category folder with at least 2 images in {media_dir}. "
            "Put images in one sub-folder per category."
        )
    return categories


def beat_grid(beat_times: list[float], bpm: float, duration_sec: float, beats_per_image: float) -> list[float]:
    """Image change times following the song's detected beats.

    Missed beats (gaps of 2+ beat periods, the stretch before the first detected beat and
    after the last) are filled from the BPM. Then every Nth beat is kept (N = beats_per_image
    ≥ 1), or each beat interval is split in 1/beats_per_image parts (< 1)."""
    period = 60.0 / bpm
    beats = sorted(t for t in beat_times if 0.0 <= t <= duration_sec) or [0.0]
    filled = [beats[0]]
    for t in beats[1:]:
        n = round((t - filled[-1]) / period)
        step = (t - filled[-1]) / n if n > 1 else 0.0
        filled.extend(filled[-1] + step * k for k in range(1, n))
        filled.append(t)
    while filled[0] - period > 0.0:
        filled.insert(0, filled[0] - period)
    while filled[-1] + period < duration_sec:
        filled.append(filled[-1] + period)

    if beats_per_image >= 1:
        return filled[::round(beats_per_image)]
    parts = round(1 / beats_per_image)
    return [a + (b - a) * k / parts for a, b in zip(filled, filled[1:]) for k in range(parts)] + [filled[-1]]


def _category_order(names: list[str], count: int) -> list[str]:
    """`count` categories drawn like a shuffled deck: every category is used once before any
    repeats, and the same one never fills two consecutive segments (also across rounds)."""
    order: list[str] = []
    while len(order) < count:
        deck = random.sample(names, len(names))
        if order and len(deck) > 1 and deck[0] == order[-1]:
            deck[0], deck[-1] = deck[-1], deck[0]
        order.extend(deck)
    return order[:count]


def _even_cuts(f0: int, f1: int, max_frames: int) -> list[int]:
    """Frames splitting [f0, f1) evenly into pieces of max_frames or fewer."""
    n = math.ceil((f1 - f0) / max_frames)
    base, extra = divmod(f1 - f0, n)
    cuts, pos = [], f0
    for k in range(n - 1):
        pos += base + (1 if k < extra else 0)
        cuts.append(pos)
    return cuts


def select_images(
    media_dir: Path,
    lyric_blocks: list[dict],
    song_duration_sec: float,
    fps: float,
    beat_times: list[float] | None = None,
    min_image_frames: int = MIN_IMAGE_FRAMES,
    max_image_sec: float = MAX_IMAGE_SEC,
) -> tuple[list[dict], list[str]]:
    """Return (images, categories): the image list in the clip-selector format
    ({path, timeline_start_sec, clip_start_sec, duration_sec, speed}) and the category
    chosen for each segment.

    beat_times: image change times (see beat_grid). Each lyric segment is cut at the ones
    inside it, skipping any that would leave an image shorter than min_image_frames.
    None: segments are split evenly into images of at most max_image_sec."""
    categories = list_categories(media_dir)
    names = list(categories)
    max_frames = max(1, math.floor(max_image_sec * fps))
    grid = sorted({round(t * fps) for t in beat_times}) if beat_times is not None else None

    cut_points = build_cut_points(lyric_blocks)
    ends = cut_points[1:] + [song_duration_sec]

    result: list[dict] = []
    chosen: list[str] = []
    last_path: str | None = None
    segments = [(round(a * fps), round(b * fps)) for a, b in zip(cut_points, ends)]
    segments = [(f0, f1) for f0, f1 in segments if f1 > f0]
    for (f0, f1), category in zip(segments, _category_order(names, len(segments))):
        chosen.append(category)
        if grid is None:
            cuts = _even_cuts(f0, f1, max_frames)
        else:
            cuts = []
            for fr in grid:
                if fr - (cuts[-1] if cuts else f0) >= min_image_frames and f1 - fr >= min_image_frames:
                    cuts.append(fr)
        pos = f0
        for nxt in cuts + [f1]:
            length = nxt - pos
            path = random.choice([p for p in categories[category] if p != last_path])
            result.append({
                "path": path,
                "timeline_start_sec": pos / fps,
                "clip_start_sec": 0.0,
                "duration_sec": length / fps,
                "speed": 1.0,
            })
            last_path = path
            pos += length
    return result, chosen


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg") or (str(FALLBACK_FFMPEG) if FALLBACK_FFMPEG.exists() else None)
    if not exe:
        raise RuntimeError(
            "ffmpeg not found (needed to turn images into clips for Resolve). "
            f"Put ffmpeg on PATH or at {FALLBACK_FFMPEG}."
        )
    return exe


def still_clips(
    images: set[str], media_dir: Path, fps: float, frame: tuple[int, int], min_sec: float = 0.0,
) -> dict[str, str]:
    """Image path → path of an H.264 clip of it at `fps`, longer than min_sec, cached in
    <media_dir>_clips/<category>/. The picture is never scaled, only center-cropped to
    `frame` (w, h), the part a center-crop timeline of that size shows anyway: Resolve
    fails to decode very large clips ("Video size is too small"). Odd widths/heights get
    one black pixel of padding (H.264 needs even sizes), invisible on the black canvas."""
    cache_root = media_dir.parent / f"{media_dir.name}_clips"
    clip_sec = max(math.ceil(STILL_CLIP_MIN_SEC), math.floor(min_sec) + 1)
    fw, fh = frame
    exe = None
    result = {}
    for image in sorted(images):
        src = Path(image)
        out = cache_root / src.parent.name / f"{src.stem}_{fps:g}fps_{clip_sec}s_{fw}x{fh}.mp4"
        if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            exe = exe or _ffmpeg()
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                [
                    exe, "-y", "-v", "error", "-loop", "1", "-framerate", f"{fps:g}", "-i", str(src),
                    "-t", str(clip_sec), "-r", f"{fps:g}",
                    "-vf", f"crop=min(iw\\,{fw}):min(ih\\,{fh}),"
                           "pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:black,"
                           "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "12", "-tune", "stillimage",
                    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    "-an", str(out),
                ],
                check=True, capture_output=True, text=True,
            )
        result[image] = str(out)
    return result
