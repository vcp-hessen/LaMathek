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
- Materialarten können **Variantenbezeichner** mit geordneten Werten haben; Einzelteile speichern je einen Wert, Mengenposten können leer lassen.
- Einzelteile einer Materialart passen zusammen (Kohte vs. Wanderkohte = zwei Materialarten; unterschiedliche Randstreifen = Varianten einer Kohtenplane).
- Stangen/Heringe etc. sind Mengen mit Posten (Anzahl, optionale Variante, optionale Bezeichnung); ein Lagerkasten ist nur Bezeichnung am Posten, kein Einzelteil.

**Sets**

- Ein Set hat eine **Zuordnung** aus Einzelteilen und Mengen sowie optionale **Optionals**.
- Ein Einzelteil liegt in höchstens einem Set (oder keinem).
- Eine vom Set reservierte **Anzahl** aus einer Menge (Zuordnung oder Optional) wird vom Bestand der Mengenposten abgezogen.
- Set- und Verleih-Positionen benennen keine Variante.
- Beispiel Jurte: Zuordnung mit Planen; Seile/Heringe/Stangen als Optionals mit je einer Anzahl.

**Verleih-Inhalt**

- Set hinzufügen kopiert die Zuordnung in Positionen plus gewählte Optionals; Setname bleibt als **Herkunft**.
- Verleih kann auch ein einzelnes Einzelteil oder eine Anzahl aus einer Menge aufnehmen.
- **Verbrauchsmaterial** (consumable): keine Rückgabe/Übernahme; Position endet nach Abholung.
- Stark beschädigtes oder **ausgesondertes** Material ist nicht anfragbar.

## Konsequenzen

- API und UI für Materialarten, Sets, Stück-/Mengenverfolgung wie oben.
- Verfügbarkeitsprüfung bei Anfrage berücksichtigt Schaden und Aussortierung.
