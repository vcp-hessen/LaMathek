---
id: D0006
titel: Positionsstatus und Korrekturen
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Position, Grund, Verlust]
---

# D0006 — Positionsstatus und Korrekturen

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Position**, **Grund**, **Verlust**.

## Kontext

Jede Position hat einen eigenen Lebenszyklus unabhängig von anderen Positionen desselben Verleihs.

## Entscheidung

**Normaler Ablauf**

Entwurf → angefragt → bestätigt → gepackt → abgeholt → zurückgemeldet → übernommen.

**Frühes Ende**

Nicht verfügbar, nicht gepackt, nicht abgeholt, nicht zurückgebracht — jeweils mit **Grund**; Verkleinerung einer Anzahl ebenfalls mit Grund.

**Korrektur durch Materialwart*in**

- Begründetes frühes Ende oder irrtümlicher **Verlust** kann rückgängig gemacht werden (Verfügbarkeit und Ersatz-Regeln beachten).
- Die Position kehrt in den Schritt zurück, den sie verlassen hat (`status_before_end`).

**Sonstiges**

- **Notiz** auf einer Position jederzeit möglich, auch während Wartezeiten; andere Positionen laufen weiter.
- **Ersatz**: neue bestätigte Position; Original endet als nicht verfügbar mit Grund.

## Konsequenzen

- API: `restore` / Korrektur-Aktionen; Migration `status_before_end`.
- UI: Grund-Panel unten; Zeilenmenü „Korrektur: wieder aktiv“ für MW.
- Tests: `test_loan_workflow_sharp.py` u. a.
