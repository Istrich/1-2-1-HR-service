## 2024-05-24 - Accessibility on global icon buttons
**Learning:** Found several core interaction points (audio playback, modal close, form submission) using the global `I` SVG object without any `aria-label` or `title` attributes. Because the frontend relies heavily on this global icon system rather than labeled UI buttons, screen readers receive zero context for critical app functions.
**Action:** Always map icon-only elements (especially from `I.*`) to standard Russian `aria-label` and `title` attributes to preserve intent for non-visual users.
