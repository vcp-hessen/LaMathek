---
id: D0005
titel: Telefon und Ansprechperson
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Ansprechperson, Ausleihende*r]
---

# D0005 — Telefon und Ansprechperson

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Ansprechperson**, **Ausleihende*r**.

## Kontext

Erreichbarkeit für Abholung und Rückfragen während des Verleihs.

## Entscheidung

- Jede Person kann eine **Telefonnummer** am Benutzerkonto speichern.
- Ein **Entwurf** darf existieren, bevor eine Nummer hinterlegt ist.
- **Anfrage** und **Bestätigung** erfordern eine Nummer bei der Ausleihenden.
- Materialwart*innen des Inventars sehen die Nummer der Ausleihenden; die Ausleihende*r sieht die Nummer der **Ansprechperson**.
- Sonst gibt die API keine Telefonnummern heraus: Personenlisten, Auswahllisten und Journale zeigen Namen (und in Listen für Materialwart*innen die E-Mail), aber keine Nummer. Ausnahme: Personen, deren Kontaktdaten der*die Betrachter*in bearbeiten darf (D0001).
- **Ansprechperson** ist eine Materialwart*in des Inventars, von den Materialwart*innen benannt.
- **Bestätigung** wartet, bis eine Ansprechperson gesetzt ist.

## Konsequenzen

- API/UI: `contactUserId`, Telefon in Serializer je nach Rolle sichtbar.
- Tests zu Anfrage ohne Telefon / ohne Ansprechperson.
