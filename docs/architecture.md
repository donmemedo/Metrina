# Architecture

```
browser ──► edge (Caddy :8080) ──┬─► frontend (Next.js :3000)   pages, nonce CSP
 publisher site (tracker.js)     └─► backend  (FastAPI :8000)   /api/*, /tracker.js
                                      │
                       in-memory stores, one process, one event loop
                       POSTS  TRACKED  BUCKETS  HITS  MEMO  EVENTS
```

In compose only the edge is published. Backend and frontend are on an `internal` network with no route out. For local development Next rewrites `/api/*` and `/tracker.js` to the backend instead of the edge.

## Data flow

1. A publisher page loads `/tracker.js`, which `sendBeacon`s `{url, title, referrer, host}` to `/api/track` as `text/plain` (a simple request, so no CORS preflight).
2. The edge sets `X-Forwarded-For` to the real client address. The `Guard` middleware checks length framing, body cap and per-IP rate, then adds security headers.
3. `track()` validates the event, creates or finds the page, bumps the live minute bucket and the hourly count.
4. The ticker adds synthetic readers every 2 s so the demo is alive before a site is connected, and prunes old counts hourly.
5. The dashboard polls `/api/overview` (every 3 s, backing off on failure). One serialized payload is built per second and served to every viewer.

## Invariants

- **Shared state is touched only on the event loop.** Every handler that reads or writes the stores is `async`, so nothing interleaves mid-build. This removed the "dictionary changed size" race and every lock. `/api/nlp` is the one sync handler: it is pure and runs on the thread pool. A test fails if a handler regresses to sync.
- **Bounded state.** Pages are capped at 500 tracked (least-viewed evicted, seeded pages survive); counts older than 72 h are dropped; the rate table is flushed above 20,000 keys; synthetic history is an LRU of 65,536 cells.
- **The body cap trusts only Content-Length**, so chunked bodies and missing lengths are refused on capped routes.

## Decisions

| # | Decision | Why | Revisit when |
| --- | --- | --- | --- |
| D1 | One module, one process, in-memory | MVP: nothing to persist yet | Real customers send events: Postgres or ClickHouse, then a worker for aggregation |
| D2 | Async handlers instead of locks | Fewer lines and no race class; a build measured ~12 ms with the seeded pages on a loaded host (it grows with tracked pages, capped at 500, and runs at most once per second) | Builds exceed ~50 ms: move to a background task |
| D3 | Edge proxy owns the client address | Next passes a forged `X-Forwarded-For` through unchanged (evidence: `docs/evidence/next-xff-passthrough.txt`) | Behind a cloud load balancer: trust its header instead |
| D4 | Nonce CSP from `proxy.ts` | Next's inline hydration scripts need a per-request nonce; pages are already dynamic (they read cookies) | Never relax `script-src` |
| D5 | No dashboard login yet | Out of MVP scope; token injection for anonymous visitors was tried and withdrawn | Before any multi-tenant or private data (plan phase 1) |

## Scaling path

In-memory rate limits and stores do not survive more than one instance. For several instances: Redis for rate limits, a database for events, and the edge for cross-instance IP trust.
