"""Migration audit of a 1C/BAS configuration (Sprint 18, product focus).

Input: a folder with a configuration dumped to files (Designer:
Configuration -> "Dump configuration to files" / "Выгрузить конфигурацию в
файлы"), or simply any folder of .bsl / .1s modules.

For every module the audit reports:
    portable        parses with the 1S parser and uses no platform object model
                    (pure business logic: can be ported as is)
    platform-bound  parses, but touches the 1C object model (Справочники.,
                    Движения., Запрос ...): logic must be mapped to the target system
    unparsed        the 1S parser cannot read it yet (a gap to close in core)

Nothing is executed and nothing is written next to the input.
"""
from __future__ import annotations

import json
import re
import threading
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..lexer import Lexer
from ..parser import Parser

# Top-level folders of a configuration dump -> metadata kind.
METADATA_DIRS = {
    "Catalogs": "catalog", "Documents": "document", "DocumentJournals": "document_journal",
    "Enums": "enum", "Constants": "constant", "Reports": "report", "DataProcessors": "data_processor",
    "InformationRegisters": "information_register", "AccumulationRegisters": "accumulation_register",
    "AccountingRegisters": "accounting_register", "CalculationRegisters": "calculation_register",
    "ChartsOfAccounts": "chart_of_accounts", "ChartsOfCharacteristicTypes": "chart_of_characteristic_types",
    "ChartsOfCalculationTypes": "chart_of_calculation_types", "BusinessProcesses": "business_process",
    "Tasks": "task", "ExchangePlans": "exchange_plan", "CommonModules": "common_module",
    "CommonForms": "common_form", "Subsystems": "subsystem", "Roles": "role",
}

MODULE_KINDS = {
    "ObjectModule": "object", "ManagerModule": "manager", "RecordSetModule": "record_set",
    "ValueManagerModule": "value_manager", "CommandModule": "command", "Module": "module",
}

# Platform object model: references that have no meaning outside 1C and must
# be mapped onto the target system. Category -> regex (case-insensitive).
PLATFORM_PATTERNS: dict[str, str] = {
    "catalogs": r"\b(Справочники|Довідники|Catalogs)\.",
    "documents": r"\b(Документы|Документи|Documents)\.",
    "registers": r"\b(РегистрыНакопления|РегистрыСведений|РегистрыБухгалтерии|РегістриНакопичення|РегістриВідомостей|РегістриБухгалтерії|AccumulationRegisters|InformationRegisters|AccountingRegisters)\.",
    "posting": r"\b(Движения|Рухи|RegisterRecords)\.",
    "queries": r"\bНовый\s+Запрос\b|\bНовий\s+Запит\b|\bNew\s+Query\b|\"\s*(ВЫБРАТЬ|ВИБРАТИ|SELECT)\b",
    "enums": r"\b(Перечисления|Перерахування|Enums)\.",
    "constants": r"\b(Константы|Константи|Constants)\.",
    "metadata": r"\b(Метаданные|Метадані|Metadata)\.",
    "forms": r"\b(ЭлементыФормы|Элементы|Елементи|Items)\.|\bОткрытьФорму\b|\bВідкритиФорму\b|\bOpenForm\b",
    "this_object": r"\b(ЭтотОбъект|ЦейОбʼєкт|ЦейОб'єкт|ThisObject)\b",
}
_PLATFORM_RE = {k: re.compile(v, re.IGNORECASE) for k, v in PLATFORM_PATTERNS.items()}

# Compilation directives (&НаСервере, &AtClient ...). The 1S lexer does not
# know them; they say where code runs, not what it does, so they are blanked
# (line numbers kept) before parsing and counted separately.
_DIRECTIVE_RE = re.compile(r"^[ \t]*&[^\r\n]*", re.MULTILINE)
_EXPORT_RE = re.compile(
    r"^[ \t]*(Функция|Функція|Function|Процедура|Procedure)\s+([\wЀ-ӿ]+)\s*\([^)]*\)\s*(Экспорт|Експорт|Export)",
    re.IGNORECASE | re.MULTILINE,
)

PORTABLE, PLATFORM_BOUND, UNPARSED = "portable", "platform-bound", "unparsed"

# Procedure boundaries (RU / UK / EN). Line based on purpose: it works even
# when the module as a whole does not parse yet.
_PROC_START_RE = re.compile(
    r"^[ \t]*(Процедура|Функция|Функція|Procedure|Function)\s+(\w+)\s*\(",
    re.IGNORECASE | re.MULTILINE,
)
_PROC_END_RE = re.compile(
    r"^[ \t]*(КонецПроцедуры|КонецФункции|КінецьПроцедури|КінецьФункції|EndProcedure|EndFunction)\b",
    re.IGNORECASE | re.MULTILINE,
)
_EXPORT_WORD_RE = re.compile(r"\)\s*(Экспорт|Експорт|Export)\b", re.IGNORECASE)


@dataclass
class ProcReport:
    name: str
    kind: str          # procedure | function
    line: int          # 1-based start line
    lines: int         # non-empty, non-comment lines
    exported: bool
    status: str        # portable | platform-bound | unparsed (module did not parse)
    platform_refs: dict[str, int] = field(default_factory=dict)


@dataclass
class ModuleReport:
    path: str
    object_kind: str
    object_name: str
    module_kind: str
    lines: int
    status: str
    platform_refs: dict[str, int] = field(default_factory=dict)
    directives: int = 0
    exports: list[str] = field(default_factory=list)
    error: str | None = None
    procedures: list[ProcReport] = field(default_factory=list)


@dataclass
class AuditReport:
    root: str
    objects: dict[str, int]
    modules: list[ModuleReport]
    metadata: list = field(default_factory=list)   # list[metadata.ObjectMeta]

    @property
    def procedure_totals(self) -> dict[str, dict[str, int]]:
        out = {s: {"procedures": 0, "lines": 0} for s in (PORTABLE, PLATFORM_BOUND, UNPARSED)}
        for m in self.modules:
            for p in m.procedures:
                out[p.status]["procedures"] += 1
                out[p.status]["lines"] += p.lines
        return out

    def odoo_map(self) -> list[dict]:
        from .odoo_map import suggest
        rows = []
        for o in self.metadata:
            s = suggest(o.kind, o.name)
            if not s.model:
                continue
            rows.append({"kind": o.kind, "name": o.name, "synonym": o.synonym, "odoo": s.model,
                         "note": s.note, "attributes": len(o.attributes),
                         "tabular_sections": len(o.tabular_sections), "references": o.references})
        return rows

    @property
    def totals(self) -> dict[str, dict[str, int]]:
        out = {s: {"modules": 0, "lines": 0} for s in (PORTABLE, PLATFORM_BOUND, UNPARSED)}
        for m in self.modules:
            out[m.status]["modules"] += 1
            out[m.status]["lines"] += m.lines
        return out

    @property
    def platform_refs(self) -> dict[str, int]:
        c: Counter[str] = Counter()
        for m in self.modules:
            c.update(m.platform_refs)
        return dict(c.most_common())

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "objects": self.objects,
            "totals": self.totals,
            "platform_refs": self.platform_refs,
            "procedure_totals": self.procedure_totals,
            "odoo_map": self.odoo_map(),
            "modules": [asdict(m) for m in self.modules],
            "metadata": [asdict(o) for o in self.metadata],
        }


def _read(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _locate(path: Path, root: Path) -> tuple[str, str, str]:
    """(object_kind, object_name, module_kind) from the dump layout."""
    parts = path.relative_to(root).parts
    object_kind, object_name = "file", path.stem
    if len(parts) >= 2 and parts[0] in METADATA_DIRS:
        object_kind, object_name = METADATA_DIRS[parts[0]], parts[1]
    module_kind = "form" if "Forms" in parts or "Form" in parts else MODULE_KINDS.get(path.stem, "module")
    return object_kind, object_name, module_kind


PARSE_TIMEOUT_S = 10.0


def _parse_with_timeout(source: str, name: str, timeout: float | None = None) -> str | None:
    """Parse in a daemon thread; return None on success or an error string.

    Audits run over code we did not write: a parser bug that loops forever on
    one module must cost that module, not the whole audit.
    """
    result: dict[str, str | None] = {}

    def work() -> None:
        try:
            Parser(Lexer(source, name).tokenize()).parse()
            result["error"] = None
        except Exception as exc:  # LexerError / ParseError / anything the core trips on
            result["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"

    th = threading.Thread(target=work, daemon=True)
    th.start()
    th.join(PARSE_TIMEOUT_S if timeout is None else timeout)
    if th.is_alive():
        return f"Timeout: parser did not finish in {PARSE_TIMEOUT_S if timeout is None else timeout:.0f}s"
    return result.get("error")


def _lines_of_code(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip() and not line.strip().startswith("//"))


def split_procedures(source: str, module_parsed: bool) -> list[ProcReport]:
    """Procedures/functions of a module with their own platform references.

    A portable function inside a platform-bound module (a VAT formula in a
    document module) is exactly what an integrator can lift as is.
    """
    out: list[ProcReport] = []
    ends = [m.end() for m in _PROC_END_RE.finditer(source)]
    for m in _PROC_START_RE.finditer(source):
        end = next((e for e in ends if e > m.start()), len(source))
        body = source[m.start():end]
        close = body.find(")")
        header = body if close < 0 else body[: body.find("\n", close) if "\n" in body[close:] else len(body)]
        refs = {k: n for k, rx in _PLATFORM_RE.items() if (n := len(rx.findall(body)))}
        status = (PLATFORM_BOUND if refs else PORTABLE) if module_parsed else UNPARSED
        out.append(ProcReport(
            name=m.group(2),
            kind="function" if m.group(1).lower() in ("функция", "функція", "function") else "procedure",
            line=source.count("\n", 0, m.start()) + 1,
            lines=_lines_of_code(body), exported=bool(_EXPORT_WORD_RE.search(header)),
            status=status, platform_refs=refs,
        ))
    return out


def audit_module(path: Path, root: Path) -> ModuleReport:
    source = _read(path)
    object_kind, object_name, module_kind = _locate(path, root)
    directives = len(_DIRECTIVE_RE.findall(source))
    cleaned = _DIRECTIVE_RE.sub("", source)
    refs = {k: n for k, rx in _PLATFORM_RE.items() if (n := len(rx.findall(source)))}
    exports = sorted({m.group(2) for m in _EXPORT_RE.finditer(source)})
    lines = sum(1 for line in source.splitlines() if line.strip() and not line.strip().startswith("//"))
    error = _parse_with_timeout(cleaned, path.name)
    status = UNPARSED if error else (PLATFORM_BOUND if refs else PORTABLE)
    procedures = split_procedures(source, module_parsed=error is None)
    return ModuleReport(
        path=str(path.relative_to(root)), object_kind=object_kind, object_name=object_name,
        module_kind=module_kind, lines=lines, status=status, platform_refs=refs,
        directives=directives, exports=exports, error=error, procedures=procedures,
    )


def audit(root: Path | str) -> AuditReport:
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a folder: {root}")
    objects: Counter[str] = Counter()
    for top, kind in METADATA_DIRS.items():
        d = root / top
        if d.is_dir():
            objects[kind] = sum(1 for p in d.iterdir() if p.is_dir() or p.suffix.lower() == ".xml")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in (".bsl", ".1s"))
    from .metadata import read_metadata  # lazy: metadata imports METADATA_DIRS from here
    return AuditReport(str(root), dict(objects), [audit_module(p, root) for p in files],
                       metadata=read_metadata(root))


# ── Rendering ────────────────────────────────────────────────────────────────

_L = {
    "en": {"title": "1S migration audit", "objects": "Configuration objects", "modules": "Modules",
           "lines": "lines of code", "portable": "Portable as is", "platform-bound": "Uses the 1C object model",
           "unparsed": "Not readable by 1S yet", "refs": "1C object model references", "top": "Largest platform-bound modules",
           "gaps": "Parser gaps (first errors)", "exports": "Exported functions in portable modules", "none": "none",
           "procs": "Procedures", "portable_procs": "Portable procedures (lift as is)", "odoo": "Objects and Odoo candidates", "custom": "need a custom model", "kind": "Kind", "object": "Object", "attrs": "Attributes", "tabs": "Tables", "model": "Odoo", "note": "Note", "line": "line"},
    "ru": {"title": "Аудит миграции 1S", "objects": "Объекты конфигурации", "modules": "Модули",
           "lines": "строк кода", "portable": "Переносятся как есть", "platform-bound": "Завязаны на объектную модель 1С",
           "unparsed": "Пока не читаются 1S", "refs": "Обращения к объектной модели 1С", "top": "Крупнейшие модули, завязанные на платформу",
           "gaps": "Пробелы парсера (первые ошибки)", "exports": "Экспортные функции в переносимых модулях", "none": "нет",
           "procs": "Процедуры", "portable_procs": "Переносимые процедуры (можно перенести как есть)", "odoo": "Объекты и кандидаты в Odoo", "custom": "требуют своей модели", "kind": "Вид", "object": "Объект", "attrs": "Реквизиты", "tabs": "Табл. части", "model": "Odoo", "note": "Заметка", "line": "строка"},
    "uk": {"title": "Аудит міграції 1S", "objects": "Об'єкти конфігурації", "modules": "Модулі",
           "lines": "рядків коду", "portable": "Переносяться як є", "platform-bound": "Прив'язані до об'єктної моделі 1С",
           "unparsed": "Поки не читаються 1S", "refs": "Звернення до об'єктної моделі 1С", "top": "Найбільші модулі, прив'язані до платформи",
           "gaps": "Прогалини парсера (перші помилки)", "exports": "Експортні функції в переносних модулях", "none": "немає",
           "procs": "Процедури", "portable_procs": "Переносні процедури (можна перенести як є)", "odoo": "Обʼєкти та кандидати в Odoo", "custom": "потребують власної моделі", "kind": "Вид", "object": "Обʼєкт", "attrs": "Реквізити", "tabs": "Табл. частини", "model": "Odoo", "note": "Примітка", "line": "рядок"},
}


def render_markdown(report: AuditReport, lang: str = "ru", top: int = 10) -> str:
    t = _L.get(lang, _L["en"])
    totals = report.totals
    all_lines = sum(v["lines"] for v in totals.values()) or 1
    out = [f"# {t['title']}", "", f"`{report.root}`", ""]
    if report.objects:
        out += [f"## {t['objects']}", ""] + [f"- {k}: {v}" for k, v in sorted(report.objects.items())] + [""]
    out += [f"## {t['modules']}: {len(report.modules)}", "", "| | " + t["modules"] + " | " + t["lines"] + " | % |", "| --- | ---: | ---: | ---: |"]
    for s in (PORTABLE, PLATFORM_BOUND, UNPARSED):
        v = totals[s]
        out.append(f"| {t[s]} | {v['modules']} | {v['lines']} | {100 * v['lines'] // all_lines} |")
    out.append("")
    refs = report.platform_refs
    out += [f"## {t['refs']}", ""] + ([f"- {k}: {v}" for k, v in refs.items()] or [f"- {t['none']}"]) + [""]
    bound = sorted((m for m in report.modules if m.status == PLATFORM_BOUND), key=lambda m: -m.lines)[:top]
    out += [f"## {t['top']}", ""] + ([f"- `{m.path}` ({m.lines}): " + ", ".join(f"{k} {v}" for k, v in m.platform_refs.items()) for m in bound] or [f"- {t['none']}"]) + [""]
    gaps = [m for m in report.modules if m.status == UNPARSED][:top]
    out += [f"## {t['gaps']}", ""] + ([f"- `{m.path}`: {m.error}" for m in gaps] or [f"- {t['none']}"]) + [""]
    exports = sorted({f"{m.object_name}.{e}" for m in report.modules if m.status == PORTABLE for e in m.exports})
    out += [f"## {t['exports']}", ""] + ([f"- {e}" for e in exports[:50]] or [f"- {t['none']}"]) + [""]

    # Procedures: the unit an integrator actually ports
    ptot = report.procedure_totals
    all_plines = sum(v["lines"] for v in ptot.values()) or 1
    out += [f"## {t['procs']}: {sum(v['procedures'] for v in ptot.values())}", "",
            f"| | {t['procs']} | {t['lines']} | % |", "| --- | ---: | ---: | ---: |"]
    for s in (PORTABLE, PLATFORM_BOUND, UNPARSED):
        v = ptot[s]
        out.append(f"| {t[s]} | {v['procedures']} | {v['lines']} | {100 * v['lines'] // all_plines} |")
    out.append("")
    portable = sorted(((m, p) for m in report.modules for p in m.procedures if p.status == PORTABLE),
                      key=lambda mp: (-mp[1].lines, mp[0].object_name, mp[1].name))
    out += [f"## {t['portable_procs']}", ""]
    out += [f"- `{m.object_name}.{p.name}` ({p.lines}, {t['line']} {p.line}){' Export' if p.exported else ''}"
            for m, p in portable[:top * 3]] or [f"- {t['none']}"]
    out.append("")

    rows = report.odoo_map()
    if rows:
        custom = sum(1 for r in rows if r["odoo"] == "custom")
        out += [f"## {t['odoo']}", "", f"{len(rows) - custom} / {len(rows)}; {custom} {t['custom']}.", "",
                f"| {t['kind']} | {t['object']} | {t['attrs']} | {t['tabs']} | {t['model']} | {t['note']} |",
                "| --- | --- | ---: | ---: | --- | --- |"]
        for r in sorted(rows, key=lambda r: (r["odoo"] == "custom", r["kind"], r["name"])):
            out.append(f"| {r['kind']} | {r['name']} | {r['attributes']} | {r['tabular_sections']} | {r['odoo']} | {r['note']} |")
        out.append("")
    return "\n".join(out)


def render_json(report: AuditReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
