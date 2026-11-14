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

Edit `config.toml`: your criteria under `[search]`, Anibis search URLs, and (optionally) the mailboxes.
Passwords come from environment variables (`HOMENOTIF_IMAP_PASSWORD`, `HOMENOTIF_SMTP_PASSWORD`);
for Gmail use an app password.

## Usage

```bash
python -m homenotif run      # dashboard + check every poll_minutes
python -m homenotif fetch    # check all sources once, notify about new matches
python -m homenotif digest   # email everything matched in the last 24 hours
python -m homenotif serve    # dashboard only
```

The dashboard runs at http://127.0.0.1:8000.

The first check of a site only fills the database; emails start with listings that appear after that.
With `[notify] enabled = false`, new matches are printed to the console instead of emailed.

## How matching works

- A listing must satisfy rent, rooms, area, radius (when it has coordinates) or the zip whitelist
  (when it doesn't), and contain none of the `exclude_keywords`.
- Values a source doesn't provide count as a pass. Anibis listings and alert emails have no
  coordinates, so filter location in the Anibis search URL / the portal's saved search, or set `zipcodes`.
- Listings with the same zip code, room count and rent (to CHF 10) are treated as the same flat;
  only the first is announced and the dashboard shows the others as "also on".

## Tests

```bash
python -m pytest
```
