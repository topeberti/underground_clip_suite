# Clip Database — Schema & Tagging

## SQLite Schema

```sql
-- src/db/schema.sql

CREATE TABLE IF NOT EXISTS clips (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT UNIQUE NOT NULL,       -- absolute path to the video file
    duration_sec REAL NOT NULL,              -- total duration in seconds
    fps          REAL NOT NULL,              -- frames per second
    width        INTEGER,                    -- resolution width
    height       INTEGER,                    -- resolution height
    tags         TEXT NOT NULL DEFAULT '[]', -- JSON array of semantic tag strings
    energy_score REAL NOT NULL DEFAULT 0.5,  -- 0.0 (calm) to 1.0 (intense)
    vibe_label   TEXT NOT NULL DEFAULT 'neutral', -- "energic" | "sad" | "neutral"
    added_at     TEXT NOT NULL               -- ISO 8601 timestamp
);

CREATE INDEX IF NOT EXISTS idx_vibe ON clips(vibe_label);
CREATE INDEX IF NOT EXISTS idx_energy ON clips(energy_score);
```

---

## Semantic Tagging with CLIP

OpenCLIP (ViT-B-32, OpenAI weights) scores every candidate tag against frames sampled
from the clip. Tags whose cosine similarity to the averaged frame embedding is ≥ 0.20
are kept; up to the top 10 are stored.

### Sampling Strategy

`n = max(4, int(duration_sec / 5))` — one frame per 5 seconds, minimum 4.

Frames are sampled at evenly-spaced indices across the clip's total frame count.

### Candidate Tag List (`src/tagger/constants.py`)

```python
CANDIDATE_TAGS = [
    # Energic / intense
    "fire", "explosion", "crowd", "concert", "city at night", "neon lights",
    "fast motion", "car chase", "fight", "storm", "lightning", "waterfall",
    "sports", "running", "jumping", "skateboarding", "waves crashing",

    # Sad / calm / melancholic
    "rain", "empty street", "alone person", "sunset", "fog", "dark room",
    "slow motion", "candle", "window", "ocean horizon", "abandoned building",
    "autumn leaves", "silhouette", "hands", "close up face",

    # Neutral / versatile
    "nature", "forest", "mountains", "sky", "clouds", "water reflection",
    "urban street", "building", "road", "smoke", "dust",
    "light leak", "bokeh background", "aerial view", "people walking",

    # Extra
    "fireworks", "night club", "graffiti", "skyscraper",
]
```

To add new tags: edit `CANDIDATE_TAGS` in `src/tagger/constants.py` and re-tag
the library with `python src/main.py tag --folder <path> --force`.

---

## Energy Scoring

Energy score combines two signals (see `src/tagger/energy_scorer.py`):

### 1. Motion Score (optical flow magnitude)

Sample 10 pairs of frames spaced evenly across the clip.
For each pair, compute Farneback optical flow and take the mean vector magnitude.
Average over all pairs, then normalize: `min(mean / 25.0, 1.0)`.

### 2. Brightness Variance Score

Sample 10 frames evenly. Compute per-frame mean pixel brightness.
Standard deviation of those means, normalized: `min(std / 60.0, 1.0)`.
High variance → fast cuts / flashing → more energic.

### Combined

```
energy_score = min(0.7 × motion_score + 0.3 × brightness_variance_score, 1.0)
```

---

## Vibe Label Assignment (`src/tagger/tag_library.py`)

```python
def assign_vibe(energy_score: float) -> str:
    if energy_score >= 0.6:
        return "energic"
    if energy_score <= 0.4:
        return "sad"
    return "neutral"
```

---

## Supported Video Formats

Defined in `src/tagger/constants.py`:

```python
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
```

---

## Re-tagging & Updates

| Task | Command |
|------|---------|
| Tag a new folder | `python src/main.py tag --folder "D:\Pack01"` |
| Re-tag a single clip | `python src/main.py retag --path "D:\Pack01\clip.mp4"` |
| Re-tag entire folder | `python src/main.py tag --folder "D:\Pack01" --force` |
| Remove a clip from DB | `python src/main.py remove-clip --path "D:\Pack01\clip.mp4"` |
| Remove an anime | `python src/main.py remove-anime --name "Naruto"` |
| View statistics | `python src/main.py stats` |

`tag` skips clips already present in the DB (matched by absolute path).
`--force` overrides this and re-tags everything in the folder.

---

## Model Loading

The CLIP model is loaded lazily on first call to `tag_clip()` and cached in memory
for the rest of the process (`_MODEL_CACHE` dict in `clip_tagger.py`).
GPU is used automatically when `torch.cuda.is_available()` is True.
