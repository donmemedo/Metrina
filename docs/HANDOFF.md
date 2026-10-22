> Superseded by ../LAST_Report.md. Kept for history; sections 5 and 7 are mostly done now.

# Metrina — session handoff (security, pentest, performance, Apple-style UX)

Written 2026-10-02 for whichever model continues this work. Read this file top to bottom before touching code.

## 1. What the owner asked for

> Use red-team and blue-team agents plus security skills to audit and fix all problems, pen-test the project, add performance work to every security change, and use the `apple-design` skill for UI/UX. Spend as many tokens as needed; aim to finish within 5 hours.

Translated into deliverables:

1. Red-team pen test of the running app (local only), with evidence.
2. Blue-team gap analysis and fixes for every confirmed issue.
3. A performance note and measurement for every security fix.
4. UI/UX pass against Apple's design principles (`~/.claude/skills/apple-design/SKILL.md`).
5. Persian copy must follow `~/references/persian-ux-vocab/README.md` (owner's global rule).

## 2. Status at a glance

| Area | State |
| --- | --- |
| Backend hardening (`backend/app.py`) | **Done but uncommitted.** Smoke test passes 16/16. Has 4 known defects, see section 5. |
| Backend performance | **Done** for the dashboard endpoint. Measured, see section 4. |
| Red-team pen test | **Not done.** Both audit workflows died on a usage limit. Zero verified findings. |
| Blue-team audit | **Not done** beyond what was fixed directly from code reading. |
| Frontend security headers / CSP | **Not started.** |
| Frontend performance | **Not started.** |
| Apple-design UX pass | **Not started.** Skill was read; rubric is in section 7. |
| Accessibility + Persian copy review | **Not started.** |
| Docker / deployment hardening | **Not started.** |
| Commit | **Nothing committed.** Branch is `main` at `110655e MVP`. Make a branch before committing. |

## 3. Project map and how to run it

Stack: FastAPI 0.141 + pydantic v2 backend in one file, Next.js 16.3.6 + React 19.3 frontend. All data is in memory and synthetic traffic is simulated by an asyncio ticker.

| Path | Role |
| --- | --- |
| `backend/app.py` | Entire API: `/api/overview`, `/api/posts/{pid}`, `/api/track` (beacon collector), `/api/nlp`, `/tracker.js`, `/health` |
| `backend/test_app.py` | Original assert self-check for NLP, forecast, referrer classification |
| `backend/test_edge.py` | **New.** In-process smoke test for the hardening in this session |
| `frontend/app/page.tsx` | Dashboard, polls `/api/overview` every 3 s |
| `frontend/app/posts/[id]/page.tsx` | Post lifecycle + forecast, polls every 10 s |
| `frontend/app/voice/page.tsx` | Text analysis form calling `/api/nlp` |
| `frontend/app/setup/page.tsx` | Tracker snippet and test-event button |
| `frontend/components/shell.tsx` | Nav, theme and language switching, `usePoll` hook |
| `frontend/components/charts.tsx` | Hand-rolled SVG charts and the `useTween` counter |
| `frontend/lib/i18n.ts` | Persian and English strings, `Intl` formatters |
| `frontend/app/globals.css` | All styling: glass cards, animated background, motion |
| `frontend/next.config.ts` | Rewrites `/api/*` and `/tracker.js` to the backend. No `headers()` yet |
| `docker-compose.yml`, `*/Dockerfile` | Deployment. Backend port is published to the host |

**Environment quirks.** The venv was created at another path, so its `pip` and `uvicorn` launchers are broken. Always go through the interpreter:

```bash
cd backend
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8737   # API
.venv/bin/python test_app.py && .venv/bin/python test_edge.py      # checks
cd ../frontend
BACKEND_URL=http://127.0.0.1:8737 node_modules/.bin/next dev -p 3737
```

`httpx` was installed into the venv for the test client. It is not in `requirements.txt` because it is test-only.

**Ports.** Metrina uses 8737 and 3737. Other sessions on this machine use 3000, 3010, 3011, 8000 and 8011. Never test against those.

**Live servers.** Both Metrina servers were left running. The backend on 8737 was started before the rewrite and has no reload, so **it still runs the old code**. Restart it before any live testing.

**Stray files.** Next dev generated `frontend/AGENTS.md` and `frontend/CLAUDE.md`. Decide whether to keep or gitignore them. `skills-lock.json` at the root was already untracked before this session.

## 4. What changed in `backend/app.py`

All of this is uncommitted. Review with `git diff backend/app.py`.

| Change | Why | Verified |
| --- | --- | --- |
| Pure ASGI `Guard` middleware: body cap and per-IP rate limit on `/api/track` (4 KB, 120/min) and `/api/nlp` (64 KB, 30/min) | No body limit or rate limit existed | 413 on oversize, 429 after about 117 requests |
| POST without `Content-Length` on those paths gets 411 | Body cap relies on the declared length | Code only |
| Security headers on every response: nosniff, frame DENY, no-referrer, `no-store`, CSP `default-src 'none'`, Permissions-Policy, HSTS when HTTPS | Baseline had none | Yes |
| CORS `allow_origins=["*"]` **removed** | Any site could read the analytics API | Behavior change, see note below |
| Swagger and OpenAPI hidden unless `API_DOCS=1`, ReDoc removed | Schema exposure | Yes |
| Optional bearer token on read endpoints via `API_TOKEN`, constant-time compare | No auth at all | Yes, 401 and 200 |
| Invalid beacon JSON returns 400 | It used to raise and return 500 | Yes |
| `Event.host` restricted to hostname characters | Junk hosts skewed the referrer split | Partly, see defect 3 |
| Post cap now evicts the least-viewed tracked page instead of dropping all new pages forever | The old cap let junk permanently lock out real pages | Yes, stays at 500 and seeded posts survive |
| Hourly prune of tracked counts older than 72 h and of idle rate-limit rows | Both grew forever | Code only |
| Ticker task is awaited on shutdown | Clean shutdown | Code only |
| Synthetic history cached per post and hour with `lru_cache`, noise from `crc32` instead of seeding a new `random.Random` per cell | Main CPU hot spot | Yes, benchmark below |
| Dashboard payload memoized per second | Every viewer polling every 3 s rebuilt it | Yes |
| `GZipMiddleware` above 1 KB | Dashboard JSON was sent uncompressed | Yes |
| `/tracker.js` sent with `Cache-Control: public, max-age=3600` | It was fetched on every page view | Yes |
| `md5(..., usedforsecurity=False)` | Marks the hash as a non-security ID | Yes |

**CORS note.** Beacons from publisher sites still work, because `sendBeacon` with a text body is a simple request that CORS does not block. Browser-based third-party readers of the API now cannot read responses. Server-side CMS or BI consumers are unaffected. If a browser consumer is needed, add an explicit origin allowlist, not `*`.

**Measured performance, in-process, same data:**

| Call | Before | After |
| --- | --- | --- |
| Dashboard build | 18.4 ms | 2.1 ms |
| Dashboard, repeat call within the same second | 18.4 ms | under 0.01 ms |
| Post detail | 0.97 ms | 0.72 ms |

## 5. Known defects in this session's edit — fix these first

1. **Spoofable client IP.** `app.py:186` takes the leftmost `X-Forwarded-For` entry when `TRUST_PROXY=1`. A client controls that entry, so it can dodge the rate limit. Take the rightmost entry appended by your own proxy instead.
2. **Lock can stall the event loop.** One `LOCK` (`app.py:76`) guards both the dashboard memo and the rate-limit table. The dashboard build holds it on a worker thread for about 2 ms, while the rate limiter and `prune()` take it on the event loop. Use two separate locks, so the event loop only ever waits on the tiny rate-limit critical section.
3. **Host `.` still accepted.** The pattern at `app.py:353` allows a bare `.`, and the comment next to it claims the opposite. Since almost every referrer URL contains a dot, such beacons always count as "internal". Require at least one letter or digit with `^[A-Za-z0-9.\-:]*[A-Za-z0-9][A-Za-z0-9.\-:]*$`. This was tested: it accepts `site.ir` and `localhost:3000` and rejects `.`, `..` and `-`. Do not use a lookahead, because pydantic's default Rust regex engine does not support it. An explicitly sent empty host would now get 400; the tracker always sends `location.host`, so that is fine.
4. **Rate limit behind the Next proxy.** In the compose setup, browser calls reach the backend through the Next server, so every user shares the proxy's IP and one 120/min bucket. Either confirm Next forwards `X-Forwarded-For` and set `TRUST_PROXY=1` with defect 1 fixed, or have the tracker post straight to the backend origin.
5. **`API_TOKEN` breaks the dashboard if set.** The frontend never sends a token. If auth is turned on, the token must be injected server-side in the Next rewrite or a route handler. It must never be shipped to the browser.
6. **Older race, still present.** `build_overview()` iterates `POSTS` on a worker thread while `track()` can insert into it on the event loop. This can raise "dictionary changed size during iteration" under load. Iterate over a snapshot with `list(POSTS.items())`.

## 6. Audit workflows — what happened and how to re-run

Two Claude Code workflows were launched, each with 5 lenses plus a skeptic that tried to refute every finding. All 10 agents stopped on a usage limit before returning anything. **There are no verified findings.** One partial observation was left behind: the NLP regexes look linear, and input is capped at 20,000 characters, so catastrophic backtracking looked unlikely. Its live probe crashed before confirming this.

Saved scripts, re-runnable from Claude Code with `Workflow({scriptPath: ...})`:

- `~/.claude/projects/-home-makhataei-Projects-Mine-Metrina/cfd7eb6a-146e-4b0a-a102-145a6ec1094c/workflows/scripts/metrina-security-assessment-wf_14140f8f-ea5.js`
- `~/.claude/projects/-home-makhataei-Projects-Mine-Metrina/cfd7eb6a-146e-4b0a-a102-145a6ec1094c/workflows/scripts/metrina-blue-perf-ux-wf_7c5b4f18-5ea.js`

Before re-running, update both scripts: the backend now has the hardening above, so lenses should test the new code and confirm the defects in section 5. Restart the backend first.

Ground rules every lens used, keep them:

- Read-only on the repo during auditing. Scripts and outputs go to a scratch folder.
- Targets are only `127.0.0.1:8737` and `127.0.0.1:3737`.
- Non-destructive: no killing processes, no docker, at most 300 requests and 20 concurrent per test, bodies at most 2 MB.
- Every finding cites `file:line` and the exact command and output, or is marked code-only.
- Every finding carries a minimal fix and a performance note.
- No invented CVEs. Say "not verified" when unsure.

## 7. Remaining work, in order

### 7.1 Fix section 5, then commit

Make a branch, apply the six fixes, run both test files, restart the backend, commit.

### 7.2 Red team, against the restarted backend

| Lens | Focus |
| --- | --- |
| Input handling | Beacon body parsing, field limits, unicode, NLP input edge cases, error bodies, method confusion |
| Availability | Remaining unbounded state, thread-pool saturation, latency at 1, 5 and 20 concurrent, memory before and after a capped flood |
| Data integrity and access | Fake pageviews, spoofed referrer and device, post-id enumeration, docs exposure through the Next proxy, what multi-tenant SaaS would need |
| Browser side | Full header capture on both ports, cookies `lang` and `theme`, stored titles rendered in React, tracker script integrity and caching, rewrite reach |
| Supply chain and deploy | `npm audit`, pinned versions, Dockerfiles, compose hardening, uvicorn proxy flags, secrets grep |

### 7.3 Frontend hardening

Facts from the baseline header capture: the Next app sends `X-Powered-By: Next.js` and no security headers at all.

- Set `poweredByHeader: false` in `frontend/next.config.ts`.
- Add `headers()` there with a CSP that allows the app's inline `style` attributes and self-hosted fonts, plus nosniff, frame-ancestors, Referrer-Policy and Permissions-Policy.
- Validate the `lang` and `theme` cookies; `frontend/app/layout.tsx` already falls back safely, so confirm and move on.

### 7.4 Frontend performance, suspects from code reading, not yet measured

- `globals.css`: an infinitely animating, blurred, full-viewport background sits under many `backdrop-filter` glass cards, which may force repaints every frame.
- `.rise` entrance animation animates `filter: blur()` on every card.
- One `requestAnimationFrame` counter per `Num` instance, re-tweening on every 3 s poll.
- Polling never backs off while offline. It does skip hidden tabs.
- Both variable fonts are imported for both locales.

### 7.5 Apple-design UX pass

Rubric: `~/.claude/skills/apple-design/SKILL.md`. Suspects from code reading:

- The looping full-viewport background motion is something the skill explicitly warns against.
- `prefers-reduced-motion` currently removes all transitions, including fades that aid comprehension. The skill says to swap in short cross-fades instead.
- No handling for `prefers-reduced-transparency` or `prefers-contrast`.
- Glass stacked on glass, for example the chart tooltip over a card.
- Chart tooltips work only with a pointer, not with touch or keyboard.
- Segmented controls and tab-bar items may be under 44 px tall.
- The big live counter re-animates on every poll.

### 7.6 Accessibility and Persian copy

- Check every Persian string in `frontend/lib/i18n.ts` against `~/references/persian-ux-vocab/README.md`.
- All charts are `aria-hidden`, so their data has no text equivalent.
- There is no live region for polling updates.
- Some states are encoded by color only.
- Check contrast of muted text on glass in both themes.
- Check that loading skeletons expose a busy state.

### 7.7 Deployment

- Pin base images by digest.
- In compose, add read-only filesystems, `no-new-privileges`, resource limits, and stop publishing the backend port to the host.
- Add a frontend healthcheck.
- Run uvicorn with proxy-header flags limited to the frontend's address.
