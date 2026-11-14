import copy
import tomllib
from pathlib import Path

DEFAULTS = {
    "search": {
        "min_rooms": 0, "max_rooms": 0, "min_rent": 0, "max_rent": 0, "min_area": 0,
        "center": [], "radius_km": 0, "zipcodes": [], "exclude_keywords": [],
    },
    "flatfox": {"enabled": True, "categories": ["APARTMENT"]},
    "anibis": {"enabled": False, "search_urls": [], "max_pages": 2},
    "email_alerts": {"enabled": False, "host": "", "user": "", "password_env": "HOMENOTIF_IMAP_PASSWORD", "folder": "INBOX"},
    "notify": {"enabled": False, "smtp_host": "", "smtp_port": 587, "user": "",
               "password_env": "HOMENOTIF_SMTP_PASSWORD", "from": "", "to": ""},
    "app": {"db_path": "data/listings.db", "poll_minutes": 15, "dashboard_url": "http://127.0.0.1:8000"},
}


def load(path="config.toml"):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"{path} not found - copy config.example.toml to {path} and edit it.")
    user = tomllib.loads(p.read_text(encoding="utf-8"))
    cfg = copy.deepcopy(DEFAULTS)
    for section, values in user.items():
        cfg.setdefault(section, {}).update(values)
    return cfg
