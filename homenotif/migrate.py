"""Applies the SQL files in migrations/ that haven't run yet, in name order."""
import logging
from pathlib import Path

log = logging.getLogger(__name__)

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"
LOCK_ID = 4242  # any constant: makes concurrent runs wait for each other


def migrate(conn):
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations "
                     "(version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        done = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}
        applied = []
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.stem in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied.append(path.stem)
    log.info("migrations: %s", ", ".join(applied) if applied else "up to date")
    return applied
