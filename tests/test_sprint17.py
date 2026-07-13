"""Sprint 17 — Run All chained SSE endpoint (9 tests)."""
from __future__ import annotations
import subprocess
from unittest.mock import MagicMock, patch

import pytest

import src.server as srv
from src.server import app, SCRIPTS, RUN_ALL_SCRIPTS


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def auth_client(client):
    with client.session_transaction() as sess:
        sess["user"] = {"username": "admin", "role": "admin"}
    return client


def _mock_proc(lines: list[str], returncode: int = 0) -> MagicMock:
    """Build a mock Popen that yields lines and then waits cleanly."""
    m = MagicMock()
    m.stdout = iter(lines)
    m.wait.return_value = None
    m.returncode = returncode
    return m


def _collect_generator(name: str = "api_demo_run_all") -> list[str]:
    """Call the view's inner generate() directly and collect all SSE lines."""
    with app.app_context():
        with app.test_request_context("/api/v1/demo/run-all"):
            view = app.view_functions[name]
            # Access generate() by calling the route and reading the generator
            # We patch Popen before calling so the generator uses mocks.
            # Return raw data: lines (strip "data: " prefix for assertions).
            resp = view()
            raw = b"".join(resp.response).decode()
            return [ln[6:] for ln in raw.splitlines() if ln.startswith("data: ")]


# ── Test 1: RUN_ALL_SCRIPTS is non-empty and all entries are in SCRIPTS ───────

class TestRunAllList:
    def test_run_all_scripts_non_empty(self):
        assert len(RUN_ALL_SCRIPTS) > 0

    def test_run_all_entries_registered_after_register(self, monkeypatch):
        """After _register_demo_scripts(), every entry in RUN_ALL_SCRIPTS exists on disk."""
        from src.server import _register_demo_scripts, EXAMPLES
        _register_demo_scripts()
        for name in RUN_ALL_SCRIPTS:
            script_path = EXAMPLES / f"{name}.1s"
            assert script_path.exists(), f"Missing on disk: {name}.1s"


# ── Test 2: auth guard ────────────────────────────────────────────────────────

class TestRunAllAuth:
    def test_run_all_requires_login(self, client):
        rv = client.get("/api/v1/demo/run-all")
        assert rv.status_code in (302, 401)


# ── Test 3: streams all scripts and ends with __DONE__ ───────────────────────

class TestRunAllStream:
    def test_streams_done_at_end(self, auth_client, monkeypatch):
        mocks = [_mock_proc(["line A\n"], 0), _mock_proc(["line B\n"], 0),
                 _mock_proc(["line C\n"], 0)]
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        assert "__DONE__" in body

    def test_output_from_all_scripts_present(self, auth_client, monkeypatch):
        mocks = [_mock_proc(["alpha output\n"], 0),
                 _mock_proc(["beta output\n"], 0),
                 _mock_proc(["gamma output\n"], 0)]
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        assert "alpha output" in body
        assert "beta output" in body
        assert "gamma output" in body


# ── Test 4: section header lines emitted between scripts ─────────────────────

class TestRunAllHeaders:
    def test_section_headers_present(self, auth_client, monkeypatch):
        mocks = [_mock_proc([], 0)] * len(RUN_ALL_SCRIPTS)
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        import re
        headers = re.findall(r"── \[\d+/\d+\] \S+", body)
        assert len(headers) == len(RUN_ALL_SCRIPTS)

    def test_header_format_matches_pattern(self, auth_client, monkeypatch):
        mocks = [_mock_proc([], 0)] * len(RUN_ALL_SCRIPTS)
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        import re
        # First header must be ── [1/N] <name> ──...
        assert re.search(r"── \[1/\d+\] demo_\w+", body)


# ── Test 5: one script fails → remaining scripts still run ───────────────────

class TestRunAllFailContinue:
    def test_continues_after_failure(self, auth_client, monkeypatch):
        mocks = [_mock_proc(["first\n"], 1),   # exit code 1
                 _mock_proc(["second\n"], 0),
                 _mock_proc(["third\n"], 0)]
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        assert "[ERROR]" in body
        assert "second" in body
        assert "third" in body
        assert "__DONE__" in body


# ── Test 6: timeout → [ERROR] + continues ────────────────────────────────────

class TestRunAllTimeout:
    def test_continues_after_timeout(self, auth_client, monkeypatch):
        def make_timeout_proc():
            m = MagicMock()
            m.stdout = iter([])
            m.wait.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=120)
            m.kill.return_value = None
            m.returncode = -1
            return m

        mocks = [make_timeout_proc(),
                 _mock_proc(["after timeout\n"], 0),
                 _mock_proc([], 0)]
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        assert "[ERROR]" in body
        assert "after timeout" in body
        assert "__DONE__" in body


# ── Test 7: /demo page renders the Run All button ────────────────────────────

class TestDemoPageRunAllButton:
    def test_run_all_button_present(self, auth_client):
        rv = auth_client.get("/demo")
        assert rv.status_code == 200
        assert b"run-all-btn" in rv.data
        assert b"Run All Demos" in rv.data


# ── Test 8: endpoint in discovery list ───────────────────────────────────────

class TestRunAllDiscovery:
    def test_run_all_in_api_discovery(self, auth_client):
        rv = auth_client.get("/api/v1")
        assert rv.status_code == 200
        body = rv.data.decode()
        assert "/api/v1/demo/run-all" in body


# ── Test 9: missing .1s file on disk → [ERROR] + __DONE__ ───────────────────

class TestRunAllMissingFile:
    def test_missing_script_emits_error_and_continues(self, auth_client, monkeypatch):
        original = list(RUN_ALL_SCRIPTS)
        # Temporarily add a non-existent script name to the list
        monkeypatch.setattr(srv, "RUN_ALL_SCRIPTS",
                            ["__nonexistent_demo_xyz__"] + original[:1])
        mocks = [_mock_proc(["real output\n"], 0)]
        monkeypatch.setattr("src.server.subprocess.Popen",
                            MagicMock(side_effect=mocks))
        rv = auth_client.get("/api/v1/demo/run-all")
        body = rv.data.decode()
        assert "[ERROR]" in body
        assert "not found" in body
        assert "__DONE__" in body
