# Changelog

LaMathek uses [CalVer](https://calver.org/) as `YYYY.MM.MICRO`. Nothing has been released yet; the first published version will get a dated CalVer tag.

- **YYYY.MM** — release month
- **MICRO** — increment within that month

Until the first release, `[Unreleased]` describes what the app can do; intermediate states that were replaced before release are not listed.

## [Unreleased]

### Added

**Grundlagen**

- Flask-API mit SQLite (SQLAlchemy 2, Alembic) und Vue-3-Client (Vite, Pinia, TanStack Query, DaisyUI, deutsche Oberfläche); Anmeldung über OpenID Connect, für die Entwicklung ohne IdP (`AUTH_DEV_*`).
- Installations-Einstellungen in der Datenbank (Titel, Impressum, Datenschutz, Kartenmittelpunkt, Bundesland), öffentliche Seiten Impressum und Datenschutz.
- Superuser*innen mit Imitation anderer Personen (mit Grund, Audit-Log); Diagnose mit Testmail und Liste nicht zugestellter Mails.

**Inventare und Material**

- Inventare mit Adresse, Karte, Notiz und Freigabe (intern, aktiv, archiviert); Berechtigungen je Inventar: verwalten oder Leserecht (ansehen und anfragen).
- Materialarten mit Kategorie, Hersteller, Modell, Einheit, Verbrauchsmaterial und beliebig vielen Variantenbezeichnern.
- Einzelteile (auch im Stapel mit Namensmuster) und Mengen aus Mengenposten; jeder Mengenposten ist genau eine Variante (#12). Optionale Angaben: Anschaffungsjahr, Neuwert, Seriennummer, Herkunft, Notiz, Status aussortiert.
- Sets mit Zuordnung und Optionals aus Einzelteilen und Mengen (je Variante); Sets reservieren nichts.
- Fotos als WebP neben der Datenbank mit Vorschaubildern, an Einzelteilen, Mengenposten, Materialarten, Sets, Schäden, Inventaren und Abhol-/Rückgabeinformationen.
- Schaden und Reparatur je Einzelteil; Totalverlust als eigenes Ereignis mit Auflösung wiedergefunden, ausgebucht oder Irrtum.

**Verleih**

- Verleih je Inventar für eine*n Ausleihende*n im Namen einer Gruppe, mit Titel, Terminen oder als Dauerleihgabe; Materialwart*innen legen Verleihe auch für andere an, auch für Personen ohne Login.
- Workflow Entwurf → Prüfung → Packen → Abholung → Rückgabe → Übernahme mit Positionsstatus, Gründen, Ersatz, Zurückziehen, Korrektur und Nachziehen von Positionen; „aktive Box“ zum Befüllen aus Material- und Set-Listen.
- Datumsbasierte Verfügbarkeit: Belegung von Abholung bis Rückgabe, Mengen nach Tageshöchstlast, überfälliges Material bis heute; Konflikte als Hinweise an jeder Position und als harte Grenze bei Bestätigen, Ersetzen, Wiederherstellen und Terminänderung.
- Verlust und Verbrauch als Ereignisse; Teilverluste werden abgespalten und lassen sich korrigieren, verlorene Mengen wiederfinden oder ausbuchen.
- Mails an Ausleihende und Materialwart*innen zu jedem Schritt über eine Outbox mit Wiederholung und „Erneut senden“; Pack-, Abhol- und Rückgabeliste als PDF (Download, Anhang an Materialwart*innen).
- Journal je Verleih und Einzelteil mit allen Änderungen.

**Übersicht und Hilfe**

- Startseite mit Karten über alle Inventare: Konflikte, nicht zugestellte Mails, offene Anfragen, Fälligkeiten, eigene Verleihe.
- Kalender als Monat und Tabelle mit Feiertagen je Bundesland und iCal-Abos (eigene Verleihe, als Ansprechperson, alle eines Inventars).
- Befehlspalette (Cmd/Strg+K) zum Anlegen von Material und Verleihen; Kontext-Hilfe und Glossar.

**Betrieb**

- Docker-Image mit gunicorn, Migrationen im Paket (`lamathek migrate`), Instanz-Zeitzone (`LAMATHEK_INSTANCE_TIMEZONE`), Demo-Daten (`scripts/seed_demo.py --reset`, `./scripts/dev.sh --seed`).
- Tests: pytest für die API (inkl. Migration ab leerer Datenbank und Vollständigkeit der Fehlertexte), Vitest für den Client.

### Security

- Rechte für globale Objekte: Zusammenführen von Personen nur durch Superuser*innen, Kontaktdaten nur durch die Person selbst bzw. zuständige Materialwart*innen, keine Telefonnummern oder Login-Kennungen in Listen und Journalen.
- Abhol- und Rückgabefotos nur für Beteiligte, Einzelteil-Journal nur für Materialwart*innen, Kalender-Abos prüfen die Rolle bei jedem Abruf.
- CSRF-Schutz über einen Pflicht-Header, SameSite/HttpOnly/Secure-Cookies, Start nur mit eigenem `SECRET_KEY`, Upload-Grenzen, Bildformate begrenzt, JSON-Fehler.
