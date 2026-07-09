# Sprint 10 Plan — SAP/Oracle-comparable ERP for SMB (≤500 employees)

<!-- /autoplan restore point: /c/Users/DrVITAL/.gstack/projects/vftens-1s-compiler/-autoplan-restore-20260709-203448.md -->

## Goal

Make 1S: ERP Free Edition not require frequent customization for industry-specific 
business logic, and reach functional parity with SAP Business One / Oracle NetSuite 
for companies up to 500 employees.

Core insight: SAP/Oracle are powerful because their business rules live in 
**configuration, not code**. Sprint 10 builds that configurability layer.

## Current State (after Sprint 9)

- ✅ 5 ERP modules: Procurement, Warehouse, Logistics, Payroll, Maintenance
- ✅ WorkflowDocument base class (Draft→Pending→Approved→Posted)
- ✅ Trilingual RU/UK/EN throughout
- ❌ Workflow rules are hardcoded (2-level only)
- ❌ No organizational hierarchy
- ❌ Modules isolated (no 3-way matching)
- ❌ Tax rates hardcoded (not configurable)
- ❌ No budget/commitment control
- ❌ Payroll is manual arithmetic, not an engine

## Deliverables

### 1. OrgUnit — Organizational Hierarchy
`src/runtime/org.py`

Hierarchy: Holding → LegalEntity → Plant → Department → CostCenter → ProfitCenter

Every document/transaction anchored to an org node. Enables:
- Multi-company bookkeeping
- Per-plant inventory
- Cost center reporting
- Budget allocation by node

### 2. WorkflowConfig — Configurable Approval Routing
`src/runtime/workflow_config.py` + `profiles/workflow/default.yaml`

Rules engine: match by (doc_type, amount, category, org_node) → approval chain.
Load from YAML at runtime. No code change needed to add approval level.

Example rule:
```yaml
purchase_order:
  - condition: {amount_lt: 50000}
    approvers: [dept_head]
  - condition: {amount_lt: 500000}
    approvers: [dept_head, cfo]
  - condition: {amount_gte: 500000}
    approvers: [dept_head, cfo, ceo]
  - condition: {category: capex}
    approvers: [+cto]  # append
```

### 3. ThreeWayMatch — PO + GR + Invoice Reconciliation
`src/runtime/three_way_match.py`

Compares: PurchaseOrder ↔ ReceivingOrder ↔ SupplierInvoice
- Quantity tolerance (e.g., ±3%)
- Price tolerance (e.g., ±2%)
- Auto-blocks invoice payment on mismatch
- Partial match handling
- Dispute workflow

### 4. TaxEngine — Pluggable Tax Tables
`src/runtime/tax_engine.py` + `profiles/tax/*.yaml`

Tax profiles loaded from YAML, not hardcoded:
- `ru_2024.yaml`: НДФЛ 13%/15%, ПФР 22%, ОМС 5.1%, ФСС 2.9%
- `ua_2024.yaml`: ПДФО 18%, ЄСВ 22%, ВЗ 1.5%
- `us_2024.yaml`: Federal brackets 10-37%, FICA 7.65%, State varies
- `eu_2024.yaml`: VAT 20%, country-specific income tax

TaxEngine.calculate(gross, profile, period) → TaxResult(net, deductions breakdown)

### 5. IndustryProfile — YAML Configuration
`profiles/industry/*.yaml`

One profile = complete ERP configuration for an industry:

```yaml
# profiles/industry/manufacturing.yaml
name: Manufacturing
workflow: profiles/workflow/manufacturing.yaml
tax: profiles/tax/ru_2024.yaml
warehouse:
  lot_tracking: true
  fifo: true
  expiry_control: false
maintenance:
  preventive_schedule: meter_based
  spare_parts_integration: true
payroll:
  overtime_multiplier: 1.5
  shift_allowance: true
```

Profiles: manufacturing, trade, construction, logistics, services, healthcare

### 6. PayrollEngine — Proper Payroll Periods
`src/runtime/payroll.py`

- Pay periods: monthly, bi-weekly, weekly
- Absence tracking: vacation, sick, unpaid
- Overtime calculation with multipliers
- Bonus/commission schemes
- Payslip generation (PDF-ready text)
- Tax calculation via TaxEngine
- Bank transfer file stub

### 7. BudgetControl — Commitment Accounting
`src/runtime/budget.py`

- Budget allocation by OrgUnit + period + account
- Commitment: PO creation reserves budget
- Consumption: GR posting consumes commitment
- Hard stop / soft warning on overrun (configurable per profile)
- Budget utilization reports

### 8. Full trilingual support (RU/UK/EN)
All new classes get Russian + Ukrainian + English method aliases.

### 9. Demo scripts (one per industry profile)
- `examples/demo_manufacturing_ru.1s` — Станкостроительный завод
- `examples/demo_trade_uk.1s` — Торгова мережа
- `examples/demo_construction_en.1s` — Construction company
- Each demonstrates: org hierarchy → budget → procurement → 3-way match → payroll

### 10. Documentation
- `docs/sprint10-erp-architecture.md` — architecture overview
- `docs/industry-profiles.md` — how to create/customize profiles
- Update `docs/erp-modules.md` with new modules

## Technical Architecture

```
profiles/
├── industry/
│   ├── manufacturing.yaml
│   ├── trade.yaml
│   ├── construction.yaml
│   ├── logistics.yaml
│   └── services.yaml
├── workflow/
│   ├── default.yaml
│   └── manufacturing.yaml
└── tax/
    ├── ru_2024.yaml
    ├── ua_2024.yaml
    └── us_2024.yaml

src/runtime/
├── org.py              # NEW: OrgUnit hierarchy
├── workflow_config.py  # NEW: configurable routing
├── three_way_match.py  # NEW: PO+GR+Invoice match
├── tax_engine.py       # NEW: pluggable tax tables
├── payroll.py          # NEW: PayrollEngine
├── budget.py           # NEW: BudgetControl
└── __init__.py         # updated exports
```

## Success Criteria

1. A manufacturing company config (YAML) runs full cycle without code changes
2. Adding a 3rd approval level requires only YAML edit, no Python
3. Tax rate changes (annual) require only YAML edit, no Python
4. 3-way match catches price/quantity discrepancies automatically
5. Budget overrun is blocked (hard) or warned (soft) at PO creation time
6. PayrollEngine produces correct net pay for RU/UK/US scenarios
7. All demo scripts run cleanly end-to-end
8. All new classes have RU/UK/EN aliases

## Out of Scope (Sprint 10)

- GUI / Web forms for configuration
- Database persistence of org structure (in-memory this sprint)
- EDI / external API integration  
- Mobile UI
- Multi-currency exchange rate feeds (static rates only)

## Estimated Effort

| Deliverable | Complexity | Est. Lines |
|-------------|-----------|-----------|
| OrgUnit | Medium | ~200 |
| WorkflowConfig | High | ~300 |
| ThreeWayMatch | Medium | ~250 |
| TaxEngine + profiles | Medium | ~200 + 4×50 YAML |
| IndustryProfile loader | Low | ~100 |
| PayrollEngine | High | ~400 |
| BudgetControl | High | ~350 |
| Demo scripts ×3 | Medium | ~300 each |
| Docs | Low | ~400 |
| **Total** | | **~3000 lines** |

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|---------|
| 1 | CEO | Full plan (7 modules) | Auto | P1 Completeness | User confirmed all premises valid | 3-module MVP, DB-first |
| 2 | CEO | Add SupplierInvoice to three_way_match.py | Auto | P1 Completeness | Missing class for 3-way match | Separate file |
| 3 | CEO | Add pyyaml to requirements | Auto | P6 User confirmed | YAML loading requires it; already installed | — |
| 4 | Eng | SupplierInvoice in three_way_match.py not procurement.py | Auto | Avoid circular imports | procurement.py already imports from workflow.py | procurement.py |
| 5 | Eng | YAML condition evaluator: field-name matching only, no eval() | Auto | Security | eval() is a code injection risk even for file-based YAML | eval-based conditions |
| 6 | Eng | Import order: org→tax→budget→workflow_config→three_way_match→payroll | Auto | Architecture | Follows dependency graph, prevents circular imports | Flat import |
| 7 | Eng | IndustryProfile as module-level loader function, not class factory | Auto | KISS | Simple dict-based config is sufficient; class adds no value | Heavy class hierarchy |
