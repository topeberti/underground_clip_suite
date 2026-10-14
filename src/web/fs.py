"""
src/web/fs.py — Read-only directory listing for the file-picker modal.
"""

import os
import string
from pathlib import Path


def _drives() -> list[dict]:
    return [
        {"name": f"{d}:\\", "path": f"{d}:\\", "is_dir": True}
        for d in string.ascii_uppercase
        if os.path.exists(f"{d}:\\")
    ]


def list_dir(path: str | None, exts: set[str] | None = None) -> dict:
    """List sub-directories and (optionally extension-filtered) files of `path`.

    An empty path returns the drive roots (Windows) or "/" contents elsewhere.
    """
    if not path:
        if os.name == "nt":
            return {"path": "", "parent": None, "entries": _drives()}
        path = "/"

    p = Path(path).expanduser()
    if not p.is_dir():
        raise FileNotFoundError(f"Not a directory: {path}")

    entries = []
    try:
        children = sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower()))
    except PermissionError as exc:
        raise PermissionError(f"Access denied: {path}") from exc

    for child in children:
        try:
            is_dir = child.is_dir()
        except OSError:
            continue
        if is_dir:
            entries.append({"name": child.name, "path": str(child), "is_dir": True})
        elif exts is None or child.suffix.lower() in exts:
            entries.append({"name": child.name, "path": str(child), "is_dir": False})

    parent = str(p.parent) if p.parent != p else ("" if os.name == "nt" else None)
    return {"path": str(p), "parent": parent, "entries": entries}
