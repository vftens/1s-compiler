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

## 🌍 v1.0 — Open ecosystem (2027)

- [ ] **Module registry** — community-published accounting rules, payroll formulas
- [ ] **1C infobase reader** — import data from real 1C `.dt` / `.cf` files
- [ ] **Multi-tenant SaaS** — isolated workspaces per company
- [ ] **Java/ANTLR runtime** — JVM-based alternative (grammar already written)
- [ ] **Mobile UI** — React Native or PWA for reports on phone

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) if it exists, or open an issue.  
Key areas that need help: query engine, VS Code extension, Excel I/O.
