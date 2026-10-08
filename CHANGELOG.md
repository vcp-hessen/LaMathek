# Changelog

LaMathek uses [CalVer](https://calver.org/) as `YYYY.MM.MICRO`. Nothing has been released yet; the first published version will get a dated CalVer tag.

- **YYYY.MM** — release month
- **MICRO** — increment within that month

## [Unreleased]

### Added

- Decision record, domain glossary, and MIT license.
- Flask API with SQLite (SQLAlchemy 2, Alembic), OpenID Connect login, and Vue 3 client (Vite, Pinia, TanStack Query, DaisyUI, German i18n).
- Installation settings (title, subtitle) and superuser management in the database.
- Development auth bypass (`AUTH_DEV_*`) for local login without an IdP.
- ADRs for SQLAlchemy, configuration split, and dev auth bypass.
- Inventare with per-user Berechtigungen and roles Materialwart*in / Verantwortliche*r (UI).
- `scripts/dev.sh` to run API, web, and migrations for local UI testing.
