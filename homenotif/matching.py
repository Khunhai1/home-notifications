import re

from .models import Listing

ROOMS_RE = re.compile(r"(\d+(?:[.,]\d)?)\s*-?\s*(?:zimmer|zi\b|pi[eè]ces?|locali|rooms?)", re.I)
AREA_RE = re.compile(r"(\d{2,3})\s*m\s?[²2]", re.I)
RENT_RE = re.compile(r"(?:CHF|Fr\.)\s*(\d{1,2}['’\s.]?\d{3}|\d{3,4})|(\d{1,2}['’]\d{3}|\d{3,4})\.[-–—]", re.I)
ZIP_RE = re.compile(r"\b([1-9]\d{3})\s+[A-ZÄÖÜ][\w'’.\- ]{2,}")


def parse_rooms(text):
    m = ROOMS_RE.search(text)
    if m:
        return float(m.group(1).replace(",", "."))
    return 1.0 if re.search(r"\bstudio\b", text, re.I) else None


def parse_area(text):
    m = AREA_RE.search(text)
    return float(m.group(1)) if m else None


def parse_rent(text):
    m = RENT_RE.search(text)
    if not m:
        return None
    return float(re.sub(r"\D", "", m.group(1) or m.group(2)))


def parse_zip(text):
    m = ZIP_RE.search(text)
    return int(m.group(1)) if m else None


def zone_of(zipcode, zones):
    """1-based number of the zone containing the postcode, or None."""
    for number, zone in enumerate(zones, 1):
        if zipcode in zone.get("npa", []):
            return number
    return None


def evaluate(l: Listing, cfg: dict):
    """(matches the criteria, zone number or None)."""
    zone = zone_of(l.zipcode, cfg["zones"])
    if cfg["zones"] and l.zipcode is not None and zone is None:
        return False, None
    return matches(l, cfg["search"]), zone


def matches(l: Listing, s: dict) -> bool:
    """Check a listing against the [search] criteria (location is handled by the zones).
    Unknown values (e.g. an alert email without a room count) pass - the source's own
    search already filtered them."""
    if l.rent is not None:
        if s["max_rent"] and l.rent > s["max_rent"]:
            return False
        if l.rent < s["min_rent"]:
            return False
    if l.rooms is not None:
        if l.rooms < s["min_rooms"] or (s["max_rooms"] and l.rooms > s["max_rooms"]):
            return False
    if l.area is not None and l.area < s["min_area"]:
        return False
    text = f"{l.title} {l.description}".lower()
    return not any(k.lower() in text for k in s["exclude_keywords"])


def fingerprint(l: Listing):
    """Same flat on two portals -> same fingerprint. Needs zip, rooms and rent."""
    if l.zipcode is None or l.rooms is None or l.rent is None:
        return None
    return f"{l.zipcode}|{l.rooms:g}|{round(l.rent / 10)}"
