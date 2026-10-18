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

Mehrere Entwürfe dürfen dasselbe Stück referenzieren; Konflikt entsteht bei Bestätigung.

## Entscheidung

- Material bleibt für andere Verleihe **verfügbar**, bis eine Position **bestätigt** ist.
- Nach Bestätigung blockiert bis frühem Ende, **Verlust** oder **Übernahme**.
- Dasselbe **Einzelteil** darf in mehreren **Entwürfen** liegen.
- Eine zweite **Bestätigung** schlägt fehl, wenn ein anderer Verleih das Stück bereits hält (`piece_unavailable`).

## Konsequenzen

- Server: Verfügbarkeitsprüfung bei Bestätigung und Anfrage; Einzelteil-Sperre über Stück-Ereignisse (nicht über historische `not_returned`-Zeilen).
- UI: verständliche Fehlermeldung mit Hinweis auf blockierenden Verleih wo möglich.
- Terminüberschneidungen bei bereits bestätigten Belegungen: **Warnung** (Speichern erlaubt); zweite Bestätigung desselben Einzelteils bleibt abgelehnt.
