## 2026-05-25 - Added aria-labels to icon-only buttons
**Learning:** Icon-only buttons (like those using global SVG object I.x, I.out, I.play, etc.) lack semantic context and fail accessibility checks. To support screen readers, explicit `aria-label` attributes are strictly required. The project UI language is Russian, so these attributes must be in Russian.
**Action:** Add translated `aria-label` props to any component rendering purely graphical icons (`I.*`) without readable text to guarantee full screen-reader compliance.
