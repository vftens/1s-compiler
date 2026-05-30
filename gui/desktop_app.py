"""
1S: ERP Free Edition — Desktop GUI (чистый Python, без Node.js/Electron).

Использует pywebview — открывает нативное окно ОС (Edge/WebKit)
с Flask-интерфейсом внутри. Никакого npm, никакого Chromium.

Запуск:
    python gui/desktop_app.py

Сборка в .exe (Windows, ~30 МБ vs 150 МБ у Electron):
    pyinstaller gui/desktop_app.py --onefile --noconsole \
        --add-data "src;src" --add-data "examples;examples" \
        --add-data "config;config" \
        --icon gui/assets/icon.ico --name "1S-ERP"
"""
from __future__ import annotations
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

PORT = 5000


def _start_flask():
    """Запустить Flask в фоновом потоке."""
    from src.auth import _USERS_FILE, _bootstrap
    if not _USERS_FILE.exists():
        _bootstrap()

    from src.server import app
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=PORT, debug=False,
            threaded=True, use_reloader=False)


def main():
    # 1. Запустить Flask в фоне
    t = threading.Thread(target=_start_flask, daemon=True)
    t.start()

    # 2. Подождать пока Flask поднимется
    import urllib.request
    url = f"http://127.0.0.1:{PORT}/login"
    for _ in range(30):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.3)

    # 3. Открыть нативное окно
    try:
        import webview
        webview.create_window(
            title="1S: ERP Free Edition",
            url=f"http://127.0.0.1:{PORT}/",
            width=1280,
            height=800,
            min_size=(900, 600),
            text_select=True,
        )
        webview.start()

    except ImportError:
        # Нет pywebview — открыть в браузере
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
        print(f"\n  1S: ERP → http://127.0.0.1:{PORT}/")
        print("  (установите pywebview для нативного окна: pip install pywebview)")
        print("  Нажмите Ctrl+C для выхода.")
        t.join()


if __name__ == "__main__":
    main()
