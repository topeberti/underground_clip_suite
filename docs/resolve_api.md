# DaVinci Resolve Scripting API — Notes

## Connection Pattern

```python
import DaVinciResolveScript as dvr_script

resolve = dvr_script.scriptapp("Resolve")
if resolve is None:
    raise RuntimeError("DaVinci Resolve is not running. Please open it first.")

project_manager = resolve.GetProjectManager()
project = project_manager.CreateProject("my_edit_v1")
media_pool = project.GetMediaPool()
```

---

## Key Object Hierarchy

```
resolve
  └── GetProjectManager()
        └── CreateProject(name) / GetCurrentProject()
              ├── GetMediaPool()
              │     ├── GetRootFolder()
              │     └── ImportMedia([paths]) → [MediaPoolItem, ...]
              └── GetCurrentTimeline() / GetTimelineByIndex(i)
                    ├── AppendClipToTimeline({mediaPoolItem, startFrame, endFrame})
                    └── GetTrackCount("video") / GetTrackCount("audio")
```

---

## Creating a Timeline

```python
media_pool = project.GetMediaPool()
timeline = media_pool.CreateEmptyTimeline("Main Edit")
project.SetCurrentTimeline(timeline)

# Set timeline FPS
project.SetSetting("timelineFrameRate", "30")  # or "24", "25", "60"
project.SetSetting("timelineResolutionWidth", "1920")
project.SetSetting("timelineResolutionHeight", "1080")
```

---

## Importing Media

```python
# Import a list of file paths
media_items = media_pool.ImportMedia([
    r"D:\VideoPacka\clip01.mp4",
    r"D:\Music\track.mp3",
])
# Returns list of MediaPoolItem objects in same order
```

---

## Placing Clips on the Timeline

```python
# AppendClipToTimeline takes a dict
clip_info = {
    "mediaPoolItem": media_item,
    "startFrame": 0,              # in clip's own frame space
    "endFrame": 90,               # exclusive, so 90 frames @ 30fps = 3 seconds
    "trackIndex": 1,              # 1-indexed, track 1 = Video Track 1
    "recordFrame": 0,             # where on the timeline to place it (in frames)
    "mediaType": 1,               # 1 = video, 2 = audio
}
media_pool.AppendClipToTimeline(clip_info)
```

> **Important:** `recordFrame` must be tracked manually. After placing each clip, 
> advance recordFrame by the clip's duration in frames.

---

## Adding a Text+ Node (Lyrics)

Text+ (Fusion titles) cannot be placed directly via the scripting API's simple clip methods.
The practical workaround:

### Option A — Use a Title from Media Pool (recommended)
```python
# Get the Titles folder from the media pool
root = media_pool.GetRootFolder()
# Titles are in a special folder; navigate to it
# Then append as any other clip with text overridden via Fusion — complex.
```

### Option B — Use plain "Text" generator (simpler, less pretty)
DaVinci Resolve has a built-in Text generator accessible via the API.
Agent should implement this path first, then upgrade to Text+ if time allows.

### Option C — Place subtitle track as .srt (easiest for MVP)
```python
timeline.ImportIntoTimeline(srt_path, {
    "timelinePath": srt_path,
    "importType": "subtitles"
})
```
This places the entire .srt as a subtitle track automatically. 
**This is the recommended MVP approach.** Text+ styling can come later.

---

## Timecode ↔ Frame Conversion

```python
def ms_to_frames(ms: float, fps: float) -> int:
    return int((ms / 1000.0) * fps)

def frames_to_timecode(frames: int, fps: float) -> str:
    total_seconds = frames / fps
    h = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    s = int(total_seconds % 60)
    f = int((total_seconds - int(total_seconds)) * fps)
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"
```

---

## Known Caveats

1. **Resolve must be open** — there is no headless mode for the scripting API.
2. **Resolve's internal Python** — the API works best when called from an external Python process with env vars set (see SETUP.md). Do NOT try to use it from within a Resolve Fusion script for this use case.
3. **AppendClipToTimeline vs InsertClipToTimeline** — Append always goes to the end; Insert lets you specify position. Use Insert with recordFrame for precise placement.
4. **Track indices are 1-based.**
5. **Frame counts in clip space** — when specifying startFrame/endFrame, these are in the *clip's* own frame space (from 0), not the timeline.
6. **Audio track** — place the song on `mediaType: 2` (audio only) to avoid a blank video track being created.

---

## Minimal Working Example

```python
import DaVinciResolveScript as dvr_script

resolve = dvr_script.scriptapp("Resolve")
pm = resolve.GetProjectManager()
project = pm.CreateProject("test_project")
mp = project.GetMediaPool()

items = mp.ImportMedia([r"D:\clip.mp4", r"D:\song.mp3"])
clip_item, audio_item = items[0], items[1]

timeline = mp.CreateEmptyTimeline("Edit")
project.SetCurrentTimeline(timeline)

# Place video clip at frame 0, duration = all frames
info = mp.GetMediaPoolItemByMeidaId  # use clip_item directly
mp.AppendClipToTimeline({"mediaPoolItem": clip_item, "startFrame": 0, "endFrame": 89})

# Place audio
mp.AppendClipToTimeline({"mediaPoolItem": audio_item, "startFrame": 0, "endFrame": 6389, "mediaType": 2})
```
