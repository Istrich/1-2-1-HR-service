## 2024-05-17 - Added Form Accessibility
**Learning:** Found that custom `Login` components need to make sure to link their `label` elements with `input` tags so screen readers can interpret them correctly.
**Action:** When creating forms, make sure to add `htmlFor` and `id` properties to input elements. Also be sure to add `aria-label` properties to icon-only buttons like "close" and "logout".
