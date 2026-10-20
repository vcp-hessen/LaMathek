---
status: accepted
---

# Instance time zone

`LAMATHEK_INSTANCE_TIMEZONE` (IANA name, default `Europe/Berlin`) defines the calendar day of the installation. "Today" for overdue checks, loss dates and the dashboard comes from `instance_today()`, and PDF timestamps from `instance_now()`, independent of the server's or container's `TZ`. The API returns timestamps in UTC with an offset; the browser shows them in its local time.

Storing it in the database settings was rejected: it is part of the deployment, like the database path ([0011](./0011-configuration.md)).
