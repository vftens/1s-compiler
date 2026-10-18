"""Public site demo: /demo/sverka (trial balance reconciliation 1C vs Odoo via GridCraft).

The comparison runs without GridCraft (CSV); tests marked `live` also check the
.xlsx path and only run when gridcraft-cli is found.
"""
from __future__ import annotations

import io
import time
from pathlib import Path

import pytest

import src.demo_reconcile as demo
from src.migrate.gridcraft import find_cli
from src.server import app, _API_ENDPOINTS

ROOT = Path(__file__).resolve().parent.parent
LEFT = ROOT / "examples" / "reconcile" / "osv_1c_jan2025.csv"
RIGHT = ROOT / "examples" / "reconcile" / "osv_odoo_jan2025.csv"
live = pytest.mark.skipif(find_cli() is None, reason="gridcraft-cli not installed")


@pytest.fixture
def client():
    app.config["TESTING"] = True
    demo._rate.clear()
    with app.test_client() as c:
        yield c
    demo._rate.clear()


@pytest.fixture
def no_gridcraft(monkeypatch):
    monkeypatch.setattr(demo, "find_cli", lambda: None)


def _files(left=LEFT, right=RIGHT, **form):
    data = {"left": (io.BytesIO(Path(left).read_bytes()), Path(left).name),
            "right": (io.BytesIO(Path(right).read_bytes()), Path(right).name)}
    data.update(form)
    return data


def _post(client, data, ip="10.0.0.1"):
    return client.post("/api/v1/demo/reconcile", data=data, content_type="multipart/form-data",
                       headers={"X-Real-IP": ip})


# ── the page ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("lang, words", [("ru", "Сверка ОСВ"), ("uk", "Звірка ОСВ"), ("en", "Trial balance")])
def test_page_is_public_and_localised(client, no_gridcraft, lang, words):
    res = client.get(f"/demo/sverka?lang={lang}")
    html = res.get_data(as_text=True)
    assert res.status_code == 200 and words in html and f'lang="{lang}"' in html
    assert "GridCraft" in html and "/api/v1/demo/reconcile" in html


def test_sample_data_has_the_two_planted_errors():
    left, right = LEFT.read_text(encoding="utf-8-sig"), RIGHT.read_text(encoding="utf-8-sig")
    assert "31;Банк;0;0;120000;50000;70000;0" in left and "31;Банк;0;0;120100;50000;70100;0" in right
    assert "\n92;" in left and "\n92;" not in right


def test_endpoints_listed_in_api_catalogue():
    paths = {e["path"] for e in _API_ENDPOINTS}
    assert {"/demo/sverka", "/api/v1/demo/reconcile", "/api/v1/demo/engine"} <= paths


# ── reconciling without GridCraft (CSV) ──────────────────────────────────────

def test_sample_without_gridcraft(client, no_gridcraft):
    res = _post(client, {"sample": "1"})
    body = res.get_json()
    assert res.status_code == 200, body
    assert body["summary"] == {"accounts": 9, "ok": 7, "mismatch": 1, "only_left": 1, "only_right": 0}
    assert body["engine"] == "python" and body["download"] is None
    rows = {r["account"]: r for r in body["rows"]}
    assert rows["31"]["status"] == "mismatch" and rows["31"]["delta"]["close_dt"] == -100.0
    assert rows["92"]["status"] == "only_left" and rows["92"]["right"] is None


def test_upload_identical_csv(client, no_gridcraft):
    body = _post(client, _files(LEFT, LEFT)).get_json()
    assert body["summary"]["ok"] == 9 and body["summary"]["mismatch"] == 0


def test_labels_are_sanitised(client, no_gridcraft):
    body = _post(client, _files(left_label="<script>BAS</script>", right_label="")).get_json()
    assert body["labels"] == ["scriptBASscript", "Odoo"]


def test_uploads_are_deleted(client, no_gridcraft, monkeypatch, tmp_path):
    made = []
    real = demo.tempfile.mkdtemp

    def spy(**kw):
        made.append(Path(real(dir=tmp_path, **kw)))
        return str(made[-1])

    monkeypatch.setattr(demo.tempfile, "mkdtemp", spy)
    assert _post(client, _files()).status_code == 200
    assert made and not made[0].exists()


# ── rejecting bad input ──────────────────────────────────────────────────────

def test_missing_file(client, no_gridcraft):
    data = _files()
    del data["right"]
    res = _post(client, data)
    assert res.status_code == 400 and res.get_json() == {"error": "missing_file", "field": "right"}


def test_bad_extension(client, no_gridcraft, tmp_path):
    exe = tmp_path / "evil.exe"
    exe.write_bytes(b"MZ")
    res = _post(client, _files(exe, RIGHT))
    assert res.status_code == 400 and res.get_json()["error"] == "bad_format"


def test_file_too_large(client, no_gridcraft, tmp_path, monkeypatch):
    monkeypatch.setattr(demo, "MAX_FILE_BYTES", 100)
    res = _post(client, _files())
    assert res.status_code == 413 and res.get_json()["error"] == "too_large"


def test_xlsx_without_gridcraft_says_send_csv(client, no_gridcraft):
    res = _post(client, _files(LEFT, ROOT / "otchet_yanvar_2025.xlsx"))
    assert res.status_code == 503 and "CSV" in res.get_json()["hint"]


def test_not_a_trial_balance(client, no_gridcraft, tmp_path):
    junk = tmp_path / "junk.csv"
    junk.write_text("a;b\n1;2\n", encoding="utf-8")
    res = _post(client, _files(junk, RIGHT))
    assert res.status_code == 422 and res.get_json()["error"] == "unreadable"


def test_rate_limit_per_ip(client, no_gridcraft):
    for _ in range(demo.RATE_LIMIT):
        assert _post(client, {"sample": "1"}, ip="10.9.9.9").status_code == 200
    assert _post(client, {"sample": "1"}, ip="10.9.9.9").status_code == 429
    assert _post(client, {"sample": "1"}, ip="10.9.9.8").status_code == 200   # other visitors unaffected


def test_busy_when_all_slots_taken(client, no_gridcraft):
    taken = [demo._slots.acquire(blocking=False) for _ in range(demo.MAX_PARALLEL)]
    try:
        res = _post(client, {"sample": "1"})
        assert res.status_code == 503 and res.get_json()["error"] == "busy"
    finally:
        for t in taken:
            if t:
                demo._slots.release()


@pytest.mark.parametrize("token", ["../../etc/passwd", "abc", "Z" * 32, "0" * 31])
def test_download_rejects_bad_tokens(client, token):
    assert client.get(f"/api/v1/demo/reconcile/{token}").status_code == 404


def test_results_expire(tmp_path):
    f = tmp_path / "x.xlsx"
    f.write_bytes(b"PK")
    demo._results["a" * 32] = (f, time.time() - demo.RESULT_TTL - 1)
    demo._sweep()
    assert "a" * 32 not in demo._results and not f.exists()


def test_engine_endpoint_without_gridcraft(client, no_gridcraft):
    assert client.get("/api/v1/demo/engine").get_json() == {"gridcraft": False, "version": None}


# ── live: real gridcraft-cli ─────────────────────────────────────────────────

@live
def test_live_sample_gives_downloadable_workbook(client):
    body = _post(client, {"sample": "1", "lang": "uk"}).get_json()
    assert body["engine"] == "gridcraft" and body["download"]
    res = client.get(body["download"])
    assert res.status_code == 200 and res.data[:2] == b"PK"
    assert "sverka_osv.xlsx" in res.headers["Content-Disposition"]
    from src.migrate.gridcraft import GridCraft
    out = demo._results[body["download"].rsplit("/", 1)[1]][0]
    values = GridCraft().read(out)
    assert values[0][0] == "Рахунок" and any(r[14] == "РОЗБІЖНІСТЬ" for r in values[1:])


@live
def test_live_xlsx_upload(client):
    body = _post(client, _files(LEFT, ROOT / "otchet_yanvar_2025.xlsx")).get_json()
    assert body["summary"]["ok"] == 9, body


@live
def test_live_engine_and_page(client):
    assert client.get("/api/v1/demo/engine").get_json()["gridcraft"] is True
    assert "GridCraft" in client.get("/demo/sverka?lang=ru").get_data(as_text=True)


# ── shipping it: Docker image, nginx, landing ────────────────────────────────

def test_dockerfile_bundles_gridcraft():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM rust:1.90-slim-bookworm AS gridcraft" in df
    assert "--tag \"$GRIDCRAFT_REF\"" in df and "ARG GRIDCRAFT_REF=v0.8.0" in df
    assert "COPY --from=gridcraft /out/bin/ ./bin/" in df
    assert "GRIDCRAFT_CLI=/app/bin/gridcraft-cli" in df
    assert "FROM python:3.11-slim-bookworm" in df       # same glibc family as the Rust stage


def test_gridcraft_licence_shipped():
    d = ROOT / "third_party" / "gridcraft"
    assert {"LICENSE-MIT", "LICENSE-APACHE", "NOTICE"} <= {p.name for p in d.iterdir()}


def test_nginx_allows_demo_uploads_and_serves_landing():
    conf = (ROOT / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    demo_block = conf.split("location /api/v1/demo/")[1].split("}")[0]
    assert "client_max_body_size 5m" in demo_block and "X-Real-IP" in demo_block
    assert "root      /opt/1s-erp/landing" in conf


def test_landing_links_to_demo():
    html = (ROOT / "landing" / "index.html").read_text(encoding="utf-8")
    assert html.count('href="/demo/sverka') >= 2 and 'id="sverka"' in html


def test_deploy_pulls_prebuilt_image():
    sh = (ROOT / "nginx" / "deploy.sh").read_text(encoding="utf-8")
    assert "ghcr.io/vftens/1s-erp:latest" in sh and "GRIDCRAFT_REF=none" in sh
