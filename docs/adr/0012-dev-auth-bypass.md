---
status: accepted
---

# Development auth bypass

Local debugging should not depend on an OpenID Connect provider on every login. When `AUTH_DEV_BYPASS` is enabled, `GET /login` creates a normal Flask session and `users` row from environment variables and never redirects to the IdP. If bypass is on, it wins even when OIDC credentials are also set.

The synthetic `AUTH_DEV_SUB` is stored in `users.oidc_sub` like a real IdP subject. Superuser follows the same bootstrap rule as OIDC login, unless `AUTH_DEV_SUPERUSER` is set explicitly.

Bypass is refused unless `FLASK_DEBUG` or `AUTH_DEV_BYPASS_ALLOW` is also set, so a single mis-set variable cannot silently disable OIDC in production. Production deployments use OIDC only; bypass is not a product feature.
