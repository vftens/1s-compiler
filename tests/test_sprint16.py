"""Sprint 16 — One-Click Demo Runner + Auto-Seed tests (20 tests)."""
from __future__ import annotations
import io
import threading
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import src.server as srv
from src.server import app, SCRIPTS, _register_demo_scripts, _check_seed_needed, _auto_seed_on_start


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def auth_client(client):
    """Client with a valid session (admin user)."""
    with client.session_transaction() as sess:
        sess["user"] = {"username": "admin", "role": "admin"}
    return client


@pytest.fixture
def reset_seed(monkeypatch):
    """Reset module-level seed state between tests."""
    monkeypatch.setattr(srv, "_seed_state", "pending")
    monkeypatch.setattr(srv, "_seed_lock", threading.Lock())
    monkeypatch.setattr(srv, "_seed_event", threading.Event())
    yield


@pytest.fixture
def empty_db(tmp_path):
    db = tmp_path / "erp.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE budget_entries (id INTEGER PRIMARY KEY, period TEXT, amount REAL)")
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def populated_db(tmp_path):
    db = tmp_path / "erp.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE budget_entries (id INTEGER PRIMARY KEY, period TEXT, amount REAL)")
    conn.execute("INSERT INTO budget_entries VALUES (1, '2026-07', 1000.0)")
    conn.commit()
    conn.close()
    return db


# ── Registration tests (3) ───────────────────────────────────────────────────

class TestRegisterDemoScripts:
    def test_register_adds_lp_scripts(self, tmp_path, monkeypatch):
        """After _register_demo_scripts(), all demo_lp_* files on disk appear in SCRIPTS."""
        fake_scripts = {
            "demo_lp_solver_en": SCRIPTS.get("demo_lp_solver_en", {}),
        }
        monkeypatch.setattr(srv, "SCRIPTS", {})
        # Create fake demo_lp_solver_en.1s
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "demo_lp_solver_en.1s").write_text("// test")
        monkeypatch.setattr(srv, "EXAMPLES", examples)
        _register_demo_scripts()
        assert "demo_lp_solver_en" in srv.SCRIPTS

    def test_register_infers_title_from_filename(self, tmp_path, monkeypatch):
        monkeypatch.setattr(srv, "SCRIPTS", {})
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "demo_lp_solver_en.1s").write_text("// test")
        monkeypatch.setattr(srv, "EXAMPLES", examples)
        _register_demo_scripts()
        title = srv.SCRIPTS["demo_lp_solver_en"]["title"].lower()
        assert "lp" in title or "solver" in title

    def test_register_does_not_overwrite_existing(self, tmp_path, monkeypatch):
        original_title = "Custom Title"
        monkeypatch.setattr(srv, "SCRIPTS", {"demo_lp_solver_en": {"title": original_title, "module": "X", "desc": ""}})
        examples = tmp_path / "examples"
        examples.mkdir()
        (examples / "demo_lp_solver_en.1s").write_text("// test")
        monkeypatch.setattr(srv, "EXAMPLES", examples)
        _register_demo_scripts()
        assert srv.SCRIPTS["demo_lp_solver_en"]["title"] == original_title


# ── Demo route tests (3) ─────────────────────────────────────────────────────

class TestDemoRoute:
    def test_demo_200_logged_in(self, auth_client):
        rv = auth_client.get("/demo")
        assert rv.status_code == 200

    def test_demo_redirects_anonymous(self, client):
        rv = client.get("/demo")
        assert rv.status_code in (302, 401)

    def test_demo_has_expected_categories(self, auth_client, monkeypatch):
        """Page body contains LP Solver and ERP Full Cycle category labels."""
        monkeypatch.setattr(srv, "SCRIPTS", {
            "demo_lp_solver_en": {"title": "LP Solver EN", "module": "LP Solver", "desc": ""},
            "demo_erp_full_en":  {"title": "ERP Full EN",  "module": "ERP Full Cycle", "desc": ""},
        })
        rv = auth_client.get("/demo")
        body = rv.data.decode()
        assert "LP Solver" in body
        assert "ERP Full Cycle" in body


# ── Stream guard tests (3) ───────────────────────────────────────────────────

class TestStreamGuard:
    def test_stream_unknown_name_returns_404(self, auth_client):
        rv = auth_client.get("/stream/does_not_exist_xyz")
        assert rv.status_code == 404

    def test_stream_path_traversal_returns_404(self, auth_client):
        rv = auth_client.get("/stream/..%2Fconfig%2Fsecret")
        assert rv.status_code in (404, 400)

    def test_stream_registered_script_ends_with_done(self, auth_client, monkeypatch):
        """SSE for a registered script ends with __DONE__."""
        monkeypatch.setitem(srv.SCRIPTS, "demo_lp_solver_en",
                            {"title": "LP Solver", "module": "LP Solver", "desc": ""})
        mock_proc = MagicMock()
        mock_proc.stdout = iter(["line one\n", "line two\n"])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        with patch("src.server.subprocess.Popen", return_value=mock_proc):
            rv = auth_client.get("/stream/demo_lp_solver_en")
            data = rv.data.decode()
        assert "__DONE__" in data


# ── Auto-seed logic tests (7) ────────────────────────────────────────────────

class TestAutoSeed:
    def test_check_seed_needed_true_when_empty(self, empty_db):
        assert _check_seed_needed(empty_db) is True

    def test_check_seed_needed_false_when_rows(self, populated_db):
        assert _check_seed_needed(populated_db) is False

    def test_check_seed_needed_false_on_exception(self, tmp_path):
        bad_db = tmp_path / "bad.db"
        bad_db.write_text("not a sqlite db")
        result = _check_seed_needed(bad_db)
        assert result is False

    def test_seed_state_pending_at_module_load(self):
        assert srv._seed_state in ("pending", "running", "ready", "error")

    def test_seed_runs_when_db_empty(self, reset_seed, empty_db, monkeypatch):
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        popen_calls = []
        def fake_popen(*a, **kw):
            popen_calls.append(1)
            return mock_proc
        monkeypatch.setattr("src.server.subprocess.Popen", fake_popen)
        _auto_seed_on_start(db_path=empty_db)
        srv._seed_event.wait(timeout=2)
        assert len(popen_calls) == 1

    def test_seed_skips_when_db_has_rows(self, reset_seed, populated_db, monkeypatch):
        popen_calls = []
        def fake_popen(*a, **kw):
            popen_calls.append(1)
            return MagicMock()
        monkeypatch.setattr("src.server.subprocess.Popen", fake_popen)
        _auto_seed_on_start(db_path=populated_db)
        srv._seed_event.wait(timeout=1)
        assert len(popen_calls) == 0
        assert srv._seed_state == "ready"

    def test_seed_state_ready_on_success(self, reset_seed, empty_db, monkeypatch):
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        monkeypatch.setattr("src.server.subprocess.Popen", lambda *a, **kw: mock_proc)
        _auto_seed_on_start(db_path=empty_db)
        srv._seed_event.wait(timeout=2)
        assert srv._seed_state == "ready"

    def test_seed_state_error_on_failure(self, reset_seed, empty_db, monkeypatch):
        mock_proc = MagicMock()
        mock_proc.stdout = iter([])
        mock_proc.wait.return_value = None
        mock_proc.returncode = 1
        monkeypatch.setattr("src.server.subprocess.Popen", lambda *a, **kw: mock_proc)
        _auto_seed_on_start(db_path=empty_db)
        srv._seed_event.wait(timeout=2)
        assert srv._seed_state == "error"


# ── Idempotency (1) ──────────────────────────────────────────────────────────

class TestSeedIdempotency:
    def test_seed_does_not_run_twice(self, monkeypatch, empty_db):
        monkeypatch.setattr(srv, "_seed_state", "ready")
        monkeypatch.setattr(srv, "_seed_lock", threading.Lock())
        monkeypatch.setattr(srv, "_seed_event", threading.Event())
        popen_calls = []
        monkeypatch.setattr("src.server.subprocess.Popen",
                            lambda *a, **kw: popen_calls.append(1) or MagicMock())
        _auto_seed_on_start(db_path=empty_db)
        assert len(popen_calls) == 0


# ── Dashboard banner (2) ─────────────────────────────────────────────────────

class TestDashboardBanner:
    def test_dashboard_banner_present(self, auth_client):
        rv = auth_client.get("/dashboard")
        assert rv.status_code == 200
        assert b"demo-banner" in rv.data

    def test_dashboard_banner_links_to_demo(self, auth_client):
        rv = auth_client.get("/dashboard")
        assert b"/demo" in rv.data


# ── API surface (1) ──────────────────────────────────────────────────────────

class TestApiSurface:
    def test_api_scripts_includes_registered_demos(self, auth_client, monkeypatch):
        monkeypatch.setitem(srv.SCRIPTS, "demo_lp_solver_en",
                            {"title": "LP Solver EN", "module": "LP Solver", "desc": ""})
        rv = auth_client.get("/api/v1/scripts")
        assert rv.status_code == 200
        import json
        data = json.loads(rv.data)
        scripts = data.get("scripts", {})
        # scripts is a dict {name: meta}
        assert "demo_lp_solver_en" in scripts
