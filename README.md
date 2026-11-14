# home-notifications

Watches Swiss apartment listings and tells you about new ones that fit your criteria:
an email as soon as a match appears, an optional daily digest, and a local dashboard.

## Sources

| Source | How | Notes |
|---|---|---|
| Flatfox | Public JSON API | Searches a radius around `[search] center`. |
| Anibis | Search pages (embedded JSON) | Uses the search URLs you paste into the config. Also carries some Homegate listings. |
| ImmoScout24, Homegate, Comparis, Newhome | Their own alert emails, read over IMAP | These sites block scrapers, so create saved searches there and send the alerts to a dedicated mailbox. |

## Setup

```bash
pip install -r requirements.txt
cp config.example.toml config.toml
```

Edit `config.toml`: your criteria under `[search]`, your zones under `[[zones]]`, Anibis search URLs, and (optionally) the mailboxes.
Passwords come from environment variables (`HOMENOTIF_IMAP_PASSWORD`, `HOMENOTIF_SMTP_PASSWORD`);
for Gmail use an app password.

## Usage

```bash
python -m homenotif run      # dashboard + check every poll_minutes
python -m homenotif fetch    # check all sources once, notify about new matches
python -m homenotif digest   # email everything matched in the last 24 hours
python -m homenotif serve    # dashboard only
python -m homenotif zones    # list your zones with the villages each NPA covers
```

The dashboard runs at http://127.0.0.1:8000.

The first check of a site, and the first check after you change the zones, only fills the database;
emails start with listings that appear after that.
With `[notify] enabled = false`, new matches are printed to the console instead of emailed.

## How matching works

- Location is decided by postcode (NPA): each `[[zones]]` entry is a list of NPAs, in order of
  preference. A listing is tagged with its zone (shown in emails and the dashboard, where you can
  filter by zone) and listings outside every zone don't match. One NPA often covers several villages;
  `python -m homenotif zones` shows which. The NPA list comes from swisstopo's official
  locality directory (`homenotif/data/npa.csv`).
- Flatfox is searched in the area around all your zones.
- A listing must also satisfy rent, rooms and area, and contain none of the `exclude_keywords`.
- Values a source doesn't provide count as a pass, including a missing postcode.
- Changing the criteria re-checks every stored listing; old listings that start to match are not emailed.
- Listings with the same zip code, room count and rent (to CHF 10) are treated as the same flat;
  only the first is announced and the dashboard shows the others as "also on".

## Tests

```bash
python -m pytest
```
