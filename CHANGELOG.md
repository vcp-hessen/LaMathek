# Changelog

LaMathek uses [CalVer](https://calver.org/) as `YYYY.MM.MICRO`. Nothing has been released yet; the first published version will get a dated CalVer tag.

- **YYYY.MM** — release month
- **MICRO** — increment within that month

## [Unreleased]

### Added

- Staging-Image (`Dockerfile`) für Coolify: gebautes Frontend, Flask auf `0.0.0.0`, Alembic beim Start, SQLite über ein Volume.
- Optionales Live-Reload-Compose (`deploy/docker-compose.dev.yml`) mit Bind-Mount, Flask-Reloader und Vite-HMR.
- Superuser-only Löschen für Inventare, Materialarten, Stücke und Sets mit Bestätigungsdialog und Hinweis auf unwiderruflich mitgelöschte abhängige Daten.

### Fixed

- Staging-Image findet das gebaute Frontend über `LAMATHEK_STATIC_ROOT` (nach `pip install` liegt das Paket nicht mehr neben `web/dist`).
- Inventar-Umschalter lädt Listen und Detailansichten des gewählten Inventars neu (reaktive vue-query-Keys, Navigation behält den aktuellen Bereich).
- Decision record, domain glossary, and MIT license.
- Flask API with SQLite (SQLAlchemy 2, Alembic), OpenID Connect login, and Vue 3 client (Vite, Pinia, TanStack Query, DaisyUI, German i18n).
- Installation settings (title, subtitle) and superuser management in the database.
- Development auth bypass (`AUTH_DEV_*`) for local login without an IdP.
- ADRs for SQLAlchemy, configuration split, and dev auth bypass.
- Inventare with per-user Berechtigungen and roles Materialwart*in / Verantwortliche*r (UI).
- `scripts/dev.sh` to run API, web, and migrations for local UI testing.
- App shell with toggleable, pinnable sidebar navigation and light/dark theme.
- Per-Inventar Materialarten (Stück or Bestand), Stücke with optional Variante, and Bestand quantities.
- Sets with Zuordnung and Optionals (Stücke and reserved Bestand) per Inventar.
- Verleih per Inventar (geplant/ausgegeben) with Gruppe, Verantwortliche*r, optional Veranstaltung, and lines for Set, Stück, or Bestand.
- Rückgabe und Verlust auf ausgegebenen Verleihen (teilweise Bestand, Stück/Set ganz), Status abgeschlossen, Bestandsabschreibung bei Verlust.
- Schaden und Reparatur pro Stück; schwerer offener Schaden sperrt Ausgabe von Stück und Set mit Zuordnung.
- Dauerleihgabe als Verleih-Art (`kind` permanent), gleiche Ausgabe und Rückgabe wie beim kurzen Verleih.

### Added

- Sets: optionales Kürzel pro Inventar.
- Einzelteile: Gruppierung und Filter nach Materialart; Batch-Anlegen mit Namensmuster, optionalem bestehendem oder neuem Set.

### Changed

- Deutsche Oberfläche und Glossar: **Einzelteil**, **Menge** (Erfassungsart) und **Anzahl** (Zählwert); „Stück“ nur noch als Einheit.
- Materialarten, Stücke und Bestand: aufklappbare Zeilen mit Bearbeitung und Speichern in der Liste.
- Inventare: aufklappbare Zeilen mit Name und Berechtigungen, Anlegen über den Button in der Liste.
- Inventare: Adresse, Karte mit Koordinaten und Notiz; Geocoding über Nominatim.
- Einstellungen: Impressumsangaben, Kartenmittelpunkt; öffentliche Impressum-Seite.
- Impressum: Website-Feld; fixer Footer mit Anbieter, Impressum und Website.
- Karten: MapLibre GL mit OpenFreeMap-Vektorkacheln statt Leaflet-Raster.
- Impressum: Verantwortliche*r für den Inhalt aus Nutzer*innen mit Inventar-Berechtigung, kein eigenes Feld.
- Materialarten: Kürzel, Beschreibung, Einheit (Bestand), Verbrauchsmaterial, optionale instanzweite Kategorie.
- Verleih bucht nur Stück- und Bestandszeilen; Set hinzufügen übernimmt die Zuordnung mit Herkunft, Optionals separat. Bestand aus Set-Reservierung wird bei der Ausgabe nicht doppelt gezählt; Stück löschen und Bestandsabsenkung sind geschützt.
