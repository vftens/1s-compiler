"""
1S: ERP Free Edition — UI translations.
Supported languages: ru (Russian), uk (Ukrainian), en (English).
"""
from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── Navigation / sidebar ────────────────────────────────────────────────
    "nav_navigation": {
        "ru": "Навигация",
        "uk": "Навігація",
        "en": "Navigation",
    },
    "nav_all_modules": {
        "ru": "Все модули",
        "uk": "Всі модулі",
        "en": "All Modules",
    },
    "nav_editor": {
        "ru": "Редактор",
        "uk": "Редактор",
        "en": "Editor",
    },
    "nav_modules": {
        "ru": "Модули",
        "uk": "Модулі",
        "en": "Modules",
    },
    "nav_admin": {
        "ru": "Администрирование",
        "uk": "Адміністрування",
        "en": "Administration",
    },
    "nav_users": {
        "ru": "Пользователи",
        "uk": "Користувачі",
        "en": "Users",
    },

    # ── Header ──────────────────────────────────────────────────────────────
    "header_panel": {
        "ru": "⚙ Панель",
        "uk": "⚙ Панель",
        "en": "⚙ Panel",
    },
    "header_logout": {
        "ru": "Выход →",
        "uk": "Вихід →",
        "en": "Logout →",
    },

    # ── Login page ──────────────────────────────────────────────────────────
    "login_subtitle": {
        "ru": "Система управления предприятием",
        "uk": "Система управління підприємством",
        "en": "Enterprise Management System",
    },
    "login_title": {
        "ru": "Вход в систему",
        "uk": "Вхід до системи",
        "en": "Sign In",
    },
    "login_username_label": {
        "ru": "Логин",
        "uk": "Логін",
        "en": "Username",
    },
    "login_username_placeholder": {
        "ru": "Введите логин",
        "uk": "Введіть логін",
        "en": "Enter username",
    },
    "login_password_label": {
        "ru": "Пароль",
        "uk": "Пароль",
        "en": "Password",
    },
    "login_password_placeholder": {
        "ru": "Введите пароль",
        "uk": "Введіть пароль",
        "en": "Enter password",
    },
    "login_button": {
        "ru": "Войти →",
        "uk": "Увійти →",
        "en": "Sign In →",
    },
    "login_default_hint": {
        "ru": "По умолчанию",
        "uk": "За замовчуванням",
        "en": "Default credentials",
    },
    "login_footer": {
        "ru": "1S: ERP Free Edition · Демонстрационный стенд",
        "uk": "1S: ERP Free Edition · Демонстраційний стенд",
        "en": "1S: ERP Free Edition · Demo",
    },
    "login_error": {
        "ru": "Неверный логин или пароль.",
        "uk": "Невірний логін або пароль.",
        "en": "Invalid username or password.",
    },

    # ── Dashboard ───────────────────────────────────────────────────────────
    "dash_title": {
        "ru": "🏠 Рабочий стол",
        "uk": "🏠 Робочий стіл",
        "en": "🏠 Dashboard",
    },
    "dash_filter_all": {
        "ru": "Все",
        "uk": "Всі",
        "en": "All",
    },
    "dash_empty": {
        "ru": "В этом модуле нет доступных скриптов.",
        "uk": "У цьому модулі немає доступних скриптів.",
        "en": "No scripts available in this module.",
    },
    "dash_run_btn": {
        "ru": "▶ Запустить",
        "uk": "▶ Запустити",
        "en": "▶ Run",
    },
    "dash_logged_as": {
        "ru": "Вы вошли как",
        "uk": "Ви увійшли як",
        "en": "Logged in as",
    },
    "dash_change_password": {
        "ru": "🔑 Сменить пароль",
        "uk": "🔑 Змінити пароль",
        "en": "🔑 Change Password",
    },
    "dash_pw_modal_title": {
        "ru": "🔑 Смена пароля",
        "uk": "🔑 Зміна пароля",
        "en": "🔑 Change Password",
    },
    "dash_pw_current": {
        "ru": "Текущий пароль",
        "uk": "Поточний пароль",
        "en": "Current password",
    },
    "dash_pw_new": {
        "ru": "Новый пароль",
        "uk": "Новий пароль",
        "en": "New password",
    },
    "dash_pw_confirm": {
        "ru": "Подтверждение",
        "uk": "Підтвердження",
        "en": "Confirm password",
    },
    "dash_pw_save": {
        "ru": "Сохранить",
        "uk": "Зберегти",
        "en": "Save",
    },

    # ── Module names ─────────────────────────────────────────────────────────
    "mod_other": {
        "ru": "Прочее",
        "uk": "Інше",
        "en": "Other",
    },
    "mod_accounting": {
        "ru": "Бухгалтерия",
        "uk": "Бухгалтерія",
        "en": "Accounting",
    },
    "mod_trade": {
        "ru": "Торговля",
        "uk": "Торгівля",
        "en": "Trade",
    },
    "mod_payroll": {
        "ru": "ЗУП",
        "uk": "ЗУП",
        "en": "Payroll",
    },
    "mod_ukrainian": {
        "ru": "Українська",
        "uk": "Українська",
        "en": "Ukrainian",
    },

    # ── Run page ─────────────────────────────────────────────────────────────
    "run_tab_exec": {
        "ru": "▶ Выполнение",
        "uk": "▶ Виконання",
        "en": "▶ Execution",
    },
    "run_tab_cython": {
        "ru": "⚡ Cython .pyx",
        "uk": "⚡ Cython .pyx",
        "en": "⚡ Cython .pyx",
    },
    "run_btn": {
        "ru": "▶ Запустить",
        "uk": "▶ Запустити",
        "en": "▶ Run",
    },
    "run_clear": {
        "ru": "🗑 Очистить",
        "uk": "🗑 Очистити",
        "en": "🗑 Clear",
    },
    "run_copy": {
        "ru": "⎘ Копировать",
        "uk": "⎘ Копіювати",
        "en": "⎘ Copy",
    },
    "run_back": {
        "ru": "← Назад",
        "uk": "← Назад",
        "en": "← Back",
    },
    "run_status_idle": {
        "ru": "ожидание",
        "uk": "очікування",
        "en": "idle",
    },
    "run_status_running": {
        "ru": "⏳ выполняется…",
        "uk": "⏳ виконується…",
        "en": "⏳ running…",
    },
    "run_status_done": {
        "ru": "✓ завершено",
        "uk": "✓ завершено",
        "en": "✓ completed",
    },
    "run_status_error": {
        "ru": "✗ ошибка соединения",
        "uk": "✗ помилка з'єднання",
        "en": "✗ connection error",
    },
    "run_hint": {
        "ru": "// Нажмите «Запустить» для выполнения скрипта",
        "uk": "// Натисніть «Запустити» для виконання скрипту",
        "en": "// Press \"Run\" to execute the script",
    },
    "run_lines": {
        "ru": "строк",
        "uk": "рядків",
        "en": "lines",
    },
    "run_cython_title": {
        "ru": "⚡ Cython — скомпилированный .pyx",
        "uk": "⚡ Cython — скомпільований .pyx",
        "en": "⚡ Cython — compiled .pyx",
    },

    # ── Editor page ───────────────────────────────────────────────────────────
    "editor_title": {
        "ru": "✏️ Редактор 1S",
        "uk": "✏️ Редактор 1S",
        "en": "✏️ 1S Editor",
    },
    "editor_source_label": {
        "ru": "Исходный код .1s",
        "uk": "Вихідний код .1s",
        "en": "Source code .1s",
    },
    "editor_output_label": {
        "ru": "Вывод программы",
        "uk": "Вивід програми",
        "en": "Output",
    },
    "editor_hint": {
        "ru": "// Напишите код слева и нажмите ▶ Запустить",
        "uk": "// Напишіть код зліва і натисніть ▶ Запустити",
        "en": "// Write code on the left and press ▶ Run",
    },
    "editor_ready": {
        "ru": "— готов —",
        "uk": "— готово —",
        "en": "— ready —",
    },
    "editor_cleared": {
        "ru": "// Очищено.",
        "uk": "// Очищено.",
        "en": "// Cleared.",
    },

    # ── Admin page ────────────────────────────────────────────────────────────
    "admin_title": {
        "ru": "Управление пользователями",
        "uk": "Управління користувачами",
        "en": "User Management",
    },
    "admin_add_user": {
        "ru": "Добавить пользователя",
        "uk": "Додати користувача",
        "en": "Add User",
    },

    # ── Chess Board ───────────────────────────────────────────────────────────
    "chess_title": {
        "ru": "Шахматная ведомость",
        "uk": "Шахматна відомість",
        "en": "Chess Board Report",
    },
    "chess_desc": {
        "ru": "Матрица оборотов Дт×Кт: наглядный перекрёстный анализ всех счетов",
        "uk": "Матриця оборотів Дт×Кт: наочний перехресний аналіз усіх рахунків",
        "en": "Debit×Credit turnover matrix: cross-tab view of all accounts",
    },
    "chess_dr":    {"ru": "Дт",      "uk": "Дт",      "en": "Dr"},
    "chess_cr":    {"ru": "Кт",      "uk": "Кт",      "en": "Cr"},
    "chess_total_dr": {"ru": "ИТОГО Дт", "uk": "РАЗОМ Дт", "en": "TOTAL Dr"},
    "chess_total_cr": {"ru": "ИТОГО Кт", "uk": "РАЗОМ Кт", "en": "TOTAL Cr"},
    "chess_legend":   {"ru": "Условные обозначения", "uk": "Легенда", "en": "Legend"},
    "chess_balance":  {
        "ru": "Итого оборотов: {n}  (Σ Дт = Σ Кт ✓)",
        "uk": "Загальний оборот: {n}  (Σ Дт = Σ Кт ✓)",
        "en": "Grand total: {n}  (Σ Dr = Σ Cr ✓)",
    },
}


def get(key: str, lang: str) -> str:
    """Return translated string for key in lang, fallback to 'ru'."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get("ru") or key


def t(lang: str) -> dict[str, str]:
    """Return a flat dict of all translations for the given language."""
    return {k: get(k, lang) for k in TRANSLATIONS}
