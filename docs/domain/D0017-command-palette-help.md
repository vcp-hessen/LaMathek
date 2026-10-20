---
id: D0017
titel: Befehlspalette und Kontext-Hilfe
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Inventar, Materialwart*in]
---

# D0017 — Befehlspalette und Kontext-Hilfe

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Inventar**, **Materialwart*in**.

## Kontext

Häufige Aktionen sollen ohne Navigieren erreichbar sein, und Fachbegriffe sollen dort erklärt werden, wo sie auftauchen.

## Entscheidung

**Befehlspalette**

- Öffnen mit Cmd/Strg+K oder dem Knopf in der Seitenleiste; nur für Materialwart*innen des gewählten Inventars.
- Befehle: neue Materialart, neues Einzelteil, mehrere Einzelteile, neuer Verleih (wird zur aktiven Box). Sie beziehen sich auf das Inventar, das beim Ausführen gewählt ist.
- Es gibt genau eine Palette in der App (auch bei geöffneter Mobil-Navigation).
- Suche über Material, Verleihe und Personen sowie Zugang für Ausleihende sind noch offen (Issue #10).

**Kontext-Hilfe**

- Ein Info-Symbol neben Überschriften öffnet eine kurze Erklärung; sie schließt mit Escape, Klick außerhalb oder erneutem Klick.
- Gibt es zum Thema einen Glossar-Eintrag, verlinkt die Erklärung ihn (`/hilfe#anker`, die Seite scrollt dorthin).
- Die Texte stehen in `help.context.*` und `help.glossary.*` der Übersetzungen; das Glossar folgt den Begriffen aus CONTEXT.

## Konsequenzen

- UI: `AppCommandPalette`, `ContextHelp`, `HelpGlossaryView`.
- Tests: Browser-Durchlauf; die Texte prüft der Typecheck nicht.

## Nicht-Ziele

- Interaktives Tutorial (Issue #1).
