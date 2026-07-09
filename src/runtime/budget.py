"""
BudgetControl — commitment accounting: allocate → commit (PO) → consume (GR) → release.
Budget is in-memory this sprint; attach OrgNode ids to budget periods.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple


@dataclass
class BudgetAllocation:
    org_id:   str
    period:   str    # "2024-Q1", "2024-01", "2024"
    account:  str
    amount:   Decimal

    def __repr__(self) -> str:
        return f"BudgetAllocation({self.org_id}/{self.period}/{self.account}: {self.amount})"


@dataclass
class BudgetEntry:
    entry_type: str    # 'commitment' | 'consumption' | 'release'
    org_id:     str
    period:     str
    account:    str
    amount:     Decimal
    doc_ref:    str
    timestamp:  datetime.datetime = field(default_factory=datetime.datetime.now)

    def __repr__(self) -> str:
        return f"BudgetEntry({self.entry_type}, {self.org_id}, {self.amount}, ref={self.doc_ref!r})"


@dataclass
class BudgetBalance:
    org_id:      str
    period:      str
    account:     str
    allocated:   Decimal
    committed:   Decimal
    consumed:    Decimal
    released:    Decimal

    @property
    def available(self) -> Decimal:
        return self.allocated - self.committed - self.consumed + self.released

    @property
    def utilization_pct(self) -> float:
        if self.allocated == 0:
            return 0.0
        return float((self.committed + self.consumed) / self.allocated * 100)

    def __repr__(self) -> str:
        return (f"BudgetBalance({self.org_id}/{self.period}/{self.account}: "
                f"allocated={self.allocated}, available={self.available}, "
                f"util={self.utilization_pct:.1f}%)")

    # Aliases EN
    @property
    def Available(self): return self.available
    @property
    def Allocated(self): return self.allocated
    @property
    def Committed(self): return self.committed

    # Aliases RU
    @property
    def Доступно(self):   return self.available
    @property
    def Выделено(self):   return self.allocated
    @property
    def Зарезервировано(self): return self.committed

    # Aliases UK
    @property
    def Доступно_uk(self): return self.available
    @property
    def Виділено(self):    return self.allocated
    @property
    def Зарезервовано(self): return self.committed


_BudgetKey = Tuple[str, str, str]   # (org_id, period, account)


class BudgetControl:
    """
    Commitment accounting ledger.

    Flow:
      allocate()  — set the budget limit
      commit()    — reserve on PO submit (commitment)
      consume()   — finalize on GR post (commitment → consumption)
      release()   — free reservation on PO rejection
    """

    def __init__(self, hard_stop: bool = True, warn_threshold: float = 0.9):
        """
        hard_stop: block PO when budget is overrun (True = SAP behavior).
        warn_threshold: warn when consumed+committed exceeds this fraction of budget.
        """
        self._hard_stop      = hard_stop
        self._warn_threshold = Decimal(str(warn_threshold))
        self._allocations:   Dict[_BudgetKey, Decimal]       = {}
        self._entries:       List[BudgetEntry]                = []

    # ── allocation ────────────────────────────────────────────────────────────
    def allocate(self, org_id: str, period: str, account: str, amount: Decimal | float | int) -> None:
        key = (org_id, period, account)
        self._allocations[key] = Decimal(str(amount))

    # ── commitment (PO submit) ────────────────────────────────────────────────
    def commit(self, org_id: str, period: str, amount: Decimal | float | int,
               doc_ref: str, account: str = "default") -> bool:
        amount = Decimal(str(amount))
        bal = self._balance_raw(org_id, period, account)
        allocated = bal["allocated"]
        net_used  = bal["committed"] + bal["consumed"] - bal["released"]
        available = allocated - net_used

        if allocated > 0 and amount > available:
            if self._hard_stop:
                print(f"[BudgetControl] BLOCKED: {doc_ref} — overrun "
                      f"{org_id}/{period}/{account}: need {amount}, available {available}")
                return False
            else:
                print(f"[BudgetControl] WARNING: {doc_ref} — budget soft overrun "
                      f"{org_id}/{period}/{account}: need {amount}, available {available}")
        elif allocated > 0 and (net_used + amount) / allocated >= self._warn_threshold:
            print(f"[BudgetControl] WARNING: {org_id}/{period}/{account} at "
                  f"{float((net_used+amount)/allocated*100):.1f}% budget utilization")

        self._entries.append(BudgetEntry(
            entry_type="commitment", org_id=org_id, period=period,
            account=account, amount=amount, doc_ref=doc_ref,
        ))
        return True

    # ── consumption (GR post) ─────────────────────────────────────────────────
    def consume(self, org_id: str, period: str, amount: Decimal | float | int,
                doc_ref: str, account: str = "default") -> bool:
        self._entries.append(BudgetEntry(
            entry_type="consumption", org_id=org_id, period=period,
            account=account, amount=Decimal(str(amount)), doc_ref=doc_ref,
        ))
        return True

    # ── release (PO rejection) ────────────────────────────────────────────────
    def release(self, org_id: str, period: str, amount: Decimal | float | int,
                doc_ref: str, account: str = "default") -> None:
        self._entries.append(BudgetEntry(
            entry_type="release", org_id=org_id, period=period,
            account=account, amount=Decimal(str(amount)), doc_ref=doc_ref,
        ))

    # ── query ─────────────────────────────────────────────────────────────────
    def _balance_raw(self, org_id: str, period: str, account: str) -> dict:
        key = (org_id, period, account)
        allocated  = self._allocations.get(key, Decimal("0"))
        committed  = Decimal("0")
        consumed   = Decimal("0")
        released   = Decimal("0")
        for e in self._entries:
            if e.org_id == org_id and e.period == period and e.account == account:
                if e.entry_type == "commitment":
                    committed += e.amount
                elif e.entry_type == "consumption":
                    consumed += e.amount
                elif e.entry_type == "release":
                    released += e.amount
        return dict(allocated=allocated, committed=committed,
                    consumed=consumed, released=released)

    def balance(self, org_id: str, period: str, account: str = "default") -> BudgetBalance:
        raw = self._balance_raw(org_id, period, account)
        return BudgetBalance(
            org_id=org_id, period=period, account=account, **raw
        )

    def report(self, org_id: Optional[str] = None) -> str:
        keys = set()
        for e in self._entries:
            keys.add((e.org_id, e.period, e.account))
        for k in self._allocations:
            keys.add(k)
        if org_id:
            keys = {k for k in keys if k[0] == org_id}

        lines = ["Budget Control Report", "=" * 50]
        for oid, period, acc in sorted(keys):
            b = self.balance(oid, period, acc)
            lines.append(
                f"  {oid}/{period}/{acc}: "
                f"allocated={b.allocated}, committed={b.committed}, "
                f"consumed={b.consumed}, available={b.available}, "
                f"util={b.utilization_pct:.1f}%"
            )
        return "\n".join(lines)

    def entries(self, org_id: Optional[str] = None) -> List[BudgetEntry]:
        if org_id:
            return [e for e in self._entries if e.org_id == org_id]
        return list(self._entries)

    # ── English method aliases ───────────────────────────────────────────────
    Allocate = allocate
    Commit   = commit
    Consume  = consume
    Release  = release
    Balance  = balance
    Report   = report
    Entries  = entries

    # ── Russian method aliases ───────────────────────────────────────────────
    def Выделить(self, org, period, account, amount): return self.allocate(org, period, account, amount)
    def Зарезервировать(self, org, period, amount, ref, account="default"):
        return self.commit(org, period, amount, ref, account)
    def Потребить(self, org, period, amount, ref, account="default"):
        return self.consume(org, period, amount, ref, account)
    def Освободить(self, org, period, amount, ref, account="default"):
        return self.release(org, period, amount, ref, account)
    def Баланс(self, org, period, account="default"): return self.balance(org, period, account)
    def Отчет(self, org=None):  return self.report(org)
    def Проводки(self, org=None): return self.entries(org)

    # ── Ukrainian method aliases ─────────────────────────────────────────────
    def Виділити(self, org, period, account, amount): return self.allocate(org, period, account, amount)
    def Зарезервувати(self, org, period, amount, ref, account="default"):
        return self.commit(org, period, amount, ref, account)
    def Спожити(self, org, period, amount, ref, account="default"):
        return self.consume(org, period, amount, ref, account)
    def Звільнити(self, org, period, amount, ref, account="default"):
        return self.release(org, period, amount, ref, account)
    def Залишок(self, org, period, account="default"): return self.balance(org, period, account)
    def Звіт(self, org=None):   return self.report(org)
    def Проведення(self, org=None): return self.entries(org)

    def __repr__(self) -> str:
        return (f"BudgetControl(hard_stop={self._hard_stop}, "
                f"allocations={len(self._allocations)}, entries={len(self._entries)})")


# ── Trilingual class aliases ─────────────────────────────────────────────────
КонтрольБюджета     = BudgetControl
КонтрольБюджету     = BudgetControl
БаланcБюджета       = BudgetBalance
ВыделениеБюджета    = BudgetAllocation
ПроводкаБюджета     = BudgetEntry
