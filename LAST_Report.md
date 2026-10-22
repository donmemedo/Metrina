# LAST_Report — Metrina (Parsely Iran) security, performance and UX audit

Branch `security-perf-ux-audit`. Model for this session: Sonnet 5.5 (no model switch attempted, as you asked). Everything below was measured on this machine unless marked **unverified**.

## 1. Status

| Area | State |
| --- | --- |
| Backend hardening, 6 handoff defects | Done and tested (35/35 edge tests, pure-logic tests pass) |
| Pen test (local only) | Done. Before 12/18 defended; after, on the final production build, **28/28** (20 API + 8 web) |
| SAST / SCA | Bandit 0 issues, Semgrep 23 files 0 findings, pip-audit clean, npm audit 0 after upgrading Next 16.3.6 → 16.4.2 |
| Frontend security headers + nonce CSP | Done, checked in headless Chrome with no violations |
| Apple-design UX / a11y pass | Done, measured before/after (section 4) |
| Docker / Caddy edge / CI | Written. **Unverified**: Docker daemon is down here, so no image was built, Caddyfile never run, CI never executed. `docker compose config` validates |
| graphify | Built: 239 nodes, 427 edges, 11 communities (`graphify-out/`) |
| docs folder (architecture, threat model, pen-test report, performance, UX, role reviews, threat-intel lifecycle, plan, runbook) | Written |
| Root README | Written |
| PWA / APK / IPA | Not started (you said later) |
| Final rebuild after removing token injection | Done. API on 8737 and web on 3737 were restarted from the final code; pen test and UI audit re-run against them |

## 2. Where this started (earlier sessions and memory)

- You asked for red + blue team audit, pen test, performance for every security fix, Apple-design UX, Persian copy review, then a PR.
- Session 1 hardened `backend/app.py` (body caps, rate limit, headers, CORS removed, docs hidden, optional token, caching, gzip) but left 6 defects, committed nothing, and both audit workflows died on a usage limit with zero verified findings. It wrongly noted the NLP regexes "look linear".
- Memory held two notes: local dev quirks (broken venv launchers, ports 8737/3737 are Metrina's, others own 3000/3010/3011/8000/8011) and "audit is mid-way, read HANDOFF.md".

## 3. Findings and fixes (evidence in `docs/evidence/`; rows 5 and 6 are partly reproduced at the primitive level, noted inline)

| # | Severity | Finding | Fix | Result |
| --- | --- | --- | --- | --- |
| 1 | High | Body cap bypass: chunked request with a forged small Content-Length got 100 KB accepted | Refuse chunked/missing length, bound the digits | 411 |
| 2 | High | One 20k-char NLP request froze the whole server | Quadratic regex replaced by one split | 83.9 s → 0.04 s, health stays 0.00 s |
| 3 | High | Rate limit dodged by forging X-Forwarded-For (0 of 135 throttled) | Use the last entry, only behind an edge that overwrites it | 15 of 135 throttled |
| 4 | Med | `dictionary changed size` 500s while dashboard rebuilt | Handlers touching shared state are async: no threads, no locks | 2 errors in 170 → 0 in 1195 |
| 5 | Low | Host "." accepted (reproduced); `netflix.com` read as x.com and `evilsite.ir` as internal (reproduced on the original commit) | Pattern fix, hostname-based classify | tested |
| 6 | Med | Non-ASCII Authorization header raises `TypeError` (primitive reproduced, not end to end); no token brute-force limit; read API unthrottled (by inspection) | bytes compare, failure throttle, 600/min reads | tested |
| 7 | High | Next 16.3.6: 6 high advisories (cache poisoning, SSRF in image optimization) | Upgraded to 16.4.2, lockfile fix | npm audit 0 |
| 8 | Info | Next passes a forged X-Forwarded-For through unchanged (API logged `ip=9.9.9.9`) | Caddy edge owns the client address | evidence `next-xff-passthrough.txt` |
| 9 | Med | **My own mistake, caught by an automated review**: the edge/Next injected the API token for every visitor (confused deputy) | Removed. Token now protects server-to-server callers only; dashboard auth is future work | withdrawn design kept as evidence |

Performance of the fixes: dashboard payload serialized once per second (build 12 ms vs memo hit 0.3 ms in-process), no thread hop on hot handlers, no lock. Host load average was 34–53 throughout, so absolute timings are noisy.

## 4. UX / accessibility, same audit script on old and new build

| Metric | Before → after |
| --- | --- |
| Texts below WCAG AA | 14 → 0 (light, dark, mobile). Worst was 2.2:1 |
| Controls under 44 px on touch | 5 → 0. Desktop mouse targets are 36 px, not 44 |
| backdrop-filter layers | 11 → 2 |
| Infinite animations | 3 → 0 |
| Live region, labelled nav, aria-current, skip link | 0 → present |
| Idle CPU | **Inconclusive**: 3 interleaved runs, medians −54%, but spread was 10x on a loaded host |

Also: chart is now a keyboard/touch slider with a spoken value, reduced-motion keeps fades only, reduced-transparency and increased-contrast are supported, polling backs off and refreshes on tab return. Persian copy matched the UX vocabulary except "تحلیل کن", now "تحلیل متن".

## 5. What I did not do, and why

- A first draft of the pen-test report claimed every finding was reproduced; three were not. I then ran them against the original code. Result: referrer misclassification reproduced, the non-ASCII header failure reproduced only as a primitive, and the huge Content-Length case was not reachable (the HTTP library answers 400 first). The docs now say so.
- Skills like fastapi-pro, python-observability and the role agents (PO, Tech Lead, Red/Blue) were not invoked. The role agents are written for another project (PropAgentAI). I applied the principles directly instead.
- A safety classifier stopped several earlier replies. I continued with local-only defensive work.
- Not verified: Docker build, Caddyfile, and the CI run.

## 6. Run it

```bash
cd backend && TRUST_PROXY=0 .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8737
cd frontend && npm run build && BACKEND_URL=http://127.0.0.1:8737 node_modules/.bin/next start -p 3737 -H 127.0.0.1
cd backend && .venv/bin/python test_app.py && .venv/bin/python test_edge.py && .venv/bin/python pentest.py
docker compose up --build   # unverified here
```

## 7. Next, in order

1. Start Docker and run `docker compose up --build`; fix whatever breaks. Pin image digests.
2. Dashboard authentication (OIDC) and per-site write keys: today anyone can read analytics and post fake pageviews.
3. Persistence (Postgres or ClickHouse), then PWA, APK, IPA. Details in `docs/implementation-plan.md`.
