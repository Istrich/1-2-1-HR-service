## 2024-05-15 - Missing ARIA labels on Icon-only components
**Learning:** In the HR 1-2-1 React frontend `static/index.html`, several buttons use a global SVG dictionary `I` for rendering icons (e.g., `I.play`, `I.x`, `I.mail`) without text. By default, these icon-only buttons do not have an accessible name, making them unreadable to screen readers.
**Action:** When adding or updating interactive elements that use the `I` icon dictionary without textual content, always ensure an appropriate `aria-label` attribute (in Russian) is added to the wrapping `<button>`.
