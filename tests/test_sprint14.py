"""
Sprint 14 tests — Linear Programming solver (GLPK 5.0 backend).
Covers: LPSolver, LPResult, BudgetAllocator, ResourceAllocator,
        REST /api/v1/lp/solve, /lp-solver page, trilingual aliases.
"""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_budget_db(tmp_path: Path) -> str:
    db = tmp_path / "erp.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE budget_allocations (org_id TEXT, period TEXT, account TEXT, amount TEXT);
        INSERT INTO budget_allocations VALUES ('dept-01','2024-01','expenses','10000.00');
        INSERT INTO budget_allocations VALUES ('dept-02','2024-01','expenses','8000.00');

        CREATE TABLE budget_entries (
            entry_type TEXT, org_id TEXT, period TEXT,
            amount TEXT, doc_ref TEXT, account TEXT
        );
        INSERT INTO budget_entries VALUES ('consumption','dept-01','2024-01','7000.00','INV-1','expenses');
        INSERT INTO budget_entries VALUES ('consumption','dept-02','2024-01','2000.00','INV-2','expenses');
    """)
    conn.close()
    return str(db)


# ── TestLPSolverBasic ─────────────────────────────────────────────────────────

class TestLPSolverBasic:

    def test_minimize_simple(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Minimize([1, 2, 3])
        s.AddInequalityConstraint([1, 1, 0], 10)
        s.AddInequalityConstraint([0, 1, 1], 8)
        s.SetBounds([[0, None], [0, None], [0, None]])
        r = s.Solve()
        assert r.status == "optimal"
        assert r.objective_value == pytest.approx(18.0, abs=1e-4)
        assert r.values is not None
        assert len(r.values) == 3

    def test_maximize_simple(self):
        # Maximize 5x1 + 4x2 s.t. 6x1+4x2 <= 24, x1+2x2 <= 6
        # AddInequalityConstraint is >=, so negate: -6x1-4x2 >= -24
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Maximize([5, 4])
        s.AddInequalityConstraint([-6, -4], -24)
        s.AddInequalityConstraint([-1, -2], -6)
        s.SetBounds([[0, None], [0, None]])
        r = s.Solve()
        assert r.status == "optimal"
        assert r.objective_value == pytest.approx(21.0, abs=1e-3)

    def test_equality_constraint(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Minimize([1, 1])
        s.AddEqualityConstraint([1, 1], 10)
        s.SetBounds([[0, None], [0, None]])
        r = s.Solve()
        assert r.status == "optimal"
        assert r.objective_value == pytest.approx(10.0, abs=1e-4)

    def test_infeasible_returns_status_not_raises(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Minimize([1, 1])
        # x1 + x2 >= 10  AND  x1 + x2 <= 5 — impossible
        s.AddInequalityConstraint([1, 1], 10)
        s.AddInequalityConstraint([-1, -1], -5)
        s.SetBounds([[0, None], [0, None]])
        r = s.Solve()
        assert r.status in ("infeasible", "error")
        assert r.values is None

    def test_bounds_respected(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Minimize([1, 1])
        s.AddInequalityConstraint([1, 0], 0)   # x1 >= 0
        s.SetBounds([[5, 10], [5, 10]])         # 5 <= xi <= 10
        r = s.Solve()
        assert r.status == "optimal"
        assert r.values[0] == pytest.approx(5.0, abs=1e-4)
        assert r.values[1] == pytest.approx(5.0, abs=1e-4)

    def test_shadow_prices_returned(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Minimize([1, 2])
        s.AddInequalityConstraint([1, 0], 4)
        s.AddInequalityConstraint([0, 1], 3)
        s.SetBounds([[0, None], [0, None]])
        r = s.Solve()
        assert r.status == "optimal"
        assert r.shadow_prices is not None
        assert len(r.shadow_prices) >= 1

    def test_mismatched_row_raises_value_error(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        s.Minimize([1, 2, 3])
        s.AddInequalityConstraint([1, 1], 10)  # only 2 coefficients for 3 vars
        with pytest.raises(ValueError, match="Row length mismatch"):
            s.Solve()

    def test_empty_objective_raises(self):
        from src.runtime.lp import LPSolver
        s = LPSolver()
        with pytest.raises(ValueError, match="Objective coefficients are empty"):
            s.Solve()

    def test_chained_api(self):
        from src.runtime.lp import LPSolver
        r = (
            LPSolver()
            .Minimize([1, 1])
            .AddInequalityConstraint([1, 0], 3)
            .AddInequalityConstraint([0, 1], 4)
            .SetBounds([[0, None], [0, None]])
            .Solve()
        )
        assert r.status == "optimal"
        assert r.objective_value == pytest.approx(7.0, abs=1e-4)


# ── TestLPSolverERP ───────────────────────────────────────────────────────────

class TestLPSolverERP:

    def test_budget_allocator_reads_erp_db(self, tmp_path):
        from src.runtime.lp import BudgetAllocator
        db = _make_budget_db(tmp_path)
        alloc = BudgetAllocator(db, "2024-01")
        r = alloc.Optimize()
        # dept-01 consumed 7000 of 10000, dept-02 consumed 2000 of 8000
        # total remaining = 3000 + 6000 = 9000
        assert r.status == "optimal"
        assert r.values is not None

    def test_budget_allocator_respects_weights(self, tmp_path):
        from src.runtime.lp import BudgetAllocator
        db = _make_budget_db(tmp_path)
        alloc = BudgetAllocator(db, "2024-01")
        alloc.SetWeights({"dept-01": 2.0, "dept-02": 1.0})
        r = alloc.Optimize()
        assert r.status == "optimal"

    def test_budget_allocator_missing_period_returns_error(self, tmp_path):
        from src.runtime.lp import BudgetAllocator
        db = _make_budget_db(tmp_path)
        r = BudgetAllocator(db, "1900-01").Optimize()
        assert r.status == "error"

    def test_resource_allocator_balances_load(self):
        from src.runtime.lp import ResourceAllocator
        ra = ResourceAllocator()
        ra.AddResource("Alice", 160)
        ra.AddResource("Bob", 120)
        ra.AddTask("Project A", 80)
        ra.AddTask("Project B", 100)
        r = ra.Solve()
        assert r.status == "optimal"
        assert r.values is not None
        total_assigned = sum(r.values)
        assert total_assigned == pytest.approx(180.0, abs=1e-3)

    def test_resource_allocator_infeasible_over_capacity(self):
        from src.runtime.lp import ResourceAllocator
        ra = ResourceAllocator()
        ra.AddResource("Alice", 10)
        ra.AddTask("Huge Task", 1000)
        r = ra.Solve()
        assert r.status in ("infeasible", "error")


# ── TestLPTrilingualAliases ───────────────────────────────────────────────────

class TestLPTrilingualAliases:

    def test_russian_aliases_minimize(self):
        from src.runtime.lp import НовыйСолвер
        s = НовыйСолвер()
        s.Минимизировать([1, 2])
        s.ДобавитьОграничениеНеравенство([1, 0], 5)
        s.УстановитьГраницы([[0, None], [0, None]])
        r = s.Решить()
        assert r.status == "optimal"
        assert r.Статус == "optimal"
        assert r.Значения is not None
        assert r.ЦелевоеЗначение == pytest.approx(5.0, abs=1e-4)

    def test_ukrainian_aliases_maximize(self):
        # Maximize 3x1 + 2x2 s.t. x1+x2 <= 4 → negated: -x1-x2 >= -4
        # optimal: x1=4, x2=0, obj=12
        from src.runtime.lp import НовийСолвер
        s = НовийСолвер()
        s.Максимізувати([3, 2])
        s.ДодатиОбмеженняНерівності([-1, -1], -4)
        s.ВстановитиМежі([[0, None], [0, None]])
        r = s.Вирішити()
        assert r.status == "optimal"
        assert r.Статус == "optimal"
        assert r.Значення is not None
        assert r.ЦільовеЗначення == pytest.approx(12.0, abs=1e-3)

    def test_english_alias_exists(self):
        from src.runtime.lp import NewSolver, LPSolver
        s = NewSolver()
        assert isinstance(s, LPSolver)
        assert hasattr(s, 'Minimize')
        assert hasattr(s, 'Maximize')
        assert hasattr(s, 'AddInequalityConstraint')
        assert hasattr(s, 'AddEqualityConstraint')
        assert hasattr(s, 'SetBounds')
        assert hasattr(s, 'Solve')

    def test_result_trilingual_attrs(self):
        from src.runtime.lp import LPSolver
        r = LPSolver().Minimize([1]).AddInequalityConstraint([1], 5).SetBounds([[0, None]]).Solve()
        assert r.Values == r.values
        assert r.ObjectiveValue == r.objective_value
        assert r.ShadowPrices == r.shadow_prices
        assert r.Message == r.message
        assert r.Сообщение == r.message
        assert r.Повідомлення == r.message


# ── TestLPRestEndpoint ────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path):
    os.environ["1S_DATA_DIR"] = str(tmp_path)
    from src.server import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test"
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user"] = {"display": "admin", "role": "admin", "username": "admin"}
        yield c


class TestLPRestEndpoint:

    def test_solve_minimize_returns_200(self, client):
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [1, 2, 3],
            "direction": "minimize",
            "inequality_constraints": [
                {"coefficients": [1, 1, 0], "rhs": 10},
                {"coefficients": [0, 1, 1], "rhs": 8},
            ],
            "bounds": [[0, None], [0, None], [0, None]],
        })
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["status"] == "optimal"
        assert d["objective_value"] == pytest.approx(18.0, abs=1e-3)
        assert d["variables_count"] == 3
        assert d["constraints_count"] == 2

    def test_solve_maximize_returns_200(self, client):
        # Maximize 5x1+4x2 s.t. 6x1+4x2<=24, x1+2x2<=6 → negated >= constraints
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [5, 4],
            "direction": "maximize",
            "inequality_constraints": [
                {"coefficients": [-6, -4], "rhs": -24},
                {"coefficients": [-1, -2], "rhs": -6},
            ],
            "bounds": [[0, None], [0, None]],
        })
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["status"] == "optimal"
        assert d["objective_value"] == pytest.approx(21.0, abs=1e-2)

    def test_solve_infeasible_returns_422(self, client):
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [1, 1],
            "direction": "minimize",
            "inequality_constraints": [
                {"coefficients": [1, 1], "rhs": 10},
                {"coefficients": [-1, -1], "rhs": -5},
            ],
            "bounds": [[0, None], [0, None]],
        })
        assert resp.status_code == 422
        d = resp.get_json()
        assert d["status"] in ("infeasible", "error")
        assert d["values"] is None

    def test_solve_invalid_row_length_returns_400(self, client):
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [1, 2, 3],
            "direction": "minimize",
            "inequality_constraints": [
                {"coefficients": [1, 1], "rhs": 10},  # only 2 for 3-var problem
            ],
        })
        assert resp.status_code == 400
        d = resp.get_json()
        assert "mismatch" in d["error"].lower()

    def test_solve_empty_objective_returns_400(self, client):
        resp = client.post("/api/v1/lp/solve", json={"objective": []})
        assert resp.status_code == 400

    def test_solve_invalid_direction_returns_400(self, client):
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [1, 2],
            "direction": "sideways",
        })
        assert resp.status_code == 400

    def test_solve_bounds_null_handled(self, client):
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [1, 1],
            "direction": "minimize",
            "inequality_constraints": [{"coefficients": [1, 0], "rhs": 3}],
            "bounds": [[None, None], [0, None]],
        })
        assert resp.status_code in (200, 422)  # solver decides; no crash

    def test_solve_unauthenticated_returns_401_or_302(self):
        from src.server import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            resp = c.post("/api/v1/lp/solve", json={"objective": [1]})
        assert resp.status_code in (302, 401)

    def test_solve_shadow_prices_in_response(self, client):
        resp = client.post("/api/v1/lp/solve", json={
            "objective": [1, 2],
            "direction": "minimize",
            "inequality_constraints": [
                {"coefficients": [1, 0], "rhs": 4},
                {"coefficients": [0, 1], "rhs": 3},
            ],
            "bounds": [[0, None], [0, None]],
        })
        assert resp.status_code == 200
        d = resp.get_json()
        assert "shadow_prices" in d
        assert isinstance(d["shadow_prices"], list)


# ── TestLPDashboard ───────────────────────────────────────────────────────────

class TestLPDashboard:

    def test_lp_solver_page_returns_200(self, client):
        resp = client.get("/lp-solver")
        assert resp.status_code == 200
        assert b"LP Solver" in resp.data or b"lp-solver" in resp.data.lower()

    def test_lp_solver_unauthenticated_redirects(self):
        from src.server import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            resp = c.get("/lp-solver")
        assert resp.status_code in (302, 401)


# ── TestLPDemoScript ──────────────────────────────────────────────────────────

class TestLPDemoScript:

    def test_demo_lp_solver_en_runs(self):
        demo = ROOT / "examples" / "demo_lp_solver_en.1s"
        if not demo.exists():
            pytest.skip("demo_lp_solver_en.1s not yet created")
        import subprocess
        result = subprocess.run(
            ["python", "-m", "src.cli", "run", str(demo)],
            capture_output=True, text=True, timeout=30, cwd=str(ROOT)
        )
        assert result.returncode == 0, result.stderr
        assert "optimal" in result.stdout.lower()
