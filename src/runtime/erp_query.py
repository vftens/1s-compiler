"""
1S: ERP Free Edition — Cross-document ERP query layer (Sprint 11).

Provides SQL-based aggregation queries across persistence tables so
accountants can answer "where did the money go" without writing SQL.

Usage:
    from src.runtime.erp_query import ERPQuery

    q = ERPQuery("data/erp.db")
    rows = q.po_spend_by_supplier(period="2024-01")
    report = q.budget_utilization(org_id="cc1", period="2024-Q1")
    history = q.payroll_history(period="2024-01")
    summary = q.summary_report(period="2024-01")
"""
from __future__ import annotations
import sqlite3
from decimal import Decimal
from pathlib import Path


_LABELS = {
    "po_spend_by_supplier": {
        "en": "PO Spend by Supplier",
        "ru": "Расходы по поставщикам",
        "uk": "Витрати за постачальниками",
    },
    "budget_utilization": {
        "en": "Budget Utilization",
        "ru": "Исполнение бюджета",
        "uk": "Виконання бюджету",
    },
    "payroll_history": {
        "en": "Payroll History",
        "ru": "История расчётов зарплаты",
        "uk": "Історія розрахунків зарплати",
    },
    "summary": {
        "en": "ERP Summary Report",
        "ru": "Сводный отчёт ERP",
        "uk": "Зведений звіт ERP",
    },
    "no_data": {
        "en": "No data",
        "ru": "Нет данных",
        "uk": "Немає даних",
    },
}


def _label(key: str, lang: str) -> str:
    return _LABELS.get(key, {}).get(lang, _LABELS[key]["en"])


class ERPQuery:
    """Cross-document ERP query engine backed by SQLite persistence."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self):
        path = Path(self.db_path)
        if not path.exists():
            raise FileNotFoundError(f"ERP database not found: {self.db_path}")
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        return conn

    def po_spend_by_supplier(self, period: str | None = None, lang: str = "en") -> list[dict]:
        """
        Aggregate PO commitment entries by doc_number prefix (supplier proxy).
        Returns list of {doc_number, total_committed, total_consumed, period}.
        """
        try:
            with self._connect() as conn:
                if period:
                    rows = conn.execute("""
                        SELECT doc_ref,
                               SUM(CASE WHEN entry_type='commitment'  THEN CAST(amount AS REAL) ELSE 0 END) AS committed,
                               SUM(CASE WHEN entry_type='consumption' THEN CAST(amount AS REAL) ELSE 0 END) AS consumed,
                               period
                        FROM budget_entries
                        WHERE period = ?
                        GROUP BY doc_ref, period
                        ORDER BY committed DESC
                    """, (period,)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT doc_ref,
                               SUM(CASE WHEN entry_type='commitment'  THEN CAST(amount AS REAL) ELSE 0 END) AS committed,
                               SUM(CASE WHEN entry_type='consumption' THEN CAST(amount AS REAL) ELSE 0 END) AS consumed,
                               period
                        FROM budget_entries
                        GROUP BY doc_ref, period
                        ORDER BY period, committed DESC
                    """).fetchall()
        except (sqlite3.OperationalError, FileNotFoundError):
            return []

        return [
            {
                "doc_number": row["doc_ref"] or "—",
                "committed": Decimal(str(round(row["committed"], 2))),
                "consumed": Decimal(str(round(row["consumed"], 2))),
                "period": row["period"],
            }
            for row in rows
        ]

    def budget_utilization(
        self,
        org_id: str | None = None,
        period: str | None = None,
    ) -> list[dict]:
        """
        Return budget utilization per (org_id, period, account).
        Each row: {org_id, period, account, allocated, committed, consumed, utilization_pct}.
        """
        try:
            with self._connect() as conn:
                alloc_params: list = []
                entry_params: list = []
                where_alloc = ""
                where_entry = ""
                if org_id:
                    where_alloc += " AND org_id = ?"
                    where_entry += " AND org_id = ?"
                    alloc_params.append(org_id)
                    entry_params.append(org_id)
                if period:
                    where_alloc += " AND period = ?"
                    where_entry += " AND period = ?"
                    alloc_params.append(period)
                    entry_params.append(period)

                alloc_sql = f"""
                    SELECT org_id, period, account, SUM(CAST(amount AS REAL)) AS allocated
                    FROM budget_allocations WHERE 1=1 {where_alloc}
                    GROUP BY org_id, period, account
                """
                allocs = {
                    (r["org_id"], r["period"], r["account"]): Decimal(str(r["allocated"]))
                    for r in conn.execute(alloc_sql, alloc_params).fetchall()
                }

                entry_sql = f"""
                    SELECT org_id, period, account,
                        SUM(CASE WHEN entry_type='commitment'  THEN CAST(amount AS REAL) ELSE 0 END) AS committed,
                        SUM(CASE WHEN entry_type='consumption' THEN CAST(amount AS REAL) ELSE 0 END) AS consumed
                    FROM budget_entries WHERE 1=1 {where_entry}
                    GROUP BY org_id, period, account
                """
                entries = conn.execute(entry_sql, entry_params).fetchall()
        except (sqlite3.OperationalError, FileNotFoundError):
            return []

        result = []
        for row in entries:
            key = (row["org_id"], row["period"], row["account"])
            allocated = allocs.get(key, Decimal("0"))
            committed = Decimal(str(round(row["committed"], 2)))
            consumed = Decimal(str(round(row["consumed"], 2)))
            used = committed + consumed
            util_pct = float(used / allocated * 100) if allocated else 0.0
            result.append({
                "org_id": row["org_id"],
                "period": row["period"],
                "account": row["account"],
                "allocated": allocated,
                "committed": committed,
                "consumed": consumed,
                "utilization_pct": round(util_pct, 1),
            })
        return result

    def payroll_history(
        self,
        emp_id: str | None = None,
        period: str | None = None,
    ) -> list[dict]:
        """
        Return payroll results from DB.
        Each row: {period, emp_id, emp_name, gross, net, tax_profile}.
        """
        try:
            with self._connect() as conn:
                params = []
                where = ""
                if emp_id:
                    where += " AND emp_id = ?"
                    params.append(emp_id)
                if period:
                    where += " AND period = ?"
                    params.append(period)
                rows = conn.execute(
                    f"SELECT * FROM payroll_results WHERE 1=1 {where} ORDER BY period, emp_name",
                    params,
                ).fetchall()
        except (sqlite3.OperationalError, FileNotFoundError):
            return []

        return [
            {
                "period": row["period"],
                "emp_id": row["emp_id"],
                "emp_name": row["emp_name"],
                "gross": Decimal(row["gross"]),
                "net": Decimal(row["net"]),
                "tax_profile": row["tax_profile"],
            }
            for row in rows
        ]

    def summary_report(self, period: str | None = None, lang: str = "en") -> dict:
        """
        Cross-module summary: total budget allocated/consumed, total payroll gross/net.
        Returns a dict with keys: budget_allocated, budget_consumed, payroll_gross,
        payroll_net, employee_count, period.
        """
        budget_rows = self.budget_utilization(period=period)
        payroll_rows = self.payroll_history(period=period)

        budget_allocated = sum(r["allocated"] for r in budget_rows)
        budget_consumed = sum(r["consumed"] for r in budget_rows)
        payroll_gross = sum(r["gross"] for r in payroll_rows)
        payroll_net = sum(r["net"] for r in payroll_rows)
        emp_count = len({r["emp_id"] for r in payroll_rows})

        return {
            "period": period or "all",
            "budget_allocated": budget_allocated,
            "budget_consumed": budget_consumed,
            "budget_utilization_pct": round(
                float(budget_consumed / budget_allocated * 100) if budget_allocated else 0.0, 1
            ),
            "payroll_gross": payroll_gross,
            "payroll_net": payroll_net,
            "employee_count": emp_count,
        }

    def format_report(self, report_type: str, rows: list[dict], lang: str = "en") -> str:
        """Format a query result as a human-readable text table."""
        if not rows:
            return f"{_label(report_type, lang)}: {_label('no_data', lang)}"

        lines = [f"── {_label(report_type, lang)} ──"]
        if report_type == "po_spend_by_supplier":
            labels = {
                "en": ("Document", "Committed", "Consumed", "Period"),
                "ru": ("Документ", "Зарезервировано", "Потреблено", "Период"),
                "uk": ("Документ", "Зарезервовано", "Спожито", "Період"),
            }.get(lang, ("Document", "Committed", "Consumed", "Period"))
            lines.append(f"  {labels[0]:<20} {labels[1]:>14} {labels[2]:>12} {labels[3]}")
            for r in rows:
                lines.append(f"  {r['doc_number']:<20} {r['committed']:>14,.2f} {r['consumed']:>12,.2f}  {r['period']}")

        elif report_type == "budget_utilization":
            labels = {
                "en": ("OrgID", "Account", "Allocated", "Committed", "Consumed", "Util%"),
                "ru": ("Орг", "Счёт", "Выделено", "Зарезерв.", "Потреблено", "Испол%"),
                "uk": ("Орг", "Рахунок", "Виділено", "Зарезерв.", "Спожито", "Вик%"),
            }.get(lang, ("OrgID", "Account", "Allocated", "Committed", "Consumed", "Util%"))
            lines.append(f"  {labels[0]:<8} {labels[1]:<12} {labels[2]:>12} {labels[3]:>12} {labels[4]:>12}  {labels[5]}")
            for r in rows:
                lines.append(
                    f"  {r['org_id']:<8} {r['account']:<12} "
                    f"{r['allocated']:>12,.2f} {r['committed']:>12,.2f} "
                    f"{r['consumed']:>12,.2f}  {r['utilization_pct']:>5.1f}%"
                )

        elif report_type == "payroll_history":
            labels = {
                "en": ("ID", "Name", "Gross", "Net", "Tax", "Period"),
                "ru": ("ИД", "Имя", "Начисл.", "На руки", "Профиль", "Период"),
                "uk": ("ІД", "Ім'я", "Нарахов.", "На руки", "Профіль", "Період"),
            }.get(lang, ("ID", "Name", "Gross", "Net", "Tax", "Period"))
            lines.append(f"  {labels[0]:<6} {labels[1]:<22} {labels[2]:>10} {labels[3]:>10}  {labels[4]:<10} {labels[5]}")
            for r in rows:
                lines.append(
                    f"  {r['emp_id']:<6} {r['emp_name']:<22} "
                    f"{r['gross']:>10,.2f} {r['net']:>10,.2f}  "
                    f"{r['tax_profile']:<10} {r['period']}"
                )
        return "\n".join(lines)

    # ── Method aliases (RU) ────────────────────────────────────────────────────
    РасходыПоПоставщикам = po_spend_by_supplier
    ИсполнениеБюджета    = budget_utilization
    ИсторияЗарплат       = payroll_history
    СводныйОтчет         = summary_report
    ФорматОтчета         = format_report

    # ── Method aliases (UK) ────────────────────────────────────────────────────
    ВитратиЗаПостачальниками = po_spend_by_supplier
    ВиконанняБюджету         = budget_utilization
    ІсторіяЗарплат           = payroll_history
    ЗведенийЗвіт             = summary_report
    ФорматЗвіту              = format_report


# ── Module-level aliases ───────────────────────────────────────────────────────

ЗапросERPe      = ERPQuery   # RU
ЗапитERPe       = ERPQuery   # UK
ERPЗапрос       = ERPQuery   # RU alt
