## 2024-05-17 - Add ARIA Labels to Icon-Only Buttons
**Learning:** Found several icon-only buttons (`<button>` tags wrapping `I.xyz` SVG references) missing screen reader descriptions and hover tooltips. The project's language is Russian, so accessibility attributes must be localized.
**Action:** Always add `aria-label` and `title` attributes in Russian when utilizing icon-only buttons from the global `I` object to improve both keyboard navigation predictability and screen reader accessibility.
