# LaMathek

LaMathek is the record of material held by VCP Hessen. Headwords are the German terms. The English word on each term is the name for the code and for the English locale.

## Documentation

| What | Where |
|------|--------|
| **Terms** (this file) | Definitions only — not workflow rules |
| **Product rules** | [docs/domain/README.md](docs/domain/README.md) (German, D0001–D0017) |
| **Index** | [docs/software.md](docs/software.md) |
| **Technical stack** | [docs/adr/](docs/adr/) |

When contributing: new or changed **terms** → update CONTEXT. New or changed **behavior** → update the matching `docs/domain/D*.md` record (and tests if applicable). Do not duplicate rules in CONTEXT.

## Language

**VCP Hessen**:
The Landesverband Hessen of the Verband Christlicher Pfadfinderinnen und Pfadfinder. This installation tracks material held by VCP Hessen.
_English_: VCP Hessen
_Avoid_: the association, the customer, Hessen

**Material**:
Something VCP Hessen holds and tracks. It is either an Einzelteil or a Menge, depending on its Materialart.
_English_: material
_Avoid_: equipment, stuff, item, asset

**Materialart**:
A configurable kind of material, tracked either as individual Einzelteile or as a Menge in each Inventar. Einzelteile of one Materialart fit together, so a normal Kohte and a Wanderkohte are two Materialarten. A Materialart may have a short name, description, unit (for Menge), consumable flag, an optional Kategorie, and optional Hersteller and Modell that apply to all Stücke and Mengenposten of that art.
_English_: material type
_Avoid_: Artikel, Sorte

**Hersteller** (an der Materialart):
The maker name shared by every Einzelteil and Mengenposten of that Materialart, when recorded.
_English_: manufacturer
_Avoid_: brand (unless that is what is meant), supplier

**Modell** (an der Materialart):
The model designation shared by every Einzelteil and Mengenposten of that Materialart, when recorded.
_English_: model name
_Avoid_: model (SQLAlchemy class name in code), SKU

**Kategorie**:
An optional label for grouping Materialarten across the whole installation (for example Zelt, Küche, Spiel). It is not the Verleih Gruppe.
_English_: category
_Avoid_: Gruppe, Sorte, Bereich

**Inventar**:
A collection of material kept at one place. The Landesmaterial on Donnerskopf is one Inventar; the Landesbüro is another. An Inventar may have an optional address, map coordinates, and a note (for access, keys, and on-site hints). Each Inventar has a **Freigabe**: **intern** (only users with a Berechtigung on that Inventar, either to manage or a Leserecht), **aktiv** (any signed-in user may read material, Sets, photos, and notes; only Materialwart*innen manage Verleih and data), or **archiviert** (like intern; kept for history, not offered in the active catalogue). Material requests and anonymous access are not part of the app yet.
_English_: inventory
_Avoid_: Standort, Lager, location

**Einzelteil**:
One identified item of a Materialart, kept in one Inventar. It sits in at most one Set, and can be moved to another Set or sit in none. It may carry optional Anschaffungsjahr, Notiz, Herkunft, Neuwert, Seriennummer, and a Status (im Bestand or aussortiert). Aussortiertes stays in the record, drops out of the normal list, and cannot be newly handed out on a Verleih.
_English_: piece
_Avoid_: Einzelstück, Exemplar, Stück (as the named item; Stück remains valid as a unit of measure)

**Anschaffungsjahr**:
The calendar year the Einzelteil or Mengenposten was acquired, when known.
_English_: acquired year
_Avoid_: purchase date, Baujahr (unless that is what is meant)

**Notiz** (am Stück bzw. Posten):
Free text about the Einzelteil or Mengenposten itself. Not the same as the Notiz on a Schaden.
_English_: note
_Avoid_: comment on damage

**Herkunft**:
How the Einzelteil or Mengenposten was obtained (donor, dealer, built in-house), as free text when recorded.
_English_: source
_Avoid_: owner, supplier enum

**Status** (im Bestand / aussortiert):
Whether the Einzelteil or Mengenposten is active in the Inventar or retired from use. Retired is not deletion; Verleih and Schaden states stay separate.
_English_: item status (active or retired)
_Avoid_: deleted, lost

**Neuwert**:
The new replacement value of the Einzelteil or Mengenposten in euro with two decimal places, stored in cents when recorded.
_English_: new value
_Avoid_: Zeitwert, replacement value (field name in code)

**Seriennummer**:
The manufacturer's serial number on the Einzelteil or Mengenposten, when recorded.
_English_: serial number
_Avoid_: inventory number (internal name is separate)

**Menge**:
A Materialart tracked by count in one Inventar, without naming individual items. Its Anzahl is the sum of its Mengenposten. A Set lists an Anzahl from it without reserving it; only confirmed Verleihe occupy stock, per day.
_English_: stock
_Avoid_: Bestand, Vorrat

**Mengenposten**:
One counted portion of a Menge: an Anzahl of exactly one Variante (every Variantenbezeichner of the Materialart is set, never a mix) and an optional Bezeichnung (for example a box name). Several Posten of the same Variante may exist and add up. A box is not an Einzelteil. It may carry the same optional Angaben and Status as an Einzelteil; a retired Posten's Anzahl does not count toward available stock.
_English_: stock lot
_Avoid_: Kiste, Behälter, Einzelteil (for the container)

**Anzahl**:
The counted value of a Menge (for example how many Heringe are in the Inventar or on a Verleih line). Not the Materialart itself.
_English_: quantity
_Avoid_: Menge (for the numeric field; Menge is the tracking kind)

**Variantenbezeichner**:
One named axis of distinction on a Materialart (for example Länge or Farbe), each with an ordered list of allowed values. A Materialart may have any number of Variantenbezeichner.
_English_: variant dimension
_Avoid_: Attribut, Merkmal, option group

**Variante**:
On an Einzelteil, one chosen value per Variantenbezeichner of its Materialart (a combination). On a Mengenposten, a Set line of a Menge and a Verleih Position of a Menge, likewise one value per Variantenbezeichner; Mengen are counted and booked per Variante.
_English_: variant
_Avoid_: version, Ausführung, option

**Set**:
A named group of material in one Inventar. It has a Zuordnung, and it can list optionals. It may have a short name (Kürzel), unique per Inventar, used for naming Einzelteile in batch creation.
_English_: set
_Avoid_: Satz, Garnitur, kit, bundle

**Zuordnung**:
The fixed belonging of Einzelteile and Mengen to a Set. In the Jurte example, the Zuordnung is twelve Vierecksplanen, six Kohtenplanen, and one Abdeckplane.
_English_: assignment
_Avoid_: membership, kit list

**Optional**:
An Einzelteil or an Anzahl from a Menge listed on a Set, outside its Zuordnung. It reserves nothing; it is shown on a Verleih of the Set as material that may still be handed out.
_English_: optional
_Avoid_: Zubehör, Zusatz, Vorschlag

**Schaden**:
A recorded harm on an Einzelteil, kept after repair. Severe Schaden means that Einzelteil must not be handed out. A lost Einzelteil is recorded as a Totalverlust, not as a Schaden.
_English_: damage
_Avoid_: Defekt, Zustand, condition

**Foto**:
An image file stored beside the database, linked to an Einzelteil, Mengenposten, Set, Materialart, Schaden, Inventar, Abholinformation, or Rückgabeinformation on a Verleih. The first Foto in sort order is the cover image where applicable; Einzelteil and Mengenposten lists may show the Materialart reference Foto when they have none of their own. Verleih list thumbnails use Abhol- or Rückgabe-Fotos when present.
_English_: photo
_Avoid_: Bild, Anhang, attachment

**Reparatur**:
The repair of a Schaden, kept with that Schaden. A Totalverlust is never repaired; it ends as found again, written off or a mistake.
_English_: repair
_Avoid_: fix, Instandsetzung

**Gruppe**:
A scouting group on whose behalf material is handed to an Ausleihende*r. A Gruppe does not use LaMathek.
_English_: group
_Avoid_: Stamm, team, borrower

**Ausleihende**:
The person a Verleih is for, on behalf of a Gruppe. Any signed-in user may be that person. In the German UI: **Ausleihende*r**.
_English_: borrower
_Avoid_: Verantwortliche*r, Empfänger, contact

**Veranstaltung**:
An occasion a Verleih usually belongs to. A Verleih can exist without one.
_English_: event
_Avoid_: Lager, camp, Fahrt

**Verleih**:
Material from one Inventar for an Ausleihende*r on behalf of a Gruppe. It usually belongs to a Veranstaltung.
_English_: loan
_Avoid_: Ausleihe, rental, booking, reservation

**Position** (am Verleih):
One Einzelteil, or an Anzahl of a Menge, on a Verleih.
_English_: loan line
_Avoid_: Mengenposten, Zeile

**Ansprechperson**:
The Materialwart*in named on a Verleih for the Ausleihende*r to reach.
_English_: loan contact
_Avoid_: Ausleihende*r, Verantwortliche*r

**Abholinformation**:
Where and how the material of a Verleih can be picked up. Free text, and it may include Fotos.
_English_: pickup note
_Avoid_: Abholort

**Rückgabeinformation**:
Where and how the material of a Verleih comes back. Free text, and it may include Fotos.
_English_: return note
_Avoid_: Abstellort

**Rückgabe**:
Material of a Verleih coming back. It can be partial.
_English_: return
_Avoid_: Rücknahme, check-in

**Übernahme**:
A Materialwart*in's acceptance of returned material back into the Inventar.
_English_: restock
_Avoid_: Rückgabe

**Verlust**:
Material that was handed out and is recorded as not brought back. It is recorded as an event (on the Einzelteil as Totalverlust, on a Mengenposten with its Anzahl) and later found again, written off or cancelled as a mistake; material itself is never deleted for it.
_English_: loss
_Avoid_: Schwund, Fehlmenge, open loan

**Verbrauch**:
The part of a consumable Menge (for example Flyer) that a Verleih used up. Recorded at Übernahme; it lowers the Mengenposten's Anzahl at once.
_English_: consumption
_Avoid_: Verlust (for consumables), Schwund

**Totalverlust**:
The Verlust of an Einzelteil, recorded as an event on the piece. While open, the piece cannot be lent. It ends as found again, written off (the piece is retired) or a mistake.
_English_: total loss
_Avoid_: Schaden (for a lost piece), gelöscht

**Grund** (am Verleih):
The explanation required when a Position ends short of handover or return, or when its Anzahl shrinks.
_English_: reason
_Avoid_: Notiz

**Notiz** (an der Position):
Free text on a Position. Separate from the Grund, and from the Notiz on a Stück or Posten.
_English_: line note
_Avoid_: Grund

**Dauerleihgabe**:
A Verleih explicitly marked as having no return date. The material stays held by VCP Hessen.
_English_: permanent loan
_Avoid_: Starterset, starter set, Grundausstattung

**Materialwart**:
Someone who manages material in the Inventare covered by their Berechtigungen. On the Donnerskopf Inventar, this office is the Beauftragte für Landesmaterial. In the German UI: **Materialwart*in**. There is no separate global flag; a person is a Materialwart*in only through a Berechtigung on an Inventar.
_English_: quartermaster
_Avoid_: Beauftragte für Landesmaterial, Materialteam, admin, staff

**Berechtigung**:
A user's right on one Inventar (a user–Inventar pair), either to **manage** it or a **Leserecht**. Only users with a login get one. Superusers and Materialwarte who already have a Berechtigung on that Inventar may grant or revoke Berechtigungen there. A job such as Jugendbildungsreferent, Geschäftsführerin, or FSJler is not a role; that person gets a Berechtigung on the Landesbüro Inventar. **Ausleihende*r** on a Verleih is the person the material is for, not a user role in the database.
_English_: permission
_Avoid_: Rolle, job title

**Leserecht**:
A Berechtigung to read an internal Inventar (material, Sets, photos) and to request Verleihe from it, without managing anything. Active Inventare need no Leserecht.
_English_: read permission
_Avoid_: Gastzugang, viewer role

**Journal**:
The append-only history of a Verleih and of an Einzelteil: who did what to which Position, when, and why.
_English_: journal
_Avoid_: Log, Protokoll, audit (the audit log is for superuser actions)

**Kalender-Abo**:
A named, revocable link with which a calendar program shows Verleihe (own ones, as Ansprechperson, or all of an Inventar).
_English_: calendar feed
_Avoid_: Export, Sync

**Mailversand**:
Mails about a Verleih are queued with the change they report and sent by the server afterwards, with retries. A step never waits for a mail.
_English_: mail outbox
_Avoid_: Benachrichtigung (for the mechanism), Newsletter
