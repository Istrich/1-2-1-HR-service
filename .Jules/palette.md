## 2024-03-24 - Add Accessible Names to Icon-Only Buttons
**Learning:** Icon-only buttons relying on SVG variables (like `I.x`) in this application were missing necessary accessible names and tooltips.
**Action:** Always add descriptive `aria-label` and `title` attributes in Russian to icon-only buttons to ensure full accessibility and usability for screen readers and keyboard users.
## 2024-05-24 - Icon-only buttons and sliders need explicit ARIA labels

**Learning:** The app makes extensive use of the global `I` object for SVG icons, leading to many icon-only buttons. The custom audio slider (`role="slider"`) is missing `aria-valuenow` to convey progress to screen readers. Relying only on visual context or `title` attributes for icon buttons breaks accessibility for keyboard/screen reader users.
**Action:** Always add explicit `aria-label` and `title` to icon-only buttons in Russian, and proper ARIA value attributes (`aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-valuetext`) to `role="slider"` elements.
