"""Public web demo: trial balance (ОСВ) reconciliation 1C/BAS vs Odoo, powered by GridCraft.

Pages and endpoints (no login, meant for www.1s-compiler.ru):

    GET  /demo/sverka                    the demo page (ru/uk/en: ?lang= or session)
    POST /api/v1/demo/reconcile          two files (left, right) or sample=1 -> JSON
    GET  /api/v1/demo/reconcile/<token>  the reconciliation .xlsx built by GridCraft
    GET  /api/v1/demo/engine             is GridCraft available, which version

Safety for a public endpoint on a small VPS:
- uploads: csv/tsv/txt/xls/xlsx/xlsb/ods only, MAX_FILE_BYTES each, read into a
  private temp dir and deleted right after the comparison;
- result workbooks live RESULT_TTL seconds under a random token, then are swept;
- RATE_LIMIT requests per minute per IP, at most MAX_PARALLEL GridCraft jobs;
- CSV needs no GridCraft; .xls/.xlsx input and the .xlsx result do. Without
  gridcraft-cli the demo still compares CSV files and says what is missing.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, render_template, request, send_file, session

from .migrate.gridcraft import GridCraft, GridCraftError, find_cli
from .migrate.reconcile import Diff, load_trial_balance, reconcile, summary, write_reconciliation

bp = Blueprint("demo_reconcile", __name__)

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_LEFT = ROOT / "examples" / "reconcile" / "osv_1c_jan2025.csv"
SAMPLE_RIGHT = ROOT / "examples" / "reconcile" / "osv_odoo_jan2025.csv"

CSV_EXT = {".csv", ".tsv", ".txt"}
BOOK_EXT = {".xls", ".xlsx", ".xlsb", ".ods"}
MAX_FILE_BYTES = 2 * 1024 * 1024
RESULT_TTL = 15 * 60
RATE_LIMIT = 10          # requests / minute / IP
MAX_PARALLEL = 2         # GridCraft processes at once (1 GB VPS)
_LABEL_RE = re.compile(r"[^\w .\-()]+", re.UNICODE)
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")

_results_dir = Path(tempfile.gettempdir()) / "1s-demo-reconcile"
_results: dict[str, tuple[Path, float]] = {}
_lock = threading.Lock()
_rate: dict[str, list[float]] = {}
_slots = threading.BoundedSemaphore(MAX_PARALLEL)
_FIELDS = ("turn_dt", "turn_ct", "close_dt", "close_ct")

TEXT = {
    "ru": {
        "title": "Сверка ОСВ после переезда с 1С",
        "lead": "Загрузите оборотно-сальдовую ведомость из 1С/BAS и из новой системы. "
                "Через пару секунд увидите, какие счета не сошлись, и скачаете книгу Excel, "
                "где каждая разница посчитана формулой.",
        "left": "ОСВ из 1С / BAS", "right": "ОСВ из новой системы (Odoo, 1S…)",
        "formats": "CSV, XLS, XLSX, ODS · до 2 МБ · файлы удаляются сразу после сверки",
        "run": "Сверить", "sample": "Попробовать на примере", "download": "Скачать сверку .xlsx",
        "accounts": "счетов", "ok": "сошлось", "mismatch": "расходится",
        "only_left": "только в 1С", "only_right": "только в новой системе",
        "acc": "Счёт", "name": "Наименование", "status": "Статус", "delta": "Разница",
        "engine_on": "Движок таблиц GridCraft {v} подключён",
        "engine_off": "GridCraft не установлен на сервере: сверяются только CSV, без скачивания .xlsx",
        "how": "Как это работает", "busy": "Сервер занят, попробуйте через минуту",
        "how1": "1S читает обе ведомости: CSV напрямую, XLS/XLSX через GridCraft (Rust).",
        "how2": "Счета сопоставляются по коду, сравниваются обороты и конечные остатки (допуск 0,005).",
        "how3": "GridCraft пишет книгу .xlsx: разницы и статусы — формулы, расхождения подсвечены.",
        "cli": "То же самое из командной строки:",
    },
    "uk": {
        "title": "Звірка ОСВ після переїзду з 1С",
        "lead": "Завантажте оборотно-сальдову відомість з 1С/BAS і з нової системи. "
                "За кілька секунд побачите, які рахунки не зійшлися, і завантажите книгу Excel, "
                "де кожна різниця порахована формулою.",
        "left": "ОСВ з 1С / BAS", "right": "ОСВ з нової системи (Odoo, 1S…)",
        "formats": "CSV, XLS, XLSX, ODS · до 2 МБ · файли видаляються одразу після звірки",
        "run": "Звірити", "sample": "Спробувати на прикладі", "download": "Завантажити звірку .xlsx",
        "accounts": "рахунків", "ok": "зійшлося", "mismatch": "розбіжність",
        "only_left": "тільки в 1С", "only_right": "тільки в новій системі",
        "acc": "Рахунок", "name": "Назва", "status": "Статус", "delta": "Різниця",
        "engine_on": "Рушій таблиць GridCraft {v} підключено",
        "engine_off": "GridCraft не встановлено на сервері: звіряються лише CSV, без завантаження .xlsx",
        "how": "Як це працює", "busy": "Сервер зайнятий, спробуйте за хвилину",
        "how1": "1S читає обидві відомості: CSV напряму, XLS/XLSX через GridCraft (Rust).",
        "how2": "Рахунки зіставляються за кодом, порівнюються обороти та кінцеві залишки (допуск 0,005).",
        "how3": "GridCraft пише книгу .xlsx: різниці та статуси — формули, розбіжності підсвічені.",
        "cli": "Те саме з командного рядка:",
    },
    "en": {
        "title": "Trial balance check after leaving 1C",
        "lead": "Upload the trial balance from 1C/BAS and from the new system. In a couple of "
                "seconds you see which accounts do not match and download an Excel workbook "
                "where every difference is a formula.",
        "left": "Trial balance from 1C / BAS", "right": "Trial balance from the new system (Odoo, 1S…)",
        "formats": "CSV, XLS, XLSX, ODS · up to 2 MB · files are deleted right after the check",
        "run": "Compare", "sample": "Try the sample", "download": "Download .xlsx",
        "accounts": "accounts", "ok": "match", "mismatch": "mismatch",
        "only_left": "only in 1C", "only_right": "only in the new system",
        "acc": "Account", "name": "Name", "status": "Status", "delta": "Difference",
        "engine_on": "GridCraft spreadsheet engine {v} connected",
        "engine_off": "GridCraft is not installed on the server: CSV only, no .xlsx download",
        "how": "How it works", "busy": "Server is busy, try again in a minute",
        "how1": "1S reads both trial balances: CSV directly, XLS/XLSX through GridCraft (Rust).",
        "how2": "Accounts are matched by code; turnovers and closing balances are compared (0.005 tolerance).",
        "how3": "GridCraft writes an .xlsx: differences and statuses are formulas, mismatches highlighted.",
        "cli": "The same from the command line:",
    },
}


def _lang() -> str:
    q = request.args.get("lang", "")
    if q in TEXT:
        session["lang"] = q
        return q
    return session.get("lang") if session.get("lang") in TEXT else "ru"


def _engine() -> dict:
    cli = find_cli()
    if cli is None:
        return {"gridcraft": False, "version": None}
    try:
        raw = GridCraft(cli, timeout=10).version()          # "gridcraft-cli 0.8.0"
        return {"gridcraft": True, "version": raw.split()[-1] if raw else None}
    except GridCraftError:
        return {"gridcraft": False, "version": None}


def _client_ip() -> str:
    """Visitor IP. X-Real-IP is trusted only from a local reverse proxy (nginx)."""
    peer = request.remote_addr or "?"
    if peer.startswith(("127.", "10.", "172.", "192.168.")) or peer == "::1":
        return request.headers.get("X-Real-IP") or peer
    return peer


def _allow(ip: str) -> bool:
    now = time.time()
    with _lock:
        hits = [t for t in _rate.get(ip, []) if now - t < 60]
        if len(hits) >= RATE_LIMIT:
            _rate[ip] = hits
            return False
        _rate[ip] = hits + [now]
        return True


def _sweep(now: float | None = None) -> None:
    now = now or time.time()
    with _lock:
        for tok, (path, born) in list(_results.items()):
            if now - born > RESULT_TTL:
                path.unlink(missing_ok=True)
                del _results[tok]


def _error(code: str, status: int, **extra):
    return jsonify({"error": code, **extra}), status


def _row(d: Diff) -> dict:
    side = lambda r: None if r is None else {f: getattr(r, f) for f in _FIELDS}  # noqa: E731
    return {"account": d.account, "name": d.name, "status": d.status,
            "left": side(d.left), "right": side(d.right),
            "delta": {f: d.delta(f) for f in _FIELDS}}


def _label(v: str | None, default: str) -> str:
    v = _LABEL_RE.sub("", (v or "").strip())[:20]
    return v or default


@bp.route("/demo/sverka")
def page():
    lang = _lang()
    return render_template("demo_sverka.html", T=TEXT[lang], lang=lang, engine=_engine(),
                           max_mb=MAX_FILE_BYTES // (1024 * 1024))


@bp.route("/api/v1/demo/engine")
def engine():
    return jsonify(_engine())


@bp.route("/api/v1/demo/reconcile", methods=["POST"])
def run():
    if not _allow(_client_ip()):
        return _error("rate_limited", 429, retry_after=60)
    if (request.content_length or 0) > 2 * MAX_FILE_BYTES + 64 * 1024:
        return _error("too_large", 413, max_bytes=MAX_FILE_BYTES)
    _sweep()
    lang = request.form.get("lang") if request.form.get("lang") in TEXT else "ru"
    left_label = _label(request.form.get("left_label"), "1C")
    right_label = _label(request.form.get("right_label"), "Odoo")
    cli = find_cli()

    if not _slots.acquire(blocking=False):
        return _error("busy", 503, retry_after=30)
    work = Path(tempfile.mkdtemp(prefix="1s-demo-"))
    try:
        if request.form.get("sample") == "1":
            left_path, right_path = SAMPLE_LEFT, SAMPLE_RIGHT
            left_label, right_label = "1C", "Odoo"
        else:
            paths = []
            for field in ("left", "right"):
                f = request.files.get(field)
                if f is None or not f.filename:
                    return _error("missing_file", 400, field=field)
                ext = Path(f.filename).suffix.lower()
                if ext not in CSV_EXT | BOOK_EXT:
                    return _error("bad_format", 400, field=field,
                                  allowed=sorted(CSV_EXT | BOOK_EXT))
                if ext in BOOK_EXT and cli is None:
                    return _error("gridcraft_missing", 503, field=field,
                                  hint="the server reads .xls/.xlsx through GridCraft; send CSV")
                data = f.read(MAX_FILE_BYTES + 1)
                if len(data) > MAX_FILE_BYTES:
                    return _error("too_large", 413, field=field, max_bytes=MAX_FILE_BYTES)
                p = work / f"{field}{ext}"           # our own name, never the client's
                p.write_bytes(data)
                paths.append(p)
            left_path, right_path = paths

        gc = GridCraft(cli, timeout=60) if cli else None
        try:
            left = load_trial_balance(left_path, gc)
            right = load_trial_balance(right_path, gc)
        except (ValueError, GridCraftError, UnicodeError) as exc:
            return _error("unreadable", 422, message=str(exc)[:300])
        diffs = reconcile(left, right)

        download = None
        if gc is not None and diffs:
            token = uuid.uuid4().hex
            _results_dir.mkdir(parents=True, exist_ok=True)
            out = _results_dir / f"{token}.xlsx"
            try:
                write_reconciliation(diffs, out, left_label, right_label, lang, gc)
                with _lock:
                    _results[token] = (out, time.time())
                download = f"/api/v1/demo/reconcile/{token}"
            except GridCraftError:
                out.unlink(missing_ok=True)
        return jsonify({"summary": summary(diffs), "rows": [_row(d) for d in diffs],
                        "labels": [left_label, right_label], "download": download,
                        "engine": "gridcraft" if gc else "python"})
    finally:
        shutil.rmtree(work, ignore_errors=True)
        _slots.release()


@bp.route("/api/v1/demo/reconcile/<token>")
def download(token: str):
    if not _TOKEN_RE.match(token):
        return _error("not_found", 404)
    _sweep()
    with _lock:
        entry = _results.get(token)
    if entry is None or not entry[0].is_file():
        return _error("not_found", 404)
    return send_file(entry[0], as_attachment=True, download_name="sverka_osv.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


API_DOCS = [
    {"method": "GET", "path": "/demo/sverka", "auth_required": False,
     "description": "Public demo page: trial balance reconciliation 1C vs Odoo (GridCraft).",
     "query_params": ["lang"], "content_type": "text/html", "example_response": "<html>…"},
    {"method": "POST", "path": "/api/v1/demo/reconcile", "auth_required": False,
     "description": "multipart: left, right (csv/xls/xlsx/ods ≤2 MB) or sample=1; lang, "
                    "left_label, right_label. Rate limited.",
     "query_params": [], "content_type": "application/json",
     "example_response": {"summary": {"accounts": 9, "ok": 7, "mismatch": 1, "only_left": 1,
                                      "only_right": 0}, "download": "/api/v1/demo/reconcile/<token>"}},
    {"method": "GET", "path": "/api/v1/demo/reconcile/<token>", "auth_required": False,
     "description": f"Reconciliation workbook (.xlsx), kept {RESULT_TTL // 60} minutes.",
     "query_params": [], "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
     "example_response": "<xlsx>"},
    {"method": "GET", "path": "/api/v1/demo/engine", "auth_required": False,
     "description": "GridCraft availability and version.", "query_params": [],
     "content_type": "application/json", "example_response": {"gridcraft": True, "version": "0.8.0"}},
]
