---
status: accepted
---

# SQLAlchemy 2 for SQLite access

LaMathek stores data in SQLite. The Flask server uses SQLAlchemy 2 with mapped classes for domain tables as they are added. Alembic owns schema changes from the first migration.

Counts of a Menge and their loss events change in the same transaction as the rest of the work (one commit per request), so nothing is half-written. The standard-library sqlite3 driver and hand-written SQL were rejected because the domain has many related entities; Peewee was rejected because SQLAlchemy is the usual choice for Flask and matches the size of the model ahead.
