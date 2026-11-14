from homenotif import db, npa
from homenotif.matching import evaluate, fingerprint, matches, parse_rent, parse_rooms
from homenotif.models import Listing
from homenotif.sources.email_alerts import listing_ref, parse_html

SEARCH = {"min_rent": 0, "min_area": 0, "min_rooms": 2.5, "max_rooms": 4.5, "max_rent": 2500, "exclude_keywords": ["WG"]}
CFG = {"search": SEARCH, "zones": [{"name": "City", "npa": [3011]}, {"name": "Around", "npa": [3072, 3084]}]}

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
    assert matches(flat(rent=2000, rooms=3.5), SEARCH)
    assert not matches(flat(rent=2600, rooms=3.5), SEARCH)
    assert not matches(flat(rent=2000, rooms=1.5), SEARCH)
    assert not matches(flat(rent=2000, rooms=3.5, title="Zimmer in WG"), SEARCH)
    assert matches(flat(), SEARCH)  # unknown values pass


def test_zones():
    assert evaluate(flat(rent=2000, rooms=3.5, zipcode=3011), CFG) == (True, 1)
    assert evaluate(flat(rent=2000, rooms=3.5, zipcode=3084), CFG) == (True, 2)
    assert evaluate(flat(rent=2000, rooms=3.5, zipcode=8001), CFG) == (False, None)  # Zurich
    assert evaluate(flat(rent=2600, rooms=3.5, zipcode=3011), CFG) == (False, 1)
    assert evaluate(flat(rent=2000, rooms=3.5), CFG) == (True, None)  # unknown postcode passes
    assert "Ostermundigen" in npa.localities(3072)
    south, west, north, east = npa.bbox([3011, 3084])
    assert south < 46.93 < 46.95 < north and west < 7.44 < 7.45 < east


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


def test_db_dedup_and_notify(conn):
    a = flat(rent=2150, rooms=3.5, zipcode=3007)
    b = flat(source="homegate", source_id="9", rent=2150, rooms=3.5, zipcode=3007)
    assert fingerprint(a) == fingerprint(b)
    assert db.insert(conn, a, True, 1, silent=False)
    assert not db.insert(conn, a, True, 1, silent=False)
    assert db.insert(conn, b, True, 1, silent=False)
    pending = db.pending(conn)
    assert [r["source"] for r in pending] == ["flatfox"]  # the duplicate is not announced
    db.mark_notified(conn, [r["id"] for r in pending])
    assert db.pending(conn) == []
    dup = conn.execute("SELECT duplicate_of FROM listings WHERE source = 'homegate'").fetchone()
    assert dup["duplicate_of"] == pending[0]["id"]


def test_silent_insert_is_not_announced(conn):
    assert db.insert(conn, flat(rent=2000, rooms=3, zipcode=3011), True, 1, silent=True)
    assert db.pending(conn) == []


def test_rematch_does_not_announce_old_listings(conn):
    db.insert(conn, flat(rent=2000, rooms=3.5, zipcode=8001), False, None, silent=False)
    assert db.rematch(conn, lambda l: evaluate(l, CFG)) == 0
    assert db.pending(conn) == []
    assert db.rematch(conn, lambda l: (True, 1)) == 1
    row = conn.execute("SELECT matched, zone, notified_at FROM listings").fetchone()
    assert (row["matched"], row["zone"]) == (True, 1) and row["notified_at"]
    assert db.pending(conn) == []


def test_settings_round_trip(conn):
    search = {"min_rooms": 2, "max_rooms": 3.5, "min_rent": 0, "max_rent": 1800, "min_area": 40,
              "exclude_keywords": ["WG"]}
    zones = [{"name": "City", "npa": [3012, 3011]}, {"name": "Around", "npa": [3084]}]
    db.save_settings(conn, search, zones, ["https://www.anibis.ch/de/q/x"], "me@example.com")
    s = db.load_settings(conn)
    assert s["search"] == search
    assert s["zones"] == [{"name": "City", "npa": [3011, 3012]}, {"name": "Around", "npa": [3084]}]
    assert s["anibis_urls"] == ["https://www.anibis.ch/de/q/x"] and s["notify_to"] == "me@example.com"
    db.save_settings(conn, search, zones[1:], [], "")
    assert [z["name"] for z in db.load_settings(conn)["zones"]] == ["Around"]


def test_state(conn):
    assert db.get_state(conn, "k") is None
    db.set_state(conn, "k", "1")
    db.set_state(conn, "k", "2")
    assert db.get_state(conn, "k") == "2"
