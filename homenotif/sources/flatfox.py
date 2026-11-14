"""Flatfox public API: /pin/ lists listing ids inside a bounding box, /public-listing/ returns details."""
from .. import npa
from ..config import all_npas
from ..models import Listing
from . import http_client

API = "https://flatfox.ch/api/v1"
SITE = "https://flatfox.ch"
MAX_PINS = 1000  # API limit per request
CHUNK = 50


def _pins(client, box, categories, depth=0):
    south, west, north, east = box
    params = [("south", south), ("west", west), ("north", north), ("east", east),
              ("max_count", MAX_PINS), ("offer_type", "RENT")]
    params += [("object_category", c) for c in categories]
    r = client.get(f"{API}/pin/", params=params)
    r.raise_for_status()
    pins = {p["pk"]: p for p in r.json()}
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


def fetch(cfg, known_ids):
    npas = all_npas(cfg)
    if not npas:
        raise RuntimeError("flatfox needs at least one [[zones]] entry to know where to search")
    with http_client() as client:
        # the box around all zones; listings in it but outside the zones are filtered out later
        pins = _pins(client, npa.bbox(npas), cfg["flatfox"]["categories"])
        max_rent = cfg["search"]["max_rent"]
        new = [pk for pk, p in pins.items()
               if str(pk) not in known_ids and not (max_rent and (p.get("price_display") or 0) > max_rent)]
        for i in range(0, len(new), CHUNK):
            params = [("pk", pk) for pk in new[i:i + CHUNK]] + [("expand", "cover_image"), ("limit", CHUNK)]
            r = client.get(f"{API}/public-listing/", params=params)
            r.raise_for_status()
            for item in r.json()["results"]:
                yield _to_listing(item)
