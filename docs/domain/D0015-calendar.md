---
id: D0015
titel: Kalender
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Inventar, Materialwart*in, Ausleihende*r]
---

# D0015 — Kalender

## Entscheidung

- Ein Eintrag pro Verleih mit gesetztem Abholtermin, ab Phase Prüfung (keine Entwürfe).
- Dauerleihgabe ohne Rückgabe: Eintrag ab Abholung, im Feed ein Tag, in der App als offener Balken bis zum Rand des sichtbaren Monats.
- Mehrtägige Verleihe sind ein durchgehender Balken über die Tage, an Wochengrenzen weitergeführt.
- Wochenenden und die gesetzlichen Feiertage des in den Installationseinstellungen gewählten Bundeslands sind im Monat markiert (Berechnung im Frontend, Standard Hessen). Blättern geht monatsweise, inklusive Sprung auf den aktuellen Monat.
- Kalender in der Benutzer-Sektion: gemeinsame Ansicht; Monatsraster (Wochenenden, Feiertage, Blättern) bleibt sichtbar, auch wenn unter „Anzeige“ keine Verleih-Ebene aktiv ist — dann ohne Balken. Anzeige mit Schalter für **Eigene Ausleihen** und je Inventar mit Berechtigung dreistufig (**Aus**, **Nur Verantwortlich**, **Alle Verleihe** — letzteres nur mit Verwaltungsrecht). Farbe pro Balken: Eigene Ausleihen, Nur Verantwortlich, oder übrige Verleihe bei „Alle Verleihe“. Deduplizierung nach Verleih-ID.
- In App und API heißt der Eintrag wie der Verleih-Titel (Veranstaltung, sonst Gruppe, sonst Platzhalter mit Verleih-ID) — nicht nur die Gruppe.
- iCal-Abos auf einer eigenen Seite: je Eintrag ein benanntes Token (Anwendung). Inhalt mit denselben Begriffen (eigene Ausleihen; je Inventar Nur Verantwortlich oder Alle Verleihe). Abruf-URL beschreibt den Inhalt im Pfad (englisch: `…/borrower.ics`, `…/inventories/{id}/contact.ics`, `…/inventories/{id}/all-loans.ics`); Authentifizierung nur per Query-Parameter `token`. Widerruf pro Eintrag, auch nachdem man die Rolle verloren hat; Abruf ohne Sitzung, aber bei jedem Abruf wird geprüft, ob die Person den Inhalt noch sehen darf (sonst „nicht gefunden“). Termin-Titel (`SUMMARY`) wie in der App, ohne Zusatz für Dauerleihgaben; im Beschreibungstext zusätzlich Gruppe, Ausleihende und Link zum Verleih (`URL`), sofern gesetzt.
