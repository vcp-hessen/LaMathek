---
id: D0001
titel: Geltungsbereich und Rollen
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [VCP Hessen, Materialwart*in, Berechtigung, Ausleihende*r, Gruppe]
---

# D0001 — Geltungsbereich und Rollen

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **VCP Hessen**, **Materialwart*in**, **Berechtigung**, **Ausleihende*r**, **Gruppe**.

## Kontext

LaMathek bildet Material ab, das VCP Hessen hält — nicht Material von Stämmen, Bezirken oder dem Bund.

## Entscheidung

- Jede angemeldete Person ist ein **Benutzer** (user).
- Eine **Materialwart*in** verwaltet nur **Inventare**, für die sie eine **Berechtigung** (Paar Benutzer–Inventar) hat.
- **Superuser*innen** verwalten die Installation und können Berechtigungen auf jedem Inventar vergeben; Materialwart*innen mit Berechtigung dürfen Berechtigungen nur auf **ihrem** Inventar vergeben oder entziehen.
- Funktionsbezeichnungen im Verein sind keine Rollen in LaMathek (z. B. Jugendbildungsreferent*in, Geschäftsführerin, FSJler erhalten eine Berechtigung auf dem Inventar Landesbüro).
- Bei einem **Verleih** kann jede angemeldete Person **Ausleihende*r** sein.
- Eine **Gruppe** (Pfadfindergruppe) nutzt LaMathek nicht als Akteur.

## Konsequenzen

- Berechtigungen und Superuser-Flags in der Datenbank und API; keine Job-Titel-Rollen.
- UI und Rechteprüfung orientieren sich an Inventar-Berechtigung und Superuser-Status.

## Nicht-Ziele

- Rollenmodell für Stamm/Bezirk/Bund-Material außerhalb VCP Hessen.
