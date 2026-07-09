<!-- /autoplan restore point: ~/.gstack/projects/vftens-1s-compiler/main-autoplan-restore-20260709.md -->

# Sprint 12 Plan — Query Engine Extension + ERP Dashboard

**Branch:** main  
**Base commit:** b2f5ebc  
**Date:** 2026-07-09  

---

## Goal

Two deliverables:

1. **Query engine extension** — `src/runtime/query.py` can now query the Sprint 11 SQLite persistence tables (`org_nodes`, `budget_allocations`, `budget_entries`, `payroll_results`, `workflow_rules`) directly from `.1s` scripts using `ВЫБРАТЬ / ОБЕРІТЬ / SELECT` syntax.

2. **ERP Dashboard** — a live `/erp-dashboard` page in the Flask Web UI that pulls from `data/erp.db` via the Sprint 11 REST API endpoints and shows:
   - Budget utilization bar chart (per org/period)
   - Payroll summary table (latest period)
   - Org tree (department hierarchy)
   - Recent PO spend (top 10 by doc_ref)

Full trilingual RU/UK/EN throughout.

---

## Scope

### Deliverable 1: Query Engine → SQLite persistence tables

**File:** `src/runtime/query.py`

Current state: `_Query.Execute()` uses an in-memory SQLite DB fed by registered `_ValueTable`s. It cannot reach `data/erp.db`.

Needed: a new `_Query.AttachDB(db_path)` / `AttachDatabase()` method that allows queries to join/read the persisted ERP tables alongside in-memory tables.

Tables exposed from `erp.db`:
- `org_nodes` — columns: `id, name, type, parent_id, org_name`
- `budget_allocations` — columns: `org_id, period, account, amount`
- `budget_entries` — columns: `entry_type, org_id, period, amount, doc_ref, account`
- `payroll_results` — columns: `period, emp_id, emp_name, gross, net, tax_profile`
- `payroll_result_lines` — columns: `result_id, name, amount, line_type`
- `workflow_rules` — columns: `doc_type, rules_json`

Implementation approach: `_Query.Execute()` detects if `_db_path` is set. If set, opens `erp.db` directly as the primary connection (read-only: `sqlite3.connect("file:{}?mode=ro".format(path), uri=True)`), sets `PRAGMA journal_mode=WAL`, then loads any registered `_ValueTable`s as TEMP tables into it. If `_db_path` is NOT set, uses `:memory:` as before (backward compatible). Path is validated: must resolve to inside `ROOT/data/` — any traversal raises `ValueError`. Column type inference scans all rows for first non-None value before deciding type, fallback to `NUMERIC`.

Trilingual aliases:
- `AttachDB` / `ПрисоединитьБД` / `ПриєднатиБД`
- `AttachDatabase` / `ПрисоединитьБазу` / `ПриєднатиБазу`

Demo script: `examples/demo_query_erp_en.1s`, `demo_query_erp_ru.1s`, `demo_query_erp_uk.1s`

### Deliverable 2: ERP Dashboard page

**New file:** `src/templates/erp_dashboard.html`  
**Modified file:** `src/server.py` — add `GET /erp-dashboard` route + `GET /api/v1/erp/chart-data`

Dashboard layout (hierarchy: finance manager monthly close view):
- Header: "Monthly ERP Summary / Щомісячний ЕРП Звіт" + YYYY-MM period filter (applies to ALL sections)
- Row 1 (full width): Budget Utilization — horizontal bar chart: allocated=`#4A90D9`, consumed=`#E85D5D`, values inline, y-axis labels truncated @20 chars, font `13px monospace`, row height 32px, canvas 100% container width
- Row 2 (two columns): Payroll Summary (left) + Recent PO Spend (right) — tables with emp_name/period/gross/net and doc_ref/committed/consumed respectively
- Row 3 (collapsible, below fold): Org Tree — `<details><summary>` nested list of org_nodes hierarchy

Per-section states (all 4 sections):
- Loading: `<div class="loading">⟳ Loading…</div>` while fetch in flight
- Error: `<div class="error">⚠ Could not load data</div>` on HTTP error
- Empty: `<div class="empty">No data for selected period</div>` on empty array

Tech: pure HTML/CSS + vanilla JS `fetch()` calls to the existing REST endpoints. No external CDN. Chart via inline `<canvas>` + canvas 2D API (no Chart.js — no CDN allowed by project).

Auth: `@login_required` on the dashboard route.

Navigation: add "ERP Dashboard" link to `dashboard.html`.

---

## Files changed

| File | Change |
|------|--------|
| `src/runtime/query.py` | Add `AttachDB()` / `Execute()` reads attached erp.db |
| `src/server.py` | Add `/erp-dashboard` + `/api/v1/erp/chart-data` |
| `src/templates/erp_dashboard.html` | New ERP dashboard page |
| `src/templates/dashboard.html` | Add ERP Dashboard nav link |
| `src/runtime/__init__.py` | Export `AttachDB` alias if needed |
| `examples/demo_query_erp_en.1s` | Demo: query erp.db from script |
| `examples/demo_query_erp_ru.1s` | Demo: Russian keywords |
| `examples/demo_query_erp_uk.1s` | Demo: Ukrainian keywords |
| `tests/test_sprint12.py` | New: 20+ tests |
| `README.md` | Update features + examples |
| `ROADMAP.md` | Add v1.0 Sprint 12 section |
| `docs/sprint12-results.md` | Post-sprint summary |

---

## Out of scope

- Multi-currency / exchange rates (v1.0)
- 1C `.dt` / `.cf` infobase reader (v1.0)
- React Native / PWA mobile UI (v1.0)
- Multi-tenant SaaS isolation (v1.0)
- External CDN dependencies in dashboard (blocked — CSP policy)

---

## What already exists

| Sub-problem | Existing code |
|-------------|--------------|
| In-memory query engine | `src/runtime/query.py` — `_Query`, `_translate_query`, `QueryResult` |
| ERP SQLite tables | Created by `src/runtime/persistence.py` Sprint 11 functions |
| REST API endpoints | `src/server.py` — `/api/v1/org`, `/api/v1/budget/utilization`, `/api/v1/payroll/history`, `/api/v1/erp/summary` |
| Flask templates | `src/templates/` — base.html, dashboard.html, login.html, run.html, analytics.html |
| Login/auth | `src/server.py` — `@login_required`, `session["user"]` |
| ERPQuery class | `src/runtime/erp_query.py` — `budget_utilization`, `payroll_history`, `po_spend_by_supplier` |
| Trilingual pattern | All Sprint 7-11 modules — EN + RU + UK alias convention |

---

## Test plan

- `TestQueryAttachDB` — attach erp.db, query org_nodes, verify rows returned
- `TestQueryERPJoin` — join in-memory `_ValueTable` with erp.db table
- `TestQueryERPFilters` — WHERE clause on budget_entries
- `TestQueryTrilingualAttach` — RU/UK alias method names work
- `TestDashboardRoute` — GET /erp-dashboard returns 200 (logged-in user)
- `TestChartDataAPI` — GET /api/v1/erp/chart-data returns budget + payroll JSON
- `TestDashboardUnauth` — GET /erp-dashboard without login redirects to /login
- `TestQueryEmptyDB` — AttachDB on non-existent path returns empty result with warning (not crash)
- `TestQueryCorruptDB` — AttachDB on corrupt file raises sqlite3.DatabaseError (not swallowed)
- `TestQueryPathInjection` — AttachDB("../../etc/passwd") raises ValueError
- `TestQueryConcurrent` — two simultaneous Execute() calls on same erp.db return correct results (WAL)
- `TestQueryNoneNumeric` — ValueTable with None in Decimal column: SUM() still works after type-inference fix
- `TestChartDataNoPeriod` — GET /api/v1/erp/chart-data with no period param returns current-month data (not 500)
- `TestPayrollBonusBug` — POST /api/v1/payroll/calculate with bonus assigns bonus to correct emp_id (regression for server.py:661 fix)
- Integration demo scripts run end-to-end

---

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|---------|
| 1 | CEO | Accept all 4 premises | Mechanical | P6 | All premises are internally consistent and technically sound | — |
| 2 | CEO | Approach A: AttachDB explicit call (not implicit table resolution) | Taste | P5 | Explicit AttachDB is readable in 3 seconds; implicit table access is a surprise | Approach B (implicit), Approach C (htmx) |
| 3 | CEO | Add empty-state handling to all 4 dashboard sections | Mechanical | P1 | Every first-time user hits empty db; cold-start UX must be defined | — |
| 4 | CEO | Keep Deliverable 1 (AttachDB) — surface CEO concern at gate | Taste | P6 | CEO subagent flagged as potentially synthetic use case; one-model signal only; bias toward action | Pause Deliverable 1 |
| 5 | CEO | Fix in blast radius: server.py:661 ab["emp_id"] → bon["emp_id"] | Mechanical | P2 | In blast radius (server.py modified this sprint) | Defer to Sprint 13 |
| 6 | Design | Reorder sections: Budget (full) → Payroll+PO (side-by-side) → Org (collapsible) | Mechanical | P5 | Finance manager primary user needs budget status first | Original order |
| 7 | Design | Per-section loading/error/empty states | Mechanical | P1 | Async fetch without states leaves users confused | — |
| 8 | Design | Period filter applies to ALL sections | Mechanical | P5 | Inconsistent filter scope is a perpetual source of bugs | Section-specific filters |
| 9 | Design | Canvas spec: allocated=#4A90D9, consumed=#E85D5D, inline values, 32px rows | Mechanical | P1 | Unspecified canvas leaves every choice as a guess | — |
| 10 | Design | Canvas labels: 20-char truncation + ellipsis, 13px monospace, dynamic height | Mechanical | P5 | Multilingual org names overflow without truncation rule | — |
| 11 | Design | Primary user: finance manager monthly close | Taste | P5 | Most likely dashboard user; surfacing at gate | CEO view, admin view |
| 12 | Eng | Execute() with _db_path: open erp.db as primary connection (ro mode), load ValueTables as TEMP | Mechanical | P5 | :memory: + ATTACH has cross-join limitations; file-primary avoids the problem entirely | ATTACH DATABASE approach |
| 13 | Eng | Validate AttachDB path stays within ROOT/data/ | Mechanical | P1 | Path traversal via user-provided .1s script string | Accept any path |
| 14 | Eng | PRAGMA journal_mode=WAL on first open | Mechanical | P1 | Concurrent readers without WAL → database locked errors | Single-connection model |
| 15 | Eng | Fix server.py:661 ab["emp_id"] → bon["emp_id"] | Mechanical | P2 | Existing bug in blast radius; bonuses assigned to wrong employees | Defer |
| 16 | Eng | Distinguish FileNotFoundError vs sqlite3.DatabaseError in AttachDB | Mechanical | P1 | Different causes need different recovery paths | Swallow all as empty result |
| 17 | Eng | chart-data endpoint: require period or default to current month + LIMIT 500 | Mechanical | P5 | Unbounded query on 3yr DB returns tens of thousands of rows | No cap |
| 18 | Eng | Column type detection: scan all rows for first non-None before deciding type | Mechanical | P1 | First-row None → TEXT affinity → SUM() broken for numeric fields | First-row-only inference |
| 19 | DX | Add fourth demo demo_query_erp_join_en.1s showing ValueTable JOIN org_nodes | Mechanical | P1 | Join is the differentiating feature; three demos don't cover it | Three demos only |
| 20 | DX | AttachDB error message shows: allowed dir, received path, escape hatch | Mechanical | P5 | Opaque errors have zero recovery path for developer | Python raw exception |
| 21 | DX | 1S_ALLOW_ANY_DB_PATH=1 env var escape hatch for CLI mode | Mechanical | P1 | CI pipelines and test DBs need unrestricted path access | Hard restriction |
| 22 | DX | Add erp.db table schema to README.md | Mechanical | P1 | Developer can't query tables they don't know exist | — |
| 23 | DX | Add Ukrainian aliases to _Query: УстановитиПараметр, Виконати, ЗареєструватиТаблицю, Запит | Mechanical | P1 | Trilingual contract is core project identity; UK was missing | RU+EN only |
| 24 | DX | AttachDB("erp.db") auto-resolves to data/erp.db (implicit data/ prefix) | Taste | P1 (ergonomics) | Saves one path segment every call; convention over config | Require full "data/erp.db" |
