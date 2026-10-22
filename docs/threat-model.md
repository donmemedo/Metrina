# Threat model

## Assets and actors

| Asset | Why it matters |
| --- | --- |
| Availability of the dashboard and beacon collector | Publishers watch it live; the collector is public |
| Integrity of analytics | Fake pageviews mislead editorial decisions |
| Confidentiality of analytics | Competitors would value another outlet's traffic. Today **public by design** |
| Host and container | Standard |

Actors: anonymous internet user, malicious publisher or site visitor (can post beacons), competitor, supply-chain attacker (npm/PyPI/images).

## Trust boundaries

| Boundary | Crossing data | Control |
| --- | --- | --- |
| Internet → edge | Everything | Caddy timeouts, 1 MB body cap, forced `X-Forwarded-For` |
| Edge → backend/frontend | Proxied requests | Internal network, no published ports |
| Third-party page → `/api/track` | Beacon JSON | Length framing, 4 KB cap, 120/min/IP, schema and host pattern |
| User text → `/api/nlp` | Up to 20,000 chars | 64 KB cap, 30/min/IP, linear-time analysis |
| Beacon text → dashboard | Titles, URLs | React escaping; CSP forbids inline script |

## Attack tree

Root: **degrade or mislead the analytics service.** `OR` = any branch suffices, `AND` = all required. Cost / skill / detectability in brackets.

```
Root
├─ OR 1. Make it unavailable
│   ├─ T1 chunked body to bypass the cap, exhaust memory   [low/low/log: no_length]  FIXED (411)
│   ├─ T2 one 20k-char NLP request freezes the loop         [low/low/slow requests]   FIXED (84 s → 0.04 s)
│   ├─ T3 flood from many IPs                                [medium/low/rate_limited] PARTIAL: per-IP limits, edge timeouts; no global shed except --limit-concurrency 200
│   └─ AND slowloris on the edge: hold many sockets          [low/low]                 MITIGATED by Caddy read timeouts. UNVERIFIED (Caddy not run here)
├─ OR 2. Mislead the data
│   ├─ T5 post fake pageviews for any host/URL               [low/low/rate_limited]    OPEN: needs per-site write keys
│   ├─ T6 forge X-Forwarded-For to get unlimited quota       [low/low]                 FIXED: last entry, edge overwrites
│   ├─ T7 craft referrers (netflix.com read as x.com)        [low/low]                 FIXED: hostname match
│   └─ T8 evict real pages with junk URLs                    [medium/low]              PARTIAL: least-viewed eviction; real pages with traffic survive
├─ OR 3. Read the data
│   └─ T4 read /api/overview as an anonymous visitor         [none/none]               OPEN BY DESIGN. API token injection for visitors was a confused deputy and was withdrawn
├─ OR 4. Run script in a victim's browser
│   └─ AND stored title with markup + a render path that does not escape   [-]         BLOCKED: React escapes, CSP script-src nonce. 0 violations in headless Chrome
└─ OR 5. Supply chain
    ├─ vulnerable Next.js (6 high advisories)               [none]                    FIXED (16.4.2)
    └─ tampered tracker.js on publisher sites                [high]                    OPEN: no SRI, 1 h cache. Version the URL and publish a hash
```

## STRIDE summary

| | Finding |
| --- | --- |
| Spoofing | Client IP spoofing fixed. No identity on beacons (T5) |
| Tampering | Body framing fixed. Beacon content unauthenticated |
| Repudiation | Denials logged as `security_event`, bounded volume |
| Information disclosure | Docs, banners, CORS closed. Analytics readable by design (T4) |
| Denial of service | T1, T2 fixed; flood resistance depends on the edge |
| Elevation | Non-root, read-only containers, no capabilities, no-new-privileges |

## Residual risk, ranked

1. T4/T5: no authentication. Acceptable for a demo, blocking for any real customer data.
2. T3: global flood protection is thin without a CDN or WAF.
3. Supply chain: images pinned by tag, not digest; CI untested.
