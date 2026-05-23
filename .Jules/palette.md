## 2024-05-18 - Missing ARIA Labels on Icon-Only Buttons
**Learning:** Found an accessibility pattern where icon-only buttons (like `I.x`, `I.out`, `I.play`) lack `aria-label` and `title` attributes. Sighted users might guess the meaning from context, but screen readers just read "button", and sighted users don't get tooltips on hover.
**Action:** When reviewing new components, always check buttons that only contain an icon for `aria-label` (for screen readers) and `title` (for sighted users).
