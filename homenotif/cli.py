import argparse
import logging
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

from . import config, db, notify, npa
from .matching import evaluate
from .migrate import migrate
from .models import Listing
from .sources import anibis, email_alerts, flatfox

log = logging.getLogger("homenotif")

SOURCES = {"flatfox": flatfox.fetch, "anibis": anibis.fetch, "email_alerts": email_alerts.fetch}


def fetch_all(cfg, conn):
    # Listings already online in a zone you just added aren't news: import them without notifying.
    area = ",".join(map(str, sorted(config.all_npas(cfg))))
    for name, fetch in SOURCES.items():
        if not cfg[name]["enabled"]:
            continue
        known = db.known_ids(conn, name)
        new_area = db.get_state(conn, f"area:{name}") != area
        # First import of a site: store everything, but don't send hundreds of old listings by email.
        silent = name != "email_alerts" and (not known or new_area)
        new = matched = 0
        try:
            for listing in fetch(cfg, known):
                ok, zone = evaluate(listing, cfg)
                if db.insert(conn, listing, ok, zone, silent):
                    new += 1
                    matched += ok
        except Exception:
            log.exception("%s failed", name)
            continue
        db.set_state(conn, f"area:{name}", area)
        log.info("%s: %d new listings, %d match your criteria%s", name, new, matched,
                 " (first import for these zones, no notification)" if silent and new else "")
    db.set_state(conn, "last_fetch", datetime.now(timezone.utc).isoformat(timespec="seconds"))


def notify_pending(cfg, conn):
    rows = db.pending(conn)
    if rows:
        notify.send(cfg, rows, f"{len(rows)} new flat{'s' if len(rows) > 1 else ''} matching your search")
    db.mark_notified(conn, [r["id"] for r in rows])


def digest(cfg, conn):
    rows = db.since(conn, datetime.now(timezone.utc) - timedelta(days=1))
    if rows:
        notify.send(cfg, rows, f"Daily digest: {len(rows)} flats from the last 24 hours")
    else:
        log.info("digest: nothing new in the last 24 hours")


def show_zones(cfg):
    if not cfg["zones"]:
        print("No zones configured: listings from anywhere match.")
    for number, zone in enumerate(cfg["zones"], 1):
        print(f"\nZone {number}: {zone['name']}")
        for code in zone.get("npa", []):
            print(f"  {code}  {', '.join(npa.localities(code))}")


def import_local(conn, toml_path, sqlite_path):
    """One-time copy of an old local setup (config.toml + SQLite database) into Postgres."""
    if toml_path:
        s = config.load_toml(toml_path)
        db.save_settings(conn, s["search"], s["zones"], s["anibis_urls"], s["notify_to"])
        log.info("settings: imported %d zones from %s", len(s["zones"]), toml_path)
    if sqlite_path:
        old = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        old.row_factory = sqlite3.Row
        rows = old.execute("SELECT * FROM listings ORDER BY id").fetchall()
        copied = 0
        text_fields = ("description", "city", "street", "image_url", "published_at")
        for row in rows:
            listing = Listing(**{k: "" if row[k] is None and k in text_fields else row[k]
                                 for k in Listing.__dataclass_fields__})
            # everything already known locally counts as notified
            copied += db.insert(conn, listing, bool(row["matched"]), None, silent=True, status=row["status"])
        with conn.transaction(), conn.cursor() as cur:  # keep the original dates, so the digest stays accurate
            cur.executemany("UPDATE listings SET first_seen = %s WHERE source = %s AND source_id = %s",
                            [(r["first_seen"], r["source"], r["source_id"]) for r in rows])
        log.info("listings: copied %d of %d from %s", copied, len(rows), sqlite_path)


def main():
    parser = argparse.ArgumentParser(prog="homenotif", description="Apartment alerts for Swiss listing sites")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="apply pending database migrations")
    sub.add_parser("fetch", help="check all sources once and notify about new matches")
    sub.add_parser("digest", help="email everything matched in the last 24 hours")
    sub.add_parser("zones", help="list the zones with the localities of each NPA")
    imp = sub.add_parser("import-local", help="copy settings and listings from an old local setup")
    imp.add_argument("--config", help="old config.toml")
    imp.add_argument("--sqlite", help="old data/listings.db")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    with db.connect(config.database_url()) as conn:
        if args.command == "migrate":
            migrate(conn)
            return
        if args.command == "import-local":
            import_local(conn, args.config, args.sqlite)
        cfg = config.load(conn)
        changed = db.rematch(conn, lambda listing: evaluate(listing, cfg))
        if changed:
            log.info("re-checked listings against the current settings: %d changed", changed)
        if args.command == "zones":
            show_zones(cfg)
        elif args.command == "fetch":
            fetch_all(cfg, conn)
            notify_pending(cfg, conn)
        elif args.command == "digest":
            digest(cfg, conn)
