"""
Linear Programming solver for 1S ERP scripts.
Backend: GLPK 5.0 (glpsol.exe) via subprocess — no scipy dependency.

Inequality constraints use >= convention (GLPK lower-bound rows).
To express A·x <= b, use AddLEConstraint(row, b) which negates internally.
"""
from __future__ import annotations

import math
import os
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── GLPK binary path ─────────────────────────────────────────────────────────

_GLPK_DEFAULT = Path(__file__).resolve().parent.parent.parent / "glpk" / "glpsol.exe"

def _glpsol_path() -> Path:
    """Resolve glpsol.exe: env override → bundled."""
    env = os.environ.get("GLPSOL_PATH")
    if env:
        return Path(env)
    if _GLPK_DEFAULT.exists():
        return _GLPK_DEFAULT
    raise FileNotFoundError(
        "glpsol.exe not found. Set GLPSOL_PATH env var or place glpsol.exe at "
        f"{_GLPK_DEFAULT}. "
        "Download GLPK 5.0 from https://sourceforge.net/projects/winglpk/"
    )


def validate_glpsol() -> bool:
    """Run a trivial 1-variable solve to confirm glpsol.exe works. Returns True on success."""
    try:
        p = _glpsol_path()
        result = subprocess.run(
            [str(p), "--version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# Semaphore: max 4 concurrent glpsol.exe processes.
_SOLVER_SEM = threading.Semaphore(4)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class LPResult:
    """Result of an LP solve."""
    status: str                          # "optimal" | "infeasible" | "unbounded" | "error"
    values: Optional[list[float]]        # decision variable values
    objective_value: Optional[float]     # c·x at solution
    shadow_prices: Optional[list[float]] # dual variables for rows (shadow prices)
    message: str                         # solver message

    # ── Trilingual attribute aliases ─────────────────────────────────────────

    @property
    def Status(self) -> str:       return self.status
    @property
    def Статус(self) -> str:       return self.status
    @property
    def Values(self) -> Optional[list[float]]:    return self.values
    @property
    def Значения(self) -> Optional[list[float]]:  return self.values
    @property
    def Значення(self) -> Optional[list[float]]:  return self.values
    @property
    def ObjectiveValue(self) -> Optional[float]:  return self.objective_value
    @property
    def ЦелевоеЗначение(self) -> Optional[float]: return self.objective_value
    @property
    def ЦільовеЗначення(self) -> Optional[float]: return self.objective_value
    @property
    def ShadowPrices(self) -> Optional[list[float]]: return self.shadow_prices
    @property
    def ТеневыеЦены(self) -> Optional[list[float]]: return self.shadow_prices
    @property
    def ТіньовіЦіни(self) -> Optional[list[float]]: return self.shadow_prices
    @property
    def Message(self) -> str:      return self.message
    @property
    def Сообщение(self) -> str:    return self.message
    @property
    def Повідомлення(self) -> str: return self.message

    def __repr__(self) -> str:
        return (
            f"LPResult(status={self.status!r}, "
            f"objective={self.objective_value}, "
            f"values={self.values})"
        )


# ── LP format writer ──────────────────────────────────────────────────────────

def _write_lp(
    c: list[float],
    direction: str,
    ineq_rows: list[tuple[list[float], float]],
    eq_rows: list[tuple[list[float], float]],
    bounds: Optional[list[tuple[Optional[float], Optional[float]]]],
) -> str:
    """Serialize the LP problem to CPLEX LP format text."""
    n = len(c)
    varnames = [f"x{i+1}" for i in range(n)]

    def _row_str(coeffs: list[float], name: str) -> str:
        terms = []
        for i, a in enumerate(coeffs):
            if a == 0.0:
                continue
            sign = "+" if a >= 0 else "-"
            val = abs(a)
            coef_str = f"{val} {varnames[i]}" if val != 1.0 else varnames[i]
            terms.append(f"{sign} {coef_str}")
        if not terms:
            return f" {name}: 0"
        return f" {name}: " + " ".join(terms)

    lines = []
    dir_kw = "Minimize" if direction == "minimize" else "Maximize"
    lines.append(dir_kw)

    obj_terms = []
    for i, ci in enumerate(c):
        if ci == 0.0:
            continue
        sign = "+" if ci >= 0 else "-"
        val = abs(ci)
        coef_str = f"{val} {varnames[i]}" if val != 1.0 else varnames[i]
        obj_terms.append(f"{sign} {coef_str}")
    obj_str = " obj: " + (" ".join(obj_terms) if obj_terms else "0")
    lines.append(obj_str)

    lines.append("Subject To")
    for idx, (row, rhs) in enumerate(ineq_rows):
        lines.append(_row_str(row, f"ie{idx+1}") + f" >= {rhs}")
    for idx, (row, rhs) in enumerate(eq_rows):
        lines.append(_row_str(row, f"eq{idx+1}") + f" = {rhs}")

    lines.append("Bounds")
    for i in range(n):
        lo, hi = None, None
        if bounds and i < len(bounds):
            lo, hi = bounds[i]
        lo_str = str(lo) if lo is not None else "-Inf"
        hi_str = str(hi) if hi is not None else "+Inf"
        lines.append(f" {lo_str} <= {varnames[i]} <= {hi_str}")

    lines.append("End")
    return "\n".join(lines)


# ── Solution file parser ──────────────────────────────────────────────────────

def _parse_solution(sol_text: str) -> tuple[str, Optional[list[float]], Optional[float], Optional[list[float]]]:
    """Parse glpsol -w plain-text solution file.

    Returns (status, values, objective, shadow_prices).
    Solution file format:
      s bas <nrows> <ncols> <f|t> <f|t> <obj_value>
      i <row_num> <status> <activity> <marginal>
      j <col_num> <status> <activity> <marginal>
    """
    status = "error"
    obj = None
    col_values: dict[int, float] = {}
    row_marginals: dict[int, float] = {}

    for line in sol_text.splitlines():
        line = line.strip()
        if not line or line.startswith("c "):
            continue
        parts = line.split()
        if parts[0] == "s":
            # s bas nrows ncols feasible_row feasible_col obj
            # status flags: f=feasible, t=infeasible/unbounded
            # GLPK uses: s bas 2 3 f f 18 for optimal
            obj_str = parts[6] if len(parts) > 6 else None
            feasible_row = parts[4] if len(parts) > 4 else "t"
            feasible_col = parts[5] if len(parts) > 5 else "t"
            if feasible_row == "f" and feasible_col == "f" and obj_str:
                try:
                    obj = float(obj_str)
                    status = "optimal"
                except ValueError:
                    status = "error"
            elif feasible_row == "t":
                status = "infeasible"
            elif feasible_col == "t":
                status = "unbounded"
        elif parts[0] == "j":
            # j col_num status activity marginal
            col_num = int(parts[1])
            try:
                col_values[col_num] = float(parts[3])
            except (ValueError, IndexError):
                col_values[col_num] = 0.0
        elif parts[0] == "i":
            # i row_num status activity marginal
            row_num = int(parts[1])
            try:
                row_marginals[row_num] = float(parts[4]) if len(parts) > 4 else 0.0
            except (ValueError, IndexError):
                row_marginals[row_num] = 0.0

    if status == "optimal" and col_values:
        n = max(col_values.keys())
        raw_values = [col_values.get(i+1, 0.0) for i in range(n)]
        # Guard against +Inf/-Inf which would crash json.dumps
        if not all(math.isfinite(v) for v in raw_values):
            return "error", None, None, None
        m = max(row_marginals.keys()) if row_marginals else 0
        shadow = [row_marginals.get(i+1, 0.0) for i in range(m)]
        return status, raw_values, obj, shadow

    return status, None, None, None


# ── LPSolver ──────────────────────────────────────────────────────────────────

class LPSolver:
    """Trilingual LP solver backed by GLPK 5.0 glpsol.exe."""

    _MAX_VARS = 500
    _MAX_CONSTRAINTS = 1000

    def __init__(self) -> None:
        self._c: list[float] = []
        self._direction: str = "minimize"
        self._ineq: list[tuple[list[float], float]] = []
        self._eq: list[tuple[list[float], float]] = []
        self._bounds: Optional[list[tuple[Optional[float], Optional[float]]]] = None

    # ── Objective ─────────────────────────────────────────────────────────────

    def Minimize(self, coefficients: list) -> "LPSolver":
        self._c = [float(x) for x in coefficients]
        self._direction = "minimize"
        return self

    def Maximize(self, coefficients: list) -> "LPSolver":
        self._c = [float(x) for x in coefficients]
        self._direction = "maximize"
        return self

    # RU aliases
    Минимизировать = Minimize
    Максимизировать = Maximize
    # UK aliases
    Мінімізувати = Minimize
    Максимізувати = Maximize

    # ── Constraints ───────────────────────────────────────────────────────────

    def AddInequalityConstraint(self, row: list, rhs: float) -> "LPSolver":
        """Add A·x ≥ rhs inequality (GLPK lower-bound row).
        Note: direction is >= (greater-than-or-equal).
        To express A·x <= rhs, use AddLEConstraint instead.
        """
        self._ineq.append(([float(x) for x in row], float(rhs)))
        return self

    def AddLEConstraint(self, row: list, rhs: float) -> "LPSolver":
        """Add A·x <= rhs (less-than-or-equal). Negates internally to fit >= convention."""
        negated = [-float(x) for x in row]
        self._ineq.append((negated, -float(rhs)))
        return self

    def AddEqualityConstraint(self, row: list, rhs: float) -> "LPSolver":
        self._eq.append(([float(x) for x in row], float(rhs)))
        return self

    # RU aliases
    ДобавитьОграничениеНеравенство = AddInequalityConstraint
    ДобавитьОграничениеРавенство = AddEqualityConstraint
    ДобавитьОграничениеНеравенствоLE = AddLEConstraint
    # UK aliases
    ДодатиОбмеженняНерівності = AddInequalityConstraint
    ДодатиОбмеженняРівності = AddEqualityConstraint
    ДодатиОбмеженняНерівностіLE = AddLEConstraint

    # ── Bounds ────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_bound(v):
        if v is None or not isinstance(v, (int, float)):
            return None
        return float(v)

    def SetBounds(self, bounds: list) -> "LPSolver":
        """Set per-variable bounds: list of [lo, hi] pairs. None/Undefined = unbounded."""
        self._bounds = [
            (self._to_bound(b[0]), self._to_bound(b[1]))
            for b in bounds
        ]
        return self

    def AddBound(self, lo, hi) -> "LPSolver":
        """Append a single variable bound [lo, hi]. Call once per variable in order.
        Pass None or Undefined (1S) for unbounded side."""
        if self._bounds is None:
            self._bounds = []
        lo_v = None if (lo is None or not isinstance(lo, (int, float))) else float(lo)
        hi_v = None if (hi is None or not isinstance(hi, (int, float))) else float(hi)
        self._bounds.append((lo_v, hi_v))
        return self

    # RU/UK aliases
    УстановитьГраницы = SetBounds
    ВстановитиМежі = SetBounds
    ДобавитьГраницу = AddBound
    ДодатиМежу = AddBound

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self) -> None:
        if not self._c:
            raise ValueError("Objective coefficients are empty — call Minimize() or Maximize() first")
        n = len(self._c)
        if n > self._MAX_VARS:
            raise ValueError(f"Problem has {n} variables; maximum allowed is {self._MAX_VARS}")
        total_constraints = len(self._ineq) + len(self._eq)
        if total_constraints > self._MAX_CONSTRAINTS:
            raise ValueError(
                f"Problem has {total_constraints} constraints; maximum allowed is {self._MAX_CONSTRAINTS}"
            )
        for idx, (row, _) in enumerate(self._ineq):
            if len(row) != n:
                raise ValueError(
                    f"Row length mismatch: objective has {n} variables, "
                    f"inequality constraint {idx+1} has {len(row)}"
                )
        for idx, (row, _) in enumerate(self._eq):
            if len(row) != n:
                raise ValueError(
                    f"Row length mismatch: objective has {n} variables, "
                    f"equality constraint {idx+1} has {len(row)}"
                )

    # ── Solve ─────────────────────────────────────────────────────────────────

    def Solve(self) -> LPResult:
        """Run glpsol.exe and return LPResult."""
        self._validate()

        lp_text = _write_lp(
            self._c, self._direction,
            self._ineq, self._eq, self._bounds,
        )

        try:
            glpsol = _glpsol_path()
        except FileNotFoundError as exc:
            return LPResult(
                status="error", values=None, objective_value=None,
                shadow_prices=None, message=str(exc),
            )

        acquired = _SOLVER_SEM.acquire(timeout=10)
        if not acquired:
            return LPResult(
                status="error", values=None, objective_value=None,
                shadow_prices=None, message="Solver busy — too many concurrent solves, try again",
            )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                lp_file = os.path.join(tmpdir, "problem.lp")
                sol_file = os.path.join(tmpdir, "solution.txt")
                with open(lp_file, "w", encoding="ascii") as f:
                    f.write(lp_text)

                direction_flag = "--min" if self._direction == "minimize" else "--max"
                cmd = [
                    str(glpsol),
                    "--lp", lp_file,
                    direction_flag,
                    "-w", sol_file,
                ]

                try:
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired:
                    return LPResult(
                        status="error", values=None, objective_value=None,
                        shadow_prices=None, message="Solver timed out after 60 seconds",
                    )
                except Exception as exc:
                    return LPResult(
                        status="error", values=None, objective_value=None,
                        shadow_prices=None, message=str(exc),
                    )

                # Determine status from stdout even if sol_file is missing
                stdout = proc.stdout + proc.stderr
                glpk_status = "error"
                glpk_message = stdout.strip().splitlines()[-1] if stdout.strip() else "No output"

                if "OPTIMAL LP SOLUTION FOUND" in stdout:
                    glpk_status = "optimal"
                elif "PROBLEM HAS NO FEASIBLE SOLUTION" in stdout or "INFEASIBLE" in stdout:
                    glpk_status = "infeasible"
                elif "PROBLEM HAS UNBOUNDED SOLUTION" in stdout or "UNBOUNDED" in stdout:
                    glpk_status = "unbounded"

                if not os.path.exists(sol_file):
                    return LPResult(
                        status=glpk_status, values=None, objective_value=None,
                        shadow_prices=None, message=glpk_message,
                    )

                with open(sol_file, encoding="ascii") as f:
                    sol_text = f.read()

            status, values, obj, shadow = _parse_solution(sol_text)

            # For maximize: glpsol maximizes natively via --max, obj is already positive
            return LPResult(
                status=status,
                values=values,
                objective_value=obj,
                shadow_prices=shadow,
                message=glpk_message,
            )
        finally:
            _SOLVER_SEM.release()

    # RU/UK/EN aliases
    Решить = Solve
    Вирішити = Solve


# ── ERP LP helpers ────────────────────────────────────────────────────────────

class BudgetAllocator:
    """Optimize budget reallocation across org units using LP.

    Reads budget_allocations and budget_entries from erp.db.
    Formulates: maximize Σ weights[i] * x[i]
                s.t.     x[i] ≤ amount[i]
                         Σ x[i] ≤ total_remaining
                         x[i] ≥ consumed[i]
    """

    def __init__(self, db_path: str, period: str) -> None:
        self._db_path = db_path
        self._period = period
        self._weights: dict[str, float] = {}

    def SetWeights(self, weights: dict) -> "BudgetAllocator":
        self._weights = {k: float(v) for k, v in weights.items()}
        return self

    УстановитьВеса = SetWeights
    ВстановитиВаги = SetWeights

    def Optimize(self) -> LPResult:
        import sqlite3
        try:
            conn = sqlite3.connect(self._db_path)
            allocations = conn.execute(
                "SELECT org_id, SUM(CAST(amount AS REAL)) "
                "FROM budget_allocations WHERE period=? GROUP BY org_id",
                (self._period,)
            ).fetchall()
            consumed = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT org_id, SUM(CAST(amount AS REAL)) "
                    "FROM budget_entries WHERE period=? AND entry_type='consumption' GROUP BY org_id",
                    (self._period,)
                ).fetchall()
            }
            conn.close()
        except Exception as exc:
            return LPResult(
                status="error", values=None, objective_value=None,
                shadow_prices=None, message=str(exc),
            )

        if not allocations:
            return LPResult(
                status="error", values=None, objective_value=None,
                shadow_prices=None, message=f"No budget data for period {self._period}",
            )

        org_ids = [r[0] for r in allocations]
        alloc_amounts = [r[1] for r in allocations]
        consume_amounts = [consumed.get(oid, 0.0) for oid in org_ids]
        weights = [self._weights.get(oid, 1.0) for oid in org_ids]
        total_remaining = sum(
            max(0.0, a - c) for a, c in zip(alloc_amounts, consume_amounts)
        )

        solver = LPSolver()
        solver.Maximize(weights)
        # x[i] ≤ allocated[i]  →  as >= constraint on -x: -x[i] >= -alloc
        for i, alloc in enumerate(alloc_amounts):
            row = [0.0] * len(org_ids)
            row[i] = 1.0
            solver.AddInequalityConstraint([-v for v in row], -alloc)
        # x[i] ≥ consumed[i]
        for i, cons in enumerate(consume_amounts):
            row = [0.0] * len(org_ids)
            row[i] = 1.0
            solver.AddInequalityConstraint(row, cons)
        # Σ x[i] ≤ total_remaining  → -Σ x[i] >= -total_remaining
        solver.AddInequalityConstraint([-1.0] * len(org_ids), -total_remaining)
        solver.SetBounds([[0.0, None]] * len(org_ids))

        result = solver.Solve()
        # Attach org_id labels as metadata for ERP callers
        result._org_ids = org_ids
        return result

    Оптимизировать = Optimize
    Оптимізувати = Optimize


class ResourceAllocator:
    """Transportation LP: assign resources to tasks minimizing total cost.

    Default cost = 1 (equal cost). Call SetCost(resource, task, cost) to customize.
    """

    def __init__(self) -> None:
        self._resources: list[tuple[str, float]] = []
        self._tasks: list[tuple[str, float]] = []
        self._costs: dict[tuple[str, str], float] = {}

    def AddResource(self, name: str, capacity: float) -> "ResourceAllocator":
        self._resources.append((name, float(capacity)))
        return self

    def AddTask(self, name: str, demand: float) -> "ResourceAllocator":
        self._tasks.append((name, float(demand)))
        return self

    def SetCost(self, resource: str, task: str, cost: float) -> "ResourceAllocator":
        self._costs[(resource, task)] = float(cost)
        return self

    ДобавитьРесурс = AddResource
    ДодатиРесурс = AddResource
    ДобавитьЗадачу = AddTask
    ДодатиЗадачу = AddTask
    УстановитьСтоимость = SetCost
    ВстановитиВартість = SetCost

    def Solve(self) -> LPResult:
        R = len(self._resources)
        T = len(self._tasks)
        n = R * T  # decision vars: x[i*T + j] = hours from resource i to task j

        # Objective: minimize total cost
        c = []
        for i, (rname, _) in enumerate(self._resources):
            for j, (tname, _) in enumerate(self._tasks):
                c.append(self._costs.get((rname, tname), 1.0))

        solver = LPSolver()
        solver.Minimize(c)

        # Supply constraints: Σ_j x[i,j] ≤ capacity[i]
        for i, (_, cap) in enumerate(self._resources):
            row = [0.0] * n
            for j in range(T):
                row[i * T + j] = -1.0
            solver.AddInequalityConstraint(row, -cap)

        # Demand constraints: Σ_i x[i,j] ≥ demand[j]
        for j, (_, dem) in enumerate(self._tasks):
            row = [0.0] * n
            for i in range(R):
                row[i * T + j] = 1.0
            solver.AddInequalityConstraint(row, dem)

        solver.SetBounds([[0.0, None]] * n)
        result = solver.Solve()
        result._resource_names = [r[0] for r in self._resources]
        result._task_names = [t[0] for t in self._tasks]
        return result

    Решить = Solve
    Вирішити = Solve


# ── Module-level constructor functions ───────────────────────────────────────

def НовыйСолвер() -> LPSolver:      return LPSolver()
def НовийСолвер() -> LPSolver:      return LPSolver()
def NewSolver() -> LPSolver:        return LPSolver()

def НовыйАллокаторБюджета(db: str, period: str) -> BudgetAllocator:
    return BudgetAllocator(db, period)
def НовийАллокаторБюджету(db: str, period: str) -> BudgetAllocator:
    return BudgetAllocator(db, period)
def NewBudgetAllocator(db: str, period: str) -> BudgetAllocator:
    return BudgetAllocator(db, period)

def НовыйАллокаторРесурсов() -> ResourceAllocator:    return ResourceAllocator()
def НовийАллокаторРесурсів() -> ResourceAllocator:    return ResourceAllocator()
def NewResourceAllocator() -> ResourceAllocator:       return ResourceAllocator()
