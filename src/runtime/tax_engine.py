"""
TaxEngine — pluggable tax rate tables loaded from YAML profiles.
Supports RU/UK/US/EU jurisdictions out of the box; extensible via YAML.
"""
from __future__ import annotations
import os
import warnings
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional


# ── Built-in tax profiles (no YAML required for demo) ───────────────────────
_BUILTIN_PROFILES: Dict[str, List[dict]] = {
    # Russia 2024
    "ru_2024": [
        {"name": "НДФЛ",      "rate": "0.13", "applies_to": "income",   "desc": "Подоходный налог 13%"},
        {"name": "ПФР",       "rate": "0.22", "applies_to": "employer", "desc": "Пенсионный фонд 22%"},
        {"name": "ОМС",       "rate": "0.051","applies_to": "employer", "desc": "Обязательное медицинское страхование 5.1%"},
        {"name": "ФСС",       "rate": "0.029","applies_to": "employer", "desc": "Фонд социального страхования 2.9%"},
    ],
    # Ukraine 2024
    "ua_2024": [
        {"name": "ПДФО",      "rate": "0.18", "applies_to": "income",   "desc": "Податок на доходи фізичних осіб 18%"},
        {"name": "ЄСВ",       "rate": "0.22", "applies_to": "employer", "desc": "Єдиний соціальний внесок 22%"},
        {"name": "ВЗ",        "rate": "0.015","applies_to": "income",   "desc": "Військовий збір 1.5%"},
    ],
    # USA 2024 (simplified federal — no state)
    "us_2024": [
        {"name": "Federal",   "rate": "0.22", "applies_to": "income",   "desc": "Federal income tax 22%"},
        {"name": "FICA_SS",   "rate": "0.062","applies_to": "income",   "desc": "Social Security 6.2%"},
        {"name": "FICA_Med",  "rate": "0.0145","applies_to": "income",  "desc": "Medicare 1.45%"},
        {"name": "FUTA",      "rate": "0.006","applies_to": "employer", "desc": "Federal Unemployment 0.6%"},
    ],
    # EU generic 2024
    "eu_2024": [
        {"name": "IncomeTax", "rate": "0.25", "applies_to": "income",   "desc": "Income tax 25% (avg EU)"},
        {"name": "SocialEmp", "rate": "0.20", "applies_to": "employer", "desc": "Social contributions employer 20%"},
        {"name": "SocialEmp2","rate": "0.10", "applies_to": "income",   "desc": "Social contributions employee 10%"},
    ],
}


@dataclass
class TaxLine:
    name:        str
    rate:        Decimal
    applies_to:  str     # 'income' (employee) or 'employer'
    amount:      Decimal
    desc:        str = ""

    def __repr__(self) -> str:
        pct = float(self.rate) * 100
        return f"TaxLine({self.name}, {pct:.1f}%, {self.amount})"

    @property
    def Name(self):    return self.name
    @property
    def Rate(self):    return self.rate
    @property
    def Amount(self):  return self.amount
    @property
    def Наименование(self): return self.name
    @property
    def Ставка(self):       return self.rate
    @property
    def Сумма(self):        return self.amount
    @property
    def Назва(self):        return self.name
    @property
    def Сума(self):         return self.amount


@dataclass
class TaxResult:
    gross:              Decimal
    net:                Decimal
    employee_tax:       Decimal
    employer_tax:       Decimal
    lines:              List[TaxLine] = field(default_factory=list)

    def __repr__(self) -> str:
        return (f"TaxResult(gross={self.gross}, net={self.net}, "
                f"employee_tax={self.employee_tax}, employer_tax={self.employer_tax})")

    def summary(self, lang: str = "en") -> str:
        labels = {
            "en": ("Gross", "Employee deductions", "Net pay", "Employer contributions"),
            "ru": ("Начислено", "Удержания (работник)", "К выплате", "Взносы работодателя"),
            "uk": ("Нараховано", "Утримання (працівник)", "До виплати", "Внески роботодавця"),
        }
        g, d, n, e = labels.get(lang, labels["en"])
        lines = [
            f"  {g}: {self.gross}",
        ]
        for line in self.lines:
            lines.append(f"    {line.name} ({float(line.rate)*100:.1f}%): -{line.amount}")
        lines += [
            f"  {d}: {self.employee_tax}",
            f"  {n}: {self.net}",
            f"  {e}: {self.employer_tax}",
        ]
        return "\n".join(lines)

    # Aliases
    @property
    def Начислено(self): return self.gross
    @property
    def КВыплате(self):  return self.net
    @property
    def Нараховано(self): return self.gross
    @property
    def ДоВиплати(self):  return self.net
    @property
    def Gross(self): return self.gross
    @property
    def Net(self):   return self.net


class TaxEngine:
    """Loads tax profiles and calculates gross→net."""

    def __init__(self, profile_dir: Optional[str] = None):
        self._profile_dir = profile_dir
        self._profiles: Dict[str, List[dict]] = dict(_BUILTIN_PROFILES)
        if profile_dir and os.path.isdir(profile_dir):
            self._load_dir(profile_dir)

    def _load_dir(self, directory: str) -> None:
        import yaml
        for fname in os.listdir(directory):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                profile_name = fname.rsplit(".", 1)[0]
                path = os.path.join(directory, fname)
                try:
                    with open(path, encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, list):
                        self._profiles[profile_name] = data
                except Exception as e:
                    warnings.warn(f"TaxEngine: could not load {path}: {e}")

    def load_profile(self, profile_name: str, yaml_path: str) -> None:
        import yaml
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, list):
            raise ValueError(f"Tax profile YAML must be a list of rate entries, got {type(data)}")
        self._profiles[profile_name] = data

    def available_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def calculate(self, gross: Decimal | float | int, profile_name: str = "ru_2024") -> TaxResult:
        gross = Decimal(str(gross))
        rates = self._profiles.get(profile_name)
        if rates is None:
            raise KeyError(f"Tax profile {profile_name!r} not found. Available: {self.available_profiles()}")

        lines: List[TaxLine] = []
        employee_tax = Decimal("0")
        employer_tax = Decimal("0")

        for entry in rates:
            rate   = Decimal(str(entry["rate"]))
            amount = (gross * rate).quantize(Decimal("0.01"))
            line   = TaxLine(
                name=entry["name"],
                rate=rate,
                applies_to=entry.get("applies_to", "income"),
                amount=amount,
                desc=entry.get("desc", ""),
            )
            lines.append(line)
            if line.applies_to == "employer":
                employer_tax += amount
            else:
                employee_tax += amount

        net = gross - employee_tax
        return TaxResult(gross=gross, net=net, employee_tax=employee_tax,
                         employer_tax=employer_tax, lines=lines)

    # ── English method aliases ───────────────────────────────────────────────
    Calculate         = calculate
    AvailableProfiles = available_profiles
    LoadProfile       = load_profile

    # ── Russian method aliases ───────────────────────────────────────────────
    def Рассчитать(self, gross, profile="ru_2024"): return self.calculate(gross, profile)
    def ДоступныеПрофили(self): return self.available_profiles()

    # ── Ukrainian method aliases ─────────────────────────────────────────────
    def Розрахувати(self, gross, profile="ua_2024"): return self.calculate(gross, profile)
    def ДоступніПрофілі(self): return self.available_profiles()

    def __repr__(self) -> str:
        return f"TaxEngine(profiles={self.available_profiles()})"


# ── Trilingual class aliases ─────────────────────────────────────────────────
НалоговыйДвижок   = TaxEngine
ПодатковийДвижок  = TaxEngine
РезультатНалога   = TaxResult
РезультатПодатку  = TaxResult
