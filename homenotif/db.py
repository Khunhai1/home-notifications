"""Postgres storage. The schema itself lives in migrations/ (see migrate.py)."""
from dataclasses import asdict

import psycopg
from psycopg.rows import dict_row
from psycopg.types.numeric import FloatLoader

from .matching import fingerprint
from .models import Listing

STATUSES = ("new", "favorite", "applied", "hidden")
SEARCH_FIELDS = ("min_rooms", "max_rooms", "min_rent", "max_rent", "min_area", "exclude_keywords")


def connect(url):
    conn = psycopg.connect(url, row_factory=dict_row, autocommit=True)
    conn.adapters.register_loader("numeric", FloatLoader)
    return conn


def load_settings(conn):
    """The search settings and zones, in the shape config.py uses."""
    s = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    zones = conn.execute(
        "SELECT z.name, coalesce(array_agg(n.npa ORDER BY n.npa) FILTER (WHERE n.npa IS NOT NULL), '{}') AS npa "
        "FROM zones z LEFT JOIN zone_npas n ON n.zone_id = z.id GROUP BY z.id ORDER BY z.position"
    ).fetchall()
    return {
        "search": {k: s[k] for k in SEARCH_FIELDS},
        "zones": [dict(z) for z in zones],
        "anibis_urls": s["anibis_urls"],
        "notify_to": s["notify_to"],
    }


def save_settings(conn, search, zones, anibis_urls, notify_to):
    with conn.transaction():
        conn.execute(
            "UPDATE settings SET min_rooms = %s, max_rooms = %s, min_rent = %s, max_rent = %s, min_area = %s, "
            "exclude_keywords = %s, anibis_urls = %s, notify_to = %s, updated_at = now() WHERE id = 1",
            (*(search[k] for k in SEARCH_FIELDS), anibis_urls, notify_to))
        conn.execute("DELETE FROM zones")
        for position, zone in enumerate(zones, 1):
            zone_id = conn.execute("INSERT INTO zones (position, name) VALUES (%s, %s) RETURNING id",
                                   (position, zone["name"])).fetchone()["id"]
            for code in zone.get("npa", []):
                conn.execute("INSERT INTO zone_npas (zone_id, npa) VALUES (%s, %s)", (zone_id, code))


def _listing(row):
    return Listing(**{k: row[k] for k in Listing.__dataclass_fields__})


def rematch(conn, evaluate):
    """Re-apply the current criteria to every stored listing, so settings changes take
    effect immediately. Old listings that start matching are not announced."""
    fields = ", ".join(Listing.__dataclass_fields__)
    changes = []
    for row in conn.execute(f"SELECT id, matched, zone, {fields} FROM listings").fetchall():
        row["published_at"] = row["published_at"].isoformat() if row["published_at"] else ""
        matched, zone = evaluate(_listing(row))
        if (row["matched"], row["zone"]) != (matched, zone):
            changes.append((matched, zone, row["id"]))
    if changes:
        with conn.transaction(), conn.cursor() as cur:
            cur.executemany(
                "UPDATE listings SET matched = %s, zone = %s, notified_at = coalesce(notified_at, now()) WHERE id = %s",
                changes)
    return len(changes)


def get_state(conn, key):
    row = conn.execute("SELECT value FROM state WHERE key = %s", (key,)).fetchone()
    return row["value"] if row else None


def set_state(conn, key, value):
    conn.execute("INSERT INTO state (key, value) VALUES (%s, %s) "
                 "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = now()", (key, value))


def known_ids(conn, source):
    return {r["source_id"] for r in conn.execute("SELECT source_id FROM listings WHERE source = %s", (source,))}


def over_budget(conn, source, max_rent):
    """source_id -> stored rent, for listings that don't match and cost more than max_rent."""
    rows = conn.execute("SELECT source_id, rent FROM listings WHERE source = %s AND NOT matched AND rent > %s",
                        (source, max_rent))
    return {r["source_id"]: r["rent"] for r in rows}


def update_rent(conn, l: Listing, matched: bool, zone):
    """Store a new rent. A listing that starts matching because it got cheaper is news: it is announced."""
    conn.execute(
        "UPDATE listings SET rent = %s, matched = %s, zone = %s, "
        "notified_at = CASE WHEN %s AND NOT matched THEN NULL ELSE notified_at END "
        "WHERE source = %s AND source_id = %s",
        (l.rent, matched, zone, matched, l.source, l.source_id))


def insert(conn, l: Listing, matched: bool, zone, silent: bool, status="new") -> bool:
    """Store a listing. Returns False if it was already known. `silent` stores it
    as already notified (used for the first import of a source)."""
    fp = fingerprint(l)
    dup = conn.execute(
        "SELECT id FROM listings WHERE fingerprint = %s AND duplicate_of IS NULL "
        "AND NOT (source = %s AND source_id = %s) ORDER BY id LIMIT 1", (fp, l.source, l.source_id)
    ).fetchone() if fp else None
    row = asdict(l) | {
        "published_at": l.published_at or None, "fingerprint": fp, "duplicate_of": dup["id"] if dup else None,
        "matched": matched, "zone": zone, "status": status,
    }
    columns = ", ".join(row)
    values = ", ".join(f"%({k})s" for k in row)
    inserted = conn.execute(
        f"INSERT INTO listings ({columns}, notified_at) VALUES ({values}, CASE WHEN %(silent)s THEN now() END) "
        "ON CONFLICT (source, source_id) DO NOTHING RETURNING id", row | {"silent": silent}
    ).fetchone()
    return inserted is not None


def pending(conn):
    """Matched listings nobody has been told about yet."""
    return conn.execute(
        "SELECT * FROM listings WHERE matched AND notified_at IS NULL AND duplicate_of IS NULL "
        "ORDER BY zone IS NULL, zone, id"
    ).fetchall()


def mark_notified(conn, ids):
    with conn.transaction():
        conn.execute("UPDATE listings SET notified_at = now() WHERE id = ANY(%s)", (list(ids),))
        # duplicates never get their own notification
        conn.execute("UPDATE listings SET notified_at = now() WHERE notified_at IS NULL AND duplicate_of IS NOT NULL")


def since(conn, when):
    return conn.execute(
        "SELECT * FROM listings WHERE matched AND duplicate_of IS NULL AND status != 'hidden' "
        "AND first_seen >= %s ORDER BY zone IS NULL, zone, id DESC", (when,)
    ).fetchall()
