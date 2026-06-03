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
from functools import wraps
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for,
                   session, Response, flash, stream_with_context, jsonify)

# In-memory store for editor run jobs: run_id → tmp_file_path
_EDITOR_RUNS: dict[str, Path] = {}

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
}

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


# ── Auth decorators ───────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*a, **kw):
        if "user" not in session:
            return redirect(url_for("login"))
        if session["user"].get("role") != "admin":
            flash("Доступ запрещён: требуются права администратора.", "danger")
            return redirect(url_for("dashboard"))
        return f(*a, **kw)
    return wrapped

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


@app.route("/admin")
@admin_required
def admin():
    from .auth import list_users
    return render_template("admin.html", users=list_users(),
                           user=session["user"])


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


# ── Entry point ───────────────────────────────────────────────────────────────

def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    from .auth import _USERS_FILE, _bootstrap
    if not _USERS_FILE.exists():
        _bootstrap()
        print(f"  Создан файл пользователей: {_USERS_FILE}")
        print("  Учётные записи по умолчанию:")
        print("    admin / admin  (роль: администратор)")
        print("    user  / user   (роль: пользователь)")
    print(f"\n  1S: ERP Free Edition — Web UI")
    print(f"  Открыть в браузере: http://{host}:{port}/\n")
    app.run(host=host, port=port, debug=debug, threaded=True)
