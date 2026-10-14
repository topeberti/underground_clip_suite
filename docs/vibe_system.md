# Vibe System

## Overview

The vibe flag is the user's creative intent signal. It drives which clips are selected
from the database for each timeline segment.

---

## Current Vibe Values

| Flag       | energy_score | Description                               |
|------------|--------------|-------------------------------------------|
| `energic`  | ≥ 0.6        | High energy, fast cuts, intense visuals   |
| `sad`      | ≤ 0.4        | Slow, melancholic, atmospheric            |
| `neutral`  | 0.4 – 0.6    | Versatile fallback used in both vibes     |

Omitting `--vibe` draws from all clips with equal weight 1.0.

---

## Clip Selection Algorithm

`clip_selector.select_clips(db_path, vibe, lyric_blocks, song_duration_sec, same_anime)`

### 1. Build the clip pool

```python
primary   = query_clips(db_path, vibe)      # weight 1.0
secondary = query_clips(db_path, "neutral") # weight 0.4
pool = primary + secondary
```

### 2. Build cut points from lyric boundaries

```python
MIN_CUT_GAP = 0.1  # seconds — prevents sub-frame segments

cut_points = [0.0]
for block in lyric_blocks:
    t = block["start_ms"] / 1000.0
    if t - cut_points[-1] >= MIN_CUT_GAP:
        cut_points.append(t)
```

Each consecutive pair of cut points defines one timeline segment.
The last segment runs from `cut_points[-1]` to `song_duration_sec`.

### 3. Assign one clip per segment

For each segment of `needed_duration` seconds:

1. Filter pool to clips that can fill the segment at ≥ 50% speed:
   `clip.duration_sec >= needed_duration * 0.5`
2. Weighted-random sample from the filtered pool.
3. Single retry if the same clip as the previous segment would be selected
   (avoids back-to-back repeats when alternatives exist).
4. Compute playback parameters:
   - If `clip.duration_sec >= needed_duration`:
     `clip_start = random(0, clip.duration_sec − needed_duration)`, `speed = 1.0`
   - Else (clip is shorter):
     `clip_start = 0`, `speed = clip.duration_sec / needed_duration`

### 4. Return value

```python
[
    {
        "path":               str,   # absolute path to source file
        "timeline_start_sec": float, # position on the output timeline
        "clip_start_sec":     float, # in-point within the source file
        "duration_sec":       float, # wall-clock duration of this segment
        "speed":              float, # playback speed (1.0 = normal, <1.0 = slow-mo)
    },
    ...
]
```

---

## Same-Anime Mode

When `same_anime=True`:

1. Extract anime folder names from clip paths
   (the folder directly inside a directory named `anime/`).
2. Shuffle the list of discovered anime names.
3. Try each candidate: simulate clip assignment and check that every segment
   can be covered with a **unique** clip from that anime.
4. Use the first anime that passes. All clips in the final output come from it.
5. Raise `RuntimeError` if no single anime has enough unique clips.

---

## Minimum Speed Floor

`MIN_SPEED = 0.5` — clips will never be slowed below 50% of their original speed.
A clip is excluded from a segment's pool entirely if
`clip.duration_sec < needed_duration * MIN_SPEED`.

---

## Vibe Weights

| Pool     | Weight | When used                              |
|----------|--------|----------------------------------------|
| Primary  | 1.0    | Clips whose `vibe_label` matches vibe  |
| Neutral  | 0.4    | Clips labelled `neutral`               |
| Opposite | —      | Never selected                         |

When `vibe=None`, all clips receive weight 1.0 and there is no secondary pool.

---

## Future Vibes (not implemented)

| Flag        | energy_score | Notes                         |
|-------------|--------------|-------------------------------|
| `hype`      | ≥ 0.8        | Subset of energic, very fast  |
| `romantic`  | 0.2 – 0.5    | Warm tones, slow, intimate    |
| `dark`      | ≤ 0.35       | Low brightness, heavy         |
| `cinematic` | 0.3 – 0.7    | Wide shots, nature, epic      |

To add a vibe: extend `CANDIDATE_TAGS`, re-tag the library, add the new label value
to `assign_vibe()` in `tag_library.py`, and add it to the CLI's vibe validation in `main.py`.
