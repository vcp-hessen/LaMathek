# Domänen-Entscheidungen (Produktregeln)

Hier stehen **verbindliche Produktregeln** für LaMathek — wer darf was, Verleih-Workflow, Mail, Verfügbarkeit. Die Texte sind **Deutsch**.

## Wo was steht

| Ebene | Ort | Inhalt |
|--------|-----|--------|
| Begriffe | [CONTEXT.md](../../CONTEXT.md) | Glossar (keine Workflow-Regeln) |
| Produktregeln | `docs/domain/D*.md` | Verhalten, Rollen, Phasen |
| Index | [software.md](../software.md) | Kurzüberblick + Tabelle aller Records |
| Technik | [adr/](../adr/) | Stack, OIDC, Fotos auf Disk (Englisch) |

**Technische** Architekturentscheidungen → `docs/adr/`. **Produktverhalten** → hier.

## Für Agenten und Entwickler

1. Begriffe aus **CONTEXT** lesen, nicht in Domain-Dateien neu definieren.
2. Bei Änderungen an Verleih, Berechtigungen, Mail oder Verfügbarkeit: passenden **D-Record** lesen und aktualisieren.
3. Neue Begriffe → CONTEXT. Neue oder geänderte Regeln → ein D-Record (+ ggf. Tests in `server/tests/`).
4. Bei Grundsatzwechsel: alten Record auf `status: superseded` setzen, neuen Record mit `ersetzt: D00xx` anlegen.

## Lesereihenfolge Verleih

| Thema | Record |
|--------|--------|
| Anlegen, Entwurf, Übergabe an Ausleihende*n | [D0003](D0003-verleih-creation-handoff.md) |
| Termine, Dauerleihgabe | [D0004](D0004-verleih-dates-permanent.md) |
| Telefon, Ansprechperson | [D0005](D0005-contact-phone.md) |
| Positionsstatus, Korrektur, Ersatz | [D0006](D0006-line-status-corrections.md) |
| Verfügbarkeit, Bestätigung | [D0007](D0007-availability-confirmation.md) |
| Zurückziehen, Positionen nachziehen | [D0008](D0008-line-withdraw-cancel-add.md) |
| Abholung, Rückgabe, Verlust, Abschluss | [D0009](D0009-pickup-return-handover-loss.md) |
| Abhol-/Rückgabeinfo, Fotos | [D0010](D0010-pickup-return-info-photos.md) |
| Phasen, Mail, Chevron-Aktionen, Löschen | [D0012](D0012-workflow-phase-mail.md) |
| Journal (Verlauf) | [D0014](D0014-loan-journal.md) |
| Kalender, iCal-Abos | [D0015](D0015-calendar.md) |
| Startseite | [D0016](D0016-dashboard.md) |

Material, Inventar, Sets, Varianten: [D0002](D0002-inventar-material-sets.md). Rollen und Rechte: [D0001](D0001-scope-roles.md). Schaden und Totalverlust: [D0011](D0011-damage.md). Befehlspalette und Hilfe: [D0017](D0017-command-palette-help.md).

## Alle Records

| ID | Titel | Datei |
|----|--------|--------|
| D0001 | Geltungsbereich und Rollen | [D0001-scope-roles.md](D0001-scope-roles.md) |
| D0002 | Inventar, Material und Sets | [D0002-inventar-material-sets.md](D0002-inventar-material-sets.md) |
| D0003 | Verleih anlegen und Übergabe | [D0003-verleih-creation-handoff.md](D0003-verleih-creation-handoff.md) |
| D0004 | Termine und Dauerleihgabe | [D0004-verleih-dates-permanent.md](D0004-verleih-dates-permanent.md) |
| D0005 | Telefon und Ansprechperson | [D0005-contact-phone.md](D0005-contact-phone.md) |
| D0006 | Positionsstatus und Korrekturen | [D0006-line-status-corrections.md](D0006-line-status-corrections.md) |
| D0007 | Verfügbarkeit und Bestätigung | [D0007-availability-confirmation.md](D0007-availability-confirmation.md) |
| D0008 | Zurückziehen und Positionen nachziehen | [D0008-line-withdraw-cancel-add.md](D0008-line-withdraw-cancel-add.md) |
| D0009 | Abholung, Rückgabe, Verlust | [D0009-pickup-return-handover-loss.md](D0009-pickup-return-handover-loss.md) |
| D0010 | Abhol- und Rückgabeinformation | [D0010-pickup-return-info-photos.md](D0010-pickup-return-info-photos.md) |
| D0011 | Schaden | [D0011-damage.md](D0011-damage.md) |
| D0012 | Workflow-Phasen und Mail | [D0012-workflow-phase-mail.md](D0012-workflow-phase-mail.md) |
| D0013 | Oberfläche und Roadmap | [D0013-ui-language-roadmap.md](D0013-ui-language-roadmap.md) |
| D0014 | Verleih-Journal | [D0014-loan-journal.md](D0014-loan-journal.md) |
| D0015 | Kalender | [D0015-calendar.md](D0015-calendar.md) |
| D0016 | Startseite | [D0016-dashboard.md](D0016-dashboard.md) |
| D0017 | Befehlspalette und Kontext-Hilfe | [D0017-command-palette-help.md](D0017-command-palette-help.md) |

Vorlage für neue Records: [_template.md](_template.md).
