# Roadmap

## ✅ Done (v0.3 — current)

- Trilingual lexer + recursive-descent parser
- Python + Cython transpiler backends
- Full 1C-compatible runtime: Array, Map, Structure, ValueTable, ValueList
- Double-entry accounting register (ПланРахунків, ОСВ, АналізРахунку)
- Accumulation + Information registers
- Work schedules (weekly / shift)
- Flask Web UI with SSE live output, user auth, admin panel
- 384 automated tests (lexer → parser → runtime → transpiler → integration)
- Ukrainian 🇺🇦 keyword set (full parity with Russian)
- Cython type inference + `cdef`/`cpdef` generation
- GPL v3 license
- GitHub: github.com/vftens/1s-compiler

---

## ✅ v0.4 — Sprint 7 complete (June 2026)

- [x] **SaaS deployment** — Docker + Nginx (`nginx/`), `deploy.sh` one-liner
- [x] **`pip install 1s-erp`** — `pyproject.toml` with extras: `[desktop,cython]`
- [x] **Landing page** — `landing/index.html` for www.1s-compiler.ru
- [ ] **Stripe/LiqPay payment** — online billing for SaaS tiers ← next
- [ ] **Demo video** — 5-min screencast
- [ ] **Migration CLI** — `python -m src.cli migrate myfile.bsl`

## ✅ v0.5 — Sprint 7 complete (June 2026)

- [x] **SQLite-backed registers** — `src/runtime/persistence.py`
- [ ] **Query engine** — full `ВЫБРАТЬ / ОБЕРІТЬ` SQL dialect ← next
- [x] **REST API** — `/api/v1/ping, /run, /eval, /scripts, /analytics-data`
- [x] **VS Code extension** — `vscode-1s/` grammar + snippets + Run button
- [x] **Excel export** — `src/runtime/excel.py` + openpyxl, CSV fallback

---

## ✅ v0.6 — Sprint 8 complete (July 2026)

- [x] **Cython type inference engine** — `_collect_numeric_vars()` recursive scanner, `cdef long` / `cpdef` for all numeric vars
- [x] **Sprint 8 demo scripts** — Cython performance benchmarks RU/UK/EN

---

## ✅ v0.7 — Sprint 9 complete (July 2026)

- [x] **Workflow engine** — `WorkflowDocument` base class, `Draft → Pending → Approved → Posted` state machine, full audit history
- [x] **Procurement module (SAP MM)** — `PurchaseOrder`, `ReceivingOrder`, `Supplier`, `ProcurementAnalytics`; goods receipt with partial fulfillment tracking
- [x] **Warehouse module (SAP WM/EWM)** — `Warehouse`, `WarehouseCell`, `StockMovement`, `ABCAnalysis` (Pareto 80/15/5), `InventoryCheck`
- [x] **Logistics module (SAP TM/SD)** — `TransportOrder`, `DeliveryRoute`, `Carrier`, `LogisticsAnalytics`, SLA tracking
- [x] **Maintenance module (SAP PM/EAM)** — `EquipmentCard` (digital twin), `RepairOrder`, `MaintenancePlan`, `MaintenanceAnalytics` (MTTR, cost KPIs)
- [x] **Payroll (SAP HCM)** — built-in arithmetic: RU (НДФЛ 13%, ПФР 22%), UK (ПДФО 18%, ЄСВ 22%), EN (22% tax, FICA 7.65%)
- [x] **Full demo suite** — `demo_erp_full_ru/uk/en.1s` + BAT launchers
- [x] **Runtime bugfixes** — `Structure["key"]` access, `DateFromString`, `Structure` EN alias, `Document.number` lowercase key, `WorkflowDocument` lowercase method aliases
- [x] **Documentation** — `docs/erp-modules.md` full module reference

---

## ✅ v0.8 — Sprint 10 complete (July 2026)

- [x] **OrgUnit hierarchy** — `OrgChart` + `OrgNode`: Holding → LegalEntity → Plant → Department → CostCenter → ProfitCenter; full trilingual RU/UK/EN
- [x] **WorkflowConfig** — YAML-configurable N-level approval routing; no code change needed to add an approval level; `profiles/workflow/*.yaml`
- [x] **ThreeWayMatch** — automatic PO ↔ GR ↔ SupplierInvoice reconciliation with configurable tolerance (qty/price %) and blocking
- [x] **TaxEngine** — pluggable tax profiles: `ru_2024` (НДФЛ+ПФР+ОМС+ФСС), `ua_2024` (ПДФО+ЄСВ+ВЗ), `us_2024` (Federal+FICA), `eu_2024`; YAML-extensible
- [x] **IndustryProfile** — YAML configuration profiles: manufacturing, trade, construction, logistics, services
- [x] **PayrollEngine** — payroll periods, absence tracking (vacation/sick/unpaid), bonus schemes, payslip generation, TaxEngine integration
- [x] **BudgetControl** — commitment accounting: allocate → commit (PO submit) → consume (GR post) → release (PO rejection); hard/soft overrun control
- [x] **Demo suite** — `demo_manufacturing_ru.1s`, `demo_trade_uk.1s`, `demo_construction_en.1s` — each runs full cycle end-to-end
- [x] **Full trilingual RU/UK/EN** — all 7 new modules with complete alias coverage

---

## ✅ v0.9 — Sprint 11 complete (July 2026)

- [x] **SQLite persistence for Sprint 10 modules** — `save_org_chart`/`load_org_chart`, `save_budget`/`load_budget`, `save_payroll_results`/`load_payroll_results`, `save_workflow_config`/`load_workflow_config`; all with RU/UK/EN aliases
- [x] **ERP query layer** (`erp_query.py`) — `ERPQuery`: `budget_utilization`, `po_spend_by_supplier`, `payroll_history`, `summary_report`; formatted text output in RU/UK/EN
- [x] **REST API Sprint 11** — `GET /api/v1/org`, `GET /api/v1/budget/utilization`, `POST /api/v1/payroll/calculate`, `GET /api/v1/payroll/history`, `GET /api/v1/erp/summary`
- [x] **Demo suite** — `demo_persistence_ru.1s`, `demo_persistence_uk.1s`, `demo_erp_query_en.1s` — all pass end-to-end
- [x] **26 new tests** — persistence round-trips, query layer, trilingual aliases; 514 passing total

---

## ✅ v1.0 — Sprint 12 complete (July 2026)

- [x] **Script query engine** — `Query("SELECT …").AttachDB("erp.db").Execute()` lets `.1s` scripts query Sprint 11 SQLite tables (`org_nodes`, `budget_allocations`, `budget_entries`, `payroll_results`, `workflow_rules`); in-memory `ValueTable` joins with SQLite tables in a single query
- [x] **Path security** — `AttachDB` validates path stays inside `ROOT/data/`; `1S_ALLOW_ANY_DB_PATH=1` env override for CLI/CI
- [x] **Full trilingual aliases** — `Запрос`/`Запит`/`Query`, `ПрисоединитьБД`/`ПриєднатиБД`/`AttachDB`, `Выполнить`/`Виконати`/`Execute`, `Выбрать`/`Вибрати`/`Select`, `Следующий`/`Наступний`/`Next`, `Значение`/`Значення`/`Value`
- [x] **Live ERP dashboard** (`/erp-dashboard`) — Canvas 2D budget chart, payroll table, PO spend table, collapsible org tree; YYYY-MM period filter applies to all sections; no external CDN; XSS-safe via `escHtml()`
- [x] **REST endpoint** — `GET /api/v1/erp/chart-data?period=YYYY-MM` — budget utilization + PO spend JSON for dashboard
- [x] **Demo suite** — `demo_query_erp_en.1s`, `demo_query_erp_ru.1s`, `demo_query_erp_uk.1s`, `demo_query_erp_join_en.1s`
- [x] **22 new tests** — AttachDB, path security, concurrent reads, trilingual aliases, dashboard routes, bonus regression

---

## ✅ v1.1 — Sprint 14 complete (July 2026)

- [x] **Linear Programming solver** — `LPSolver` backed by GLPK 5.0 (`glpsol.exe`); minimize/maximize, inequality/equality constraints, variable bounds, shadow prices; no scipy dependency
- [x] **ERP LP helpers** — `BudgetAllocator` (optimal budget reallocation across org units), `ResourceAllocator` (transportation LP for staff assignment); both read directly from `erp.db`
- [x] **REST LP endpoint** — `POST /api/v1/lp/solve` — full JSON problem definition → solution + shadow prices; 422 for infeasible/unbounded; DoS guard (500 vars, 1000 constraints); Bearer token support
- [x] **LP Solver dashboard** — `/lp-solver` — browser LP problem builder: dynamic variable count, inequality/equality constraints, per-variable bounds, live solve, shadow prices table; no external CDN
- [x] **Demo suite** — `demo_lp_solver_en.1s` (diet problem), `demo_lp_budget_ru.1s` (budget optimization), `demo_lp_resources_uk.1s` (resource assignment)
- [x] **Full trilingual RU/UK/EN** — `НовыйСолвер`/`НовийСолвер`/`NewSolver`, all constraint/bound/result aliases
- [x] **30 new tests** — solver math, ERP helpers, REST endpoint, dashboard, aliases; 566 passing total

---

## 🌍 v1.2 — Open ecosystem (2027)

- [ ] **Module registry** — community-published accounting rules, payroll formulas
- [ ] **1C infobase reader** — import data from real 1C `.dt` / `.cf` files
- [ ] **Multi-tenant SaaS** — isolated workspaces per company
- [ ] **Java/ANTLR runtime** — JVM-based alternative (grammar already written)
- [ ] **Mobile UI** — React Native or PWA for reports on phone

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) if it exists, or open an issue.  
Key areas that need help: query engine, VS Code extension, Excel I/O.
