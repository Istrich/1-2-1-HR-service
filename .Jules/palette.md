## 2024-05-15 - Missing ARIA Labels on Icon-only Buttons
**Learning:** Found multiple instances of icon-only buttons (play/pause, close modals, send actions) lacking `aria-label` attributes. This makes screen reader navigation frustrating as the purpose of the buttons isn't conveyed.
**Action:** Always ensure icon-only buttons have a descriptive `aria-label` and `title` (for sighted users) in Russian, matching the app's language.
