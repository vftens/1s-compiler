# 1S: ERP Free Edition

> Open-source 1C-compatible ERP scripting engine — bilingual (Ukrainian 🇺🇦 + Russian), runs on Python, no vendor lock-in.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-384%20passed-brightgreen.svg)](tests/)

**1S** (Latin S, not Cyrillic С) — we are **not affiliated with 1C Company** in any way.

---

## What is this?

1S is a compiler + runtime that lets you write, run, and migrate **1C-style business scripts**
without buying a 1C license. Your existing `.1s` / `.bsl` scripts work as-is.

```
Функція РозрахуватиПДВ(Сума)   // Ukrainian
    Повернути Сума * 0.20;
КінецьФункції;

Повідомити(РозрахуватиПДВ(10000));   // → 2000
```

**Runs as Python → or compiles to Cython for 10–50× speed on numeric workloads.**

---

## For whom

| Who | Problem | How 1S solves it |
|-----|---------|-----------------|
| Ukrainian companies (post-2022) | Must migrate off Russian 1C | Drop-in compatibility, Ukrainian keywords |
| Small/medium business | 1C license $300–3000/seat/year | **Free** — GPL v3 |
| 1C developers | Vendor lock-in, closed ecosystem | Open source, Python ecosystem |
| Accounting firms | Per-seat pricing on scripts | Self-hosted, unlimited users |
| Startups | Can't afford 1C | Full ERP runtime in `pip install` |

---

## Features

- **Trilingual lexer** — Russian + Ukrainian + English keywords (~200 entries)
- **Full 1C-compatible AST** — variables, functions, procedures, loops, exceptions
- **Double-entry accounting** — `ПланРахунків`, `РегістрБухгалтерії`, `ОСВ`, `АналізРахунку`
- **Accumulation & Information registers** — inventory, payroll, HR
- **SAP-comparable ERP modules** (Sprint 9) — Procurement (MM), Warehouse (WM/EWM), Logistics (TM/SD), Payroll (HCM), Maintenance (PM/EAM) — all via Workflow engine
- **Workflow engine** — `Draft → Pending → Approved → Posted` state machine on every document
- **YAML-configurable ERP layer** (Sprint 10) — OrgUnit hierarchy, N-level WorkflowConfig, TaxEngine (ru/ua/us/eu), ThreeWayMatch, PayrollEngine, BudgetControl, IndustryProfiles — add approval levels or change tax rates in YAML, no code changes
- **SQLite ERP persistence** (Sprint 11) — OrgChart, BudgetControl, PayrollEngine, WorkflowConfig all save/load to SQLite; survives server restarts; `save_org_chart`, `save_budget`, `save_payroll_results`, `save_workflow_config` + trilingual aliases
- **ERP query layer** (Sprint 11) — `ERPQuery` for cross-document reporting: `budget_utilization`, `po_spend_by_supplier`, `payroll_history`, `summary_report` — all with RU/UK/EN text output
- **REST API v1 (Sprint 11)** — `GET /api/v1/org`, `GET /api/v1/budget/utilization`, `POST /api/v1/payroll/calculate`, `GET /api/v1/payroll/history`, `GET /api/v1/erp/summary`
- **Script query engine** (Sprint 12) — `Query("SELECT …").AttachDB("erp.db").Execute()` in `.1s` scripts; joins in-memory `ValueTable` with SQLite ERP tables in a single query; trilingual aliases: `Запрос`/`Запит`/`Query`, `ПрисоединитьБД`/`ПриєднатиБД`/`AttachDB`, `Выполнить`/`Виконати`/`Execute`
- **Live ERP dashboard** (Sprint 12) — `/erp-dashboard` — budget utilization chart (Canvas 2D), payroll summary, PO spend, collapsible org tree; period filter; no external CDN; trilingual RU/UK/EN
- **REST API v1 extended** (Sprint 12) — `GET /api/v1/erp/chart-data?period=YYYY-MM` — budget + PO spend for dashboard
- **Cython transpiler** — typed `.pyx` output, `cdef long` / `cpdef` for 10–50× speedup
- **Web UI** — Flask shell with live SSE script runner, ERP dashboard, user management, admin panel
- **406 tests** — lexer, parser, runtime, transpiler, ERP persistence, query engine, dashboard routes

---

## Quick start

```bash
git clone https://github.com/vftens/1s-compiler
cd 1s-compiler
pip install flask

# Run a demo script
python -m src.cli run examples/accounting_uk.1s

# Launch Web UI
python -m src.cli serve
# → open http://127.0.0.1:5000  (login: admin / admin)
```

---

## Examples included

| Script | What it demonstrates |
|--------|---------------------|
| `hello_uk.1s` | Ukrainian keywords, arrays, maps, exceptions |
| `accounting_uk.1s` | Double-entry bookkeeping, УКСГП chart of accounts, ОСВ |
| `erp_sale_uk.1s` | Sales orders, inventory, VAT, financial result |
| `hrm_payroll.1s` | Payroll, NDFL, insurance, vacation |
| `hrm_zup.1s` | HR infobase, work schedules, staffing |
| `demo_erp_full_ru.1s` | Full ERP cycle in Russian: Procurement→Warehouse→Logistics→Payroll→Maintenance |
| `demo_erp_full_uk.1s` | Full ERP cycle in Ukrainian (ПДФО 18%, ЄСВ 22%) |
| `demo_erp_full_en.1s` | Full ERP cycle in English (Federal tax 22%, FICA 7.65%) |
| `demo_manufacturing_ru.1s` | Sprint 10: Manufacturing — OrgChart, Budget, 3-Way Match, Payroll (ru_2024) |
| `demo_trade_uk.1s` | Sprint 10: Retail trade — YAML routing, ПДФО+ЄСВ+ВЗ payroll (ua_2024) |
| `demo_construction_en.1s` | Sprint 10: Construction — Budget commitment, FICA payroll (us_2024) |
| `demo_persistence_ru.1s` | Sprint 11: OrgChart+Budget+Payroll → SQLite → reload + ERP queries (Russian) |
| `demo_persistence_uk.1s` | Sprint 11: Агрохолдинг → SQLite → reload + Ukrainian ERP queries |
| `demo_erp_query_en.1s` | Sprint 11: ERPQuery layer — budget utilization, PO spend, payroll history, summary |
| `demo_query_erp_en.1s` | Sprint 12: Query ERP tables from .1s scripts (English) — SELECT org_nodes, budget, payroll |
| `demo_query_erp_ru.1s` | Sprint 12: Запросы к таблицам ERP из .1s скриптов (Russian) |
| `demo_query_erp_uk.1s` | Sprint 12: Запити до таблиць ERP зі скриптів .1s (Ukrainian) |
| `demo_query_erp_join_en.1s` | Sprint 12: JOIN in-memory ValueTable with org_nodes from erp.db in one query |

---

## Paid services

> The code is free. Your **time and peace of mind** are not.

See **[SERVICES.md](SERVICES.md)** for full offer.  
Contact: **aico@ya.ru** | Telegram: [@vftens](https://t.me/vftens)

| Service | Price |
|---------|-------|
| Hosted Web UI (SaaS) | from $29/month |
| 1C → 1S migration audit | from $199 |
| Custom script development | from $49/hour |
| Priority support | from $99/month |
| Enterprise self-hosted setup | from $499 one-time |

---

## Architecture

```
.1s source
    │
    ▼
Lexer (trilingual, ~200 keywords)
    │
    ▼
Parser (recursive descent → typed AST)
    │
    ├──▶ Python backend  → .py  (runs immediately)
    └──▶ Cython backend  → .pyx (compile for 10–50× speed)
              │
              ▼
         src/runtime/  (types, registers, query engine)
```

---

## Running tests

```bash
pip install pytest
python -m pytest tests/ -q
# 384 passed
```

---

## License

GNU GPL v3 — free to use, modify, distribute.  
Commercial use: contact us for a commercial license exception.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md)
