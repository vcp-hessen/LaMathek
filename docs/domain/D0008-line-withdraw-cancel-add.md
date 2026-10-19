---
id: D0008
titel: Zurückziehen und Positionen nachziehen
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Position, Ausleihende*r]
---

# D0008 — Zurückziehen und Positionen nachziehen

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Position**, **Ausleihende*r**.

## Entscheidung

- **Ausleihende*r** kann angefragte oder bestätigte Positionen **vor dem Packen** vom Verleih nehmen → Status **zurückgezogen**, Material sofort frei, **ohne Grund**.
- Nach dem Packen kann **Materialwart*in** bis zur Abholung mit Grund als **nicht gepackt** beenden.
- Nach der ersten Bestätigung dürfen **weitere Positionen** hinzukommen: starten als **angefragt**, übernehmen die Termine des Verleihs, werden nur durch Materialwart*in **bestätigt** — nur solange der Verleih in **Entwurf**, **Prüfung** oder **Packen** ist (ab Abholung keine neuen Positionen).
- In **Packen** dürfen angefragte Nachzüge bestätigt, abgelehnt, zurückgezogen oder ersetzt werden; der Packen-Schritt schließt erst, wenn keine angefragte Position mehr offen ist.
- Bereits **bestätigte** Positionen können in **Prüfung** und **Packen** zurückgezogen (Ausleihende*r oder Materialwart*in), abgelehnt oder ersetzt werden (Materialwart*in, mit Grund) — also auch, solange andere Positionen noch angefragt sind.

## Konsequenzen

- Workflow-Aktionen `withdraw`, `mark-not-packed`; Nachziehen nur in `draft`, `review`, `pack`.
