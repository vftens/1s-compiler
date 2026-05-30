"""
1S: ERP Free Edition — System Tray Desktop Launcher.

Starts the Flask web server on localhost and puts a tray icon
so the user can open the UI or stop the app without a terminal.

Usage:
    python gui/tray_app.py [--port 5000]

Build standalone .exe:
    pyinstaller gui/tray_app.py --onefile --noconsole \
        --add-data "src;src" --add-data "examples;examples" \
        --icon gui/assets/icon.ico --name "1S-ERP"
"""
from __future__ import annotations
import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

# ── Make sure project root is on sys.path ─────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Icon helpers ──────────────────────────────────────────────────────────────

def _make_icon():
    """
    Return a PIL Image for the tray icon.
    If gui/assets/icon.png exists, use it; otherwise generate a simple one.
    """
    from PIL import Image, ImageDraw
    icon_path = ROOT / "gui" / "assets" / "icon.png"
    if icon_path.exists():
        return Image.open(icon_path)
    # Fallback: draw a simple blue square with "1S" text
    img = Image.new("RGB", (64, 64), color=(25, 118, 210))
    draw = ImageDraw.Draw(img)
    draw.text((8, 18), "1S", fill=(255, 255, 255))
    return img


# ── Flask launcher (background thread) ───────────────────────────────────────

def _start_flask(host: str, port: int, debug: bool = False):
    """Bootstrap auth and start the Flask dev server in a daemon thread."""
    from src.auth import _USERS_FILE, _bootstrap
    if not _USERS_FILE.exists():
        _bootstrap()
    from src.server import app
    # Silence Flask's startup banner so it doesn't flood the tray log
    import logging
    log = logging.getLogger("werkzeug")
    log.setLevel(logging.ERROR)
    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


# ── Tray application ──────────────────────────────────────────────────────────

def run_tray(host: str = "127.0.0.1", port: int = 5000):
    try:
        import pystray
    except ImportError:
        # No pystray: just open browser and block until Ctrl-C
        print(f"  1S: ERP — starting at http://{host}:{port}/")
        print("  (install pystray for system-tray icon: pip install pystray)")
        _start_flask_blocking(host, port)
        return

    url = f"http://{host}:{port}/"

    # Start Flask in background
    t = threading.Thread(target=_start_flask, args=(host, port), daemon=True)
    t.start()

    # Give Flask a moment to start, then open browser
    import time; time.sleep(1.2)
    webbrowser.open(url)

    # Build tray menu
    def open_browser(icon, item):
        webbrowser.open(url)

    def quit_app(icon, item):
        icon.stop()
        os._exit(0)

    icon_image = _make_icon()
    menu = pystray.Menu(
        pystray.MenuItem("📂 Открыть / Відкрити", open_browser, default=True),
        pystray.MenuItem(f"🌐 {url}", open_browser),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("✖ Закрыть / Закрити", quit_app),
    )
    icon = pystray.Icon(
        name="1S-ERP",
        icon=icon_image,
        title="1S: ERP Free Edition",
        menu=menu,
    )
    print(f"  1S: ERP запущен → {url}")
    icon.run()


def _start_flask_blocking(host: str, port: int):
    """Fallback: run Flask in the main thread (no tray icon)."""
    from src.auth import _USERS_FILE, _bootstrap
    if not _USERS_FILE.exists():
        _bootstrap()
    from src.server import app
    print(f"\n  1S: ERP Free Edition — Web UI")
    print(f"  Открыть: http://{host}:{port}/\n")
    app.run(host=host, port=port, debug=False, threaded=True)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="1S: ERP — Desktop launcher")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--no-tray", action="store_true",
                    help="Run without system-tray icon (terminal mode)")
    args = ap.parse_args()

    if args.no_tray:
        _start_flask_blocking(args.host, args.port)
    else:
        run_tray(args.host, args.port)
