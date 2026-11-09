"""SQLite veritabanı yardımcıları ve şema tanımı."""
import os
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS suites (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    suite_id    INTEGER NOT NULL REFERENCES suites(id) ON DELETE CASCADE,
    test_code   TEXT DEFAULT '',
    title       TEXT NOT NULL,
    module      TEXT DEFAULT '',
    steps       TEXT DEFAULT '',
    expected    TEXT DEFAULT '',
    actual      TEXT DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'not_run',
    bug_link    TEXT DEFAULT '',
    tester      TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_cases_suite  ON cases(suite_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_code   ON cases(test_code);

CREATE TABLE IF NOT EXISTS todos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority    TEXT NOT NULL DEFAULT 'medium',
    due_date    TEXT DEFAULT '',
    done        INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


def get_db():
    if "db" not in g:
        # timeout: birden fazla kullanıcı aynı anda yazarken "database is locked" hatasını önler
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _migrate(conn):
    """Eski veritabanlarına yeni kolonları ekler (veri kaybı olmadan)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(todos)")}
    if "status" not in cols:
        # Kanban durumu: todo / in_progress / review / done  (done kolonu bununla senkron tutulur)
        conn.execute("ALTER TABLE todos ADD COLUMN status TEXT NOT NULL DEFAULT 'todo'")
        conn.execute("UPDATE todos SET status = 'done' WHERE done = 1")
    if "position" not in cols:
        conn.execute("ALTER TABLE todos ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
        conn.execute("UPDATE todos SET position = id")


def init_db(app):
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    with sqlite3.connect(app.config["DATABASE"]) as conn:
        conn.execute("PRAGMA journal_mode=WAL")  # eşzamanlı okuma/yazma için
        conn.executescript(SCHEMA)
        _migrate(conn)
    app.teardown_appcontext(close_db)
