from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree


def _t(frames: int, fps: int) -> str:
    return f"{frames}/{fps}s" if frames > 0 else "0s"


def build_fcpxml(
    project_name: str,
    clips_sequence: list[dict],
    fps: float,
    song_duration_sec: float,
    output_dir: Path,
) -> Path:
    fps_int = int(fps)
    total_frames = int(song_duration_sec * fps_int)

    root = Element("fcpxml", version="1.10")
    resources = SubElement(root, "resources")

    SubElement(resources, "format",
        id="r1",
        frameDuration=f"1/{fps_int}s",
        width="1920",
        height="1080",
    )

    asset_map: dict[str, str] = {}
    aid = 2
    for clip in clips_sequence:
        p = clip["path"]
        if p not in asset_map:
            asset_map[p] = f"r{aid}"
            SubElement(resources, "asset",
                id=f"r{aid}",
                name=Path(p).name,
                src=Path(p).as_uri(),
                start="0s",
                duration=f"999999/{fps_int}s",
                hasVideo="1",
                hasAudio="1",
            )
            aid += 1

    library = SubElement(root, "library")
    event = SubElement(library, "event", name="Video Generator")
    project_el = SubElement(event, "project", name=project_name)
    sequence = SubElement(project_el, "sequence",
        duration=_t(total_frames, fps_int),
        format="r1",
        tcStart="0s",
        tcFormat="NDF",
    )
    spine = SubElement(sequence, "spine")

    for clip in clips_sequence:
        offset_f = int(clip["timeline_start_sec"] * fps_int)
        dur_f = max(1, int(clip["duration_sec"] * fps_int))
        start_f = int(clip["clip_start_sec"] * fps_int)
        speed = clip.get("speed", 1.0)

        clip_el = SubElement(spine, "asset-clip",
            name=Path(clip["path"]).name,
            ref=asset_map[clip["path"]],
            offset=_t(offset_f, fps_int),
            duration=_t(dur_f, fps_int),
            start=_t(start_f, fps_int),
        )

        if speed < 1.0:
            # timeMap: stretch source range [start_f, source_end_f] to fill timeline dur_f.
            source_end_f = start_f + int(clip["duration_sec"] * speed * fps_int)
            time_map = SubElement(clip_el, "timeMap")
            SubElement(time_map, "timept",
                time="0s",
                value=_t(start_f, fps_int),
                interp="linear",
            )
            SubElement(time_map, "timept",
                time=_t(dur_f, fps_int),
                value=_t(source_end_f, fps_int),
                interp="linear",
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in project_name)
    output_path = output_dir / f"{safe_name}.fcpxml"

    with open(str(output_path), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n')
        ElementTree(root).write(f, encoding="unicode", xml_declaration=False)

    return output_path
