# Deploying from scratch

The pieces and where they run:

| Piece | Where | What it needs |
|---|---|---|
| Fetch job (every 15 min) + daily digest | GitHub Actions (`.github/workflows/fetch.yml`, `digest.yml`) | `DATABASE_URL`, optional SMTP/IMAP secrets |
| Database | Neon Postgres, `main` branch (plus a `dev` branch for local work and tests) | the schema in `migrations/`, applied by `python -m homenotif migrate` |
| Dashboard + settings | Cloudflare Pages project `home-notifications`, deployed by `.github/workflows/deploy-web.yml` | Pages secrets below |
| Login | Cloudflare Zero Trust Access app on `home-notifications.pages.dev` and `*.home-notifications.pages.dev` | an allow policy for your email, one-time PIN login |

## 1. Neon
1. Create a project (region `aws-eu-central-1`, Frankfurt, closest to Switzerland). The free plan is enough.
2. Keep compute small to stay inside the free compute hours: 0.25–0.5 CU, scale to zero enabled.
3. Create a `dev` branch for local development and tests.
4. Put both connection strings in `.env`: `DATABASE_URL` (main) and `TEST_DATABASE_URL` (dev).
5. Run `python -m homenotif migrate` against each.
6. Optionally move an old local setup in with `python -m homenotif import-local --config config.toml --sqlite data/listings.db`.

## 2. GitHub
1. Create the repository and push `main`.
2. Repository secrets (`gh secret set NAME`):

| Secret | Used by |
|---|---|
| `DATABASE_URL` | fetch, digest |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | deploy-web |
| `HOMENOTIF_SMTP_USER`, `HOMENOTIF_SMTP_PASSWORD` | email notifications (optional; e.g. a Gmail address + app password) |
| `HOMENOTIF_IMAP_USER`, `HOMENOTIF_IMAP_PASSWORD` | reading portal alert emails (optional) |

Email is only sent once the SMTP secrets are set **and** a notification address is saved on the settings page.

## 3. Cloudflare
The API token needs: Account › Cloudflare Pages: Edit, Account › Access: Apps and Policies: Edit,
Account › Access: Organizations, Identity Providers, and Groups: Edit.

1. **Pages project** `home-notifications`, production branch `main`. Deploys come from GitHub
   Actions (`wrangler pages deploy`), not from Cloudflare's Git integration.
2. **Pages variables**, all as *secrets* so wrangler deploys keep them:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon main connection string |
| `ACCESS_TEAM_DOMAIN` | `<team>.cloudflareaccess.com` |
| `ACCESS_AUD` | the Access application's AUD tag |
| `GITHUB_REPO` | `owner/home-notifications` |
| `GITHUB_TOKEN` | optional, enables "Check now" on the settings page (below) |

3. **Access**:
   - add the one-time PIN login method;
   - create a policy *Owner only* (allow, include: your email);
   - create a self-hosted application covering `home-notifications.pages.dev` **and**
     `*.home-notifications.pages.dev` (without the wildcard, preview deployments stay public);
   - copy its AUD tag into `ACCESS_AUD`.
   - The dashboard also verifies the Access token itself (`web/src/hooks.server.ts`), so a request
     that somehow bypasses Access still gets 403.

## "Check now" button (optional)
Create a fine-grained personal access token on GitHub:
- Settings › Developer settings › Fine-grained tokens;
- only this repository;
- permission **Actions: Read and write**.

Store it as the Pages secret `GITHUB_TOKEN`. Without it the button is hidden.

## Local development
- Python: see the README; `.env` holds `DATABASE_URL`.
- Web: `web/.dev.vars` holds `DATABASE_URL` (use the dev branch) and `DEV_USER=dev@example.com`,
  which skips the Access check locally. Then `npm --prefix web run dev`.
