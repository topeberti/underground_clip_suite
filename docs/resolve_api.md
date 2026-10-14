# DaVinci Resolve Scripting API — Notes

> **Status: Legacy reference.**
> The CLI (`src/main.py build`) now generates `.fcpxml` files imported manually into
> Resolve. Direct scripting via the Resolve API (`resolve_builder.py`) is no longer
> used by the CLI but the module is kept for reference.

---

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
media_items = media_pool.ImportMedia([
    r"D:\VideoPacka\clip01.mp4",
    r"D:\Music\track.mp3",
])
# Returns list of MediaPoolItem objects in same order
```

---

## Placing Clips on the Timeline

```python
clip_info = {
    "mediaPoolItem": media_item,
    "startFrame": 0,      # in clip's own frame space
    "endFrame": 90,       # exclusive: 90 frames @ 30fps = 3 seconds
    "trackIndex": 1,      # 1-indexed, track 1 = Video Track 1
    "recordFrame": 0,     # timeline position in frames
    "mediaType": 1,       # 1 = video, 2 = audio
}
media_pool.AppendClipToTimeline(clip_info)
```

> `recordFrame` must be tracked manually. Advance it by the clip's duration
> in frames after each placement.

---

## Adding Subtitles from SRT

```python
timeline.ImportIntoTimeline(srt_path, {
    "timelinePath": srt_path,
    "importType": "subtitles"
})
```

This places the entire `.srt` as a subtitle track.

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
2. **Environment variables required** — see SETUP.md §3 for `RESOLVE_SCRIPT_API`,
   `RESOLVE_SCRIPT_LIB`, and `PYTHONPATH` settings.
3. **Track indices are 1-based.**
4. **Frame counts in clip space** — `startFrame`/`endFrame` are relative to the
   clip's own frame 0, not the timeline.
5. **Audio track** — place the song with `mediaType: 2` to avoid creating a blank
   video track.
6. **AppendClipToTimeline vs InsertClipToTimeline** — Append always goes to the end;
   Insert lets you specify `recordFrame` for precise placement.
