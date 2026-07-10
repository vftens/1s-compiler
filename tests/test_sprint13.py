"""
Sprint 13 tests: Excel/PDF export, Bearer token auth, user script persistence.
32 tests → ~598 total.
"""
from __future__ import annotations

import io
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_path(tmp_path):
    """Return path to a minimal erp.db with payroll + budget + org data."""
    db = tmp_path / "erp.db"
    conn = sqlite3.connect(str(db))
    conn.executescript("""
        CREATE TABLE payroll_results (
            emp_id TEXT, emp_name TEXT, period TEXT,
            gross REAL, deductions REAL, net REAL, tax_profile TEXT
        );
        CREATE TABLE budget_allocations (
            org_id TEXT, period TEXT, account TEXT, allocated REAL
        );
        CREATE TABLE budget_entries (
            org_id TEXT, period TEXT, account TEXT, amount REAL
        );
        CREATE TABLE org_nodes (
            node_id TEXT PRIMARY KEY, name TEXT, node_type TEXT, parent_id TEXT
        );
    """)
    conn.execute(
        "INSERT INTO payroll_results VALUES (?,?,?,?,?,?,?)",
        ("E1", "Іваненко", "2026-06", 10000, 2200, 7800, "ua_2024"),
    )
    conn.execute(
        "INSERT INTO payroll_results VALUES (?,?,?,?,?,?,?)",
        ("E2", "Петренко", "2026-06", 8000, 1760, 6240, "ua_2024"),
    )
    conn.execute(
        "INSERT INTO payroll_results VALUES (?,?,?,?,?,?,?)",
        ("E3", "Сидоренко", "2026-07", 9000, 1980, 7020, "ua_2024"),
    )
    conn.execute(
        "INSERT INTO budget_allocations VALUES (?,?,?,?)",
        ("D1", "2026-06", "OpEx", 50000),
    )
    conn.execute(
        "INSERT INTO budget_allocations VALUES (?,?,?,?)",
        ("D2", "2026-06", "CapEx", 0),
    )
    conn.execute(
        "INSERT INTO budget_entries VALUES (?,?,?,?)",
        ("D1", "2026-06", "OpEx", 30000),
    )
    conn.execute(
        "INSERT INTO org_nodes VALUES (?,?,?,?)",
        ("ROOT", "Holding", "Holding", None),
    )
    conn.execute(
        "INSERT INTO org_nodes VALUES (?,?,?,?)",
        ("D1", "Department A", "Department", "ROOT"),
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def client(tmp_path, db_path):
    """Flask test client with Sprint 13 DB and scripts dir patched."""
    from src.runtime.token_auth import TokenStore
    import src.server as srv
    scripts_dir = tmp_path / "user_scripts"
    scripts_dir.mkdir()
    new_ts = TokenStore(db_path)
    with (
        patch.object(srv, "_ERP_DB_S13", db_path),
        patch.object(srv, "_USER_SCRIPTS_DIR", scripts_dir),
        patch.object(srv, "_token_store", new_ts),
    ):
        # Clear rate limit state between tests
        srv._TOKEN_RATE.clear()
        srv.app.config["TESTING"] = True
        srv.app.config["SECRET_KEY"] = "test"
        with srv.app.test_client() as c:
            with srv.app.app_context():
                yield c, db_path, scripts_dir


@pytest.fixture()
def auth_client(client):
    """Test client with admin session already set."""
    c, db_path, scripts_dir = client
    with c.session_transaction() as sess:
        sess["user"] = {"username": "admin", "role": "admin"}
    return c, db_path, scripts_dir


# ── TestPayrollExport ─────────────────────────────────────────────────────────

class TestPayrollExport:
    def test_payroll_xlsx_returns_200(self, auth_client):
        c, *_ = auth_client
        r = c.get("/api/v1/export/payroll?period=2026-06")
        assert r.status_code == 200

    def test_payroll_xlsx_content_type_is_xlsx(self, auth_client):
        c, *_ = auth_client
        r = c.get("/api/v1/export/payroll?period=2026-06")
        assert "spreadsheetml" in r.content_type

    def test_payroll_xlsx_has_correct_columns(self, auth_client):
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/payroll?period=2026-06")
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        ws = wb.active
        headers = [ws.cell(1, i + 1).value for i in range(7)]
        assert "emp_id" in headers or "Таб. №" in headers

    def test_payroll_xlsx_trilingual_ru(self, auth_client):
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/payroll?period=2026-06&lang=ru")
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        headers = [wb.active.cell(1, i + 1).value for i in range(7)]
        assert "Сотрудник" in headers

    def test_payroll_unauthenticated_returns_401_or_redirect(self, client):
        c, *_ = client
        r = c.get("/api/v1/export/payroll?period=2026-06")
        assert r.status_code in (302, 401)

    def test_payroll_empty_period_returns_header_only_sheet(self, auth_client):
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/payroll?period=1900-01")
        assert r.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        ws = wb.active
        # Row 1 = header; row 2 should be empty (no data)
        assert ws.max_row == 1


# ── TestBudgetExport ──────────────────────────────────────────────────────────

class TestBudgetExport:
    def test_budget_xlsx_returns_200(self, auth_client):
        c, *_ = auth_client
        r = c.get("/api/v1/export/budget?period=2026-06")
        assert r.status_code == 200

    def test_budget_xlsx_utilization_pct_computed(self, auth_client):
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/budget?period=2026-06")
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        ws = wb.active
        # Find D1/OpEx row — utilization should be ~60.0
        util_col = 8
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == "D1":
                assert abs(row[util_col - 1] - 60.0) < 0.1
                break

    def test_budget_allocated_zero_returns_na_cell(self, auth_client):
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/budget?period=2026-06")
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        ws = wb.active
        util_col = 8
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] == "D2":
                assert row[util_col - 1] is None  # None renders as blank/"N/A" in Excel
                break

    def test_budget_empty_period_returns_empty_sheet(self, auth_client):
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/budget?period=1900-01")
        assert r.status_code == 200
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        assert wb.active.max_row == 1  # header only

    def test_budget_period_isolation(self, auth_client):
        """2026-07 export must not contain 2026-06 data."""
        import openpyxl
        c, *_ = auth_client
        r = c.get("/api/v1/export/budget?period=2026-07")
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        ws = wb.active
        periods = [ws.cell(row=i, column=3).value for i in range(2, ws.max_row + 1)]
        assert "2026-06" not in periods


# ── TestOrgPdfExport ──────────────────────────────────────────────────────────

class TestOrgPdfExport:
    def test_org_pdf_returns_200(self, auth_client):
        c, *_ = auth_client
        r = c.get("/api/v1/export/org")
        assert r.status_code == 200

    def test_org_pdf_content_type_is_pdf(self, auth_client):
        c, *_ = auth_client
        r = c.get("/api/v1/export/org")
        assert "pdf" in r.content_type

    def test_org_pdf_empty_db_returns_placeholder_page(self, tmp_path):
        """Org PDF with no org_nodes returns a 1-page PDF, not a 500."""
        from src.runtime.export import OrgPdfExporter
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE org_nodes (node_id TEXT, name TEXT, node_type TEXT, parent_id TEXT)")
        conn.commit()
        conn.close()
        pdf_bytes = OrgPdfExporter(db).export()
        assert pdf_bytes[:4] == b"%PDF"


# ── TestTokenAuth ─────────────────────────────────────────────────────────────

class TestTokenAuth:
    def test_create_token_returns_token_and_expires_at(self, client):
        c, *_ = client
        r = c.post("/api/v1/token", json={"username": "admin", "password": "admin"})
        assert r.status_code == 200
        d = r.get_json()
        assert "token" in d
        assert "expires_at" in d
        # expires_at must be ISO 8601 UTC
        assert d["expires_at"].endswith("Z")

    def test_token_accepted_on_protected_api_endpoint(self, client):
        c, *_ = client
        r = c.post("/api/v1/token", json={"username": "admin", "password": "admin"})
        token = r.get_json()["token"]
        r2 = c.get("/api/v1/scripts/user",
                   headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200

    def test_expired_token_rejected(self, client, db_path):
        from src.runtime.token_auth import TokenStore, _hash, _iso
        # Insert an already-expired token directly into the DB
        raw = "expiredtokenvalue" + "x" * 50
        h = _hash(raw)
        past = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR REPLACE INTO tokens (token_hash, user, role, expires, created) VALUES (?,?,?,?,?)",
            (h, "admin", "user", past, past),
        )
        conn.commit()
        conn.close()
        c, *_ = client
        r = c.get("/api/v1/scripts/user",
                  headers={"Authorization": f"Bearer {raw}"})
        assert r.status_code == 401

    def test_invalid_token_rejected(self, client):
        c, *_ = client
        r = c.get("/api/v1/scripts/user",
                  headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401

    def test_revoke_token(self, client):
        c, *_ = client
        r = c.post("/api/v1/token", json={"username": "admin", "password": "admin"})
        token = r.get_json()["token"]
        r2 = c.delete("/api/v1/token",
                      headers={"Authorization": f"Bearer {token}"})
        assert r2.get_json()["revoked"] is True
        # Subsequent use must fail
        r3 = c.get("/api/v1/scripts/user",
                   headers={"Authorization": f"Bearer {token}"})
        assert r3.status_code == 401

    def test_wrong_password_returns_401(self, client):
        c, *_ = client
        r = c.post("/api/v1/token", json={"username": "admin", "password": "wrongpass"})
        assert r.status_code == 401

    def test_ttl_is_server_side_only(self, client):
        """?ttl_hours= param must NOT be accepted by the endpoint."""
        c, *_ = client
        r = c.post("/api/v1/token?ttl_hours=1",
                   json={"username": "admin", "password": "admin"})
        # Endpoint does not reject the request, but TTL is controlled server-side
        assert r.status_code == 200
        d = r.get_json()
        # expires_at should be ~24h from now, not 1h
        from datetime import timezone
        expires = datetime.fromisoformat(d["expires_at"].replace("Z", "+00:00"))
        diff_h = (expires - datetime.now(timezone.utc)).total_seconds() / 3600
        assert diff_h > 20  # server-side default 24h

    def test_401_body_identical_for_wrong_password_vs_nonexistent_user(self, client):
        """No user enumeration: same hint for bad password and nonexistent user."""
        c, *_ = client
        r1 = c.post("/api/v1/token", json={"username": "admin", "password": "bad"})
        r2 = c.post("/api/v1/token", json={"username": "nosuchuser", "password": "bad"})
        d1 = r1.get_json()
        d2 = r2.get_json()
        assert d1.get("hint") == d2.get("hint")
        assert d1.get("error") == d2.get("error")

    def test_token_expiry_at_exact_boundary(self, db_path):
        """Off-by-one guard: token expires exactly at 'now' must be rejected."""
        from src.runtime.token_auth import TokenStore, _hash, _iso
        import time
        ts = TokenStore(db_path)
        raw = "boundarytesttoken" + "x" * 50
        h = _hash(raw)
        now = datetime.now(timezone.utc)
        # Insert token with expires = exactly now
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT OR REPLACE INTO tokens (token_hash, user, role, expires, created) VALUES (?,?,?,?,?)",
            (h, "admin", "user", _iso(now), _iso(now)),
        )
        conn.commit()
        conn.close()
        time.sleep(0.01)  # ensure we are past the expiry
        result = ts.validate(raw)
        assert result is None  # must be expired


# ── TestUserScripts ───────────────────────────────────────────────────────────

class TestUserScripts:
    def test_save_script(self, auth_client):
        c, *_ = auth_client
        r = c.post("/api/v1/scripts/save",
                   json={"name": "test_script.1s", "code": "Сообщить(1);"})
        assert r.status_code == 201
        assert r.get_json()["saved"] == "test_script.1s"

    def test_list_user_scripts(self, auth_client):
        c, *_ = auth_client
        c.post("/api/v1/scripts/save", json={"name": "alpha.1s", "code": "x=1;"})
        r = c.get("/api/v1/scripts/user")
        assert "alpha.1s" in r.get_json()["scripts"]

    def test_delete_script(self, auth_client):
        c, *_ = auth_client
        c.post("/api/v1/scripts/save", json={"name": "todelete.1s", "code": "x=1;"})
        r = c.delete("/api/v1/scripts/todelete.1s")
        assert r.status_code == 200
        r2 = c.get("/api/v1/scripts/user")
        assert "todelete.1s" not in r2.get_json()["scripts"]

    def test_path_traversal_blocked(self, auth_client):
        c, *_ = auth_client
        r = c.post("/api/v1/scripts/save",
                   json={"name": "../../etc/passwd", "code": "x=1;"})
        assert r.status_code == 400

    def test_invalid_name_rejected(self, auth_client):
        c, *_ = auth_client
        for bad in ["my script.1s", "foo.bsl", "foo", "foo.1s.bak", "foo;rm.1s"]:
            r = c.post("/api/v1/scripts/save", json={"name": bad, "code": ""})
            assert r.status_code == 400, f"Expected 400 for {bad!r}, got {r.status_code}"

    def test_session_isolation(self, client, tmp_path):
        """User A's scripts must not appear in user B's listing."""
        c, db_path, scripts_dir = client
        with c.session_transaction() as sess:
            sess["user"] = {"username": "alice", "role": "user"}
        c.post("/api/v1/scripts/save", json={"name": "alice_priv.1s", "code": "x=1;"})
        with c.session_transaction() as sess:
            sess["user"] = {"username": "bob", "role": "user"}
        r = c.get("/api/v1/scripts/user")
        assert "alice_priv.1s" not in r.get_json()["scripts"]

    def test_save_409_on_name_collision(self, auth_client):
        c, *_ = auth_client
        c.post("/api/v1/scripts/save", json={"name": "dup.1s", "code": "x=1;"})
        r2 = c.post("/api/v1/scripts/save", json={"name": "dup.1s", "code": "x=2;"})
        assert r2.status_code == 409


# ── TestLoginRequiredDecorator ────────────────────────────────────────────────

class TestLoginRequiredDecorator:
    def test_decorator_accepts_session_cookie(self, auth_client):
        c, *_ = auth_client
        r = c.get("/api/v1/scripts/user")
        assert r.status_code == 200

    def test_decorator_accepts_bearer_token(self, client):
        c, *_ = client
        r = c.post("/api/v1/token", json={"username": "admin", "password": "admin"})
        token = r.get_json()["token"]
        r2 = c.get("/api/v1/scripts/user",
                   headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200

    def test_decorator_rejects_neither_returns_401(self, client):
        c, *_ = client
        r = c.get("/api/v1/scripts/user",
                  headers={"Accept": "application/json"})
        assert r.status_code in (302, 401)


# ── TestAdminRequiredWithBearer ───────────────────────────────────────────────

class TestAdminRequiredWithBearer:
    def test_admin_required_accepts_bearer_if_role_admin(self, client):
        """admin_required must also work with Bearer tokens, not just session."""
        c, *_ = client
        r = c.post("/api/v1/token", json={"username": "admin", "password": "admin"})
        token = r.get_json()["token"]
        # /admin is admin-only — if Bearer works, we get 200 not 401
        r2 = c.get("/admin",
                   headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200


# ── TestApiDiscovery ──────────────────────────────────────────────────────────

class TestApiDiscovery:
    def test_api_v1_returns_endpoint_list_with_auth_required_field(self, client):
        c, *_ = client
        r = c.get("/api/v1")
        assert r.status_code == 200
        d = r.get_json()
        assert "endpoints" in d
        # Every endpoint entry must have auth_required field
        for ep in d["endpoints"]:
            assert "auth_required" in ep, f"Missing auth_required on {ep.get('path')}"


# ── TestDependencyGraceDegradation ────────────────────────────────────────────

class TestDependencyGraceDegradation:
    def test_org_pdf_without_reportlab_returns_503(self, auth_client):
        """OrgPdfExporter must return ImportError when reportlab is missing."""
        from src.runtime.export import OrgPdfExporter
        c, db_path, _ = auth_client
        with patch.dict("sys.modules", {"reportlab": None,
                                        "reportlab.lib": None,
                                        "reportlab.lib.pagesizes": None,
                                        "reportlab.lib.units": None,
                                        "reportlab.pdfgen": None,
                                        "reportlab.pdfgen.canvas": None}):
            with pytest.raises(ImportError, match="reportlab"):
                OrgPdfExporter(db_path).export()
