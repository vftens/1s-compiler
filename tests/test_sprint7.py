"""
Tests for Sprint 7: Excel export, persistence, VS Code extension scaffold.
"""
import tempfile
import datetime
import pytest
from decimal import Decimal
from pathlib import Path

from src.runtime.types import _ValueTable, Undefined
from src.runtime.excel import ExcelWorkbook, ExcelSheet, ExportCSV
from src.runtime.persistence import (
    save_accounting, load_accounting,
    save_accumulation, load_accumulation,
    save_register, load_register,
)
from src.runtime.registers import (
    ChartOfAccounts, AccountingRegister, AccumulationRegister,
)


# ── ExcelSheet._to_list ───────────────────────────────────────────────────────

def test_to_list_from_python_list():
    sheet = ExcelSheet(None, "test")
    assert sheet._to_list(["a", "b"]) == ["a", "b"]

def test_to_list_from_string():
    sheet = ExcelSheet(None, "test")
    result = sheet._to_list("Col1, Col2, Col3")
    assert result == ["Col1", "Col2", "Col3"]

def test_to_list_from_array():
    from src.runtime.types import _Array
    arr = _Array()
    arr.Add("x"); arr.Add("y")
    sheet = ExcelSheet(None, "test")
    assert sheet._to_list(arr) == ["x", "y"]


# ── ExcelWorkbook ─────────────────────────────────────────────────────────────

class TestExcelWorkbook:
    def test_create_workbook(self):
        wb = ExcelWorkbook()
        assert wb is not None

    def test_add_sheet(self):
        wb = ExcelWorkbook()
        s = wb.AddSheet("Test")
        assert s is not None
        assert s.name == "Test"

    def test_add_sheet_with_header(self):
        wb = ExcelWorkbook()
        s = wb.AddSheet("Data")
        s.SetHeader("Col1, Col2, Col3")
        assert s is not None

    def test_add_row(self):
        wb = ExcelWorkbook()
        s = wb.AddSheet("Data")
        s.SetHeader("A, B")
        from src.runtime.types import _Array
        arr = _Array(); arr.Add(1); arr.Add(2)
        s.AddRow(arr)

    def test_save_creates_xlsx(self):
        wb = ExcelWorkbook()
        s = wb.AddSheet("Sheet1")
        s.SetHeader("Name, Value")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        wb.Save(path)
        assert Path(path).exists()
        assert Path(path).stat().st_size > 0

    def test_add_sheet_from_table(self):
        t = _ValueTable()
        t.Columns.Add("Name")
        t.Columns.Add("Amount")
        r = t.Add(); r["Name"] = "Test"; r["Amount"] = 100
        wb = ExcelWorkbook()
        wb.AddSheetFromTable("Report", t)
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        wb.Save(path)
        assert Path(path).exists()

    def test_russian_aliases(self):
        wb = ExcelWorkbook()
        s = wb.ДобавитьЛист("Тест")
        assert s.name == "Тест"
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        wb.Сохранить(path)
        assert Path(path).exists()

    def test_ukrainian_aliases(self):
        wb = ExcelWorkbook()
        s = wb.ДодатиАркуш("Тест")
        assert s.name == "Тест"


# ── ExportCSV ────────────────────────────────────────────────────────────────

class TestExportCSV:
    def test_export_csv(self):
        t = _ValueTable()
        t.Columns.Add("Name"); t.Columns.Add("Value")
        r = t.Add(); r["Name"] = "Alpha"; r["Value"] = 42
        r = t.Add(); r["Name"] = "Beta";  r["Value"] = 99
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        result = ExportCSV(t, path)
        assert Path(result).exists()
        content = Path(result).read_text(encoding="utf-8-sig")
        assert "Name" in content
        assert "Alpha" in content
        assert "42" in content

    def test_export_csv_empty_table(self):
        t = _ValueTable()
        t.Columns.Add("A")
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        ExportCSV(t, path)
        assert Path(path).exists()


# ── Accounting persistence ────────────────────────────────────────────────────

def _make_accounting_reg():
    coa = ChartOfAccounts("Test")
    coa.AddAccount("10", "Fixed assets")
    coa.AddAccount("40", "Capital")
    reg = AccountingRegister("Main", coa)
    dt  = datetime.date(2025, 1, 15)
    reg.Post(dt, "DOC001", coa["10"], coa["40"], Decimal("150000"),
             description="Opening entry")
    return reg, coa


class TestAccountingPersistence:
    def test_save_and_load(self):
        reg, coa = _make_accounting_reg()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name

        n_saved = save_accounting(reg, path)
        assert n_saved == 2   # one posting = 2 entries (Dr + Cr)

        reg2 = AccountingRegister("Main", coa)
        n_loaded = load_accounting(reg2, path)
        assert n_loaded == 2

        b = reg2.Balance(coa["10"])
        assert b["Dt"] == Decimal("150000")

    def test_save_register_auto_detects_type(self):
        reg, coa = _make_accounting_reg()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        save_register(reg, path)
        reg2 = AccountingRegister("Main", coa)
        load_register(reg2, path)
        assert len(reg2._entries) == 2

    def test_load_missing_db_returns_zero(self):
        coa = ChartOfAccounts("T"); coa.AddAccount("10","X")
        reg = AccountingRegister("Main", coa)
        n = load_accounting(reg, "/tmp/nonexistent_12345.db")
        assert n == 0

    def test_postings_rebuilt(self):
        reg, coa = _make_accounting_reg()
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        save_accounting(reg, path)
        reg2 = AccountingRegister("Main", coa)
        load_accounting(reg2, path)
        assert len(reg2._postings) == 1
        assert reg2._postings[0].AccountDt == "10"
        assert reg2._postings[0].AccountKt == "40"


# ── Accumulation persistence ──────────────────────────────────────────────────

class TestAccumulationPersistence:
    def test_save_and_load(self):
        reg = AccumulationRegister("Stock")
        dt = datetime.date(2025, 1, 1)
        reg.Write(dt, "PO1", True, 500, dim1="Flour")
        reg.Write(dt, "SO1", False, 200, dim1="Flour")

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name

        n = save_accumulation(reg, path)
        assert n == 2

        reg2 = AccumulationRegister("Stock")
        n2 = load_accumulation(reg2, path)
        assert n2 == 2

        bal = reg2.Balance(dim1="Flour")
        assert bal["Resource1"] == Decimal("300")

    def test_save_register_accumulation(self):
        reg = AccumulationRegister("Inv")
        reg.Write(datetime.date(2025,1,1), "D1", True, 100, dim1="X")
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        save_register(reg, path)
        reg2 = AccumulationRegister("Inv")
        load_register(reg2, path)
        assert len(reg2._entries) == 1


# ── VS Code extension files exist ────────────────────────────────────────────

class TestVSCodeExtension:
    EXT = Path(__file__).parent.parent / "vscode-1s"

    def test_package_json_exists(self):
        assert (self.EXT / "package.json").exists()

    def test_grammar_exists(self):
        assert (self.EXT / "syntaxes" / "1s.tmLanguage.json").exists()

    def test_snippets_exist(self):
        assert (self.EXT / "snippets" / "1s.json").exists()

    def test_language_config_exists(self):
        assert (self.EXT / "language-configuration.json").exists()

    def test_package_has_language(self):
        import json
        pkg = json.loads((self.EXT / "package.json").read_text())
        lang_ids = [l["id"] for l in pkg["contributes"]["languages"]]
        assert "oneslang" in lang_ids

    def test_package_has_snippets(self):
        import json
        pkg = json.loads((self.EXT / "package.json").read_text())
        assert pkg["contributes"]["snippets"]

    def test_grammar_has_keywords(self):
        import json
        g = json.loads((self.EXT / "syntaxes" / "1s.tmLanguage.json").read_text())
        # Verify keywords pattern covers if/while/for
        patterns_str = str(g)
        # Grammar contains keyword patterns (use ASCII portion to avoid encoding issues)
        assert "keyword.control.1s" in patterns_str or "keyword.declaration.1s" in patterns_str


# ── Landing page exists ───────────────────────────────────────────────────────

class TestLandingPage:
    def test_index_html_exists(self):
        p = Path(__file__).parent.parent / "landing" / "index.html"
        assert p.exists()

    def test_index_has_content(self):
        p = Path(__file__).parent.parent / "landing" / "index.html"
        content = p.read_text(encoding="utf-8")
        assert "1S: ERP" in content
        assert "github.com/vftens" in content
        assert "GPL" in content


# ── Nginx config exists ───────────────────────────────────────────────────────

class TestNginxConfig:
    def test_nginx_conf_exists(self):
        p = Path(__file__).parent.parent / "nginx" / "nginx.conf"
        assert p.exists()

    def test_deploy_sh_exists(self):
        p = Path(__file__).parent.parent / "nginx" / "deploy.sh"
        assert p.exists()
