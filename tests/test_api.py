"""
Tests for REST API endpoints (/api/v1/) and site config.
Uses Flask test client — no real server needed.
"""
import json
import pytest
from src.server import app, _load_site, _SITE_DEFAULTS


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = b"test-secret-key"
    with app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(client):
    """Client with admin session pre-set."""
    with client.session_transaction() as sess:
        sess["user"] = {"username": "admin", "role": "admin",
                        "display": "Администратор"}
        sess["lang"] = "en"
    return client


# ── /api/v1/ping ──────────────────────────────────────────────────────────────

class TestPing:
    def test_ping_no_auth(self, client):
        r = client.get("/api/v1/ping")
        assert r.status_code == 200

    def test_ping_returns_json(self, client):
        r = client.get("/api/v1/ping")
        data = r.get_json()
        assert data["status"] == "ok"

    def test_ping_has_version(self, client):
        r = client.get("/api/v1/ping")
        data = r.get_json()
        assert "version" in data

    def test_ping_has_product(self, client):
        r = client.get("/api/v1/ping")
        data = r.get_json()
        assert "1S" in data["product"]


# ── /api/v1/scripts ───────────────────────────────────────────────────────────

class TestScripts:
    def test_scripts_requires_auth(self, client):
        r = client.get("/api/v1/scripts")
        assert r.status_code in (302, 401)   # redirect to login

    def test_scripts_returns_list(self, auth_client):
        r = auth_client.get("/api/v1/scripts")
        assert r.status_code == 200
        data = r.get_json()
        assert "scripts" in data
        assert "hello" in data["scripts"]

    def test_scripts_has_title(self, auth_client):
        r = auth_client.get("/api/v1/scripts")
        data = r.get_json()
        assert "title" in data["scripts"]["hello"]

    def test_scripts_has_module(self, auth_client):
        r = auth_client.get("/api/v1/scripts")
        data = r.get_json()
        assert "module" in data["scripts"]["hello"]


# ── /api/v1/run/<name> ────────────────────────────────────────────────────────

class TestRunScript:
    def test_run_unknown_returns_404(self, auth_client):
        r = auth_client.post("/api/v1/run/nonexistent_script_xyz")
        assert r.status_code == 404

    def test_run_returns_output(self, auth_client):
        r = auth_client.post("/api/v1/run/hello")
        assert r.status_code == 200
        data = r.get_json()
        assert "output" in data
        assert "exit_code" in data
        assert isinstance(data["output"], list)

    def test_run_hello_has_content(self, auth_client):
        r = auth_client.post("/api/v1/run/hello")
        data = r.get_json()
        # hello.1s prints something
        assert len(data["output"]) > 0

    def test_run_exit_code_zero(self, auth_client):
        r = auth_client.post("/api/v1/run/hello")
        data = r.get_json()
        assert data["exit_code"] == 0

    def test_run_includes_title(self, auth_client):
        r = auth_client.post("/api/v1/run/hello")
        data = r.get_json()
        assert "title" in data

    def test_run_get_also_works(self, auth_client):
        r = auth_client.get("/api/v1/run/hello")
        assert r.status_code == 200


# ── /api/v1/eval ─────────────────────────────────────────────────────────────

class TestEval:
    def test_eval_requires_auth(self, client):
        r = client.post("/api/v1/eval",
                        json={"code": "Message(42);"})
        assert r.status_code in (302, 401)

    def test_eval_simple_code(self, auth_client):
        r = auth_client.post("/api/v1/eval",
                             json={"code": "Message(42);"})
        assert r.status_code == 200
        data = r.get_json()
        assert "output" in data
        assert "42" in data["output"]

    def test_eval_multiline(self, auth_client):
        code = "Var X; X = 2 + 2; Message(X);"
        r = auth_client.post("/api/v1/eval", json={"code": code})
        data = r.get_json()
        assert "4" in data["output"]

    def test_eval_cyrillic(self, auth_client):
        r = auth_client.post("/api/v1/eval",
                             json={"code": 'Повідомити("ОК");'})
        data = r.get_json()
        assert "ОК" in data["output"]

    def test_eval_empty_code_runs(self, auth_client):
        r = auth_client.post("/api/v1/eval", json={"code": ""})
        assert r.status_code == 200

    def test_eval_has_exit_code(self, auth_client):
        r = auth_client.post("/api/v1/eval",
                             json={"code": "Message(1);"})
        data = r.get_json()
        assert "exit_code" in data

    def test_eval_no_body(self, auth_client):
        r = auth_client.post("/api/v1/eval")
        assert r.status_code == 200   # treats empty as no-op


# ── Site config ───────────────────────────────────────────────────────────────

class TestSiteConfig:
    def test_load_site_returns_dict(self):
        site = _load_site()
        assert isinstance(site, dict)

    def test_load_site_has_required_keys(self):
        site = _load_site()
        for key in ("phone", "website", "email", "company"):
            assert key in site

    def test_load_site_website_default(self):
        site = _load_site()
        assert "1s-compiler" in site["website"]

    def test_defaults_are_strings(self):
        for k, v in _SITE_DEFAULTS.items():
            assert isinstance(v, str), f"Key {k!r} should be str"

    def test_site_injected_into_templates(self, auth_client):
        r = auth_client.get("/dashboard")
        assert r.status_code == 200
        # Templates render without error when site{} is available
        assert b"1S" in r.data

    def test_admin_site_post(self, auth_client, tmp_path, monkeypatch):
        """Admin can update site.json; test uses a temp file to avoid overwriting config."""
        import src.server as srv
        fake_cfg = tmp_path / "site.json"
        fake_cfg.write_text('{}', encoding='utf-8')
        monkeypatch.setattr(srv, 'ROOT', tmp_path)
        (tmp_path / "config").mkdir(exist_ok=True)
        r = auth_client.post("/admin/site", data={
            "phone":       "+1 (555) 000-0000",
            "website":     "https://test.example.com",
            "email":       "test@example.com",
            "tagline_ru":  "Тест",
            "tagline_uk":  "Тест UA",
            "tagline_en":  "Test EN",
        }, follow_redirects=True)
        assert r.status_code == 200

    def test_lang_auto_selects_tagline(self, client):
        with client.session_transaction() as sess:
            sess["user"] = {"username": "u", "role": "user", "display": "U"}
            sess["lang"] = "uk"
        r = client.get("/dashboard")
        assert r.status_code == 200


# ── Language routes ───────────────────────────────────────────────────────────

class TestLangSwitch:
    def test_set_lang_ru(self, auth_client):
        r = auth_client.get("/lang/ru", follow_redirects=False)
        assert r.status_code in (302,)

    def test_set_lang_invalid_ignored(self, auth_client):
        r = auth_client.get("/lang/zz", follow_redirects=True)
        assert r.status_code == 200   # redirects but doesn't crash

    def test_set_lang_persists_in_session(self, auth_client):
        auth_client.get("/lang/uk")
        with auth_client.session_transaction() as sess:
            assert sess.get("lang") == "uk"


# ── Dashboard / Editor routes ─────────────────────────────────────────────────

class TestWebRoutes:
    def test_dashboard_requires_login(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302

    def test_dashboard_ok_when_logged_in(self, auth_client):
        r = auth_client.get("/dashboard")
        assert r.status_code == 200

    def test_editor_route_exists(self, auth_client):
        r = auth_client.get("/editor")
        assert r.status_code == 200

    def test_source_known_script(self, auth_client):
        r = auth_client.get("/source/hello")
        assert r.status_code == 200
        data = r.get_json()
        assert "source" in data
        assert len(data["source"]) > 0

    def test_source_unknown_script(self, auth_client):
        r = auth_client.get("/source/does_not_exist")
        assert r.status_code == 404

    def test_run_script_page(self, auth_client):
        r = auth_client.get("/run/hello")
        assert r.status_code == 200

    def test_run_unknown_script(self, auth_client):
        r = auth_client.get("/run/totally_unknown_xyz")
        # Should redirect with flash
        assert r.status_code in (302, 404)
