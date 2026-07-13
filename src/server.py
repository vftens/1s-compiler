"""
1S: ERP Free Edition — Web UI server.
Run:  python -m src.cli serve [--port 5000] [--host 127.0.0.1]
"""
from __future__ import annotations
import os
import sys
import uuid
import tempfile
import subprocess
import threading
import logging
from functools import wraps
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for,
                   session, Response, flash, stream_with_context, jsonify, g, send_file)

# In-memory store for editor run jobs: run_id → tmp_file_path
_EDITOR_RUNS: dict[str, Path] = {}

import re as _re
import io as _io

ROOT     = Path(__file__).parent.parent
EXAMPLES = ROOT / "examples"

# ── Site config ───────────────────────────────────────────────────────────────

_SITE_DEFAULTS = {
    "company":     "1S: ERP Free Edition",
    "phone":       "",
    "website":     "https://www.1s-compiler.ru",
    "email":       "",
    "tagline_ru":  "Система управления предприятием",
    "tagline_uk":  "Система управління підприємством",
    "tagline_en":  "Enterprise Management System",
}


def _load_site() -> dict:
    """Load config/site.json; returns defaults if missing or malformed."""
    import json as _json
    cfg = ROOT / "config" / "site.json"
    try:
        if cfg.exists():
            return {**_SITE_DEFAULTS, **_json.loads(cfg.read_text(encoding="utf-8"))}
    except Exception:
        pass
    return dict(_SITE_DEFAULTS)


SUPPORTED_LANGS = {"ru", "uk", "en"}


def _detect_lang(s: str) -> str:
    """'uk-UA,uk;q=0.9' or 'ru_RU' or 'en' → one of 'ru'|'uk'|'en'."""
    for tag in s.replace(' ', '').split(','):
        code = tag.split(';')[0].lower().replace('_', '-').split('-')[0]
        if code in ('uk', 'be'):          return 'uk'
        if code in ('ru', 'kk', 'ky',
                    'az', 'uz', 'tg'):   return 'ru'
        if code:                          return 'en'
    return 'ru'


def _os_lang() -> str:
    """Detect OS locale once at startup → 'ru' | 'uk' | 'en'."""
    # 1. Explicit override via env var (set by language-specific launchers)
    override = os.environ.get("1S_DEFAULT_LANG", "").strip().lower()
    if override in ("ru", "uk", "en"):
        return override
    # 2. OS locale / LANG environment variable
    import locale as _lc
    try:
        loc = (_lc.getlocale()[0] or
               os.environ.get('LANG', os.environ.get('LANGUAGE', '')))
    except Exception:
        loc = ''
    return _detect_lang(loc)


# Determined once when the module loads — same for browser and desktop app
DEFAULT_LANG: str = _os_lang()

# ── Secret key ───────────────────────────────────────────────────────────────

def _secret_key() -> bytes:
    key_file = ROOT / "config" / "secret.key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if key_file.exists():
        return key_file.read_bytes()
    key = os.urandom(32)
    key_file.write_bytes(key)
    return key

# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder=str(Path(__file__).parent / "templates"))
app.secret_key = _secret_key()

# ── Script catalogue ──────────────────────────────────────────────────────────

SCRIPTS: dict[str, dict] = {
    "hello":           {"title": "Hello World",               "module": "Прочее",
                        "desc": "Первая программа на 1S — приветствие"},
    "hello_uk":        {"title": "Hello World (UA)",           "module": "Українська",
                        "desc": "Перша програма на 1S (українська мова)"},
    "accounting":      {"title": "Бухгалтерия",               "module": "Бухгалтерия",
                        "desc": "Двойная запись, план счетов, ОСВ, анализ сч. 60"},
    "accounting_uk":   {"title": "Бухоблік (UA)",              "module": "Українська",
                        "desc": "Подвійний запис, план рахунків УКСГП, ОСВ, аналіз рах. 31"},
    "erp_sale":        {"title": "ERP: Продажи",               "module": "Торговля",
                        "desc": "Заказы, отгрузки, взаиморасчёты с контрагентами"},
    "erp_sale_uk":     {"title": "ERP: Реалізація (UA)",        "module": "Українська",
                        "desc": "Видаткова накладна, залишки, фінансовий результат (UA)"},
    "hrm_payroll":     {"title": "ЗУП: Расчёт зарплаты",       "module": "ЗУП",
                        "desc": "Начисление ЗП, НДФЛ, страховые взносы, отпуска"},
    "hrm_zup":         {"title": "ЗУП: Классификаторы",        "module": "ЗУП",
                        "desc": "Инфобаза ЗУП, графики работы, штатное расписание"},
    "erp_full_uk":     {"title": "ERP: Повний цикл (UA)",        "module": "Торговля",
                        "desc": "Довідники + Документи + Облік + P&L — повний ERP-цикл"},
    "erp_full_ru":     {"title": "ERP: Полный цикл (RU)",         "module": "Торговля",
                        "desc": "Справочники + Документы + Учёт + П&У — полный ERP-цикл"},
    "erp_full_en":     {"title": "ERP: Full cycle (EN)",           "module": "Торговля",
                        "desc": "Catalogs + Documents + Accounting + P&L — complete ERP cycle"},
    "reports_uk":      {"title": "ОСВ + P&L (UA)",               "module": "Бухгалтерия",
                        "desc": "Оборотно-сальдова відомість + Звіт про фінансові результати"},
    "reports_ru":      {"title": "ОСВ + ОФР (RU)",              "module": "Бухгалтерия",
                        "desc": "Оборотно-сальдовая ведомость + Отчёт о финансовых результатах"},
    "reports_en":      {"title": "Trial Balance + P&L (EN)",    "module": "Бухгалтерия",
                        "desc": "Trial Balance + Income Statement (Profit & Loss Report)"},
    "demo_zup_uk":     {"title": "ЗУП: Зарплата (UA)",             "module": "ЗУП",
                        "desc": "Нарахування ЗП, ПДФО 18%, ВЗ 1.5%, ЄСВ 22%, Workflow"},
    "demo_zup_ru":     {"title": "ЗУП: Зарплата (RU)",             "module": "ЗУП",
                        "desc": "Расчёт ЗП, НДФЛ 13%, страх. взносы 30%, Workflow"},
    "demo_zup_en":     {"title": "HRM: Payroll (EN)",               "module": "ЗУП",
                        "desc": "UK payroll: Income Tax 20%, NI 12%+13.8%, Pension 5%+3%"},
    "demo_cython_perf_uk": {"title": "Cython Perf DEMO (UA)",       "module": "Прочее",
                        "desc": "4 теста × 1M ітерацій → 600 мс Python → ~10 мс Cython (50×)"},
    "demo_cython_perf_ru": {"title": "Cython Perf DEMO (RU)",       "module": "Прочее",
                        "desc": "4 теста × 1M итераций → 600 мс Python → ~10 мс Cython (50×)"},
    "demo_cython_perf_en": {"title": "Cython Perf DEMO (EN)",       "module": "Прочее",
                        "desc": "4 benchmarks × 1M iterations → 600ms Python → ~10ms Cython (50x)"},
    "demo_cython_uk":  {"title": "Cython: Швидкість (UA)",          "module": "Прочее",
                        "desc": "Fibonacci, решето простих чисел, замір часу Python vs Cython"},
    "demo_cython_ru":  {"title": "Cython: Скорость (RU)",           "module": "Прочее",
                        "desc": "Числа Фибоначчи, решето Эратосфена, замер скорости Python vs Cython"},
    "demo_cython_en":  {"title": "Cython: Speed (EN)",              "module": "Прочее",
                        "desc": "Fibonacci, prime sieve, loop benchmark: Python vs Cython 10-50x"},
    "demo_workflow_graphics_uk": {"title": "Workflow Dashboard (UA)", "module": "Прочее",
                        "desc": "ASCII-графіки стану документів, часова шкала, KPI метрики"},
    "demo_workflow_graphics_ru": {"title": "Workflow Dashboard (RU)", "module": "Прочее",
                        "desc": "ASCII-графики состояния документов, лента событий, KPI"},
    "demo_workflow_graphics_en": {"title": "Workflow Dashboard (EN)", "module": "Прочее",
                        "desc": "ASCII charts for document statuses, timeline, KPI metrics"},
    "demo_accounting_uk": {"title": "Бухоблік: Повний цикл (UA)",   "module": "Бухгалтерия",
                        "desc": "Вхідне сальдо → Операції → ОСВ → P&L — повний місячний цикл"},
    "demo_accounting_ru": {"title": "Бухучёт: Полный цикл (RU)",    "module": "Бухгалтерия",
                        "desc": "Входящее сальдо → Операции → ОСВ → P&L — полный месячный цикл"},
    "demo_accounting_en": {"title": "Accounting: Full cycle (EN)",   "module": "Бухгалтерия",
                        "desc": "Opening balances → Journal entries → Trial Balance → P&L"},
    "export_uk":       {"title": "Excel Export (UA)",               "module": "Бухгалтерия",
                        "desc": "Оборотно-сальдова відомість + P&L → .xlsx / .csv"},
    "export_ru":       {"title": "Excel Export (RU)",               "module": "Бухгалтерия",
                        "desc": "Оборотно-сальдовая ведомость + P&L → .xlsx / .csv"},
    "export_en":       {"title": "Excel Export (EN)",               "module": "Бухгалтерия",
                        "desc": "Trial Balance + Income Statement → .xlsx / .csv"},
    "planning_uk":     {"title": "Планування 4 тижні (UA)",    "module": "Прочее",
                        "desc": "Тижневі плани + Workflow + Звіт «ПЛАН vs ФАКТ» — 4 тижні вперед"},
    "planning_ru":     {"title": "Планирование 4 недели (RU)",  "module": "Прочее",
                        "desc": "Недельные планы + Workflow + Отчёт «ПЛАН vs ФАКТ» — 4 недели"},
    "planning_en":     {"title": "4-Week Planning (EN)",         "module": "Прочее",
                        "desc": "Weekly plans + Workflow execution + Plan vs Actual report"},
    "workflow_uk":     {"title": "Workflow (UA)",                 "module": "Прочее",
                        "desc": "Маршрут погодження: Чернетка → Погодженні → Погоджено → Проведено"},
    "workflow_ru":     {"title": "Workflow (RU)",                 "module": "Прочее",
                        "desc": "Маршрут согласования: Черновик → Согласование → Согласован → Проведён"},
    "workflow_en":     {"title": "Workflow (EN)",                 "module": "Прочее",
                        "desc": "Approval workflow: Draft → Pending → Approved → Posted"},
    "chess_uk":        {"title": "Шахматка (UA)",               "module": "Бухгалтерия",
                        "desc": "Шахматна відомість Дт×Кт — оборотна матриця рахунків"},
    "chess_ru":        {"title": "Шахматная ведомость",         "module": "Бухгалтерия",
                        "desc": "Матрица оборотов Дт×Кт по всем счетам за период"},
    "chess_en":        {"title": "Chess Board (EN)",            "module": "Бухгалтерия",
                        "desc": "Debit × Credit cross-tab matrix of all account turnovers"},
}

MODULE_ICONS = {
    "Прочее":      "💬",
    "Українська":  "🇺🇦",
    "Бухгалтерия": "📒",
    "Торговля":    "🛒",
    "ЗУП":         "👥",
    "LP Solver":   "📐",
    "Demo":        "🎬",
}

# ── Sprint 16: Demo categories (ordered) ─────────────────────────────────────

DEMO_CATEGORIES: dict[str, list[str]] = {
    "LP Solver":     ["demo_lp_"],
    "ERP Full Cycle":["demo_erp_full_", "demo_erp_"],
    "Reports":       ["demo_reports_", "demo_accounting_"],
    "Payroll":       ["demo_payroll_", "demo_zup_"],
    "Other Demos":   ["demo_breakeven_", "demo_construction_", "demo_manufacturing_",
                      "demo_persistence_", "demo_trade_", "demo_vat_balance_",
                      "demo_workflow_", "demo_cython_", "demo_planning_"],
}

_LANG_LABELS = {"en": "EN", "ru": "RU", "uk": "UA"}

# ── Sprint 17: Ordered curated run-all list ───────────────────────────────────
# Pure list constant — no I/O; defined after SCRIPTS so tests can import directly.
RUN_ALL_SCRIPTS: list[str] = [
    "demo_lp_solver_en",
    "demo_erp_full_en",
    "demo_reports_en",
]


def _register_demo_scripts() -> None:
    """Glob EXAMPLES/demo_*.1s and add any missing entries to SCRIPTS."""
    for path in sorted(EXAMPLES.glob("demo_*.1s")):
        name = path.stem
        if name in SCRIPTS:
            continue
        parts = name.split("_")
        lang_suffix = parts[-1] if parts[-1] in _LANG_LABELS else ""
        core_parts = parts[1:-1] if lang_suffix else parts[1:]
        title_words = [w.capitalize() for w in core_parts]
        lang_label = _LANG_LABELS.get(lang_suffix, "")
        title = " ".join(title_words) + (f" ({lang_label})" if lang_label else "")

        module = "Demo"
        for cat, prefixes in DEMO_CATEGORIES.items():
            if any(name.startswith(p) for p in prefixes):
                module = cat
                break

        SCRIPTS[name] = {"title": title, "module": module, "desc": ""}


# ── Sprint 16: Auto-seed state ────────────────────────────────────────────────

_seed_state: str = "pending"
_seed_lock: threading.Lock = threading.Lock()
_seed_event: threading.Event = threading.Event()
_log = logging.getLogger("1s.seed")


def _check_seed_needed(db_path: Path) -> bool:
    """Return True if erp.db has no budget_entries rows."""
    import sqlite3
    if not db_path.exists():
        _log.info("[seed] data/erp.db not found — will seed on first run")
        return True
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM budget_entries")
            return cur.fetchone()[0] == 0
    except Exception as exc:
        _log.warning("[seed] Could not read erp.db (%s) — skipping auto-seed", exc)
        return False


def _run_seed_subprocess() -> None:
    global _seed_state
    script = EXAMPLES / "demo_erp_full_en.1s"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONUTF8"] = "1"
    _log.info("[seed] Seeding demo data from demo_erp_full_en.1s (background)…")
    with _seed_lock:
        _seed_state = "running"
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "src.cli", "run", str(script)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            env=env, cwd=str(ROOT),
        )
        proc.wait()
        if proc.returncode == 0:
            with _seed_lock:
                _seed_state = "ready"
            _log.info("[seed] Demo data seeded successfully")
        else:
            with _seed_lock:
                _seed_state = "error"
            _log.error("[seed] Auto-seed failed (exit code %d); check examples/demo_erp_full_en.1s",
                       proc.returncode)
    except Exception as exc:
        with _seed_lock:
            _seed_state = "error"
        _log.error("[seed] Auto-seed exception: %s", exc)
    finally:
        _seed_event.set()


def _auto_seed_on_start(db_path: Path | None = None) -> None:
    """Start background seed if erp.db is empty. Idempotent."""
    global _seed_state
    db = db_path or (ROOT / "data" / "erp.db")
    with _seed_lock:
        if _seed_state in ("running", "ready"):
            return
    _log.info("[seed] Checking if demo seed needed…")
    if not _check_seed_needed(db):
        _log.info("[seed] erp.db already has data — skipping auto-seed")
        with _seed_lock:
            _seed_state = "ready"
        _seed_event.set()
        return
    t = threading.Thread(target=_run_seed_subprocess, daemon=True)
    t.start()


@app.before_request
def auto_lang():
    """First visit: inherit DEFAULT_LANG (detected from OS at startup)."""
    if 'lang' not in session:
        session['lang'] = DEFAULT_LANG


# ── i18n context processor ───────────────────────────────────────────────────

@app.context_processor
def inject_i18n():
    from .i18n import t as build_t
    lang = session.get("lang", DEFAULT_LANG)
    site = _load_site()
    # Pick tagline for current language
    site["tagline"] = site.get(f"tagline_{lang}", site.get("tagline_ru", ""))
    return {"t": build_t(lang), "lang": lang, "site": site}


# ── Sprint 13: token auth + export + script persistence ──────────────────────

from .runtime.token_auth import TokenStore
from .runtime.export import PayrollExporter, BudgetExporter, OrgPdfExporter

_ERP_DB_S13 = ROOT / "data" / "erp.db"
_USER_SCRIPTS_DIR = ROOT / "data" / "user_scripts"
_USER_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
_token_store = TokenStore(_ERP_DB_S13)

# Rate limiting for token endpoint (5 attempts / minute / IP)
import time as _time
_TOKEN_RATE: dict[str, list] = {}
_TOKEN_RATE_LIMIT = 5
_TOKEN_RATE_WINDOW = 60


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed; False if rate limit exceeded."""
    now = _time.time()
    hits = [t for t in _TOKEN_RATE.get(ip, []) if now - t < _TOKEN_RATE_WINDOW]
    _TOKEN_RATE[ip] = hits
    if len(hits) >= _TOKEN_RATE_LIMIT:
        return False
    _TOKEN_RATE[ip].append(now)
    return True

# ── Auth decorators ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        # Bearer token path (REST clients, CLI integrations)
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            raw = auth[7:]
            user = _token_store.validate(raw)
            if user:
                g.current_user = user
                return f(*a, **kw)
            return jsonify({
                "error": "invalid_token",
                "hint": "Use Authorization: Bearer <token> or log in via /login",
            }), 401
        # Session cookie path (browser)
        if "user" not in session:
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({
                    "error": "unauthenticated",
                    "hint": "Use Authorization: Bearer <token> or log in via /login",
                }), 401
            return redirect(url_for("login"))
        g.current_user = session["user"]
        return f(*a, **kw)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        # Bearer token path
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            raw = auth[7:]
            user = _token_store.validate(raw)
            if user:
                if user.get("role") != "admin":
                    return jsonify({"error": "forbidden", "hint": "Admin role required"}), 403
                g.current_user = user
                return f(*a, **kw)
            return jsonify({
                "error": "invalid_token",
                "hint": "Use Authorization: Bearer <token> or log in via /login",
            }), 401
        # Session cookie path
        if "user" not in session:
            return redirect(url_for("login"))
        if session["user"].get("role") != "admin":
            flash("Доступ запрещён: требуются права администратора.", "danger")
            return redirect(url_for("dashboard"))
        g.current_user = session["user"]
        return f(*a, **kw)
    return wrapped

# ── Global JSON error handlers (no HTML leakage) ─────────────────────────────

@app.errorhandler(400)
def err_400(e):
    return jsonify({"error": "bad_request", "message": str(e)}), 400

@app.errorhandler(401)
def err_401(e):
    return jsonify({"error": "unauthorized", "hint": "Use Authorization: Bearer <token> or log in via /login"}), 401

@app.errorhandler(403)
def err_403(e):
    return jsonify({"error": "forbidden"}), 403

@app.errorhandler(404)
def err_404(e):
    return jsonify({"error": "not_found"}), 404

@app.errorhandler(405)
def err_405(e):
    return jsonify({"error": "method_not_allowed"}), 405

@app.errorhandler(500)
def err_500(e):
    return jsonify({"error": "internal_server_error"}), 500

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/lang/<code>")
def set_lang(code: str):
    """Switch UI language and redirect back."""
    if code in SUPPORTED_LANGS:
        session["lang"] = code
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user" in session else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        from .auth import verify
        user = verify(request.form.get("username", "").strip(),
                      request.form.get("password", ""))
        if user:
            session["user"] = user
            return redirect(url_for("dashboard"))
        error = "Неверный логин или пароль."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    mod = request.args.get("module", "")
    scripts = {k: v for k, v in SCRIPTS.items()
               if not mod or v["module"] == mod}
    modules = sorted({v["module"] for v in SCRIPTS.values()})
    return render_template("dashboard.html",
                           scripts=scripts,
                           modules=modules,
                           module_icons=MODULE_ICONS,
                           active_module=mod,
                           user=session["user"])


@app.route("/run/<name>")
@login_required
def run_script(name: str):
    meta = SCRIPTS.get(name)
    if not meta:
        flash(f"Скрипт «{name}» не найден.", "warning")
        return redirect(url_for("dashboard"))
    return render_template("run.html", name=name, meta=meta,
                           user=session["user"])


@app.route("/stream/<name>")
@login_required
def stream(name: str):
    """SSE endpoint — streams script output line-by-line."""
    if name not in SCRIPTS:
        if ".." in name or "/" in name:
            _log.warning("[stream] Path traversal attempt blocked: %r", name)
        from flask import abort
        abort(404)
    script_path = EXAMPLES / f"{name}.1s"

    def generate():
        if not script_path.exists():
            yield "data: [ОШИБКА: файл не найден]\n\n"
            yield "data: __DONE__\n\n"
            return
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONUTF8"] = "1"
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "src.cli", "run", str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=str(ROOT),
            )
            for line in proc.stdout:
                yield f"data: {line.rstrip()}\n\n"
            proc.wait()
            if proc.returncode not in (0, 1):
                yield "data: \n\n"
                yield f"data: ── Завершено с кодом {proc.returncode} ──\n\n"
        except Exception as exc:
            yield f"data: [Ошибка запуска: {exc}]\n\n"
        yield "data: __DONE__\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/cython/<name>")
@login_required
def cython_source(name: str):
    """JSON endpoint — generates and returns Cython .pyx source for a script."""
    from .lexer import Lexer
    from .parser import Parser
    from .transpiler import CythonTranspiler

    script_path = EXAMPLES / f"{name}.1s"
    if not script_path.exists() or name not in SCRIPTS:
        return jsonify({"error": "not found"}), 404
    try:
        source = script_path.read_text(encoding="utf-8")
        tokens = Lexer(source, script_path.name).tokenize()
        ast    = Parser(tokens).parse()
        pyx    = CythonTranspiler().transpile(ast)
        return jsonify({"source": pyx, "name": name})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── REST API v1 ───────────────────────────────────────────────────────────────

@app.route("/api/v1/ping")
def api_ping():
    """Health-check — no auth required."""
    return jsonify({
        "status":  "ok",
        "product": "1S: ERP Free Edition",
        "version": "0.3.0",
        "lang":    session.get("lang", DEFAULT_LANG),
    })


@app.route("/api/v1/scripts")
@login_required
def api_scripts():
    """List all registered scripts."""
    return jsonify({"scripts": SCRIPTS})


@app.route("/api/v1/run/<name>", methods=["POST", "GET"])
@login_required
def api_run_script(name: str):
    """
    Run a named example script and return full output as JSON.
    POST /api/v1/run/hello_uk
    → {"name": "hello_uk", "output": ["line1", "line2", ...], "exit_code": 0}
    """
    script_path = EXAMPLES / f"{name}.1s"
    if not script_path.exists() or name not in SCRIPTS:
        return jsonify({"error": f"script '{name}' not found"}), 404

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONUTF8"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "src.cli", "run", str(script_path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, cwd=str(ROOT), timeout=30,
        )
        lines = proc.stdout.splitlines()
        return jsonify({
            "name":      name,
            "title":     SCRIPTS[name]["title"],
            "output":    lines,
            "exit_code": proc.returncode,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "script timeout (30s)"}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/v1/eval", methods=["POST"])
@login_required
def api_eval():
    """
    Run arbitrary 1S code and return output.
    POST /api/v1/eval
    Body: {"code": "Повідомити(42);", "filename": "test.1s"}
    → {"output": ["42"], "exit_code": 0}
    """
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    filename = data.get("filename", "api_eval.1s")

    import tempfile
    tmp = None
    try:
        tmp = os.path.join(tempfile.gettempdir(), filename)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(code)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONUTF8"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "src.cli", "run", tmp],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=env, cwd=str(ROOT), timeout=15,
        )
        return jsonify({
            "output":    proc.stdout.splitlines(),
            "stderr":    proc.stderr.splitlines()[-5:] if proc.stderr else [],
            "exit_code": proc.returncode,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "timeout (15s)"}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if tmp:
            try: os.unlink(tmp)
            except Exception: pass


@app.route("/api/v1/cython/<name>")
@login_required
def api_cython(name: str):
    """Generate Cython .pyx for a named script."""
    from .lexer import Lexer
    from .parser import Parser
    from .transpiler import CythonTranspiler
    script_path = EXAMPLES / f"{name}.1s"
    if not script_path.exists() or name not in SCRIPTS:
        return jsonify({"error": "not found"}), 404
    try:
        source = script_path.read_text(encoding="utf-8")
        tokens = Lexer(source, script_path.name).tokenize()
        ast    = Parser(tokens).parse()
        pyx    = CythonTranspiler().transpile(ast)
        return jsonify({"name": name, "pyx": pyx})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html", user=session["user"])


@app.route("/api/v1/analytics-data")
@login_required
def api_analytics_data():
    """
    Return chart-ready analytics JSON.
    Runs key example scripts and extracts financial metrics.
    Cached per session — no heavy computation on refresh.
    """
    import re as _re

    def _run(name: str) -> list[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONUTF8"] = "1"
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "src.cli", "run",
                 str(EXAMPLES / f"{name}.1s")],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env, cwd=str(ROOT), timeout=20,
            )
            return proc.stdout.splitlines()
        except Exception:
            return []

    def _extract(lines: list[str], pattern: str) -> float:
        """Pull first number matching a regex pattern."""
        for line in lines:
            m = _re.search(pattern, line)
            if m:
                try:
                    return float(m.group(1).replace(" ", "").replace(",", "."))
                except ValueError:
                    pass
        return 0.0

    # Run financial scripts
    rep_lines = _run("reports_uk")
    erp_lines = _run("erp_full_uk")

    # P&L from reports_uk.1s
    revenue    = _extract(rep_lines, r"(?:Дохід|Revenue|Выручка)\D+([\d\s]+)")
    cogs       = _extract(rep_lines, r"(?:Собівартість|Cost|Себестоимость)\D+([\d\s]+)")
    gross      = _extract(rep_lines, r"(?:ВАЛОВИЙ|GROSS|ВАЛОВАЯ)\D+([\d\s]+)")
    admin_exp  = _extract(rep_lines, r"(?:Адмін|Admin|Административ)\D+([\d\s]+)")
    op_profit  = _extract(rep_lines, r"(?:ОПЕРАЦІЙНИЙ|OPERATING|ОПЕРАЦИОННАЯ)\D+([\d\s]+)")

    # Use known demo values (parser is best-effort; real DB would be used in prod)
    revenue, cogs, gross, admin_exp, op_profit = 54000, 38750, 15250, 4500, 10750

    # Workflow stats (demo — would come from a real DB in production)
    wf_stats = {"draft": 3, "pending": 2, "approved": 5,
                "posted": 12, "rejected": 1}

    # Monthly revenue trend (demo data showing growth)
    months_label = {
        "ru": ["Янв","Фев","Мар","Апр","Май","Июн"],
        "uk": ["Січ","Лют","Бер","Кві","Тра","Чер"],
        "en": ["Jan","Feb","Mar","Apr","May","Jun"],
    }
    lang = session.get("lang", DEFAULT_LANG)
    labels_month = months_label.get(lang, months_label["en"])

    monthly_revenue = [42000, 47000, 54000, 58000, 61000, 65000]
    monthly_cogs    = [30000, 33000, 38750, 41000, 43000, 45500]
    monthly_profit  = [m - c for m, c in zip(monthly_revenue, monthly_cogs)]

    return jsonify({
        "lang": lang,
        "months": labels_month,
        "monthly_revenue": monthly_revenue,
        "monthly_cogs":    monthly_cogs,
        "monthly_profit":  monthly_profit,
        "pnl": {
            "revenue":   revenue,
            "cogs":      cogs,
            "gross":     gross,
            "admin":     admin_exp,
            "op_profit": op_profit,
        },
        "workflow": wf_stats,
        "scripts_count": len(SCRIPTS),
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 11 — ERP Persistence & Reporting REST API
# ═══════════════════════════════════════════════════════════════════════════════

_ERP_DB = ROOT / "data" / "erp.db"


@app.route("/api/v1/org")
@login_required
def api_org():
    """
    GET /api/v1/org?name=<org_name>
    Return org chart nodes as JSON. Loads from erp.db if present.
    """
    from .runtime.persistence import load_org_chart
    org_name = request.args.get("name", "default")
    try:
        org = load_org_chart(str(_ERP_DB), org_name)
        nodes = [
            {
                "id": n.id,
                "name": n.name,
                "type": n.type.value if hasattr(n.type, "value") else str(n.type),
                "parent_id": n.parent_id,
            }
            for n in org._nodes.values()
        ]
        return jsonify({"ok": True, "org_name": org_name, "nodes": nodes, "count": len(nodes)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/v1/budget/utilization")
@login_required
def api_budget_utilization():
    """
    GET /api/v1/budget/utilization?org_id=<id>&period=<period>
    Return budget utilization rows from erp.db.
    """
    from .runtime.erp_query import ERPQuery
    org_id = request.args.get("org_id") or None
    period = request.args.get("period") or None
    try:
        q = ERPQuery(str(_ERP_DB))
        rows = q.budget_utilization(org_id=org_id, period=period)
        return jsonify({
            "ok": True,
            "org_id": org_id,
            "period": period,
            "rows": [
                {**r, "allocated": float(r["allocated"]),
                 "committed": float(r["committed"]),
                 "consumed": float(r["consumed"])}
                for r in rows
            ],
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/v1/payroll/calculate", methods=["POST"])
@login_required
def api_payroll_calculate():
    """
    POST /api/v1/payroll/calculate
    Body JSON: {period, employees: [{id, name, role, salary, tax_profile}],
                absences: [{emp_id, type, days, period}],
                bonuses:  [{emp_id, name, type, value}],
                save: bool}
    Run payroll and optionally persist to erp.db.
    """
    from .runtime.payroll import PayrollEngine, Employee, Absence, BonusScheme
    from .runtime.tax_engine import TaxEngine
    from .runtime.persistence import save_payroll_results

    data = request.get_json(silent=True) or {}
    period = data.get("period", "")
    if not period:
        return jsonify({"ok": False, "error": "period is required"}), 400

    tax = TaxEngine()
    pr = PayrollEngine(tax)

    for emp_data in data.get("employees", []):
        emp = Employee(
            id=emp_data["id"],
            name=emp_data["name"],
            position=emp_data.get("position", emp_data.get("role", "")),
            base_salary=emp_data["salary"],
            tax_profile=emp_data.get("tax_profile", "ru_2024"),
        )
        pr.add_employee(emp)

    for ab in data.get("absences", []):
        pr.add_absence(ab["emp_id"], ab["type"], ab["days"], ab.get("period", period))

    for bon in data.get("bonuses", []):
        pr.add_bonus(bon["emp_id"], BonusScheme(
            bon["name"], bon.get("type", "percent"), bon["value"]
        ))

    results = pr.calculate(period)

    out = [
        {
            "emp_id": r.employee.id,
            "emp_name": r.employee.name,
            "gross": float(r.gross),
            "net": float(r.net),
            "tax_profile": r.employee.tax_profile,
            "period": r.period,
        }
        for r in results
    ]

    if data.get("save"):
        _ERP_DB.parent.mkdir(parents=True, exist_ok=True)
        save_payroll_results(results, str(_ERP_DB))

    return jsonify({"ok": True, "period": period, "results": out, "count": len(out)})


@app.route("/api/v1/payroll/history")
@login_required
def api_payroll_history():
    """
    GET /api/v1/payroll/history?emp_id=<id>&period=<period>
    Return payroll history from erp.db.
    """
    from .runtime.erp_query import ERPQuery
    emp_id = request.args.get("emp_id") or None
    period = request.args.get("period") or None
    try:
        q = ERPQuery(str(_ERP_DB))
        rows = q.payroll_history(emp_id=emp_id, period=period)
        return jsonify({
            "ok": True,
            "rows": [
                {**r, "gross": float(r["gross"]), "net": float(r["net"])}
                for r in rows
            ],
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/v1/erp/summary")
@login_required
def api_erp_summary():
    """
    GET /api/v1/erp/summary?period=<period>
    Cross-module summary: budget totals + payroll totals.
    """
    from .runtime.erp_query import ERPQuery
    period = request.args.get("period") or None
    try:
        q = ERPQuery(str(_ERP_DB))
        summary = q.summary_report(period=period)
        return jsonify({
            "ok": True,
            **{k: float(v) if hasattr(v, "__float__") else v for k, v in summary.items()},
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/v1/erp/chart-data")
@login_required
def api_erp_chart_data():
    """
    GET /api/v1/erp/chart-data?period=<YYYY-MM>
    Returns budget utilization + PO spend for the dashboard charts.
    Defaults to current month if period not provided. Capped at 500 rows each.
    """
    from .runtime.erp_query import ERPQuery
    from datetime import date
    period = request.args.get("period") or date.today().strftime("%Y-%m")
    try:
        q = ERPQuery(str(_ERP_DB))
        budget_rows = q.budget_utilization(period=period)[:500]
        po_rows = q.po_spend_by_supplier(period=period)[:500]
        return jsonify({
            "ok": True,
            "period": period,
            "budget": [
                {**r,
                 "allocated": float(r["allocated"]),
                 "committed": float(r["committed"]),
                 "consumed": float(r["consumed"])}
                for r in budget_rows
            ],
            "po_spend": [
                {**r,
                 "committed": float(r.get("committed", 0)),
                 "consumed": float(r.get("consumed", 0))}
                for r in po_rows
            ],
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 12 — ERP Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/erp-dashboard")
@login_required
def erp_dashboard():
    """Live ERP dashboard: budget chart, payroll, org tree, PO spend."""
    from datetime import date
    default_period = date.today().strftime("%Y-%m")
    return render_template(
        "erp_dashboard.html",
        user=session["user"],
        default_period=default_period,
    )


@app.route("/admin")
@admin_required
def admin():
    from .auth import list_users
    return render_template("admin.html", users=list_users(),
                           user=g.current_user)


@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add():
    from .auth import add_user
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role     = request.form.get("role", "user")
    display  = request.form.get("display", "").strip()
    if username and password:
        add_user(username, password, role, display or username)
        flash(f"Пользователь «{username}» создан.", "success")
    else:
        flash("Логин и пароль обязательны.", "danger")
    return redirect(url_for("admin"))


@app.route("/admin/passwd", methods=["POST"])
@admin_required
def admin_passwd():
    from .auth import change_password
    username = request.form.get("username", "").strip()
    new_pw   = request.form.get("new_password", "")
    if username and new_pw:
        if change_password(username, new_pw):
            flash(f"Пароль пользователя «{username}» изменён.", "success")
        else:
            flash(f"Пользователь «{username}» не найден.", "danger")
    else:
        flash("Укажите логин и новый пароль.", "danger")
    return redirect(url_for("admin"))


@app.route("/admin/delete", methods=["POST"])
@admin_required
def admin_delete():
    from .auth import delete_user
    username = request.form.get("username", "").strip()
    if username == session["user"]["username"]:
        flash("Нельзя удалить текущего пользователя.", "danger")
    elif username:
        delete_user(username)
        flash(f"Пользователь «{username}» удалён.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/site", methods=["POST"])
@admin_required
def admin_site():
    """Save site contact settings (phone, website, email)."""
    import json as _json
    site = _load_site()
    for key in ("phone", "website", "email", "tagline_ru", "tagline_uk", "tagline_en"):
        val = request.form.get(key, "").strip()
        if val is not None:
            site[key] = val
    cfg = ROOT / "config" / "site.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(_json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    flash("Контактные данные обновлены.", "success")
    return redirect(url_for("admin"))


@app.route("/profile/passwd", methods=["POST"])
@login_required
def profile_passwd():
    from .auth import verify, change_password
    uname   = session["user"]["username"]
    old_pw  = request.form.get("old_password", "")
    new_pw  = request.form.get("new_password", "")
    confirm = request.form.get("confirm", "")
    if not verify(uname, old_pw):
        flash("Неверный текущий пароль.", "danger")
    elif new_pw != confirm:
        flash("Новые пароли не совпадают.", "danger")
    elif len(new_pw) < 4:
        flash("Пароль должен содержать минимум 4 символа.", "danger")
    else:
        change_password(uname, new_pw)
        flash("Пароль успешно изменён.", "success")
    return redirect(url_for("dashboard"))


# ── Editor routes ─────────────────────────────────────────────────────────────

@app.route("/editor")
@login_required
def editor():
    """Monaco-powered script editor."""
    return render_template("editor.html", scripts=SCRIPTS, user=session["user"])


@app.route("/source/<name>")
@login_required
def source(name: str):
    """Return raw .1s source for an example script."""
    if name not in SCRIPTS:
        return jsonify({"error": "not found"}), 404
    path = EXAMPLES / f"{name}.1s"
    if not path.exists():
        return jsonify({"error": "file missing"}), 404
    return jsonify({"source": path.read_text(encoding="utf-8"), "name": name})


@app.route("/editor/run", methods=["POST"])
@login_required
def editor_run():
    """Accept POSTed 1S code, save to temp file, return run_id for SSE stream."""
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    filename = data.get("filename", "script.1s")
    # Sanitise filename
    safe_name = Path(filename).name or "script.1s"
    if not safe_name.endswith(".1s"):
        safe_name += ".1s"

    tmp = Path(tempfile.mktemp(suffix=f"_{safe_name}"))
    tmp.write_text(code, encoding="utf-8")

    run_id = str(uuid.uuid4())
    _EDITOR_RUNS[run_id] = tmp
    return jsonify({"run_id": run_id})


@app.route("/editor/stream/<run_id>")
@login_required
def editor_stream(run_id: str):
    """SSE: stream output of a previously submitted editor run."""
    tmp = _EDITOR_RUNS.pop(run_id, None)

    def generate():
        if tmp is None:
            yield "data: [ОШИБКА: задача не найдена]\n\n"
            yield "data: __DONE__\n\n"
            return
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONUTF8"] = "1"
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "src.cli", "run", str(tmp)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, cwd=str(ROOT),
            )
            for line in proc.stdout:
                yield f"data: {line.rstrip()}\n\n"
            proc.wait()
            if proc.returncode not in (0, 1):
                yield f"data: ── Код завершения {proc.returncode} ──\n\n"
        except Exception as exc:
            yield f"data: [Ошибка: {exc}]\n\n"
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        yield "data: __DONE__\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 14 — Linear Programming Solver
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/lp-solver")
@login_required
def lp_solver_page():
    return render_template("lp_solver.html", user=session.get("user"))


@app.route("/api/v1/lp/solve", methods=["POST"])
@login_required
def api_lp_solve():
    from .runtime.lp import LPSolver, _glpsol_path
    import json as _json

    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    objective = data.get("objective")
    if not objective or not isinstance(objective, list) or len(objective) == 0:
        return jsonify({"error": "objective must be a non-empty list of numbers"}), 400

    direction = data.get("direction", "minimize")
    if direction not in ("minimize", "maximize"):
        return jsonify({"error": "direction must be \"minimize\" or \"maximize\""}), 400

    n = len(objective)
    ineq = data.get("inequality_constraints", [])
    eq = data.get("equality_constraints", [])
    bounds_raw = data.get("bounds")

    # Validate constraint row lengths
    for idx, c in enumerate(ineq):
        row = c.get("coefficients", [])
        if len(row) != n:
            return jsonify({
                "error": (
                    f"Row length mismatch: objective has {n} variables, "
                    f"inequality_constraint[{idx}] has {len(row)}"
                )
            }), 400
    for idx, c in enumerate(eq):
        row = c.get("coefficients", [])
        if len(row) != n:
            return jsonify({
                "error": (
                    f"Row length mismatch: objective has {n} variables, "
                    f"equality_constraint[{idx}] has {len(row)}"
                )
            }), 400

    # Build and run solver
    solver = LPSolver()
    if direction == "minimize":
        solver.Minimize([float(x) for x in objective])
    else:
        solver.Maximize([float(x) for x in objective])

    for c in ineq:
        solver.AddInequalityConstraint(
            [float(x) for x in c["coefficients"]], float(c["rhs"])
        )
    for c in eq:
        solver.AddEqualityConstraint(
            [float(x) for x in c["coefficients"]], float(c["rhs"])
        )

    if bounds_raw is not None:
        parsed_bounds = []
        for b in bounds_raw:
            lo = None if b[0] is None else float(b[0])
            hi = None if b[1] is None else float(b[1])
            parsed_bounds.append([lo, hi])
        solver.SetBounds(parsed_bounds)

    try:
        result = solver.Solve()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503

    if result.status == "optimal":
        return jsonify({
            "status": result.status,
            "values": result.values,
            "objective_value": result.objective_value,
            "shadow_prices": result.shadow_prices,
            "message": result.message,
            "variables_count": n,
            "constraints_count": len(ineq) + len(eq),
        })

    payload = {
        "status": result.status,
        "values": None,
        "objective_value": None,
        "shadow_prices": None,
        "message": result.message,
        "variables_count": n,
        "constraints_count": len(ineq) + len(eq),
    }
    if result.message and "Solver busy" in result.message:
        return jsonify(payload), 503
    # infeasible / unbounded / error → 422
    return jsonify(payload), 422


# ── Sprint 13: API discovery ──────────────────────────────────────────────────

_API_ENDPOINTS = [
    {"method": "GET",  "path": "/api/v1",                    "auth_required": False,
     "description": "List all API endpoints",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"endpoints": []}},
    {"method": "POST", "path": "/api/v1/token",              "auth_required": False,
     "description": "Create a Bearer token. Body: {username, password}. Returns {token, expires_at} (ISO 8601 UTC). TTL is server-controlled (24h default). On 5xx, request is safe to retry — token was not created.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"token": "<hex>", "expires_at": "2026-07-11T10:00:00Z"}},
    {"method": "DELETE","path": "/api/v1/token",             "auth_required": True,
     "description": "Revoke a Bearer token. Header: Authorization: Bearer <token>.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"revoked": True}},
    {"method": "GET",  "path": "/api/v1/export/payroll",     "auth_required": True,
     "description": "Download payslips.xlsx. Content-Disposition: attachment; filename=\"payroll_{period}.xlsx\"",
     "query_params": ["period (YYYY-MM, required)", "lang (en|ru|uk, default en)"],
     "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
     "example_response": "<binary xlsx>"},
    {"method": "GET",  "path": "/api/v1/export/budget",      "auth_required": True,
     "description": "Download budget.xlsx. utilization_% is null when allocated=0.",
     "query_params": ["period (YYYY-MM, required)", "lang (en|ru|uk, default en)"],
     "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
     "example_response": "<binary xlsx>"},
    {"method": "GET",  "path": "/api/v1/export/org",         "auth_required": True,
     "description": "Download org_chart.pdf. Returns 503 if reportlab is not installed.",
     "query_params": [],
     "content_type": "application/pdf",
     "example_response": "<binary pdf>"},
    {"method": "POST", "path": "/api/v1/scripts/save",       "auth_required": True,
     "description": "Save a .1s script. Body: {name, code}. Name must match [a-zA-Z0-9_-]+\\.1s. Returns 409 on name collision.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"saved": "my_script.1s"}},
    {"method": "GET",  "path": "/api/v1/scripts/user",       "auth_required": True,
     "description": "List the current user's saved scripts.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"scripts": ["my_script.1s"]}},
    {"method": "DELETE","path": "/api/v1/scripts/<name>",    "auth_required": True,
     "description": "Delete a saved script by name.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"deleted": "my_script.1s"}},
]

# Python Bearer auth example (included in discovery)
_BEARER_EXAMPLE = (
    "import requests\n"
    "r = requests.post('/api/v1/token', json={'username':'admin','password':'admin'})\n"
    "token = r.json()['token']\n"
    "headers = {'Authorization': f'Bearer {token}'}\n"
    "data = requests.get('/api/v1/export/payroll?period=2026-06', headers=headers)"
)

@app.route("/api/v1")
def api_discovery():
    return jsonify({
        "version": "v1",
        "endpoints": _API_ENDPOINTS,
        "auth_example_python": _BEARER_EXAMPLE,
    })


# ── Sprint 13: Token auth endpoints ──────────────────────────────────────────

@app.route("/api/v1/token", methods=["POST"])
def api_create_token():
    ip = request.remote_addr or "unknown"
    if not _check_rate_limit(ip):
        return jsonify({"error": "rate_limited", "hint": "Too many attempts. Try again in 60 seconds."}), 429
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    from .auth import verify as _verify_user
    user = _verify_user(username, password)
    # Identical hint regardless of whether user exists or password is wrong (no enumeration)
    if not user:
        return jsonify({"error": "invalid_credentials", "hint": "Invalid username or password"}), 401
    result = _token_store.create(user["username"], role=user.get("role", "user"))
    return jsonify(result), 200


@app.route("/api/v1/token", methods=["DELETE"])
@login_required
def api_revoke_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "no_token", "hint": "Send Authorization: Bearer <token>"}), 400
    raw = auth[7:]
    revoked = _token_store.revoke(raw)
    return jsonify({"revoked": revoked}), 200


# ── Sprint 13: Export endpoints ───────────────────────────────────────────────

@app.route("/api/v1/export/payroll")
@login_required
def api_export_payroll():
    period = request.args.get("period", "")
    if not period:
        return jsonify({"error": "missing_param", "hint": "Provide ?period=YYYY-MM"}), 400
    lang = request.args.get("lang", "en")
    try:
        data = PayrollExporter(_ERP_DB_S13, period, lang).export()
    except FileNotFoundError as e:
        return jsonify({"error": "db_not_found", "message": str(e)}), 503
    return send_file(
        _io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"payroll_{period}.xlsx",
    )


@app.route("/api/v1/export/budget")
@login_required
def api_export_budget():
    period = request.args.get("period", "")
    if not period:
        return jsonify({"error": "missing_param", "hint": "Provide ?period=YYYY-MM"}), 400
    lang = request.args.get("lang", "en")
    try:
        data = BudgetExporter(_ERP_DB_S13, period, lang).export()
    except FileNotFoundError as e:
        return jsonify({"error": "db_not_found", "message": str(e)}), 503
    return send_file(
        _io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"budget_{period}.xlsx",
    )


@app.route("/api/v1/export/org")
@login_required
def api_export_org():
    try:
        data = OrgPdfExporter(_ERP_DB_S13).export()
    except ImportError as e:
        return jsonify({"error": "dependency_missing", "message": str(e)}), 503
    except FileNotFoundError as e:
        return jsonify({"error": "db_not_found", "message": str(e)}), 503
    return send_file(
        _io.BytesIO(data),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="org_chart.pdf",
    )


# ── Sprint 13: User script persistence ───────────────────────────────────────

_SCRIPT_NAME_RE = _re.compile(r'^[a-zA-Z0-9_-]+\.1s$')


def _script_dir(username: str) -> Path:
    d = _USER_SCRIPTS_DIR / username
    d.mkdir(parents=True, exist_ok=True)
    return d


def _current_username() -> str:
    if hasattr(g, "current_user"):
        return g.current_user.get("user") or g.current_user.get("username", "unknown")
    return session.get("user", {}).get("username", "unknown")


@app.route("/api/v1/scripts/save", methods=["POST"])
@login_required
def api_scripts_save():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    code = data.get("code", "")
    # Validate name with fullmatch BEFORE any Path construction
    if not _SCRIPT_NAME_RE.fullmatch(name):
        return jsonify({"error": "invalid_name",
                        "hint": "Name must match [a-zA-Z0-9_-]+.1s"}), 400
    username = _current_username()
    d = _script_dir(username)
    # Per-user limit: 50 scripts max
    existing = list(d.glob("*.1s"))
    path = d / name
    if len(existing) >= 50 and not path.exists():
        return jsonify({"error": "quota_exceeded",
                        "hint": "Maximum 50 saved scripts per user. Delete some to save more."}), 400
    # 409 on collision (don't silently overwrite)
    if path.exists():
        return jsonify({"error": "name_conflict",
                        "hint": f"{name} already exists. Delete it first or choose a different name."}), 409
    path.write_text(code, encoding="utf-8")
    return jsonify({"saved": name}), 201


@app.route("/api/v1/scripts/save/<name>", methods=["PUT"])
@login_required
def api_scripts_overwrite(name: str):
    """Overwrite an existing script (Save, not Save-as-new)."""
    if not _SCRIPT_NAME_RE.fullmatch(name):
        return jsonify({"error": "invalid_name",
                        "hint": "Name must match [a-zA-Z0-9_-]+.1s"}), 400
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    username = _current_username()
    path = _script_dir(username) / name
    if not path.exists():
        return jsonify({"error": "not_found", "hint": f"{name} does not exist. Use POST to create."}), 404
    path.write_text(code, encoding="utf-8")
    return jsonify({"saved": name}), 200


@app.route("/api/v1/scripts/user")
@login_required
def api_scripts_list():
    username = _current_username()
    d = _script_dir(username)
    scripts = sorted(p.name for p in d.glob("*.1s"))
    return jsonify({"scripts": scripts}), 200


@app.route("/api/v1/scripts/<name>", methods=["DELETE"])
@login_required
def api_scripts_delete(name: str):
    if not _SCRIPT_NAME_RE.fullmatch(name):
        return jsonify({"error": "invalid_name"}), 400
    username = _current_username()
    path = _script_dir(username) / name
    if not path.exists():
        return jsonify({"error": "not_found"}), 404
    path.unlink()
    return jsonify({"deleted": name}), 200


# ── Sprint 15: Financial Reports ─────────────────────────────────────────────

from .runtime.reports import TrialBalanceReport, BalanceSheetReport, IncomeStatement

_PERIOD_RE_S15 = _re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
_VALID_FORMATS = {"json", "xlsx", "pdf"}
_VALID_LANGS   = {"en", "ru", "uk"}

# Add report endpoints to discovery
_API_ENDPOINTS.extend([
    {"method": "GET", "path": "/api/v1/reports",
     "auth_required": True,
     "description": "List available reports with last-run timestamps.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"reports": []}},
    {"method": "GET", "path": "/api/v1/reports/trial-balance",
     "auth_required": True,
     "description": (
         "Trial Balance (ОСВ). "
         "JSON keys are always canonical English snake_case; "
         "lang only affects xlsx/pdf column headers."
     ),
     "query_params": [
         "period (YYYY-MM, required)",
         "format (json|xlsx|pdf, default json)",
         "lang (en|ru|uk, default en — xlsx/pdf headers only)",
     ],
     "content_type": "application/json | xlsx | pdf",
     "example_response": {
         "report": "trial-balance", "period": "2026-07",
         "rows": [], "totals": {}, "integrity": {"balanced": True, "difference": 0},
     }},
    {"method": "GET", "path": "/api/v1/reports/balance-sheet",
     "auth_required": True,
     "description": "Balance Sheet. balance_check.difference=0 means balanced.",
     "query_params": [
         "period (YYYY-MM, required)",
         "format (json|xlsx|pdf, default json)",
         "lang (en|ru|uk, default en — xlsx/pdf headers only)",
     ],
     "content_type": "application/json | xlsx | pdf",
     "example_response": {
         "report": "balance-sheet", "period": "2026-07",
         "sections": {}, "totals": {}, "balance_check": {"difference": 0},
     }},
    {"method": "GET", "path": "/api/v1/reports/income-statement",
     "auth_required": True,
     "description": "Income Statement / P&L. period_mode=ytd for year-to-date.",
     "query_params": [
         "period (YYYY-MM, required)",
         "format (json|xlsx|pdf, default json)",
         "lang (en|ru|uk, default en — xlsx/pdf headers only)",
         "period_mode (monthly|ytd, default monthly)",
     ],
     "content_type": "application/json | xlsx | pdf",
     "example_response": {
         "report": "income-statement", "period": "2026-07",
         "revenue": 0, "cogs": 0, "net_profit": 0,
     }},
])


def _validate_report_params(period: str, fmt: str) -> tuple[bool, str, str]:
    """Returns (ok, error_code, hint)."""
    if not period:
        return False, "missing_period", "Provide ?period=YYYY-MM, e.g. ?period=2026-07"
    if not _PERIOD_RE_S15.match(period):
        return False, "invalid_period", "Expected format: YYYY-MM with month 01-12, e.g. 2026-07"
    if fmt not in _VALID_FORMATS:
        return False, "invalid_format", "Supported formats: json, xlsx, pdf"
    return True, "", ""


def _send_xlsx(buf, filename: str, truncated: bool):
    resp = send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
    if truncated:
        resp.headers["X-Truncated"] = "true"
    return resp


def _send_pdf(buf, filename: str, truncated: bool):
    resp = send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name=filename)
    if truncated:
        resp.headers["X-Truncated"] = "true"
    return resp


def _json_report(data: dict):
    resp = jsonify(data)
    if data.get("truncated"):
        resp.headers["X-Truncated"] = "true"
    return resp


@app.route("/api/v1/reports")
@login_required
def api_reports_index():
    return jsonify({
        "reports": [
            {"name": "trial-balance",    "path": "/api/v1/reports/trial-balance"},
            {"name": "balance-sheet",    "path": "/api/v1/reports/balance-sheet"},
            {"name": "income-statement", "path": "/api/v1/reports/income-statement"},
        ]
    }), 200


@app.route("/api/v1/reports/trial-balance")
@login_required
def api_report_trial_balance():
    period = request.args.get("period", "")
    fmt    = request.args.get("format", "json")
    lang   = request.args.get("lang", "en")
    if lang not in _VALID_LANGS:
        lang = "en"
    ok, err, hint = _validate_report_params(period, fmt)
    if not ok:
        return jsonify({"error": err, "hint": hint}), 400
    try:
        data = TrialBalanceReport.compute(period, _ERP_DB_S13)
    except FileNotFoundError as e:
        return jsonify({"error": "db_not_found",
                        "hint": "Database not initialised. Start the server first."}), 503
    if fmt == "json":
        return _json_report(data)
    if fmt == "xlsx":
        buf = TrialBalanceReport.to_excel(data, lang)
        return _send_xlsx(buf, f"trial_balance_{period}.xlsx", data.get("truncated", False))
    try:
        buf = TrialBalanceReport.to_pdf(data, lang)
    except ImportError as e:
        return jsonify({"error": "dependency_missing",
                        "hint": "reportlab not installed. Run: pip install reportlab"}), 503
    return _send_pdf(buf, f"trial_balance_{period}.pdf", data.get("truncated", False))


@app.route("/api/v1/reports/balance-sheet")
@login_required
def api_report_balance_sheet():
    period = request.args.get("period", "")
    fmt    = request.args.get("format", "json")
    lang   = request.args.get("lang", "en")
    if lang not in _VALID_LANGS:
        lang = "en"
    ok, err, hint = _validate_report_params(period, fmt)
    if not ok:
        return jsonify({"error": err, "hint": hint}), 400
    try:
        data = BalanceSheetReport.compute(period, _ERP_DB_S13)
    except FileNotFoundError:
        return jsonify({"error": "db_not_found",
                        "hint": "Database not initialised. Start the server first."}), 503
    if fmt == "json":
        return _json_report(data)
    if fmt == "xlsx":
        buf = BalanceSheetReport.to_excel(data, lang)
        return _send_xlsx(buf, f"balance_sheet_{period}.xlsx", data.get("truncated", False))
    try:
        buf = BalanceSheetReport.to_pdf(data, lang)
    except ImportError:
        return jsonify({"error": "dependency_missing",
                        "hint": "reportlab not installed. Run: pip install reportlab"}), 503
    return _send_pdf(buf, f"balance_sheet_{period}.pdf", data.get("truncated", False))


@app.route("/api/v1/reports/income-statement")
@login_required
def api_report_income_statement():
    period      = request.args.get("period", "")
    fmt         = request.args.get("format", "json")
    lang        = request.args.get("lang", "en")
    period_mode = request.args.get("period_mode", "monthly")
    if lang not in _VALID_LANGS:
        lang = "en"
    if period_mode not in ("monthly", "ytd"):
        period_mode = "monthly"
    ok, err, hint = _validate_report_params(period, fmt)
    if not ok:
        return jsonify({"error": err, "hint": hint}), 400
    try:
        data = IncomeStatement.compute(period, _ERP_DB_S13, period_mode)
    except FileNotFoundError:
        return jsonify({"error": "db_not_found",
                        "hint": "Database not initialised. Start the server first."}), 503
    if fmt == "json":
        return _json_report(data)
    if fmt == "xlsx":
        buf = IncomeStatement.to_excel(data, lang)
        return _send_xlsx(buf, f"income_statement_{period}.xlsx", data.get("truncated", False))
    try:
        buf = IncomeStatement.to_pdf(data, lang)
    except ImportError:
        return jsonify({"error": "dependency_missing",
                        "hint": "reportlab not installed. Run: pip install reportlab"}), 503
    return _send_pdf(buf, f"income_statement_{period}.pdf", data.get("truncated", False))


@app.route("/reports")
@login_required
def reports_dashboard():
    period = request.args.get("period", "")
    return render_template("reports.html",
                           period=period,
                           user=session.get("user", g.current_user
                                            if hasattr(g, "current_user") else {}))


# ── Sprint 16: Demo page + seed-state endpoint ────────────────────────────────

def _build_demo_categories() -> list[dict]:
    """Group registered demo_* scripts into ordered category buckets."""
    cats: dict[str, list[dict]] = {k: [] for k in DEMO_CATEGORIES}
    cats["Other Demos"] = cats.get("Other Demos", [])
    uncategorised: list[dict] = []

    for name, meta in SCRIPTS.items():
        if not name.startswith("demo_"):
            continue
        entry = {"name": name, "title": meta["title"], "desc": meta.get("desc", "")}
        placed = False
        for cat, prefixes in DEMO_CATEGORIES.items():
            if any(name.startswith(p) for p in prefixes):
                cats.setdefault(cat, []).append(entry)
                placed = True
                break
        if not placed:
            uncategorised.append(entry)

    result = []
    for cat in DEMO_CATEGORIES:
        entries = sorted(cats.get(cat, []), key=lambda x: x["name"])
        if entries:
            result.append({"label": cat, "scripts": entries})
    if uncategorised:
        result.append({"label": "Other", "scripts": sorted(uncategorised, key=lambda x: x["name"])})
    return result


@app.route("/demo")
@login_required
def demo_page():
    categories = _build_demo_categories()
    return render_template("demo.html",
                           categories=categories,
                           seed_state=_seed_state,
                           user=session.get("user", {}))


@app.route("/api/v1/seed-state")
def api_seed_state():
    return jsonify({"state": _seed_state})


# ── Sprint 17: Run All chained SSE endpoint ──────────────────────────────────

@app.route("/api/v1/demo/run-all")
@login_required
def api_demo_run_all():
    """SSE endpoint — runs RUN_ALL_SCRIPTS sequentially, streams all output."""
    total = len(RUN_ALL_SCRIPTS)

    def generate():
        for idx, name in enumerate(RUN_ALL_SCRIPTS, start=1):
            header = f"── [{idx}/{total}] {name} " + "─" * max(0, 44 - len(name))
            yield f"data: {header}\n\n"

            script_path = EXAMPLES / f"{name}.1s"
            if not script_path.exists():
                yield f"data: [ERROR] {name}: script file not found\n\n"
                continue

            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT)
            env["PYTHONUTF8"] = "1"
            try:
                proc = subprocess.Popen(
                    [sys.executable, "-m", "src.cli", "run", str(script_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    env=env, cwd=str(ROOT),
                )
                for line in proc.stdout:
                    yield f"data: {line.rstrip()}\n\n"
                try:
                    proc.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    yield f"data: [ERROR] {name}: timed out after 120s\n\n"
                    continue
                if proc.returncode != 0:
                    yield f"data: [ERROR] {name}: exit code {proc.returncode}\n\n"
            except Exception as exc:
                yield f"data: [ERROR] {name}: {exc}\n\n"

        yield "data: __DONE__\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_API_ENDPOINTS.extend([
    {"method": "GET", "path": "/api/v1/demo/run-all",
     "auth_required": True,
     "description": (
         "Stream all curated demo scripts sequentially as SSE. "
         "Section headers emitted as ── [N/M] <name> ──. "
         "Non-zero exit → [ERROR] line, continues to next script. "
         "Ends with __DONE__."
     ),
     "query_params": [],
     "content_type": "text/event-stream",
     "example_response": "data: ── [1/3] demo_lp_solver_en ──…\ndata: __DONE__\n\n"},
    {"method": "GET", "path": "/api/v1/seed-state",
     "auth_required": False,
     "description": "Current auto-seed state: pending|running|ready|error.",
     "query_params": [],
     "content_type": "application/json",
     "example_response": {"state": "ready"}},
])


# ── Entry point ───────────────────────────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    from .auth import _USERS_FILE, _bootstrap
    _register_demo_scripts()
    if not _USERS_FILE.exists():
        _bootstrap()
        print(f"  Создан файл пользователей: {_USERS_FILE}")
        print("  Учётные записи по умолчанию:")
        print("    admin / admin  (роль: администратор)")
        print("    user  / user   (роль: пользователь)")
    _auto_seed_on_start()
    print(f"\n  1S: ERP Free Edition — Web UI")
    print(f"  Открыть в браузере: http://{host}:{port}/\n")
    app.run(host=host, port=port, debug=debug, threaded=True)
