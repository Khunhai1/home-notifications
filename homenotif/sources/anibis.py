"""Anibis search pages embed their results as JSON in a __NEXT_DATA__ script tag."""
import json
import re

from ..matching import parse_area, parse_rooms
from ..models import Listing
from . import http_client

SITE = "https://www.anibis.ch"
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
MONTHLY_RE = re.compile(r"monat|mois|mese|month", re.I)


def parse_page(html):
    m = NEXT_DATA_RE.search(html)
    if not m:
        raise RuntimeError("anibis: page has no __NEXT_DATA__ (layout changed or request blocked)")
    data = json.loads(m.group(1))
    for query in data["props"]["pageProps"]["dehydratedState"]["queries"]:
        listings = (query["state"].get("data") or {}).get("listings")
        if listings:
            return [e["node"] for e in listings["edges"]]
    return []


def _to_listing(node):
    price = node.get("formattedPrice") or ""
    if not MONTHLY_RE.search(price):
        return None  # for sale, or no price
    text = node["localization"]
    title, body = text.get("title") or "", text.get("body") or ""
    place = node.get("postcodeInformation") or {}
    thumb = (node.get("thumbnail") or {}).get("retinaRendition") or {}
    digits = re.sub(r"\D", "", price.split(".-")[0])
    return Listing(
        source="anibis",
        source_id=node["listingID"],
        url=f"{SITE}/de/vi/{node['listingID']}",
        title=title or "Anibis listing",
        description=body,
        rent=float(digits) if digits else None,
        rooms=parse_rooms(f"{title} {body}"),
        area=parse_area(f"{title} {body}"),
        zipcode=int(place["postcode"]) if (place.get("postcode") or "").isdigit() else None,
        city=place.get("locationName") or "",
        image_url=thumb.get("src") or "",
        published_at=node.get("timestamp") or "",
    )


def fetch(cfg, known_ids):
    with http_client() as client:
        for url in cfg["anibis"]["search_urls"]:
            for page in range(1, cfg["anibis"]["max_pages"] + 1):
                r = client.get(url, params={"page": page} if page > 1 else None, follow_redirects=True)
                r.raise_for_status()
                nodes = parse_page(r.text)
                fresh = [n for n in nodes if n["listingID"] not in known_ids]
                for node in fresh:
                    listing = _to_listing(node)
                    if listing:
                        yield listing
                if not fresh:
                    break  # results are newest first: nothing new further down
