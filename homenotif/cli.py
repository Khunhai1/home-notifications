import argparse
import logging
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from . import config, db, notify
from .matching import matches
from .sources import anibis, email_alerts, flatfox

log = logging.getLogger("homenotif")

SOURCES = {"flatfox": flatfox.fetch, "anibis": anibis.fetch, "email_alerts": email_alerts.fetch}


def fetch_all(cfg, conn):
    for name, fetch in SOURCES.items():
        if not cfg[name]["enabled"]:
            continue
        known = db.known_ids(conn, name)
        # First import of a site: store everything, but don't send hundreds of old listings by email.
        silent = name != "email_alerts" and not known
        new = matched = 0
        try:
            for listing in fetch(cfg, known):
                ok = matches(listing, cfg["search"])
                if db.insert(conn, listing, ok, silent):
                    new += 1
                    matched += ok
        except Exception:
            log.exception("%s failed", name)
            continue
        log.info("%s: %d new listings, %d match your criteria%s", name, new, matched,
                 " (first import, no notification)" if silent and new else "")


def notify_pending(cfg, conn):
    rows = db.pending(conn)
    if rows:
        notify.send(cfg, rows, f"{len(rows)} new flat{'s' if len(rows) > 1 else ''} matching your search")
    db.mark_notified(conn, [r["id"] for r in rows])


def digest(cfg, conn):
    day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    rows = db.since(conn, day_ago)
    if rows:
        notify.send(cfg, rows, f"Daily digest: {len(rows)} flats from the last 24 hours")
    else:
        log.info("digest: nothing new in the last 24 hours")


def serve(cfg, conn):
    import uvicorn

    from .web import create_app

    url = urlsplit(cfg["app"]["dashboard_url"])
    uvicorn.run(create_app(cfg, conn), host=url.hostname or "127.0.0.1", port=url.port or 8000, log_level="warning")


def poll_forever(cfg):
    conn = db.connect(cfg["app"]["db_path"])  # own connection for this thread
    while True:
        try:
            fetch_all(cfg, conn)
            notify_pending(cfg, conn)
        except Exception:
            log.exception("poll failed")
        time.sleep(cfg["app"]["poll_minutes"] * 60)


def main():
    parser = argparse.ArgumentParser(prog="homenotif", description="Apartment alerts for Swiss listing sites")
    parser.add_argument("command", choices=["fetch", "digest", "serve", "run"],
                        help="fetch: check all sources once and notify | digest: email the last 24h | "
                             "serve: dashboard only | run: dashboard + check every poll_minutes")
    parser.add_argument("--config", default="config.toml")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    cfg = config.load(args.config)
    conn = db.connect(cfg["app"]["db_path"])

    if args.command == "fetch":
        fetch_all(cfg, conn)
        notify_pending(cfg, conn)
    elif args.command == "digest":
        digest(cfg, conn)
    elif args.command == "serve":
        print(f"Dashboard: {cfg['app']['dashboard_url']}")
        serve(cfg, conn)
    else:
        threading.Thread(target=poll_forever, args=(cfg,), daemon=True).start()
        print(f"Dashboard: {cfg['app']['dashboard_url']} - checking every {cfg['app']['poll_minutes']} min")
        serve(cfg, conn)
