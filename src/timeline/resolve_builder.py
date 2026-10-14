from pathlib import Path

from rich.console import Console

console = Console()


def _sec_to_frames(sec: float, fps: float) -> int:
    return int(sec * fps)


def _connect_resolve():
    import os
    import sys

    modules_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
    dll_path = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll"

    if modules_path not in sys.path:
        sys.path.insert(0, modules_path)

    os.environ.setdefault("RESOLVE_SCRIPT_API",
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting")
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", dll_path)

    try:
        import DaVinciResolveScript as dvr_script
    except ImportError:
        raise RuntimeError(
            "DaVinci Resolve scripting API not found. Check PYTHONPATH. See SETUP.md."
        )
    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError(
            "DaVinci Resolve is not running. Please open it before running build."
        )
    return resolve


def build_project(
    project_name: str,
    clips_sequence: list[dict],
    srt_path: Path,
    song_path: Path,
    fps: float,
    song_duration_sec: float,
) -> None:
    fps = int(fps)  # timeline is set to an integer rate; compute frames at that same rate
    console.print("  [dim]→ Connecting to Resolve…[/dim]")
    resolve = _connect_resolve()
    console.print("  [dim]→ Connected.[/dim]")

    pm = resolve.GetProjectManager()
    console.print("  [dim]→ Got ProjectManager.[/dim]")

    project = pm.CreateProject(project_name)
    if project is None:
        console.print("  [dim]→ Project exists, loading…[/dim]")
        project = pm.LoadProject(project_name)
    if project is None:
        raise RuntimeError(f"Could not create or load project '{project_name}'.")
    console.print(f"  [dim]→ Project ready: {project_name}[/dim]")

    project.SetSetting("timelineFrameRate", str(int(fps)))
    project.SetSetting("timelineResolutionWidth", "1920")
    project.SetSetting("timelineResolutionHeight", "1080")
    console.print("  [dim]→ Settings applied.[/dim]")

    mp = project.GetMediaPool()
    console.print("  [dim]→ Got MediaPool.[/dim]")

    timeline = mp.CreateEmptyTimeline("Main Edit")
    if timeline is None:
        raise RuntimeError("Failed to create timeline 'Main Edit'.")
    project.SetCurrentTimeline(timeline)
    console.print("  [dim]→ Timeline created.[/dim]")

    seen: dict[str, int] = {}
    ordered_paths: list[str] = []
    for clip in clips_sequence:
        p = clip["path"]
        if p not in seen:
            seen[p] = len(ordered_paths)
            ordered_paths.append(p)
    song_str = str(song_path)
    if song_str not in seen:
        seen[song_str] = len(ordered_paths)
        ordered_paths.append(song_str)

    console.print(f"  [dim]→ Importing {len(ordered_paths)} media files…[/dim]")
    imported = mp.ImportMedia(ordered_paths)
    if not imported:
        raise RuntimeError("ImportMedia returned nothing. Check that clip paths are valid.")
    console.print(f"  [dim]→ Imported {len(imported)} items.[/dim]")

    path_to_item = {ordered_paths[i]: imported[i] for i in range(len(ordered_paths))}

    console.print(f"  [dim]→ Placing {len(clips_sequence)} video clips…[/dim]")
    for clip in clips_sequence:
        item = path_to_item.get(clip["path"])
        if item is None:
            console.print(f"  [yellow]warning[/yellow] media item missing for {clip['path']}, skipping.")
            continue
        # Derive length from rounded boundaries so adjacent clips never leave a gap.
        record_frame = round(clip["timeline_start_sec"] * fps)
        end_record = round((clip["timeline_start_sec"] + clip["duration_sec"]) * fps)
        start_frame = round(clip["clip_start_sec"] * fps)
        end_frame = start_frame + max(1, end_record - record_frame)
        try:
            mp.AppendClipToTimeline({
                "mediaPoolItem": item,
                "startFrame": start_frame,
                "endFrame": end_frame,
                "trackIndex": 1,
                "recordFrame": record_frame,
                "mediaType": 1,
            })
        except Exception as exc:
            console.print(f"  [yellow]warning[/yellow] could not place {Path(clip['path']).name}: {exc}")

    console.print("  [dim]→ Placing audio track…[/dim]")
    audio_item = path_to_item.get(song_str)
    if audio_item:
        try:
            mp.AppendClipToTimeline({
                "mediaPoolItem": audio_item,
                "startFrame": 0,
                "endFrame": _sec_to_frames(song_duration_sec, fps),
                "trackIndex": 1,
                "recordFrame": 0,
                "mediaType": 2,
            })
        except Exception as exc:
            console.print(f"  [yellow]warning[/yellow] could not place audio track: {exc}")
    else:
        console.print("  [yellow]warning[/yellow] song not found in imported media.")

    console.print("  [dim]→ Importing subtitles…[/dim]")
    try:
        timeline.ImportIntoTimeline(str(srt_path), {"importType": "subtitles"})
    except Exception as exc:
        console.print(f"  [yellow]warning[/yellow] could not import subtitles: {exc}")

    console.print(f"[green]Done.[/green] Project '[bold]{project_name}[/bold]' is ready in DaVinci Resolve.")
