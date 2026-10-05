"""Sprint 18 — product focus fixed in code: module tiers, frozen showcase API, migration audit."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src import product
from src.migrate import audit, render_json, render_markdown
from src.migrate.audit import PLATFORM_BOUND, PORTABLE, UNPARSED

ROOT = Path(__file__).resolve().parent.parent


# ── G1: every module has a tier ──────────────────────────────────────────────

def test_every_module_has_a_tier():
    missing = [m for m in product.discover_modules() if product.tier_of(m) is None]
    assert not missing, (
        f"Modules without a product tier: {missing}. Decide in src/product.py MODULE_TIERS: "
        "core (the toolkit needs it), focus (migration), or showcase (frozen ERP demo)."
    )


def test_tiers_point_at_real_modules():
    discovered = set(product.discover_modules())
    stale = [m for m in product.MODULE_TIERS if m not in discovered]
    assert not stale, f"MODULE_TIERS lists modules that no longer exist: {stale}"


def test_focus_is_migration():
    assert product.PRODUCT_FOCUS == "migration"
    assert product.tier_of("src.migrate") == product.FOCUS
    assert product.tier_of("src.migrate.audit") == product.FOCUS  # submodules inherit


# ── G2: showcase modules are frozen ──────────────────────────────────────────

def test_showcase_public_api_is_frozen():
    frozen = json.loads(product.FROZEN_API_FILE.read_text(encoding="utf-8"))
    current = product.showcase_api()
    grown = {m: sorted(set(names) - set(frozen.get(m, []))) for m, names in current.items()}
    grown = {m: n for m, n in grown.items() if n}
    assert not grown, (
        f"New public API in frozen showcase modules: {grown}. Since Sprint 18 the ERP showcase "
        "gets fixes only. Put new work in src/migrate (focus) or src core; if this is a deliberate "
        "product decision, change the tier in src/product.py and run `python -m src.product --snapshot`."
    )


def test_tagline_is_trilingual_and_on_the_readme():
    assert set(product.TAGLINE) == {"en", "ru", "uk"}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert product.TAGLINE["en"] in readme


# ── G3: migration audit ──────────────────────────────────────────────────────

PORTABLE_BSL = """
Функция СуммаСНДС(Сумма, Ставка = 20) Экспорт
    Возврат Сумма + Сумма * Ставка / 100;
КонецФункции
"""

POSTING_BSL = """
#Если Сервер Тогда
Процедура ОбработкаПроведения(Отказ, Режим)
    Движения.ОстаткиТоваров.Записывать = Истина;
    Запрос = Новый Запрос;
    Запрос.Текст = "ВЫБРАТЬ 1";
КонецПроцедуры
#КонецЕсли
"""

DIRECTIVE_BSL = """
&НаСервере
Функция Курс(Валюта) Экспорт
    Возврат Справочники.Валюты.НайтиПоКоду(Валюта).Курс;
КонецФункции
"""

BROKEN_BSL = "Процедура Сломано(\n"


@pytest.fixture
def dump(tmp_path: Path) -> Path:
    files = {
        "CommonModules/Налоги/Ext/Module.bsl": PORTABLE_BSL,
        "Documents/Реализация/Ext/ObjectModule.bsl": POSTING_BSL,
        "CommonModules/Валюты/Ext/Module.bsl": DIRECTIVE_BSL,
        "Catalogs/Номенклатура/Ext/ManagerModule.bsl": BROKEN_BSL,
        "Catalogs/Валюты.xml": "<MetaDataObject/>",
    }
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


def _by_name(report, name):
    return next(m for m in report.modules if m.object_name == name)


def test_audit_classifies_modules(dump):
    r = audit(dump)
    assert _by_name(r, "Налоги").status == PORTABLE
    assert _by_name(r, "Реализация").status == PLATFORM_BOUND
    assert _by_name(r, "Номенклатура").status == UNPARSED
    assert r.objects["catalog"] == 2 and r.objects["document"] == 1


def test_audit_strips_directives_and_counts_them(dump):
    m = _by_name(audit(dump), "Валюты")
    assert m.status == PLATFORM_BOUND  # parsed despite &НаСервере
    assert m.directives == 1
    assert m.platform_refs == {"catalogs": 1}


def test_audit_finds_posting_queries_and_exports(dump):
    r = audit(dump)
    assert _by_name(r, "Реализация").platform_refs == {"posting": 1, "queries": 2}
    assert _by_name(r, "Налоги").exports == ["СуммаСНДС"]
    assert _by_name(r, "Реализация").module_kind == "object"


def test_audit_reads_cp1251(tmp_path):
    (tmp_path / "old.bsl").write_bytes(PORTABLE_BSL.encode("cp1251"))
    assert audit(tmp_path).modules[0].status == PORTABLE


@pytest.mark.parametrize("lang,word", [("ru", "Переносятся"), ("uk", "Переносяться"), ("en", "Portable")])
def test_markdown_report_languages(dump, lang, word):
    md = render_markdown(audit(dump), lang)
    assert word in md and "СуммаСНДС" in md


def test_json_report_totals(dump):
    data = json.loads(render_json(audit(dump)))
    assert data["totals"][PORTABLE]["modules"] == 1
    assert data["totals"][PLATFORM_BOUND]["modules"] == 2
    assert data["totals"][UNPARSED]["modules"] == 1


def test_audit_rejects_missing_folder(tmp_path):
    with pytest.raises(NotADirectoryError):
        audit(tmp_path / "nope")


def test_cli_migrate_audit_writes_report(dump, tmp_path):
    out = tmp_path / "report.md"
    res = subprocess.run(
        [sys.executable, "-m", "src.cli", "migrate", "audit", str(dump), "--lang", "en", "-o", str(out)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert res.returncode == 0, res.stderr
    assert "Portable as is" in out.read_text(encoding="utf-8")


def test_cli_about_shows_focus():
    res = subprocess.run(
        [sys.executable, "-m", "src.cli", "about"], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", timeout=60,
    )
    assert res.returncode == 0 and "Focus: migration" in res.stdout


# ── G4: LP solver finds glpsol on Linux servers ──────────────────────────────

def test_glpsol_found_on_path(monkeypatch, tmp_path):
    from src.runtime import lp
    fake = tmp_path / "glpsol"
    fake.write_text("")
    monkeypatch.delenv("GLPSOL_PATH", raising=False)
    monkeypatch.setattr(lp, "_GLPK_DEFAULT", tmp_path / "glpsol.exe")
    (tmp_path / "glpsol.exe").write_text("")  # bundled Windows binary present
    monkeypatch.setattr(lp.os, "name", "posix")
    monkeypatch.setattr(lp.shutil, "which", lambda name: str(fake) if name == "glpsol" else None)
    assert lp._glpsol_path() == fake


# ── G5: parser never spins forever ───────────────────────────────────────────

def _parse_in_subprocess(code: str) -> subprocess.CompletedProcess:
    script = (
        "import sys\nfrom src.lexer import Lexer\nfrom src.parser import Parser\n"
        "src = sys.stdin.read()\n"
        "try:\n    Parser(Lexer(src, 'x').tokenize()).parse(); print('parsed')\n"
        "except Exception as e:\n    print('error', type(e).__name__)\n"
    )
    return subprocess.run([sys.executable, "-c", script], input=code, cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", timeout=20)


@pytest.mark.parametrize("code", [
    "з = 1;",                                   # Ukrainian keyword "з" as a Russian variable
    "з = Запрос(\"ВЫБРАТЬ 1\");\nрез = з.Выполнить();",
])
def test_short_keyword_as_variable_parses(code):
    assert _parse_in_subprocess(code).stdout.strip() == "parsed"


@pytest.mark.parametrize("code", ["КонецЕсли;", "Тогда 1;"])
def test_stray_keyword_is_an_error_not_a_hang(code):
    assert _parse_in_subprocess(code).stdout.strip() == "error ParseError"


def test_audit_survives_a_hanging_parser(monkeypatch, tmp_path):
    import time
    import importlib
    A = importlib.import_module("src.migrate.audit")

    class Stuck:
        def __init__(self, *a):
            pass

        def parse(self):
            time.sleep(5)

    monkeypatch.setattr(A, "Parser", Stuck)
    monkeypatch.setattr(A, "PARSE_TIMEOUT_S", 0.2)
    (tmp_path / "m.bsl").write_text(PORTABLE_BSL, encoding="utf-8")
    m = audit(tmp_path).modules[0]
    assert m.status == UNPARSED and m.error.startswith("Timeout")
