# DaVinci Resolve Automation (one-click script)

Build writes a Lua script, `videogen_build.lua`, into Resolve's Scripts menu. Run once from
**Workspace → Scripts → videogen_build**, it builds every timeline from that Build and
renders each one as a vertical `.mp4` with burned-in lyrics. Code: `src/timeline/resolve_script.py`.

Verified on **DaVinci Resolve 21.2 free** (Windows), November 2026.

---

## Why a Lua script (and not Python or the MCP server)

| Route | Free 21.2 | Why |
|---|---|---|
| External scripting (`DaVinciResolveScript` from Python, MCP servers) | ❌ | Studio-only feature |
| Python scripts in Workspace → Scripts | ❌ | Moved to Studio in 21.1; `.py` files are not even listed |
| **Lua scripts in Workspace → Scripts** | ✅ | Full `resolve` API access |

The in-app Lua is sandboxed:

- `io` is `nil`, so the script **cannot read or write files**. Every input (paths, cut list,
  zooms) is baked into the generated script.
- `print` output does not reach the Console window. The script reports with
  `error("VIDEOGEN RESULT: …")`, which Resolve writes to its log:
  `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\logs\ResolveDebug.txt`.

To check a run, search that file for `VIDEOGEN RESULT`:

```
project=a | finn_1: clips=9/9 missing=0 subs=9 scaling=scaleToCrop/scaleToCrop | … | render_started=true jobs=10
```

Other possible messages: `NO_PROJECT_OPEN`, `NO_TEMPLATE …`, `SONG_IMPORT_FAILED`,
`SRT_IMPORT_FAILED`, `<name>: TIMELINE_FAILED`, `<name>: RENDER_JOB_FAILED`, `ERROR …`.

---

## What Build produces

| File | Where |
|---|---|
| `<name>.fcpxml` (one per timeline) | output folder (default `timelines\` next to the song). Kept for manual import |
| `<name>_subtitles.srt` | output folder: the lyrics with long lines wrapped |
| `videogen_build.lua` | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\` (overwritten on every Build) |
| rendered `.mp4` files (after running the script) | `videos\` next to the song |

Timeline names skip any `videos\<name>.mp4` that already exists, so a new Build never
overwrites an earlier render. Running the **same** script twice does re-render to the same
names, because the script can't look at the disk.

---

## What the script does, per timeline

1. **Duplicate the template.** It copies the `videogen_template` timeline, empties the copy,
   and forces 1080×1920 with "scale full frame with crop".
2. **Add subtitles first.** The wrapped `.srt` goes into the empty timeline.
3. **Place the clips one by one**, video only, each starting where the previous clip really ended.
4. **Zoom each clip.** 1.0, or more for clips with letterbox bars baked into the picture.
5. **Add the song** on A1 at 00:00.
6. **Queue a render job.** It uses the `videogen_tiktok` render preset if the project has one,
   otherwise H.264 MP4 at 1080×1920 with subtitles burned in.

After the loop it starts all the render jobs at once. Imported media goes into a
**Video Generator** bin in the Media Pool.

---

## Resolve API behaviour this relies on (measured)

### Subtitles always append at the timeline end
`MediaPool:AppendToTimeline` ignores `recordFrame` for a subtitle (`.srt`) item and places it
after the last item in the timeline. With clips already there, every caption landed
`timeline length` frames late. Fix: append the subtitles **while the timeline is still
empty**, then place the clips.

### Source frames are counted in the clip's own fps
`startFrame` / `endFrame` in a clip-info dict are frames of the **source** (23.976 or 24 fps
for most anime), not of the 30 fps timeline. `endFrame` is **exclusive** and is rounded to a
whole frame. Whole 24 fps frames can't produce every 30 fps length (for example, no whole
source length gives exactly 49 timeline frames), so placing all clips at fixed record frames
left 1-frame gaps. Fix: place clips one at a time. Each starts at the previous clip's real
`GetEnd()` and aims at its lyric cut, so cuts are within ±1 frame and there are no gaps.

### Clip speed can't be set
There is no API to set a retime speed. Build therefore calls the clip selector with
`min_speed=1.0`: only clips at least as long as their segment are used (no slow-motion).
A song whose last lyric ends long before the song itself does needs one very long clip for
the ending, and Build fails with "No clip long enough".

### Subtitle styles and presets can't be set
No API reads or writes subtitle font, size, position or presets. The style lives on the
subtitle **track**, and duplicating a timeline keeps it. That is why the script copies a
user-made `videogen_template` timeline. Without the template it creates a plain timeline,
and the subtitles keep Resolve's default style.

### Image scaling
The timeline setting `timelineInputResMismatchBehavior` alone was seen to be ignored (clips
followed the project's scaling), so the script sets `scaleToCrop` on **both** the timeline
and the project. Note that this changes the project's image scaling for any timeline that
uses project settings.

### Pinterest (still-image) edits
Build with `--edit-type pinterest` (or *Edit type → Pinterest images* in the web UI) puts
still images in the clip table instead of video clips: one entry per image (changing on the song's beats, or every ≤ 0.5 s),
`src = 0`, zoom 1.0. The script sets scaling to `centerCrop` ("center crop with no
resizing") instead of `scaleToCrop`, so every image shows at its native pixel size, centered
in 1080×1920. As with clips, this changes the project's scaling setting.

**Stills can't be trimmed:** `AppendToTimeline` ignores `startFrame`/`endFrame` for an
image and places it at the default still duration (5 s): 27 images gave a 135 s video.
So Build first turns each used image into an H.264 clip (1 s, or longer than the longest image) at the timeline fps and native
size (cached in `pinterest\media_clips\`, using ffmpeg from PATH or Subtitle Edit's copy),
and the script cuts those clips like any video. H.264 needs even sizes, so an odd width or
height gets 1 black pixel of padding. The picture itself is never scaled.

### Render burn-in works
`SetRenderSettings({ExportSubtitle = true, SubtitleFormat = "BurnIn"})` with H.264 MP4
produced burned-in subtitles in the timeline's subtitle style. No preset is needed. A saved
`videogen_tiktok` preset is optional and takes priority.

---

## Framing (zoom)

"Scale full frame with crop" already fills the 1080×1920 frame from each clip's own
resolution (1920×1080, 1920×800, 1920×1038…). The only extra zoom is for **letterbox bars
baked into the picture** (e.g. Arcane: 1920×1080 file, picture only on rows 132–948).

`measure_zoom()` samples 8 frames and finds, per frame, the thinner of the top/bottom dark
bands (max row brightness ≤ 24). The thinnest band counts as a bar only if all three hold:

- it is at least 2% of the height;
- it is at most 15% of the height (a 2.39:1 picture inside 16:9 is about 12.5%);
- at least two samples have their edge within 4 px of it.

Real bars stay put; a dark scene gives bands that move or are too big. Without the last two
checks, a night scene in Howl's Moving Castle was zoomed 7×.

Zoom = `height / (height − 2·bar) × 1.02`, or exactly **1.0** when there are no bars. On a
random sample of 200 library clips, the only values were 1.0 and about 1.35 (Arcane).

---

## Subtitle line wrapping

Lines longer than **20 characters** (`MAX_LINE_CHARS`) are split into two lines at the most
balanced word boundary, e.g. `Y ahora me ha cambiao el horario` → `Y ahora me ha` /
`cambiao el horario`. The original `.srt` is never modified.

---

## One-time setup in Resolve

Create a timeline named exactly **`videogen_template`**:

1. Media Pool → right-click → Timelines → Create New Timeline. Untick *Use Project
   Settings*. Format: 1080 × 1920, 30 fps.
2. Add a subtitle track and one subtitle item.
3. In the Inspector's **Track** tab, apply the subtitle preset (we use **Subtitle 1**).
4. Leave the placeholder subtitle there. The script deletes it from every copy.

---

## Things that did not work (don't retry)

- **MCP server / external Python**: Studio-only.
- **The MCP's in-app Python bridge (`resolve_bridge.py`)**: free 21.1+ doesn't list `.py`
  scripts. Installing a python.org Python does not change this.
- **Importing the FCPXML and appending the song to A1**: A1 is already occupied by the clips'
  own audio, so the song was silently dropped. The script now places video only.
- **Zoom computed on top of "scale to fit"**: the project's scaling took over and the zooms
  stacked (3–4× too much). Use "scale to crop" plus bar-only zoom.
