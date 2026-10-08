# LaMathek

Material inventory for VCP Hessen. Domain language is in [CONTEXT.md](CONTEXT.md). Product and architecture decisions are in [docs/software.md](docs/software.md) and [docs/adr/](docs/adr/).

**Version:** [CalVer](https://calver.org/) `YYYY.MM.MICRO` (see [CHANGELOG.md](CHANGELOG.md)).

## Development

Python dependencies are declared in [server/pyproject.toml](server/pyproject.toml).

Copy `.env.example` to `.env`. Use either OpenID Connect or the development bypass below.

### Local login without OIDC

For faster debugging, set in `.env`:

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

### Database migrations

```bash
cd server
source .venv/bin/activate
alembic upgrade head
```
