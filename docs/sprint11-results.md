# Sprint 11 Results — Persistence + Reporting

**Commit:** `346687b`  
**Date:** 2026-07-09  
**Tests:** 26 new, 514 passing total (4 pre-existing catalog failures unrelated to Sprint 11)

---

## What shipped

### `src/runtime/persistence.py` — extended

8 new save/load functions for Sprint 10 ERP modules:

| Function | What it saves |
|----------|--------------|
| `save_org_chart(org, db)` / `load_org_chart(db, name)` | OrgNode tree; skips auto-root; two-pass reload for deep hierarchies |
| `save_budget(budget, db)` / `load_budget(db)` | `Dict[Tuple, Decimal]` allocations + `BudgetEntry` list with `doc_ref` |
| `save_payroll_results(results, db)` / `load_payroll_results(db, period)` | PayrollResult rows + TaxLine breakdown per employee |
| `save_workflow_config(cfg, db)` / `load_workflow_config(db)` | WFRule lists as JSON blobs per doc_type |

Full trilingual aliases:

| EN | RU | UK |
|----|----|----|
| `save_org_chart` | `СохранитьОргСтруктуру` | `ЗберегтиОргСтруктуру` |
| `load_org_chart` | `ЗагрузитьОргСтруктуру` | `ЗавантажитиОргСтруктуру` |
| `save_budget` | `СохранитьБюджет` | `ЗберегтиБюджет` |
| `load_budget` | `ЗагрузитьБюджет` | `ЗавантажитиБюджет` |
| `save_payroll_results` | `СохранитьРасчетыЗП` | `ЗберегтиРозрахункиЗП` |
| `load_payroll_results` | `ЗагрузитьРасчетыЗП` | `ЗавантажитиРозрахункиЗП` |
| `save_workflow_config` | `СохранитьМаршрут` | `ЗберегтиМаршрут` |
| `load_workflow_config` | `ЗагрузитьМаршрут` | `ЗавантажитиМаршрут` |

---

### `src/runtime/erp_query.py` — new module

`ERPQuery(db_path)` — cross-document SQL reporting without writing SQL:

| Method | Returns |
|--------|---------|
| `budget_utilization(org_id, period)` | allocated / committed / consumed / utilization% per (org, period, account) |
| `po_spend_by_supplier(period)` | committed vs consumed per doc_ref |
| `payroll_history(emp_id, period)` | gross / net / tax_profile per employee per period |
| `summary_report(period)` | cross-module totals: budget + payroll in one dict |
| `format_report(type, rows, lang)` | formatted text table in RU / UK / EN |

Class aliases: `ЗапросERPe` (RU), `ЗапитERPe` (UK)  
Method aliases: `ИсполнениеБюджета`, `ИсторияЗарплат`, `СводныйОтчет` (RU); `ВиконанняБюджету`, `ІсторіяЗарплат`, `ЗведенийЗвіт` (UK)

---

### `src/server.py` — 5 new REST endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/org` | GET | Org chart nodes from `data/erp.db` |
| `/api/v1/budget/utilization` | GET | Budget utilization (params: `org_id`, `period`) |
| `/api/v1/payroll/calculate` | POST | Run payroll + optionally persist (`save: true` in body) |
| `/api/v1/payroll/history` | GET | Payroll history (params: `emp_id`, `period`) |
| `/api/v1/erp/summary` | GET | Cross-module summary (param: `period`) |

All require login. DB path: `data/erp.db` relative to project root.

---

### Demo scripts (all pass end-to-end)

| Script | Language | Demonstrates |
|--------|----------|-------------|
| `examples/demo_persistence_ru.1s` | Russian | ЗАО Промышленный Холдинг → SQLite → reload; ERP queries in Russian |
| `examples/demo_persistence_uk.1s` | Ukrainian | ПАТ Агрохолдинг Україна → SQLite → reload; ERP queries in Ukrainian |
| `examples/demo_erp_query_en.1s` | English | ERPQuery full cycle: seed → persist → reload → budget_utilization + po_spend + payroll_history + summary |

---

### Tests — `tests/test_sprint11.py`

26 tests across 5 classes:

- `TestOrgChartPersistence` — round-trip, empty-db fallback, overwrite, multi-org isolation
- `TestBudgetPersistence` — round-trip, empty fallback, utilization% after reload
- `TestPayrollPersistence` — round-trip, period filter, wrong-period returns empty, lines saved
- `TestWorkflowConfigPersistence` — round-trip, `get_approvers` works after reload
- `TestERPQuery` — budget utilization (all + filtered), po_spend, payroll history (all + filtered), summary, missing DB returns empty, format_report in EN

---

## Architecture notes

- `OrgChart._nodes` includes auto-created `"root"` node — `save_org_chart` skips it; `load_org_chart` recreates via `OrgChart(org_name)` then two-pass add for deep trees
- `BudgetControl._allocations` is `Dict[Tuple[str,str,str], Decimal]` — not a list
- `BudgetEntry.doc_ref` (not `doc_number`); `entry_type` values are `"commitment"` / `"consumption"` / `"release"`
- `PayrollResult` has no `.lines` — tax deduction lines live in `res.tax_result.lines` (TaxLine objects)
- 1S transpiler does not support keyword arguments — use positional or `Undefined` for optional leading args
- `Неопределено` (Undefined) is falsy in Python → `if org_id:` works correctly when called from .1s scripts
