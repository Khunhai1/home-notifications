from homenotif import db
from homenotif.config import DEFAULTS
from homenotif.matching import fingerprint, matches, parse_rent, parse_rooms
from homenotif.models import Listing
from homenotif.sources.email_alerts import listing_ref, parse_html

SEARCH = DEFAULTS["search"] | {"min_rooms": 2.5, "max_rooms": 4.5, "max_rent": 2500,
                               "center": [46.948, 7.447], "radius_km": 8, "exclude_keywords": ["WG"]}

ALERT_HTML = """
<a href="https://www.homegate.ch/mieten/4001234567?utm_source=alert"><img src="x.jpg" alt=""></a>
<a href="https://www.homegate.ch/mieten/4001234567?utm_source=alert">Helle 3.5-Zimmer-Wohnung mit Balkon</a>
<a href="https://www.homegate.ch/mieten/4001234567">CHF 2'150.– · 3.5 Zimmer · 82 m² · 3007 Bern</a>
<a href="https://click.mail.example/?u=https%3A%2F%2Fwww.comparis.ch%2Fimmobilien%2Fmarktplatz%2Fdetails%2Fshow%2F37536669">
  4.5 Zimmer, CHF 2400</a>
<a href="https://www.homegate.ch/unsubscribe/99999999">Abmelden</a>
<a href="https://www.homegate.ch/mieten/wohnung/ort-bern/trefferliste">Alle Treffer</a>
"""


def flat(**kw):
    return Listing(**({"source": "flatfox", "source_id": "1", "url": "u", "title": "Nice flat"} | kw))


def test_parsers():
    assert parse_rooms("Schöne 3,5-Zimmer-Wohnung") == 3.5
    assert parse_rooms("Appartement 4 pièces") == 4
    assert parse_rooms("Studio in Orbe") == 1
    assert parse_rent("CHF 2'150.– pro Monat") == 2150
    assert parse_rent("1'870.- pro Monat") == 1870
    assert parse_rent("CHF 950") == 950


def test_matches():
    assert matches(flat(rent=2000, rooms=3.5, lat=46.95, lon=7.45), SEARCH)
    assert not matches(flat(rent=2600, rooms=3.5), SEARCH)
    assert not matches(flat(rent=2000, rooms=1.5), SEARCH)
    assert not matches(flat(rent=2000, rooms=3.5, lat=47.37, lon=8.54), SEARCH)  # Zurich
    assert not matches(flat(rent=2000, rooms=3.5, title="Zimmer in WG"), SEARCH)
    assert matches(flat(), SEARCH)  # unknown values pass


def test_listing_ref():
    assert listing_ref("https://www.immoscout24.ch/rent/4001999888?x=1") == (
        "immoscout24", "4001999888", "https://www.immoscout24.ch/rent/4001999888")
    assert listing_ref("https://flatfox.ch/de/flat/3007-bern/86543406/")[:2] == ("flatfox", "86543406")
    assert listing_ref("https://www.homegate.ch/mieten/wohnung/ort-bern/trefferliste") is None
    assert listing_ref("https://evil.example/homegate.ch/4001234567") is None


def test_alert_email():
    found = {l.source: l for l in parse_html(ALERT_HTML)}
    assert set(found) == {"homegate", "comparis"}
    h = found["homegate"]
    assert (h.source_id, h.rent, h.rooms, h.area, h.zipcode) == ("4001234567", 2150, 3.5, 82, 3007)
    assert h.url == "https://www.homegate.ch/mieten/4001234567"
    assert found["comparis"].source_id == "37536669" and found["comparis"].rent == 2400


def test_db_dedup_and_notify(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    a = flat(rent=2150, rooms=3.5, zipcode=3007)
    b = flat(source="homegate", source_id="9", rent=2150, rooms=3.5, zipcode=3007)
    assert fingerprint(a) == fingerprint(b)
    assert db.insert(conn, a, True, silent=False)
    assert not db.insert(conn, a, True, silent=False)
    assert db.insert(conn, b, True, silent=False)
    pending = db.pending(conn)
    assert [r["source"] for r in pending] == ["flatfox"]  # the duplicate is not announced
    db.mark_notified(conn, [r["id"] for r in pending])
    assert db.pending(conn) == []
    rows = db.browse(conn)
    assert len(rows) == 1 and rows[0]["also_on"][0]["source"] == "homegate"
