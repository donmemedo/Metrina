# UX and accessibility audit

Rubric: Apple's fluid-interface and materials guidance (the `apple-design` skill) plus WCAG 2.2 AA. Measured with `scripts/ui-audit.mjs` in headless Chrome on the same page before and after; screenshots and JSON are in `docs/evidence/ui/`.

## Measured, before → after

| Metric | Light | Dark | Mobile (touch) | Reduced motion |
| --- | --- | --- | --- | --- |
| Texts below AA | 14 → 0 | 14 → 0 | 14 → 0 | 14 → 0 |
| Controls under 44 px | 8 → 8 | 8 → 8 | 5 → 0 | 8 → 8 |
| backdrop-filter elements | 11 → 2 | 11 → 2 | 11 → 2 | 11 → 2 |
| Infinite animations | 3 → 0 | 3 → 0 | 3 → 0 | 0 → 0 |
| Live regions | 0 → 1 | 0 → 1 | 0 → 1 | 0 → 1 |

Desktop mouse targets are 36 px: above WCAG 2.5.8's 24 px minimum but below Apple's 44 px, which applies on touch (where it is now met).

## What changed against the rubric

| Principle | Before | After |
| --- | --- | --- |
| No full-viewport looping motion | 26 s drifting, blurred background | Static gradient |
| Materials encode hierarchy; never glass on glass | 11 glass layers, tooltip over glass cards | Glass on header, tab bar and tooltip only; content cards are plain surfaces |
| Reduced motion means gentler, not none | Everything switched off | Fades kept; positional and looping motion removed |
| Reduced transparency, increased contrast | Not handled | Handled (solid surfaces, stronger borders, darker muted text) |
| Direct manipulation | Chart tooltip only with a pointer | Pointer, touch scrub, and keyboard (arrows, Home/End, PageUp/Down) with a spoken value |
| Feedback and status | Banner without a role, skeleton without a busy state | `role=alert` banner, busy skeleton, throttled live summary (at most every 30 s) |
| Wayfinding | Two unlabeled navs, no current page | Labeled navs, `aria-current`, skip link |

Not done: spring-based, interruptible interactions and haptics (the app has no drag-driven surfaces yet); the 36 px desktop target size; a visual-regression suite.

## Persian copy against the UX vocabulary

| String | Verdict |
| --- | --- |
| پیش‌خوان (dashboard), بازگشت (back), کپی (copy), اینجا را خالی نگذارید (empty field) | Match the vocabulary |
| بازدیدکننده, مطلب فعال, نسبت به دیروز, اتصال به سرور برقرار نیست | Consistent and polite |
| تحلیل کن | Informal imperative next to polite forms → **تحلیل متن** |
| New: پرش به محتوا, پیمایش اصلی, در حال بارگذاری… | Added for accessibility; not in the vocabulary file, chosen to match its tone |

**Open recommendation**: the dashboard shows simulated traffic as if real. Add a visible "demo data" indicator until a site is connected (the "responsibility" principle).
