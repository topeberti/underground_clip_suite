# Video Generator — Agent Instructions

## What This Project Does
Automates the creation of a DaVinci Resolve project scaffold for lyric/edit videos.

Given:
- A song file (.mp3 / .wav)
- A lyrics file (.srt, timed manually in Subtitle Edit)
- A vibe flag ("energic" or "sad")

It produces:
- A DaVinci Resolve project with clips placed on the timeline, lyrics as Text+ nodes, and the song on the audio track.
- The human then does final creative editing. The scaffold is a starting point, not the final product.

---

## Repository Structure

```
video_generator/
├── AGENT_INSTRUCTIONS.md        ← you are here
├── ARCHITECTURE.md              ← full technical design
├── SETUP.md                     ← environment + dependency setup
├── docs/
│   ├── resolve_api.md           ← DaVinci Resolve scripting notes
│   ├── clip_database.md         ← clip tagging + DB schema
│   ├── srt_format.md            ← .srt parsing notes
│   └── vibe_system.md           ← how vibe maps to clip selection
├── src/
│   ├── main.py                  ← CLI entry point
│   ├── tagger/
│   │   ├── clip_tagger.py       ← CLIP-based semantic tagging
│   │   └── energy_scorer.py     ← motion + brightness energy scoring
│   ├── timeline/
│   │   ├── beat_detector.py     ← librosa BPM + beat timestamps
│   │   ├── clip_selector.py     ← vibe-based weighted random selection
│   │   └── resolve_builder.py   ← DaVinci Resolve API timeline builder
│   ├── lyrics/
│   │   └── srt_parser.py        ← .srt file parser
│   └── db/
│       ├── schema.sql            ← SQLite schema
│       └── db_manager.py        ← DB read/write helpers
├── clips_db/
│   └── clips.db                 ← SQLite database (generated, not committed)
└── output/                      ← generated Resolve projects land here
```

---

## Build Order for the Agent

Implement in this exact order. Each step is independently testable.

### Step 1 — SRT Parser (`src/lyrics/srt_parser.py`)
Parse a `.srt` file into a list of dicts:
```python
[{"index": 1, "start_ms": 12500, "end_ms": 15800, "text": "First line"}, ...]
```
Test: parse the sample `docs/srt_format.md` example and print results.

### Step 2 — Database (`src/db/`)
Create the SQLite DB from `schema.sql`. Implement `db_manager.py` with:
- `insert_clip(path, duration, fps, tags, energy_score, vibe_label)`
- `query_clips(vibe_label, min_energy, max_energy, min_duration)` → list of clip dicts

### Step 3 — Clip Tagger (`src/tagger/`)
- `clip_tagger.py`: sample frames from a video, run through CLIP, return top semantic tags
- `energy_scorer.py`: compute motion variance (optical flow or frame diff) + brightness variance → return float 0.0–1.0
- Wire both into a `tag_library.py` script that walks a folder, tags all clips, and inserts into DB

### Step 4 — Beat Detector (`src/timeline/beat_detector.py`)
Use librosa to return:
```python
{"bpm": 128.0, "beat_times": [0.47, 0.94, 1.41, ...], "duration": 213.5}
```

### Step 5 — Clip Selector (`src/timeline/clip_selector.py`)
Given vibe, song duration, and beat_times:
- Query DB for matching clips
- Fill the song duration with randomly selected clips, preferring cuts on beats
- Return an ordered list of `{"path": ..., "start_sec": ..., "duration_sec": ...}`

### Step 6 — Resolve Builder (`src/timeline/resolve_builder.py`)
Connect to a running DaVinci Resolve instance via its Python API.
Place clips, lyrics (Text+ nodes), and song on the timeline.
See `docs/resolve_api.md` for connection details and caveats.

### Step 7 — CLI Entry Point (`src/main.py`)
Wire everything together. See ARCHITECTURE.md for the full flow.

---

## Key Constraints
- DaVinci Resolve **must be open and running** before the script executes. The API connects to a live instance.
- The clip library tagging (`Step 3`) is a **one-time setup** per video pack. Re-run only when adding new packs.
- Python version: **3.10+**
- Platform: **Windows** (user runs DaVinci Resolve on Windows)
- All paths should use `pathlib.Path` for cross-platform safety even on Windows.
