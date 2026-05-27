-- src/db/schema.sql
-- Run via: python src/main.py init-db

CREATE TABLE IF NOT EXISTS clips (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    path         TEXT UNIQUE NOT NULL,
    duration_sec REAL NOT NULL,
    fps          REAL NOT NULL,
    width        INTEGER,
    height       INTEGER,
    tags         TEXT NOT NULL DEFAULT '[]',
    energy_score REAL NOT NULL DEFAULT 0.5,
    vibe_label   TEXT NOT NULL DEFAULT 'neutral'
        CHECK(vibe_label IN ('energic', 'sad', 'neutral')),
    added_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vibe   ON clips(vibe_label);
CREATE INDEX IF NOT EXISTS idx_energy ON clips(energy_score);
CREATE INDEX IF NOT EXISTS idx_path   ON clips(path);
