"""
1S: ERP Free Edition — Web UI server.
Run:  python -m src.cli serve [--port 5000] [--host 127.0.0.1]
"""
from __future__ import annotations
import os
import sys
import subprocess
from functools import wraps
from pathlib import Path
from flask import (Flask, render_template, request, redirect, url_for,
                   session, Response, flash, stream_with_context, jsonify)

ROOT     = Path(__file__).parent.parent
EXAMPLES = ROOT / "examples"

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
}

MODULE_ICONS = {
    "Прочее":      "💬",
    "Українська":  "🇺🇦",
    "Бухгалтерия": "📒",
    "Торговля":    "🛒",
    "ЗУП":         "👥",
}

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
