# Sprint 11 Plan — Persistence + Reporting

<!-- /autoplan restore point -->

## Goal

Eliminate in-memory-only limitation: Sprint 10 ERP objects (OrgChart, BudgetControl,
PayrollEngine, WorkflowConfig) must survive server restarts. Add cross-document ERP
reporting queries so accountants can answer "where did the money go" without writing SQL.
Add REST API endpoints for the new modules.

## Current State (after Sprint 10)

- ✅ 7 Sprint 10 modules: OrgUnit, TaxEngine, BudgetControl, WorkflowConfig, PayrollEngine, ThreeWayMatch, IndustryProfile
- ✅ SQLite persistence for accounting/accumulation registers (`persistence.py`)
- ❌ Sprint 10 objects are in-memory only — restart loses org chart, budget state, payroll history
- ❌ No cross-document reporting (PO spend by supplier, budget vs actual, payroll history)
- ❌ No REST API for Sprint 10 modules

## Deliverables

### 1. Extend `persistence.py` — Sprint 10 module persistence

**OrgChart** — `org_nodes` table: id, name, type, parent_id, org_name
**BudgetControl** — `budget_allocations` + `budget_entries` tables
**PayrollEngine** — `payroll_results` + `payroll_lines` tables
**WorkflowConfig** — `workflow_rules` table (JSON blob per doc_type)

New functions:
```
save_org_chart(org, db_path)      / load_org_chart(db_path, name)
save_budget(budget, db_path)      / load_budget(db_path)
save_payroll_results(results, db) / load_payroll_results(db, period)
save_workflow_config(cfg, db)     / load_workflow_config(db)
```

### 2. New `erp_query.py` — Cross-document reporting

```python
class ERPQuery:
    def po_spend_by_supplier(self, db_path, period=None) → list[dict]
    def budget_utilization(self, db_path, org_id=None, period=None) → list[dict]
    def payroll_history(self, db_path, emp_id=None, period=None) → list[dict]
    def summary_report(self, db_path, period) → dict
```

All methods have RU/UK/EN aliases.

### 3. REST API endpoints (in `server.py`)

```
GET  /api/v1/org                      — org chart nodes as JSON
GET  /api/v1/budget/utilization       — budget utilization by org/period
POST /api/v1/payroll/calculate        — run payroll + optionally persist
GET  /api/v1/payroll/history          — payroll history query
GET  /api/v1/erp/summary              — cross-module summary report
```

### 4. Demo scripts (trilingual)

- `examples/demo_persistence_ru.1s` — save/load org+budget+payroll (Russian)
- `examples/demo_persistence_uk.1s` — Ukrainian
- `examples/demo_erp_query_en.1s`   — ERP query layer (English)

### 5. Tests

`tests/test_sprint11.py` — persistence round-trip + query layer tests

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|---------|
| 1 | CEO | Full scope: persistence + reporting + REST API | Auto | User confirmed | User explicitly requested all 3 pillars | Persistence-only MVP |
| 2 | CEO | Add to persistence.py (not separate erp_persistence.py) | Auto | KISS | User said "extend persistence.py" — honour literal request | Separate file |
| 3 | Eng | erp_query.py as new module | Auto | SRP | Query logic is complex (SQL aggregations), warrants separation | Inline in persistence.py |
| 4 | Eng | WorkflowConfig saved as JSON blob per doc_type | Auto | Simplicity | Rules are small lists; JSON avoids 4 normalized tables per condition type | Normalized condition tables |
| 5 | Eng | PayrollResult serialized via Employee.id + period key | Auto | Correctness | Employee objects aren't DB rows; id+period is the natural key | Employee FK table |
| 6 | Eng | REST API in existing server.py under /api/v1/ | Auto | DRY | server.py already has /api/v1/* pattern; no new routing setup needed | Separate blueprint |
| 7 | DX | Full trilingual RU/UK/EN aliases on all new public functions | Auto | Requirement | Explicit Sprint 11 requirement | English-only |

## Success Criteria

1. `save_org_chart` + `load_org_chart` round-trips an OrgChart losslessly
2. `save_budget` + `load_budget` recovers all allocations and entries
3. `save_payroll_results` + `load_payroll_results` recovers net pay per employee
4. `ERPQuery.budget_utilization` returns correct utilization% for seeded data
5. All 3 REST endpoints return valid JSON with 200
6. All 3 demo scripts run end-to-end without error
7. All new public names have RU/UK/EN aliases
8. `tests/test_sprint11.py` passes
