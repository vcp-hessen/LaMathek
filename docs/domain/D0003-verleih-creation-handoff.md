---
id: D0003
titel: Verleih anlegen und Übergabe
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Verleih, Ausleihende*r, Gruppe, Veranstaltung, Ansprechperson]
---

# D0003 — Verleih anlegen und Übergabe

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Verleih**, **Ausleihende*r**, **Gruppe**, **Veranstaltung**, **Ansprechperson**.

## Kontext

Ein Verleih gehört zu einem Inventar, einer Gruppe und meist einer Veranstaltung.

## Entscheidung

- Ein **Verleih** gehört zu genau einem **Inventar**, ist Material für eine*n **Ausleihende*n** im Namen einer **Gruppe**, und gehört meist zu einer **Veranstaltung** (kann auch ohne).
- **Ausleihende*r** kann auf Inventar mit Freigabe **aktiv** einen Verleih eröffnen.
- Auf Inventar mit Freigabe **intern** eröffnen **Materialwart*innen** und Personen mit **Leserecht** (siehe D0001) Verleihe; Lesen heißt auch Anfragen.
- **Archiviertes** Inventar: keine neuen Verleihe.
- Mehrere **Entwürfe** und mehrere laufende Verleihe pro Person/Inventar sind erlaubt.

**Anwendung: Neuer Verleih**

- **Neuer Verleih** erzeugt immer den **Entwurf des Erstellers** (Ersteller ist zunächst Ausleihende*r).
- Bereitet eine Materialwart*in für jemand anderen vor: Stammdaten und Material im Entwurf, **Ausleihende*n** wählen, **Speichern** → Übergabe:
  - Phase **Prüfung** (`review`),
  - Materialwart*in wird **Ansprechperson**,
  - vorhandene Positionen werden **angefragt**.
- Nur die Auswahl im Entwurf **ohne Speichern** übergeben noch nicht.

**Platzhalter-Benutzer**

- Person ohne Login nur als Platzhalter für eine Ausleihe: keine Berechtigung, keine Ansprechperson.
- **Merge** Platzhalter auf Login-Konto: Verleihe werden umgeschrieben, Platzhalter gelöscht.

(Die API kann einen Verleih weiterhin direkt mit `borrowerUserId` anlegen — z. B. Tests/Import; die UI folgt dem Entwurfs-Weg.)

## Konsequenzen

- UI: keine Auswahl der Ausleihenden in der Verleihliste; Übergabe beim Speichern in Stammdaten.
- Backend: `hand_draft_to_borrower` bei Übergabe; Wunschtermine können in feste Termine kopiert werden.

## Nicht-Ziele

- Gruppen als eigene Login-Akteure.
