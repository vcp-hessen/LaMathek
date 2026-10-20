---
id: D0002
titel: Inventar, Material und Sets
status: accepted
ersetzt: null
ersetzt_durch: null
context_begriffe: [Inventar, Materialart, Einzelteil, Menge, Set, Variante]
---

# D0002 — Inventar, Material und Sets

## Begriffe

Siehe [CONTEXT.md](../../CONTEXT.md) — **Inventar**, **Materialart**, **Einzelteil**, **Menge**, **Set**, **Variante**.

## Kontext

Material liegt ortsgebunden in Inventaren (z. B. Donnerskopf, Landesbüro). Sets bündeln Einzelteile und Mengenanteile für die Ausgabe.

## Entscheidung

**Inventar**

- Ein Inventar ist Material an einem Ort. **Set**, **Einzelteil** und **Menge** gehören jeweils genau einem Inventar.

**Materialarten**

- Materialarten sind in der Anwendung konfigurierbar.
- Pro Inventar wird eine Materialart als **Einzelteile** oder als **Menge** geführt.
- Materialarten können **Variantenbezeichner** mit geordneten Werten haben; Einzelteile und Mengenposten speichern je einen Wert pro Bezeichner. Ein Mengenposten ist genau **eine Materialart in einer Variante**, nie eine Mischung (#12).
- Einzelteile einer Materialart passen zusammen (Kohte vs. Wanderkohte = zwei Materialarten; unterschiedliche Randstreifen = Varianten einer Kohtenplane).
- Stangen/Heringe etc. sind Mengen mit Posten (Anzahl, Variante falls die Materialart Varianten hat, optionale Bezeichnung); ein Lagerkasten ist nur Bezeichnung am Posten, kein Einzelteil.

**Sets**

- Ein Set hat eine **Zuordnung** aus Einzelteilen und Mengen sowie optionale **Optionals**.
- Ein Einzelteil liegt in höchstens einem Set (oder keinem).
- Ein Set **reserviert nichts**: Die Anzahl einer Set-Zeile beschreibt nur, wie viel zum Set gehört (höchstens die Menge des Inventars). Belegt wird erst beim Bestätigen eines Verleihs (D0007).
- Set-Zeilen und Verleih-Positionen einer Menge benennen die Variante (z. B. „12 × Seil (3 m)“, „3 × Seil (4 m)“). Anzahl, Verfügbarkeit (D0007) und Verluste (D0009) zählen je Variante.
- Ändern sich die Variantenbezeichner einer Materialart später, behalten bestehende Positionen ihre damalige Bezeichnung (Historie); neu angelegte Posten müssen die neue Kombination vollständig angeben.
- Beispiel Jurte: Zuordnung mit Planen; Seile/Heringe/Stangen als Optionals mit je einer Anzahl.

**Verleih-Inhalt**

- Set hinzufügen kopiert die Zuordnung in Positionen plus gewählte Optionals; Setname bleibt als **Herkunft**.
- Verleih kann auch ein einzelnes Einzelteil oder eine Anzahl aus einer Menge aufnehmen.
- **Verbrauchsmaterial** (consumable): Rückgabe und Übernahme wie bei anderen Mengen; bei der Übernahme wird nur der nicht zurückgegebene Teil vom Bestand abgeschrieben (Menge 0 = Verlust mit Grund).
- Stark beschädigtes oder **ausgesondertes** Material ist nicht anfragbar.

## Konsequenzen

- API und UI für Materialarten, Sets, Stück-/Mengenverfolgung wie oben.
- Verfügbarkeitsprüfung bei Anfrage berücksichtigt Schaden und Aussortierung.
