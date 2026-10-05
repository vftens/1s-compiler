# Sprint 18 — Focus: one product, fixed in code

## Theme

1S tried to be three products at once: a free 1C replacement, a SAP-level ERP and a 1C
migration tool. One developer cannot win on three fronts, and since 22 Oct 2025 a product
sold as "1C-compatible" is a liability in Ukraine (Cabinet Resolution No. 1335 bans 1C and
BAS; the state treats a renamed 1C as 1C). From this sprint the product is **one thing: a
toolkit for moving business logic out of 1C/BAS — audit, port, verify.**

The decision lives in code, not only in this document, so it cannot quietly erode.

## Goals

### G1 — Product manifest `src/product.py`
`PRODUCT_FOCUS = "migration"`, a trilingual `TAGLINE`, and `MODULE_TIERS` classifying
every module under `src/`:

| Tier | Meaning | Modules |
|---|---|---|
| focus | The product. New work goes here. | `src.migrate`, `src.product` |
| core | Language and runtime the toolkit needs | lexer, parser, transpiler, cli, i18n, types, catalogs, registers, query, db, persistence, reports, excel, export, server, auth |
| showcase | ERP demo modules. Kept working, **frozen** | procurement, warehouse, logistics, maintenance, payroll, tax_engine, budget, org, workflow(+config), three_way_match, industry_profile, erp_query, lp |

`python -m src.cli about` prints the focus and tiers.

### G2 — Guardrails (tests/test_sprint18.py)
- A module without a tier fails the build: adding code forces the product decision.
- Showcase public API is pinned in `tests/frozen_api.json` (14 modules, 172 names);
  a new public name in a showcase module fails with a message pointing to `src/migrate`.
  Bug fixes inside existing functions are allowed (see G4).
- The README must carry `TAGLINE["en"]`, so positioning and code cannot drift apart.

Changing a tier = edit `MODULE_TIERS`, run `python -m src.product --snapshot`, explain in
the commit message.

### G3 — `migrate audit` MVP (`src/migrate/audit.py`)
`python -m src.cli migrate audit <dump-dir> [--lang ru|uk|en] [--json] [-o report.md]`

Input: a configuration dumped to files (Designer → "Выгрузить конфигурацию в файлы"), or any
folder of `.bsl` / `.1s`. Per module:
- **portable** — parses with the 1S parser, no 1C object model: port as is;
- **platform-bound** — parses, but uses `Справочники.`, `Движения.`, `Новый Запрос` …:
  logic must be mapped onto the target system;
- **unparsed** — a gap in the 1S core to close.

Also: metadata object counts, compilation directives (`&НаСервере`, blanked before parsing),
exported functions, cp1251 input, Markdown/JSON report in RU/UK/EN. Nothing is executed.

### G4 — LP solver runs on Linux servers
The bundled `glpk/glpsol.exe` is a Windows binary but was picked on every OS, so all LP
features failed on Linux (17 tests). Now: `GLPSOL_PATH` → bundled `.exe` on Windows →
`glpsol` on PATH (`apt install glpk-utils`). Needed for the demo VPS.

### G5 — The parser never spins forever
Found by running the audit on `examples/`: a statement starting with a short keyword
(Ukrainian `з` = IN, Russian `и` = AND) made `_parse_statement` return without consuming
the token, so the caller looped forever. `demo_query_erp_ru.1s` and `_uk.1s` hung even under
`cli run`. Now: such a word before `=`, `.`, `(`, `[` or in operand position is read as a
variable (`з = Запрос(...)`, `рез = з.Выполнить()`); any other stray token is a `ParseError`.
The audit also parses each module with a 10 s guard, so a future parser bug costs one
module, not the whole audit.

## Results

- 22 new tests; full suite on Linux: 703 passed, 4 failed (was 664 passed / 21 failed).
  Remaining 4 are environment-only: `reportlab` not installed (3 PDF tests) and one
  SQLite-on-Linux corrupt-DB case — unchanged by this sprint.
- `migrate audit examples/`: 67 modules in 0.6 s; 74% of lines portable, 24% platform-bound,
  1% unparsed. The unparsed ones are real gaps in our own demos (below).

## Next (Sprint 19 candidates, all in focus)

1. Audit per procedure, not per module (a portable function inside a platform-bound module).
2. Read `Configuration.xml` / object XML: attributes, tabular sections, register dimensions.
3. Mapping report for one target (Odoo first): which 1C objects map to which models.
4. Data reconciliation: trial balance (ОСВ) before/after migration must match.
5. Real-world corpus: run the audit on 3 real configurations, fix the top parser gaps.
6. Query engine: `ПЕРВЫЕ N` is emitted as `TOP N` at the end of the SQL (SQLite needs
   `LIMIT N`), and the Ukrainian `ІЗ` is mangled (`INІД`); `demo_query_erp_ru/uk.1s` fail at run time.
7. Own demos the audit cannot read: `demo_query_erp_en.1s` (Expected ENDDO at 44:1),
   `demo_query_erp_join_en.1s` (unterminated string at 31:11).

## Non-goals

- New ERP features in showcase modules.
- Claims that a whole 1C configuration "runs as is".
