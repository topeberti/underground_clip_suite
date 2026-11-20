# Video Generator — Agent Instructions

## What This Project Does

Automates the creation of AMV / lyric-edit videos.

Given:
- A song file (.mp3 / .wav)
- A lyrics file (.srt, timed manually in Subtitle Edit)
- An optional vibe flag ("energic" or "sad")

It produces:
- A `.fcpxml` file per timeline (kept for manual import).
- `videogen_build.lua` in Resolve's Scripts menu: one click in Resolve builds every timeline
  (vertical 1080×1920, song, styled subtitles) and renders the `.mp4` files.
  See `docs/resolve_automation.md`.

The project is **fully implemented**. Agent tasks are typically bug fixes, new features,
or extending the vibe/tagging system.

---

## Repository Structure

```
video_generator/
├── AGENT_INSTRUCTIONS.md        ← you are here
├── ARCHITECTURE.md              ← full technical design (authoritative)
├── SETUP.md                     ← environment + dependency setup
├── docs/
│   ├── resolve_automation.md    ← one-click Lua script: how it works, Resolve API quirks
│   ├── resolve_api.md           ← legacy Resolve scripting notes (Studio-only Python)
│   ├── clip_database.md         ← clip tagging + DB schema
│   ├── srt_format.md            ← .srt parsing notes
│   └── vibe_system.md           ← how vibe maps to clip selection
├── src/
│   ├── main.py                  ← CLI entry point (typer)
│   ├── tagger/
│   │   ├── constants.py         ← CANDIDATE_TAGS list, VIDEO_EXTENSIONS set
│   │   ├── clip_tagger.py       ← OpenCLIP semantic tagging
│   │   ├── energy_scorer.py     ← optical-flow + brightness energy scoring
│   │   └── tag_library.py       ← batch-tag a folder; single-clip re-tag
│   ├── timeline/
│   │   ├── beat_detector.py     ← librosa BPM + duration analysis
│   │   ├── clip_selector.py     ← lyric-boundary cut points + weighted clip selection
│   │   ├── fcpxml_builder.py    ← render clip list → .fcpxml file
│   │   ├── resolve_script.py    ← framing, subtitle wrapping, generated Resolve Lua script
│   │   ├── build_runner.py      ← shared Build pipeline (CLI + web UI)
│   │   └── resolve_builder.py   ← legacy: direct Resolve API (not used by CLI)
│   ├── lyrics/
│   │   └── srt_parser.py        ← .srt file parser (pysrt + regex fallback)
│   ├── db/
│   │   ├── schema.sql            ← SQLite schema
│   │   └── db_manager.py        ← DB CRUD helpers
│   └── uploader/
│       ├── batch.py             ← bulk .mp4 upload to TikTok / Instagram
│       ├── auth.py              ← OAuth flows (TikTok, Instagram)
│       ├── tiktok.py            ← TikTok Video Upload API wrapper
│       ├── instagram.py         ← Instagram Graph API Reels wrapper
│       └── ngrok_server.py      ← local OAuth redirect server
├── clips_db/
│   └── clips.db                 ← SQLite database (generated, not committed)
└── output/                      ← .fcpxml files land here
```

---

## Core Pipeline (already implemented)

```
srt_parser → beat_detector → clip_selector → fcpxml_builder → .fcpxml
                                           └→ resolve_script → videogen_build.lua → (Resolve) → .mp4
```

See ARCHITECTURE.md for the full annotated data flow.

---

## CLI Commands

```bash
python src/main.py init-db
python src/main.py tag --folder "D:\Clips\Pack01"
python src/main.py tag --folder "D:\Clips\Pack01" --force   # re-tag existing
python src/main.py retag --path "D:\Clips\clip.mp4"
python src/main.py remove-clip --path "D:\Clips\clip.mp4"
python src/main.py remove-anime --name "Naruto" [--dry-run] [--delete-files]
python src/main.py stats
python src/main.py build --song track.mp3 --lyrics track.srt --vibe energic --fps 30 --name edit_v1
python src/main.py build ... --count 5 --same-anime
python src/main.py setup-upload [--platform tiktok|instagram|all]
python src/main.py upload-batch --folder exports/ --caption "caption #fyp"
python src/main.py upload-status [--last N]
```

---

## Key Design Decisions

- **Cut points come from lyric boundaries**, not beat-snapping. One clip per lyric segment.
  `beat_detector` is still called to obtain `duration_sec`; `beat_times` is not used downstream.
- **Resolve is driven by a generated Lua script**, not the Python API: the user runs free
  Resolve 21.2, where external/Python scripting is Studio-only. The script has no file
  access (`io` is nil) and reports via `error()` into Resolve's log. Read
  `docs/resolve_automation.md` before touching `resolve_script.py`.
- **No slow-motion in Build** (`min_speed=1.0`): Resolve's API can't set clip speed.
  `MIN_SPEED = 0.5` is still the selector default for other callers.
- **MIN_CUT_GAP = 0.1 s** — cut points within 100 ms of the previous are discarded,
  preventing a 1-frame first clip when an SRT starts at 1 ms instead of 0 ms.
- **same_anime mode** uses a greedy feasibility check before committing to an anime;
  raises `RuntimeError` rather than silently reusing footage.

---

## Key Constraints

- Python **3.10+**
- Platform: **Windows** (user runs DaVinci Resolve on Windows)
- All paths should use `pathlib.Path`
- OpenCLIP model (`ViT-B-32`) is loaded lazily and cached in-process; GPU used when available
- The database (`clips_db/clips.db`) and output folder are git-ignored
