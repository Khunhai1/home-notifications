import logging
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

log = logging.getLogger(__name__)


def _chf(value):
    return f"{value:,.0f}".replace(",", "'") if value is not None else "?"


def _when(value):
    try:
        when = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        return when.astimezone().strftime("%d %b %H:%M")
    except (TypeError, ValueError):
        return ""


templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)
templates.filters["chf"] = _chf
templates.filters["when"] = _when


def send(cfg, listings, subject):
    """Email the listings, or print them when [notify] is disabled."""
    n = cfg["notify"]
    if not n["enabled"]:
        print(f"\n{subject}")
        for l in listings:
            print(f"  [zone {l['zone'] or '-'}] [{l['source']}] CHF {_chf(l['rent'])} | {l['rooms'] or '?'} rooms | "
                  f"{l['zipcode'] or ''} {l['city'] or ''} | {l['title'][:60]}\n    {l['url']}")
        return
    password = os.environ.get(n["password_env"])
    if not password:
        raise RuntimeError(f"notify: environment variable {n['password_env']} is not set")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = n["from"]
    msg["To"] = n["to"]
    msg.set_content("\n\n".join(
        f"{'[zone %d] ' % l['zone'] if l['zone'] else ''}{l['title']}\nCHF {_chf(l['rent'])} - {l['rooms'] or '?'} rooms - {l['zipcode'] or ''} {l['city'] or ''}\n{l['url']}"
        for l in listings))
    html = templates.get_template("email.html").render(
        listings=listings, subject=subject, dashboard_url=cfg["app"]["dashboard_url"],
        zone_names=[z["name"] for z in cfg["zones"]])
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(n["smtp_host"], n["smtp_port"], timeout=30) as smtp:
        smtp.starttls()
        smtp.login(n["user"], password)
        smtp.send_message(msg)
    log.info("sent email '%s' to %s", subject, n["to"])
