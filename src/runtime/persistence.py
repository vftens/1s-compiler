"""
1S: ERP Free Edition — SQLite persistence for registers.

Saves and loads AccountingRegister and AccumulationRegister
to/from a SQLite database so data survives server restarts.

Usage:
    from src.runtime.persistence import save_register, load_register

    reg = AccountingRegister("Main", chart)
    reg.Post(...)

    # Save at shutdown
    save_register(reg, "data/accounting.db")

    # Load at startup
    reg2 = AccountingRegister("Main", chart)
    load_register(reg2, "data/accounting.db")
"""
from __future__ import annotations
import sqlite3
import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registers import AccountingRegister, AccumulationRegister


# ── Accounting Register ───────────────────────────────────────────────────────

def save_accounting(reg: "AccountingRegister", db_path: str) -> int:
    """
    Save all entries from an AccountingRegister to SQLite.
    Creates (or appends to) the database at db_path.
    Returns number of entries saved.
    """
    from .registers import AccountingEntry
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounting_entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                register_name TEXT NOT NULL,
                period        TEXT,
                recorder      TEXT,
                recorder_type TEXT,
                account_code  TEXT,
                subconto1     TEXT,
                subconto2     TEXT,
                subconto3     TEXT,
                amount        TEXT,
                amount_currency TEXT,
                currency      TEXT,
                is_debit      INTEGER,
                description   TEXT
            )
        """)
        conn.execute(
            "DELETE FROM accounting_entries WHERE register_name = ?",
            (reg.name,)
        )
        rows = []
        for e in reg._entries:
            rows.append((
                reg.name,
                str(e.period) if e.period else None,
                e.recorder,
                e.recorder_type,
                e.account.code if e.account else None,
                str(e.subconto1) if e.subconto1 else None,
                str(e.subconto2) if e.subconto2 else None,
                str(e.subconto3) if e.subconto3 else None,
                str(e.amount),
                str(e.amount_currency),
                e.currency,
                1 if e.is_debit else 0,
                e.description,
            ))
        conn.executemany("""
            INSERT INTO accounting_entries
            (register_name,period,recorder,recorder_type,account_code,
             subconto1,subconto2,subconto3,amount,amount_currency,
             currency,is_debit,description)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        conn.commit()
    return len(rows)


def load_accounting(reg: "AccountingRegister", db_path: str) -> int:
    """
    Load entries from SQLite into an AccountingRegister.
    Returns number of entries loaded.
    """
    from .registers import AccountingEntry, _PostingPair
    path = Path(db_path)
    if not path.exists():
        return 0

    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM accounting_entries WHERE register_name = ? ORDER BY id",
            (reg.name,)
        ).fetchall()

    reg._entries.clear()
    reg._postings.clear()

    for row in rows:
        period = None
        if row["period"]:
            try:
                period = datetime.date.fromisoformat(row["period"])
            except Exception:
                pass

        account = reg.chart.FindByCode(row["account_code"]) if row["account_code"] else None
        from .types import Undefined
        if account is Undefined:
            account = None

        entry = AccountingEntry(
            period=period,
            recorder=row["recorder"] or "",
            recorder_type=row["recorder_type"] or "",
            account=account,
            subconto1=row["subconto1"],
            subconto2=row["subconto2"],
            subconto3=row["subconto3"],
            amount=Decimal(row["amount"]),
            amount_currency=Decimal(row["amount_currency"]),
            currency=row["currency"] or "",
            is_debit=bool(row["is_debit"]),
            description=row["description"] or "",
        )
        reg._entries.append(entry)

    # Rebuild postings from paired entries
    i = 0
    while i + 1 < len(reg._entries):
        dt = reg._entries[i]
        ct = reg._entries[i + 1]
        if (dt.recorder == ct.recorder and dt.is_debit and not ct.is_debit):
            reg._postings.append(_PostingPair(
                period=dt.period, recorder=dt.recorder,
                description=dt.description,
                debit_account=dt.account, credit_account=ct.account,
                subconto_debit=dt.subconto1, subconto_credit=ct.subconto1,
                amount=dt.amount,
            ))
            i += 2
        else:
            i += 1

    return len(reg._entries)


# ── Accumulation Register ─────────────────────────────────────────────────────

def save_accumulation(reg: "AccumulationRegister", db_path: str) -> int:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accumulation_entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                register_name TEXT NOT NULL,
                period        TEXT,
                recorder      TEXT,
                dimension1    TEXT,
                dimension2    TEXT,
                dimension3    TEXT,
                resource1     TEXT,
                resource2     TEXT,
                is_receipt    INTEGER
            )
        """)
        conn.execute(
            "DELETE FROM accumulation_entries WHERE register_name = ?",
            (reg.name,)
        )
        rows = [
            (reg.name, str(e.period) if e.period else None, e.recorder,
             str(e.dimension1) if e.dimension1 else None,
             str(e.dimension2) if e.dimension2 else None,
             str(e.dimension3) if e.dimension3 else None,
             str(e.resource1), str(e.resource2),
             1 if e.is_receipt else 0)
            for e in reg._entries
        ]
        conn.executemany("""
            INSERT INTO accumulation_entries
            (register_name,period,recorder,dimension1,dimension2,dimension3,
             resource1,resource2,is_receipt)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, rows)
        conn.commit()
    return len(rows)


def load_accumulation(reg: "AccumulationRegister", db_path: str) -> int:
    from .registers import AccumulationEntry
    path = Path(db_path)
    if not path.exists():
        return 0

    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM accumulation_entries WHERE register_name = ? ORDER BY id",
            (reg.name,)
        ).fetchall()

    reg._entries.clear()
    for row in rows:
        period = None
        if row["period"]:
            try: period = datetime.date.fromisoformat(row["period"])
            except Exception: pass
        reg._entries.append(AccumulationEntry(
            period=period, recorder=row["recorder"] or "",
            dimension1=row["dimension1"], dimension2=row["dimension2"],
            dimension3=row["dimension3"],
            resource1=Decimal(row["resource1"]),
            resource2=Decimal(row["resource2"]),
            is_receipt=bool(row["is_receipt"]),
        ))
    return len(reg._entries)


# ── Convenience wrappers ──────────────────────────────────────────────────────

def save_register(reg, db_path: str) -> int:
    """Auto-detect register type and save."""
    from .registers import AccountingRegister, AccumulationRegister
    if isinstance(reg, AccountingRegister):
        return save_accounting(reg, db_path)
    if isinstance(reg, AccumulationRegister):
        return save_accumulation(reg, db_path)
    raise TypeError(f"Unknown register type: {type(reg)}")


def load_register(reg, db_path: str) -> int:
    """Auto-detect register type and load."""
    from .registers import AccountingRegister, AccumulationRegister
    if isinstance(reg, AccountingRegister):
        return load_accounting(reg, db_path)
    if isinstance(reg, AccumulationRegister):
        return load_accumulation(reg, db_path)
    raise TypeError(f"Unknown register type: {type(reg)}")


# ── Russian / Ukrainian aliases (registers) ────────────────────────────────────

СохранитьРегистр  = save_register
ЗагрузитьРегистр  = load_register
ЗберегтиРегістр   = save_register
ЗавантажитиРегістр = load_register


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 11 — Persistence for Sprint 10 ERP modules
# ═══════════════════════════════════════════════════════════════════════════════

import json as _json


# ── OrgChart ──────────────────────────────────────────────────────────────────

def save_org_chart(org, db_path: str) -> int:
    """Save OrgChart nodes to SQLite. Returns node count saved (excluding root)."""
    org_name = org._root.name
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS org_nodes (
                id        TEXT NOT NULL,
                name      TEXT NOT NULL,
                type      TEXT NOT NULL,
                parent_id TEXT,
                org_name  TEXT NOT NULL
            )
        """)
        conn.execute("DELETE FROM org_nodes WHERE org_name = ?", (org_name,))
        rows = []
        for node in org._nodes.values():
            if node.id == "root":
                continue  # root is recreated automatically on load
            parent_id = node.parent.id if node.parent else "root"
            rows.append((
                node.id, node.name,
                node.org_type.value if hasattr(node.org_type, "value") else str(node.org_type),
                parent_id, org_name,
            ))
        conn.executemany(
            "INSERT INTO org_nodes (id, name, type, parent_id, org_name) VALUES (?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def load_org_chart(db_path: str, org_name: str):
    """Load OrgChart from SQLite. Returns a new OrgChart instance."""
    from .org import OrgChart
    path = Path(db_path)
    if not path.exists():
        return OrgChart(org_name)

    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM org_nodes WHERE org_name = ? ORDER BY rowid",
            (org_name,),
        ).fetchall()

    org = OrgChart(org_name)
    # Two-pass: nodes whose parent already exists first, then children
    remaining = list(rows)
    max_passes = len(remaining) + 1
    passes = 0
    while remaining and passes < max_passes:
        passes += 1
        still_pending = []
        for row in remaining:
            parent_id = row["parent_id"] or "root"
            if parent_id in org._nodes:
                org.add_node(row["id"], row["name"], row["type"], parent_id)
            else:
                still_pending.append(row)
        remaining = still_pending
    return org


# ── BudgetControl ─────────────────────────────────────────────────────────────

def save_budget(budget, db_path: str) -> int:
    """Save BudgetControl allocations and entries to SQLite."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budget_allocations (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id   TEXT NOT NULL,
                period   TEXT NOT NULL,
                account  TEXT NOT NULL,
                amount   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budget_entries (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_type   TEXT NOT NULL,
                org_id       TEXT NOT NULL,
                period       TEXT NOT NULL,
                amount       TEXT NOT NULL,
                doc_ref      TEXT,
                account      TEXT
            )
        """)
        conn.execute("DELETE FROM budget_allocations")
        conn.execute("DELETE FROM budget_entries")

        # _allocations is Dict[Tuple[org_id, period, account], Decimal]
        alloc_rows = [
            (org_id, period, account, str(amount))
            for (org_id, period, account), amount in budget._allocations.items()
        ]
        conn.executemany(
            "INSERT INTO budget_allocations (org_id, period, account, amount) VALUES (?,?,?,?)",
            alloc_rows,
        )
        # BudgetEntry has: entry_type, org_id, period, account, amount, doc_ref
        entry_rows = [
            (e.entry_type, e.org_id, e.period, str(e.amount), e.doc_ref, e.account)
            for e in budget._entries
        ]
        conn.executemany(
            "INSERT INTO budget_entries (entry_type, org_id, period, amount, doc_ref, account) VALUES (?,?,?,?,?,?)",
            entry_rows,
        )
        conn.commit()
    return len(alloc_rows) + len(entry_rows)


def load_budget(db_path: str, hard_stop: bool = True, warn_threshold: float = 0.9):
    """Load BudgetControl from SQLite. Returns a new BudgetControl instance."""
    from .budget import BudgetControl, BudgetEntry
    path = Path(db_path)
    budget = BudgetControl(hard_stop=hard_stop, warn_threshold=warn_threshold)
    if not path.exists():
        return budget

    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        allocs = conn.execute("SELECT * FROM budget_allocations ORDER BY id").fetchall()
        entries = conn.execute("SELECT * FROM budget_entries ORDER BY id").fetchall()

    # _allocations is Dict[Tuple[org_id, period, account], Decimal]
    for row in allocs:
        budget._allocations[(row["org_id"], row["period"], row["account"])] = Decimal(row["amount"])
    for row in entries:
        budget._entries.append(BudgetEntry(
            entry_type=row["entry_type"], org_id=row["org_id"],
            period=row["period"], amount=Decimal(row["amount"]),
            doc_ref=row["doc_ref"] or "", account=row["account"] or "",
        ))
    return budget


# ── PayrollEngine results ─────────────────────────────────────────────────────

def save_payroll_results(results: list, db_path: str) -> int:
    """Save PayrollResult list to SQLite."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payroll_results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                period      TEXT NOT NULL,
                emp_id      TEXT NOT NULL,
                emp_name    TEXT NOT NULL,
                gross       TEXT NOT NULL,
                net         TEXT NOT NULL,
                tax_profile TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payroll_lines (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id   INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount      TEXT NOT NULL,
                line_type   TEXT NOT NULL
            )
        """)
        if results:
            period = results[0].period
            conn.execute("DELETE FROM payroll_results WHERE period = ?", (period,))
            conn.execute(
                "DELETE FROM payroll_lines WHERE result_id IN "
                "(SELECT id FROM payroll_results WHERE period = ?)", (period,)
            )

        saved = 0
        for res in results:
            cur = conn.execute(
                "INSERT INTO payroll_results (period, emp_id, emp_name, gross, net, tax_profile) "
                "VALUES (?,?,?,?,?,?)",
                (res.period, res.employee.id, res.employee.name,
                 str(res.gross), str(res.net), res.employee.tax_profile),
            )
            rid = cur.lastrowid
            # Save tax deduction lines from tax_result
            line_rows = []
            if res.tax_result and res.tax_result.lines:
                for ln in res.tax_result.lines:
                    line_rows.append((rid, ln.name, str(ln.amount), "deduction"))
            if line_rows:
                conn.executemany(
                    "INSERT INTO payroll_lines (result_id, description, amount, line_type) VALUES (?,?,?,?)",
                    line_rows,
                )
            saved += 1
        conn.commit()
    return saved


def load_payroll_results(db_path: str, period: str | None = None) -> list:
    """Load PayrollResult records from SQLite. Returns list of dicts (not full objects)."""
    path = Path(db_path)
    if not path.exists():
        return []

    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        if period:
            rows = conn.execute(
                "SELECT * FROM payroll_results WHERE period = ? ORDER BY id",
                (period,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM payroll_results ORDER BY id").fetchall()

        records = []
        for row in rows:
            lines = conn.execute(
                "SELECT * FROM payroll_lines WHERE result_id = ? ORDER BY id",
                (row["id"],),
            ).fetchall()
            records.append({
                "period": row["period"],
                "emp_id": row["emp_id"],
                "emp_name": row["emp_name"],
                "gross": Decimal(row["gross"]),
                "net": Decimal(row["net"]),
                "tax_profile": row["tax_profile"],
                "lines": [
                    {"description": ln["description"], "amount": Decimal(ln["amount"]),
                     "line_type": ln["line_type"]}
                    for ln in lines
                ],
            })
    return records


# ── WorkflowConfig ────────────────────────────────────────────────────────────

def ensure_period_snapshots_table(db_path: str) -> None:
    """Create period_snapshots table if not exists (Sprint 15 — opening balance support)."""
    path = Path(db_path)
    if not path.exists():
        return
    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS period_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                period      TEXT NOT NULL,
                account     TEXT NOT NULL,
                debit       TEXT NOT NULL DEFAULT '0',
                credit      TEXT NOT NULL DEFAULT '0',
                UNIQUE(period, account)
            )
        """)
        conn.commit()


def save_workflow_config(cfg, db_path: str) -> int:
    """Save WorkflowConfig rules to SQLite as JSON blobs per doc_type."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(path)) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_rules (
                doc_type TEXT PRIMARY KEY,
                rules_json TEXT NOT NULL
            )
        """)
        conn.execute("DELETE FROM workflow_rules")
        rows = []
        for doc_type, rule_list in cfg._rules.items():
            serialized = [
                {"condition": r.condition, "approvers": r.approvers}
                for r in rule_list
            ]
            rows.append((doc_type, _json.dumps(serialized, ensure_ascii=False)))
        conn.executemany(
            "INSERT INTO workflow_rules (doc_type, rules_json) VALUES (?,?)", rows
        )
        conn.commit()
    return len(rows)


def load_workflow_config(db_path: str):
    """Load WorkflowConfig from SQLite. Returns a WorkflowConfig instance."""
    from .workflow_config import WorkflowConfig, WFRule
    path = Path(db_path)
    cfg = WorkflowConfig()
    if not path.exists():
        return cfg

    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM workflow_rules").fetchall()

    for row in rows:
        rule_list = []
        for r in _json.loads(row["rules_json"]):
            rule_list.append(WFRule(condition=r["condition"], approvers=r["approvers"]))
        cfg._rules[row["doc_type"]] = rule_list
    return cfg


# ── Sprint 11 Russian / Ukrainian aliases ─────────────────────────────────────

# OrgChart
СохранитьОргСтруктуру   = save_org_chart
ЗагрузитьОргСтруктуру   = load_org_chart
ЗберегтиОргСтруктуру    = save_org_chart
ЗавантажитиОргСтруктуру = load_org_chart

# BudgetControl
СохранитьБюджет   = save_budget
ЗагрузитьБюджет   = load_budget
ЗберегтиБюджет    = save_budget
ЗавантажитиБюджет = load_budget

# Payroll
СохранитьРасчетыЗП   = save_payroll_results
ЗагрузитьРасчетыЗП   = load_payroll_results
ЗберегтиРозрахункиЗП  = save_payroll_results
ЗавантажитиРозрахункиЗП = load_payroll_results

# WorkflowConfig
СохранитьМаршрут   = save_workflow_config
ЗагрузитьМаршрут   = load_workflow_config
ЗберегтиМаршрут    = save_workflow_config
ЗавантажитиМаршрут = load_workflow_config
