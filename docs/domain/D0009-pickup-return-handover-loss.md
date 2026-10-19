---
id: D0009
titel: Abholung, Rückgabe, Verlust
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Verlust, Rückgabe]
---

# D0009 — Abholung, Rückgabe, Verlust

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Verleih**, **Verlust**, **Rückgabe**.

## Entscheidung

- Abholung und Rückgabe können **ohne persönliches Treffen** erfolgen.
- **Ausleihende*r**: abgeholt, nicht abgeholt, Rückmeldung pro Position.
- **Materialwart*in**: gepackt, übernommen; darf auch abgeholt, nicht abgeholt und Rückgabe markieren — MW-Markierung reicht allein.
- **Nicht zurückgebracht** = **Verlust**. Er wird als **Ereignis** gebucht, nie durch Löschen oder Verkleinern von Material:
  - **Einzelteil:** Totalverlust-Ereignis am Stück (siehe D0011).
  - **Menge:** Verlust mit Anzahl an einem Mengenposten. Der Posten behält seine Soll-Anzahl, Bezeichnung, Variante und Fotos; solange der Verlust offen ist, fehlt die Anzahl beim Verleihen.
- Fehlt nur ein Teil einer Position, wird dieser Teil als eigene Position abgespalten und als Verlust beendet; der Rest bleibt draußen bzw. wird übernommen. Mehr als die Position kann nicht verloren gehen.
- Meldet Ausleihende*r Rückgabe, Material fehlt → MW bucht **Verlust**.
- Verbrauchsmaterial: Rückgabe und Übernahme; zurückgegebene Menge bleibt, der Rest wird als **Verbrauch** gebucht und senkt die Soll-Anzahl sofort.
- **Auflösen eines Mengenverlusts** am Mengenposten, jeweils mit Grund: **wiedergefunden** (auch teilweise; die Anzahl ist wieder verleihbar) oder **ausgebucht** (endgültig; die Soll-Anzahl sinkt). Ein Einzelteil-Totalverlust wird wiedergefunden oder ausgebucht (Teil wird aussortiert), nie „repariert“.
- **Korrektur** einer irrtümlich als Verlust beendeten Position (Wiederherstellen): Das Ereignis wird als „irrtümlich erfasst“ geschlossen; die Position belegt wieder, sofern das Material im Zeitraum frei ist (D0007).
- Mengenposten mit verbuchten Verlusten werden nicht gelöscht; sie sind deren Nachweis.
- Verleih **geschlossen**, wenn jede Position geendet hat: übernommen, Verlust, frühes Ende oder zurückgezogen.

## Konsequenzen

- Phasen `handover`, `return`, `restock`, `closed`; Bestandsbuchung bei Verlust.
- Einzelteil-Verlust legt zusätzlich ein **Totalverlust-Ereignis** am Stück an; die Zeile `not_returned` bleibt Verleih-Historie.
- **Wieder im Bestand** nach abgeschlossenem Verleih: Auflösung des Ereignisses am Stück, alter Verleih unverändert.
