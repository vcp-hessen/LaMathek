# Software decisions

What LaMathek is for. How it is built lives in [docs/adr](./adr/). Domain language lives in [CONTEXT.md](../CONTEXT.md).

## Decided

LaMathek keeps track of material held by VCP Hessen. This installation does not track material held by Stämme, Bezirke, or the Bund.

Anyone who signs in is a user. A **Materialwart*in** manages only Inventare where they have a **Berechtigung** (user–Inventar pair). Superusers manage the installation and may grant Berechtigungen on any Inventar; Materialwarte with a Berechtigung may grant or revoke Berechtigungen on that Inventar only. Job titles are not roles: the Jugendbildungsreferent, the Geschäftsführerin, and an FSJler get a Berechtigung on the Landesbüro Inventar. At a Verleih, any signed-in user may be the **Ausleihende*r**. A Gruppe does not use LaMathek.

An Inventar is the material kept at one place. Donnerskopf holds the Landesmaterial. The Landesbüro holds material such as a Beamer, board games, and button machines. A Set, an Einzelteil, and a Menge each belong to one Inventar.

Materialarten are configurable in the application. Each Materialart is tracked either as individual Einzelteile or as a Menge in each Inventar, and it may define any number of Variantenbezeichner (each with an ordered list of values). Einzelteile store one value per Bezeichner; Mengenposten may leave a Bezeichner unset. Einzelteile of one Materialart fit together. A normal Kohte and a Wanderkohte do not, so they are two Materialarten. Different Randstreifen (0, 10, 35, or 70 cm) still fit together, so they are Varianten of one Kohtenplane Materialart. Poles and pegs are each a Menge, split into Mengenposten (Anzahl, optional Variante, optional Bezeichnung). A storage box is only a Bezeichnung on a Posten, not an Einzelteil. Most other material is tracked as Einzelteile.

A Set has a Zuordnung of Einzelteile and Mengen, and it can list optionals. An Einzelteil sits in at most one Set and can be moved to another Set or sit in none. An Anzahl a Set names from a Menge, as Zuordnung or as optional, is reserved from the sum of that Menge's Mengenposten. Set and Verleih lines do not name a Variante. In the Jurte example, the Zuordnung is twelve Vierecksplanen, six Kohtenplanen, and one Abdeckplane. Twelve Seile, twelve Heringe, twelve Stangen, and Mittelstangen are optionals on that Set, each a single Anzahl reserved from its Menge, and not part of the Zuordnung.

A Verleih belongs to one Inventar. It is material for an Ausleihende*r on behalf of a Gruppe, and it usually belongs to a Veranstaltung. It can exist without a Veranstaltung. An Ausleihende*r may open one on an Inventar with Freigabe aktiv. A Materialwart*in may open one for an Ausleihende*r, including on an Inventar with Freigabe intern. An archived Inventar takes no new Verleih. Each person has at most one Entwurf per Inventar. Several submitted Verleihe at once are fine.

Adding a Set copies its Zuordnung into Positionen, plus one Position for each Optional someone selects. The Set name stays on those Positionen as Herkunft. A Verleih can also take a single Einzelteil, or an Anzahl from a Menge. A consumable Menge skips Rückgabe and Übernahme; that Position ends once it is abgeholt. Material with severe Schaden, and ausgesondertes material, cannot be requested.

The Ausleihende*r proposes one Abholtermin for the whole Verleih, and one Rückgabetermin, with the Anfrage. A Materialwart*in confirms or changes those dates, and is the only one who can change them afterwards. A Dauerleihgabe is an explicit mark on the Verleih. The Ausleihende*r may set it on the Entwurf. A Materialwart*in confirms it with the first Freigabe or sets it. Afterwards only a Materialwart*in changes the mark. While it is set, the Rückgabetermin stays empty. Clearing the mark includes setting a Rückgabetermin. Abholung, Rückgabe, Übernahme, and Verlust still apply when that material comes back.

Each user may store a phone number. The Entwurf may exist before that number is there. Anfrage and Bestätigung require a number on the Ausleihende*r. On that Verleih, the Materialwart*innen of the Inventar see the Ausleihende*r's number, and the Ausleihende*r sees the Ansprechperson's number. The Ansprechperson is a Materialwart*in of that Inventar, named by the Materialwart*innen. Bestätigung waits until one is set.

A Position moves on its own: Entwurf, angefragt, bestätigt, gepackt, abgeholt, zurückgemeldet, übernommen. It can end early as nicht verfügbar, nicht gepackt, nicht abgeholt, or nicht zurückgebracht. An early end, and any shrink of an Anzahl, needs a Grund. A Notiz may sit on a Position at any time, including while it waits. Other Positionen move on. Ersatz is a new bestätigte Position; the original ends as nicht verfügbar, with a Grund.

Material stays available to other Verleihe until a Position is bestätigt. It stays blocked until an early end, a Verlust, or the Übernahme. The same Einzelteil may sit on several Entwürfe. A second Bestätigung fails when another Verleih already holds it.

The Ausleihende*r may take an angefragte or bestätigte Position off the Verleih before it is gepackt. It stays visible as zurückgezogen, the material is free at once, and Zurückziehen needs no Grund. After packing, a Materialwart*in may end it as nicht gepackt, with a Grund, until Abholung. Further Positionen may be added after the first Bestätigung. They start as angefragt, share the Verleih's dates, and become bestätigt only through a Materialwart*in.

Abholung and Rückgabe can happen without the two people meeting. The Ausleihende*r marks abgeholt, nicht abgeholt, and whether each Position came back. A Materialwart*in marks gepackt and übernommen, and may also mark abgeholt, nicht abgeholt, and the Rückgabe. A Materialwart*in's mark is enough on its own. Nicht zurückgebracht is a Verlust and writes the Anzahl out of stock. When the Ausleihende*r reports a return and the material is missing, the Materialwart*in records a Verlust. The Verleih is closed when every Position has ended: übernommen, Verlust, an early end, zurückgezogen, or abgeholt for a consumable.

Abholinformation and Rückgabeinformation sit on the Verleih. Each is optional free text and may include Fotos. A Materialwart*in writes the Abholinformation, for example while packing. A Materialwart*in may write the Rückgabeinformation in advance, and the Ausleihende*r adds to it when bringing the material back.

Schaden sits on an Einzelteil. Severe Schaden, such as a large cut in a canvas, means that Einzelteil must not go out, so a Set that has it in its Zuordnung cannot go out as a whole. A Reparatur is kept with the Schaden. After repair the Einzelteil can go out again, and the log stays.

Each completed action sends one mail, covering every Position included in that action. The Ausleihende*r receives a receipt of the Anfrage, and a mail when a Materialwart*in changes the Verleih: Bestätigung, Ablehnung, Ersatz, dates, Ansprechperson, packing, Übernahme, Verlust, Abholinformation. The Anfrage goes to the Materialwart*innen of the Inventar. After an Ansprechperson is set, mails about the Ausleihende*r's actions go to the Ansprechperson, with the other Materialwart*innen of that Inventar in CC: Zurückziehen, Abholung, Nicht-Abholung, Rückmeldung, Rückgabeinformation. The action stands when the user has no email address, and no mail is sent.

The interface is German. A public catalogue is a later idea.
