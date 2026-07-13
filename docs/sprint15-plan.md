<!-- /autoplan restore point: /c/Users/DrVITAL/.gstack/projects/vftens-1s-compiler/sprint-12-query-engine-erp-dashboard-autoplan-restore-20260710-164040.md -->
# Sprint 15 Plan — Financial Reporting Module

**Branch:** `sprint-15-financial-reports`
**Target date:** 2026-07-14

---

## Context

Sprints 9–14 built a full ERP stack: double-entry accounting, payroll, procurement,
budget control, LP optimization, and REST export. The accounting data is all there
in `erp.db` — but there are no standard financial reports. Accountants who need a
Balance Sheet or P&L today have to export raw data and build it in Excel manually.

This sprint adds the three core financial statements that every ERP must produce,
plus REST endpoints and dashboard integration so reports are one click away.

---

## What already exists (leverage map)

| Sub-problem | Existing code |
|-------------|---------------|
| Double-entry ledger data | `src/runtime/persistence.py` — `budget_allocations`, `budget_entries`; `PlanOfAccounts` (Sprint 9) |
| Payroll figures | `payroll_results` table, `PayrollEngine` |
| Procurement spend | `purchase_orders`, `receiving_orders` tables |
| Excel export | `src/runtime/export.py` — `PayrollExporter`, `BudgetExporter` (Sprint 13 openpyxl) |
| PDF export | `src/runtime/export.py` — `OrgPdfExporter` (Sprint 13 reportlab) |
| REST auth | Bearer token + `@login_required` (Sprint 13) |
| Dashboard pattern | `/erp-dashboard` Canvas chart + collapsible sections (Sprint 12) |
| ERP query layer | `erp_query.py` — `ERPQuery` with `budget_utilization`, `payroll_history`, `summary_report` |

**Key constraint:** All three reports must work against live `erp.db` data with zero
additional schema changes. The data is already there.

---

## Deliverable 1 — Report Engine (`src/runtime/reports.py`)

Three report classes, each following the same pattern:
- `compute(period: str, db_path: str) → dict` — pure computation, no I/O
- `to_excel(period, db_path) → BytesIO` — returns in-memory xlsx
- `to_pdf(period, db_path) → BytesIO` — returns in-memory pdf
- Full trilingual RU/UK/EN column headers and section labels

### 1A — Trial Balance (Оборотно-сальдова відомість / ОСВ)

Columns: account_code, account_name, opening_debit, opening_credit, period_debit,
period_credit, closing_debit, closing_credit.

Sourced from `budget_entries` grouped by account. Validates: total debit == total
credit for each period (double-entry integrity check — fails with `TrialBalanceError`
if violated).

### 1B — Balance Sheet (Баланс / Balance Sheet)

Standard two-column layout: Assets (left) vs Liabilities + Equity (right).

```
ASSETS                          LIABILITIES + EQUITY
─────────────────────────────   ─────────────────────────────
Current Assets:                 Current Liabilities:
  Cash & equivalents  X           Accounts payable    X
  Accounts receivable X           Accrued payroll     X
  Inventory           X         Long-term Liabilities:
Fixed Assets:                     (reserved)          0
  Property/Equipment  X         Equity:
  Less: Depreciation (X)          Retained earnings   X
                      ─────                           ─────
Total Assets          X         Total L + E           X
```

Sourced by mapping `budget_allocations.account` to asset/liability/equity buckets
via a configurable account plan mapping (`profiles/chart_of_accounts.yaml` or
hardcoded default). Must balance: `Total Assets == Total L+E`. If they don't,
appends a `difference` line (not an error — signals incomplete data, not code bug).

### 1C — Income Statement / P&L (Звіт про фінансові результати)

```
Revenue                         X
Cost of Goods Sold             (X)
─────────────────────────────────
Gross Profit                    X
  Operating expenses           (X)
  Payroll expenses             (X)
─────────────────────────────────
Operating Profit (EBIT)         X
  Other income/expense          X
─────────────────────────────────
Net Profit / (Loss)             X
```

Sourced from `budget_entries` (revenue/expense accounts) + `payroll_results`
(payroll line). Period filter: calendar month or YTD via `period_mode=monthly|ytd`.

---

## Deliverable 2 — REST Endpoints (`src/server.py`)

All `@login_required`. All support `?period=YYYY-MM&format=json|xlsx|pdf&lang=ru|uk|en`.

```
GET /api/v1/reports/trial-balance    → JSON or xlsx or pdf
GET /api/v1/reports/balance-sheet    → JSON or xlsx or pdf
GET /api/v1/reports/income-statement → JSON or xlsx or pdf
GET /api/v1/reports                  → JSON index of available reports + last-run timestamp
```

Response for `format=json`:
```json
{
  "report": "trial-balance",
  "period": "2026-07",
  "generated_at": "2026-07-11T10:00:00Z",
  "rows": [...],
  "totals": {...},
  "integrity": {"balanced": true, "difference": 0}
}
```

For xlsx/pdf: `Content-Disposition: attachment; filename="trial_balance_2026-07.xlsx"`

---

## Deliverable 3 — Reports Dashboard page (`/reports`)

Extend the ERP dashboard pattern:

- Period selector (YYYY-MM, same as `/erp-dashboard`)
- Three tabs: Trial Balance / Balance Sheet / Income Statement
- Each tab: summary KPI row + full table + "Export Excel" + "Export PDF" buttons
- Empty state: "No accounting data for this period" (not blank or error)
- Same dark/light theme, no external CDN

---

## Deliverable 4 — 1S script bindings

```
// English
Reporter = NewReporter()
TB = Reporter.TrialBalance("2026-07")
Message("Balanced: " + String(TB.IsBalanced))
Message("Total debit: " + String(TB.TotalDebit))

BS = Reporter.BalanceSheet("2026-07")
Message("Total assets: " + String(BS.TotalAssets))
Message("Equity: " + String(BS.Equity))

PL = Reporter.IncomeStatement("2026-07")
Message("Net profit: " + String(PL.NetProfit))
```

Trilingual: `НовыйОтчетчик` / `НовийЗвітник` / `NewReporter`,
`ОборотноСальдоваяВедомость` / `ОборотноСальдоваВідомість` / `TrialBalance`,
`Баланс` / `Баланс` / `BalanceSheet`,
`ОтчетОПрибылях` / `ЗвітПроПрибутки` / `IncomeStatement`.

---

## Architecture

```
src/
  server.py              ← 4 new routes + /reports page
  runtime/
    reports.py           ← NEW: TrialBalanceReport, BalanceSheetReport, IncomeStatement
src/templates/
  reports.html           ← NEW: 3-tab dashboard
  _report_table.html     ← NEW: reusable partial (server-side render for PDF)
profiles/
  chart_of_accounts.yaml ← NEW: account → asset/liability/equity mapping (default)
examples/
  demo_reports_ru.1s     ← trial balance + balance sheet RU
  demo_reports_uk.1s     ← income statement + YTD comparison UK
  demo_reports_en.1s     ← full cycle: compute + export EN
```

---

## Security

| Concern | Mitigation |
|---------|-----------|
| Data leakage | All endpoints `@login_required`; each report is read-only against `erp.db` |
| Period injection | `period` validated: `r'^\d{4}-\d{2}$'` before any SQL |
| Path traversal | `db_path` validated via existing `AttachDB` path-jail logic |
| Large output DoS | Max 10,000 rows per report; truncated with `X-Truncated: true` header |

---

## Test Plan

New file: `tests/test_sprint15.py` (target: 32 tests)

```
TestTrialBalance
  test_trial_balance_returns_rows
  test_trial_balance_debit_credit_balanced
  test_trial_balance_empty_period_returns_empty
  test_trial_balance_xlsx_export
  test_trial_balance_pdf_export

TestBalanceSheet
  test_balance_sheet_assets_equals_liabilities_plus_equity
  test_balance_sheet_period_filter
  test_balance_sheet_difference_line_on_imbalance
  test_balance_sheet_xlsx_export

TestIncomeStatement
  test_income_statement_net_profit_computed
  test_income_statement_ytd_mode
  test_income_statement_empty_period

TestReportEndpoints
  test_trial_balance_json_endpoint
  test_trial_balance_xlsx_endpoint
  test_trial_balance_pdf_endpoint
  test_balance_sheet_json_endpoint
  test_income_statement_json_endpoint
  test_reports_index_endpoint
  test_reports_unauthenticated_redirects
  test_period_injection_blocked
  test_format_param_invalid_returns_400

TestReportsDashboard
  test_reports_page_returns_200
  test_reports_page_unauthenticated

TestNewReporterBinding
  test_trial_balance_binding_is_balanced
  test_balance_sheet_binding_total_assets
  test_income_statement_binding_net_profit
  test_trilingual_ru_aliases
  test_trilingual_uk_aliases

TestReportEdgeCases
  test_max_rows_truncation_header
  test_missing_db_returns_503
  test_empty_db_no_500
  test_pdf_reportlab_import_error_returns_503
```

**Target:** 32 new tests → 647 total

---

## Decision Audit Trail

### Original (planning)
| # | Decision | Rationale | Rejected |
|---|----------|-----------|---------|
| 1 | Build on existing `export.py` openpyxl/reportlab | Infrastructure already in place, no new deps | New report library |
| 2 | `profiles/chart_of_accounts.yaml` for account mapping | Configurable without code change; matches industry norm | Hardcoded mapping only |
| 3 | `format=json\|xlsx\|pdf` single endpoint per report | One URL, negotiated format; cleaner DX | Separate `/json`, `/xlsx`, `/pdf` endpoints |
| 4 | Period mode `monthly\|ytd` on income statement | YTD comparison is standard accounting practice | Monthly only |
| 5 | Max 10,000 rows + truncation header | DoS guard; in practice trial balance rarely exceeds 500 rows | No limit |
| 6 | `TrialBalanceError` on debit≠credit | Data integrity signal, not silent failure | Return unbalanced silently |
| 7 | `/reports` tab dashboard (not separate pages) | One URL to share; consistent with `/erp-dashboard` pattern | Separate pages per report |

### CEO Review — auto-decisions
| # | Decision | Rationale | Rejected |
|---|----------|-----------|---------|
| C1 | `chart_of_accounts.yaml` mapping is required deliverable, not optional | Balance Sheet correctness depends on it; validation required | Leave as optional |
| C2 | Add `period_snapshots` table spec + `opening_balance_note` in JSON | `budget_entries` has no carry-forward mechanism; make explicit | Silently return zeros |
| C3 | Defer Cash Flow Statement to Sprint 16 | Indirect method needs AP/AR aging data not yet modeled | Implement in Sprint 15 |
| C4 | Defer full МСФО/П(С)БО compliance certification | Requires external auditor input, not a code problem | Certify in Sprint 15 |

### Design Review — auto-decisions
| # | Decision | Rationale | Rejected |
|---|----------|-----------|---------|
| D1 | Tab layout stays on single `/reports` page | One URL to bookmark/share; consistent with dashboard pattern | Separate pages per report |
| D2 | Empty state: "No accounting data for YYYY-MM" per tab | Prevents blank/error confusion when period has no entries | Generic "no data" |
| D3 | Export buttons always visible, disabled when no data | Discoverable; not hidden until data loads | Hidden until data |
| D4 | Period selector shared across all three tabs | Single period context; avoids 3-pickers confusion for beginners | Per-tab selector (taste decision pending) |
| D5 | Dark/light theme via CSS custom properties | Matches existing dashboard; no external CDN | New theme library |

### Eng Review — auto-decisions
| # | Decision | Rationale | Rejected |
|---|----------|-----------|---------|
| E1 | Extract `src/runtime/db.py` shared `_connect()` helper | DRY: `export.py` and `reports.py` both need DB access | Duplicate `_connect` |
| E2 | `reports.py` delegates to `ERPQuery` for data access | P4: reuse existing query layer; no raw SQL in reports.py | Raw SQL in reports |
| E3 | `compute(period, db_path) → dict`; `to_excel(data)` / `to_pdf(data)` accept pre-computed dict | Prevents double-query; REST endpoint calls compute() once | Pass db_path to format methods |
| E4 | `CAST(amount AS REAL)` + null guard; log warning for non-numeric rows | TEXT column silently returns NULL on non-numeric; must handle explicitly | Raise exception |
| E5 | Period validation: `r'^\d{4}-(0[1-9]\|1[0-2])$'` (month 01-12 only) | Prevents month 13/00 from reaching SQL | `r'^\d{4}-\d{2}$'` |
| E6 | `pyyaml` in `requirements.txt`; fallback to hardcoded default if missing/malformed | P1: must work even if yaml unavailable | Crash on missing yaml |
| E7 | `LIMIT 10001` in SQL; detect 10001st row → set `X-Truncated: true` header | DoS guard at DB level, not Python truncation | Python-level slice |
| E8 | `db_path` is hardcoded application path for report endpoints (no user input) | No path traversal risk on read-only report routes | Validate path-jail |
| E9 | 7 additional tests added (yaml fallback, text amount, ytd mixed formats, month OOB, lang fallback, double-query regression, excel pre-computed dict) | Cover new failure modes discovered in eng review | Skip edge cases |

### DX Review — auto-decisions
| # | Decision | Rationale | Rejected |
|---|----------|-----------|---------|
| X1 | JSON always uses canonical English snake_case keys; `?lang` only affects xlsx/pdf headers | Prevents silent consumer breakage when team language preference differs | lang changes JSON keys |
| X2 | Add 4 report endpoints to `_API_ENDPOINTS` dict in `server.py` | Discovery gap: `GET /api/v1` would return zero report endpoints | Leave discovery stale |
| X3 | `integrity` block only on Trial Balance; Balance Sheet gets `balance_check: {difference: N}` (nullable) | `integrity.balanced` is meaningless on BS/IS which can legitimately not balance mid-period | Same structure everywhere |
| X4 | All 400/422/503 error responses include `{"error": "...", "hint": "..."}` | Actionable errors reduce TTHW; consistent with token endpoint pattern | Error string only |
| X5 | Document format-negotiation divergence in discovery description; don't backport to Sprint 13 | YAGNI: touching old export endpoints in Sprint 15 risks regression | Align old endpoints |
| X6 | `Reporter.IncomeStatement("2026-07", "ytd")` — second optional param defaulting to `"monthly"` | YTD mode must be accessible from 1S scripts; was missing entirely | REST-only YTD |

---

## GSTACK REVIEW REPORT

| Review | Status | Findings | Auto-decided | Taste decisions |
|--------|--------|----------|--------------|-----------------|
| CEO Review | complete | 5 | 4 | 1 |
| Design Review | complete | 6 | 5 | 1 |
| Eng Review | complete | 9 | 9 | 0 |
| DX Review | complete | 6 | 6 | 0 |

### Taste decisions (Phase 4 gate — user-confirmed)
| # | Question | Decision | Notes |
|---|----------|----------|-------|
| T1 | Cut 1S script bindings from Sprint 15? | **Keep** — ship `NewReporter()` + trilingual aliases as scoped | User chose feature completeness |
| T2 | Per-tab or global period selector? | **Single global selector** — one `?period=` param, all tabs in sync | Standard accounting UX |

**Test plan updated:** 32 → 39 tests (7 new edge cases from Eng review)

---

## Deferred Items (post-Sprint 15)

- Cash Flow Statement (indirect method) — Sprint 16; needs AP/AR aging data
- AR/AP aging reports — Sprint 16
- CSV/Excel data import / onboarding wizard — Sprint 16+
- Full МСФО/П(С)БО compliance certification — external auditor input required
- Format negotiation on legacy Sprint 13 export endpoints — YAGNI for now
