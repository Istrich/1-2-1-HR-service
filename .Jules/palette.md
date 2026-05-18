## 2024-05-24 - Missing ARIA Labels on Icon-Only Buttons
**Learning:** Found a recurring accessibility issue where icon-only buttons (like the audio play toggle and modal close buttons) were missing accessible names, making them difficult to use with screen readers.
**Action:** Always ensure icon-only `<button>` elements have an explicit `aria-label` attribute (in Russian for this project) so their function is clear to assistive technologies.
