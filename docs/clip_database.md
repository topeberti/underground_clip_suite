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

CLIP (Contrastive Language-Image Pretraining) scores a set of candidate text labels
against sampled frames from the video. The top-scoring labels become the clip's tags.

### Candidate Tag List

The agent should define a master list of candidate tags. Suggested starting set:

```python
CANDIDATE_TAGS = [
    # Energic / intense
    "fire", "explosion", "crowd", "concert", "city at night", "neon lights",
    "fast motion", "car chase", "fight", "storm", "lightning", "waterfall",
    "sports", "running", "jumping", "skateboarding", "waves crashing",

    # Sad / calm / melancholic
    "rain", "empty street", "alone", "sunset", "fog", "dark room",
    "slow motion", "candle", "window", "ocean horizon", "abandoned",
    "autumn leaves", "silhouette", "crying", "hands", "close up face",

    # Neutral / versatile
    "nature", "forest", "mountains", "sky", "clouds", "water",
    "urban", "building", "road", "texture", "abstract", "smoke",
    "light leak", "bokeh", "aerial", "people walking",
]
```

### Sampling Strategy

Sample N frames evenly distributed across the clip duration.
Recommended N: `max(4, int(duration_sec / 5))` — one frame per 5 seconds, minimum 4.

```python
import cv2

def sample_frames(video_path: str, n: int) -> list:
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = [int(i * total / n) for i in range(n)]
    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames
```

---

## Energy Scoring

Energy score combines two signals:

### 1. Motion Score (optical flow magnitude)
```python
def motion_score(video_path: str, sample_pairs: int = 10) -> float:
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    scores = []
    step = max(1, total // sample_pairs)
    prev = None
    for i in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            flow = cv2.calcOpticalFlowFarneback(prev, gray, None,
                                                0.5, 3, 15, 3, 5, 1.2, 0)
            magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2).mean()
            scores.append(magnitude)
        prev = gray
    cap.release()
    # Normalize: typical range 0–30, clip and scale to 0–1
    raw = np.mean(scores) if scores else 0.0
    return float(min(raw / 25.0, 1.0))
```

### 2. Brightness Variance Score
```python
def brightness_variance_score(video_path: str, n_frames: int = 10) -> float:
    frames = sample_frames(video_path, n_frames)
    if not frames:
        return 0.5
    means = [np.mean(f) for f in frames]
    variance = np.std(means)
    # High variance = fast cuts / flashing = more energic
    return float(min(variance / 60.0, 1.0))
```

### Combined Energy Score
```python
energy_score = 0.7 * motion_score + 0.3 * brightness_variance_score
```

---

## Vibe Label Assignment

```python
def assign_vibe(energy_score: float) -> str:
    if energy_score >= 0.6:
        return "energic"
    elif energy_score <= 0.4:
        return "sad"
    else:
        return "neutral"
```

---

## Re-tagging & Updates

- Running `tag` on a folder that's already been tagged will **skip** existing clips (by path).
- To **force re-tag** a clip: `python src/main.py retag --path "D:\clip.mp4"`
- To **delete** a clip from DB (e.g. file moved): `python src/main.py remove-clip --path "D:\clip.mp4"`
- To **inspect** the DB: `python src/main.py stats` — shows clip count, vibe distribution, energy histogram.
