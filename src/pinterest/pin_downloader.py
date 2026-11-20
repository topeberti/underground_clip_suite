"""
Pin downloader — saves every image of a Pinterest pin or board at full resolution.

Accepts a pin URL (pinterest.com/pin/<id>/, any country domain, slugged URLs), a board URL
(pinterest.com/<user>/<board>/, optionally /<section>/), a pin.it short link to either, or
a bare pin id. Data comes from Pinterest's public resource endpoints (the ones its own web
app calls; no login needed for public pins and boards).

A pin can hold several images: carousel slots, or the pages of an idea (story) pin.
Single-image pins fall back to images["orig"]. Video blocks are skipped. Board feeds carry
the same fields, so a board costs one request per 25 pins. A whole board also includes the
pins in its sections. Files are named after Pinterest's image hash (like the existing media
folders), so downloading again skips images that are already there.
"""

import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from rich.console import Console

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
RESOURCE_URL = "https://www.pinterest.com/resource/{}/get/"
PIN_ID_RE = re.compile(r"/pin/(?:[^/?#]*--)?(\d+)")
# First path segments that are Pinterest pages, not usernames.
NOT_USERS = {"pin", "search", "ideas", "today", "explore", "resource", "settings", "business",
             "categories", "topics", "news_hub", "videos", "_", "shopping"}
PAGE_SIZE = 25
TIMEOUT = 20


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _resource(session: requests.Session, name: str, options: dict, handler: str) -> dict:
    """One call to a Pinterest resource endpoint; returns resource_response."""
    params = {"data": json.dumps({"options": options})}
    # Without this header the endpoints answer 403 "Invalid Resource Request".
    resp = session.get(RESOURCE_URL.format(name), params=params,
                       headers={"X-Pinterest-PWS-Handler": handler}, timeout=TIMEOUT)
    if resp.status_code == 404:
        raise RuntimeError("Not found on Pinterest (deleted, private or a wrong link).")
    resp.raise_for_status()
    return resp.json().get("resource_response", {})


def _expand(url: str, session: requests.Session) -> str:
    """Follow a pin.it short link to the pinterest.com URL it points to."""
    if not url.startswith("http"):
        url = "https://" + url
    resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    for r in [*resp.history, resp]:
        for candidate in (r.headers.get("Location", ""), r.url):
            if "pinterest." in urlparse(candidate).netloc and "url_shortener" not in candidate:
                return candidate
    raise ValueError(f"Short link didn't lead to a pin or board: {url}")


def parse_link(url: str, session: requests.Session | None = None) -> tuple:
    """("pin", pin_id) or ("board", username, board_slug, section_slug_or_None)."""
    url = url.strip()
    if url.isdigit():
        return ("pin", url)
    if "pin.it/" in url:
        url = _expand(url, session or _session())
    m = PIN_ID_RE.search(url)
    if m:
        return ("pin", m.group(1))
    parsed = urlparse(url if "://" in url else "https://" + url)
    parts = [unquote(p) for p in parsed.path.split("/") if p]
    if "pinterest." in parsed.netloc and len(parts) in (2, 3) and parts[0] not in NOT_USERS:
        return ("board", parts[0], parts[1], parts[2] if len(parts) == 3 else None)
    raise ValueError(f"Not a Pinterest pin or board link: {url}")


def fetch_pin(pin_id: str, session: requests.Session | None = None) -> dict:
    """The pin's full ("detailed") data dict."""
    data = _resource(session or _session(), "PinResource",
                     {"id": pin_id, "field_set_key": "detailed"}, "www/pin/[id].js").get("data")
    if not data:
        raise RuntimeError(f"Pinterest returned no data for pin {pin_id}.")
    return data


def _feed(session: requests.Session, name: str, options: dict, handler: str):
    """Yield every pin of a paginated feed resource."""
    bookmark = None
    while True:
        opts = {**options, "page_size": PAGE_SIZE, **({"bookmarks": [bookmark]} if bookmark else {})}
        resp = _resource(session, name, opts, handler)
        for item in resp.get("data") or []:
            if item.get("type") == "pin":   # feeds also mix in "story" recommendation modules
                yield item
        bookmark = resp.get("bookmark")
        if not bookmark or bookmark == "-end-" or not resp.get("data"):
            return


def board_pins(username: str, slug: str, section: str | None = None,
               session: requests.Session | None = None, console: Console | None = None) -> tuple[str, list[dict]]:
    """(board name, pins) of a board, or of one of its sections. A whole board includes the
    pins in its sections."""
    session = session or _session()
    handler = "www/[username]/[slug].js"
    board = _resource(session, "BoardResource",
                      {"username": username, "slug": slug, "field_set_key": "detailed"}, handler).get("data")
    if not board:
        raise RuntimeError(f"Board {username}/{slug} not found.")
    name = board.get("name") or slug

    sections = _sections(session, board["id"], handler) if section or board.get("section_count") else []
    if section:
        match = [s for s in sections if section in (s.get("slug"), s.get("title"))]
        if not match:
            raise RuntimeError(f"Section '{section}' not found in board '{name}'.")
        sections, name, feeds = match, f"{name} / {match[0].get('title', section)}", []
    else:
        feeds = [("BoardFeedResource", {"board_id": board["id"]})]
    feeds += [("BoardSectionPinsResource", {"section_id": s["id"]}) for s in sections]

    pins = {}
    for resource, options in feeds:
        for pin in _feed(session, resource, options, handler):
            pins.setdefault(pin["id"], pin)
        if console:
            console.print(f"  ...{len(pins)} pin(s) found")
    return name, list(pins.values())


def _sections(session: requests.Session, board_id: str, handler: str) -> list[dict]:
    out, bookmark = [], None
    while True:
        opts = {"board_id": board_id, **({"bookmarks": [bookmark]} if bookmark else {})}
        resp = _resource(session, "BoardSectionsResource", opts, handler)
        out += resp.get("data") or []
        bookmark = resp.get("bookmark")
        if not bookmark or bookmark == "-end-" or not resp.get("data"):
            return out


def _variants(images: dict | None) -> list[str]:
    """URLs of a Pinterest images dict ({"orig": {url, width}, "736x": ...}), best first.
    An original's URL sometimes has the wrong extension (idea pin pages list .jpg for a
    .png original, which answers 403), so the other extension is tried next."""
    if not images:
        return []
    sized = [v for v in images.values() if isinstance(v, dict) and v.get("url")]
    sized.sort(key=lambda v: ("/originals/" not in v["url"], -(v.get("width") or 0)))
    urls = []
    for v in sized:
        urls.append(v["url"])
        if "/originals/" in v["url"]:
            base, _, ext = v["url"].rpartition(".")
            urls.append(f"{base}.{'png' if ext.lower() in ('jpg', 'jpeg') else 'jpg'}")
    return list(dict.fromkeys(urls))


def _hash(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?")[0].rsplit(".", 1)[0]


def image_urls(pin: dict) -> list[list[str]]:
    """The pin's images in display order: for each, its candidate URLs, best first."""
    groups: dict[str, list[str]] = {}

    def add(images, new_ok=True):
        urls = _variants(images)
        if not urls:
            return
        key = _hash(urls[0])
        if key in groups:
            groups[key] += [u for u in urls if u not in groups[key]]
        elif new_ok:
            groups[key] = urls

    for slot in (pin.get("carousel_data") or {}).get("carousel_slots") or []:
        add(slot.get("images"))
    for page in (pin.get("story_pin_data") or {}).get("pages") or []:
        for block in page.get("blocks") or []:
            if block.get("type") == "story_pin_image_block":
                add((block.get("image") or {}).get("images"))
    # The pin's own image: extra candidates for a page it duplicates, or the only image.
    add(pin.get("images"), new_ok=not groups and not pin.get("videos"))
    return list(groups.values())


def _save(images: list[list[str]], out_dir: Path, session: requests.Session, console: Console, on_progress) -> list[Path]:
    """Download each image (first candidate URL that works) into out_dir, skipping images
    already there under any extension. Returns all their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved, new, failed = [], 0, 0
    for i, candidates in enumerate(images, 1):
        tag = f"  [{i}/{len(images)}]"
        name = _hash(candidates[0])
        existing = [f for f in out_dir.glob(f"{name}.*") if f.suffix != ".part"]
        if existing:
            console.print(f"{tag} {existing[0].name} already there, skipped")
            saved.append(existing[0])
        else:
            for url in candidates:
                try:
                    resp = session.get(url, timeout=TIMEOUT)
                except requests.RequestException:
                    continue
                if resp.ok and resp.content:
                    break
            else:
                failed += 1
                console.print(f"{tag} {name} failed: Pinterest refused every size of this image")
                resp = None
            if resp is not None:
                dest = out_dir / url.rsplit("/", 1)[-1].split("?")[0]
                tmp = dest.with_name(dest.name + ".part")
                tmp.write_bytes(resp.content)
                tmp.replace(dest)
                new += 1
                note = ("" if url == candidates[0] else
                        f", as .{url.rsplit('.', 1)[-1]}" if "/originals/" in url else f", {url.split('/')[3]} size")
                console.print(f"{tag} {dest.name} ({len(resp.content) // 1024} KB{note})")
                saved.append(dest)
        if on_progress:
            on_progress(i, len(images))
    console.print(f"[green]{new} new image(s), {len(saved) - new} already there"
                  f"{f', {failed} failed' if failed else ''}, in {out_dir}[/green]")
    return saved


def download(url: str, out_dir: Path, console: Console | None = None, on_progress=None) -> list[Path]:
    """Download every image of the pin or board at `url` into out_dir. Returns the image
    paths (including ones that were already there)."""
    console = console or Console()
    session = _session()
    link = parse_link(url, session)
    if link[0] == "pin":
        pin = fetch_pin(link[1], session)
        images = image_urls(pin)
        title = (pin.get("title") or pin.get("grid_title") or "").strip()
        console.print(f"Pin {link[1]}{f' - {title}' if title else ''}: {len(images)} image(s)")
    else:
        console.print(f"Board {link[1]}/{link[2]}{f'/{link[3]}' if link[3] else ''}: reading pins...")
        name, pins = board_pins(*link[1:], session=session, console=console)
        images = list({_hash(c[0]): c for pin in pins for c in image_urls(pin)}.values())
        console.print(f"Board '{name}': {len(pins)} pin(s), {len(images)} image(s)")
    if not images:
        console.print("[yellow]No images found (video pins are not downloaded).[/yellow]")
        return []
    return _save(images, out_dir, session, console, on_progress)
