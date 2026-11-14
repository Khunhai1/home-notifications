# Web dashboard

SvelteKit app for Cloudflare Pages: the listings dashboard (`/`) and the settings page (`/settings`).
It reads and writes the same Neon Postgres database as the Python job.

## Local dev

Create `web/.dev.vars` (gitignored):

```
DATABASE_URL="postgres://…"   # a Neon branch you can write to
DEV_USER="dev@example.com"    # skips the Cloudflare Access check; never set in production
```

Then `npm install` and `npm run dev` (http://localhost:5173). `predev`/`prebuild` regenerate
`static/npa.json` from `../homenotif/data/npa.csv`.

## Production environment (Pages project settings)

`DATABASE_URL`, `ACCESS_AUD`, `ACCESS_TEAM_DOMAIN` (e.g. `myteam.cloudflareaccess.com`),
and optionally `GITHUB_TOKEN` + `GITHUB_REPO` for the "Check now" button
(a token allowed to dispatch the `fetch.yml` workflow).

## Checks

`npm run check`, `npm test`, `npm run build`.
