---
status: accepted
---

# SQLAlchemy 2 for SQLite access

LaMathek stores data in SQLite. The Flask server uses SQLAlchemy 2 with mapped classes for domain tables as they are added. Alembic owns schema changes from the first migration.

A Bestand count changes through an explicit UPDATE in the same transaction as the rest of the work, so a reservation is not lost in the identity map. The standard-library sqlite3 driver and hand-written SQL were rejected because the domain has many related entities; Peewee was rejected because SQLAlchemy is the usual choice for Flask and matches the size of the model ahead.
