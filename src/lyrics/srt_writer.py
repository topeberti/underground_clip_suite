from pathlib import Path


def _ms_to_ts(ms: int) -> str:
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(entries: list[dict], out_path: Path) -> None:
    lines = []
    for e in entries:
        lines.append(str(e["index"]))
        lines.append(f"{_ms_to_ts(e['start_ms'])} --> {_ms_to_ts(e['end_ms'])}")
        lines.append(e["text"])
        lines.append("")
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
