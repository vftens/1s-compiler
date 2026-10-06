"""Sprint 19 — variant A (Ukraine): procedures, metadata, Odoo map, query engine, packaging."""
from __future__ import annotations

import ast
import importlib
import json
import os
from pathlib import Path

import pytest

from src.migrate import audit, render_json, render_markdown
from src.migrate.audit import PLATFORM_BOUND, PORTABLE, UNPARSED, split_procedures
from src.migrate.metadata import read_metadata, read_object
from src.migrate.odoo_map import suggest
from src.runtime.query import _translate_query

ROOT = Path(__file__).resolve().parent.parent

NS = ('xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:v8="http://v8.1c.ru/8.1/data/core" '
      'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
      'xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config"')


def _attr(name: str, *types: str) -> str:
    t = "".join(f"<v8:Type>{x}</v8:Type>" for x in types)
    return f"<Attribute><Properties><Name>{name}</Name><Type>{t}</Type></Properties></Attribute>"


CATALOG_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS} version="2.16">
 <Catalog uuid="1">
  <Properties><Name>Контрагенты</Name>
   <Synonym><v8:item><v8:lang>ru</v8:lang><v8:content>Контрагенты</v8:content></v8:item></Synonym>
  </Properties>
  <ChildObjects>
   {_attr("КодПоЕДРПОУ", "xs:string")}
   {_attr("ОсновнойДоговор", "cfg:CatalogRef.ДоговорыКонтрагентов")}
  </ChildObjects>
 </Catalog>
</MetaDataObject>"""

DOCUMENT_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject {NS}>
 <Document uuid="2">
  <Properties><Name>РеализацияТоваровУслуг</Name></Properties>
  <ChildObjects>
   {_attr("Контрагент", "cfg:CatalogRef.Контрагенты")}
   {_attr("СуммаДокумента", "xs:decimal")}
   {_attr("Дата", "xs:dateTime")}
   <TabularSection><Properties><Name>Товары</Name></Properties><ChildObjects>
    {_attr("Номенклатура", "cfg:CatalogRef.Номенклатура")}
    {_attr("Количество", "xs:decimal")}
   </ChildObjects></TabularSection>
  </ChildObjects>
 </Document>
</MetaDataObject>"""

REGISTER_XML = f"""<MetaDataObject {NS}><AccumulationRegister>
  <Properties><Name>ТоварыНаСкладах</Name></Properties>
  <ChildObjects>
   <Dimension><Properties><Name>Склад</Name><Type><v8:Type>cfg:CatalogRef.Склады</v8:Type></Type></Properties></Dimension>
   <Resource><Properties><Name>Количество</Name><Type><v8:Type>xs:decimal</v8:Type></Type></Properties></Resource>
  </ChildObjects></AccumulationRegister></MetaDataObject>"""

MIXED_BSL = """
Функция СуммаСНДС(Сумма, Ставка = 20) Экспорт
    Возврат Сумма + Сумма * Ставка / 100;
КонецФункции

&НаСервере
Процедура ОбработкаПроведения(Отказ, Режим)
    Движения.ОстаткиТоваров.Записывать = Истина;
КонецПроцедуры
"""


@pytest.fixture
def dump(tmp_path: Path) -> Path:
    files = {
        "Catalogs/Контрагенты.xml": CATALOG_XML,
        "Documents/РеализацияТоваровУслуг.xml": DOCUMENT_XML,
        "AccumulationRegisters/ТоварыНаСкладах.xml": REGISTER_XML,
        "Catalogs/Сломанный.xml": "<MetaDataObject><Catalog>",
        "Catalogs/ВидыПродукцииСпецучета.xml": f"<MetaDataObject {NS}><Catalog><Properties><Name>ВидыПродукцииСпецучета</Name></Properties></Catalog></MetaDataObject>",
        "Documents/РеализацияТоваровУслуг/Ext/ObjectModule.bsl": MIXED_BSL,
        "CommonModules/Общий/Ext/Module.bsl": "Процедура Сломано(\n",
    }
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp_path


# ── G1: procedures ───────────────────────────────────────────────────────────

def test_portable_function_inside_platform_bound_module(dump):
    r = audit(dump)
    mod = next(m for m in r.modules if m.object_name == "РеализацияТоваровУслуг")
    assert mod.status == PLATFORM_BOUND
    procs = {p.name: p for p in mod.procedures}
    assert procs["СуммаСНДС"].status == PORTABLE and procs["СуммаСНДС"].exported
    assert procs["СуммаСНДС"].kind == "function" and procs["СуммаСНДС"].line == 2
    assert procs["ОбработкаПроведения"].status == PLATFORM_BOUND
    assert procs["ОбработкаПроведения"].platform_refs == {"posting": 1}
    assert not procs["ОбработкаПроведения"].exported


def test_procedures_of_unparsed_module_are_unparsed(dump):
    mod = next(m for m in audit(dump).modules if m.object_name == "Общий")
    assert [p.status for p in mod.procedures] == [UNPARSED]


@pytest.mark.parametrize("src,name,kind", [
    ("Функція Податок(С) Експорт\n Повернути С * 0.2;\nКінецьФункції", "Податок", "function"),
    ("Procedure Post() Export\nEndProcedure", "Post", "procedure"),
])
def test_split_procedures_ukrainian_and_english(src, name, kind):
    [p] = split_procedures(src, module_parsed=True)
    assert (p.name, p.kind, p.exported, p.status) == (name, kind, True, PORTABLE)


def test_report_has_procedure_section(dump):
    md = render_markdown(audit(dump), "uk")
    assert "Переносні процедури" in md and "РеализацияТоваровУслуг.СуммаСНДС" in md


# ── G2: metadata ─────────────────────────────────────────────────────────────

def test_reads_catalog_attributes_types_and_synonym(dump):
    o = read_object(dump / "Catalogs/Контрагенты.xml", "catalog")
    assert o.error is None and o.name == "Контрагенты" and o.synonym == "Контрагенты"
    assert [(f.name, f.type) for f in o.attributes] == [
        ("КодПоЕДРПОУ", "string"), ("ОсновнойДоговор", "ref:Catalog.ДоговорыКонтрагентов")]


def test_reads_document_tabular_sections_and_references(dump):
    o = read_object(dump / "Documents/РеализацияТоваровУслуг.xml", "document")
    assert {f.name: f.type for f in o.attributes} == {
        "Контрагент": "ref:Catalog.Контрагенты", "СуммаДокумента": "number", "Дата": "date"}
    assert [f.name for f in o.tabular_sections["Товары"]] == ["Номенклатура", "Количество"]
    assert o.references == ["Catalog.Контрагенты", "Catalog.Номенклатура"]


def test_reads_register_dimensions_and_resources(dump):
    o = read_object(dump / "AccumulationRegisters/ТоварыНаСкладах.xml", "accumulation_register")
    assert [f.name for f in o.dimensions] == ["Склад"] and [f.name for f in o.resources] == ["Количество"]


def test_broken_xml_is_reported_not_fatal(dump):
    broken = next(o for o in read_metadata(dump) if o.name == "Сломанный")
    assert broken.error and broken.error.startswith("ParseError")


# ── G3: Odoo map ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kind,name,model", [
    ("catalog", "Контрагенты", "res.partner"),
    ("catalog", "Контрагенти", "res.partner"),
    ("catalog", "Номенклатура", "product.template"),
    ("catalog", "БанковскиеСчета", "res.partner.bank"),
    ("catalog", "Организации", "res.company"),
    ("catalog", "Склады", "stock.warehouse"),
    ("catalog", "ДоговорыКонтрагентов", "custom"),
    ("document", "РеализацияТоваровУслуг", "sale.order + account.move"),
    ("document", "ВидатковаНакладна", "sale.order + account.move"),
    ("document", "ПоступлениеТоваровУслуг", "purchase.order + account.move"),
    ("document", "ПлатіжнеДоручення", "account.payment"),
    ("document", "НачислениеЗарплаты", "hr.payslip"),
    ("accumulation_register", "ТоварыНаСкладах", "stock.quant"),
    ("information_register", "КурсыВалют", "res.currency.rate"),
    ("accounting_register", "Хозрасчетный", "account.move.line"),
    ("chart_of_accounts", "Хозрасчетный", "account.account"),
    ("catalog", "ВидыПродукцииСпецучета", "custom"),
])
def test_odoo_suggestions(kind, name, model):
    assert suggest(kind, name).model == model


def test_code_objects_are_not_migrated():
    assert suggest("common_module", "ОбщегоНазначения").model == ""


def test_report_has_odoo_table(dump):
    data = json.loads(render_json(audit(dump)))
    by_name = {r["name"]: r for r in data["odoo_map"]}
    assert by_name["Контрагенты"]["odoo"] == "res.partner"
    assert by_name["РеализацияТоваровУслуг"]["tabular_sections"] == 1
    assert by_name["ВидыПродукцииСпецучета"]["odoo"] == "custom"
    md = render_markdown(audit(dump), "ru")
    assert "Объекты и кандидаты в Odoo" in md and "| catalog | Контрагенты |" in md


# ── G4: query engine ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [
    "ВЫБРАТЬ id ИЗ org_nodes ГДЕ id <> 'root' ПЕРВЫЕ 20",
    "ВЫБРАТЬ ПЕРВЫЕ 20 id ИЗ org_nodes ГДЕ id <> 'root'",
    "ВИБРАТИ id ВІД org_nodes ДЕ id <> 'root' ПЕРШІ 20",
    "SELECT TOP 20 id FROM org_nodes WHERE id <> 'root'",
])
def test_first_n_becomes_limit(raw):
    assert _translate_query(raw) == "SELECT id FROM org_nodes WHERE id <> 'root' LIMIT 20"


def test_ukrainian_letters_stay_inside_words():
    assert _translate_query("ВИБРАТИ Ціна ВІД ціни") == "SELECT Ціна FROM ціни"


@pytest.mark.parametrize("word,sql", [("УБЫВ", "DESC"), ("ВОЗР", "ASC"), ("СПАД", "DESC"), ("ЗРОСТ", "ASC")])
def test_order_short_forms(word, sql):
    assert _translate_query(f"ВЫБРАТЬ a ИЗ t УПОРЯДОЧИТЬ ПО a {word}").endswith(f"ORDER BY a {sql}")


def test_existing_limit_is_kept():
    assert _translate_query("SELECT a FROM t LIMIT 5") == "SELECT a FROM t LIMIT 5"


def test_string_plus_number_follows_1c():
    from src.lexer import Lexer
    from src.parser import Parser
    from src.transpiler import PythonTranspiler
    from src import runtime
    code = PythonTranspiler().transpile(Parser(Lexer('Р = "Итого: " + 5 + " шт";', "x").tokenize()).parse())
    ns = {k: getattr(runtime, k) for k in dir(runtime) if not k.startswith("__")}
    exec(code, ns)
    assert ns["Р"] == "Итого: 5 шт"


def test_numeric_plus_stays_plain_python():
    from src.lexer import Lexer
    from src.parser import Parser
    from src.transpiler import PythonTranspiler
    code = PythonTranspiler().transpile(Parser(Lexer("А = 1 + 2;", "x").tokenize()).parse())
    assert "_cat" not in code and "(1 + 2)" in code


def test_value_table_has_english_alias():
    from src import runtime
    assert runtime.ValueTable is runtime.ТаблицаЗначений
    assert runtime.ValueList is runtime.СписокЗначений


# ── G5: packaging ────────────────────────────────────────────────────────────

SPEC = ROOT / "packaging" / "windows.spec"


def _run_spec(edition: str) -> dict:
    """Execute the spec with stub PyInstaller objects and return what EXE got."""
    captured: dict = {}

    class _Stub:
        def __init__(self, *args, **kw):
            self.args, self.kw = args, kw
            self.pure = self.scripts = self.binaries = self.datas = []

    def EXE(*args, **kw):  # noqa: N802 - PyInstaller name
        captured.update(kw)
        captured["_scripts"] = analysis.args[0]
        captured["_datas"] = analysis.kw["datas"]

    def Analysis(*args, **kw):  # noqa: N802
        nonlocal analysis
        analysis = _Stub(*args, **kw)
        return analysis

    analysis = None
    env = os.environ.copy()
    os.environ["ONES_EDITION"] = edition
    try:
        exec(compile(SPEC.read_text(encoding="utf-8"), str(SPEC), "exec"),
             {"SPECPATH": str(SPEC.parent), "Analysis": Analysis, "PYZ": _Stub, "EXE": EXE,
              "__name__": "__main__"})
    finally:
        os.environ.clear()
        os.environ.update(env)
    return captured


@pytest.mark.parametrize("edition,exe,entry,icon", [
    ("ru", "1S-ERP-RU", "app_ru.py", "icon_ru.ico"),
    ("uk", "1S-ERP-UK", "app_uk.py", "icon_uk.ico"),
    ("en", "1S-ERP-EN", "app_en.py", "icon_en.ico"),
    ("base", "1S-ERP", "desktop_app.py", "icon.ico"),
])
def test_windows_spec_editions(edition, exe, entry, icon):
    got = _run_spec(edition)
    assert got["name"] == exe and got["console"] is False
    [script] = got["_scripts"]
    assert Path(script).name == entry and Path(script).exists()
    assert Path(got["icon"][0]).name == icon and Path(got["icon"][0]).exists()
    assert all(Path(src).exists() for src, _dst in got["_datas"])


def test_windows_spec_rejects_unknown_edition():
    with pytest.raises(SystemExit):
        _run_spec("de")


def test_old_root_specs_are_gone_and_build_script_uses_packaging():
    assert not list(ROOT.glob("*.spec"))
    build = (ROOT / "installer" / "build.py").read_text(encoding="utf-8")
    assert "packaging" in build and "windows.spec" in build
    ast.parse(build)
