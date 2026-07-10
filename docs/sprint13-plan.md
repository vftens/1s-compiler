# Sprint 13 Plan — Document Export (Excel/PDF) + REST API Expansion

**Branch:** `sprint-13-export-api`
**Target date:** 2026-07-10

---

## Context

Sprint 12 landed a live ERP dashboard (Canvas budget chart, payroll table, PO spend,
org tree) and a `.1s` script query engine that joins in-memory ValueTables with the
SQLite `erp.db`. The REST API now serves budget utilization, payroll, org, and
chart-data endpoints.

**Gap:** There is no way to export ERP data. An accountant can see the budget chart
in a browser, but cannot hand a spreadsheet to their CFO or attach a payslip PDF to
an email. The editor saves nothing — every REPL session is ephemeral. The REST API
has no auth token system, so integrations require browser sessions.

---

## Sprint 13 Scope

### Deliverable 1 — Excel/PDF export endpoints

Three new REST endpoints that write real files and return them as downloads:

```
GET /api/v1/export/payroll?period=YYYY-MM   → payslips.xlsx  (one sheet per employee)
GET /api/v1/export/budget?period=YYYY-MM    → budget.xlsx    (utilization: allocated vs consumed)
GET /api/v1/export/org                      → org_chart.pdf  (tree diagram: SVG → PDF via reportlab)
```

All three are `@login_required`. Files are generated in-memory (BytesIO), never written
to disk. Trilingual: sheet names and column headers in RU/UK/EN based on `Accept-Language`
or `?lang=` param.

**Libraries:**
- `openpyxl` — Excel output (already in the ROADMAP "Excel I/O" backlog, pure Python, no native deps)
- `reportlab` — PDF output (pure Python, handles CJK+Cyrillic fonts)

**Payroll sheet columns:** emp_id, emp_name, period, gross, deductions, net, tax_profile
**Budget sheet columns:** org_id, org_name, period, account, allocated, consumed, remaining, utilization_%
**Org PDF:** Box-and-line tree. Root at top. Each node: name + type + id. Max depth 6.

### Deliverable 1a — Export edge cases (from Eng review)

- `BudgetExporter`: when `allocated = 0`, set `utilization_% = None` → renders as "N/A" in Excel (avoids division-by-zero)
- `OrgPdfExporter`: when DB has no nodes, return a 1-page PDF with "No organizational data" (not 500)

### Deliverable 1b — DX: API discovery endpoint

```
GET /api/v1        → JSON {endpoints: [{method, path, description}]}
```

Lists all v1 endpoints. No auth required. 5-line dict, written inline in server.py.

### Deliverable 2 — REST API token auth (`/api/v1/token`)

Currently all REST endpoints need a browser session cookie. This blocks CLI integrations
and cron jobs.

```
POST /api/v1/token         body: {username, password}  → {token, expires_at}
DELETE /api/v1/token       header: Authorization: Bearer <token>  → revoke
```

Tokens: 64-byte `secrets.token_hex()`. Stored in `data/tokens.json` (path-secured,
same pattern as `erp.db`). TTL: 24 hours default, configurable via `?ttl_hours=N`
(max 168 = 7 days). All existing `@login_required` routes accept either session cookie
OR `Authorization: Bearer <token>` header — decorator extended, not duplicated.

Token file schema:
```json
{
  "tokens": {
    "<hex>": {"user": "admin", "expires": "2026-07-11T10:00:00Z", "created": "2026-07-10T10:00:00Z"}
  }
}
```

### Deliverable 3 — Script editor: save + load user scripts

The `/editor` page runs `.1s` scripts but has no persistence — everything disappears
on close. Add:

- `POST /api/v1/scripts/save`  body: `{name, code}` → saves to `data/user_scripts/<user>/<name>.1s`
- `GET  /api/v1/scripts/user`  → lists user's saved scripts
- `DELETE /api/v1/scripts/<name>` → deletes one script

Files are stored under `data/user_scripts/<username>/`. Path validation: name must
match `[a-zA-Z0-9_-]+\.1s`, no path separators. The editor UI gets a "Save" button
and a "My Scripts" dropdown next to the existing "Examples" dropdown. Scripts in
`data/user_scripts/` are auto-populated on server start alongside `EXAMPLES`.

---

## Architecture

```
src/
  server.py              ← extend login_required + admin_required (Bearer) + 8 new routes
                            + global @app.errorhandler (400/401/404/405/500 → JSON)
  runtime/
    export.py            ← NEW: PayrollExporter, BudgetExporter, OrgPdfExporter
                            (reportlab: lazy import; erp.db missing → 503)
    token_auth.py        ← NEW: TokenStore (SQLite erp.db tokens table, NOT tokens.json)
                            TokenStore has no Flask imports; __repr__ masks token value
data/
  user_scripts/          ← NEW (runtime dir, .gitignore'd)
    <username>/
      <name>.1s          ← re.fullmatch([a-zA-Z0-9_-]+\.1s) BEFORE Path() construction
erp.db                   ← ADD tokens table (user, token_hash, expires UTC, created)
src/templates/
  editor.html            ← extend: name-prompt modal, Save (idle/saving/error states),
                            My Scripts dropdown (placeholder when empty), active-script tracking
                            Toolbar order: Run / Examples / My Scripts / Save
                            Save: overwrites current; Save-as-new: separate action
```

**Token table schema (SQLite in erp.db):**
```sql
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY,   -- sha256(raw_token), not raw
    user       TEXT NOT NULL,
    role       TEXT NOT NULL,
    expires    TEXT NOT NULL,      -- ISO 8601 UTC, e.g. 2026-07-11T10:00:00Z
    created    TEXT NOT NULL
);
```
TTL is server-side config only (no user-controlled `?ttl_hours=`). Default 24h.

`export.py` and `token_auth.py` are standalone modules — no circular imports with
`erp_query.py` or `persistence.py`.

---

## Security

- Token file and user_scripts dir: same path-jail pattern as `AttachDB` (Sprint 12)
- `token_auth.py`: constant-time comparison (`hmac.compare_digest`) for token lookup
- Export endpoints: read-only queries against `erp.db` (already read-only in Sprint 12)
- Script save: filename sanitized (regex + Path().name), no directory traversal
- Token TTL enforced on every request (not just creation)
- Expired tokens purged on each `TokenStore.load()` call (lazy GC, no background thread)
- 401 responses include `hint` field for developer actionability (e.g. "use Authorization: Bearer <token> or log in via /login")

---

## Test Plan

New test file: `tests/test_sprint13.py` (target: **32 tests** → ~598 total)

```
TestPayrollExport (6)
  test_payroll_xlsx_returns_200
  test_payroll_xlsx_content_type_is_xlsx
  test_payroll_xlsx_has_correct_columns
  test_payroll_xlsx_trilingual_ru
  test_payroll_unauthenticated_returns_401_or_redirect
  test_payroll_empty_period_returns_header_only_sheet        ← added (Eng)

TestBudgetExport (5)
  test_budget_xlsx_returns_200
  test_budget_xlsx_utilization_pct_computed
  test_budget_allocated_zero_returns_na_cell
  test_budget_empty_period_returns_empty_sheet
  test_budget_period_isolation                               ← added (Eng)

TestOrgPdfExport (3)
  test_org_pdf_returns_200
  test_org_pdf_content_type_is_pdf
  test_org_pdf_empty_db_returns_placeholder_page

TestTokenAuth (9)
  test_create_token_returns_token_and_expires_at
  test_token_accepted_on_protected_api_endpoint
  test_expired_token_rejected
  test_invalid_token_rejected
  test_revoke_token
  test_wrong_password_returns_401
  test_ttl_is_server_side_only (no ?ttl_hours= param)       ← changed (CEO)
  test_401_body_identical_for_wrong_password_vs_nonexistent_user  ← added (CEO)
  test_token_expiry_at_exact_boundary                        ← added (Eng)

TestUserScripts (7)
  test_save_script
  test_list_user_scripts
  test_delete_script
  test_path_traversal_blocked
  test_invalid_name_rejected
  test_session_isolation
  test_save_409_on_name_collision                            ← added (Design/Eng)

TestLoginRequiredDecorator (3)
  test_decorator_accepts_session_cookie
  test_decorator_accepts_bearer_token
  test_decorator_rejects_neither_returns_401

TestAdminRequiredWithBearer (1)
  test_admin_required_accepts_bearer_if_role_admin           ← added (Eng)

TestApiDiscovery (1)
  test_api_v1_returns_endpoint_list_with_auth_required_field

TestDependencyGraceDegradation (1)
  test_org_pdf_without_reportlab_returns_503                 ← added (Eng)
```

---

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|---------|
| 1 | CEO | Export library: openpyxl + reportlab | Mechanical | P1+P5 | Pure Python, no native deps, Cyrillic support | xlsxwriter+weasyprint (needs GTK on Windows) |
| 2 | CEO | Full 3-deliverable scope | Mechanical | P2 | All in blast radius, <1 day CC effort | Trim D3 (script save) |
| 3 | CEO | **tokens → SQLite table in erp.db, not tokens.json** | Mechanical | P4+P5 | erp.db already exists; WAL handles concurrency; JSON corrupts under concurrent writes on Windows | tokens.json |
| 4 | CEO | **Rate limiting on POST /api/v1/token (5 req/min/IP)** | Mechanical | P1 | Without it the endpoint is brute-forceable | Skip |
| 5 | CEO | **Remove user-controlled ?ttl_hours= param; TTL is server-side config only** | Mechanical | P5 | Clients should not control their own token lifetime | Keep param |
| 6 | CEO | **401 hint: identical body for wrong password and nonexistent user** | Mechanical | P5 | Different messages expose username existence (user enumeration attack) | Distinct hints |
| 7 | CEO | **Per-user script count limit: 50 scripts max** | Mechanical | P1 | No quota = storage DoS vector | Skip |
| 8 | Design | Save button: modal/inline name prompt with regex pattern shown in plain language | Mechanical | P5 | Unnamed save = broken UX; discovered on first test | Silent timestamp name |
| 9 | Design | Save button: 3 states — idle / saving (disabled+spinner) / error (toast+retry) | Mechanical | P1 | Silent failure = lost work | No feedback |
| 10 | Design | My Scripts dropdown: "No saved scripts yet" placeholder when empty | Mechanical | P5 | Empty dropdown looks broken | Skip |
| 11 | Design | POST /api/v1/scripts/save: return 409 on name conflict; UI prompts overwrite/rename | Mechanical | P1 | Silent overwrite loses work | Silent overwrite |
| 12 | Design | Toolbar order: Run / Examples / My Scripts / Save; aria-label on all controls | Mechanical | P5 | Run is primary; ARIA = accessibility baseline | Unspecified order |
| 13 | Design | Editor tracks active script name; Save overwrites current; Save-as-new is separate | Mechanical | P5 | Without state, Save is ambiguous after load | Single Save button |
| 14 | Eng | login_required sets g.current_user; token_auth.py has zero Flask imports | Mechanical | P5 | Testable without app context; no circular imports | Flask imports in token_auth |
| 15 | Eng | admin_required also reads g.current_user (bearer users with role=admin can reach admin routes) | Mechanical | P1 | Otherwise bearer tokens locked out of admin forever | Leave broken |
| 16 | Eng | erp.db missing → catch OperationalError → 503 with human-readable message | Mechanical | P5 | New installs get clear error, not 500 | Unhandled exception |
| 17 | Eng | reportlab: lazy import inside OrgPdfExporter.__init__; ImportError → 503 "install reportlab" | Mechanical | P5 | Optional dep must not hard-fail startup | Module-level import |
| 18 | Eng | Add test_token_expiry_at_exact_boundary (expires=now tested at now and now+1s) | Mechanical | P1 | Off-by-one in TTL check is a real bug class | Skip |
| 19 | Eng | Add test_script_save_409_on_name_collision | Mechanical | P1 | Silent overwrite = data loss; behavior must be tested | Skip |
| 20 | Eng | Add test_export_period_isolation (2026-06 data must not appear in 2026-07 export) | Mechanical | P1 | Period filter must be tested for correctness | Skip |
| 21 | Eng | re.fullmatch() on script name before any Path() construction | Mechanical | P5 | Eliminates Windows drive-letter path traversal edge case | Path().name alone |
| 22 | Eng | TokenStore: mask token value in __repr__; document no-logging rule in module docstring | Mechanical | P5 | Prevent accidental token leakage to debug logs | Skip |
| 23 | DX | GET /api/v1 includes auth_required, query_params, content_type, example_response per endpoint | Mechanical | P1 | Developer can't use an endpoint they don't understand | Bare {method,path,description} |
| 24 | DX | expires_at documented as ISO 8601 UTC (Z suffix) in API response and plan | Mechanical | P5 | Timezone ambiguity = silent bugs in client code | Undocumented |
| 25 | DX | 5xx on POST /api/v1/token: document that request is safe to retry | Mechanical | P5 | Retry safety is a developer contract | Skip |
| 26 | DX | Export endpoints: Content-Disposition: attachment; filename="payroll_{period}.xlsx" + correct MIME type | Mechanical | P1 | Without this, browser/client can't name or open the file | Skip |
| 27 | DX | Add 5-line Python Bearer auth code example to docs or GET /api/v1 discovery response | Mechanical | P5 | First-time auth is non-obvious; example eliminates support burden | Skip |
| 28 | DX | Register global @app.errorhandler for 400/401/404/405/500 returning JSON | Mechanical | P5 | Flask default HTML errors break JSON client contracts | Skip |

---

## GSTACK REVIEW REPORT

| Review | Runs | Last Run | Status | Unresolved |
|--------|------|----------|--------|------------|
| CEO Review | 1 | 2026-07-10 | ✅ clean (28 decisions; 3 strategic concerns at gate) | 0 |
| Design Review | 1 | 2026-07-10 | ✅ clean (6 mechanical fixes applied) | 0 |
| Eng Review | 1 | 2026-07-10 | ✅ clean (9 mechanical fixes; 32-test plan) | 0 |
| DX Review | 1 | 2026-07-10 | ✅ clean (6 mechanical fixes; DX 7.5→9/10) | 0 |
| Dual Voices | 1 | 2026-07-10 | [subagent-only] — Codex CLI unavailable | — |
