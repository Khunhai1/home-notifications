import copy
import tomllib
from pathlib import Path

from . import npa

DEFAULTS = {
    "search": {
        "min_rooms": 0, "max_rooms": 0, "min_rent": 0, "max_rent": 0, "min_area": 0,
        "exclude_keywords": [],
    },
    "zones": [],
    "flatfox": {"enabled": True, "categories": ["APARTMENT"]},
    "anibis": {"enabled": False, "search_urls": [], "max_pages": 2},
    "email_alerts": {"enabled": False, "host": "", "user": "", "password_env": "HOMENOTIF_IMAP_PASSWORD", "folder": "INBOX"},
    "notify": {"enabled": False, "smtp_host": "", "smtp_port": 587, "user": "",
               "password_env": "HOMENOTIF_SMTP_PASSWORD", "from": "", "to": ""},
    "app": {"db_path": "data/listings.db", "poll_minutes": 15, "dashboard_url": "http://127.0.0.1:8000"},
}


def _check_zones(zones):
    seen = {}
    for number, zone in enumerate(zones, 1):
        zone.setdefault("name", f"Zone {number}")
        for code in zone.get("npa", []):
            if code not in npa.table():
                raise SystemExit(f"config: zone '{zone['name']}' has unknown NPA {code}")
            if code in seen:
                raise SystemExit(f"config: NPA {code} is in both '{seen[code]}' and '{zone['name']}'")
            seen[code] = zone["name"]


def load(path="config.toml"):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"{path} not found - copy config.example.toml to {path} and edit it.")
    user = tomllib.loads(p.read_text(encoding="utf-8"))
    cfg = copy.deepcopy(DEFAULTS)
    for section, values in user.items():
        if isinstance(values, dict):
            cfg.setdefault(section, {}).update(values)
        else:
            cfg[section] = values
    _check_zones(cfg["zones"])
    return cfg


def all_npas(cfg):
    return [code for zone in cfg["zones"] for code in zone.get("npa", [])]
