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
- Geschrieben wird bei Stammdaten-Änderungen am Verleih, Positionsaktionen (bestätigen, packen, Verlust, …), Phasenabschluss, Mailversand (inkl. PDF-Anhangsart), Schaden/Reparatur und „wieder aufgetaucht“.
- API: `GET /api/loans/<id>/journal`, `GET /api/pieces/<id>/journal` für berechtigte Nutzer*innen.

## Konsequenzen

- UI: Journal-Abschnitt in Verleih- und Einzelteil-Detail.
- Tests ergänzen, wenn Journal-Verhalten gezielt abgesichert werden soll.
