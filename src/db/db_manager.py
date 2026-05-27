import json
import sqlite3
from pathlib import Path


def init_db(db_path: Path) -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(schema_sql)


def insert_clip(
    db_path: Path,
    path: str,
    duration_sec: float,
    fps: float,
    tags: list[str],
    energy_score: float,
    vibe_label: str,
    width: int | None = None,
    height: int | None = None,
) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO clips
                (path, duration_sec, fps, width, height, tags, energy_score, vibe_label)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (path, duration_sec, fps, width, height, json.dumps(tags), energy_score, vibe_label),
        )


def query_clips(
    db_path: Path,
    vibe_label: str,
    min_energy: float = 0.0,
    max_energy: float = 1.0,
    min_duration: float = 0.0,
) -> list[dict]:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT * FROM clips
            WHERE vibe_label = ?
              AND energy_score >= ?
              AND energy_score <= ?
              AND duration_sec >= ?
            """,
            (vibe_label, min_energy, max_energy, min_duration),
        )
        rows = cursor.fetchall()
    return [{**dict(row), "tags": json.loads(row["tags"])} for row in rows]


def clip_exists(db_path: Path, path: str) -> bool:
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("SELECT 1 FROM clips WHERE path = ?", (path,))
        return cursor.fetchone() is not None


def delete_clip(db_path: Path, path: str) -> bool:
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("DELETE FROM clips WHERE path = ?", (path,))
        return cursor.rowcount > 0


def delete_clips_by_anime(db_path: Path, anime_name: str) -> int:
    pattern = f"%{anime_name}%"
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.execute("DELETE FROM clips WHERE path LIKE ?", (pattern,))
        return cursor.rowcount


def get_stats(db_path: Path) -> dict:
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row

        total = conn.execute("SELECT COUNT(*) FROM clips").fetchone()[0]
        total_hours = conn.execute("SELECT SUM(duration_sec) FROM clips").fetchone()[0] or 0.0

        by_vibe = {}
        for row in conn.execute("SELECT vibe_label, COUNT(*) as cnt FROM clips GROUP BY vibe_label"):
            by_vibe[row["vibe_label"]] = row["cnt"]

        low = conn.execute(
            "SELECT COUNT(*) FROM clips WHERE energy_score <= 0.4"
        ).fetchone()[0]
        mid = conn.execute(
            "SELECT COUNT(*) FROM clips WHERE energy_score > 0.4 AND energy_score < 0.6"
        ).fetchone()[0]
        high = conn.execute(
            "SELECT COUNT(*) FROM clips WHERE energy_score >= 0.6"
        ).fetchone()[0]

    return {
        "total": total,
        "by_vibe": by_vibe,
        "energy_histogram": {"low": low, "mid": mid, "high": high},
        "total_hours": total_hours / 3600.0,
    }
