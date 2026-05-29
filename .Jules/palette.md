## 2024-05-29 - Explicit ARIA Labels for SVG Icon Buttons
**Learning:** Icon-only buttons in this app often use a global `I` object containing SVG elements (like `I.x`, `I.play`, `I.out`). Because the SVG itself is directly injected without semantic text, these buttons lack accessible names for screen readers.
**Action:** When adding or encountering icon-only buttons rendered via the global `I` object, ensure an explicit `aria-label` attribute (in Russian) is added to the wrapping `<button>` element to make the action clear to assistive technologies (e.g. `aria-label="Закрыть"` for `I.x`).
