# Graph Report - Metrina  (2026-10-22)

## Corpus Check
- 40 files · ~101,796 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 7, .log 2, .example 1)

## Summary
- 301 nodes · 484 edges · 20 communities (16 shown, 4 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `140e0ea6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- app.py
- app/page.tsx
- shell.tsx
- time
- package.json
- compilerOptions
- 7. Remaining work, in order
- auth
- ui-audit.mjs
- AGENTS.md
- LAST_Report — Metrina (Parsely Iran) security, performance and UX audit
- Runbook
- Role reviews
- Threat model
- Parsely Iran (Metrina)
- Pen-test report
- UX and accessibility audit
- Threat-intelligence lifecycle for this stack
- implementation-plan.md

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `useApp()` - 13 edges
3. `track()` - 12 edges
4. `Dashboard()` - 12 edges
5. `post()` - 10 edges
6. `Icon()` - 10 edges
7. `simulate()` - 9 edges
8. `build_overview()` - 8 edges
9. `PostPage()` - 8 edges
10. `Area()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `Tech lead` --references--> `build_overview()`  [INFERRED]
  docs/role-reviews.md → backend/app.py
- `7.4 Frontend performance, suspects from code reading, not yet measured` --references--> `Num()`  [INFERRED]
  docs/HANDOFF.md → frontend/components/charts.tsx
- `4. What changed in `backend/app.py`` --references--> `Guard`  [INFERRED]
  docs/HANDOFF.md → backend/app.py
- `What each security control costs` --references--> `Guard`  [INFERRED]
  docs/security-performance.md → backend/app.py
- `5. Known defects in this session's edit — fix these first` --references--> `build_overview()`  [INFERRED]
  docs/HANDOFF.md → backend/app.py

## Import Cycles
- None detected.

## Communities (20 total, 4 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.07
Nodes (25): analyze(), build_overview(), classify(), deseason(), Event, evict(), forecast(), health() (+17 more)

### Community 1 - "app/page.tsx"
Cohesion: 0.12
Nodes (31): Dashboard(), Kpi(), KV, Overview, Row, Post, PostPage(), STAGE_COLOR (+23 more)

### Community 2 - "shell.tsx"
Cohesion: 0.09
Nodes (21): metadata, RootLayout(), viewport, AppCtx, Ctx, IconName, NAV, PATHS (+13 more)

### Community 3 - "time"
Cohesion: 0.10
Nodes (15): bucket(), send_with_headers(), lifespan(), new_bucket(), ticker(), call(), hp(), raw() (+7 more)

### Community 4 - "package.json"
Cohesion: 0.09
Nodes (22): dependencies, @fontsource-variable/inter, @fontsource-variable/vazirmatn, next, react, react-dom, devDependencies, @types/node (+14 more)

### Community 5 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 6 - "7. Remaining work, in order"
Cohesion: 0.12
Nodes (16): prune(), 1. What the owner asked for, 2. Status at a glance, 3. Project map and how to run it, 5. Known defects in this session's edit — fix these first, 6. Audit workflows — what happened and how to re-run, 7.1 Fix section 5, then commit, 7.2 Red team, against the restarted backend (+8 more)

### Community 7 - "auth"
Cohesion: 0.12
Nodes (13): auth(), client_ip(), deny(), Guard, limited(), sec_event(), Architecture, Data flow (+5 more)

### Community 11 - "LAST_Report — Metrina (Parsely Iran) security, performance and UX audit"
Cohesion: 0.22
Nodes (8): 1. Status, 2. Where this started (earlier sessions and memory), 3. Findings and fixes (evidence in `docs/evidence/`; rows 5 and 6 are partly reproduced at the primitive level, noted inline), 4. UX / accessibility, same audit script on old and new build, 5. What I did not do, and why, 6. Run it, 7. Next, in order, LAST_Report — Metrina (Parsely Iran) security, performance and UX audit

### Community 12 - "Runbook"
Cohesion: 0.25
Nodes (7): Detection signals, Incident outline, Protecting the dashboard today (unverified), Rotating the token, Runbook, Settings, Start, stop, test

### Community 13 - "Role reviews"
Cohesion: 0.29
Nodes (6): Blue team, Product owner, QA hints, Red team (remaining ideas, ordered), Role reviews, Tech lead

### Community 14 - "Threat model"
Cohesion: 0.29
Nodes (6): Assets and actors, Attack tree, Residual risk, ranked, STRIDE summary, Threat model, Trust boundaries

### Community 15 - "Parsely Iran (Metrina)"
Cohesion: 0.33
Nodes (5): Configuration, Documentation, Parsely Iran (Metrina), Run it, Tests

### Community 16 - "Pen-test report"
Cohesion: 0.40
Nodes (4): Defended probes (selection), Not covered, Pen-test report, Result

### Community 17 - "UX and accessibility audit"
Cohesion: 0.40
Nodes (4): Measured, before → after, Persian copy against the UX vocabulary, UX and accessibility audit, What changed against the rubric

### Community 18 - "Threat-intelligence lifecycle for this stack"
Cohesion: 0.50
Nodes (3): Response targets, Threat-intelligence lifecycle for this stack, Worked example from this audit

## Knowledge Gaps
- **4 isolated node(s):** `@types/node`, `@types/react`, `@types/react-dom`, `typescript`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 164 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Metrina — session handoff (security, pentest, performance, Apple-style UX)` connect `7. Remaining work, in order` to `auth`?**
  _High betweenness centrality (0.297) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `track()` (e.g. with `Data flow` and `5. Known defects in this session's edit — fix these first`) actually correct?**
  _`track()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@types/node`, `@types/react`, `@types/react-dom` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07390648567119155 - nodes in this community are weakly interconnected._
- **Why does `3. Project map and how to run it` connect `7. Remaining work, in order` to `app/page.tsx`?**
  _High betweenness centrality (0.256) - this node is a cross-community bridge._
- **Should `app/page.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.12280701754385964 - nodes in this community are weakly interconnected._
- **Why does `usePoll()` connect `app/page.tsx` to `shell.tsx`, `7. Remaining work, in order`?**
  _High betweenness centrality (0.237) - this node is a cross-community bridge._