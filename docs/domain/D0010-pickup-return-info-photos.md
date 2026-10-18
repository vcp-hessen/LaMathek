---
id: D0010
titel: Abhol- und Rückgabeinformation
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Abholinformation, Rückgabeinformation, Foto]
---

# D0010 — Abhol- und Rückgabeinformation

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Abholinformation**, **Rückgabeinformation**, **Foto**.

## Entscheidung

- **Abholinformation** und **Rückgabeinformation** am Verleih: optionaler Freitext, jeweils mit **Fotos** möglich.
- Keine allgemeinen Verleih-Fotos ohne Rolle — nur `pickup` und `return`.
- Materialwart*in pflegt Abholinformation (z. B. beim Packen).
- Materialwart*in kann Rückgabeinformation vorbereiten; Ausleihende*r ergänzt bei der Rückgabe.

## Konsequenzen

- API: Fotos nur mit `role=pickup|return`; Migration entfernt alte allgemeine Verleih-Fotos.
- Listen-Thumbnails: Abhol- oder Rückgabe-Foto.
