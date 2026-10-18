"""Trial balance (ОСВ) reconciliation after a migration.

Two trial balances for the same period — one exported from 1C/BAS (usually
.xls), one from the target system (Odoo .xlsx/.csv) — are matched by account
and compared on turnovers and closing balances.

The comparison itself is plain Python (reconcile()), so it is testable and
works without GridCraft. GridCraft is used to read .xls/.xlsb/.ods and to
write the result as a real workbook: differences are live formulas (=C2-G2),
mismatches are highlighted by conditional formatting, totals are SUM()s — the
accountant can audit every number in Excel or GridCraft.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .gridcraft import GridCraft, Step

TOLERANCE = 0.005  # half a kopeck / копійки

_ACCOUNT_HEADERS = {"счёт", "счет", "сч.", "сч", "рахунок", "рах.", "account", "acc", "code", "код"}


@dataclass
class TBRow:
    account: str
    name: str
    open_dt: float = 0.0
    open_ct: float = 0.0
    turn_dt: float = 0.0
    turn_ct: float = 0.0
    close_dt: float = 0.0
    close_ct: float = 0.0


@dataclass
class Diff:
    account: str
    name: str
    left: TBRow | None
    right: TBRow | None

    def _v(self, side: TBRow | None, f: str) -> float:
        return getattr(side, f) if side else 0.0

    def delta(self, f: str) -> float:
        return round(self._v(self.left, f) - self._v(self.right, f), 2)

    @property
    def ok(self) -> bool:
        return self.left is not None and self.right is not None and all(
            abs(self.delta(f)) < TOLERANCE for f in ("turn_dt", "turn_ct", "close_dt", "close_ct"))

    @property
    def status(self) -> str:
        if self.left is None:
            return "only_right"
        if self.right is None:
            return "only_left"
        return "ok" if self.ok else "mismatch"


# ── reading ──────────────────────────────────────────────────────────────────

def _num(v: Any) -> float | None:
    if v is None or v == "":
        return 0.0
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace("\xa0", "").replace(" ", "").replace(",", ".")
    if s in ("", "-", "—"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return None


def _norm_account(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def rows_to_trial_balance(rows: list[list[Any]]) -> list[TBRow]:
    """Find the header (a cell like Счёт/Сч./Рахунок/Account) and read the rows below it.

    Layout expected (as 1C/BAS and 1S print it): account, name, then six
    numbers — opening Dt/Ct, turnover Dt/Ct, closing Dt/Ct. Rows whose account
    is empty or whose numbers do not parse (totals captions, footers) are skipped.
    """
    start = None
    for i, row in enumerate(rows):
        if row and str(row[0]).strip().lower().strip("﻿") in _ACCOUNT_HEADERS:
            start = i + 1
            break
    if start is None:
        raise ValueError("no header row with an account column (Счёт / Сч. / Рахунок / Account)")
    out: list[TBRow] = []
    for row in rows[start:]:
        if len(row) < 8 or row[0] in (None, "") or all(v in (None, "") for v in row[1:8]):
            continue  # short rows, blank account, footers like "Подписи:"
        nums = [_num(v) for v in row[2:8]]
        if any(n is None for n in nums):
            continue
        acc = _norm_account(row[0])
        if acc.lower() in ("итого", "разом", "всього", "total"):
            continue
        out.append(TBRow(acc, str(row[1] or "").strip(), *nums))  # type: ignore[arg-type]
    return out


def load_trial_balance(path: Path | str, gc: GridCraft | None = None, sheet: str | None = None) -> list[TBRow]:
    """CSV is read directly; .xls/.xlsx/.xlsb/.ods go through GridCraft."""
    path = Path(path)
    if path.suffix.lower() in (".csv", ".tsv", ".txt"):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=";,\t")
        return rows_to_trial_balance([r for r in csv.reader(text.splitlines(), dialect)])
    return rows_to_trial_balance((gc or GridCraft()).read(path, sheet=sheet))


# ── comparing ────────────────────────────────────────────────────────────────

def _acc_key(acc: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"[.\-/ ]", acc))


def reconcile(left: list[TBRow], right: list[TBRow]) -> list[Diff]:
    lmap = {r.account: r for r in left}
    rmap = {r.account: r for r in right}
    accounts = sorted(set(lmap) | set(rmap), key=_acc_key)
    return [Diff(a, (lmap.get(a) or rmap[a]).name, lmap.get(a), rmap.get(a)) for a in accounts]


def summary(diffs: list[Diff]) -> dict[str, int]:
    out = {"accounts": len(diffs), "ok": 0, "mismatch": 0, "only_left": 0, "only_right": 0}
    for d in diffs:
        out[d.status] += 1
    return out


# ── writing (GridCraft) ──────────────────────────────────────────────────────

LABELS = {
    "ru": {"sheet": "Сверка ОСВ", "acc": "Счёт", "name": "Наименование", "td": "Обор. Дт", "tc": "Обор. Кт",
           "cd": "Кон. Дт", "cc": "Кон. Кт", "d": "Δ", "status": "Статус", "ok": "OK", "bad": "РАСХОЖДЕНИЕ",
           "total": "Итого"},
    "uk": {"sheet": "Звірка ОСВ", "acc": "Рахунок", "name": "Назва", "td": "Обор. Дт", "tc": "Обор. Кт",
           "cd": "Кін. Дт", "cc": "Кін. Кт", "d": "Δ", "status": "Статус", "ok": "OK", "bad": "РОЗБІЖНІСТЬ",
           "total": "Разом"},
    "en": {"sheet": "TB reconciliation", "acc": "Account", "name": "Name", "td": "Turn. Dr", "tc": "Turn. Cr",
           "cd": "Close Dr", "cc": "Close Cr", "d": "Δ", "status": "Status", "ok": "OK", "bad": "MISMATCH",
           "total": "Total"},
}
_FIELDS = ("turn_dt", "turn_ct", "close_dt", "close_ct")
_COLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def build_steps(diffs: list[Diff], left_label: str, right_label: str, lang: str = "ru") -> list[Step]:
    """GridCraft commands that lay out the reconciliation sheet.

    Columns: A account, B name, C-F left (turn Dt/Ct, close Dt/Ct), G-J right,
    K-N deltas as formulas, O status formula.
    """
    t = LABELS.get(lang, LABELS["en"])
    heads = [t["td"], t["tc"], t["cd"], t["cc"]]
    header = ([t["acc"], t["name"]] + [f"{left_label} {h}" for h in heads]
              + [f"{right_label} {h}" for h in heads] + [f"{t['d']} {h}" for h in heads] + [t["status"]])
    rows: list[list[Any]] = [header]
    for i, d in enumerate(diffs, start=2):
        lv = [getattr(d.left, f) if d.left else None for f in _FIELDS]
        rv = [getattr(d.right, f) if d.right else None for f in _FIELDS]
        deltas = [f"=N({_COLS[2 + k]}{i})-N({_COLS[6 + k]}{i})" for k in range(4)]
        status = (f'=IF(AND(COUNT(C{i}:F{i})=4,COUNT(G{i}:J{i})=4,'
                  f'MAX(ABS(K{i}),ABS(L{i}),ABS(M{i}),ABS(N{i}))<{TOLERANCE}),"{t["ok"]}","{t["bad"]}")')
        rows.append([d.account, d.name, *lv, *rv, *deltas, status])
    last = len(rows)
    total_row = [t["total"], None] + [f"=SUM({c}2:{c}{last})" for c in _COLS[2:14]] + [None]
    n = last + 1
    return [
        ("sheet.rename", {"name": t["sheet"]}),
        # Accounts stay text: "41.010" and "41.01" are different accounts, "31" is not 31.0
        ("home.numberFormat", {"range": f"A2:A{last}", "format": "Text"}),
        ("range.setValues", {"range": "A1", "values": rows + [total_row]}),
        ("home.numberFormat", {"range": f"C2:N{n}", "code": "#,##0.00"}),
        ("home.bold", {"range": f"A1:O1"}),
        ("home.bold", {"range": f"A{n}:O{n}"}),
        ("home.conditionalFormat", {"range": f"K2:N{last}", "rule": {
            "type": "cellIs", "operator": "notBetween", "value": f"-{TOLERANCE}", "value2": f"{TOLERANCE}",
            "preset": "lightRedFillDarkRedText"}}),
        ("home.conditionalFormat", {"range": f"O2:O{last}", "rule": {
            "type": "cellIs", "operator": "equal", "value": f'"{t["bad"]}"', "preset": "lightRedFillDarkRedText"}}),
        ("home.conditionalFormat", {"range": f"O2:O{last}", "rule": {
            "type": "cellIs", "operator": "equal", "value": f'"{t["ok"]}"', "preset": "greenFill"}}),
        ("view.freezeTopRow", {}),
        ("home.autofitColumnWidth", {"range": f"A1:O{n}"}),
    ]


def write_reconciliation(diffs: list[Diff], out: Path | str, left_label: str = "1C",
                         right_label: str = "Odoo", lang: str = "ru", gc: GridCraft | None = None) -> Path:
    gc = gc or GridCraft()
    gc.run(build_steps(diffs, left_label, right_label, lang), out=out)
    return Path(out)
