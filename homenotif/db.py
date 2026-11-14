import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .matching import fingerprint
from .models import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    rent REAL, rooms REAL, area REAL,
    zipcode INTEGER, city TEXT, street TEXT,
    lat REAL, lon REAL,
    image_url TEXT,
    published_at TEXT,
    first_seen TEXT NOT NULL,
    fingerprint TEXT,
    duplicate_of INTEGER REFERENCES listings(id),
    matched INTEGER NOT NULL,
    notified_at TEXT,
    status TEXT NOT NULL DEFAULT 'new',   -- new, favorite, applied, hidden
    UNIQUE (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_listings_fingerprint ON listings(fingerprint);
"""

STATUSES = ("new", "favorite", "applied", "hidden")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def known_ids(conn, source):
    return {r[0] for r in conn.execute("SELECT source_id FROM listings WHERE source = ?", (source,))}


def insert(conn, l: Listing, matched: bool, silent: bool) -> bool:
    """Store a listing. Returns False if it was already known. `silent` stores it
    as already notified (used for the first import of a source)."""
    if conn.execute("SELECT 1 FROM listings WHERE source = ? AND source_id = ?", (l.source, l.source_id)).fetchone():
        return False
    fp = fingerprint(l)
    dup = conn.execute(
        "SELECT id FROM listings WHERE fingerprint = ? AND duplicate_of IS NULL ORDER BY id LIMIT 1", (fp,)
    ).fetchone() if fp else None
    row = asdict(l) | {
        "first_seen": now(), "fingerprint": fp, "duplicate_of": dup["id"] if dup else None,
        "matched": int(matched), "notified_at": now() if silent else None,
    }
    conn.execute(f"INSERT INTO listings ({', '.join(row)}) VALUES ({', '.join(':' + k for k in row)})", row)
    conn.commit()
    return True


def pending(conn):
    """Matched listings nobody has been told about yet."""
    return conn.execute(
        "SELECT * FROM listings WHERE matched = 1 AND notified_at IS NULL AND duplicate_of IS NULL ORDER BY id"
    ).fetchall()


def mark_notified(conn, ids):
    conn.executemany("UPDATE listings SET notified_at = ? WHERE id = ?", [(now(), i) for i in ids])
    # duplicates never get their own notification
    conn.execute("UPDATE listings SET notified_at = ? WHERE notified_at IS NULL AND duplicate_of IS NOT NULL", (now(),))
    conn.commit()


def since(conn, iso):
    return conn.execute(
        "SELECT * FROM listings WHERE matched = 1 AND duplicate_of IS NULL AND status != 'hidden' "
        "AND first_seen >= ? ORDER BY id DESC", (iso,)
    ).fetchall()


def browse(conn, status="", source="", include_unmatched=False, limit=300):
    sql = "SELECT * FROM listings WHERE duplicate_of IS NULL"
    args = []
    if status:
        sql += " AND status = ?"
        args.append(status)
    else:
        sql += " AND status != 'hidden'"
    if source:
        sql += " AND source = ?"
        args.append(source)
    if not include_unmatched:
        sql += " AND matched = 1"
    rows = conn.execute(
        sql + " ORDER BY COALESCE(NULLIF(published_at, ''), first_seen) DESC LIMIT ?", (*args, limit)
    ).fetchall()
    dups = {}
    for d in conn.execute("SELECT duplicate_of, source, url FROM listings WHERE duplicate_of IS NOT NULL"):
        dups.setdefault(d["duplicate_of"], []).append(d)
    return [dict(r) | {"also_on": dups.get(r["id"], [])} for r in rows]


def sources(conn):
    return [r[0] for r in conn.execute("SELECT DISTINCT source FROM listings ORDER BY source")]


def set_status(conn, listing_id, status):
    if status in STATUSES:
        conn.execute("UPDATE listings SET status = ? WHERE id = ?", (status, listing_id))
        conn.commit()
