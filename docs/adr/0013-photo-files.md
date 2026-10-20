---
status: accepted
---

# Photo files beside SQLite

LaMathek stores photo bytes on disk, not in SQLite. The database records which entity owns each photo and the sort order for the cover image.

Files live in the same volume as the database (`MEDIA_PATH`, default `media` next to `SQLITE_PATH`). Staging mounts `/data` for both `lamathek.sqlite3` and `media/`. Uploads are normalized to lossy WebP without EXIF; cached thumbnails at 160 px and 640 px are generated on upload. The API serves images to signed-in users who may view the owning Inventar (any signed-in user for an active Inventar, a Berechtigung for an internal one). Pickup and return photos of a Verleih are only served to people who may see that Verleih. Uploads are limited to JPEG, PNG and WebP of at most 64 megapixels.

Blobs in SQLite were rejected because backups and size would couple image traffic to the database file. A separate object store was rejected because one small installation does not need S3 or similar.
