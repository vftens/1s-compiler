# Sprint 16 — One-Click Demo Runner + Auto-Seed on Start

## Theme

Make demos run with a single click, and auto-seed sample data when the server starts so the ERP dashboard is populated on first visit.

## Background

The server already has:
- `/dashboard` — lists all scripts from the `SCRIPTS` dict with a Run button each
- `/run/<name>` — renders `run.html`, user presses play → SSE via `/stream/<name>`
- LP demo scripts: `demo_lp_solver_en.1s`, `demo_lp_procurement_ru.1s`, `demo_lp_production_uk.1s`, `demo_lp_staffing_en.1s`, `demo_lp_budget_ru.1s`, `demo_lp_resources_uk.1s`
- `demo_erp_full_*.1s`, `demo_reports_*.1s`, `demo_accounting_*.1s` etc.

**Problem**: most `demo_*` scripts are not registered in the `SCRIPTS` dict, so they don't appear on the dashboard and can't be run from the UI. The LP demo page (`/lp-solver`) exists but requires manual data entry; the 1S-script demos are not surfaced.

## Goals

### G1 — One-click Demo Page
A dedicated `/demo` page ("Quick Demo") that:
- Lists curated demo scripts by category (LP Solver, ERP Full Cycle, Reports)
- Each demo has a "Run" button that streams output inline (SSE, same as existing run.html)
- "Run All" button that chains demos sequentially (one finishes → next starts)
- No login required for view; run still requires login (existing `@login_required` on `/stream/<name>`)

### G2 — Register Missing Demo Scripts
Add all `demo_lp_*`, `demo_erp_full_*`, `demo_reports_*`, `demo_erp_query_*`, `demo_breakeven_*`, `demo_construction_*`, `demo_manufacturing_*`, `demo_payroll_tax_*`, `demo_persistence_*`, `demo_trade_*`, `demo_vat_balance_*`, `demo_zup_*` scripts to the `SCRIPTS` dict so they appear on the existing `/dashboard`.

### G3 — Auto-seed on Server Start
When `run_server()` is called (or `python -m src.cli serve`), check if `data/erp.db` has `budget_entries` rows; if empty (or db missing), auto-run `examples/demo_erp_full_en.1s` in a background thread to seed the ERP with sample data. After seeding completes, log "Demo data seeded successfully".

### G4 — Dashboard "Highlighted" Demo Banner
On the existing `/dashboard`, add a highlighted card at the top linking to `/demo` with a description: "Click here to see all 1S demos in action".

## Non-Goals / Deferred

- Persistent demo output storage (output is ephemeral, SSE only)
- Demo auto-refresh / re-run scheduling
- Auth bypass for demo running (security: `/stream/<name>` stays `@login_required`)

## Files to Change

| File | Change |
|------|--------|
| `src/server.py` | Add ~40 scripts to `SCRIPTS` dict; add `/demo` route; add `_auto_seed_on_start()` background function called in `run_server()`; add `GET /api/v1/demo/run-all` SSE endpoint |
| `src/templates/demo.html` | New page: curated demo grid + inline SSE output panels |
| `src/templates/dashboard.html` | Add "Quick Demo" banner card at top |

## GSTACK REVIEW REPORT

| Phase | Reviewer | Verdict |
|-------|----------|---------|
| CEO   | C1–C5    | PROCEED WITH CHANGES |
| Design| D1–D5    | APPROVED WITH CHANGES |
| Eng   | E1–E8    | APPROVED WITH CHANGES |
| DX    | X1–X6    | APPROVED WITH CHANGES |

### CEO Decisions (C1–C5)
- **C1 APPROVE** — G2 (register scripts) is the foundation; ships in same PR
- **C2 REVISE** — G3 seed thread: add "seeding in progress" amber banner; log timing
- **C3 REVISE** — Cut "Run All" SSE endpoint to Sprint 17; per-demo SSE only this sprint
- **C4 APPROVE** — G4 banner; write real copy naming LP Solver / ERP / Reports
- **C5 REVISE** — Add test for `/stream/<name>` returns 401 when unauthenticated

### Design Decisions (D1–D5)
- **D1 APPROVE** — Two-col layout: left sidebar with category anchors, right content with section-per-category
- **D2 APPROVE W/ CHANGES** — SSE panel collapsed by default, expands in-place below card on Run click
- **D3 APPROVE** — Seeding: amber full-width alert bar (not a card); Ready: blue banner; no meta-refresh on Ready
- **D4 APPROVE** — status-badge pattern from run.html; if card B clicked while A streams, close A's EventSource first
- **D5 REVISE** — No hero section; page-title + subtitle; back button to dashboard; no CDN

### Engineering Decisions (E1–E8)
- **E1 REVISE** — threading.Event + Lock; check rows inside lock (TOCTOU); log ERROR when seed subprocess fails
- **E2 APPROVE** — module-level `_seed_state` str; `/api/v1/seed-state` JSON endpoint; template renders amber bar server-side initially
- **E3 REVISE** — route passes `categories` (server-grouped via `DEMO_CATEGORIES` ordered dict), `seed_state`, `user`
- **E4 APPROVE** — mock Popen at `src.server`; `_check_seed_needed()` helper patchable; tmpdir SQLite
- **E5 REVISE** — `/stream/<name>`: guard `name not in SCRIPTS → abort(404)` BEFORE path construction
- **E6 APPROVE** — single EventSource at a time (client-side); document mobile Safari teardown caveat
- **E7 APPROVE** — MODULE_ICONS key: `"LP Solver"` for all `demo_lp_*` scripts
- **E8 REVISE** — `_register_demo_scripts()` globs `EXAMPLES/"demo_*.1s"`, derives title/lang from filename, merges into SCRIPTS; hand-registered entries not clobbered

### DX Decisions (X1–X6)
- **X1 REVISE** — Exact 20 tests: 3 registration, 3 demo route, 3 stream guard, 7 seed logic, 1 idempotency, 2 banner, 1 api/scripts
- **X2 REVISE** — No `_reset_seed_state()` in prod code; use `conftest.py` autouse fixture with monkeypatch
- **X3 REVISE** — Add `GET /api/v1/seed-state` endpoint this sprint (not Sprint 17)
- **X4 APPROVE** — No new doc file; add one sentence to README + SERVICES.md
- **X5 BLOCK** — `_register_demo_scripts()` must be called in `run_server()`, NOT at import time
- **X6 REVISE** — 7 required `[seed]` log lines defined; path-traversal attempts logged at WARNING

### Deferred to Sprint 17
- "Run All" chained SSE endpoint (`GET /api/v1/demo/run-all`)
- Mobile Safari EventSource teardown fix
- Demo output persistence / history

## Test Plan

- `tests/test_sprint16.py` — ~20 tests covering:
  - All new `demo_lp_*` scripts appear in `GET /api/v1/scripts`
  - `/demo` renders 200
  - `/stream/demo_lp_solver_en` streams and ends with `__DONE__`
  - Auto-seed logic: when db has no rows, seed runs; when db has rows, seed skipped
  - Demo page lists expected script categories
