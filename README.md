# home-notifications

Watches Swiss apartment listings and tells you about new ones that fit your criteria.

- **GitHub Actions** checks the listing sites every 15 minutes and sends a daily digest.
- **Neon Postgres** stores the listings, your search criteria and your zones.
- **A SvelteKit dashboard on Cloudflare Pages** shows the matches on a list and a map. It also has a
  settings page for the criteria and zones. Cloudflare Access protects it, so only your email can log in.

Setting it up from scratch is described in [docs/DEPLOY.md](docs/DEPLOY.md).

## Sources

| Source | How | Notes |
|---|---|---|
| Flatfox | Public JSON API | Searches the area around your zones. |
| Anibis | Search pages (embedded JSON) | Uses the search URLs saved on the settings page. |
| ImmoScout24, Homegate, Comparis, Newhome | Their own alert emails, read over IMAP | These sites block scrapers. Create saved searches there and send the alerts to a dedicated mailbox. |

## How matching works

- **Location:** zones are lists of postcodes (NPA), in order of preference. A listing is tagged with
  its zone, and listings outside every zone don't match. One NPA often covers several villages;
  `python -m homenotif zones` shows which. The NPA list comes from swisstopo's official locality
  directory (`homenotif/data/npa.csv`).
- **Criteria:** a listing must also satisfy rent, rooms and area, and contain none of the
  excluded keywords. Values a source doesn't provide count as a pass, including a missing postcode.
- **Duplicates:** listings with the same postcode, room count and rent (to CHF 10) count as the same flat.
  Only the first is announced; the dashboard shows the others as "also on".
- **No floods of old listings:**
  - The first check of a site, and the first check after the zones change, only fills the database.
    Notifications start with listings that appear after that.
  - Changing the criteria re-checks every stored listing; old listings that start to match are not emailed.

## Running the job locally

```bash
pip install -r requirements.txt
cp .env.example .env    # then fill in DATABASE_URL
python -m homenotif migrate
python -m homenotif fetch     # check all sources once, notify about new matches
python -m homenotif digest    # email everything matched in the last 24 hours
python -m homenotif zones     # list your zones with the villages each NPA covers
```

Email is only sent when the SMTP user and password are set and a notification address is saved on
the settings page. Otherwise new matches are printed to the console.

To move an old local setup (`config.toml` + `data/listings.db`) into the database:

```bash
python -m homenotif import-local --config config.toml --sqlite data/listings.db
```

## Tests

```bash
python -m pytest            # DB tests need TEST_DATABASE_URL (e.g. a Neon dev branch)
cd web && npm test
```
