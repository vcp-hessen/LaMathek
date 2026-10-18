---
id: D0012
titel: Workflow-Phasen und Mail
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Position, Ansprechperson, Ausleihende*r]
---

# D0012 — Workflow-Phasen und Mail

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Verleih**, **Position**, **Ansprechperson**, **Ausleihende*r**.

## Entscheidung

**Phasen und Aktionen**

- Positionen werden in der Liste bearbeitet.
- Jede Listenaktion gehört zur Verleih-**phase** (`draft`, `review`, `pack`, `handover`, `return`, `restock`, `closed`).
- Solange ein Mail-Receipt der aktuellen Phase offen ist (`mail_pending` an Positionen), rückt die Phase nicht vor; keine Aktion aus späteren Schritten.
- Phase im Schritt-Überblick abschließen sendet **ein** Receipt-Mail, erst wenn **alle** Positionen dieser Phase bearbeitet sind.
- Schritte: Anfrage, Zusage, Packen, Abholung, Rückgabe, Übernahme.
- Sprünge (nicht abgeholt, nicht gepackt, Abholung überspringen) nutzen dieselben Schrittregeln.
- **Abbrechen** und Sprung direkt zur Rückgabe: je ein Receipt über dieselbe Pipeline.

**Seltene Verleih-Aktionen (Chevron-Menü)**

- Verleih löschen, abbrechen, Abholung überspringen, alle als nicht abgeholt markieren — neben Phase-Abschluss, gleiche Phasen-Logik wie Zeilenaktionen.
- **Ausleihende*r**: nur unveröffentlichten **Entwurf** löschen.
- **Superuser*in**: jeden Verleih in jeder Phase löschen; Material wird **nicht** automatisch zurückgebucht.

**Mail**

- Jedes Receipt: **zwei** Mails mit rollenspezifischem Text — eine an Ausleihende*n, eine an Materialwart*innen.
- MW-Mail: **Ansprechperson** im To, übrige MW des Inventars im CC (gleicher MW-Text); Ausleihende*r nicht im CC der MW-Mail.
- Jede Mail listet alle Nicht-Entwurfs-Positionen mit Status und markiert Änderungen der Phase.
- **Anfrage senden** stellt Receipt in die Queue und schließt Anfrage-Schritt in einer Aktion ab.
- Geschlossener Verleih mit stillen Änderungen: Button **Änderungen mitteilen**, nur diese Änderungen.
- Ohne E-Mail-Adresse des Nutzers: Schritt gilt als erledigt, **keine** Mail.

## Konsequenzen

- `loan_workflow`, `mail_pending`, Mail-Templates; UI Schritt-Header und Chevron-Menü.
- Tests: `test_loan_notifications.py`, `test_loan_shortcuts.py` (Superuser-Delete).
