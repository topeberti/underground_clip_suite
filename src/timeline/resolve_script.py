"""
Resolve automation — writes a Lua script that builds, frames, subtitles and renders the
edits inside DaVinci Resolve, run with one click from Workspace > Scripts.

Why Lua: Resolve 21.1+ free only runs Lua from its Scripts menu (Python scripting and
external control are Studio-only). That Lua has no `io` and its `print` never reaches the
Console, so every input is baked into the script and results are reported with error(),
which lands in Resolve's log (Support/logs/ResolveDebug.txt).

Resolve API behaviour the script works around (measured on 21.2 free):
- A subtitle item appended with AppendToTimeline always lands at the timeline END, so the
  subtitles go into the empty timeline first and the clips are placed afterwards.
- startFrame/endFrame count in the clip's own fps (endFrame exclusive, whole frames only),
  so 24 fps sources can't hit every 30 fps length: clips are placed one by one from where
  the previous one really ended, aiming at the lyric cut (±1 frame, never a gap).
- Subtitle styles/presets can't be set through the API: the script duplicates a
  user-made template timeline whose subtitle track already carries the style.
- Speed changes can't be set either, so builds for Resolve only use clips that are long
  enough for their segment (see clip_selector min_speed).
- Image scaling is set on the timeline AND the project (timeline-only was ignored):
  "scaleToCrop" for video clips, "centerCrop" (no resizing) for still-image edits.
"""

import os
from pathlib import Path

import cv2
import numpy as np

SCRIPT_NAME = "videogen_build"
TEMPLATE_NAME = "videogen_template"
RENDER_PRESET = "videogen_tiktok"
OUT_W, OUT_H = 1080, 1920
MAX_LINE_CHARS = 20   # longer lyric lines are split in two so they fit a vertical frame
ZOOM_MARGIN = 1.02    # hides the soft edge left where a letterbox bar was cropped
BAR_LEVEL = 24        # rows darker than this in every sample count as letterbox
MIN_BAR_FRAC = 0.02   # thinner dark bands are picture, not bars
MAX_BAR_FRAC = 0.15   # thicker ones are a dark scene, not bars
BAR_TOLERANCE = 4     # px a bar edge may wobble between sampled frames


def scripts_dir() -> Path:
    """Resolve's per-user Utility scripts folder (listed directly under Workspace > Scripts)."""
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Fusion" / "Scripts" / "Utility"


# ---------------------------------------------------------------- subtitles

def wrap_line(text: str, max_chars: int = MAX_LINE_CHARS) -> str:
    """Split a line longer than max_chars into two lines at the most balanced word boundary."""
    text = " ".join(text.split())
    words = text.split(" ")
    if len(text) <= max_chars or len(words) < 2:
        return text
    best = min(
        range(1, len(words)),
        key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))),
    )
    return " ".join(words[:best]) + "\n" + " ".join(words[best:])


def _srt_time(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_wrapped_srt(blocks: list[dict], out_path: Path) -> Path:
    """Write the parsed lyric blocks back out as SRT with long lines wrapped."""
    out = [
        f"{i}\n{_srt_time(b['start_ms'])} --> {_srt_time(b['end_ms'])}\n{wrap_line(b['text'])}"
        for i, b in enumerate(blocks, 1)
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n\n".join(out) + "\n", encoding="utf-8")
    return out_path


# ---------------------------------------------------------------- framing

def measure_zoom(path: str, samples: int = 8) -> float:
    """Extra zoom on top of Resolve's "scale to crop", which already fills the vertical
    frame from the clip's resolution. Only clips with letterbox bars baked into the
    picture need more: 1.0 otherwise."""
    cap = cv2.VideoCapture(path)
    try:
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if w <= 0 or h <= 0:
            raise RuntimeError(f"Can't read video size of {path}")
        # Per sample, the thinner of the top/bottom dark bands (letterbox is symmetric).
        bands: list[int] = []
        for k in range(samples):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * (0.05 + 0.9 * (k + 0.5) / samples)))
            ok, frame = cap.read()
            if not ok:
                continue
            rows = np.flatnonzero(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).max(axis=1) > BAR_LEVEL)
            if rows.size:   # an all-black frame says nothing about bars
                bands.append(min(int(rows[0]), h - 1 - int(rows[-1])))
    finally:
        cap.release()

    # Real bars sit at the same rows in several frames and are at most ~13% of the
    # height (2.39:1 inside 16:9); a dark scene gives wandering or oversized bands.
    bar = min(bands, default=0)
    steady = sum(b <= bar + BAR_TOLERANCE for b in bands) >= 2
    if bar < MIN_BAR_FRAC * h or bar > MAX_BAR_FRAC * h or not steady:
        bar = 0
    if bar == 0:
        return 1.0
    return h / (h - 2 * bar) * ZOOM_MARGIN


# ---------------------------------------------------------------- Lua

def _lua_str(s: str) -> str:
    """Lua long-bracket literal: no escaping needed for Windows paths or quotes."""
    level = 0
    while f"]{'=' * level}]" in s:
        level += 1
    eq = "=" * level
    return f"[{eq}[{s}]{eq}]"


def write_lua(
    builds: list[dict],
    song: Path,
    srt: Path,
    render_dir: Path,
    zooms: dict[str, float],
    script_path: Path,
    scaling: str = "scaleToCrop",
) -> Path:
    """Write the Resolve script. scaling: Resolve's timelineInputResMismatchBehavior,
    "scaleToCrop" (fill the frame) or "centerCrop" (native size, never resized).

    builds: [{"name": str, "clips": [{"path", "timeline_start_sec", "clip_start_sec", "duration_sec"}]}]
    """
    lines = ["local BUILDS = {"]
    for b in builds:
        lines.append(f"  {{ name = {_lua_str(b['name'])}, clips = {{")
        for c in b["clips"]:
            lines.append(
                f"    {{ path = {_lua_str(str(Path(c['path'])))}, at = {c['timeline_start_sec']:.6f}, "
                f"len = {c['duration_sec']:.6f}, src = {c['clip_start_sec']:.6f}, "
                f"zoom = {zooms[c['path']]:.4f} }},"
            )
        lines.append("  } },")
    lines.append("}")

    header = "\n".join([
        "-- Generated by Video Generator. Run from Workspace > Scripts with a project open.",
        "-- Regenerated on every Build; edits here are overwritten.",
        f"local SONG = {_lua_str(str(song))}",
        f"local SRT = {_lua_str(str(srt))}",
        f"local RENDER_DIR = {_lua_str(str(render_dir))}",
        f"local TEMPLATE = {_lua_str(TEMPLATE_NAME)}",
        f"local RENDER_PRESET = {_lua_str(RENDER_PRESET)}",
        f"local OUT_W, OUT_H = {OUT_W}, {OUT_H}",
        f"local SCALING = {_lua_str(scaling)}",
        *lines,
    ])

    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(header + "\n" + _LUA_BODY, encoding="utf-8")
    return script_path


_LUA_BODY = r"""
local log = {}
local function step(s) log[#log + 1] = tostring(s) end
local function round(x) return math.floor(x + 0.5) end

local function timelineNamed(project, name)
    for i = 1, project:GetTimelineCount() do
        local t = project:GetTimelineByIndex(i)
        if t:GetName() == name then return t end
    end
end

local function uniqueName(project, base)
    local name, k = base, 2
    while timelineNamed(project, name) do name = base .. "_" .. k; k = k + 1 end
    return name
end

local ok, err = pcall(function()
    local r = resolve or (Resolve and Resolve()) or (bmd and bmd.scriptapp and bmd.scriptapp("Resolve"))
    if not r then step("NO_RESOLVE_OBJECT"); return end
    local project = r:GetProjectManager():GetCurrentProject()
    if not project then step("NO_PROJECT_OPEN"); return end
    local mp = project:GetMediaPool()
    step("project=" .. tostring(project:GetName()))

    -- Everything this script imports goes into one bin.
    local root = mp:GetRootFolder()
    local bin
    for _, f in ipairs(root:GetSubFolderList() or {}) do
        if f:GetName() == "Video Generator" then bin = f end
    end
    bin = bin or mp:AddSubFolder(root, "Video Generator")
    if bin then mp:SetCurrentFolder(bin) end

    local items = {}
    local function item(path)
        if items[path] == nil then items[path] = (mp:ImportMedia({ path }) or {})[1] or false end
        return items[path] or nil
    end
    local song, subs = item(SONG), item(SRT)
    if not song then step("SONG_IMPORT_FAILED " .. SONG) end
    if not subs then step("SRT_IMPORT_FAILED " .. SRT) end

    local template = timelineNamed(project, TEMPLATE)
    if not template then step("NO_TEMPLATE (subtitles keep Resolve's default style)") end

    local hasPreset = false
    for _, p in ipairs(project:GetRenderPresetList() or {}) do
        if p == RENDER_PRESET then hasPreset = true end
    end

    local jobs = {}
    for _, b in ipairs(BUILDS) do
        local name = uniqueName(project, b.name)
        local tl
        if template then
            project:SetCurrentTimeline(template)
            tl = template:DuplicateTimeline(name)
        else
            tl = mp:CreateEmptyTimeline(name)
        end
        if not tl then
            step(name .. ": TIMELINE_FAILED")
        else
            project:SetCurrentTimeline(tl)
            -- Empty the copy (the template keeps a styled placeholder subtitle).
            local all = {}
            for _, kind in ipairs({ "video", "audio", "subtitle" }) do
                for t = 1, tl:GetTrackCount(kind) do
                    for _, it in ipairs(tl:GetItemListInTrack(kind, t) or {}) do all[#all + 1] = it end
                end
            end
            if #all > 0 then tl:DeleteClips(all, false) end

            -- Vertical frame. "Scale to crop" fills it from each clip's own resolution (the
            -- per-clip zoom below only removes baked-in letterbox); "center crop" keeps stills
            -- at native size. Set on the project too: a timeline-only setting was ignored.
            tl:SetSetting("useCustomSettings", "1")
            tl:SetSetting("timelineResolutionWidth", tostring(OUT_W))
            tl:SetSetting("timelineResolutionHeight", tostring(OUT_H))
            tl:SetSetting("timelineOutputResolutionWidth", tostring(OUT_W))
            tl:SetSetting("timelineOutputResolutionHeight", tostring(OUT_H))
            tl:SetSetting("timelineInputResMismatchBehavior", SCALING)
            project:SetSetting("timelineInputResMismatchBehavior", SCALING)
            local fps = tonumber(tl:GetSetting("timelineFrameRate")) or 30
            local start = tl:GetStartFrame()

            -- Subtitles first: Resolve appends them at the timeline end, which is still its start.
            if subs then
                if tl:GetTrackCount("subtitle") == 0 then tl:AddTrack("subtitle") end
                mp:AppendToTimeline({ subs })
            end

            -- Clips one by one, each from where the previous really ended, aiming at its lyric cut.
            local pos, missing = start, 0
            for _, c in ipairs(b.clips) do
                local mpi = item(c.path)
                local target = start + round((c.at + c.len) * fps)
                if mpi then
                    local srcFps = tonumber(mpi:GetClipProperty("FPS")) or fps
                    local srcStart = round(c.src * srcFps)
                    local srcLen = round((target - pos) * srcFps / fps)
                    mp:AppendToTimeline({ { mediaPoolItem = mpi, startFrame = srcStart, endFrame = srcStart + srcLen,
                        mediaType = 1, trackIndex = 1, recordFrame = pos } })
                    local placed = tl:GetItemListInTrack("video", 1) or {}
                    local last = placed[#placed]
                    if last and last:GetStart() == pos then
                        -- Set every clip explicitly so no zoom left over from the template survives.
                        last:SetProperty("ZoomGang", true)
                        last:SetProperty("ZoomX", c.zoom)
                        last:SetProperty("ZoomY", c.zoom)
                        pos = last:GetEnd()
                    else
                        missing = missing + 1
                        pos = target
                    end
                else
                    missing = missing + 1
                    pos = target
                end
            end

            if song then
                if tl:GetTrackCount("audio") == 0 then tl:AddTrack("audio", "stereo") end
                mp:AppendToTimeline({ { mediaPoolItem = song, mediaType = 2, trackIndex = 1, recordFrame = start } })
            end

            local nsubs = #(tl:GetItemListInTrack("subtitle", 1) or {})
            local nclips = #(tl:GetItemListInTrack("video", 1) or {})
            step(name .. ": clips=" .. nclips .. "/" .. #b.clips .. " missing=" .. missing .. " subs=" .. nsubs
                .. " scaling=" .. tostring(tl:GetSetting("timelineInputResMismatchBehavior"))
                .. "/" .. tostring(project:GetSetting("timelineInputResMismatchBehavior")))

            -- Render job: a saved preset wins, otherwise H.264 at the timeline's size.
            if hasPreset then project:LoadRenderPreset(RENDER_PRESET)
            else project:SetCurrentRenderFormatAndCodec("mp4", "H264") end
            project:SetRenderSettings({
                SelectAllFrames = true, TargetDir = RENDER_DIR, CustomName = name,
                FormatWidth = OUT_W, FormatHeight = OUT_H, FrameRate = fps,
                ExportVideo = true, ExportAudio = true,
                ExportSubtitle = true, SubtitleFormat = "BurnIn" })
            local job = project:AddRenderJob()
            if job then jobs[#jobs + 1] = job else step(name .. ": RENDER_JOB_FAILED") end
        end
    end

    if #jobs > 0 then
        step("render_started=" .. tostring(project:StartRendering((table.unpack or unpack)(jobs))) .. " jobs=" .. #jobs)
    end
end)
if not ok then step("ERROR " .. tostring(err)) end
error("VIDEOGEN RESULT: " .. table.concat(log, " | "))
"""
