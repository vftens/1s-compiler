# Sprint 15 Plan — Excel/PDF Export + Token Auth + Script Persistence

**Branch:** `sprint-15-export-auth-scripts`
**Target date:** 2026-07-11

---

## Context

Sprints 12–14 landed the ERP dashboard, script query engine, and GLPK LP solver (566 tests).
Sprint 13 was planned and reviewed but never implemented — its scope remains the highest-value
gap in the product. This sprint ships it.

**What's missing:**
- Accountants can see the budget chart but can't export to Excel or attach a PDF
- Every editor session is ephemeral — scripts are lost on close
- REST API requires a browser cookie — CLI integrations and cron jobs are blocked

---

## Deliverable 1 — Excel/PDF Export (`src/runtime/export.py`)

Three REST endpoints, files generated in-memory (BytesIO), never written to disk:

```
GET /api/v1/export/payroll?period=YYYY-MM   → payslips.xlsx  (one sheet per employee)
GET /api/v1/export/budget?period=YYYY-MM    → budget.xlsx    (utilization: allocated vs consumed)
GET /api/v1/export/org                      → org_chart.pdf  (org tree via reportlab)
```

All `@login_required`. Trilingual headers via `?lang=ru|uk|en` (default: `en`).

**Payroll sheet columns:** emp_id, emp_name, period, gross, deductions, net, tax_profile
**Budget sheet columns:** org_id, org_name, period, account, allocated, consumed, remaining, utilization_%
- When `allocated = 0`: `utilization_% = None` → cell renders as "N/A" (avoids div/zero)

**Org PDF:** Box-and-line tree; root at top; each node shows name + type + id; max depth 6.
- Empty DB: return a 1-page PDF with "No organizational data" (not 500).

**Libraries:** `openpyxl` (Excel), `reportlab` (PDF) — pure Python, Cyrillic-safe, no native deps.

### Deliverable 1b — API discovery endpoint

```
GET /api/v1   → JSON {"endpoints": [{method, path, description}]}
```

No auth required. ~10-line dict in `server.py`. Free discoverability.

---

## Deliverable 2 — REST Token Auth (`src/runtime/token_auth.py`)

```
POST /api/v1/token     body: {username, password}              → {token, expires_at}
DELETE /api/v1/token   header: Authorization: Bearer <token>   → revoke
```

- Tokens: 64-byte `secrets.token_hex()`
- Stored in `data/tokens.json` (path-jailed, .gitignore'd)
- TTL: 24h default, `?ttl_hours=N` up to 168 (7 days)
- All existing `@login_required` routes accept session cookie OR `Authorization: Bearer <token>`
- `hmac.compare_digest` for constant-time token comparison
- Expired tokens purged lazily on each `TokenStore.load()`
- `os.replace()` atomic write (prevents corruption on concurrent saves)
- 401 body includes `hint` field: `"use Authorization: Bearer <token> or log in via /login"`

Token file schema:
```json
{
  "tokens": {
    "<hex>": {"user": "admin", "expires": "2026-07-12T10:00:00Z", "created": "2026-07-11T10:00:00Z"}
  }
}
```

---

## Deliverable 3 — Script Editor: Save / Load (`data/user_scripts/`)

```
POST /api/v1/scripts/save     body: {name, code}   → saves to data/user_scripts/<user>/<name>.1s
GET  /api/v1/scripts/user                          → lists user's saved scripts
DELETE /api/v1/scripts/<name>                      → deletes one script
```

- Filename validation: must match `[a-zA-Z0-9_-]+\.1s`, no path separators
- Session isolation: user A cannot read or list user B's scripts
- Editor UI: "Save" button + "My Scripts" dropdown alongside existing "Examples" dropdown
- `data/user_scripts/` auto-populated on server start

---

## Architecture

```
src/
  server.py              ← extend @login_required + 7 new routes + GET /api/v1
  runtime/
    export.py            ← NEW: PayrollExporter, BudgetExporter, OrgPdfExporter
    token_auth.py        ← NEW: TokenStore (load/save/validate/create/revoke)
data/
  tokens.json            ← runtime only (.gitignore'd)
  user_scripts/          ← runtime dir (.gitignore'd)
    <username>/
      <name>.1s
src/templates/
  editor.html            ← extend: Save button + My Scripts dropdown
```

---

## Security

| Concern | Mitigation |
|---------|-----------|
| Token guessing | 64-byte hex = 128 hex chars; brute-force infeasible |
| Token timing attack | `hmac.compare_digest` on every lookup |
| Token file corruption | `os.replace()` atomic write |
| Script path traversal | `Path(name).name` == name assertion + regex `[a-zA-Z0-9_-]+\.1s` |
| Script session isolation | scripts stored under `data/user_scripts/<session_user>/` |
| Export data leakage | endpoints are `@login_required`; read-only against `erp.db` |
| Token TTL bypass | TTL checked on every request, not just creation |

---

## Test Plan

New file: `tests/test_sprint15.py` (target: 28 tests)

```
TestPayrollExport
  test_payroll_xlsx_returns_200
  test_payroll_xlsx_content_type
  test_payroll_xlsx_has_correct_columns
  test_payroll_xlsx_trilingual_ru
  test_payroll_unauthenticated_redirects

TestBudgetExport
  test_budget_xlsx_returns_200
  test_budget_xlsx_utilization_pct_computed
  test_budget_allocated_zero_renders_na
  test_budget_empty_period_returns_empty_sheet

TestOrgPdfExport
  test_org_pdf_returns_200
  test_org_pdf_content_type
  test_org_pdf_empty_db_returns_placeholder_page

TestTokenAuth
  test_create_token_returns_token
  test_token_accepted_on_api_endpoint
  test_expired_token_rejected
  test_invalid_token_rejected
  test_revoke_token
  test_wrong_password_401
  test_ttl_hours_param
  test_401_body_includes_hint

TestUserScripts
  test_save_script
  test_list_user_scripts
  test_delete_script
  test_path_traversal_blocked
  test_invalid_name_rejected
  test_session_isolation

TestLoginRequiredDecorator
  test_decorator_accepts_session_cookie
  test_decorator_accepts_bearer_token
  test_decorator_rejects_neither

TestApiDiscovery
  test_api_v1_returns_endpoint_list
```

**Target:** 28 new tests → ~594 total

---

## Decision Audit Trail

| # | Decision | Rationale | Rejected |
|---|----------|-----------|---------|
| 1 | openpyxl + reportlab | Pure Python, Cyrillic, no native deps | xlsxwriter+weasyprint (needs GTK on Windows) |
| 2 | Full 3-deliverable scope | All reviewed in Sprint 13; unblocks real users today | Trim D3 |
| 3 | BytesIO, never disk | No cleanup logic needed; stateless per-request | Temp files |
| 4 | `os.replace()` atomic write for tokens.json | Prevents corruption on concurrent saves | File lock |
| 5 | Lazy TTL GC on load | No background thread; simple; correct | Cron purge |
| 6 | 401 hint field | Developer can act without reading docs | Bare 401 |
| 7 | Filename regex + Path.name assertion | Defense in depth for path traversal | One check only |

---

## GSTACK REVIEW REPORT

| Review | Status |
|--------|--------|
| CEO Review | ✅ carried from Sprint 13 plan |
| Eng Review | ✅ carried from Sprint 13 plan |
| DX Review | ✅ carried from Sprint 13 plan |
| Sprint 15 approval | pending user |
