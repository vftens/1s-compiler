"""
1S: ERP Free Edition — Accounting register model
Implements the classic 1C double-entry accounting register pattern.
"""
from __future__ import annotations
import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Any, Optional
from .types import _Undefined, Undefined, _Array, _ValueTable


# ── Chart of Accounts (Plan of Accounts) ────────────────────────────────────

@dataclass
class Account:
    """
    Счёт / Account — a node in the chart of accounts.
    Supports sub-accounts (субконто / subconto).
    """
    code: str
    name: str
    parent: Optional["Account"] = None
    active: bool = True      # активный счёт
    passive: bool = False    # пассивный счёт (both = active-passive)
    subconto_kinds: list[str] = field(default_factory=list)  # types of subconto (up to 3)
    children: list["Account"] = field(default_factory=list)
    is_group: bool = False

    def __repr__(self): return f"Account({self.code}, {self.name!r})"
    def __hash__(self): return hash(self.code)
    def __eq__(self, other): return isinstance(other, Account) and self.code == other.code

    # Russian aliases
    @property
    def Код(self): return self.code
    @property
    def Наименование(self): return self.name


class ChartOfAccounts:
    """
    ПланСчетов / ChartOfAccounts.
    A simple in-memory implementation.
    """
    def __init__(self, name: str = "Main"):
        self.name = name
        self._accounts: dict[str, Account] = {}

    def AddAccount(self, code: str, name: str, parent_code: str = "",
                   active: bool = True, passive: bool = False,
                   subconto_kinds: list[str] | None = None) -> Account:
        parent = self._accounts.get(parent_code)
        acc = Account(
            code=code, name=name, parent=parent,
            active=active, passive=passive,
            subconto_kinds=subconto_kinds or [],
        )
        self._accounts[code] = acc
        if parent:
            parent.children.append(acc)
        return acc

    def Додати(self, code: str, name: str, active: bool = True,
               passive: bool = False, subconto: str = "") -> Account:
        """Ukrainian API: Додати(code, name, active, passive, subconto='')."""
        return self.AddAccount(code, name, active=active, passive=passive,
                               subconto_kinds=[subconto] if subconto else [])

    def FindByCode(self, code: str) -> Account | _Undefined:
        return self._accounts.get(code, Undefined)

    def Назва(self) -> str:
        return self.name

    def Select(self) -> "_ChartOfAccountsSelection":
        return _ChartOfAccountsSelection(list(self._accounts.values()))

    def __getitem__(self, code: str) -> Account:
        return self._accounts[code]

    def __iter__(self): return iter(self._accounts.values())

    # Russian aliases
    ДобавитьСчёт = AddAccount
    НайтиПоКоду  = FindByCode
    # Ukrainian aliases
    НайтиЗаКодом = FindByCode
    Вибрати       = Select

ПланСчетов = ChartOfAccounts


class _ChartOfAccountsSelection:
    """Iterator over Chart of Accounts entries."""
    def __init__(self, accounts: list):
        self._accounts = accounts
        self._pos = -1

    def Next(self) -> bool:
        self._pos += 1
        return self._pos < len(self._accounts)

    def Current(self) -> Account | None:
        if 0 <= self._pos < len(self._accounts):
            return self._accounts[self._pos]
        return None

    Следующий = Next
    Текущий   = Current
    Наступний = Next
    Поточний  = Current


# ── Accounting register entry ────────────────────────────────────────────────

@dataclass
class AccountingEntry:
    """
    ЗаписьРегистраБухгалтерии — a single debit/credit posting.
    """
    period: datetime.datetime
    recorder: str                   # document ref that created this
    recorder_type: str = ""
    account: Optional[Account] = None
    subconto1: Any = None           # first dimension value
    subconto2: Any = None
    subconto3: Any = None
    amount: Decimal = Decimal(0)
    amount_currency: Decimal = Decimal(0)
    currency: str = ""
    is_debit: bool = True           # True = debit, False = credit
    description: str = ""           # human-readable transaction description

    @property
    def Период(self): return self.period
    @property
    def Регистратор(self): return self.recorder
    @property
    def Счёт(self): return self.account
    @property
    def Сумма(self): return self.amount
    @property
    def СуммаВалюта(self): return self.amount_currency
    @property
    def ВидДвижения(self): return "Дебет" if self.is_debit else "Кредит"


# ── Accounting Register ──────────────────────────────────────────────────────

@dataclass
class _PostingPair:
    """A paired debit+credit entry for pair-based iteration."""
    period: datetime.datetime
    recorder: str
    description: str
    debit_account: Optional[Account]
    credit_account: Optional[Account]
    subconto_debit: Any
    subconto_credit: Any
    amount: Decimal

    @property
    def AccountDt(self) -> str:
        return self.debit_account.code if self.debit_account else ""
    @property
    def AccountKt(self) -> str:
        return self.credit_account.code if self.credit_account else ""
    @property
    def SubcontoDt(self): return self.subconto_debit
    @property
    def SubcontoKt(self): return self.subconto_credit
    @property
    def Amount(self): return self.amount
    @property
    def Period(self): return self.period
    @property
    def Recorder(self): return self.recorder
    @property
    def Description(self): return self.description
    # Russian
    @property
    def РахунокДт(self): return self.AccountDt
    @property
    def РахунокКт(self): return self.AccountKt
    @property
    def Сумма(self): return self.amount
    @property
    def Сума(self): return self.amount


class AccountingRegister:
    """
    РегистрБухгалтерии — the core accounting engine.
    Stores double-entry postings and answers balance queries.
    """

    def __init__(self, name: str, chart: ChartOfAccounts):
        self.name = name
        self.chart = chart
        self._entries: list[AccountingEntry] = []
        self._postings: list[_PostingPair] = []

    # ── Write postings ───────────────────────────────────────────────────────

    def Post(self,
             period: datetime.datetime,
             recorder: str,
             debit_account: Account | str,
             credit_account: Account | str,
             amount: Decimal | float,
             currency: str = "",
             amount_currency: Decimal | float = Decimal(0),
             subconto_debit=(),
             subconto_credit=(),
             description: str = "") -> None:
        """Create a double-entry posting (debit + credit)."""
        if isinstance(debit_account, str):
            debit_account = self.chart.FindByCode(debit_account)
        if isinstance(credit_account, str):
            credit_account = self.chart.FindByCode(credit_account)
        amount = Decimal(str(amount))

        def _sc(v):
            if v is None or v == () or v == "":
                return [None, None, None]
            if isinstance(v, (list, tuple)):
                return (list(v) + [None, None, None])[:3]
            return [v, None, None]

        sc_d = _sc(subconto_debit)
        sc_c = _sc(subconto_credit)

        dt_entry = AccountingEntry(
            period=period, recorder=recorder,
            account=debit_account,
            subconto1=sc_d[0], subconto2=sc_d[1], subconto3=sc_d[2],
            amount=amount, currency=currency,
            amount_currency=Decimal(str(amount_currency)),
            is_debit=True, description=description,
        )
        ct_entry = AccountingEntry(
            period=period, recorder=recorder,
            account=credit_account,
            subconto1=sc_c[0], subconto2=sc_c[1], subconto3=sc_c[2],
            amount=amount, currency=currency,
            amount_currency=Decimal(str(amount_currency)),
            is_debit=False, description=description,
        )
        self._entries.append(dt_entry)
        self._entries.append(ct_entry)
        self._postings.append(_PostingPair(
            period=period, recorder=recorder, description=description,
            debit_account=dt_entry.account, credit_account=ct_entry.account,
            subconto_debit=sc_d[0], subconto_credit=sc_c[0],
            amount=amount,
        ))

    def Провести(self, period, recorder, *args) -> None:
        """Smart dispatcher: detects old (RU) vs new (UK) call signature.

        Old: Провести(period, recorder, debit, credit, amount, ...)
        New: Провести(period, recorder, description, debit, credit, amount, sc_dt, sc_ct)
        """
        def _is_account_like(v) -> bool:
            if isinstance(v, Account): return True
            if isinstance(v, str): return v.strip().lstrip('0').isdigit() or v in self.chart._accounts
            return False

        if args and not _is_account_like(args[0]):
            # New Ukrainian format: description, debit, credit, amount, [sc_dt, sc_ct]
            description = args[0]
            debit    = args[1] if len(args) > 1 else None
            credit   = args[2] if len(args) > 2 else None
            amount   = args[3] if len(args) > 3 else 0
            sc_dt    = args[4] if len(args) > 4 else ()
            sc_ct    = args[5] if len(args) > 5 else ()
            self.Post(period, recorder, debit, credit, amount,
                      subconto_debit=sc_dt, subconto_credit=sc_ct,
                      description=description)
        else:
            # Old Russian format: debit, credit, amount, [currency, amount_currency, sc_dt, sc_ct]
            debit    = args[0] if len(args) > 0 else None
            credit   = args[1] if len(args) > 1 else None
            amount   = args[2] if len(args) > 2 else 0
            currency = args[3] if len(args) > 3 else ""
            amt_cur  = args[4] if len(args) > 4 else 0
            sc_dt    = args[5] if len(args) > 5 else ()
            sc_ct    = args[6] if len(args) > 6 else ()
            self.Post(period, recorder, debit, credit, amount, currency, amt_cur, sc_dt, sc_ct)

    # ── Balance queries ──────────────────────────────────────────────────────

    def Balance(self,
                account: Account | str,
                period_end: datetime.datetime | None = None,
                subconto1=None, subconto2=None, subconto3=None
                ) -> dict:
        """
        Return {"Dt": debit_total, "Ct": credit_total, "Balance": net}
        Net = Dt - Ct for active accounts (Dt > Ct means asset).
        """
        if isinstance(account, str):
            account = self.chart.FindByCode(account)
        dt_sum = Decimal(0)
        ct_sum = Decimal(0)
        for e in self._entries:
            if e.account != account: continue
            if period_end and e.period > period_end: continue
            if subconto1 is not None and e.subconto1 != subconto1: continue
            if subconto2 is not None and e.subconto2 != subconto2: continue
            if subconto3 is not None and e.subconto3 != subconto3: continue
            if e.is_debit:
                dt_sum += e.amount
            else:
                ct_sum += e.amount
        return {
            "Dt": dt_sum, "Дт": dt_sum,
            "Ct": ct_sum, "Кт": ct_sum,
            "Balance": dt_sum - ct_sum,
            "Остаток": dt_sum - ct_sum,
        }

    def Turnover(self,
                 account: Account | str,
                 period_start: datetime.datetime,
                 period_end: datetime.datetime,
                 subconto1=None) -> dict:
        """Debit and credit turnover for the period."""
        if isinstance(account, str):
            account = self.chart.FindByCode(account)
        dt_sum = Decimal(0)
        ct_sum = Decimal(0)
        for e in self._entries:
            if e.account != account: continue
            if e.period < period_start or e.period > period_end: continue
            if subconto1 is not None and e.subconto1 != subconto1: continue
            if e.is_debit: dt_sum += e.amount
            else:          ct_sum += e.amount
        return {
            "DtTurnover": dt_sum, "ОборотДт": dt_sum,
            "CtTurnover": ct_sum, "ОборотКт": ct_sum,
        }

    # ── Turnover-balance report ──────────────────────────────────────────────

    def TurnoverBalance(self, period_start, period_end) -> list:
        """Returns list of dicts: Рахунок, Найменування, ОборотДт, ОборотКт."""
        from collections import defaultdict
        totals: dict = defaultdict(lambda: [Decimal(0), Decimal(0)])
        for e in self._entries:
            if e.period < period_start or e.period > period_end:
                continue
            code = e.account.code if e.account else "???"
            if e.is_debit:
                totals[code][0] += e.amount
            else:
                totals[code][1] += e.amount
        result = []
        for code in sorted(totals):
            acc = self.chart.FindByCode(code)
            name = acc.name if hasattr(acc, "name") else code
            dt, ct = totals[code]
            result.append({"Рахунок": code, "Найменування": name,
                           "ОборотДт": dt, "ОборотКт": ct})
        return result

    def AccountAnalysis(self, account, period_start, period_end) -> list:
        """Returns list of dicts: Дата, Документ, Зміст, Дебет, Кредит."""
        target = account if isinstance(account, str) else account.code
        result = []
        for p in self._postings:
            if p.period < period_start or p.period > period_end:
                continue
            dt_code = p.debit_account.code if p.debit_account else ""
            ct_code = p.credit_account.code if p.credit_account else ""
            if target not in (dt_code, ct_code):
                continue
            result.append({
                "Дата":     p.period,
                "Документ": p.recorder,
                "Зміст":    p.description,
                "Дебет":    p.amount if dt_code == target else Decimal(0),
                "Кредит":   p.amount if ct_code == target else Decimal(0),
            })
        return result

    # ── Selection (pair-based) ───────────────────────────────────────────────

    def Select(self,
               period_start=None,
               period_end=None) -> "_AccountingRegisterSelection":
        return _AccountingRegisterSelection(self._postings, period_start, period_end)

    # Russian aliases
    Остаток      = Balance
    Оборот       = Turnover
    Выбрать      = Select
    # Ukrainian aliases
    Залишок              = Balance
    Оборот               = Turnover
    Вибрати              = Select
    ОборотноСальдоВідомість = TurnoverBalance
    АналізРахунку           = AccountAnalysis

РегістрБухгалтерії = AccountingRegister
РегистрБухгалтерии = AccountingRegister


class _AccountingRegisterSelection:
    """Iterator over posting pairs."""
    def __init__(self, postings, period_start=None, period_end=None):
        self._postings = [
            p for p in postings
            if (period_start is None or p.period >= period_start)
            and (period_end is None or p.period <= period_end)
        ]
        self._pos = -1
        self._current: _PostingPair | None = None

    def Next(self) -> bool:
        self._pos += 1
        if self._pos < len(self._postings):
            self._current = self._postings[self._pos]
            return True
        return False

    def Current(self) -> "_PostingPair | None":
        return self._current

    @property
    def Period(self): return self._current.period if self._current else None
    @property
    def Amount(self): return self._current.amount if self._current else Decimal(0)

    # Russian aliases
    Следующий = Next
    Текущий   = Current
    Период    = property(lambda s: s.Period)
    Сумма     = property(lambda s: s.Amount)
    # Ukrainian aliases
    Наступний = Next
    Поточний  = Current


# ── Accumulation Register ────────────────────────────────────────────────────

@dataclass
class AccumulationEntry:
    period: datetime.datetime
    recorder: str
    dimension1: Any = None
    dimension2: Any = None
    dimension3: Any = None
    resource1: Decimal = Decimal(0)
    resource2: Decimal = Decimal(0)
    is_receipt: bool = True   # True = приход, False = расход


class AccumulationRegister:
    """
    РегистрНакопления — tracks stock/balance by dimensions.
    Supports Remainder (остаток) and Turnover (оборот) modes.
    """

    def __init__(self, name: str, mode: str = "Balance"):
        self.name = name
        self.mode = mode   # "Balance" | "Turnover"
        self._entries: list[AccumulationEntry] = []

    def Write(self, period: datetime.datetime, recorder: str,
              is_receipt: bool, resource1: Decimal | float = 0,
              dim1=None, dim2=None, resource2: Decimal | float = 0,
              dim3=None):
        self._entries.append(AccumulationEntry(
            period=period, recorder=recorder,
            dimension1=dim1, dimension2=dim2, dimension3=dim3,
            resource1=Decimal(str(resource1)),
            resource2=Decimal(str(resource2)),
            is_receipt=is_receipt,
        ))

    def Balance(self, period_end: datetime.datetime | None = None,
                dim1=None, dim2=None) -> dict:
        res1 = Decimal(0)
        res2 = Decimal(0)
        for e in self._entries:
            if period_end and e.period > period_end: continue
            if dim1 is not None and e.dimension1 != dim1: continue
            if dim2 is not None and e.dimension2 != dim2: continue
            sign = Decimal(1) if e.is_receipt else Decimal(-1)
            res1 += sign * e.resource1
            res2 += sign * e.resource2
        return {"Resource1": res1, "Resource2": res2,
                "Ресурс1": res1, "Ресурс2": res2}

    # Russian aliases
    Записать = Write
    Остаток  = Balance
    # Ukrainian aliases
    Записати = Write
    Залишок  = Balance

РегистрНакопления = AccumulationRegister


# ── Information Register ─────────────────────────────────────────────────────

@dataclass
class InformationEntry:
    """One record in an information register."""
    period: Optional[datetime.datetime]
    recorder: str
    dimensions: dict = field(default_factory=dict)
    resources: dict  = field(default_factory=dict)


class InformationRegister:
    """
    РегистрСведений — stores arbitrary key→value records,
    optionally periodic (the latest record for a period wins).

    Usage:
        reg.Write({"Сотрудник": emp}, {"Оклад": 50000}, period=dt)
        rec = reg.Get({"Сотрудник": emp}, period_end=dt)  # → {"Оклад": 50000}
    """

    def __init__(self, name: str, periodic: bool = True):
        self.name = name
        self.periodic = periodic
        self._entries: list[InformationEntry] = []

    @staticmethod
    def _to_dict(obj) -> dict:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "_data"):        # _Structure or _Map
            return dict(obj._data)
        return {}

    def Write(self,
              dimensions,
              resources,
              period: Optional[datetime.datetime] = None,
              recorder: str = "") -> None:
        self._entries.append(InformationEntry(
            period=period, recorder=recorder,
            dimensions=self._to_dict(dimensions),
            resources=self._to_dict(resources),
        ))

    def Get(self,
            dimensions,
            period_end: Optional[datetime.datetime] = None) -> dict:
        """Return resources of the latest matching record (≤ period_end)."""
        dim = self._to_dict(dimensions)
        matched = [
            e for e in self._entries
            if all(e.dimensions.get(k) == v for k, v in dim.items())
            and (period_end is None or e.period is None or e.period <= period_end)
        ]
        if not matched:
            return {}
        latest = max(matched, key=lambda e: e.period or datetime.datetime.min)
        return dict(latest.resources)

    def Select(self,
               period_start: Optional[datetime.datetime] = None,
               period_end: Optional[datetime.datetime] = None,
               **dim_filters) -> "_InformationRegisterSelection":
        entries = [
            e for e in self._entries
            if (period_start is None or e.period is None or e.period >= period_start)
            and (period_end is None or e.period is None or e.period <= period_end)
            and all(e.dimensions.get(k) == v for k, v in dim_filters.items())
        ]
        return _InformationRegisterSelection(entries)

    # Russian aliases
    Записать = Write
    Получить = Get
    Выбрать  = Select


class _InformationRegisterSelection:
    def __init__(self, entries: list[InformationEntry]):
        self._entries = entries
        self._pos = -1
        self._current: Optional[InformationEntry] = None

    def Next(self) -> bool:
        self._pos += 1
        if self._pos < len(self._entries):
            self._current = self._entries[self._pos]
            return True
        return False

    def Get(self, field_name: str):
        if self._current is None:
            return None
        return self._current.resources.get(field_name,
               self._current.dimensions.get(field_name))

    @property
    def Period(self): return self._current.period if self._current else None

    Следующий = Next
    Получить  = Get

РегистрСведений = InformationRegister


# ── Work Schedule ────────────────────────────────────────────────────────────

class WorkSchedule:
    """
    ГрафикРаботы — weekly or shift-cycle work schedule.

    Weekly:  SetWeekly([1,2,3,4,5], 8)        → Mon-Fri, 8 h/day
    Shift:   SetShift([T,T,F,F], 11, start_dt) → 2-on/2-off, 11 h/shift
    """

    def __init__(self, name: str):
        self.name = name
        self._work_weekdays: set = {1, 2, 3, 4, 5}
        self._hours: float = 8.0
        self._is_shift: bool = False
        self._shift_cycle: list = []
        self._shift_start: Optional[datetime.datetime] = None

    def SetWeekly(self, work_days, hours_per_day: float = 8.0) -> None:
        """work_days — list/_Array of ints (1=Mon … 7=Sun)."""
        self._is_shift = False
        self._work_weekdays = {int(d) for d in work_days}
        self._hours = float(hours_per_day)

    def SetShift(self, cycle, hours_per_shift: float, start_date) -> None:
        """cycle — list/_Array of bool (True=work, False=rest)."""
        self._is_shift = True
        self._shift_cycle = [bool(x) for x in cycle]
        self._hours = float(hours_per_shift)
        if isinstance(start_date, datetime.datetime):
            self._shift_start = start_date
        else:
            self._shift_start = datetime.datetime(
                start_date.year, start_date.month, start_date.day)

    def _to_dt(self, d) -> datetime.datetime:
        if isinstance(d, datetime.datetime):
            return d
        return datetime.datetime(d.year, d.month, d.day)

    def IsWorkDay(self, dt) -> bool:
        d = self._to_dt(dt)
        if self._is_shift:
            if not self._shift_cycle or self._shift_start is None:
                return False
            delta = (d.date() - self._shift_start.date()).days
            if delta < 0:
                return False
            return bool(self._shift_cycle[delta % len(self._shift_cycle)])
        return (d.weekday() + 1) in self._work_weekdays

    def WorkingDays(self, period_start, period_end) -> int:
        dt = self._to_dt(period_start)
        end = self._to_dt(period_end)
        count = 0
        while dt <= end:
            if self.IsWorkDay(dt):
                count += 1
            dt += datetime.timedelta(days=1)
        return count

    def WorkingHours(self, period_start, period_end) -> float:
        return self.WorkingDays(period_start, period_end) * self._hours

    def HoursPerWeek(self) -> float:
        if self._is_shift:
            cycle_len = len(self._shift_cycle)
            work_days = sum(1 for x in self._shift_cycle if x)
            return (work_days / cycle_len) * 7 * self._hours if cycle_len else 0
        return len(self._work_weekdays) * self._hours

    # Russian aliases
    УстановитьНедельный = SetWeekly
    УстановитьСменный   = SetShift
    ЭтоРабочийДень      = IsWorkDay
    РабочихДней         = WorkingDays
    РабочихЧасов        = WorkingHours
    ЧасовВНеделю        = HoursPerWeek

ГрафикРаботы = WorkSchedule

# ── Ukrainian aliases ─────────────────────────────────────────────────────────
ПланРахунків         = ChartOfAccounts
РегістрБухгалтерії   = AccountingRegister
РегістрНакопичення   = AccumulationRegister
РегістрВідомостей    = InformationRegister
ГрафікРоботи         = WorkSchedule
