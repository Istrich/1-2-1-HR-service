
## 2024-03-24 - Add Accessibility Labels for Icon-Only Buttons Rendered via Global `I` Object
**Learning:** The frontend uses a global `I` object to render raw SVG icons inside buttons. By default, developers might insert these into `<button>` elements without providing `aria-label` or `title` attributes. Because the SVGs don't contain inherently accessible text, this leads to icon-only buttons that are completely invisible to screen readers and difficult to understand without context.
**Action:** Always verify that buttons containing only icons from the global `I` object explicitly declare descriptive `aria-label` and `title` attributes in Russian (e.g. `aria-label="Закрыть"`).
