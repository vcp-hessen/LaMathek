---
status: accepted
---

# Configuration: environment versus database

Each LaMathek installation is deployed once and then run by Materialwarte. Some settings belong to the host and must not be editable in the UI. Others describe this installation and should default sensibly, then be changed in the app by superusers.

**Environment** holds what ties the process to infrastructure and identity: database location, Flask secret, OpenID Connect client credentials and metadata URL, redirect URI, frontend URL, SMTP credentials for outbound mail (`SMTP_HOST`, `SMTP_FROM`, and related variables), the instance timezone (`LAMATHEK_INSTANCE_TIMEZONE`) and paths (`SQLITE_PATH` or `DATABASE_URL`, `MEDIA_PATH`, `LAMATHEK_STATIC_ROOT`). These values are set when the instance is deployed. Changing them requires a redeploy or a restart, not a screen in LaMathek. For local development only, optional `AUTH_DEV_*` variables can skip OIDC; see [0012-dev-auth-bypass.md](./0012-dev-auth-bypass.md).

**Database** holds installation settings that operators may change without touching the server: display title and subtitle, legal imprint fields for the public Impressum page, and the default map centre used when an Inventar has no coordinates. Rows are created with defaults on first migration or first boot. Superusers edit them in the application.

A **superuser** is an installation-wide administrator, not tied to one Inventar. The first person who signs in with OpenID Connect while no superuser exists becomes a superuser. Later superusers are appointed by existing superusers. Superusers manage installation settings and can grant Berechtigungen on any Inventar. A **Materialwart*in** is anyone with a managing Berechtigung on an Inventar; they manage that Inventar and may grant or revoke Berechtigungen on it. A Berechtigung can instead be a **Leserecht**: read an internal Inventar and request Verleihe from it. There is no global Materialwart flag on users.

The product name LaMathek can stay in code and i18n as the software name; the database title and subtitle identify this deployment (for example VCP Hessen and Landesmaterial).

**Considered options:** Putting branding only in locale files was rejected because another group’s copy should not require a rebuild to rename the UI. Putting OIDC secrets in the database was rejected because they are deployment secrets and belong in the environment.
