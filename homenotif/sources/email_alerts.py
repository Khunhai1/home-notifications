"""Reads the portals' own saved-search alert emails over IMAP and extracts the listings.

Listings are recognised by their links: a link to a known portal whose path contains
a numeric listing id. The text of all links pointing at the same listing (title,
price, rooms ...) is used to fill in the details.
"""
import email
import email.policy
import imaplib
import os
import re
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlsplit

from ..matching import parse_area, parse_rent, parse_rooms, parse_zip
from ..models import Listing
from . import http_client

PORTALS = {
    "immoscout24.ch": "immoscout24",
    "homegate.ch": "homegate",
    "comparis.ch": "comparis",
    "newhome.ch": "newhome",
    "flatfox.ch": "flatfox",
}
SKIP_RE = re.compile(
    r"unsubscribe|abmelden|abbestellen|d[ée]sabonn|d[ée]sinscri|disiscri|preferences|einstellungen|"
    r"privacy|datenschutz|impressum", re.I)
LISTING_HINT_RE = re.compile(r"CHF|Fr\.|zimmer|pi[eè]ce|locali|rooms|m²|m2", re.I)
MAX_RESOLVES = 30
MAX_HOPS = 5


class _Links(HTMLParser):
    """Collects (href, visible text) for every <a>."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._href, self._text = attrs["href"], []
        elif tag == "img" and self._href and attrs.get("alt"):
            self._text.append(attrs["alt"])

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(" ".join(self._text).split())))
            self._href = None


def _portal(host):
    host = (host or "").lower()
    for domain, name in PORTALS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def listing_ref(url, _nested=False):
    """(source, listing id, clean url) if the url points at a listing, else None."""
    parts = urlsplit(url)
    source = _portal(parts.hostname)
    if source:
        ids = [seg for seg in parts.path.split("/") if seg.isdigit() and len(seg) >= 5]
        if ids:
            return source, ids[-1], f"https://{parts.hostname}{parts.path}"
    if not _nested:
        # tracking links often carry the real target in a query parameter
        for _, value in parse_qsl(parts.query):
            if value.startswith("http"):
                ref = listing_ref(value, _nested=True)
                if ref:
                    return ref
    return None


def _resolve(url, client):
    """Follow a tracking link's redirects until it reveals a listing url."""
    for _ in range(MAX_HOPS):
        try:
            r = client.get(url, follow_redirects=False)
        except Exception:
            return None
        url = r.headers.get("location")
        if not r.is_redirect or not url:
            return None
        url = str(r.url.join(url))
        ref = listing_ref(url)
        if ref:
            return ref
    return None


def parse_html(html, from_portal=False, client=None, published_at=""):
    parser = _Links()
    parser.feed(html)
    found = {}  # (source, id) -> {"url": ..., "texts": [...]}
    resolves = 0
    for href, text in parser.links:
        if SKIP_RE.search(href) or SKIP_RE.search(text):
            continue
        ref = listing_ref(href)
        if not ref and client and from_portal and resolves < MAX_RESOLVES and LISTING_HINT_RE.search(text):
            resolves += 1
            ref = _resolve(href, client)
        if ref:
            entry = found.setdefault(ref[:2], {"url": ref[2], "texts": []})
            if text and text not in entry["texts"]:
                entry["texts"].append(text)
    for (source, source_id), entry in found.items():
        context = " ".join(entry["texts"])
        titles = [t for t in entry["texts"] if len(t) <= 150]
        yield Listing(
            source=source,
            source_id=source_id,
            url=entry["url"],
            title=max(titles, key=len) if titles else f"New listing on {source}",
            description=context[:1000],
            rent=parse_rent(context),
            rooms=parse_rooms(context),
            area=parse_area(context),
            zipcode=parse_zip(context),
            published_at=published_at,
        )


def parse_message(msg, client=None):
    body = msg.get_body(preferencelist=("html",))
    if body is None:
        return
    sender = str(msg.get("From", ""))
    from_portal = any(domain in sender.lower() for domain in PORTALS)
    try:
        published = parsedate_to_datetime(str(msg["Date"])).isoformat()
    except (TypeError, ValueError):
        published = ""
    yield from parse_html(body.get_content(), from_portal, client, published)


def fetch(cfg, known_ids=None):
    c = cfg["email_alerts"]
    password = os.environ.get(c["password_env"])
    if not password:
        raise RuntimeError(f"email_alerts: environment variable {c['password_env']} is not set")
    with imaplib.IMAP4_SSL(c["host"]) as imap, http_client() as client:
        imap.login(c["user"], password)
        imap.select(c["folder"])
        _, data = imap.search(None, "UNSEEN")
        for num in data[0].split():
            _, parts = imap.fetch(num, "(RFC822)")  # also marks the mail as seen
            msg = email.message_from_bytes(parts[0][1], policy=email.policy.default)
            yield from parse_message(msg, client)
