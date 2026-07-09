"""
Sprint 12 tests — Query Engine extension + ERP Dashboard.
Covers: AttachDB, path validation, WAL, type inference, REST endpoints.
"""
from __future__ import annotations
import os
import sqlite3
import tempfile
import threading
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent


def _make_erp_db(tmp_path: Path) -> str:
    """Create a minimal erp.db with org_nodes + budget_allocations + payroll_results."""
    db_path = tmp_path / "erp.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS org_nodes (
            id TEXT, name TEXT, type TEXT, parent_id TEXT, org_name TEXT
        );
        INSERT INTO org_nodes VALUES ('dept-01','Finance','department','root','TestCo');
        INSERT INTO org_nodes VALUES ('dept-02','IT','department','root','TestCo');

        CREATE TABLE IF NOT EXISTS budget_allocations (
            org_id TEXT, period TEXT, account TEXT, amount TEXT
        );
        INSERT INTO budget_allocations VALUES ('dept-01','2024-01','expenses','10000.00');
        INSERT INTO budget_allocations VALUES ('dept-02','2024-01','expenses','8000.00');

        CREATE TABLE IF NOT EXISTS budget_entries (
            entry_type TEXT, org_id TEXT, period TEXT,
            amount TEXT, doc_ref TEXT, account TEXT
        );
        INSERT INTO budget_entries VALUES ('consumption','dept-01','2024-01','3000.00','INV-001','expenses');
        INSERT INTO budget_entries VALUES ('consumption','dept-02','2024-01','1500.00','INV-002','expenses');

        CREATE TABLE IF NOT EXISTS payroll_results (
            period TEXT, emp_id TEXT, emp_name TEXT,
            gross TEXT, net TEXT, tax_profile TEXT
        );
        INSERT INTO payroll_results VALUES ('2024-01','e1','Alice Smith','5000.00','4200.00','us_2024');
        INSERT INTO payroll_results VALUES ('2024-01','e2','Bob Jones','4500.00','3780.00','us_2024');

        CREATE TABLE IF NOT EXISTS workflow_rules (doc_type TEXT, rules_json TEXT);
    """)
    conn.close()
    return str(db_path)


# ── TestQueryAttachDB ─────────────────────────────────────────────────────────

class TestQueryAttachDB:

    def test_attach_and_query_org_nodes(self, tmp_path):
        db = _make_erp_db(tmp_path)
        from src.runtime.query import _Query
        q = _Query("SELECT id, name FROM org_nodes WHERE id <> 'root'")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            q.AttachDB(db)
        result = q.Execute()
        assert result.Count() == 2
        names = {row[1] for row in result._rows}
        assert "Finance" in names
        assert "IT" in names

    def test_attach_query_budget(self, tmp_path):
        db = _make_erp_db(tmp_path)
        from src.runtime.query import _Query
        q = _Query("SELECT org_id, amount FROM budget_allocations ORDER BY org_id")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            q.AttachDB(db)
        result = q.Execute()
        assert result.Count() == 2

    def test_attach_query_payroll(self, tmp_path):
        db = _make_erp_db(tmp_path)
        from src.runtime.query import _Query
        q = _Query("SELECT emp_name, gross FROM payroll_results ORDER BY emp_name")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            q.AttachDB(db)
        result = q.Execute()
        assert result.Count() == 2
        cursor = result.Choose()
        cursor.Next()
        assert cursor.Value("emp_name") == "Alice Smith"

    def test_no_attach_still_works_memory(self):
        """Existing :memory: path must not break."""
        from src.runtime.query import _Query
        from src.runtime.types import _ValueTable
        vt = _ValueTable()
        vt.Columns.Add("x")
        r = vt.Add(); r["x"] = 42
        q = _Query("SELECT x FROM t")
        q.RegisterTable("t", vt)
        result = q.Execute()
        assert result.Count() == 1

    def test_chained_api(self, tmp_path):
        db = _make_erp_db(tmp_path)
        from src.runtime.query import _Query
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            result = (
                _Query("SELECT id FROM org_nodes WHERE type = :t")
                .AttachDB(db)
                .SetParam("t", "department")
                .Execute()
            )
        assert result.Count() == 2


# ── TestQueryERPJoin ─────────────────────────────────────────────────────────

class TestQueryERPJoin:

    def test_join_valuetable_with_erp_db(self, tmp_path):
        """In-memory ValueTable joined with org_nodes from erp.db."""
        db = _make_erp_db(tmp_path)
        from src.runtime.query import _Query
        from src.runtime.types import _ValueTable

        vt = _ValueTable()
        vt.Columns.Add("org_key")
        vt.Columns.Add("target_pct")
        r1 = vt.Add(); r1["org_key"] = "dept-01"; r1["target_pct"] = 85
        r2 = vt.Add(); r2["org_key"] = "dept-99"; r2["target_pct"] = 70  # no match

        q = _Query("""
            SELECT t.org_key, t.target_pct, o.name AS org_name
            FROM targets t
            LEFT JOIN org_nodes o ON o.id = t.org_key
            ORDER BY t.target_pct DESC
        """)
        q.RegisterTable("targets", vt)
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            q.AttachDB(db)
        result = q.Execute()
        assert result.Count() == 2
        cursor = result.Choose()
        cursor.Next()
        assert cursor.Value("org_name") == "Finance"
        cursor.Next()
        assert cursor.Value("org_name") is None  # LEFT JOIN — no match


# ── TestQueryPathSecurity ────────────────────────────────────────────────────

class TestQueryPathSecurity:

    def test_path_injection_raises(self):
        from src.runtime.query import _resolve_db_path
        with pytest.raises(ValueError, match="outside the allowed directory"):
            _resolve_db_path("../../etc/passwd")

    def test_traversal_dotdot_raises(self):
        from src.runtime.query import _resolve_db_path
        with pytest.raises(ValueError, match="outside the allowed directory"):
            _resolve_db_path("../secrets.db")

    def test_allowed_path_resolves(self, tmp_path):
        from src.runtime.query import _resolve_db_path, _ALLOWED_DB_DIR
        # patch allowed dir to tmp_path
        with patch("src.runtime.query._ALLOWED_DB_DIR", tmp_path):
            resolved = _resolve_db_path("erp.db")
        assert resolved == str(tmp_path / "erp.db")

    def test_allow_any_env_overrides(self, tmp_path):
        from src.runtime.query import _resolve_db_path
        external = str(tmp_path / "external.db")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            resolved = _resolve_db_path(external)
        assert resolved == external


# ── TestQueryEmptyAndCorrupt ──────────────────────────────────────────────────

class TestQueryEmptyAndCorrupt:

    def test_missing_db_returns_empty(self, tmp_path, recwarn):
        from src.runtime.query import _Query
        missing = str(tmp_path / "nonexistent.db")
        q = _Query("SELECT 1")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            q.AttachDB(missing)
        result = q.Execute()
        assert result.Count() == 0
        assert any("not found" in str(w.message) for w in recwarn.list)

    def test_corrupt_db_raises(self, tmp_path):
        from src.runtime.query import _Query
        corrupt = tmp_path / "corrupt.db"
        corrupt.write_bytes(b"this is not a sqlite database !!!")
        q = _Query("SELECT 1")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            q.AttachDB(str(corrupt))
        with pytest.raises(RuntimeError):
            q.Execute()


# ── TestQueryNoneNumeric ──────────────────────────────────────────────────────

class TestQueryNoneNumeric:

    def test_none_in_numeric_column_sum(self):
        """SUM() must work even when first row has None for a Decimal column."""
        from src.runtime.query import _Query
        from src.runtime.types import _ValueTable

        vt = _ValueTable()
        vt.Columns.Add("amt")
        r1 = vt.Add(); r1["amt"] = None
        r2 = vt.Add(); r2["amt"] = Decimal("100.00")
        r3 = vt.Add(); r3["amt"] = Decimal("200.00")

        q = _Query("SELECT SUM(amt) AS total FROM amounts")
        q.RegisterTable("amounts", vt)
        result = q.Execute()
        assert result.Count() == 1
        cursor = result.Choose()
        cursor.Next()
        assert float(cursor.Value("total") or 0) == pytest.approx(300.0)


# ── TestQueryConcurrent ───────────────────────────────────────────────────────

class TestQueryConcurrent:

    def test_concurrent_reads(self, tmp_path):
        """Two threads querying the same erp.db simultaneously must not deadlock."""
        db = _make_erp_db(tmp_path)
        errors = []

        def run():
            from src.runtime.query import _Query
            try:
                q = _Query("SELECT COUNT(*) AS n FROM org_nodes")
                q.AttachDB(db)
                result = q.Execute()
                cursor = result.Choose()
                cursor.Next()
                assert int(cursor.Value("n") or 0) >= 2
            except Exception as exc:
                errors.append(exc)

        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            threads = [threading.Thread(target=run) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
        assert not errors, f"Concurrent query errors: {errors}"


# ── TestQueryTrilingualAliases ────────────────────────────────────────────────

class TestQueryTrilingualAliases:

    def test_russian_aliases(self, tmp_path):
        db = _make_erp_db(tmp_path)
        from src.runtime.query import Запрос
        з = Запрос("SELECT id FROM org_nodes LIMIT 1")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            з.ПрисоединитьБД(db)
        result = з.Выполнить()
        assert result.Count() >= 1

    def test_ukrainian_aliases(self, tmp_path):
        db = _make_erp_db(tmp_path)
        from src.runtime.query import Запит
        з = Запит("SELECT id FROM org_nodes LIMIT 1")
        with patch.dict(os.environ, {"1S_ALLOW_ANY_DB_PATH": "1"}):
            з.ПриєднатиБД(db)
        result = з.Виконати()
        assert result.Count() >= 1

    def test_query_english_alias_exists(self):
        from src.runtime.query import Query
        assert hasattr(Query, "AttachDB")
        assert hasattr(Query, "SetParam")
        assert hasattr(Query, "Execute")


# ── TestDashboardRoutes ───────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path):
    """Flask test client with a logged-in admin session."""
    os.environ["1S_DATA_DIR"] = str(tmp_path)
    from src.server import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test"
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user"] = {"display": "admin", "role": "admin"}
        yield c


class TestDashboardRoutes:

    def test_erp_dashboard_returns_200(self, client):
        resp = client.get("/erp-dashboard")
        assert resp.status_code == 200
        assert b"ERP Dashboard" in resp.data or b"erp-dashboard" in resp.data.lower()

    def test_erp_dashboard_unauthenticated(self):
        from src.server import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            resp = c.get("/erp-dashboard")
        assert resp.status_code in (302, 401)

    def test_chart_data_no_period_returns_200(self, client, tmp_path):
        """chart-data defaults to current month when no period param given."""
        resp = client.get("/api/v1/erp/chart-data")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "period" in data

    def test_chart_data_with_period(self, client):
        resp = client.get("/api/v1/erp/chart-data?period=2024-01")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["period"] == "2024-01"
        assert "budget" in data
        assert "po_spend" in data

    def test_payroll_bonus_emp_id_fix(self, client):
        """Regression: bonus must be assigned to bon['emp_id'], not ab['emp_id']."""
        payload = {
            "period": "2024-01",
            "employees": [
                {"id": "e1", "name": "Alice", "salary": 5000, "tax_profile": "us_2024"},
                {"id": "e2", "name": "Bob",   "salary": 4000, "tax_profile": "us_2024"},
            ],
            "absences": [],
            "bonuses": [
                {"emp_id": "e2", "name": "Performance", "type": "percent", "value": 10}
            ],
            "save": False,
        }
        resp = client.post(
            "/api/v1/payroll/calculate",
            json=payload,
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"]
        # Bob (e2) got the bonus — his gross should be higher than base 4000
        bob = next(r for r in data["results"] if r["emp_id"] == "e2")
        assert bob["gross"] > 4000
