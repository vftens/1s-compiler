# Sprint 13 Completion Summary

**Branch:** `sprint-12-query-engine-erp-dashboard`
**Commit:** `7dc6875`
**Date:** 2026-07-10
**Tests:** 36 new / 602 total passing

---

## Deliverables Shipped

### 1 — Excel Export (`src/runtime/export.py`)

- `GET /api/v1/export/payroll?period=YYYY-MM` → `payslips.xlsx`
- `GET /api/v1/export/budget?period=YYYY-MM` → `budget.xlsx`
- Trilingual column headers: EN / RU / UK via `?lang=` param
- In-memory BytesIO — nothing written to disk
- `Content-Disposition: attachment; filename="payroll_{period}.xlsx"` + correct MIME type
- Division-by-zero guard: `utilization_%` is `None` (blank cell) when `allocated = 0`
- `FileNotFoundError` on missing `erp.db` → 503 with human-readable message

### 2 — PDF Export (`src/runtime/export.py`)

- `GET /api/v1/export/org` → `org_chart.pdf`
- Depth-first org tree rendered by reportlab (max depth 6)
- Empty DB → single placeholder page "No organizational data" (not 500)
- reportlab is a lazy import inside `OrgPdfExporter.__init__`; `ImportError` → 503 "install reportlab"

### 3 — Bearer Token Auth (`src/runtime/token_auth.py` + `src/server.py`)

- `POST /api/v1/token` — creates token; rate-limited to 5 req/min/IP
- `DELETE /api/v1/token` — revokes token via `Authorization: Bearer <token>`
- Tokens stored in `erp.db:tokens` table (sha256 hashes only, never raw values)
- Server-side TTL: 24 h default, 168 h max — not user-configurable
- Identical 401 hint body for wrong password vs nonexistent user (closes user enumeration)
- `login_required` and `admin_required` both check Bearer before session cookie; set `g.current_user`
- `/admin` route migrated from `session["user"]` to `g.current_user` to support Bearer

### 4 — User Script Persistence (`src/server.py`)

- `POST /api/v1/scripts/save` — save new script; 409 on name collision
- `PUT /api/v1/scripts/save/<name>` — overwrite existing script
- `GET /api/v1/scripts/user` — list user's saved scripts
- `DELETE /api/v1/scripts/<name>` — delete one script
- Files stored under `data/user_scripts/<username>/<name>.1s`
- `re.fullmatch(r'^[a-zA-Z0-9_-]+\.1s$')` validated **before** any `Path()` construction
- 50-script per-user quota

### 5 — API Discovery + Quality (`src/server.py`)

- `GET /api/v1` — lists all v1 endpoints with `auth_required`, `query_params`, `content_type`, `example_response`, and a Python Bearer auth code example
- Global `@app.errorhandler` for 400 / 401 / 403 / 404 / 405 / 500 → always JSON, never HTML

---

## Files Changed

| File | Status | Notes |
|------|--------|-------|
| `src/runtime/export.py` | NEW | PayrollExporter, BudgetExporter, OrgPdfExporter |
| `src/runtime/token_auth.py` | NEW | TokenStore, no Flask imports, threading.Lock |
| `src/server.py` | MODIFIED | Bearer auth, 8 new routes, global error handlers |
| `tests/test_sprint13.py` | NEW | 36 tests across 9 classes |
| `docs/sprint13-plan.md` | NEW | 28-decision audit trail, 4-phase GSTACK review |

---

## autoplan Review Results

All 4 phases clean before implementation:

| Phase | Status | Key Changes Applied |
|-------|--------|---------------------|
| CEO | ✅ | Tokens → SQLite (not JSON); rate limiting; server-side TTL; user enumeration closed |
| Design | ✅ | Save modal, 3 UI states, 409 conflict UX, toolbar order |
| Eng | ✅ | re.fullmatch before Path(); lazy reportlab; admin Bearer; 4 extra tests |
| DX | ✅ | Discovery endpoint metadata; expires_at ISO 8601 Z; Content-Disposition; global error handlers |

---

## Test Breakdown

```
TestPayrollExport          6 tests
TestBudgetExport           5 tests
TestOrgPdfExport           3 tests
TestTokenAuth              9 tests
TestUserScripts            7 tests
TestLoginRequiredDecorator 3 tests
TestAdminRequiredWithBearer 1 test
TestApiDiscovery           1 test
TestDependencyGraceDegradation 1 test
─────────────────────────────
Total                     36 tests
```
