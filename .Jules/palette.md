## 2024-06-14 - Missing ARIA Attributes on Custom UI Controls and Icon Buttons
**Learning:** This app uses custom UI controls like audio sliders (`role="slider"`) and SVG-based icon-only buttons (via the global `I` object) which often lack necessary ARIA state attributes (`aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`) and descriptive `aria-label`s. This makes them inaccessible to screen readers.
**Action:** When implementing or modifying custom UI sliders (`role="slider"`), always ensure `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, and `aria-valuetext` are dynamically updated. Additionally, any icon-only button must include a descriptive `aria-label` and `title` attribute in Russian (e.g. `aria-label="Скрыть ошибку"`).
## 2024-05-24 - Icon-only buttons and sliders need explicit ARIA labels

**Learning:** The app makes extensive use of the global `I` object for SVG icons, leading to many icon-only buttons. The custom audio slider (`role="slider"`) is missing `aria-valuenow` to convey progress to screen readers. Relying only on visual context or `title` attributes for icon buttons breaks accessibility for keyboard/screen reader users.
**Action:** Always add explicit `aria-label` and `title` to icon-only buttons in Russian, and proper ARIA value attributes (`aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-valuetext`) to `role="slider"` elements.

## 2024-05-18 - Missing ARIA labels in form inputs and symbol buttons
**Learning:** Found that custom search inputs, file upload inputs, settings inputs, and text symbol-based navigation buttons (like '‹', '›') lacked appropriate accessible names. This resulted in screen readers reading out the raw markup or input type without context, confusing users navigating via keyboard.
**Action:** Consistently apply `aria-label` to these interactive elements and associate visual labels using `htmlFor` and `id` for settings inputs.
