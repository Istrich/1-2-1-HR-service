## 2024-06-14 - Missing ARIA Attributes on Custom UI Controls and Icon Buttons
**Learning:** This app uses custom UI controls like audio sliders (`role="slider"`) and SVG-based icon-only buttons (via the global `I` object) which often lack necessary ARIA state attributes (`aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`) and descriptive `aria-label`s. This makes them inaccessible to screen readers.
**Action:** When implementing or modifying custom UI sliders (`role="slider"`), always ensure `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, and `aria-valuetext` are dynamically updated. Additionally, any icon-only button must include a descriptive `aria-label` and `title` attribute in Russian (e.g. `aria-label="Скрыть ошибку"`).
## 2024-05-24 - Icon-only buttons and sliders need explicit ARIA labels

**Learning:** The app makes extensive use of the global `I` object for SVG icons, leading to many icon-only buttons. The custom audio slider (`role="slider"`) is missing `aria-valuenow` to convey progress to screen readers. Relying only on visual context or `title` attributes for icon buttons breaks accessibility for keyboard/screen reader users.
**Action:** Always add explicit `aria-label` and `title` to icon-only buttons in Russian, and proper ARIA value attributes (`aria-valuemin`, `aria-valuemax`, `aria-valuenow`, `aria-valuetext`) to `role="slider"` elements.
## 2024-07-15 - Missing ARIA labels on search, text-symbol buttons, and inline edits
**Learning:** Text-symbol buttons (like '‹', '›' for previous/next navigation) and input elements without an explicit, visible `<label>` (such as `type="search"` in toolbars or inline `.title-edit` inputs relying solely on placeholders or visual context) are inaccessible to screen readers without specific ARIA descriptors.
**Action:** Always add descriptive `aria-label` and `title` attributes in Russian to search inputs, inline text inputs without visible labels, and text-symbol buttons.
