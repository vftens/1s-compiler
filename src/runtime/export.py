"""
1S: ERP Free Edition — Excel/PDF export.

All exporters work in-memory (BytesIO) and never write to disk.
Trilingual support via lang parameter ('en', 'ru', 'uk').
"""
from __future__ import annotations

import io
import sqlite3
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# ---------------------------------------------------------------------------
# Column header translations
# ---------------------------------------------------------------------------

_PAYROLL_HEADERS = {
    "en": ["emp_id", "emp_name", "period", "gross", "deductions", "net", "tax_profile"],
    "ru": ["Таб. №", "Сотрудник", "Период", "Начислено", "Удержания", "К выплате", "Налог. профиль"],
    "uk": ["Таб. №", "Співробітник", "Період", "Нараховано", "Утримання", "До виплати", "Подат. профіль"],
}

_BUDGET_HEADERS = {
    "en": ["org_id", "org_name", "period", "account", "allocated", "consumed", "remaining", "utilization_%"],
    "ru": ["ID орг.", "Орг. единица", "Период", "Счёт", "Выделено", "Израсходовано", "Остаток", "Утилизация, %"],
    "uk": ["ID орг.", "Орг. одиниця", "Період", "Рахунок", "Виділено", "Витрачено", "Залишок", "Утилізація, %"],
}

_SHEET_NAMES = {
    "payroll": {"en": "Payroll", "ru": "Зарплата", "uk": "Зарплата"},
    "budget": {"en": "Budget", "ru": "Бюджет", "uk": "Бюджет"},
}


def _connect(db_path: Path) -> sqlite3.Connection:
    from .db import connect as _db_connect
    return _db_connect(db_path)


def _header_row(ws, headers: list[str]) -> None:
    fill = PatternFill("solid", fgColor="2F5496")
    font = Font(bold=True, color="FFFFFF")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center")


# ---------------------------------------------------------------------------
# PayrollExporter
# ---------------------------------------------------------------------------

class PayrollExporter:
    def __init__(self, db_path: Path, period: str, lang: str = "en") -> None:
        self._db = db_path
        self._period = period
        self._lang = lang if lang in ("en", "ru", "uk") else "en"

    def export(self) -> bytes:
        """Return payslips.xlsx bytes. One sheet; one row per employee record."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = _SHEET_NAMES["payroll"][self._lang]
        headers = _PAYROLL_HEADERS[self._lang]
        _header_row(ws, headers)

        try:
            conn = _connect(self._db)
        except FileNotFoundError:
            raise

        try:
            rows = conn.execute(
                "SELECT emp_id, emp_name, period, gross, deductions, net, tax_profile "
                "FROM payroll_results WHERE period = ? ORDER BY emp_name",
                (self._period,),
            ).fetchall()
        finally:
            conn.close()

        for r_idx, row in enumerate(rows, 2):
            for c_idx, val in enumerate(
                [row["emp_id"], row["emp_name"], row["period"],
                 row["gross"], row["deductions"], row["net"], row["tax_profile"]],
                1,
            ):
                ws.cell(row=r_idx, column=c_idx, value=val)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# BudgetExporter
# ---------------------------------------------------------------------------

class BudgetExporter:
    def __init__(self, db_path: Path, period: str, lang: str = "en") -> None:
        self._db = db_path
        self._period = period
        self._lang = lang if lang in ("en", "ru", "uk") else "en"

    def export(self) -> bytes:
        """Return budget.xlsx bytes."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = _SHEET_NAMES["budget"][self._lang]
        headers = _BUDGET_HEADERS[self._lang]
        _header_row(ws, headers)

        try:
            conn = _connect(self._db)
        except FileNotFoundError:
            raise

        try:
            rows = conn.execute(
                """
                SELECT a.org_id,
                       COALESCE(n.name, a.org_id) AS org_name,
                       a.period,
                       a.account,
                       a.allocated,
                       COALESCE(e.consumed, 0.0) AS consumed
                FROM budget_allocations a
                LEFT JOIN org_nodes n ON n.node_id = a.org_id
                LEFT JOIN (
                    SELECT org_id, account, SUM(amount) AS consumed
                    FROM budget_entries
                    WHERE period = ?
                    GROUP BY org_id, account
                ) e ON e.org_id = a.org_id AND e.account = a.account
                WHERE a.period = ?
                ORDER BY a.org_id, a.account
                """,
                (self._period, self._period),
            ).fetchall()
        finally:
            conn.close()

        for r_idx, row in enumerate(rows, 2):
            allocated = row["allocated"]
            consumed = row["consumed"]
            remaining = allocated - consumed
            utilization = None if allocated == 0 else round(consumed / allocated * 100, 2)
            for c_idx, val in enumerate(
                [row["org_id"], row["org_name"], row["period"],
                 row["account"], allocated, consumed, remaining, utilization],
                1,
            ):
                ws.cell(row=r_idx, column=c_idx, value=val)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# OrgPdfExporter
# ---------------------------------------------------------------------------

class OrgPdfExporter:
    def __init__(self, db_path: Path) -> None:
        self._db = db_path

    def export(self) -> bytes:
        """Return org_chart.pdf bytes using reportlab. Lazy import."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError as exc:
            raise ImportError(
                "reportlab is required for PDF export. Install with: pip install reportlab"
            ) from exc

        try:
            conn = _connect(self._db)
        except FileNotFoundError:
            raise

        try:
            rows = conn.execute(
                "SELECT node_id, name, node_type, parent_id FROM org_nodes ORDER BY parent_id NULLS FIRST, node_id"
            ).fetchall()
        finally:
            conn.close()

        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 2 * cm, "Organizational Chart")

        if not rows:
            c.setFont("Helvetica", 12)
            c.drawCentredString(width / 2, height / 2, "No organizational data")
            c.save()
            return buf.getvalue()

        # Build parent → children map
        children: dict[Optional[str], list] = {}
        for row in rows:
            pid = row["parent_id"]
            children.setdefault(pid, []).append(dict(row))

        # Render tree (depth-first, max depth 6)
        y = height - 4 * cm
        c.setFont("Helvetica", 10)

        def render(node_id: Optional[str], depth: int) -> None:
            nonlocal y
            if depth > 6 or y < 2 * cm:
                return
            for child in children.get(node_id, []):
                indent = depth * 1.2 * cm
                label = f"{child['name']}  [{child['node_type']}]  id={child['node_id']}"
                c.drawString(2 * cm + indent, y, label)
                y -= 0.6 * cm
                render(child["node_id"], depth + 1)

        render(None, 0)
        c.save()
        return buf.getvalue()
