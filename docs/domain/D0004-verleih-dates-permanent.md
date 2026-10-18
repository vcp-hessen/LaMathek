---
id: D0004
titel: Termine und Dauerleihgabe
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Dauerleihgabe]
---

# D0004 — Termine und Dauerleihgabe

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Verleih**, **Dauerleihgabe**.

## Kontext

Termine gelten für den ganzen Verleih, nicht pro Position einzeln (außer konsumierbare Ausnahmen im Workflow).

## Entscheidung

**Wunschtermine**

- Die Ausleihende*r schlägt einen **Abhol-** und einen **Rückgabetermin** als Wunschtermine im Entwurf und mit der Anfrage vor.
- Materialwart*innen können Wunschtermine beim Vorbereiten und nach der Übergabe setzen oder anpassen.

**Betreuungstermine**

- Bestätigte Abhol- und Rückgabetermine unter **Betreuung** setzt oder ändert nur eine Materialwart*in.

**Dauerleihgabe**

- Explizite Markierung am Verleih; Ausleihende*r kann sie im Entwurf setzen.
- Materialwart*in bestätigt sie mit der ersten Freigabe oder setzt sie; danach nur noch MW-Änderung.
- Bei gesetzter Dauerleihgabe bleibt der Rückgabetermin leer; Aufheben der Markierung erfordert einen Rückgabetermin.
- Abholung, Rückgabe, Übernahme und Verlust gelten weiter, wenn Material zurückkommt.

## Konsequenzen

- Felder `wishPickupOn` / `wishReturnOn` vs. `pickupOn` / `returnOn` in API und Stammdaten-UI.
