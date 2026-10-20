---
status: accepted
---

# Production server and hardening

The image runs `lamathek migrate` and then gunicorn with one worker and eight threads (SQLite has one writer; the mail outbox thread runs in-process), behind the proxy with `ProxyFix`. Migrations ship inside the package (`lamathek/migrations`); a test upgrades an empty database to head and compares it with the models.

Defaults are safe: the app refuses to start outside debug with the built-in `SECRET_KEY`; the session cookie is HttpOnly, SameSite=Lax and Secure behind HTTPS; every state-changing `/api` request must carry `X-Requested-With: lamathek` (a cross-site form cannot set it); request bodies are limited to 25 MB; API errors are JSON. The Flask development server is for local use only.
