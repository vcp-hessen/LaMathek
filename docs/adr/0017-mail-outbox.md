---
status: accepted
---

# Mail outbox

Mails about a Verleih are rows in `mail_outbox`, written in the same transaction as the change they report. A background thread in the app process sends due rows. It claims each row with a short lease (an UPDATE only one process can win), so several gunicorn workers or the dev reloader never send twice. Failed sends are retried after 1, 5 and 30 minutes, 2 and 6 hours, then marked failed; Materialwart*innen can resend from the Verleih, superusers see failed mails under Diagnose. PDF attachments are rendered when sending.

Sending inside the request was rejected: a slow or failing SMTP server left steps half committed and kept the SQLite write lock. A separate worker process or a queue service (Redis, Celery) was rejected as too much infrastructure for one small installation. Without SMTP configured, no loan mails are queued; the journal records that.
