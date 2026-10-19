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
- Schlägt der Versand für eine Rolle fehl (SMTP), bleibt der Schritt offen (`mail_pending`); erneuter Abschluss versendet nur die noch ausstehende Rolle, ohne Doppelversand an bereits zugestellte Empfänger.
- Phasen-Receipt-Mails an Ausleihende*n und Materialwart*innen können einen **PDF-Anhang** tragen: nach Freigabe die Packliste, nach Packen die Abholliste, nach Abholung die Rückgabeliste. Dieselben Listen sind ab der passenden Phase per API abrufbar. Layout: kompakt, QR oben rechts zum Verleih, zweispaltiger Kopf (Verleih/Gruppe/Ausleihende | Inventar/Datum von–bis/Materialwart*in), Tabelle (Stück/Menge, Materialart, Set), Fußzeile unterhalb des Rahmens mit Instanztitel und Erstellzeitpunkt. PDF-Dokumenteigenschaften: Titel „Listenart — Verleih“; Autor zuständige Materialwart*in; Erstellt mit LaMathek inkl. Instanztitel und Untertitel; Beschreibung zeilenweise wie der Kopfbereich; Erstellzeit in der per Umgebungsvariable `LAMATHEK_INSTANCE_TIMEZONE` konfigurierten Zeitzone (Standard Europe/Berlin) aus UTC. Abhol- und Rückgabeliste: nebeneinander Unterschriftsfeld (Beschriftung „Unterschrift Ausleihende*r“ unter der Linie) und Datumsfeld.

## Konsequenzen

- `loan_workflow`, `mail_pending`, Mail-Templates; UI Schritt-Header und Chevron-Menü; in der Schritt-Leiste (bzw. für Ausleihende als Link unter dem Hinweis) PDF der Pack-, Abhol- oder Rückgabeliste öffnen, sobald die API sie für die aktuelle Phase freigibt.
- Tests: `test_loan_notifications.py`, `test_loan_shortcuts.py` (Superuser-Delete).
