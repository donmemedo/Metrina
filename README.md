# Parsely Iran (Metrina)

Real-time content analytics for Persian publishers: a live reader count, hourly traffic, per-story lifecycle with a 24-hour forecast, referrer and device split, and a Persian/English text analyzer. FastAPI backend, Next.js 16 frontend, light and dark themes, fa/en with RTL.

## Run it

```bash
# API (port 8737)
cd backend && python -m venv .venv && .venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8737

# Web (port 3737)
cd frontend && npm ci && npm run build
BACKEND_URL=http://127.0.0.1:8737 node_modules/.bin/next start -p 3737 -H 127.0.0.1
```

Or everything behind the Caddy edge: `cp .env.example .env && docker compose up --build`, then open http://localhost:8080. (The compose setup was written but not built in the audit environment; see `LAST_Report.md`.)

Connect a site by pasting `<script async src="https://YOUR-HOST/tracker.js"></script>`.

## Configuration

| Variable | Where | Meaning |
| --- | --- | --- |
| `TRUST_PROXY=1` | backend | Client IP is the last `X-Forwarded-For` entry. Only behind an edge that overwrites that header (Caddy in compose). Next alone does not. |
| `API_TOKEN` | backend | API requires `Authorization: Bearer <token>`. Server-to-server only: the public dashboard sends no token. |
| `API_DOCS=1` | backend | Serve Swagger UI. Off by default. |
| `BACKEND_URL` | frontend build | Where Next rewrites `/api/*` (dev and single-host use). |
| `WEB_PORT`, `SITE_ADDRESS` | compose | Published port; a real domain turns on automatic HTTPS. |

## Tests

```bash
cd backend
.venv/bin/python test_app.py      # NLP, forecast, referrer classification, regex worst cases
.venv/bin/python test_edge.py     # 35 HTTP-level checks: caps, limits, headers, auth, state caps
.venv/bin/python pentest.py       # local-only pen test of the running API and web app (28 probes)
node scripts/ui-audit.mjs http://127.0.0.1:3737/ out --dark   # contrast, targets, CPU, landmarks in headless Chrome
```

## Documentation

| File | Contents |
| --- | --- |
| `LAST_Report.md` | What was done, measured, skipped, and what is next |
| `docs/architecture.md` | Components, data flow, invariants, decisions |
| `docs/threat-model.md` | Assets, trust boundaries, attack tree, residual risk |
| `docs/pentest-report.md` | Method, findings with before/after evidence |
| `docs/security-performance.md` | Cost of each security control |
| `docs/ux-audit.md` | Apple-design and accessibility pass, Persian copy review |
| `docs/role-reviews.md` | Product owner, tech lead, red team, blue team, QA |
| `docs/threat-intel-lifecycle.md` | How advisories are collected, triaged and closed |
| `docs/implementation-plan.md` | What is next, with acceptance criteria |
| `docs/runbook.md` | Operating, detecting, responding |
| `docs/evidence/` | Raw outputs: pen test, SCA, SAST, UI audits, screenshots |

All data is in memory and resets on restart; traffic shown before a real site is connected is simulated.
