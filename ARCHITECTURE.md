# Architecture

## Full Data Flow

```
INPUTS
  song.mp3 / song.wav
  lyrics.srt               (hand-timed in Subtitle Edit)
  vibe = "energic" | "sad"

STEP 1 — PARSE LYRICS
  srt_parser.py
  → List of {index, start_ms, end_ms, text}

STEP 2 — ANALYZE SONG
  beat_detector.py (librosa)
  → {bpm, beat_times: [float, ...], duration_sec}

STEP 3 — SELECT CLIPS
  clip_selector.py
  → query SQLite DB by vibe + energy range
  → fill song duration with randomly chosen clips
  → snap cut points to nearest beat timestamp
  → List of {path, start_sec, duration_sec}

STEP 4 — BUILD RESOLVE PROJECT
  resolve_builder.py
  → connect to running Resolve instance
  → create new project + timeline
  → Video track 1:   place clips
  → Video track 2:   Text+ nodes from SRT blocks
  → Audio track 1:   song file at 00:00:00:00

OUTPUT
  DaVinci Resolve project (live, open in Resolve)
  Human takes over for final edit
```

---

## Vibe → Clip Mapping

| Vibe     | energy_score range | Example CLIP tags                        |
|----------|--------------------|------------------------------------------|
| energic  | 0.6 – 1.0          | crowd, fire, fast, explosion, neon, city |
| sad      | 0.0 – 0.4          | rain, alone, dark, sunset, slow, empty   |

Clips scored 0.4–0.6 are "neutral" and can appear in either vibe at lower weight.

The `vibe_label` column in the DB is set at tagging time based on energy_score:
- energy >= 0.6 → "energic"
- energy <= 0.4 → "sad"
- else → "neutral"

Clip selector weights: primary vibe 70%, neutral 30%, opposite 0%.

---

## Beat Snapping Logic

For each clip cut point candidate:
1. Find the nearest beat timestamp within a ±150ms tolerance window.
2. If a beat exists in that window, snap to it.
3. If not, keep the raw cut point.

This keeps cuts musical without forcing every cut onto a beat.

---

## Lyric Block → Text+ Node Mapping

Each SRT block becomes one Text+ node on Video Track 2:
- `In` point = `start_ms` converted to Resolve timecode at project FPS
- `Out` point = `end_ms` converted to Resolve timecode
- `Text` content = the raw SRT text (newlines preserved)

Font, size, position are set to sensible defaults and left for the human to style globally.
Default: white, center screen, 72pt, no outline (easy to change as a compound node).

---

## SQLite Schema Summary

See `src/db/schema.sql` for full schema. Key table:

```sql
clips (
  id           INTEGER PRIMARY KEY,
  path         TEXT UNIQUE NOT NULL,
  duration_sec REAL,
  fps          REAL,
  tags         TEXT,        -- JSON array: ["fire", "neon", "crowd"]
  energy_score REAL,        -- 0.0 to 1.0
  vibe_label   TEXT,        -- "energic" | "sad" | "neutral"
  width        INTEGER,
  height       INTEGER,
  added_at     TEXT         -- ISO timestamp
)
```

---

## CLI Interface

```bash
# Tag a new video pack (one-time per pack)
python src/main.py tag --folder "D:/VideoPacka/Pack01"

# Build a Resolve project
python src/main.py build \
  --song "D:/Music/track.mp3" \
  --lyrics "D:/Music/track.srt" \
  --vibe energic \
  --fps 30 \
  --name "my_edit_v1"

# Preview which clips would be removed for a given anime (no deletion)
python src/main.py remove-anime --name "Naruto" --dry-run

# Remove all clips from an anime from the database only
python src/main.py remove-anime --name "Naruto"

# Remove all clips from an anime from the database AND delete the files from disk
python src/main.py remove-anime --name "Naruto" --delete-files

# Remove a single clip by exact path
python src/main.py remove-clip --path "D:/Clips/Naruto/ep01.mp4"
```

### `remove-anime` details

Matches clips whose `path` contains the given `--name` as a substring (case-insensitive on most filesystems). Always shows the matching list and asks for confirmation before deleting.

| Flag | Default | Effect |
|------|---------|--------|
| `--name` | required | Substring matched against clip paths |
| `--dry-run` | false | List matches without deleting |
| `--delete-files` | false | Also delete the video files from disk (irreversible) |

---

## Error Handling Expectations

- If Resolve is not running → print clear error: "Please open DaVinci Resolve before running build."
- If DB has fewer clips than needed to fill song duration → allow clip reuse (random re-selection, avoid consecutive repeats).
- If a clip file has moved or is missing → skip it, log a warning, continue.
- If an SRT block has no text → skip that block silently.
