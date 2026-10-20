---
id: D0016
titel: Startseite
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Inventar, Materialwart*in, Ausleihende*r]
---

# D0016 — Startseite

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Verleih**, **Inventar**, **Materialwart*in**, **Ausleihende*r**.

## Kontext

Wer sich anmeldet, soll ohne Suchen sehen, was gerade zu tun ist — über alle Inventare, in denen die Person etwas verwaltet oder leiht.

## Entscheidung

- Die Startseite zeigt Karten mit offenen (nicht abgeschlossenen, keinen Entwurfs-) Verleihen; jeder Eintrag verlinkt den Verleih. Nach acht Einträgen lässt sich die Karte aufklappen.
- **Ausleihende** sehen nur „Eigene Verleihe“.
- **Materialwart*innen** sehen zusätzlich, über alle Inventare mit Verwaltungsrecht:
  - **Konflikte bei der Belegung**: Verleihe in Prüfung, Packen oder Abholung, bei denen eine Position nicht frei ist (D0007) oder ein Einzelteil verloren bzw. schwer beschädigt ist. Wird hervorgehoben und nur gezeigt, wenn es etwas gibt.
  - **Mails nicht zugestellt**: Verleihe mit Mails, deren Versand fehlgeschlagen ist (D0012). Ebenfalls nur bei Bedarf.
  - **Offene Anfragen** (Phase Prüfung), **Warten auf Materialwart*in** (Prüfung, Packen, Abholung, Übernahme), **Rückgabe fällig** (Rückgabedatum heute oder früher), **Überfällige Rückgaben**, **Änderungen noch nicht mitgeteilt**.
- „Heute“ ist der Tag in der Zeitzone der Instanz.
- Superuser*innen sehen die Karten über alle Inventare.

## Konsequenzen

- API: `GET /api/dashboard`; gefiltert wird in der Datenbank, nicht über alle Verleihe.
- UI: Startseite (`HomeView`).
- Tests: `tests/test_records.py`, `tests/test_dashboard.py`.

## Nicht-Ziele

- Konfigurierbare Karten oder Benachrichtigungen außerhalb der Mails.
