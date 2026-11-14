"""Configuration: infrastructure from environment variables, search settings from the database."""
import os
import tomllib
from pathlib import Path

from . import db, npa

try:
    from dotenv import load_dotenv
except ImportError:  # optional: only used for local runs
    load_dotenv = None


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def _flag(name, default=True):
    return _env(name, "1" if default else "0").lower() not in ("0", "false", "no", "off", "")


def check_zones(zones):
    seen = {}
    for number, zone in enumerate(zones, 1):
        zone.setdefault("name", f"Zone {number}")
        for code in zone.get("npa", []):
            if code not in npa.table():
                raise SystemExit(f"zone '{zone['name']}' has unknown NPA {code}")
            if code in seen:
                raise SystemExit(f"NPA {code} is in both '{seen[code]}' and '{zone['name']}'")
            seen[code] = zone["name"]


def database_url():
    if load_dotenv:
        load_dotenv()
    url = _env("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set (see .env.example)")
    return url


def load(conn):
    s = db.load_settings(conn)
    check_zones(s["zones"])
    smtp_user = _env("HOMENOTIF_SMTP_USER")
    imap_user = _env("HOMENOTIF_IMAP_USER")
    return {
        "search": s["search"],
        "zones": s["zones"],
        "flatfox": {"enabled": _flag("HOMENOTIF_FLATFOX"), "categories": ["APARTMENT"]},
        "anibis": {"enabled": _flag("HOMENOTIF_ANIBIS") and bool(s["anibis_urls"]),
                   "search_urls": s["anibis_urls"], "max_pages": 2},
        "email_alerts": {"enabled": bool(imap_user) and _flag("HOMENOTIF_EMAIL_ALERTS"),
                         "host": _env("HOMENOTIF_IMAP_HOST", "imap.gmail.com"), "user": imap_user,
                         "password_env": "HOMENOTIF_IMAP_PASSWORD", "folder": _env("HOMENOTIF_IMAP_FOLDER", "INBOX")},
        "notify": {"enabled": bool(smtp_user and _env("HOMENOTIF_SMTP_PASSWORD") and s["notify_to"]),
                   "smtp_host": _env("HOMENOTIF_SMTP_HOST", "smtp.gmail.com"),
                   "smtp_port": int(_env("HOMENOTIF_SMTP_PORT", "587")), "user": smtp_user,
                   "password_env": "HOMENOTIF_SMTP_PASSWORD", "from": _env("HOMENOTIF_SMTP_FROM", smtp_user),
                   "to": s["notify_to"]},
        "app": {"dashboard_url": _env("HOMENOTIF_DASHBOARD_URL", "https://home-notifications.pages.dev")},
    }


def load_toml(path):
    """Settings from an old config.toml, for `import-local`."""
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"{path} not found")
    user = tomllib.loads(p.read_text(encoding="utf-8"))
    search = {"min_rooms": 0, "max_rooms": 0, "min_rent": 0, "max_rent": 0, "min_area": 0, "exclude_keywords": []}
    search.update({k: v for k, v in user.get("search", {}).items() if k in search})
    zones = user.get("zones", [])
    check_zones(zones)
    return {
        "search": search,
        "zones": zones,
        "anibis_urls": user.get("anibis", {}).get("search_urls", []),
        "notify_to": user.get("notify", {}).get("to", ""),
    }


def all_npas(cfg):
    return [code for zone in cfg["zones"] for code in zone.get("npa", [])]
