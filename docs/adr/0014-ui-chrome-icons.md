---
status: accepted
---

# Heroicons for generic UI chrome

Waldläuferzeichen carry domain meaning in navigation and empty states. Hamburger menus, chevrons, and similar controls are not part of that lexicon and should not borrow WLZ glyphs.

The web client uses `@heroicons/vue` (24 px outline) for those generic controls. Import them only through `UiIcon.vue` so the set stays consistent and tree-shaken.

WLZ rules in `docs/vcp-corporate-design.md` are unchanged.
