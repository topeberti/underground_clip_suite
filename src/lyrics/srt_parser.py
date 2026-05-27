import re
from pathlib import Path


def _ts_to_ms(ts: str) -> int:
    ts = ts.replace(".", ",")
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3_600_000 + int(m) * 60_000 + int(s) * 1_000 + int(ms)


def _parse_srt_fallback(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    pattern = re.compile(
        r"(\d+)\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+([\s\S]*?)(?=\n\n|\Z)",
        re.MULTILINE,
    )
    blocks = []
    for m in pattern.finditer(text):
        raw_text = m.group(4).strip()
        if not raw_text:
            continue
        blocks.append({
            "index": int(m.group(1)),
            "start_ms": _ts_to_ms(m.group(2)),
            "end_ms": _ts_to_ms(m.group(3)),
            "text": raw_text,
        })
    return blocks


def parse_srt(path: Path) -> list[dict]:
    try:
        import pysrt
        subs = pysrt.open(str(path), encoding="utf-8-sig")
        blocks = []
        for sub in subs:
            raw_text = sub.text.strip()
            if not raw_text:
                continue
            blocks.append({
                "index": sub.index,
                "start_ms": sub.start.ordinal,
                "end_ms": sub.end.ordinal,
                "text": raw_text,
            })
        return blocks
    except ImportError:
        return _parse_srt_fallback(path)
