from dataclasses import dataclass


@dataclass
class Listing:
    source: str            # flatfox, anibis, immoscout24, homegate, comparis, newhome
    source_id: str
    url: str
    title: str
    description: str = ""
    rent: float | None = None      # CHF per month
    rooms: float | None = None
    area: float | None = None      # m²
    zipcode: int | None = None
    city: str = ""
    street: str = ""
    lat: float | None = None
    lon: float | None = None
    image_url: str = ""
    published_at: str = ""
