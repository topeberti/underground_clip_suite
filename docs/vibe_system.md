# Vibe System

## Overview

The vibe flag is the user's creative intent signal. It drives:
1. Which clips are selected from the database
2. (Future) Which default color grade preset to apply
3. (Future) Which transition style to use

---

## Current Vibe Values

| Flag       | Description                                        |
|------------|----------------------------------------------------|
| `energic`  | High energy, fast cuts, intense visuals            |
| `sad`      | Slow, melancholic, atmospheric                     |

More vibes can be added by extending the tag candidate list and the DB vibe_label enum.

---

## Clip Selection Algorithm

```python
def select_clips(
    vibe: str,
    song_duration_sec: float,
    beat_times: list[float],
    db_path: str,
    min_clip_duration: float = 2.0,
    max_clip_duration: float = 8.0,
) -> list[dict]:
    """
    Returns ordered list of:
    {
        "path": str,
        "timeline_start_sec": float,  # where to place on timeline
        "clip_start_sec": float,      # start point within the clip file
        "duration_sec": float,        # how long to use
    }
    """
```

### Step-by-step

1. **Query clips by vibe:**
   - Primary pool: clips where `vibe_label == vibe` (weight 1.0)
   - Secondary pool: clips where `vibe_label == "neutral"` (weight 0.4)
   - Combine into a weighted pool

2. **Generate cut points:**
   - Start from t=0
   - Pick a random duration between `min_clip_duration` and `max_clip_duration`
   - Snap the end point to the nearest beat within ±150ms (see beat snapping below)
   - Advance position to end point, repeat until `song_duration_sec` is covered

3. **For each cut point, pick a clip:**
   - Sample from the weighted pool (without consecutive repeats)
   - If the clip is shorter than the needed duration, use the full clip and pick another
   - If the clip is longer, pick a random start point within `clip_duration - needed_duration`

4. **Return the ordered list**

---

## Beat Snapping

```python
def snap_to_beat(t: float, beat_times: list[float], tolerance: float = 0.15) -> float:
    candidates = [b for b in beat_times if abs(b - t) <= tolerance]
    if not candidates:
        return t
    return min(candidates, key=lambda b: abs(b - t))
```

---

## Clip Reuse Policy

If the pool is exhausted (more cuts needed than clips available):
- Allow reuse, but never place the same clip consecutively
- Shuffle the pool and restart selection
- Log a warning: "Pool exhausted — reusing clips. Consider adding more packs."

---

## Future Vibes (not implemented, documented for extension)

| Flag        | energy_score range | Notes                          |
|-------------|--------------------|---------------------------------|
| `hype`      | 0.8 – 1.0          | Subset of energic, very fast   |
| `romantic`  | 0.2 – 0.5          | Warm tones, slow, intimate     |
| `dark`      | 0.0 – 0.35         | Low brightness, heavy          |
| `cinematic` | 0.3 – 0.7          | Wide shots, nature, epic       |

To add a vibe: add it to the candidate tag list, re-tag the library, add a new `vibe_label` value.
