"""
1S: ERP Free Edition — Financial Reporting Module (Sprint 15).

Three standard financial statements:
  TrialBalanceReport   — Оборотно-сальдова відомість / ОСВ
  BalanceSheetReport   — Баланс / Balance Sheet
  IncomeStatement      — Звіт про фінансові результати / P&L

All reports follow the same pattern:
  compute(period, db_path) -> dict        pure computation, no side effects
  to_excel(data)           -> BytesIO     in-memory xlsx
  to_pdf(data)             -> BytesIO     in-memory pdf
"""
from __future__ import annotations

import io
import logging
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .db import connect as _db_connect

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chart of accounts — lazy-loaded with fallback
# ---------------------------------------------------------------------------

_HARDCODED_MAPPING: dict[str, str] = {
    "10": "fixed_assets", "11": "fixed_assets", "12": "fixed_assets",
    "13": "fixed_assets", "14": "fixed_assets", "15": "fixed_assets",
    "20": "current_assets", "21": "current_assets", "22": "current_assets",
    "25": "current_assets", "26": "current_assets", "28": "current_assets",
    "30": "current_assets", "31": "current_assets", "33": "current_assets",
    "34": "current_assets", "35": "current_assets", "36": "current_assets",
    "37": "current_assets",
    "40": "equity", "41": "equity", "42": "equity", "43": "equity", "44": "equity",
    "50": "long_term_liabilities", "51": "long_term_liabilities",
    "52": "long_term_liabilities", "53": "long_term_liabilities",
    "55": "long_term_liabilities",
    "60": "current_liabilities", "61": "current_liabilities",
    "62": "current_liabilities", "63": "current_liabilities",
    "64": "current_liabilities", "65": "current_liabilities",
    "66": "current_liabilities", "67": "current_liabilities",
    "68": "current_liabilities",
    "70": "revenue", "71": "revenue", "72": "revenue", "73": "revenue",
    "74": "revenue",
    "80": "operating_expenses", "81": "operating_expenses",
    "82": "operating_expenses", "83": "operating_expenses",
    "90": "cogs", "91": "operating_expenses", "92": "operating_expenses",
    "93": "operating_expenses", "94": "operating_expenses",
    "95": "operating_expenses", "96": "operating_expenses",
    "97": "operating_expenses", "98": "operating_expenses",
    "99": "operating_expenses",
}

_PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles"
_YAML_PATH = _PROFILES_DIR / "chart_of_accounts.yaml"
_account_mapping: Optional[dict[str, str]] = None


def _load_account_mapping() -> dict[str, str]:
    global _account_mapping
    if _account_mapping is not None:
        return _account_mapping
    try:
        import yaml  # type: ignore
        with open(_YAML_PATH, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        if isinstance(doc, dict) and isinstance(doc.get("accounts"), dict):
            _account_mapping = {str(k): str(v) for k, v in doc["accounts"].items()}
            return _account_mapping
        warnings.warn("chart_of_accounts.yaml malformed — using hardcoded default mapping")
    except ImportError:
        warnings.warn("pyyaml not installed — using hardcoded default account mapping")
    except FileNotFoundError:
        warnings.warn("profiles/chart_of_accounts.yaml not found — using hardcoded default")
    except Exception as exc:
        warnings.warn(f"Failed to load chart_of_accounts.yaml ({exc}) — using hardcoded default")
    _account_mapping = dict(_HARDCODED_MAPPING)
    return _account_mapping


def _bucket_for(account: str) -> str:
    """Return financial bucket for a given account code string."""
    mapping = _load_account_mapping()
    for prefix_len in (3, 2, 1):
        prefix = account[:prefix_len]
        if prefix in mapping:
            return mapping[prefix]
    return "other"


# ---------------------------------------------------------------------------
# Period validation
# ---------------------------------------------------------------------------

_PERIOD_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


def _valid_period(period: str) -> bool:
    return bool(_PERIOD_RE.match(period))


def _ytd_prefix(period: str) -> str:
    """Return the year portion for YTD LIKE filter, e.g. '2026-07' -> '2026-'"""
    return period[:5]  # '2026-'


def _ytd_month(period: str) -> str:
    """Return month string '07' from '2026-07'."""
    return period[5:]


# ---------------------------------------------------------------------------
# Excel / PDF helpers
# ---------------------------------------------------------------------------

def _xlsx_header_row(ws, headers: list[str]) -> None:
    try:
        from openpyxl.styles import Font, PatternFill, Alignment
        fill = PatternFill("solid", fgColor="2F5496")
        font = Font(bold=True, color="FFFFFF")
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = fill
            cell.font = font
            cell.alignment = Alignment(horizontal="center")
    except ImportError:
        for col, h in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=h)


# ---------------------------------------------------------------------------
# Column headers (display-only — never used as JSON keys)
# ---------------------------------------------------------------------------

_TB_DISPLAY_HEADERS = {
    "en": ["Account", "Account Name", "Opening Dr", "Opening Cr",
           "Period Dr", "Period Cr", "Closing Dr", "Closing Cr"],
    "ru": ["Счёт", "Наименование", "Нач. Дт", "Нач. Кт",
           "Об. Дт", "Об. Кт", "Кон. Дт", "Кон. Кт"],
    "uk": ["Рахунок", "Найменування", "Поч. Дт", "Поч. Кт",
           "Об. Дт", "Об. Кт", "Кін. Дт", "Кін. Кт"],
}

_BS_SECTION_LABELS = {
    "en": {
        "current_assets": "Current Assets",
        "fixed_assets": "Non-current Assets",
        "current_liabilities": "Current Liabilities",
        "long_term_liabilities": "Long-term Liabilities",
        "equity": "Equity",
        "total_assets": "Total Assets",
        "total_liabilities_equity": "Total Liabilities + Equity",
        "difference": "Difference (imbalance)",
    },
    "ru": {
        "current_assets": "Оборотные активы",
        "fixed_assets": "Необоротные активы",
        "current_liabilities": "Текущие обязательства",
        "long_term_liabilities": "Долгосрочные обязательства",
        "equity": "Собственный капитал",
        "total_assets": "Итого активов",
        "total_liabilities_equity": "Итого обязательств и капитала",
        "difference": "Разница (дисбаланс)",
    },
    "uk": {
        "current_assets": "Оборотні активи",
        "fixed_assets": "Необоротні активи",
        "current_liabilities": "Поточні зобов'язання",
        "long_term_liabilities": "Довгострокові зобов'язання",
        "equity": "Власний капітал",
        "total_assets": "Разом активів",
        "total_liabilities_equity": "Разом зобов'язань та капіталу",
        "difference": "Різниця (дисбаланс)",
    },
}

_IS_SECTION_LABELS = {
    "en": {
        "revenue": "Revenue",
        "cogs": "Cost of Goods Sold",
        "gross_profit": "Gross Profit",
        "operating_expenses": "Operating Expenses",
        "payroll": "Payroll Expenses",
        "operating_profit": "Operating Profit (EBIT)",
        "other": "Other Income / Expense",
        "net_profit": "Net Profit / (Loss)",
    },
    "ru": {
        "revenue": "Выручка",
        "cogs": "Себестоимость продаж",
        "gross_profit": "Валовая прибыль",
        "operating_expenses": "Операционные расходы",
        "payroll": "Расходы на оплату труда",
        "operating_profit": "Операционная прибыль (EBIT)",
        "other": "Прочие доходы / расходы",
        "net_profit": "Чистая прибыль / (убыток)",
    },
    "uk": {
        "revenue": "Дохід",
        "cogs": "Собівартість продажів",
        "gross_profit": "Валовий прибуток",
        "operating_expenses": "Операційні витрати",
        "payroll": "Витрати на оплату праці",
        "operating_profit": "Операційний прибуток (EBIT)",
        "other": "Інші доходи / витрати",
        "net_profit": "Чистий прибуток / (збиток)",
    },
}


def _safe_float(val) -> float:
    """Convert TEXT or numeric DB value to float. Returns 0.0 on failure."""
    if val is None:
        return 0.0
    try:
        result = float(val)
        if result != result:  # NaN check
            return 0.0
        return result
    except (ValueError, TypeError):
        logger.warning("Non-numeric amount value %r — treated as 0.0", val)
        return 0.0


# ---------------------------------------------------------------------------
# TrialBalanceReport
# ---------------------------------------------------------------------------

class TrialBalanceError(Exception):
    """Raised when double-entry integrity is violated."""


class TrialBalanceReport:
    """Оборотно-сальдова відомість / Trial Balance."""

    @staticmethod
    def compute(period: str, db_path: Path) -> dict:
        """
        Returns:
          {report, period, generated_at, rows, totals, integrity, opening_balance_note}
        Each row has canonical snake_case keys (never translated).
        """
        conn = _db_connect(db_path)
        try:
            raw = conn.execute(
                """
                SELECT account,
                       SUM(CASE WHEN entry_type='debit'  THEN CAST(amount AS REAL) ELSE 0 END) AS period_debit,
                       SUM(CASE WHEN entry_type='credit' THEN CAST(amount AS REAL) ELSE 0 END) AS period_credit
                FROM budget_entries
                WHERE period = ?
                GROUP BY account
                ORDER BY account
                LIMIT 10001
                """,
                (period,),
            ).fetchall()
        finally:
            conn.close()

        truncated = len(raw) > 10000
        raw = raw[:10000]

        rows = []
        total_dr = 0.0
        total_cr = 0.0
        for r in raw:
            dr = _safe_float(r["period_debit"])
            cr = _safe_float(r["period_credit"])
            closing_dr = max(dr - cr, 0.0)
            closing_cr = max(cr - dr, 0.0)
            total_dr += dr
            total_cr += cr
            rows.append({
                "account_code":    str(r["account"] or ""),
                "account_name":    str(r["account"] or ""),  # name lookup deferred
                "opening_debit":   0.0,  # see opening_balance_note
                "opening_credit":  0.0,
                "period_debit":    round(dr, 2),
                "period_credit":   round(cr, 2),
                "closing_debit":   round(closing_dr, 2),
                "closing_credit":  round(closing_cr, 2),
            })

        balanced = abs(total_dr - total_cr) < 0.005
        return {
            "report":       "trial-balance",
            "period":       period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rows":         rows,
            "totals": {
                "total_debit":  round(total_dr, 2),
                "total_credit": round(total_cr, 2),
            },
            "integrity": {
                "balanced":   balanced,
                "difference": round(total_dr - total_cr, 2),
            },
            "opening_balance_note": (
                "Opening balances are zero — period_snapshots table not yet populated. "
                "Closing = period turnover only."
            ),
            "truncated": truncated,
        }

    @staticmethod
    def to_excel(data: dict, lang: str = "en") -> io.BytesIO:
        import openpyxl
        lang = lang if lang in ("en", "ru", "uk") else "en"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = {"en": "Trial Balance", "ru": "ОСВ", "uk": "ОСВ"}[lang]
        headers = _TB_DISPLAY_HEADERS[lang]
        _xlsx_header_row(ws, headers)
        for r_idx, row in enumerate(data.get("rows", []), 2):
            for c_idx, val in enumerate([
                row["account_code"], row["account_name"],
                row["opening_debit"], row["opening_credit"],
                row["period_debit"], row["period_credit"],
                row["closing_debit"], row["closing_credit"],
            ], 1):
                ws.cell(row=r_idx, column=c_idx, value=val)
        totals = data.get("totals", {})
        last = len(data.get("rows", [])) + 2
        ws.cell(row=last, column=1, value={"en": "TOTAL", "ru": "ИТОГО", "uk": "РАЗОМ"}[lang])
        ws.cell(row=last, column=5, value=totals.get("total_debit"))
        ws.cell(row=last, column=6, value=totals.get("total_credit"))
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    @staticmethod
    def to_pdf(data: dict, lang: str = "en") -> io.BytesIO:
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError as exc:
            raise ImportError(
                "reportlab is required for PDF export. Install with: pip install reportlab"
            ) from exc
        lang = lang if lang in ("en", "ru", "uk") else "en"
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=landscape(A4))
        w, h = landscape(A4)
        title = {"en": "Trial Balance", "ru": "Оборотно-сальдовая ведомость",
                 "uk": "Оборотно-сальдова відомість"}[lang]
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 1.5 * cm,
                            f"{title} — {data.get('period', '')}")
        rows = data.get("rows", [])
        if not rows:
            c.setFont("Helvetica", 10)
            c.drawCentredString(w / 2, h / 2,
                                {"en": "No data", "ru": "Нет данных", "uk": "Немає даних"}[lang])
        else:
            c.setFont("Helvetica", 7)
            y = h - 2.5 * cm
            headers = _TB_DISPLAY_HEADERS[lang]
            col_x = [1.5, 3.5, 8.5, 11.5, 14.5, 17.5, 20.5, 23.5]
            for i, hdr in enumerate(headers):
                c.drawString(col_x[i] * cm, y, hdr[:12])
            y -= 0.5 * cm
            for row in rows[:200]:
                if y < 1.5 * cm:
                    c.showPage()
                    y = h - 2 * cm
                    c.setFont("Helvetica", 7)
                c.drawString(col_x[0] * cm, y, row["account_code"][:8])
                c.drawString(col_x[1] * cm, y, row["account_name"][:14])
                c.drawString(col_x[2] * cm, y, f"{row['period_debit']:.2f}")
                c.drawString(col_x[3] * cm, y, f"{row['period_credit']:.2f}")
                c.drawString(col_x[4] * cm, y, f"{row['closing_debit']:.2f}")
                c.drawString(col_x[5] * cm, y, f"{row['closing_credit']:.2f}")
                y -= 0.45 * cm
        c.save()
        buf.seek(0)
        return buf


# ---------------------------------------------------------------------------
# BalanceSheetReport
# ---------------------------------------------------------------------------

class BalanceSheetReport:
    """Баланс / Balance Sheet."""

    @staticmethod
    def compute(period: str, db_path: Path) -> dict:
        conn = _db_connect(db_path)
        try:
            raw = conn.execute(
                """
                SELECT account,
                       SUM(CASE WHEN entry_type='debit'  THEN CAST(amount AS REAL) ELSE 0 END)
                     - SUM(CASE WHEN entry_type='credit' THEN CAST(amount AS REAL) ELSE 0 END)
                     AS net_balance
                FROM budget_entries
                WHERE period = ?
                GROUP BY account
                ORDER BY account
                LIMIT 10001
                """,
                (period,),
            ).fetchall()
        finally:
            conn.close()

        truncated = len(raw) > 10000
        raw = raw[:10000]

        buckets: dict[str, float] = {
            "current_assets": 0.0, "fixed_assets": 0.0,
            "current_liabilities": 0.0, "long_term_liabilities": 0.0,
            "equity": 0.0, "revenue": 0.0, "cogs": 0.0,
            "operating_expenses": 0.0, "other": 0.0,
        }
        rows = []
        _CREDIT_NORMAL = {"equity", "current_liabilities", "long_term_liabilities",
                          "revenue"}
        for r in raw:
            acct = str(r["account"] or "")
            net = _safe_float(r["net_balance"])
            bucket = _bucket_for(acct)
            # Credit-normal accounts: positive balance when credit > debit (net < 0)
            balance = abs(net) if bucket in _CREDIT_NORMAL else net
            buckets[bucket] = buckets.get(bucket, 0.0) + balance
            rows.append({"account_code": acct, "net_balance": round(net, 2),
                         "bucket": bucket})

        total_assets = round(
            buckets["current_assets"] + buckets["fixed_assets"], 2
        )
        total_liab_equity = round(
            buckets["current_liabilities"] + buckets["long_term_liabilities"]
            + buckets["equity"], 2
        )
        difference = round(total_assets - total_liab_equity, 2)

        return {
            "report":       "balance-sheet",
            "period":       period,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rows":         rows,
            "sections": {k: round(v, 2) for k, v in buckets.items()},
            "totals": {
                "total_assets":             total_assets,
                "total_liabilities_equity": total_liab_equity,
            },
            "balance_check": {
                "difference": difference,
            },
            "opening_balance_note": (
                "Opening balances are zero — period_snapshots table not yet populated."
            ),
            "truncated": truncated,
        }

    @staticmethod
    def to_excel(data: dict, lang: str = "en") -> io.BytesIO:
        import openpyxl
        lang = lang if lang in ("en", "ru", "uk") else "en"
        labels = _BS_SECTION_LABELS[lang]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = {"en": "Balance Sheet", "ru": "Баланс", "uk": "Баланс"}[lang]
        _xlsx_header_row(ws, [
            {"en": "Section", "ru": "Раздел", "uk": "Розділ"}[lang],
            {"en": "Amount", "ru": "Сумма", "uk": "Сума"}[lang],
        ])
        sections = data.get("sections", {})
        r = 2
        for key in ("current_assets", "fixed_assets", "current_liabilities",
                    "long_term_liabilities", "equity"):
            ws.cell(row=r, column=1, value=labels.get(key, key))
            ws.cell(row=r, column=2, value=sections.get(key, 0.0))
            r += 1
        totals = data.get("totals", {})
        ws.cell(row=r, column=1, value=labels["total_assets"])
        ws.cell(row=r, column=2, value=totals.get("total_assets", 0.0))
        r += 1
        ws.cell(row=r, column=1, value=labels["total_liabilities_equity"])
        ws.cell(row=r, column=2, value=totals.get("total_liabilities_equity", 0.0))
        diff = data.get("balance_check", {}).get("difference", 0.0)
        if diff:
            r += 1
            ws.cell(row=r, column=1, value=labels["difference"])
            ws.cell(row=r, column=2, value=diff)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    @staticmethod
    def to_pdf(data: dict, lang: str = "en") -> io.BytesIO:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError as exc:
            raise ImportError(
                "reportlab is required for PDF export. Install with: pip install reportlab"
            ) from exc
        lang = lang if lang in ("en", "ru", "uk") else "en"
        labels = _BS_SECTION_LABELS[lang]
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        title = {"en": "Balance Sheet", "ru": "Бухгалтерский баланс",
                 "uk": "Бухгалтерський баланс"}[lang]
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 1.5 * cm,
                            f"{title} — {data.get('period', '')}")
        c.setFont("Helvetica", 9)
        y = h - 3 * cm
        sections = data.get("sections", {})
        totals = data.get("totals", {})
        for key in ("current_assets", "fixed_assets"):
            c.drawString(2 * cm, y, labels.get(key, key))
            c.drawRightString(w - 2 * cm, y, f"{sections.get(key, 0.0):.2f}")
            y -= 0.7 * cm
        c.drawString(2 * cm, y, labels["total_assets"])
        c.drawRightString(w - 2 * cm, y, f"{totals.get('total_assets', 0.0):.2f}")
        y -= 1.2 * cm
        for key in ("current_liabilities", "long_term_liabilities", "equity"):
            c.drawString(2 * cm, y, labels.get(key, key))
            c.drawRightString(w - 2 * cm, y, f"{sections.get(key, 0.0):.2f}")
            y -= 0.7 * cm
        c.drawString(2 * cm, y, labels["total_liabilities_equity"])
        c.drawRightString(w - 2 * cm, y,
                          f"{totals.get('total_liabilities_equity', 0.0):.2f}")
        diff = data.get("balance_check", {}).get("difference", 0.0)
        if diff:
            y -= 0.7 * cm
            c.setFont("Helvetica-Bold", 9)
            c.drawString(2 * cm, y, labels["difference"])
            c.drawRightString(w - 2 * cm, y, f"{diff:.2f}")
        c.save()
        buf.seek(0)
        return buf


# ---------------------------------------------------------------------------
# IncomeStatement
# ---------------------------------------------------------------------------

class IncomeStatement:
    """Звіт про фінансові результати / P&L / Income Statement."""

    @staticmethod
    def compute(period: str, db_path: Path,
                period_mode: str = "monthly") -> dict:
        """
        period_mode: 'monthly' (default) | 'ytd'
        """
        conn = _db_connect(db_path)
        try:
            if period_mode == "ytd":
                year_prefix = _ytd_prefix(period)
                cutoff_month = _ytd_month(period)
                # Include all months from 01 up to and including the given month
                rows_raw = conn.execute(
                    """
                    SELECT account,
                           SUM(CASE WHEN entry_type='debit'  THEN CAST(amount AS REAL) ELSE 0 END) AS dr,
                           SUM(CASE WHEN entry_type='credit' THEN CAST(amount AS REAL) ELSE 0 END) AS cr
                    FROM budget_entries
                    WHERE period LIKE ? AND substr(period, 6, 2) <= ?
                    GROUP BY account
                    LIMIT 10001
                    """,
                    (year_prefix + "%", cutoff_month),
                ).fetchall()
            else:
                rows_raw = conn.execute(
                    """
                    SELECT account,
                           SUM(CASE WHEN entry_type='debit'  THEN CAST(amount AS REAL) ELSE 0 END) AS dr,
                           SUM(CASE WHEN entry_type='credit' THEN CAST(amount AS REAL) ELSE 0 END) AS cr
                    FROM budget_entries
                    WHERE period = ?
                    GROUP BY account
                    LIMIT 10001
                    """,
                    (period,),
                ).fetchall()

            # Payroll for the period
            if period_mode == "ytd":
                year_prefix = _ytd_prefix(period)
                cutoff_month = _ytd_month(period)
                payroll_raw = conn.execute(
                    """
                    SELECT SUM(CAST(gross AS REAL)) AS total_gross
                    FROM payroll_results
                    WHERE period LIKE ? AND substr(period, 6, 2) <= ?
                    """,
                    (year_prefix + "%", cutoff_month),
                ).fetchone()
            else:
                payroll_raw = conn.execute(
                    "SELECT SUM(CAST(gross AS REAL)) AS total_gross FROM payroll_results WHERE period = ?",
                    (period,),
                ).fetchone()
        finally:
            conn.close()

        truncated = len(rows_raw) > 10000
        rows_raw = rows_raw[:10000]

        revenue = 0.0
        cogs = 0.0
        operating_expenses = 0.0
        other = 0.0

        for r in rows_raw:
            acct = str(r["account"] or "")
            # For P&L: credit-side revenue, debit-side expenses
            net = _safe_float(r["cr"]) - _safe_float(r["dr"])
            bucket = _bucket_for(acct)
            if bucket == "revenue":
                revenue += net
            elif bucket == "cogs":
                cogs += abs(net)
            elif bucket == "operating_expenses":
                operating_expenses += abs(net)
            else:
                other += net

        payroll = _safe_float(
            payroll_raw["total_gross"] if payroll_raw else None
        )

        gross_profit = revenue - cogs
        operating_profit = gross_profit - operating_expenses - payroll
        net_profit = operating_profit + other

        return {
            "report":       "income-statement",
            "period":       period,
            "period_mode":  period_mode,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "revenue":              round(revenue, 2),
            "cogs":                 round(cogs, 2),
            "gross_profit":         round(gross_profit, 2),
            "operating_expenses":   round(operating_expenses, 2),
            "payroll":              round(payroll, 2),
            "operating_profit":     round(operating_profit, 2),
            "other":                round(other, 2),
            "net_profit":           round(net_profit, 2),
            "truncated":            truncated,
        }

    @staticmethod
    def to_excel(data: dict, lang: str = "en") -> io.BytesIO:
        import openpyxl
        lang = lang if lang in ("en", "ru", "uk") else "en"
        labels = _IS_SECTION_LABELS[lang]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = {"en": "Income Statement", "ru": "ОФР", "uk": "ЗФР"}[lang]
        _xlsx_header_row(ws, [
            {"en": "Line", "ru": "Строка", "uk": "Рядок"}[lang],
            {"en": "Amount", "ru": "Сумма", "uk": "Сума"}[lang],
        ])
        rows = [
            (labels["revenue"],            data.get("revenue", 0.0)),
            (labels["cogs"],              -data.get("cogs", 0.0)),
            (labels["gross_profit"],       data.get("gross_profit", 0.0)),
            (labels["operating_expenses"], -data.get("operating_expenses", 0.0)),
            (labels["payroll"],            -data.get("payroll", 0.0)),
            (labels["operating_profit"],   data.get("operating_profit", 0.0)),
            (labels["other"],              data.get("other", 0.0)),
            (labels["net_profit"],         data.get("net_profit", 0.0)),
        ]
        for r_idx, (label, amount) in enumerate(rows, 2):
            ws.cell(row=r_idx, column=1, value=label)
            ws.cell(row=r_idx, column=2, value=amount)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    @staticmethod
    def to_pdf(data: dict, lang: str = "en") -> io.BytesIO:
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import cm
            from reportlab.pdfgen import canvas as rl_canvas
        except ImportError as exc:
            raise ImportError(
                "reportlab is required for PDF export. Install with: pip install reportlab"
            ) from exc
        lang = lang if lang in ("en", "ru", "uk") else "en"
        labels = _IS_SECTION_LABELS[lang]
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        title = {"en": "Income Statement", "ru": "Отчёт о финансовых результатах",
                 "uk": "Звіт про фінансові результати"}[lang]
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(w / 2, h - 1.5 * cm,
                            f"{title} — {data.get('period', '')}")
        c.setFont("Helvetica", 9)
        y = h - 3 * cm
        line_items = [
            (labels["revenue"],             data.get("revenue", 0.0),            False),
            (labels["cogs"],               -data.get("cogs", 0.0),               False),
            (labels["gross_profit"],        data.get("gross_profit", 0.0),        True),
            (labels["operating_expenses"], -data.get("operating_expenses", 0.0),  False),
            (labels["payroll"],            -data.get("payroll", 0.0),             False),
            (labels["operating_profit"],    data.get("operating_profit", 0.0),    True),
            (labels["other"],               data.get("other", 0.0),               False),
            (labels["net_profit"],          data.get("net_profit", 0.0),          True),
        ]
        for label, amount, bold in line_items:
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
            c.drawString(2 * cm, y, label)
            c.drawRightString(w - 2 * cm, y, f"{amount:.2f}")
            y -= 0.7 * cm
        c.save()
        buf.seek(0)
        return buf


# ---------------------------------------------------------------------------
# 1S Reporter binding
# ---------------------------------------------------------------------------

class _ReportResult:
    """Lightweight wrapper so 1S scripts can access report fields as properties."""
    def __init__(self, data: dict) -> None:
        self._data = data

    # Trial Balance
    @property
    def IsBalanced(self) -> bool:
        return self._data.get("integrity", {}).get("balanced", True)

    @property
    def TotalDebit(self) -> float:
        return self._data.get("totals", {}).get("total_debit", 0.0)

    @property
    def TotalCredit(self) -> float:
        return self._data.get("totals", {}).get("total_credit", 0.0)

    # Balance Sheet
    @property
    def TotalAssets(self) -> float:
        return self._data.get("totals", {}).get("total_assets", 0.0)

    @property
    def TotalLiabilities(self) -> float:
        s = self._data.get("sections", {})
        return round(
            s.get("current_liabilities", 0.0) + s.get("long_term_liabilities", 0.0), 2
        )

    @property
    def Equity(self) -> float:
        return self._data.get("sections", {}).get("equity", 0.0)

    # Income Statement
    @property
    def NetProfit(self) -> float:
        return self._data.get("net_profit", 0.0)

    @property
    def Revenue(self) -> float:
        return self._data.get("revenue", 0.0)

    @property
    def GrossProfit(self) -> float:
        return self._data.get("gross_profit", 0.0)

    # Russian aliases
    СбалансировананО = IsBalanced
    ИтогоДт = TotalDebit
    ИтогоКт = TotalCredit
    ИтогоАктивов = TotalAssets
    Обязательства = TotalLiabilities
    СобственныйКапитал = Equity
    ЧистаяПрибыль = NetProfit
    Выручка = Revenue
    ВаловаяПрибыль = GrossProfit

    # Ukrainian aliases
    Збалансовано = IsBalanced
    ПідсумокДт = TotalDebit
    ПідсумокКт = TotalCredit
    ПідсумокАктивів = TotalAssets
    Зобов_язання = TotalLiabilities
    ВласнийКапітал = Equity
    ЧистийПрибуток = NetProfit
    Дохід = Revenue
    ВаловийПрибуток = GrossProfit


class Reporter:
    """
    NewReporter() — access financial reports from 1S scripts.

    Usage (English):
        Reporter = NewReporter()
        TB = Reporter.TrialBalance("2026-07")
        Message("Balanced: " + String(TB.IsBalanced))
        BS = Reporter.BalanceSheet("2026-07")
        Message("Assets: " + String(BS.TotalAssets))
        PL = Reporter.IncomeStatement("2026-07", "ytd")
        Message("Net profit: " + String(PL.NetProfit))
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            # Default: look for erp.db next to the project root
            from pathlib import Path as _Path
            candidate = _Path(__file__).parent.parent.parent / "data" / "erp.db"
            self._db = candidate
        else:
            self._db = Path(db_path)

    def TrialBalance(self, period: str) -> _ReportResult:
        return _ReportResult(TrialBalanceReport.compute(period, self._db))

    def BalanceSheet(self, period: str) -> _ReportResult:
        return _ReportResult(BalanceSheetReport.compute(period, self._db))

    def IncomeStatement(self, period: str,
                        period_mode: str = "monthly") -> _ReportResult:
        return _ReportResult(IncomeStatement.compute(period, self._db, period_mode))

    # Russian aliases
    ОборотноСальдоваяВедомость = TrialBalance
    Баланс                     = BalanceSheet
    ОтчетОПрибылях             = IncomeStatement

    # Ukrainian aliases
    ОборотноСальдоваВідомість  = TrialBalance
    ЗвітПроПрибутки            = IncomeStatement


# Module-level constructor (used by 1S runtime)
def NewReporter(db_path: Optional[Path] = None) -> Reporter:
    return Reporter(db_path)


НовыйОтчетчик  = NewReporter   # Russian
НовийЗвітник   = NewReporter   # Ukrainian
