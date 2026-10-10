# Software decisions

What LaMathek is for. How it is built lives in [docs/adr](./adr/). Domain language lives in [CONTEXT.md](../CONTEXT.md).

## Decided

LaMathek keeps track of material held by VCP Hessen. This installation does not track material held by Stämme, Bezirke, or the Bund.

The user roles are Materialwart*in and Verantwortliche*r (code: `materialwart`, `verantwortliche`). A Materialwart*in manages only the Inventare covered by their Berechtigungen. Job titles are not roles: the Jugendbildungsreferent, the Geschäftsführerin, and an FSJler get a Berechtigung on the Landesbüro Inventar. A Gruppe does not use LaMathek.

An Inventar is the material kept at one place. Donnerskopf holds the Landesmaterial. The Landesbüro holds material such as a Beamer, board games, and button machines. A Set, an Einzelteil, and a Menge each belong to one Inventar.

Materialarten are configurable in the application. Each Materialart is tracked either as individual Einzelteile or as a Menge in each Inventar, and it may define any number of Variantenbezeichner (each with an ordered list of values). Einzelteile store one value per Bezeichner; Mengenposten may leave a Bezeichner unset. Einzelteile of one Materialart fit together. A normal Kohte and a Wanderkohte do not, so they are two Materialarten. Different Randstreifen (0, 10, 35, or 70 cm) still fit together, so they are Varianten of one Kohtenplane Materialart. Poles and pegs are each a Menge, split into Mengenposten (Anzahl, optional Variante, optional Bezeichnung). A storage box is only a Bezeichnung on a Posten, not an Einzelteil. Most other material is tracked as Einzelteile.

A Set has a Zuordnung of Einzelteile and Mengen, and it can list optionals. An Einzelteil sits in at most one Set and can be moved to another Set or sit in none. An Anzahl a Set names from a Menge, as Zuordnung or as optional, is reserved from the sum of that Menge's Mengenposten. Set and Verleih lines do not name a Variante. In the Jurte example, the Zuordnung is twelve Vierecksplanen, six Kohtenplanen, and one Abdeckplane. Twelve Seile, twelve Heringe, twelve Stangen, and Mittelstangen are optionals on that Set, each a single Anzahl reserved from its Menge, and not part of the Zuordnung.

A Verleih of the Set shows those optionals as material that may still be handed out. A Verleih can also hand out a single Einzelteil, or an Anzahl from a Menge, on its own. It can be recorded before handout, so an Einzelteil or Set on it can still be changed.

Material is handed to a Verantwortliche*r, who is in charge of it, on behalf of a Gruppe. A Materialwart*in records that. The common case is a Verleih of about two weeks and belongs to a Veranstaltung. A Verleih can exist without a Veranstaltung.

A Rückgabe can be partial. Material that is not brought back is a Verlust and stays recorded. Material that is out is not handed out again until that Rückgabe. Schaden sits on an Einzelteil. Severe Schaden, such as a large cut in a canvas, means that Einzelteil must not be handed out, so a Set that has it in its Zuordnung cannot go out as a whole. A Reparatur is kept with the Schaden. After repair the Einzelteil can be handed out again, and the log stays.

A Dauerleihgabe hands material to a Verantwortliche*r on behalf of a Gruppe for a long time. The material stays held by VCP Hessen. Giving it to the Gruppe, or taking it back, is an edge.

The interface is German. A public catalogue and reservation requests are later ideas, not part of the first version.
