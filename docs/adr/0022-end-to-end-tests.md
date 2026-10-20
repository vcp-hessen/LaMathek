---
status: accepted
---

# End-to-end tests with Playwright

Besides pytest (the API through the Flask test client) and Vitest (client building blocks), `web/e2e/` holds journeys that click through the real app: a whole Verleih from the box to the receipt mail, a refused overlapping request, a partial Mengen loss, Leserecht, setting up material, error pages and an expired session. `npm run test:e2e` runs them with `@playwright/test` in the locally installed Google Chrome (`channel: 'chrome'`, no browser download).

Each run starts its own stack (`e2e/support/start-stack.sh`): a fresh SQLite database with the demo seed, the client built with Vite and served by Flask under gunicorn as in production, the dev login bypass, and `API_CONTRACT_CHECK=1`, so an answer that breaks its model (ADR 0021) fails the journey as a 5xx. Mails go to a small in-process SMTP sink (`e2e/support/smtp-sink.ts`) that the tests read, so recipients and attachments are checked and no mail leaves the machine. People switch through the app's own impersonation. A journey's past can be arranged through the API as the acting person; the part under test is clicked. Every test fails on page errors, console errors and any 5xx.

The journeys share one database and run one after another; each creates what it changes. Selectors use roles and visible German labels, which is why form fields carry accessible names. CI is not set up yet; a CI run would use Playwright's own Chromium.
