## 2026-06-13 - Custom Slider Accessibility
**Learning:** Screen readers cannot announce the value of a custom `role="slider"` element (like an audio progress track) if it lacks `aria-valuenow` and `aria-valuetext`. Without these, the user knows it's a slider but has no idea what its current state or time is.
**Action:** Always add `aria-valuemin`, `aria-valuemax`, `aria-valuenow`, and `aria-valuetext` to custom sliders so their real-time state is conveyed accurately.
