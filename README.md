# LaMathek

Material inventory and lending for VCP Hessen.

**What it does**

- **Inventare** at several places, with Materialarten (with variants), named **Einzelteile**, counted **Mengen** and **Sets** (e.g. a Jurte).
- **Verleih** from request to restock: availability per date range, packing, pickup and return lists as PDF, losses and corrections as events, a journal of every change.
- Mails to borrowers and Materialwart*innen through a retrying outbox; a dashboard, a calendar with iCal feeds, and context help.
- Roles per Inventar (manage or read), superusers for the installation; OpenID Connect login.

Domain terms are German on purpose; [CONTEXT.md](CONTEXT.md) defines them.

**Documentation**

- [CONTEXT.md](CONTEXT.md) — domain glossary (terms; German headwords, English for code)
- [docs/domain/README.md](docs/domain/README.md) — **product rules (Deutsch)** — start here for Verleih, workflow, permissions
- [docs/software.md](docs/software.md) — index of domain records
- [docs/adr/](docs/adr/) — technical ADRs (English)

**Version:** [CalVer](https://calver.org/) `YYYY.MM.MICRO` (see [CHANGELOG.md](CHANGELOG.md)).

## Development

### Quick start (UI)

From the repository root:

```bash
./scripts/dev.sh
```

The script sets `LAMATHEK_ENV=dev`, loads [`.env.dev`](.env.dev) (dev login, SQLite path, ports), then starts the API and Vite. Open [http://127.0.0.1:5173](http://127.0.0.1:5173) and click **Anmelden**.

`.env.dev` is tracked and holds only safe defaults. Put personal values (your name and mail for the dev login, SMTP credentials) in **`.env.local`**, which is gitignored and loaded after `.env.dev`. Never commit credentials.

`./scripts/dev.sh --seed` deletes the local database and media, migrates, and loads demo data: two Inventare, the set „Jurte 1“ and Verleihe in every phase. The same works standalone with `python scripts/seed_demo.py --reset`.

PDF lists use WeasyPrint, which needs Cairo and Pango on the host (`brew install pango` on macOS, `libpango-1.0-0 libpangocairo-1.0-0` on Debian; see the [Dockerfile](Dockerfile)).

Python dependencies are declared in [server/pyproject.toml](server/pyproject.toml).

For OIDC or a custom setup without the script, copy `.env.example` to `.env` and configure it yourself.

### Local login without OIDC

[`.env.dev`](.env.dev) is used by `./scripts/dev.sh`. To configure manually, set in `.env`:

- `FLASK_DEBUG=1` (or `AUTH_DEV_BYPASS_ALLOW=1`)
- `AUTH_DEV_BYPASS=1`
- `AUTH_DEV_SUB=dev:local` (required; becomes `users.oidc_sub`)
- Optional: `AUTH_DEV_NAME`, `AUTH_DEV_EMAIL`
- Optional: `AUTH_DEV_SUPERUSER=1` or `0`; if unset, the first user bootstrap rule applies

Click **Anmelden** as usual; `/login` skips the IdP and signs you in as that dev user. Each distinct `AUTH_DEV_SUB` is a separate row in `users`. With bypass enabled, OIDC is not used even if credentials are configured.

### API (Flask)

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
lamathek
```

The API listens on `http://127.0.0.1:5001` (port 5001 avoids macOS AirPlay on 5000).

### Web (Vue)

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api`, `/login`, `/auth`, and `/logout` to the API.

### API contract

The JSON answers of `/api` are Pydantic models in [server/lamathek/contract/models.py](server/lamathek/contract/models.py); each route declares its model with `@responds(...)`. Tests and the dev server validate every answer against it. After changing a model or an answer:

```bash
cd server && lamathek openapi          # writes lamathek/domain/openapi.json
cd ../web && npm run generate:api      # writes src/api/generated/schemas.ts
```

`pytest` and `npm test` fail while either file is stale. See [ADR 0021](docs/adr/0021-api-contract-openapi.md).

### Production-style run

```bash
cd web && npm run build
cd ../server && source .venv/bin/activate
lamathek migrate
SECRET_KEY=… gunicorn --workers 1 --threads 8 'lamathek.app:create_app()'
```

With `web/dist` present, Flask serves the built client. Use one worker: SQLite has a single writer. Outside `FLASK_DEBUG` the app refuses to start without a real `SECRET_KEY`.

### Staging image locally

```bash
docker compose -f deploy/docker-compose.staging.yml up --build
```

Open `http://127.0.0.1:5001`. The compose file enables dev auth bypass for local smoke tests and binds to localhost only; never expose it. Coolify uses OIDC only.

### Staging (Coolify)

Coolify builds the root [Dockerfile](Dockerfile) and serves the built client from Flask (`LAMATHEK_STATIC_ROOT=/app/web/dist`). Use the Dockerfile as the build pack, not Nixpacks. Connect the GitHub App so a push to `main` webhooks Coolify and redeploys. The image sets `SQLITE_PATH=/data/lamathek.sqlite3`, runs `lamathek migrate` on startup, then serves with gunicorn (one worker, eight threads) behind the proxy (`X-Forwarded-*` is honoured). Mount a volume at `/data` so the database and uploaded photos (`/data/media` by default, or set `MEDIA_PATH`) survive deploys. The image listens on `0.0.0.0` and `PORT` (default 5001).

Set these in Coolify, not in the repo: `SECRET_KEY`, `FRONTEND_URL=https://<domain>`, `OIDC_REDIRECT_URI=https://<domain>/auth/callback` (same URI in the IdP), `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_SERVER_METADATA_URL`. Do not set `AUTH_DEV_BYPASS`.

Optional: `LAMATHEK_INSTANCE_TIMEZONE` (IANA, default `Europe/Berlin`) for "today" and timestamps.

Optional outbound mail: `SMTP_HOST`, `SMTP_FROM`, and usually `SMTP_PORT` (default 587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS`, `SMTP_SSL` (for port 465), `SMTP_TIMEOUT`. Superusers can send a test mail from **Diagnose** when SMTP is configured.

### Live reload in Docker (optional)

[deploy/docker-compose.dev.yml](deploy/docker-compose.dev.yml) bind-mounts the checkout, reloads Flask when `LAMATHEK_RELOAD=1`, and runs Vite on port 5173. The API stays internal and Vite proxies to it. SQLite is `server/lamathek.sqlite3` inside the mount (gitignored), separate from the staging volume.

```bash
docker compose -f deploy/docker-compose.dev.yml up
```

Use the same OIDC variables as staging (`FRONTEND_URL` pointing at wherever this stack is reached). Behind HTTPS, set `VITE_HMR_HOST` to that hostname. A second Coolify resource can run this file on its own domain. Leave auto-deploy off for that resource: a GitHub redeploy replaces the checkout and drops uncommitted edits there.

### Database migrations

Migrations live in [server/lamathek/migrations](server/lamathek/migrations) and ship with the package.

```bash
cd server
source .venv/bin/activate
lamathek migrate                                   # apply
alembic revision --autogenerate -m "short slug"    # new migration from model changes
```

`tests/test_migrations.py` upgrades an empty database to head and compares it with the models, so a migration that drifts from the models fails CI.
