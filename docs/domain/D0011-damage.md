---
id: D0011
titel: Schaden
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Schaden, Einzelteil, Set]
---

# D0011 — Schaden

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Schaden**, **Einzelteil**, **Set**.

## Entscheidung

- **Schaden** hängt am **Einzelteil**.
- **Schwerer Schaden** (z. B. großer Riss in Zeltplane): Einzelteil darf nicht ausgegeben werden. Beim Hinzufügen eines Sets wird es (wie aussortierte oder verlorene Teile) übersprungen und als Hinweis gemeldet; der Rest des Sets kommt auf den Verleih.
- **Reparatur** wird am Schaden mitgeführt; nach Reparatur wieder ausgebbar, Protokoll bleibt.
- **Totalverlust** am Einzelteil: eigener Ereignistyp (`total_loss`), aus Verleih „Verlust verbuchen“; blockiert Ausleihe bis Auflösung (`found_again` am Stück nach abgeschlossenem Verleih, `cancelled_mistake` bei Korrektur im offenen Verleih).

## Konsequenzen

- Schwerer offener Schaden und offener Totalverlust blockieren Verleih und Set-Ausgabe über ein gemeinsames Gate; milde Schäden nur Hinweis.
