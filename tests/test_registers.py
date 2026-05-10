"""
Tests for src.runtime.registers — ChartOfAccounts, AccountingRegister,
AccumulationRegister, InformationRegister, WorkSchedule.
"""
import datetime
import pytest
from decimal import Decimal
from src.runtime.registers import (
    ChartOfAccounts, Account,
    AccountingRegister,
    AccumulationRegister,
    InformationRegister,
    WorkSchedule,
    ПланРахунків,
    РегістрБухгалтерії,
    РегістрНакопичення,
)
from src.runtime.types import Undefined


# ── Chart of Accounts ─────────────────────────────────────────────────────────

class TestChartOfAccounts:
    def test_add_account(self):
        coa = ChartOfAccounts("Test")
        acc = coa.AddAccount("10", "Основные средства", active=True, passive=False)
        assert acc.code == "10"
        assert acc.name == "Основные средства"
        assert acc.active is True
        assert acc.passive is False

    def test_find_by_code(self):
        coa = ChartOfAccounts("Test")
        coa.AddAccount("30", "Касса")
        found = coa.FindByCode("30")
        assert found.code == "30"

    def test_find_missing(self):
        coa = ChartOfAccounts("Test")
        assert coa.FindByCode("99") is Undefined

    def test_subscript_access(self):
        coa = ChartOfAccounts("Test")
        coa.AddAccount("50", "Банк")
        assert coa["50"].name == "Банк"

    def test_iteration(self):
        coa = ChartOfAccounts("Test")
        coa.AddAccount("10", "А")
        coa.AddAccount("20", "Б")
        codes = {a.code for a in coa}
        assert codes == {"10", "20"}

    def test_ukrainian_dodati(self):
        coa = ChartOfAccounts("УКСГП")
        acc = coa.Додати("31", "Рахунки в банках", True, False, "Контрагент")
        assert acc.code == "31"
        assert acc.subconto_kinds == ["Контрагент"]

    def test_ukrainian_dodati_no_subconto(self):
        coa = ChartOfAccounts("Test")
        acc = coa.Додати("10", "Товари")
        assert acc.subconto_kinds == []

    def test_selection(self):
        coa = ChartOfAccounts("Test")
        coa.AddAccount("10", "А")
        coa.AddAccount("20", "Б")
        sel = coa.Select()
        results = []
        while sel.Next():
            results.append(sel.Current().code)
        assert len(results) == 2

    def test_account_eq_by_code(self):
        coa = ChartOfAccounts("Test")
        a1 = coa.AddAccount("10", "One")
        a2 = coa.AddAccount("10", "Duplicate code")
        assert a1 == a2

    def test_account_hash(self):
        coa = ChartOfAccounts("Test")
        a = coa.AddAccount("10", "Товари")
        assert hash(a) == hash("10")

    def test_alias_plan_rakhunkiv(self):
        coa = ПланРахунків("UA")
        acc = coa.Додати("36", "Розрахунки")
        assert acc.code == "36"


# ── Accounting Register ───────────────────────────────────────────────────────

def make_register():
    coa = ChartOfAccounts("Test")
    coa.AddAccount("10", "Товари", active=True)
    coa.AddAccount("36", "Покупці", active=True)
    coa.AddAccount("70", "Дохід", passive=True)
    reg = AccountingRegister("Main", coa)
    return reg, coa


class TestAccountingRegisterPost:
    def test_post_creates_entries(self):
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Post(dt, "DOC001", coa["36"], coa["70"], 1000)
        assert len(reg._entries) == 2  # debit + credit

    def test_post_by_code(self):
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Post(dt, "DOC001", "36", "70", 5000)
        assert len(reg._postings) == 1

    def test_balance_after_post(self):
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Post(dt, "D1", coa["36"], coa["70"], Decimal("1000"))
        b = reg.Balance(coa["36"])
        assert b["Dt"] == Decimal("1000")
        assert b["Ct"] == Decimal("0")

    def test_balance_net(self):
        reg, coa = make_register()
        dt1 = datetime.datetime(2025, 1, 1)
        dt2 = datetime.datetime(2025, 2, 1)
        reg.Post(dt1, "D1", coa["36"], coa["70"], 3000)
        reg.Post(dt2, "D2", coa["70"], coa["36"], 1000)
        b = reg.Balance(coa["36"])
        assert b["Balance"] == Decimal("2000")

    def test_balance_period_filter(self):
        reg, coa = make_register()
        dt1 = datetime.datetime(2025, 1, 1)
        dt2 = datetime.datetime(2025, 3, 1)
        reg.Post(dt1, "D1", coa["36"], coa["70"], 500)
        reg.Post(dt2, "D2", coa["36"], coa["70"], 500)
        cutoff = datetime.datetime(2025, 2, 1)
        b = reg.Balance(coa["36"], period_end=cutoff)
        assert b["Dt"] == Decimal("500")


class TestAccountingRegisterProvesti:
    def test_provesti_russian_format(self):
        """Провести with account-like first arg → Russian format."""
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Провести(dt, "DOC1", coa["36"], coa["70"], 2000)
        assert len(reg._postings) == 1
        assert reg._postings[0].amount == Decimal("2000")

    def test_provesti_ukrainian_format(self):
        """Провести with description-string first arg → Ukrainian format."""
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Провести(dt, "DOC1", "Продаж товару", coa["36"], coa["70"], 5000)
        pair = reg._postings[0]
        assert pair.amount == Decimal("5000")
        assert pair.description == "Продаж товару"

    def test_provesti_by_code_detected_as_account(self):
        """Purely numeric string is detected as account code → Russian format."""
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Провести(dt, "DOC1", "36", "70", 100)
        assert reg._postings[0].AccountDt == "36"
        assert reg._postings[0].AccountKt == "70"


class TestAccountingRegisterReports:
    def _setup(self):
        reg, coa = make_register()
        jan = datetime.datetime(2025, 1, 15)
        feb = datetime.datetime(2025, 2, 10)
        reg.Post(jan, "D1", coa["36"], coa["70"], 3000)
        reg.Post(feb, "D2", coa["36"], coa["70"], 2000)
        return reg, coa

    def test_turnover_balance(self):
        reg, coa = self._setup()
        start = datetime.datetime(2025, 1, 1)
        end   = datetime.datetime(2025, 12, 31)
        osv = reg.TurnoverBalance(start, end)
        codes = {row["Рахунок"] for row in osv}
        assert "36" in codes
        assert "70" in codes

    def test_turnover_balance_amounts_match(self):
        reg, coa = self._setup()
        start = datetime.datetime(2025, 1, 1)
        end   = datetime.datetime(2025, 12, 31)
        osv = reg.TurnoverBalance(start, end)
        row_36 = next(r for r in osv if r["Рахунок"] == "36")
        assert row_36["ОборотДт"] == Decimal("5000")
        assert row_36["ОборотКт"] == Decimal("0")

    def test_account_analysis(self):
        reg, coa = self._setup()
        start = datetime.datetime(2025, 1, 1)
        end   = datetime.datetime(2025, 12, 31)
        analysis = reg.AccountAnalysis(coa["36"], start, end)
        assert len(analysis) == 2
        total_debit = sum(r["Дебет"] for r in analysis)
        assert total_debit == Decimal("5000")

    def test_selection(self):
        reg, coa = self._setup()
        start = datetime.datetime(2025, 1, 1)
        end   = datetime.datetime(2025, 1, 31)
        sel = reg.Select(start, end)
        count = 0
        while sel.Next():
            count += 1
        assert count == 1

    def test_posting_pair_properties(self):
        reg, coa = make_register()
        dt = datetime.datetime(2025, 1, 1)
        reg.Post(dt, "DOC1", coa["36"], coa["70"], 1234, description="Test")
        pair = reg._postings[0]
        assert pair.AccountDt == "36"
        assert pair.AccountKt == "70"
        assert pair.Amount == Decimal("1234")
        assert pair.Description == "Test"


# ── Accumulation Register ─────────────────────────────────────────────────────

class TestAccumulationRegister:
    def test_write_and_balance(self):
        reg = AccumulationRegister("Товари")
        dt = datetime.datetime(2025, 1, 1)
        reg.Write(dt, "PO1", True, 100, dim1="Борошно")
        b = reg.Balance(dim1="Борошно")
        assert b["Resource1"] == Decimal("100")

    def test_write_receipt_and_expense(self):
        reg = AccumulationRegister("Товари")
        dt1 = datetime.datetime(2025, 1, 1)
        dt2 = datetime.datetime(2025, 1, 10)
        reg.Write(dt1, "PO1", True, 200, dim1="Цукор")
        reg.Write(dt2, "SO1", False, 50, dim1="Цукор")
        b = reg.Balance(dim1="Цукор")
        assert b["Resource1"] == Decimal("150")

    def test_balance_by_dimension(self):
        reg = AccumulationRegister("Склад")
        dt = datetime.datetime(2025, 1, 1)
        reg.Write(dt, "D1", True, 100, dim1="A")
        reg.Write(dt, "D2", True, 200, dim1="B")
        b_a = reg.Balance(dim1="A")
        assert b_a["Resource1"] == Decimal("100")

    def test_balance_period_filter(self):
        reg = AccumulationRegister("Склад")
        dt1 = datetime.datetime(2025, 1, 1)
        dt2 = datetime.datetime(2025, 6, 1)
        reg.Write(dt1, "D1", True, 500, dim1="X")
        reg.Write(dt2, "D2", True, 300, dim1="X")
        cutoff = datetime.datetime(2025, 3, 1)
        b = reg.Balance(period_end=cutoff, dim1="X")
        assert b["Resource1"] == Decimal("500")

    def test_ukrainian_alias(self):
        reg = РегістрНакопичення("Склад")
        dt = datetime.datetime(2025, 1, 1)
        reg.Записати(dt, "D1", True, 999, dim1="Y")
        b = reg.Залишок(dim1="Y")
        assert b["Resource1"] == Decimal("999")


# ── Information Register ──────────────────────────────────────────────────────

class TestInformationRegister:
    def test_write_and_get(self):
        reg = InformationRegister("Оклади")
        dt = datetime.datetime(2025, 1, 1)
        reg.Write({"Сотрудник": "Іван"}, {"Оклад": 50000}, period=dt)
        result = reg.Get({"Сотрудник": "Іван"}, period_end=dt)
        assert result["Оклад"] == 50000

    def test_get_missing_returns_empty(self):
        reg = InformationRegister("Test")
        result = reg.Get({"Key": "missing"})
        assert result == {}

    def test_periodic_latest_wins(self):
        reg = InformationRegister("Rates")
        dt1 = datetime.datetime(2025, 1, 1)
        dt2 = datetime.datetime(2025, 6, 1)
        reg.Write({"Currency": "USD"}, {"Rate": 38.0}, period=dt1)
        reg.Write({"Currency": "USD"}, {"Rate": 42.0}, period=dt2)
        result = reg.Get({"Currency": "USD"}, period_end=dt2)
        assert result["Rate"] == 42.0

    def test_period_boundary(self):
        reg = InformationRegister("Rates")
        dt1 = datetime.datetime(2025, 1, 1)
        dt2 = datetime.datetime(2025, 6, 1)
        reg.Write({"Currency": "EUR"}, {"Rate": 42.0}, period=dt1)
        reg.Write({"Currency": "EUR"}, {"Rate": 46.0}, period=dt2)
        # Should get Jan rate only
        result = reg.Get({"Currency": "EUR"}, period_end=datetime.datetime(2025, 3, 1))
        assert result["Rate"] == 42.0


# ── Work Schedule ─────────────────────────────────────────────────────────────

class TestWorkSchedule:
    def test_weekly_working_days(self):
        sched = WorkSchedule("5/2")
        sched.SetWeekly([1, 2, 3, 4, 5], 8)
        # Week of 2025-01-06 (Mon) to 2025-01-10 (Fri)
        start = datetime.datetime(2025, 1, 6)
        end   = datetime.datetime(2025, 1, 10)
        assert sched.WorkingDays(start, end) == 5

    def test_weekly_weekend_not_counted(self):
        sched = WorkSchedule("5/2")
        sched.SetWeekly([1, 2, 3, 4, 5], 8)
        # Saturday
        sat = datetime.datetime(2025, 1, 11)
        assert not sched.IsWorkDay(sat)

    def test_weekly_hours(self):
        sched = WorkSchedule("5/2")
        sched.SetWeekly([1, 2, 3, 4, 5], 8)
        start = datetime.datetime(2025, 1, 6)
        end   = datetime.datetime(2025, 1, 10)
        assert sched.WorkingHours(start, end) == 40.0

    def test_shift_schedule(self):
        sched = WorkSchedule("2/2")
        # 2 on, 2 off — starting Monday 2025-01-06
        start = datetime.datetime(2025, 1, 6)
        sched.SetShift([True, True, False, False], 12, start)
        assert sched.IsWorkDay(datetime.datetime(2025, 1, 6))   # day 0 → work
        assert sched.IsWorkDay(datetime.datetime(2025, 1, 7))   # day 1 → work
        assert not sched.IsWorkDay(datetime.datetime(2025, 1, 8))  # day 2 → rest
        assert not sched.IsWorkDay(datetime.datetime(2025, 1, 9))  # day 3 → rest
        assert sched.IsWorkDay(datetime.datetime(2025, 1, 10))  # day 4 → work (cycle repeats)

    def test_hours_per_week_weekly(self):
        sched = WorkSchedule("5/2")
        sched.SetWeekly([1, 2, 3, 4, 5], 8)
        assert sched.HoursPerWeek() == 40.0
