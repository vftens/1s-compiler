"""Sprint 20 — packaging for Windows, Linux, macOS; CI builds; no shared secret key."""
from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "packaging"
WORKFLOWS = ROOT / ".github" / "workflows"


class _Rec:
    """Stand-in for PyInstaller's Analysis/PYZ/EXE/COLLECT/BUNDLE: records the call."""
    calls: dict[str, "_Rec"] = {}

    def __init__(self, kind: str, *args, **kw):
        self.kind, self.args, self.kw = kind, args, kw
        self.pure = self.scripts = self.binaries = self.datas = []
        _Rec.calls[kind] = self


def run_spec(name: str, env: dict[str, str] | None = None) -> dict[str, _Rec]:
    """Execute packaging/<name> with stub PyInstaller globals; return the recorded calls."""
    _Rec.calls = {}
    spec = PKG / name
    saved = os.environ.copy()
    os.environ.update(env or {})
    try:
        exec(compile(spec.read_text(encoding="utf-8"), str(spec), "exec"), {
            "SPECPATH": str(PKG), "__name__": "__main__",
            **{k: (lambda *a, _k=k, **kw: _Rec(_k, *a, **kw))
               for k in ("Analysis", "PYZ", "EXE", "COLLECT", "BUNDLE")},
        })
    finally:
        os.environ.clear()
        os.environ.update(saved)
    return _Rec.calls


def _datas(calls) -> list[tuple[str, str]]:
    return calls["Analysis"].kw["datas"]


# ── G1: Linux CLI ────────────────────────────────────────────────────────────

def test_linux_spec_builds_a_onedir_cli():
    calls = run_spec("linux.spec")
    [script] = calls["Analysis"].args[0]
    assert Path(script) == PKG / "entry_cli.py" and Path(script).exists()
    assert calls["EXE"].kw["name"] == "1s" and calls["EXE"].kw["console"] is True
    assert calls["EXE"].kw["exclude_binaries"] is True       # onedir: data persists next to the app
    assert calls["COLLECT"].kw["name"] == "1s"
    assert "BUNDLE" not in calls


def test_linux_spec_includes_every_src_module_and_templates():
    calls = run_spec("linux.spec")
    hidden = set(calls["Analysis"].kw["hiddenimports"])
    for mod in ("src.cli", "src.server", "src.migrate", "src.migrate.audit",
                "src.migrate.odoo_map", "src.runtime.query", "src.transpiler.python_backend"):
        assert mod in hidden, mod
    assert all(Path(src).exists() for src, _ in _datas(calls))
    assert ("src/templates" in [dst for _, dst in _datas(calls)])
    assert "webview" in calls["Analysis"].kw["excludes"]


def test_cli_entry_calls_src_cli_main():
    tree = ast.parse((PKG / "entry_cli.py").read_text(encoding="utf-8"))
    imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert any(n.module == "src.cli" and n.names[0].name == "main" for n in imports)


# ── G2: macOS app ────────────────────────────────────────────────────────────

def test_macos_spec_builds_an_app_bundle():
    calls = run_spec("macos.spec")
    [script] = calls["Analysis"].args[0]
    assert Path(script).name == "desktop_app.py" and Path(script).exists()
    bundle = calls["BUNDLE"].kw
    assert bundle["name"] == "1S-ERP.app" and bundle["bundle_identifier"]
    assert Path(bundle["icon"]).exists()
    assert bundle["info_plist"]["NSHighResolutionCapable"] is True
    hidden = calls["Analysis"].kw["hiddenimports"]
    assert "webview.platforms.cocoa" in hidden and "src.migrate" in hidden
    assert "webview.platforms.winforms" in calls["Analysis"].kw["excludes"]
    assert all(Path(src).exists() for src, _ in _datas(calls))


# ── G3: no shared secret key ─────────────────────────────────────────────────

@pytest.mark.parametrize("spec,env", [
    ("windows.spec", {"ONES_EDITION": "uk"}),
    ("windows.spec", {"ONES_EDITION": "base"}),
    ("linux.spec", None),
    ("macos.spec", None),
])
def test_no_spec_ships_config(spec, env):
    for src, dst in _datas(run_spec(spec, env)):
        assert Path(src).name != "config" and not dst.startswith("config"), (spec, src)


def test_secret_key_is_not_tracked():
    try:
        tracked = subprocess.run(["git", "ls-files", "config/secret.key"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        pytest.skip("git not available")
    if tracked.returncode != 0:
        pytest.skip("not a git checkout")
    assert tracked.stdout.strip() == ""
    assert "config/secret.key" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_new_install_generates_its_own_key(tmp_path, monkeypatch):
    import src.server as srv
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    k1 = srv._secret_key()
    assert len(k1) == 32 and (tmp_path / "config" / "secret.key").read_bytes() == k1
    assert srv._secret_key() == k1                      # stable for this install
    other = tmp_path / "other"
    monkeypatch.setattr(srv, "ROOT", other)
    assert srv._secret_key() != k1                      # different install, different key


def test_specs_are_not_gitignored():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for name in ("windows", "linux", "macos"):
        assert f"!packaging/{name}.spec" in gi


# ── G4: CI ───────────────────────────────────────────────────────────────────

def _wf(name: str) -> dict:
    data = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    data["on"] = data.pop(True, data.get("on"))  # PyYAML reads the key `on` as True
    return data


def test_build_workflow_covers_every_windows_edition():
    wf = _wf("build.yml")
    editions = {row["edition"] for row in wf["jobs"]["windows"]["strategy"]["matrix"]["include"]}
    spec = (PKG / "windows.spec").read_text(encoding="utf-8")
    tree = ast.parse(spec)
    spec_editions = next(
        {k.value for k in node.value.keys}
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "EDITIONS"
    )
    assert editions == spec_editions == {"base", "ru", "uk", "en"}


def test_build_workflow_jobs_and_release():
    wf = _wf("build.yml")
    jobs = wf["jobs"]
    assert set(jobs) == {"windows", "linux", "macos", "release"}
    assert jobs["windows"]["runs-on"].startswith("windows")
    assert jobs["macos"]["runs-on"].startswith("macos")
    assert set(jobs["release"]["needs"]) == {"windows", "linux", "macos"}
    assert jobs["release"]["permissions"]["contents"] == "write"
    assert "refs/tags/v" in jobs["release"]["if"]
    assert "v*" in wf["on"]["push"]["tags"] and "workflow_dispatch" in wf["on"]
    for job in ("windows", "linux", "macos"):
        text = yaml.safe_dump(jobs[job])
        assert "packaging/" in text and "upload-artifact" in text


def test_ci_runs_on_every_branch_and_installs_test_deps():
    wf = _wf("ci.yml")
    assert wf["on"]["push"]["branches"] == ["**"]
    install = next(s["run"] for s in wf["jobs"]["test"]["steps"] if s.get("name") == "Install dependencies")
    for pkg in ("glpk-utils", "reportlab", "pyyaml"):
        assert pkg in install
    assert "release" not in wf["jobs"]  # moved to build.yml
