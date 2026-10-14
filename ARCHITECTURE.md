# Architecture

## Full Data Flow

```
INPUTS
  song.mp3 / song.wav
  lyrics.srt               (hand-timed in Subtitle Edit)
  vibe = "energic" | "sad" | (omit for all clips)

STEP 1 — PARSE LYRICS
  srt_parser.py
  → List of {index, start_ms, end_ms, text}

STEP 2 — ANALYZE SONG
  beat_detector.py (librosa)
  → {bpm, beat_times: [float, ...], duration_sec}
  Note: only duration_sec is used downstream; bpm/beat_times are informational.

STEP 3 — SELECT CLIPS
  clip_selector.py
  → build cut points: t=0 plus the start_ms of every lyric block (skipping any
    point within 100 ms of the previous to avoid sub-frame first segments)
  → one segment per gap between consecutive cut points; last segment runs to
    song_duration_sec
  → for each segment, query SQLite by vibe_label (primary weight 1.0, neutral 0.4)
  → weighted-random clip selection; trim (random in-point) or slow (≥ 50% speed)
    to fill the segment exactly
  → optional same-anime mode: restrict all clips to one anime folder, no repetition
  → List of {path, timeline_start_sec, clip_start_sec, duration_sec, speed}

STEP 4 — BUILD FCPXML
  fcpxml_builder.py
  → write a .fcpxml (Final Cut Pro XML) file describing the timeline
  → assets section: one <asset> per unique source clip
  → spine: one <asset-clip> per segment with offset, duration, start (in-point)
  → slow-motion clips get a <timeMap> child element with two timept nodes
  → saved to output/<project_name>.fcpxml

OUTPUT
  output/<project_name>.fcpxml
  Human imports into DaVinci Resolve:
    1. File → Import Timeline → Import AAF, EDL, XML… → select .fcpxml
    2. Drag song onto audio track
    3. File → Import → Subtitles → select .srt
```

---

## Vibe → Clip Mapping

| Vibe     | energy_score range | Example CLIP tags                            |
|----------|--------------------|----------------------------------------------|
| energic  | ≥ 0.6              | crowd, fire, fast motion, explosion, neon    |
| sad      | ≤ 0.4              | rain, alone person, dark room, sunset, fog   |
| neutral  | 0.4 – 0.6          | sky, nature, urban street, bokeh background  |

`vibe_label` is assigned at tagging time from energy_score:
- energy ≥ 0.6 → "energic"
- energy ≤ 0.4 → "sad"
- else → "neutral"

Clip selector weights: primary vibe 1.0, neutral 0.4, opposite 0.

---

## Cut-Point Model

Cut points are derived directly from lyric block boundaries:

```
cut_points = [0.0, block[0].start_sec, block[1].start_sec, ..., block[N-1].start_sec]
```

Rules applied during construction:
- A cut point is only added if it is ≥ 100 ms later than the previous one.
  This prevents a sub-frame first segment when an SRT file starts at 1 ms instead of 0.
- Duplicate start times are de-duplicated by the same `>= MIN_CUT_GAP` check.

Each segment's duration = `cut_points[i+1] − cut_points[i]` (last segment ends at `song_duration_sec`).

---

## Clip Fit Strategy

For each segment of `needed_duration` seconds:

| Clip duration vs. segment | Action |
|---------------------------|--------|
| clip ≥ needed             | random in-point `∈ [0, clip_dur − needed]`, speed = 1.0 |
| clip < needed (but ≥ 50%) | in-point = 0, speed = `clip_dur / needed` (slow-motion) |
| clip < 50% of needed      | clip is excluded from the pool for this segment |

The 50% floor (`MIN_SPEED = 0.5`) prevents visually unacceptable slow-motion.

---

## Same-Anime Mode

When `--same-anime` is passed:

1. All clip paths are scanned for a folder named `anime/` with sub-folders per show.
2. Anime folders are shuffled and tried in order.
3. The first anime for which every segment can be filled with a *different* clip is selected.
4. If no single anime has enough unique clips, a `RuntimeError` is raised.

---

## FCPXML Timeline Format

```xml
<fcpxml version="1.10">
  <resources>
    <format id="r1" frameDuration="1/30s" width="1920" height="1080"/>
    <asset id="r2" name="clip.mp4" src="file:///..." start="0s"
           duration="999999/30s" hasVideo="1" hasAudio="1"/>
    ...
  </resources>
  <library>
    <event name="Video Generator">
      <project name="my_edit">
        <sequence duration="5400/30s" format="r1" tcStart="0s">
          <spine>
            <asset-clip ref="r2" offset="0s" duration="60/30s" start="45/30s"/>
            <!-- slow-motion clip: -->
            <asset-clip ref="r3" offset="60/30s" duration="240/30s" start="0s">
              <timeMap>
                <timept time="0s"        value="0s"        interp="linear"/>
                <timept time="240/30s"   value="120/30s"   interp="linear"/>
              </timeMap>
            </asset-clip>
            ...
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

All time values are expressed as `frames/fps s` (rational seconds). Zero is `0s`.

---

## SQLite Schema Summary

See `src/db/schema.sql` for the full schema. Key table:

```sql
clips (
  id           INTEGER PRIMARY KEY,
  path         TEXT UNIQUE NOT NULL,   -- absolute path to the video file
  duration_sec REAL,
  fps          REAL,
  tags         TEXT,                   -- JSON array: ["fire", "neon", "crowd"]
  energy_score REAL,                   -- 0.0 to 1.0
  vibe_label   TEXT,                   -- "energic" | "sad" | "neutral"
  width        INTEGER,
  height       INTEGER,
  added_at     TEXT                    -- ISO timestamp
)
```

---

## Module Map

| Module | Responsibility |
|--------|----------------|
| `src/main.py` | CLI (typer). All commands: init-db, tag, retag, remove-clip, remove-anime, stats, build, upload-batch, setup-upload, upload-status |
| `src/web/app.py` | Local web UI (FastAPI, 127.0.0.1). `/api/*` routes + static page. Start: `python src/main.py serve` |
| `src/web/jobs.py` | Background job threads; rich output captured and streamed to the browser via SSE |
| `src/web/fs.py` | Directory listing for the file-picker |
| `src/web/static/` | Single-page frontend (plain HTML/JS/CSS, no build step) |
| `src/timeline/build_runner.py` | Build pipeline shared by CLI `build` and the web UI |
| `src/lyrics/srt_parser.py` | Parse .srt → list of block dicts |
| `src/timeline/beat_detector.py` | librosa BPM + duration analysis |
| `src/timeline/clip_selector.py` | Lyric-boundary cut points → weighted clip assignment |
| `src/timeline/fcpxml_builder.py` | Render clip list → .fcpxml file |
| `src/tagger/clip_tagger.py` | OpenCLIP semantic tag extraction per clip |
| `src/tagger/energy_scorer.py` | Optical-flow + brightness-variance energy score |
| `src/tagger/tag_library.py` | Batch-tag a folder; single-clip re-tag |
| `src/tagger/constants.py` | CANDIDATE_TAGS list, VIDEO_EXTENSIONS set |
| `src/db/db_manager.py` | SQLite CRUD: insert, query, delete, stats |
| `src/uploader/batch.py` | Bulk-upload .mp4 files to TikTok / Instagram |
| `src/uploader/auth.py` | OAuth flows for TikTok and Instagram |
| `src/uploader/tiktok.py` | TikTok Video Upload API wrapper |
| `src/uploader/instagram.py` | Instagram Graph API Reels wrapper |
| `src/timeline/resolve_builder.py` | Legacy: direct Resolve scripting API (not used by CLI) |

---

## Error Handling Expectations

- No clips in DB for requested vibe → `RuntimeError` with actionable message ("Run `tag` first").
- Segment too long for any clip (even at 50% speed) → `RuntimeError` with duration info.
- Same-anime mode with insufficient unique clips → `RuntimeError`.
- SRT block with no text → skipped silently by the parser.
- Clip file missing at tagging time → caught per-clip, warning printed, continues.
