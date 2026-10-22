# Runbook

## Start, stop, test

```bash
cd backend && .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8737
cd frontend && BACKEND_URL=http://127.0.0.1:8737 node_modules/.bin/next start -p 3737 -H 127.0.0.1
cd backend && .venv/bin/python test_app.py && .venv/bin/python test_edge.py && .venv/bin/python pentest.py
```

Use `python -m …` for the venv: its `pip` and `uvicorn` launchers have dead shebangs. Other sessions on the same machine use ports 3000, 3010, 3011, 8000, 8011; Metrina uses 8737 and 3737. Next dev regenerates `frontend/AGENTS.md` and `CLAUDE.md`; they are committed.

## Settings

See the table in `README.md`. `TRUST_PROXY=1` is correct only when an edge overwrites `X-Forwarded-For`. Next does not (evidence: `docs/evidence/next-xff-passthrough.txt`).

## Detection signals

Backend log lines like `security_event kind=too_large ip=… path=… count=N`, written at counts 1, 2, 4, 8…

| Kind | Meaning | First response |
| --- | --- | --- |
| `no_length` | Chunked or length-less body on a capped route | Usually a scanner. Block the IP at the edge if it repeats |
| `too_large` | Body over the cap or a malformed length | Same |
| `rate_limited` | A client exceeded its per-minute budget | Check whether it is one IP or many; many means a flood, so tighten at the edge |
| `unauthorized` | Wrong or missing token (only when `API_TOKEN` is set) | Rotate the token if the source is unexpected |

## Protecting the dashboard today (unverified)

Setting `API_TOKEN` alone breaks the dashboard, because the dashboard is public and sends no token. Do **not** inject the token for anonymous visitors (that makes it look protected while it is not). Until phase 1 lands, put authentication in front first: a Caddy `basic_auth` block (or `forward_auth` to your identity provider) on every route except `/api/track` and `/tracker.js`, and only after it succeeds add `header_up Authorization "Bearer {$API_TOKEN}"` on `/api/*`. This configuration has not been run: Caddy was not available when this was written.

## Rotating the token

Change `API_TOKEN` in `.env`, then `docker compose up -d backend`. Clients holding the old token start failing with 401; the failure throttle stops guessing at 30 attempts per minute.

## Incident outline

1. Identify the kind and source from the log. 2. Block at the edge. 3. Check `/health` and the dashboard. 4. If memory is high, restart: all data is in memory and resets, which is also the recovery. 5. Add a probe to `pentest.py` for what happened.
