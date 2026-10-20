---
id: D0007
titel: Verfügbarkeit und Bestätigung
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Position, Verleih, Einzelteil]
---

# D0007 — Verfügbarkeit und Bestätigung

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Position**, **Verleih**, **Einzelteil**.

## Kontext

Die meisten Verleihe kommen pünktlich und vollständig zurück. Material soll deshalb für jeden Zeitraum verleihbar sein, in dem es frei ist — ein Zelt, das für Dezember zugesagt ist, darf im Juli raus.

## Entscheidung

- **Belegung ist datumsbasiert.** Eine Position belegt ihr Material von **Abholung** bis **Rückgabe**, beide Tage eingeschlossen. Eine **Dauerleihgabe** belegt ab Abholung ohne Ende. Am selben Tag zurück und wieder raus gilt als Überschneidung; einen Puffer für Trocknen oder Prüfen legen Materialwart*innen über die Termine selbst fest.
- **Nur bestätigtes Material belegt** (Status bestätigt, gepackt, abgeholt, Rückgabe gemeldet). Entwürfe und Anfragen belegen nichts; dasselbe Einzelteil darf in mehreren Entwürfen und Anfragen liegen.
- **Überfällig:** Ist Material nach dem Rückgabedatum noch draußen, belegt es bis **heute** (Instanz-Zeitzone). Es kann also jetzt nicht erneut raus; spätere Zeiträume bleiben verleihbar und zeigen einen Hinweis.
- **Einzelteile:** frei, wenn keine andere belegende Position den Zeitraum berührt und das Teil nicht aussortiert, als Totalverlust verbucht oder schwer beschädigt ist (letzteres gilt unabhängig vom Datum).
- **Mengen:** Je Materialart **und Variante** (#12) wird für jeden Tag des Zeitraums die belegte Anzahl über **alle** Verleihe summiert (auch weitere Positionen desselben Verleihs). Die höchste Tageslast plus die neue Anzahl darf die Menge der aktiven Mengenposten nicht übersteigen.
- **Sets reservieren nichts.** Ein Set beschreibt nur, was zusammengehört; geprüft werden seine Einzelteile und Mengen wie jede andere Position.
- **Bestätigung braucht Termine:** ohne Abholung (und bei kurzem Verleih ohne Rückgabe) keine Bestätigung.

**Wo geprüft wird (harte Grenze, 409 mit den Konflikten):**

- Bestätigen und Ersetzen einer Position.
- Wiederherstellen einer beendeten Position, wenn sie dadurch wieder belegt.
- Terminänderung oder Wechsel Dauerleihgabe ↔ Verleih bei einem Verleih mit belegenden Positionen.
- Menge von Hand senken: nur wenn die neue Anzahl unter der höchsten Belegung ab heute läge (`below_loaned`). Ein Verlust wird dagegen immer verbucht und erzeugt Hinweise.

**Wo gewarnt wird (Speichern erlaubt):** An jeder offenen Position erscheint, was eine Bestätigung verhindern würde, mit Link auf den anderen Verleih; dazu Hinweise auf parallele Anfragen desselben Einzelteils und auf offene leichte Schäden. Auf der Seite eines verlorenen oder schwer beschädigten Einzelteils stehen die Verleihe, die es noch eingeplant haben.

## Konsequenzen

- Server: eine einzige Prüfstelle `services/availability.py` für Gates und Warnungen; Fehler `piece_unavailable` / `over_loaned` / `dates_conflict` mit `conflicts` (Position, anderer Verleih, freie Anzahl).
- UI: Hinweisliste am Verleih und Markierung je Position; Fehlermeldungen nennen den blockierenden Verleih.
- Tests: `tests/test_availability.py`.
