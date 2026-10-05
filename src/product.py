"""Product focus of 1S, fixed in code (Sprint 18).

1S used to try to be three products at once: a free 1C replacement, a
SAP-level ERP and a 1C migration tool. From Sprint 18 the product is ONE
thing: a toolkit for moving business logic OUT of 1C/BAS (audit, port,
verify). Everything else is either the language core that the toolkit
needs, or a frozen showcase.

Tiers:
    core      Language and runtime the migration toolkit depends on.
              Bug fixes and features that serve migration.
    focus     The migration toolkit itself. New work goes here.
    showcase  ERP demo modules (procurement, payroll, LP ...). Kept working
              and tested, but FROZEN: no new public API. Their current
              public names are pinned in tests/frozen_api.json and
              tests/test_sprint18.py fails if one is added.

Changing a tier is a product decision: edit MODULE_TIERS, update the
snapshot (python -m src.product --snapshot) and say why in the commit.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

PRODUCT_FOCUS = "migration"

TAGLINE = {
    "en": "Move your business logic out of 1C/BAS: audit, port and verify on open-source Python.",
    "ru": "Выведите бизнес-логику из 1С/BAS: аудит, перенос и сверка на открытом Python.",
    "uk": "Виведіть бізнес-логіку з 1С/BAS: аудит, перенесення та звірка на відкритому Python.",
}

CORE, FOCUS, SHOWCASE = "core", "focus", "showcase"

# Every module under src/ must be listed. A new module without a tier fails
# tests/test_sprint18.py, so adding code forces the product decision.
MODULE_TIERS: dict[str, str] = {
    # language
    "src.lexer": CORE,
    "src.parser": CORE,
    "src.transpiler": CORE,
    "src.cli": CORE,
    "src.i18n": CORE,
    # runtime the toolkit needs (1C value types, registers, queries, storage)
    "src.runtime.types": CORE,
    "src.runtime.catalogs": CORE,
    "src.runtime.registers": CORE,
    "src.runtime.query": CORE,
    "src.runtime.db": CORE,
    "src.runtime.persistence": CORE,
    "src.runtime.reports": CORE,
    "src.runtime.excel": CORE,
    "src.runtime.export": CORE,
    # web shell (runs scripts, hosts reports and the demo)
    "src.server": CORE,
    "src.auth": CORE,
    "src.runtime.token_auth": CORE,
    "src.runtime.audit": CORE,
    # the product
    "src.migrate": FOCUS,
    "src.product": FOCUS,
    # frozen ERP showcase
    "src.runtime.procurement": SHOWCASE,
    "src.runtime.warehouse": SHOWCASE,
    "src.runtime.logistics": SHOWCASE,
    "src.runtime.maintenance": SHOWCASE,
    "src.runtime.payroll": SHOWCASE,
    "src.runtime.tax_engine": SHOWCASE,
    "src.runtime.budget": SHOWCASE,
    "src.runtime.org": SHOWCASE,
    "src.runtime.workflow": SHOWCASE,
    "src.runtime.workflow_config": SHOWCASE,
    "src.runtime.three_way_match": SHOWCASE,
    "src.runtime.industry_profile": SHOWCASE,
    "src.runtime.erp_query": SHOWCASE,
    "src.runtime.lp": SHOWCASE,
}

SRC_ROOT = Path(__file__).resolve().parent
FROZEN_API_FILE = SRC_ROOT.parent / "tests" / "frozen_api.json"


def tier_of(module: str) -> str | None:
    """Tier of a dotted module name; a submodule inherits its package's tier."""
    parts = module.split(".")
    for i in range(len(parts), 0, -1):
        tier = MODULE_TIERS.get(".".join(parts[:i]))
        if tier:
            return tier
    return None


def discover_modules() -> list[str]:
    """Top-level packages and modules under src/, plus every src/runtime module."""
    names: list[str] = []
    for p in sorted(SRC_ROOT.iterdir()):
        if p.name.startswith(("_", ".")):
            continue
        if p.is_dir() and (p / "__init__.py").exists():
            if p.name == "runtime":
                names += [f"src.runtime.{m.stem}" for m in sorted(p.glob("*.py"))
                          if not m.name.startswith("_")]
            else:
                names.append(f"src.{p.name}")
        elif p.suffix == ".py":
            names.append(f"src.{p.stem}")
    return names


def public_api(module: str) -> list[str]:
    """Public top-level names (functions, classes, assignments) of a module, read statically."""
    rel = Path(*module.split(".")[1:])
    path = SRC_ROOT / rel.with_suffix(".py")
    if not path.exists():
        path = SRC_ROOT / rel / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return sorted(n for n in names if not n.startswith("_"))


def showcase_api() -> dict[str, list[str]]:
    return {m: public_api(m) for m, t in sorted(MODULE_TIERS.items()) if t == SHOWCASE}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--snapshot"]:
        FROZEN_API_FILE.write_text(
            json.dumps(showcase_api(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Wrote {FROZEN_API_FILE}")
        return 0
    print(f"Focus: {PRODUCT_FOCUS}\n{TAGLINE['en']}\n")
    for tier in (FOCUS, CORE, SHOWCASE):
        mods = [m for m, t in sorted(MODULE_TIERS.items()) if t == tier]
        print(f"{tier:9} {', '.join(mods)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
