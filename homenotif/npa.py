"""Swiss postcodes (NPA) with their localities and approximate coordinates."""
import csv
import math
from functools import cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "npa.csv"


@cache
def table():
    with DATA.open(encoding="utf-8") as f:
        rows = csv.DictReader((line for line in f if not line.startswith("#")), delimiter=";")
        return {int(r["npa"]): {"canton": r["canton"], "localities": r["localities"].split("|"),
                                "lat": float(r["lat"]), "lon": float(r["lon"])} for r in rows}


def localities(npa):
    entry = table().get(npa)
    return entry["localities"] if entry else []


def bbox(npas, margin_km=3.0):
    """(south, west, north, east) around the given postcodes."""
    points = [table()[n] for n in npas if n in table()]
    if not points:
        raise ValueError("none of the configured NPAs is a known Swiss postcode")
    lat_pad = margin_km / 111.0
    lon_pad = margin_km / (111.32 * math.cos(math.radians(points[0]["lat"])))
    return (min(p["lat"] for p in points) - lat_pad, min(p["lon"] for p in points) - lon_pad,
            max(p["lat"] for p in points) + lat_pad, max(p["lon"] for p in points) + lon_pad)


def center(npas):
    points = [table()[n] for n in npas if n in table()]
    if not points:
        return []
    return [sum(p["lat"] for p in points) / len(points), sum(p["lon"] for p in points) / len(points)]
