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
- Eine **Materialwart*in** verwaltet nur **Inventare**, für die sie eine **Berechtigung** (Paar Benutzer–Inventar) mit der Rolle **verwalten** hat.
- Die Berechtigung mit der Rolle **Leserecht** erlaubt auf einem Inventar mit Freigabe **intern** das Lesen von Material, Sets und Fotos und das **Anfragen** eigener Verleihe. Verwalten darf sie nichts. Auf **aktiven** Inventaren braucht niemand ein Leserecht.
- Berechtigungen bekommen nur Personen mit Login. **Lokale Personen** (ohne Login, nur als Ausleihende*r angelegt) haben keine Berechtigung.
- **Superuser*innen** verwalten die Installation und können Berechtigungen auf jedem Inventar vergeben; Materialwart*innen mit Berechtigung dürfen Berechtigungen nur auf **ihrem** Inventar vergeben oder entziehen.
- Funktionsbezeichnungen im Verein sind keine Rollen in LaMathek (z. B. Jugendbildungsreferent*in, Geschäftsführerin, FSJler erhalten eine Berechtigung auf dem Inventar Landesbüro).
- Bei einem **Verleih** kann jede angemeldete Person **Ausleihende*r** sein.
- **Kontaktdaten** (E-Mail, Telefon): Personen mit Login pflegen ihre eigenen; die E-Mail kommt bei jeder Anmeldung vom Login-Anbieter. Lokale Personen bearbeiten Superuser*innen und Materialwart*innen eines Inventars, in dem die Person einen Verleih hat (oder, solange sie noch keinen hat, jede Materialwart*in). Mails und PDFs gehen an diese Adresse, deshalb darf niemand fremde Adressen umbiegen.
- **Zusammenführen** einer lokalen Person in ein Login-Konto dürfen nur Superuser*innen: es verschiebt Verleihe über Inventargrenzen. Verleihe, Ansprechperson, Journal und Audit wandern mit; der Vorgang steht im Audit-Log.
- **Superuser*innen** können andere Personen **imitieren** (mit Grund, im Audit-Log). Bei jeder Anfrage wird geprüft, ob die Person noch Superuser*in ist; eine neue Anmeldung beendet die Imitation. Das Journal nennt bei imitierten Aktionen beide.
- Eine **Gruppe** (Pfadfindergruppe) nutzt LaMathek nicht als Akteur.

## Konsequenzen

- Berechtigungen und Superuser-Flags in der Datenbank und API; keine Job-Titel-Rollen.
- UI und Rechteprüfung orientieren sich an Inventar-Berechtigung und Superuser-Status.

## Nicht-Ziele

- Rollenmodell für Stamm/Bezirk/Bund-Material außerhalb VCP Hessen.
