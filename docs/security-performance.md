# What each security control costs

Host load average was 34–53 during measurement, so absolute times are noisy. "Measured" means a number from this repo's tests or probes; "structural" means counted or reasoned from the code; "unmeasured" says so.

| Control | Cost | Basis |
| --- | --- | --- |
| Pure-ASGI `Guard` (cap, rate limit, headers) | One header scan and one deque operation per request; no per-request task | Structural. Not benchmarked separately |
| Per-IP rate limit | O(1) amortized; table flushed above 20,000 keys, so memory is bounded | Structural |
| Async handlers instead of locks | No lock, no thread hop. A dashboard build blocks the loop for its duration: about 12 ms with the seeded pages, growing with tracked pages (cap 500), at most once per second | Measured (12.09 ms) |
| Dashboard payload serialized once per second | Build 12.09 ms vs memo hit 0.345 ms in-process, roughly 35x | Measured |
| Linear-time NLP | Worst 20k-char input 83.87 s → 0.04 s via HTTP; 56 ms in-process on a loaded host | Measured |
| Security events logged at counts 1, 2, 4, 8… | O(log n) log lines under attack instead of one per request | Structural |
| Nonce CSP | A random UUID per page request. Pages were already dynamic (the layout reads cookies), so no static optimization is lost | Structural |
| Static background, glass on navigation only | Backdrop-filter elements 11 → 2; infinite animations 3 → 0; no `filter: blur` entrance | Measured counts |
| Counters write the DOM and skip tiny changes | No React render per animation frame (previously ~10 elements × 60 fps for 0.9 s per poll) | Structural |
| Idle CPU in headless Chrome | Median over 3 interleaved runs: task time −54%, script −75%, but run-to-run spread was 10x | **Inconclusive**, software rendering on a loaded host |
| Polling backoff and visibility refresh | Fewer requests while offline or hidden; at most one request per 30 s when failing | Structural |
| Caddy edge | One extra local hop; compression moves to the edge | **Unmeasured** (not run here) |
| Container limits (memory, pids, cpu) | Protect the host; the single process must fit 256 MB | **Unmeasured** |
