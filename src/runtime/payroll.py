"""
PayrollEngine — payroll periods, absence tracking, bonus schemes, payslip generation.
Tax calculation delegated to TaxEngine.
"""
from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from .tax_engine import TaxEngine, TaxResult


class PayPeriod(str, Enum):
    MONTHLY   = "monthly"
    BIWEEKLY  = "biweekly"
    WEEKLY    = "weekly"


class AbsenceType(str, Enum):
    VACATION = "vacation"
    SICK     = "sick"
    UNPAID   = "unpaid"
    OTHER    = "other"


@dataclass
class Employee:
    id:            str
    name:          str
    position:      str
    base_salary:   Decimal
    tax_profile:   str = "ru_2024"
    org_id:        str = ""

    def __post_init__(self):
        if not isinstance(self.base_salary, Decimal):
            object.__setattr__(self, "base_salary", Decimal(str(self.base_salary)))

    def __repr__(self) -> str:
        return f"Employee({self.id!r}, {self.name!r}, {self.position!r})"

    @property
    def Id(self):         return self.id
    @property
    def Name(self):       return self.name
    @property
    def Position(self):   return self.position
    @property
    def BaseSalary(self): return self.base_salary

    @property
    def Код(self):           return self.id
    @property
    def Имя(self):           return self.name
    @property
    def Должность(self):     return self.position
    @property
    def ОкладОсновной(self): return self.base_salary

    @property
    def Ім(self):            return self.name
    @property
    def Посада(self):        return self.position
    @property
    def ОкладОсновний(self): return self.base_salary


@dataclass
class Absence:
    employee_id: str
    absence_type: AbsenceType
    days:  int
    period: str    # "2024-01"

    @property
    def Type(self):         return self.absence_type
    @property
    def Days(self):         return self.days
    @property
    def Тип(self):          return self.absence_type
    @property
    def Дни(self):          return self.days
    @property
    def Дні(self):          return self.days


@dataclass
class BonusScheme:
    name:       str
    bonus_type: str        # 'fixed' | 'percent'
    value:      Decimal    # amount or fraction (0.10 = 10%)

    def __post_init__(self):
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

    def calculate(self, base_salary: Decimal) -> Decimal:
        if self.bonus_type == "percent":
            return (base_salary * self.value).quantize(Decimal("0.01"))
        return self.value

    @property
    def Name(self):  return self.name
    @property
    def Value(self): return self.value
    @property
    def Наименование(self): return self.name
    @property
    def Назва(self):        return self.name


@dataclass
class PayslipLine:
    label:  str
    amount: Decimal
    is_deduction: bool = False

    def __repr__(self) -> str:
        sign = "-" if self.is_deduction else "+"
        return f"  {sign} {self.label}: {self.amount}"

    @property
    def Label(self):  return self.label
    @property
    def Amount(self): return self.amount
    @property
    def IsDeduction(self): return self.is_deduction


@dataclass
class Payslip:
    employee:   Employee
    period:     str
    lines:      List[PayslipLine] = field(default_factory=list)
    gross:      Decimal = Decimal("0")
    net:        Decimal = Decimal("0")

    def __repr__(self) -> str:
        return f"Payslip({self.employee.name!r}, {self.period}, net={self.net})"

    def render(self, lang: str = "en") -> str:
        header = {
            "en": ("PAYSLIP", "Employee", "Period", "TOTAL NET"),
            "ru": ("РАСЧЁТНЫЙ ЛИСТ", "Сотрудник", "Период", "ИТОГО К ВЫПЛАТЕ"),
            "uk": ("РОЗРАХУНКОВИЙ ЛИСТ", "Працівник", "Період", "РАЗОМ ДО ВИПЛАТИ"),
        }.get(lang, ("PAYSLIP", "Employee", "Period", "TOTAL NET"))

        lines = [
            f"{'='*40}",
            f"{header[0]}",
            f"{header[1]}: {self.employee.name} ({self.employee.position})",
            f"{header[2]}: {self.period}",
            f"{'-'*40}",
        ]
        for ln in self.lines:
            sign = "-" if ln.is_deduction else "+"
            lines.append(f"  {sign} {ln.label}: {ln.amount}")
        lines += [f"{'='*40}", f"{header[3]}: {self.net}"]
        return "\n".join(lines)

    # Aliases
    Render       = render
    Сформировать = render
    Сформувати   = render

    @property
    def Employee(self): return self.employee
    @property
    def Period(self):   return self.period
    @property
    def Net(self):      return self.net
    @property
    def Gross(self):    return self.gross
    @property
    def КВыплате(self):  return self.net
    @property
    def ДоВиплати(self): return self.net


@dataclass
class PayrollResult:
    employee:     Employee
    period:       str
    gross:        Decimal
    net:          Decimal
    tax_result:   TaxResult
    absences:     List[Absence] = field(default_factory=list)
    bonuses:      List[BonusScheme] = field(default_factory=list)
    bonus_amount: Decimal = Decimal("0")

    def __repr__(self) -> str:
        return (f"PayrollResult({self.employee.name!r}, {self.period}, "
                f"gross={self.gross}, net={self.net})")

    @property
    def Employee(self): return self.employee
    @property
    def Gross(self):    return self.gross
    @property
    def Net(self):      return self.net
    @property
    def Period(self):   return self.period
    @property
    def КВыплате(self):  return self.net
    @property
    def ДоВиплати(self): return self.net
    @property
    def Начислено(self):  return self.gross
    @property
    def Нараховано(self): return self.gross


class PayrollEngine:
    """
    Calculates payroll for a set of employees over a period.
    Delegates tax calculation to TaxEngine.

    Usage:
        engine = PayrollEngine()
        engine.add_employee(Employee("E1", "Иванов И.И.", "Engineer", Decimal("100000")))
        engine.add_absence("E1", AbsenceType.VACATION, days=5, period="2024-01")
        results = engine.calculate("2024-01")
        print(engine.generate_payslip(results[0]).render("ru"))
    """

    WORKING_DAYS = {
        PayPeriod.MONTHLY:  22,
        PayPeriod.BIWEEKLY: 10,
        PayPeriod.WEEKLY:    5,
    }

    def __init__(
        self,
        tax_engine: Optional[TaxEngine] = None,
        pay_period: PayPeriod = PayPeriod.MONTHLY,
        overtime_multiplier: float = 1.5,
    ):
        self._tax_engine         = tax_engine or TaxEngine()
        self._pay_period         = pay_period
        self._overtime_multiplier = Decimal(str(overtime_multiplier))
        self._employees:  Dict[str, Employee]           = {}
        self._absences:   List[Absence]                 = []
        self._bonuses:    Dict[str, List[BonusScheme]]  = {}

    def add_employee(self, employee: Employee) -> None:
        self._employees[employee.id] = employee

    def add_absence(self, employee_id: str, absence_type: AbsenceType | str,
                    days: int, period: str) -> None:
        if isinstance(absence_type, str):
            absence_type = AbsenceType(absence_type)
        self._absences.append(Absence(employee_id=employee_id,
                                      absence_type=absence_type,
                                      days=days, period=period))

    def add_bonus(self, employee_id: str, scheme: BonusScheme) -> None:
        self._bonuses.setdefault(employee_id, []).append(scheme)

    def calculate(self, period: str) -> List[PayrollResult]:
        results: List[PayrollResult] = []
        working_days = self.WORKING_DAYS[self._pay_period]

        for emp in self._employees.values():
            # Absences for this employee/period
            emp_absences = [a for a in self._absences
                            if a.employee_id == emp.id and a.period == period]
            absent_days = sum(a.days for a in emp_absences
                              if a.absence_type != AbsenceType.VACATION)
            # Vacation: paid; sick/unpaid: reduce gross
            unpaid_days = sum(a.days for a in emp_absences
                              if a.absence_type == AbsenceType.UNPAID)
            sick_days   = sum(a.days for a in emp_absences
                              if a.absence_type == AbsenceType.SICK)

            daily_rate = (emp.base_salary / working_days).quantize(Decimal("0.01"))
            # Sick pay at 80%, unpaid at 0%
            deduction  = (daily_rate * unpaid_days + daily_rate * sick_days * Decimal("0.2"))
            base_gross = emp.base_salary - deduction

            # Bonuses
            bonus_amount = Decimal("0")
            emp_bonuses  = self._bonuses.get(emp.id, [])
            for bonus in emp_bonuses:
                bonus_amount += bonus.calculate(emp.base_salary)

            gross = (base_gross + bonus_amount).quantize(Decimal("0.01"))

            # Tax
            tax_result = self._tax_engine.calculate(gross, emp.tax_profile)

            results.append(PayrollResult(
                employee=emp,
                period=period,
                gross=gross,
                net=tax_result.net,
                tax_result=tax_result,
                absences=emp_absences,
                bonuses=emp_bonuses,
                bonus_amount=bonus_amount,
            ))

        return results

    def generate_payslip(self, result: PayrollResult, lang: str = "en") -> Payslip:
        lbl = {
            "en": {"salary": "Base salary", "bonus": "Bonus", "tax": "Income tax",
                   "social": "Social contributions", "net": "Net pay"},
            "ru": {"salary": "Оклад", "bonus": "Премия", "tax": "НДФЛ",
                   "social": "Социальные взносы", "net": "К выплате"},
            "uk": {"salary": "Оклад", "bonus": "Премія", "tax": "ПДФО",
                   "social": "Соціальні внески", "net": "До виплати"},
        }.get(lang, {"salary": "Base salary", "bonus": "Bonus", "tax": "Income tax",
                     "social": "Social contributions", "net": "Net pay"})

        lines: List[PayslipLine] = [
            PayslipLine(lbl["salary"], result.employee.base_salary),
        ]
        if result.bonus_amount > 0:
            lines.append(PayslipLine(lbl["bonus"], result.bonus_amount))

        for tax_line in result.tax_result.lines:
            if tax_line.applies_to == "income":
                lines.append(PayslipLine(tax_line.name, tax_line.amount, is_deduction=True))

        return Payslip(employee=result.employee, period=result.period,
                       lines=lines, gross=result.gross, net=result.net)

    def payroll_summary(self, results: List[PayrollResult], lang: str = "en") -> str:
        hdr = {
            "en": ("PAYROLL SUMMARY", "Employee", "Gross", "Net", "Tax"),
            "ru": ("ВЕДОМОСТЬ ЗАРПЛАТЫ", "Сотрудник", "Начислено", "К выплате", "Налоги"),
            "uk": ("ВІДОМІСТЬ ЗАРПЛАТИ", "Працівник", "Нараховано", "До виплати", "Податки"),
        }.get(lang, ("PAYROLL SUMMARY", "Employee", "Gross", "Net", "Tax"))
        lines = [hdr[0], "=" * 60]
        total_gross = Decimal("0")
        total_net   = Decimal("0")
        for r in results:
            tax = r.gross - r.net
            lines.append(f"  {r.employee.name:<20} {hdr[2]}:{r.gross:>10}  "
                         f"{hdr[3]}:{r.net:>10}  {hdr[4]}:{tax:>10}")
            total_gross += r.gross
            total_net   += r.net
        lines += ["=" * 60,
                  f"  {'TOTAL':<20} {hdr[2]}:{total_gross:>10}  {hdr[3]}:{total_net:>10}"]
        return "\n".join(lines)

    # ── English method aliases ───────────────────────────────────────────────
    AddEmployee     = add_employee
    AddAbsence      = add_absence
    AddBonus        = add_bonus
    Calculate       = calculate
    GeneratePayslip = generate_payslip
    PayrollSummary  = payroll_summary

    # ── Russian method aliases ───────────────────────────────────────────────
    def ДобавитьСотрудника(self, emp): return self.add_employee(emp)
    def ДобавитьОтсутствие(self, id, typ, days, period): return self.add_absence(id, typ, days, period)
    def ДобавитьПремию(self, id, scheme): return self.add_bonus(id, scheme)
    def Рассчитать(self, period): return self.calculate(period)
    def СформироватьРасчетныйЛист(self, result, lang="ru"): return self.generate_payslip(result, lang)
    def ВедомостьЗарплаты(self, results, lang="ru"): return self.payroll_summary(results, lang)

    # ── Ukrainian method aliases ─────────────────────────────────────────────
    def ДодатиПрацівника(self, emp): return self.add_employee(emp)
    def ДодатиВідсутність(self, id, typ, days, period): return self.add_absence(id, typ, days, period)
    def ДодатиПремію(self, id, scheme): return self.add_bonus(id, scheme)
    def Розрахувати(self, period): return self.calculate(period)
    def СформуватиРозрахунковийЛист(self, result, lang="uk"): return self.generate_payslip(result, lang)
    def ВідомістьЗарплати(self, results, lang="uk"): return self.payroll_summary(results, lang)

    def __repr__(self) -> str:
        return (f"PayrollEngine(employees={len(self._employees)}, "
                f"period={self._pay_period.value})")


# ── Trilingual class aliases ─────────────────────────────────────────────────
РасчетЗарплаты   = PayrollEngine
РозрахунокЗарплати = PayrollEngine
Сотрудник        = Employee
Працівник        = Employee
Отсутствие       = Absence
Відсутність      = Absence
Премия           = BonusScheme
Премія           = BonusScheme
РасчетныйЛист    = Payslip
РозрахунковийЛист = Payslip
ПериодОплаты     = PayPeriod
ПеріодОплати     = PayPeriod
ТипОтсутствия    = AbsenceType
ТипВідсутності   = AbsenceType
