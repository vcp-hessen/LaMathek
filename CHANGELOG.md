# Changelog

LaMathek uses [CalVer](https://calver.org/) as `YYYY.MM.MICRO`. Nothing has been released yet; the first published version will get a dated CalVer tag.

- **YYYY.MM** — release month
- **MICRO** — increment within that month

## [Unreleased]

### Added

- App-Icon auf Basis des Logos mit abgerundeten Ecken (`web/public/app-icon.svg`, `app-icon.png`).
- Öffentliche Seite Datenschutzerklärung (`/datenschutz`), verlinkt in der Fußzeile; Hoster, Anmelde-Dienst und Aufsichtsbehörde in den Einstellungen konfigurierbar.
- Inventar-Berechtigungen: Superuser und berechtigte Materialwarte vergeben und entziehen Nutzer–Inventar-Paare; Nutzer*innen-Suche beim Hinzufügen (`/api/users/search`).
- Staging-Image (`Dockerfile`) für Coolify: gebautes Frontend, Flask auf `0.0.0.0`, Alembic beim Start, SQLite über ein Volume.
- Optionales Live-Reload-Compose (`deploy/docker-compose.dev.yml`) mit Bind-Mount, Flask-Reloader und Vite-HMR.
- Superuser-only Löschen für Inventare, Materialarten, Stücke und Sets mit Bestätigungsdialog und Hinweis auf unwiderruflich mitgelöschte abhängige Daten.

### Changed

- Berechtigungen: globale Rolle Materialwart/Verantwortliche entfällt; Materialwart*in nur noch über Inventar-Berechtigung; am Verleih ist jede angemeldete Nutzer*in als Verantwortliche*r wählbar.
- Materialarten: beliebig viele Variantenbezeichner mit je eigener Werteliste; Einzelteile speichern je Bezeichner einen Wert, Mengenposten optional pro Bezeichner (`variant` als Objekt in der API).
- Mengen bestehen aus Mengenposten (optionale Bezeichnung, optionale Variante, Anzahl). Verleih und Set rechnen mit der Summe. Eine Kiste ist keine Einzelteil.
- Variantenwerte bei Materialarten: einzeln per Eingabe und „Hinzufügen“ (DaisyUI-Join und Badges) statt kommagetrenntem Textfeld; Reihenfolge per Sortable.js (`vue-draggable-plus`) mit Live-Verschiebung; neue Werte werden lexikographisch (de) einsortiert.
- Sidebar: Einstellungen und Abmelden mit Waldläuferzeichen (geheim, zurück zum Anfang).
- Inventarwahl in der Sidebar als kompaktes Dropdown (Teleport), in der schmalen Leiste nur WLZ-Icon.

### Fixed

- WLZ-Buchstaben für Einstellungen (`W`) und Abmelden (`N`) in `wlz-glyphs.ts` ergänzt (Icons waren leer).
- Mobil: Theme und Abmelden nicht mehr doppelt in der Kopfzeile (nur im Hamburger-Menü).
- Staging-Image findet das gebaute Frontend über `LAMATHEK_STATIC_ROOT` (nach `pip install` liegt das Paket nicht mehr neben `web/dist`).
- Staging-Start migriert dieselbe SQLite-Datei, die die App öffnet (`SQLITE_PATH=/data/lamathek.sqlite3`). Vorher lief Alembic aus dem Quellbaum und die App aus `site-packages` gegen zwei verschiedene Dateien, `/api/settings` antwortete dann mit 500.
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
