# Role reviews

Written from each role's point of view against the evidence in this repo. The product-owner, tech-lead and red/blue-team agents available in this environment are scoped to another project, so they were not used.

## Product owner

- **Who pays, who uses.** Buyer is a publisher executive; daily user is an editor. The dashboard serves the editor, the forecast and recommendation serve both. Keep that split visible.
- **Highest-value gap.** Anyone can read the analytics and post fake pageviews. Per-site write keys and login come before any other feature (plan phase 1).
- **Honesty.** Simulated traffic looks real. Add a "demo data" marker until a site is connected.
- **Activation metric.** Time from pasting the snippet to the first real pageview on the dashboard (target under 60 s). Instrument it.
- **Scope.** "Audience voice" (text analysis) is a separate job from live analytics; keep it, but do not let it delay auth.

## Tech lead

- Single module is right for now (see decisions D1, D2). Split into routers when the file passes about 600 lines or persistence lands.
- Replace environment reads with one typed settings object when a fourth variable appears.
- Tests are assert scripts, deliberately minimal. Move to pytest when CI runs them in a matrix.
- `build_overview` does all aggregation per call. Fine at 500 pages; precompute incrementally if pages or viewers grow.
- Tehran season uses a fixed UTC+3:30 offset, correct since Iran dropped daylight saving.
- Pin image digests and sign images once a registry exists.

## Red team (remaining ideas, ordered)

1. Tracker supply chain: `tracker.js` is served from one origin with a one-hour cache and no integrity hash. Compromise it and every publisher runs your script.
2. Fake-data campaigns against a competitor's host and URLs (T5).
3. Bidirectional-control characters in stored titles to spoof rows in the top-stories list. React escapes markup but not visual reordering.
4. Reaching uvicorn directly if the edge is bypassed: slowloris, forged forwarded headers.
5. Eviction pressure: many junk pages with two hits each to push out low-traffic real pages.

## Blue team

- **Detect.** `security_event kind=… ip=… path=… count=…` lines (kinds: `no_length`, `too_large`, `rate_limited`, `unauthorized`) appear at counts 1, 2, 4, 8… Alert on any `unauthorized` and on `rate_limited` counts doubling within minutes.
- **Respond.** Runbook has the steps. Block at the edge, never in the app.
- **Harden next.** Structured JSON logs with a request id, an internal-only metrics endpoint, SBOM generation in CI, gitleaks history scan (configured in CI, not run locally).
- **Contain.** Read-only filesystems, no capabilities, internal network are in compose; they are untested here.

## QA hints

- **Already automated.** NLP and classification checks, 35 HTTP-level edge checks, 28 pen-test probes, UI audit across four configurations.
- **Timing tests must be relative.** The first version failed on a loaded host with an absolute threshold; tests now compare against a baseline.
- **Gaps to cover.** Tracker behavior on a real single-page-app site (popstate counting), keyboard operation of the chart, offline and backoff behavior, Persian digit and RTL snapshots per theme, k6 load test at the documented limits.
- **Acceptance for phase 1.** A beacon without a valid site key is rejected; a dashboard request without a session is rejected; both rejections are logged as security events.
