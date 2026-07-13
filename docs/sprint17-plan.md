# Sprint 17 — "Run All" Chained SSE Demo Endpoint

## Theme

Add a single button on the `/demo` page that runs all curated demo scripts sequentially
(one finishes → next starts) with a unified live output stream.

## Background

Sprint 16 shipped:
- `/demo` page with per-card SSE via `/stream/<name>`
- One EventSource at a time enforced client-side
- `_register_demo_scripts()` auto-registers all `demo_*.1s`
- `_auto_seed_on_start()` seeds ERP data on server start

Deferred from Sprint 16:
- "Run All" chained SSE endpoint (`GET /api/v1/demo/run-all`)

## Goals

### G1 — `GET /api/v1/demo/run-all` SSE endpoint
Server-side chained execution: runs a curated ordered list of demo scripts one after
another, streaming all output to one EventSource. Between scripts, emits a separator
line so the client knows which script is running. Ends with `__DONE__` after the last
script finishes. If a script fails (non-zero exit), logs the error, emits an error
line, and continues to the next script (fail-fast is wrong for a demo).

### G2 — "Run All" button on `/demo` page
A prominent button at the top of the demo page ("▶ Run All Demos") that opens a
full-width terminal panel and starts a single EventSource to `/api/v1/demo/run-all`.
While running, the button shows "⟳ Running…" and is disabled. On completion, shows
"✓ Done — Run Again".

### G3 — Curated run-all script list
A module-level `RUN_ALL_SCRIPTS` list in `server.py` that defines the ordered sequence.
Default: LP Solver → ERP Full Cycle → Reports (one script per category, English).
This list is the source of truth for both the endpoint and the test plan.

### G4 — Per-script progress in the unified stream
Each script boundary emits a structured SSE comment/header line the client renders
as a section break:
```
data: ── [1/3] demo_lp_solver_en ──────────────────────
```
Client renders this with `.line-head` CSS (already defined in demo.html).

## Non-Goals / Deferred

- Persistent run-all output log
- User-configurable script ordering
- Parallel execution (intentionally sequential for demo clarity)
- Auth bypass (endpoint stays `@login_required`)

## Files to Change

| File | Change |
|------|--------|
| `src/server.py` | Add `RUN_ALL_SCRIPTS` list; add `GET /api/v1/demo/run-all` SSE route; add to `_API_ENDPOINTS` |
| `src/templates/demo.html` | Add "Run All" button + full-width terminal panel at page top |

## GSTACK REVIEW REPORT

| Phase | Reviewer | Verdict |
|-------|----------|---------|
| CEO   | C1–C5    | PROCEED WITH CHANGES |
| Design| D1–D5    | APPROVED WITH CHANGES |
| Eng   | E1–E7    | APPROVED WITH CHANGES |
| DX    | X1–X5    | APPROVED WITH CHANGES |

### CEO (C1–C5)
- **C1 APPROVE** — Full vertical slice: endpoint + client + list + headers + tests
- **C2 APPROVE** — "Continue on failure" is right; error line format: `[ERROR] <name>: <msg>`
- **C3 APPROVE** — Two files, one constant, one route — minimal blast radius
- **C4 REVISE** — Add test asserting section header format matches `── [N/M] <name>`
- **C5 APPROVE** — All four non-goals correctly deferred

### Design (D1–D5)
- **D1 APPROVE W/ CHANGES** — Hero strip between subtitle and seed banner; NOT sticky header
- **D2 APPROVE** — Unified terminal: `border-radius:8px` all sides, `min-height:220px`, label bar above
- **D3 APPROVE** — `colorLine()` checks `/^── \[\d+\/\d+\]/` first → `.line-head` (teal bold)
- **D4 APPROVE W/ CHANGES** — Button shows `(n/total)` counter; idle/running/done/error states
- **D5 APPROVE** — Per-card Run while Run All active: `stopRunAll()` helper closes `_runAllSource`, resets

### Engineering (E1–E7)
- **E1 APPROVE** — Sequential generator: for-loop over RUN_ALL_SCRIPTS, Popen per script
- **E2 APPROVE** — RUN_ALL_SCRIPTS read-only list; no thread safety concern
- **E3 REVISE** — `proc.wait(timeout=120)`, `TimeoutExpired → proc.kill() + [ERROR] line + continue`
- **E4 APPROVE** — Error format exactly: `f"data: [ERROR] {name}: exit code {proc.returncode}\n\n"`
- **E5 APPROVE** — Add to `_API_ENDPOINTS`: `{"method":"GET","path":"/api/v1/demo/run-all",...}`
- **E6 REVISE** — Mock via `side_effect` list of mocks; collect via `list(generate())` directly
- **E7 REVISE** — Response headers: `X-Accel-Buffering: no, Cache-Control: no-cache`; document disconnect caveat

### DX (X1–X5)
- **X1 APPROVE** — Add 9th test: missing `.1s` file on disk → `[ERROR]` + `__DONE__` (not exception)
- **X2 APPROVE** — `list(generate())` for streaming tests; auth_client.get() only for auth + discovery
- **X3 REVISE** — `reset_seed` fixture required for tests touching module state; add `data/.gitkeep`
- **X4 APPROVE** — `curl -N -H "Authorization: Bearer <TOKEN>"` manual test workflow documented
- **X5 REVISE** — `RUN_ALL_SCRIPTS` is a pure list literal/comprehension; defined after SCRIPTS, no I/O

### Deferred to Sprint 18
- Persistent run-all output log
- User-configurable script ordering
- Client disconnect propagation (Werkzeug dev server limitation)

## Test Plan

`tests/test_sprint17.py` — ~15 tests:
- `RUN_ALL_SCRIPTS` is non-empty and all entries are registered in SCRIPTS
- `/api/v1/demo/run-all` requires login (401 when unauthenticated)
- Endpoint streams all scripts and ends with `__DONE__`
- Section header lines emitted between scripts
- If one script fails, remaining scripts still run
- `/demo` page renders the Run All button
- Run All button present in page body
- Endpoint appears in `GET /api/v1` discovery list
