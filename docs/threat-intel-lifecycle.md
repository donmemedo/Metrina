# Threat-intelligence lifecycle for this stack

Scope: vulnerabilities and attacker techniques that can affect FastAPI, Starlette, Pydantic, uvicorn, Next.js, React, Node and the container images.

| Phase | What we do | Tooling |
| --- | --- | --- |
| Direction | Priorities: availability of the collector, integrity of analytics, supply chain. Review when the data becomes private | This repo's threat model |
| Collection | Advisories for every pinned dependency; exploited-in-the-wild lists; framework release notes | Dependabot (pip, npm, docker, actions), `pip-audit`, `npm audit`, weekly scheduled CI run, Trivy |
| Processing | Map each advisory to a pinned version and to whether the vulnerable feature is used | `requirements.lock`, `package-lock.json`, CI logs |
| Analysis | Exploitable here? Check reachability (for example image optimization is unused), exposure (public or internal) and exploit status | Maintainer, with the threat model |
| Dissemination | Pull request with the fix and a one-line impact note; findings in `docs/evidence/` | GitHub PRs |
| Feedback | Add a regression probe for anything that was exploitable; adjust the threat model | `pentest.py`, `test_edge.py` |

## Response targets

| Condition | Target |
| --- | --- |
| Known exploited, or reachable and critical | 48 hours |
| High and reachable | 7 days |
| High but unreachable, or medium | 30 days |
| Low | Next release |

## Worked example from this audit

`npm audit` reported 3 high findings in production dependencies: Next.js 16.3.6 (six advisories including SSRF in image optimization and cache poisoning of statically generated pages) plus two transitive packages. Analysis: image optimization is unused and pages are dynamic, so exploitability here was low, but the fix was a minor bump. Action: upgrade to 16.4.2 and refresh the lockfile; `npm audit` then reported 0. Evidence: `docs/evidence/sca-npm.txt`, `sca-npm-after.txt`.

Python: `pip-audit` on the pinned lock reported no known vulnerabilities (`sca-python.txt`).
