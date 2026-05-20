## 2024-05-24 - Accessibility for Icon-Only Buttons in Russian
**Learning:** Found several icon-only buttons (like play/pause, close modals, send actions) that lacked `aria-label` attributes, making them inaccessible to screen readers. Since the project's primary language is Russian, all accessibility attributes must also be in Russian.
**Action:** Always verify that interactive elements without visible text have descriptive `aria-label`s in Russian (e.g., "Закрыть", "Воспроизведение") to ensure inclusivity and compliance with accessibility standards.
