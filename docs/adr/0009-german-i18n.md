---
status: accepted
---

# German first, through an i18n layer

The interface is German. User-facing strings go through an internationalization layer from the start, even though no second language is translated yet.

Role and people labels use gender-inclusive German (for example Ausleihende*r, Materialwart*in). Domain terms in code and the database stay the short forms from `CONTEXT.md`.

Retrofitting that layer later means touching every screen. Shipping only German now avoids translating into a language nobody has asked for.
