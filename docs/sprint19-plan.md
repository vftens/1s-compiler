# Sprint 19 — Variant A: a migration audit an integrator can sell

## Theme

Ukraine banned 1C and BAS (Cabinet Resolution No. 1335, from 22 Oct 2025). Companies
need to leave, integrators moving them to Odoo / Dilovod / MASTER need to understand
someone else's 1C code fast — and 1S already parses the 1C language with Ukrainian
keywords. This sprint turns `migrate audit` from a per-module summary into the
document an integrator brings to a client: **which procedures port as is, which
objects map to which Odoo models, and what is custom scope.**

Positioning note: the product is a tool for leaving 1C/BAS. It must never be sold as
"1C that keeps running"; the audit report says "migration", not "compatibility".

## Goals

### G1 — Audit per procedure
`split_procedures()` cuts each module into procedures/functions (RU/UK/EN keywords,
works even when the module does not parse) and classifies each one on its own:
portable, platform-bound (touches `Справочники.`, `Движения.`, queries …) or unparsed.
A VAT formula inside a document module is now reported as portable.

On `examples/`: by module 74% of lines are portable, **by procedure 94%** (90 of 91).

### G2 — Metadata from the configuration dump
`src/migrate/metadata.py` reads the object XMLs that Designer writes with
"Выгрузить конфигурацию в файлы": name, synonym, attributes with types
(`string`, `number`, `date`, `ref:Catalog.X`, composite), tabular sections, register
dimensions and resources, and the references between objects (migration order).
Namespace-agnostic; a broken XML is reported, never fatal.

### G3 — 1C → Odoo map
`src/migrate/odoo_map.py`: ~40 rules by object kind and RU/UK/EN name stems onto Odoo
17/18 Community models (res.partner, product.template, sale.order + account.move,
account.payment, stock.quant, res.currency.rate, account.account …), each with a note
on what to check. Unmatched objects are listed as **custom** — that list is the real
scope of a migration quote. Payroll is flagged: not in Odoo Community core.

The audit report (Markdown/JSON, RU/UK/EN) gains two sections: portable procedures and
"Objects and Odoo candidates".

### G4 — Query engine and the four query demos
- `ПЕРВЫЕ N` / `ПЕРШІ N` / `TOP N` → SQLite `LIMIT N` (it was emitted as `TOP`).
- Ukrainian letters `І Ї Є Ґ` are part of words (`ВІД` used to become `INІД`).
- Short sort words `УБЫВ`/`ВОЗР`/`СПАД`/`ЗРОСТ`.
- 1C `+` with a string literal: `"Итого: " + 5` → `"Итого: 5"` (Python raised
  TypeError). Emitted as `_cat()` only when a string literal is involved; numeric `+`
  is untouched.
- English aliases `ValueTable`, `ValueList`.
- Demo fixes: `EndWhile` → `EndDo` (1C syntax), `|` continuation in a multi-line query.

All four `demo_query_erp_*` scripts now run end to end.

### G5 — `packaging/windows.spec`
One PyInstaller spec instead of four near-identical files in the root
(`1S-ERP.spec`, `-RU`, `-UK`, `-EN`). Edition via `ONES_EDITION=base|ru|uk|en`;
paths built from `SPECPATH`, so it runs from any directory. `installer/build.py` and
`install.bat` use it. Tests execute the spec with stub PyInstaller objects and check
entry script, exe name, icon and data folders for every edition.

## Results

- 47 new tests; full suite on Linux: 750 passed, 4 failed (environment only: reportlab
  ×3, SQLite-on-Linux ×1), 2 skipped.

## Next (Sprint 20)

1. Run the audit on 3 real BAS/1C configurations (БАС Бухгалтерія, УТП, a custom one);
   tune Odoo rules and parser gaps on real code.
2. Trial balance (ОСВ) reconciliation: 1C export vs Odoo after import, per account and period.
3. Odoo import files: CSV/XML for res.partner, product.template, opening balances from the dump.
4. Audit report as a one-page PDF/HTML for the client (with the integrator's logo).
