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
- **Cython transpiler** — typed `.pyx` output, `cdef long` / `cpdef` for 10–50× speedup
- **Web UI** — Flask shell with live SSE script runner, user management, admin panel
- **384 tests** — lexer, parser, runtime, transpiler, integration

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
