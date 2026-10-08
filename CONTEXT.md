# LaMathek

LaMathek is the record of material held by VCP Hessen. Headwords are the German terms. The English word on each term is the name for code and for the English locale.

## Language

**VCP Hessen**:
The Landesverband Hessen of the Verband Christlicher Pfadfinderinnen und Pfadfinder. This installation tracks material held by VCP Hessen.
_English_: VCP Hessen
_Avoid_: the association, the customer, Hessen

**Material**:
Something VCP Hessen holds and tracks. It is either a Stück or a Bestand, depending on its Materialart.
_English_: material
_Avoid_: equipment, stuff, item, asset

**Materialart**:
A configurable kind of material, tracked either as individual Stücke or as a Bestand in each Inventar. Stücke of one Materialart fit together, so a normal Kohte and a Wanderkohte are two Materialarten.
_English_: material type
_Avoid_: Artikel, Sorte, Kategorie

**Inventar**:
A collection of material kept at one place. The Landesmaterial on Donnerskopf is one Inventar; the Landesbüro is another.
_English_: inventory
_Avoid_: Standort, Lager, location

**Stück**:
One identified item of a Materialart, kept in one Inventar. It sits in at most one Set, and can be moved to another Set or sit in none.
_English_: piece
_Avoid_: Einzelstück, Exemplar

**Bestand**:
A counted quantity of one Materialart in one Inventar. A Set reserves a single quantity from it; the individual pieces are not identified.
_English_: stock
_Avoid_: Menge, Vorrat

**Variante**:
A distinction within one Materialart, defined on the Materialart and stored on the Stück. Kohtenplanen of one Materialart vary by Randstreifen (0, 10, 35, or 70 cm); those lengths still fit together.
_English_: variant
_Avoid_: version, Ausführung, option

**Set**:
A named group of material in one Inventar. It has a Zuordnung, and it can list optionals.
_English_: set
_Avoid_: Satz, Garnitur, kit, bundle

**Zuordnung**:
The fixed belonging of Stücke and Bestand to a Set. In the Jurte example, the Zuordnung is twelve Vierecksplanen, six Kohtenplanen, and one Abdeckplane.
_English_: assignment
_Avoid_: membership, kit list

**Optional**:
A Stück or a single quantity from a Bestand listed on a Set, outside its Zuordnung. That quantity is reserved from the Inventar's Bestand and shown on a Verleih of the Set as material that may still be handed out.
_English_: optional
_Avoid_: Zubehör, Zusatz, Vorschlag

**Schaden**:
A recorded harm on a Stück, kept after repair. Severe Schaden means that Stück must not be handed out.
_English_: damage
_Avoid_: Defekt, Zustand, condition

**Reparatur**:
The repair of a Schaden, kept with that Schaden.
_English_: repair
_Avoid_: fix, Instandsetzung

**Gruppe**:
A scouting group on whose behalf material is handed to a Verantwortliche. A Gruppe does not use LaMathek.
_English_: group
_Avoid_: Stamm, team, borrower

**Verantwortliche**:
The person material is handed to, and who is in charge of it, on behalf of a Gruppe. Verantwortliche is also a user role.
_English_: person in charge
_Avoid_: Empfänger, borrower, contact

**Veranstaltung**:
An occasion a Verleih usually belongs to. A Verleih can exist without one.
_English_: event
_Avoid_: Lager, camp, Fahrt

**Verleih**:
Material for a Verantwortliche on behalf of a Gruppe for a short time, usually about two weeks. It can be recorded before handout, usually belongs to a Veranstaltung, and ends with a Rückgabe.
_English_: loan
_Avoid_: Ausleihe, rental, booking, reservation

**Rückgabe**:
Material from a Verleih or a Dauerleihgabe coming back. It can be partial.
_English_: return
_Avoid_: Rücknahme, check-in

**Verlust**:
Material that was handed out and is recorded as not brought back.
_English_: loss
_Avoid_: Schwund, Fehlmenge, open loan

**Dauerleihgabe**:
Material handed to a Verantwortliche on behalf of a Gruppe for a long time. It stays held by VCP Hessen.
_English_: permanent loan
_Avoid_: Starterset, starter set, Grundausstattung

**Materialwart**:
A user role for someone who manages material in the Inventare covered by their Berechtigungen. On the Donnerskopf Inventar, this office is the Beauftragte für Landesmaterial.
_English_: quartermaster
_Avoid_: Beauftragte für Landesmaterial, Materialteam, admin, staff

**Berechtigung**:
A user's right to manage one Inventar. A job such as Jugendbildungsreferent, Geschäftsführerin, or FSJler is not a role; that person gets a Berechtigung on the Landesbüro Inventar.
_English_: permission
_Avoid_: Rolle, job title
