# SRT Format — Reference & Parsing

## Format Spec

Standard `.srt` (SubRip Text) format:

```
1
00:00:12,500 --> 00:00:15,800
First line of lyrics

2
00:00:15,800 --> 00:00:18,200
Second line here

3
00:00:18,200 --> 00:00:21,000
Third line
and this one wraps
```

- Index: integer, 1-based
- Timestamps: `HH:MM:SS,mmm` (hours, minutes, seconds, **comma** milliseconds)
- Text: one or more lines until a blank line
- Blocks separated by blank lines

---

## Parsing Target

Parse into:
```python
[
    {"index": 1, "start_ms": 12500, "end_ms": 15800, "text": "First line of lyrics"},
    {"index": 2, "start_ms": 15800, "end_ms": 18200, "text": "Second line here"},
    {"index": 3, "start_ms": 18200, "end_ms": 21000, "text": "Third line\nand this one wraps"},
]
```

---

## Parser Implementation

Use `pysrt` (listed in requirements) — it handles edge cases cleanly:

```python
import pysrt

def parse_srt(path: str) -> list[dict]:
    subs = pysrt.open(path, encoding="utf-8")
    blocks = []
    for sub in subs:
        blocks.append({
            "index": sub.index,
            "start_ms": sub.start.ordinal,   # .ordinal = total milliseconds
            "end_ms": sub.end.ordinal,
            "text": sub.text.strip(),
        })
    return blocks
```

If `pysrt` is unavailable, the format is simple enough to parse with regex:

```python
import re

def parse_srt_manual(path: str) -> list[dict]:
    text = open(path, encoding="utf-8-sig").read()
    pattern = re.compile(
        r"(\d+)\n"
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n"
        r"([\s\S]*?)(?=\n\n|\Z)",
        re.MULTILINE
    )

    def ts_to_ms(ts: str) -> int:
        h, m, rest = ts.split(":")
        s, ms = rest.split(",")
        return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)

    return [
        {
            "index": int(m.group(1)),
            "start_ms": ts_to_ms(m.group(2)),
            "end_ms": ts_to_ms(m.group(3)),
            "text": m.group(4).strip(),
        }
        for m in pattern.finditer(text)
    ]
```

---

## Notes

- Subtitle Edit exports UTF-8 with BOM by default — use `encoding="utf-8-sig"` to strip the BOM.
- Some editors use `.` instead of `,` as the millisecond separator — handle both.
- Empty text blocks (blank lyric gaps) should be skipped silently downstream.
- The `.srt` file is the **source of truth** for timing. Do not modify timestamps programmatically except for optional beat-snapping.
