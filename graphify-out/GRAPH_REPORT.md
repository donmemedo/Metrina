# Graph Report - Metrina  (2026-10-22)

## Corpus Check
- 29 files · ~96,507 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 12 file(s) not represented in the graph (top: (none) 7, .log 2, .example 1)

## Summary
- 239 nodes · 427 edges · 11 communities (8 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `aeeaabff`
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

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 16 edges
2. `useApp()` - 13 edges
3. `Dashboard()` - 12 edges
4. `track()` - 11 edges
5. `post()` - 10 edges
6. `Icon()` - 10 edges
7. `simulate()` - 9 edges
8. `PostPage()` - 8 edges
9. `Area()` - 8 edges
10. `react` - 8 edges

## Surprising Connections (you probably didn't know these)
- `7.4 Frontend performance, suspects from code reading, not yet measured` --references--> `Num()`  [INFERRED]
  HANDOFF.md → frontend/components/charts.tsx
- `5. Known defects in this session's edit — fix these first` --references--> `build_overview()`  [INFERRED]
  HANDOFF.md → backend/app.py
- `5. Known defects in this session's edit — fix these first` --references--> `track()`  [INFERRED]
  HANDOFF.md → backend/app.py
- `3. Project map and how to run it` --references--> `usePoll()`  [INFERRED]
  HANDOFF.md → frontend/components/shell.tsx
- `5. Known defects in this session's edit — fix these first` --references--> `prune()`  [INFERRED]
  HANDOFF.md → backend/app.py

## Import Cycles
- None detected.

## Communities (11 total, 3 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.07
Nodes (28): analyze(), bucket(), build_overview(), classify(), deseason(), Event, evict(), forecast() (+20 more)

### Community 1 - "app/page.tsx"
Cohesion: 0.12
Nodes (31): Dashboard(), Kpi(), KV, Overview, Row, Post, PostPage(), STAGE_COLOR (+23 more)

### Community 2 - "shell.tsx"
Cohesion: 0.09
Nodes (21): metadata, RootLayout(), viewport, AppCtx, Ctx, IconName, NAV, PATHS (+13 more)

### Community 3 - "time"
Cohesion: 0.13
Nodes (7): call(), hp(), raw(), reader(), slow(), writer(), best()

### Community 4 - "package.json"
Cohesion: 0.09
Nodes (22): dependencies, @fontsource-variable/inter, @fontsource-variable/vazirmatn, next, react, react-dom, devDependencies, @types/node (+14 more)

### Community 5 - "compilerOptions"
Cohesion: 0.11
Nodes (18): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+10 more)

### Community 6 - "7. Remaining work, in order"
Cohesion: 0.12
Nodes (16): prune(), headers, 1. What the owner asked for, 2. Status at a glance, 3. Project map and how to run it, 5. Known defects in this session's edit — fix these first, 6. Audit workflows — what happened and how to re-run, 7.1 Fix section 5, then commit (+8 more)

### Community 7 - "auth"
Cohesion: 0.15
Nodes (11): auth(), client_ip(), deny(), Guard, send_with_headers(), limited(), sec_event(), guard() (+3 more)

## Knowledge Gaps
- **4 isolated node(s):** `@types/node`, `@types/react`, `@types/react-dom`, `typescript`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 115 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Metrina — session handoff (security, pentest, performance, Apple-style UX)` connect `7. Remaining work, in order` to `auth`?**
  _High betweenness centrality (0.392) - this node is a cross-community bridge._
- **What connects `@types/node`, `@types/react`, `@types/react-dom` to the rest of the system?**
  _4 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07142857142857142 - nodes in this community are weakly interconnected._
- **Why does `3. Project map and how to run it` connect `7. Remaining work, in order` to `app/page.tsx`?**
  _High betweenness centrality (0.340) - this node is a cross-community bridge._
- **Should `app/page.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.12280701754385964 - nodes in this community are weakly interconnected._
- **Why does `usePoll()` connect `app/page.tsx` to `shell.tsx`, `7. Remaining work, in order`?**
  _High betweenness centrality (0.314) - this node is a cross-community bridge._
- **Should `shell.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.09032258064516129 - nodes in this community are weakly interconnected._