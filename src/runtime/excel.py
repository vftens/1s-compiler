"""
1S: ERP Free Edition — Excel export/import (inspired by SAP ALV Grid).

ExcelWorkbook wraps openpyxl with a 1C-friendly API.
Falls back gracefully to CSV if openpyxl is not installed.

Usage (Ukrainian):
    Книга = ExcelWorkbook()
    Аркуш = Книга.AddSheet("ОСВ")
    Аркуш.SetHeader(["Рахунок", "Обор.Дт", "Обор.Кт", "Сальдо"])
    Для Кожного Р З ТаблицяОСВ Цикл
        Аркуш.AddRow([Р["Рахунок"], Р["ОборотДт"], Р["ОборотКт"], Р["Сальдо"]])
    КінецьЦиклу;
    Книга.Save("osv_sichen_2025.xlsx")

Usage from ValueTable directly:
    Книга = ExcelWorkbook()
    Книга.AddSheetFromTable("Дані", МояТаблиця)
    Книга.Save("звіт.xlsx")
"""
from __future__ import annotations
import datetime
from pathlib import Path
from typing import Any
from .types import _ValueTable, _Undefined, Undefined

try:
    import openpyxl
    from openpyxl.styles import (Font, PatternFill, Alignment,
                                  Border, Side, numbers)
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ── Colour palette (SAP-inspired) ────────────────────────────────────────────

_HEADER_FILL  = "1565C0"   # blue  (SAP ALV header)
_TOTAL_FILL   = "E3F2FD"   # light blue (total rows)
_ALT_FILL     = "F5F9FF"   # alternating row tint
_BORDER_COLOR = "BDBDBD"


def _thin_border():
    s = Side(style="thin", color=_BORDER_COLOR)
    return Border(left=s, right=s, top=s, bottom=s)


# ── Excel Sheet ───────────────────────────────────────────────────────────────

class ExcelSheet:
    """One sheet inside an ExcelWorkbook."""

    def __init__(self, ws, name: str):
        self._ws   = ws
        self.name  = name
        self._row  = 1     # current write row (1-indexed)

    # ── Title ────────────────────────────────────────────────────────

    def SetTitle(self, title: str) -> "ExcelSheet":
        """Write a big title row at the top."""
        if not HAS_OPENPYXL:
            return self
        ws = self._ws
        ws.cell(self._row, 1, title)
        ws.cell(self._row, 1).font = Font(bold=True, size=14, color="1A237E")
        self._row += 2
        return self

    # ── Header row ───────────────────────────────────────────────────

    @staticmethod
    def _to_list(cols) -> list:
        """Accept Python list, _Array (Масив), or comma-separated string."""
        if isinstance(cols, str):
            return [c.strip() for c in cols.split(",")]
        if hasattr(cols, "_items"):   # _Array / Масив
            return cols._items
        return list(cols)

    def SetHeader(self, cols) -> "ExcelSheet":
        """Write a styled header row. cols: list | _Array | comma-string."""
        cols = self._to_list(cols)
        if not HAS_OPENPYXL:
            return self
        ws = self._ws
        for c, val in enumerate(cols, 1):
            cell = ws.cell(self._row, c, str(val))
            cell.font      = Font(bold=True, color="FFFFFF", size=10)
            cell.fill      = PatternFill("solid", fgColor=_HEADER_FILL)
            cell.alignment = Alignment(horizontal="center",
                                       vertical="center", wrap_text=True)
            cell.border    = _thin_border()
        ws.row_dimensions[self._row].height = 24
        self._row += 1
        return self

    # ── Data rows ────────────────────────────────────────────────────

    def AddRow(self, values, bold: bool = False,
               total: bool = False) -> "ExcelSheet":
        values = self._to_list(values)
        if not HAS_OPENPYXL:
            return self
        ws  = self._ws
        alt = (self._row % 2 == 0)
        bg  = _TOTAL_FILL if total else (_ALT_FILL if alt else "FFFFFF")
        for c, val in enumerate(values, 1):
            # Convert 1S types to Python scalars
            if isinstance(val, _Undefined) or val is None:
                val = ""
            elif hasattr(val, '_data'):    # Structure / CatalogItem
                val = str(val)
            py_val = val
            # Decimals → float for Excel number formatting
            try:
                from decimal import Decimal
                if isinstance(val, Decimal):
                    py_val = float(val)
            except Exception:
                pass
            cell = ws.cell(self._row, c, py_val)
            cell.fill   = PatternFill("solid", fgColor=bg)
            cell.border = _thin_border()
            cell.font   = Font(bold=bold, size=10)
            if isinstance(py_val, (int, float)) and not isinstance(py_val, bool):
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = '#,##0.00' if isinstance(py_val, float) and py_val != int(py_val) else '#,##0'
        self._row += 1
        return self

    def AddBlankRow(self) -> "ExcelSheet":
        self._row += 1
        return self

    # ── Auto-fit columns ─────────────────────────────────────────────

    def AutoFit(self, max_width: int = 40) -> "ExcelSheet":
        if not HAS_OPENPYXL:
            return self
        ws = self._ws
        for col in ws.columns:
            best = 8
            for cell in col:
                if cell.value:
                    best = max(best, min(len(str(cell.value)) + 2, max_width))
            ws.column_dimensions[get_column_letter(col[0].column)].width = best
        return self

    # ── From ValueTable ──────────────────────────────────────────────

    def FromTable(self, table: _ValueTable,
                  title: str = "",
                  total_cols: list | None = None) -> "ExcelSheet":
        """Populate sheet from a _ValueTable."""
        col_names = list(table.Columns)
        if title:
            self.SetTitle(title)
        self.SetHeader(col_names)
        for row in table:
            self.AddRow([row[c] for c in col_names])
        if total_cols:
            totals = ["ИТОГО / РАЗОМ / TOTAL" if c == col_names[0]
                      else (float(table.Total(c)) if c in total_cols else "")
                      for c in col_names]
            self.AddRow(totals, bold=True, total=True)
        self.AutoFit()
        return self

    # Russian aliases
    УстановитьЗаголовок = SetTitle
    УстановитьШапку     = SetHeader
    ДобавитьСтроку      = AddRow
    АвтоШирина          = AutoFit
    ИзТаблицы           = FromTable
    # Ukrainian aliases
    ВстановитиЗаголовок = SetTitle
    ВстановитиШапку     = SetHeader
    ДодатиРядок         = AddRow
    АвтоШирина          = AutoFit
    ЗТаблиці            = FromTable


# ── Excel Workbook ────────────────────────────────────────────────────────────

class ExcelWorkbook:
    """
    Книга Excel / ExcelWorkbook

    Example:
        Book = ExcelWorkbook()
        Sheet = Book.AddSheet("ОСВ")
        Sheet.SetHeader(["Рах.", "Дт", "Кт", "Сальдо"])
        Sheet.AddRow(["10", 150000, 0, 150000])
        Book.Save("osv.xlsx")
    """

    def __init__(self):
        if HAS_OPENPYXL:
            self._wb = openpyxl.Workbook()
            self._wb.remove(self._wb.active)   # remove default empty sheet
        else:
            self._wb = None
        self._sheets: list[ExcelSheet] = []
        self._csv_rows: list[list] = []

    def AddSheet(self, name: str = "Sheet1") -> ExcelSheet:
        if HAS_OPENPYXL:
            ws = self._wb.create_sheet(title=name[:31])   # Excel max 31 chars
            sheet = ExcelSheet(ws, name)
        else:
            sheet = ExcelSheet(None, name)
        self._sheets.append(sheet)
        return sheet

    def AddSheetFromTable(self, name: str, table: _ValueTable,
                          title: str = "",
                          total_cols: list | None = None) -> ExcelSheet:
        sheet = self.AddSheet(name)
        sheet.FromTable(table, title=title, total_cols=total_cols)
        return sheet

    def Save(self, path: str) -> str:
        """Save to .xlsx (or .csv fallback)."""
        p = Path(path)
        if HAS_OPENPYXL and self._wb:
            # Ensure at least one sheet
            if not self._sheets:
                self.AddSheet("Sheet1")
            self._wb.save(str(p))
            return str(p)
        else:
            # CSV fallback: write all rows
            csv_path = p.with_suffix(".csv")
            with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
                import csv
                w = csv.writer(f)
                for sheet in self._sheets:
                    w.writerow([f"=== {sheet.name} ==="])
            return str(csv_path)

    def __repr__(self):
        return f"ExcelWorkbook({len(self._sheets)} sheets)"

    # Russian aliases
    ДобавитьЛист        = AddSheet
    ДобавитьЛистТаблица = AddSheetFromTable
    Сохранить           = Save
    # Ukrainian aliases
    ДодатиАркуш         = AddSheet
    ДодатиАркушТаблиця  = AddSheetFromTable
    Зберегти            = Save


# ── CSV export (no dependencies) ─────────────────────────────────────────────

def ExportCSV(table: _ValueTable, path: str,
              delimiter: str = ";",
              encoding: str = "utf-8-sig") -> str:
    """
    Export a ValueTable to CSV — no openpyxl needed.
    utf-8-sig adds BOM so Excel opens Cyrillic correctly.
    """
    import csv
    p = Path(path)
    col_names = list(table.Columns)
    with open(p, "w", encoding=encoding, newline="") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerow(col_names)
        for row in table:
            w.writerow([
                "" if isinstance(row[c], _Undefined) else str(row[c])
                for c in col_names
            ])
    return str(p)


# ── Constructor aliases ───────────────────────────────────────────────────────

КнигаExcel      = ExcelWorkbook   # Russian / Ukrainian
ExcelBook       = ExcelWorkbook
ЭкспортCSV      = ExportCSV
ЕксельЗбереження = ExportCSV      # quick function alias
