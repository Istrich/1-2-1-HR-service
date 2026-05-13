## 2024-05-13 - Form Error Announcement Pattern
**Learning:** Found that the React error states (like `{err && <div className="err">{err}</div>}`) in this app were completely silent to screen readers upon dynamic login failure. Adding `role="alert"` and `aria-live="polite"` was required to ensure the screen reader announces the error without moving focus.
**Action:** Apply `role="alert"` specifically to dynamically appearing error text nodes in this app, rather than relying on standard DOM insertion.
