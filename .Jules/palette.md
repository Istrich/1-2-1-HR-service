## 2024-05-24 - Missing ARIA Labels on Icon Buttons
**Learning:** Found a recurring accessibility issue where icon-only buttons (like play/pause, close modals, send actions) lack `aria-label` attributes, making them unreadable for screen reader users. The application relies heavily on global `I` object for SVG icons, making manual ARIA labels crucial.
**Action:** Always verify that buttons containing only icons (e.g. `{I.play}`) have descriptive `aria-label` attributes in Russian.
