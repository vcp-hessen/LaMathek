---
status: accepted
---

# SQLite as the only database

LaMathek stores all of its data in SQLite. There is no separate database server.

The database is one file. About five people use LaMathek at once, so SQLite’s limit of one writer at a time is acceptable. Hosting and backup still have to treat that file as the database.
