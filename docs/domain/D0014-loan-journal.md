---
id: D0014
titel: Verleih-Journal
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Position, Einzelteil, Schaden]
---

# D0014 — Verleih-Journal

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Verleih**, **Position**, **Einzelteil**, **Schaden**.

## Entscheidung

- Pro Verleih und pro Einzelteil gibt es ein **append-only Journal** (`loan_journal_entries`).
- Einträge haben `kind`, optional `actor_user_id`, JSON-`payload`, Verknüpfungen zu Verleih, Position und/oder Einzelteil.
- Geschrieben wird bei:
  - **Verleih:** anlegen; Stammdaten ändern (mit altem und neuem Wert je Feld); Phasenabschluss.
  - **Positionen:** hinzufügen (einzeln oder als Set, inkl. übersprungener Set-Teile), entfernen (Entwurf), Anzahl ändern (mit Grund), anfragen, bestätigen, ablehnen, ersetzen (Original und Ersatz), zurückziehen, packen, abholen, Rückgabe, Übernahme, Verlust, Abbruch, Abholung übersprungen, Korrektur.
  - **Mails:** versendet, endgültig nicht zustellbar, nicht möglich (keine Adresse oder kein Mailversand eingerichtet).
  - **Einzelteil:** Schaden, Reparatur, wiedergefunden, ausgebucht.
- Jeder Positionseintrag nennt das betroffene Teil (Name bzw. „Anzahl × Materialart“), damit das Journal ohne Positionsliste lesbar ist.
- Handelt eine Superuser*in in Imitation, nennt der Eintrag beide (D0001).
- API: `GET /api/loans/<id>/journal` für alle, die den Verleih sehen; `GET /api/pieces/<id>/journal` nur für Materialwart*innen des Inventars (es listet alle Verleihe des Teils samt Gründen).

## Konsequenzen

- UI: Journal-Abschnitt in Verleih- und Einzelteil-Detail.
- Tests: `tests/test_records.py`, `tests/test_security.py` (Zugriff, Imitation).
