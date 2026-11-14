from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import db
from .notify import _chf, templates


def create_app(cfg, conn):
    app = FastAPI(title="Flat finder", docs_url=None, redoc_url=None)

    @app.get("/", response_class=HTMLResponse)
    def index(status: str = "", source: str = "", all: str = ""):
        listings = db.browse(conn, status, source, include_unmatched=bool(all))
        points = [
            {"id": l["id"], "lat": l["lat"], "lon": l["lon"],
             "label": f"CHF {_chf(l['rent'])} · {l['rooms'] or '?'} rooms"}
            for l in listings if l["lat"] is not None and l["lon"] is not None
        ]
        return templates.get_template("index.html").render(
            listings=listings, points=points, center=cfg["search"]["center"],
            status=status, source=source, show_all=bool(all), sources=db.sources(conn))

    @app.post("/listing/{listing_id}/status")
    def set_status(listing_id: int, request: Request, status: str = Form()):
        db.set_status(conn, listing_id, status)
        return RedirectResponse(request.headers.get("referer") or "/", status_code=303)

    return app
