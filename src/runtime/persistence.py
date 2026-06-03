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


# ── Russian / Ukrainian aliases ───────────────────────────────────────────────

СохранитьРегистр  = save_register
ЗагрузитьРегистр  = load_register
ЗберегтиРегістр   = save_register
ЗавантажитиРегістр = load_register
