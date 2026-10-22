# Implementation plan

Done: backend and edge hardening, pen test, nonce CSP, UX and accessibility pass, hardened compose, CI. See `LAST_Report.md`.

| Phase | Work | Acceptance criteria |
| --- | --- | --- |
| 0. Verify | Start Docker, build both images, bring up compose, run the CI workflow once | `docker compose up` serves the dashboard on :8080; `pentest.py` against it passes; CI green; image digests pinned |
| 1. Trust | Per-site write keys on `/api/track`; dashboard login (OIDC); token for machine clients | Beacon without a valid key gets 401 and a `security_event`; dashboard without a session redirects to login; pen test gains probes for both |
| 2. Persistence | Postgres or ClickHouse for events, background aggregation, retention policy | Restart keeps history; dashboard build time independent of page count; migration tested |
| 3. Observability | JSON logs with request id, internal metrics endpoint, alert rules on security events | Alert fires in a drill for `unauthorized` and `rate_limited` growth |
| 4. Scale-out | Redis rate limits, more than one backend instance | Limits hold across instances in a k6 test |
| 5. Supply chain | SBOM in CI, image signing, versioned `tracker.js` with an integrity hash | Publishers can pin the script by hash |
| 6. Apps | PWA first (manifest, service worker, offline shell), then APK and IPA wrappers | Lighthouse PWA pass; installable on Android and iOS |

Risks: authentication changes the public-dashboard assumption in the threat model; persistence changes the performance numbers in `security-performance.md`, which must be re-measured.
