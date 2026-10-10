# LaMathek

Material inventory for VCP Hessen. Domain language is in [CONTEXT.md](CONTEXT.md). Product and architecture decisions are in [docs/software.md](docs/software.md) and [docs/adr/](docs/adr/).

**Version:** [CalVer](https://calver.org/) `YYYY.MM.MICRO` (see [CHANGELOG.md](CHANGELOG.md)).

## Development

### Quick start (UI)

From the repository root:

```bash
./scripts/dev.sh
```

The script sets `LAMATHEK_ENV=dev`, loads [`.env.dev`](.env.dev) (dev login, SQLite path, ports), then starts the API and Vite. Open [http://127.0.0.1:5173](http://127.0.0.1:5173) and click **Anmelden**.

Optional: copy `.env.example` to `.env` for local overrides on top of `.env.dev` when using the dev script.

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

### Production-style run

```bash
cd web && npm run build
cd ../server && source .venv/bin/activate && lamathek
```

With `web/dist` present, Flask serves the built client.

### Staging (Coolify)

Coolify builds the root [Dockerfile](Dockerfile) and serves the built client from Flask (`LAMATHEK_STATIC_ROOT=/app/web/dist`). Use the Dockerfile as the build pack, not Nixpacks. Connect the GitHub App so a push to `main` webhooks Coolify and redeploys. Set `SQLITE_PATH=/data/lamathek.sqlite3` and mount a volume at `/data` so the database survives deploys. The image listens on `0.0.0.0` and `PORT` (default 5001).

Set these in Coolify, not in the repo: `SECRET_KEY`, `FRONTEND_URL=https://<domain>`, `OIDC_REDIRECT_URI=https://<domain>/auth/callback` (same URI in the IdP), `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_SERVER_METADATA_URL`. Do not set `AUTH_DEV_BYPASS`.

### Live reload in Docker (optional)

[deploy/docker-compose.dev.yml](deploy/docker-compose.dev.yml) bind-mounts the checkout, reloads Flask when `LAMATHEK_RELOAD=1`, and runs Vite on port 5173. The API stays internal and Vite proxies to it. SQLite is `server/lamathek.sqlite3` inside the mount (gitignored), separate from the staging volume.

```bash
docker compose -f deploy/docker-compose.dev.yml up
```

Use the same OIDC variables as staging (`FRONTEND_URL` pointing at wherever this stack is reached). Behind HTTPS, set `VITE_HMR_HOST` to that hostname. A second Coolify resource can run this file on its own domain. Leave auto-deploy off for that resource: a GitHub redeploy replaces the checkout and drops uncommitted edits there.

### Database migrations

```bash
cd server
source .venv/bin/activate
alembic upgrade head
```
