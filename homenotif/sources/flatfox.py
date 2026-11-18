"""Flatfox public API: /pin/ lists listing ids inside a bounding box, /public-listing/ returns details."""
import logging
import time

from .. import npa
from ..config import all_npas
from ..models import Listing
from . import http_client

API = "https://flatfox.ch/api/v1"
SITE = "https://flatfox.ch"
MAX_PINS = 1000  # API limit per request
CHUNK = 50
DELAY = 1.0  # seconds between requests: Flatfox publishes no rate limit, so stay well below any
USER_AGENT = "home-notifications (personal apartment alert; +https://github.com/Khunhai1/home-notifications)"

log = logging.getLogger(__name__)


class Blocked(RuntimeError):
    """Flatfox refused us (rate limit or ban): stop for this run instead of insisting."""


def _get(client, url, params):
    time.sleep(DELAY)
    r = client.get(url, params=params)
    if r.status_code in (403, 429):
        raise Blocked(f"flatfox answered {r.status_code} to {url}; skipping the rest of this run")
    r.raise_for_status()
    return r.json()


def _pins(client, box, categories, depth=0):
    south, west, north, east = box
    params = [("south", south), ("west", west), ("north", north), ("east", east),
              ("max_count", MAX_PINS), ("offer_type", "RENT")]
    params += [("object_category", c) for c in categories]
    pins = {p["pk"]: p for p in _get(client, f"{API}/pin/", params)}
    log.info("flatfox: %d pins in search box (depth %d)", len(pins), depth)  # no coordinates: the logs are public
    if len(pins) >= MAX_PINS and depth < 4:
        # result was cut off: split the box in four and ask again
        mid_lat, mid_lon = (south + north) / 2, (west + east) / 2
        for sub in ((south, west, mid_lat, mid_lon), (south, mid_lon, mid_lat, east),
                    (mid_lat, west, north, mid_lon), (mid_lat, mid_lon, north, east)):
            pins |= _pins(client, sub, categories, depth + 1)
    return pins


def _absolute(url):
    return SITE + url if url and url.startswith("/") else url or ""


def _to_listing(r):
    cover = r.get("cover_image") if isinstance(r.get("cover_image"), dict) else {}
    rooms = r.get("number_of_rooms")
    return Listing(
        source="flatfox",
        source_id=str(r["pk"]),
        url=_absolute(r["url"]),
        title=r.get("description_title") or r.get("short_title") or r.get("public_title") or "Flatfox listing",
        description=(r.get("description") or "")[:3000],
        rent=r.get("rent_gross") or r.get("price_display"),
        rooms=float(rooms) if rooms else None,
        area=r.get("surface_living"),
        zipcode=r.get("zipcode"),
        city=r.get("city") or "",
        street=r.get("street") or "",
        lat=r.get("latitude"),
        lon=r.get("longitude"),
        image_url=_absolute(cover.get("url_thumb_m") or cover.get("url")),
        published_at=r.get("published") or "",
    )


def _details(client, pks):
    """Full listings for the given ids, CHUNK per request. Listings no longer online are left out."""
    for i in range(0, len(pks), CHUNK):
        chunk = pks[i:i + CHUNK]
        params = [("pk", pk) for pk in chunk] + [("expand", "cover_image"), ("limit", CHUNK)]
        results = _get(client, f"{API}/public-listing/", params)["results"]
        missing = set(chunk) - {item["pk"] for item in results}
        if missing:
            log.warning("flatfox: no details returned for %d listings", len(missing))
        for item in results:
            yield _to_listing(item)


def fetch(cfg, known_ids):
    npas = all_npas(cfg)
    if not npas:
        raise RuntimeError("flatfox needs at least one [[zones]] entry to know where to search")
    with http_client(USER_AGENT) as client:
        # the box around all zones; listings in it but outside the zones are filtered out later
        pins = _pins(client, npa.bbox(npas), cfg["flatfox"]["categories"])
        # Every unknown listing is fetched, whatever its price: the pin's price_display is sometimes
        # CHF 400-500 above the real rent, so filtering on it dropped flats that match.
        new = sorted(pk for pk in pins if str(pk) not in known_ids)
        log.info("flatfox: %d pins, %d already stored, fetching %d", len(pins), len(pins) - len(new), len(new))
        yield from _details(client, new)
