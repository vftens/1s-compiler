# -*- mode: python ; coding: utf-8 -*-
"""1S: ERP — one PyInstaller spec for every Windows edition.

Replaces 1S-ERP.spec, 1S-ERP-RU.spec, 1S-ERP-UK.spec and 1S-ERP-EN.spec,
which differed only in entry script, exe name and icon.

Build one edition (from the repository root):
    PowerShell:  $env:ONES_EDITION = "uk"; python -m PyInstaller packaging/windows.spec --clean --noconfirm
    cmd:         set ONES_EDITION=uk && python -m PyInstaller packaging/windows.spec --clean --noconfirm
or all of them with zips:
    python installer/build.py --zip

Editions: base (multilingual desktop app, default), ru, uk, en.
"""
import os
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH is set by PyInstaller
GUI = ROOT / "gui"
ASSETS = GUI / "assets"

EDITIONS = {
    "base": {"entry": "desktop_app.py", "name": "1S-ERP",    "icon": "icon.ico",    "version": True},
    "ru":   {"entry": "app_ru.py",      "name": "1S-ERP-RU", "icon": "icon_ru.ico", "version": False},
    "uk":   {"entry": "app_uk.py",      "name": "1S-ERP-UK", "icon": "icon_uk.ico", "version": False},
    "en":   {"entry": "app_en.py",      "name": "1S-ERP-EN", "icon": "icon_en.ico", "version": False},
}

edition = os.environ.get("ONES_EDITION", "base").strip().lower()
if edition not in EDITIONS:
    raise SystemExit(f"ONES_EDITION={edition!r}: expected one of {', '.join(EDITIONS)}")
ed = EDITIONS[edition]

hiddenimports = [
    "webview", "webview.platforms.winforms",
    "flask", "jinja2", "werkzeug",
    "src.server", "src.auth", "src.cli",
    "src.lexer", "src.parser", "src.runtime", "src.transpiler",
    "src.i18n", "src.migrate", "src.product", "clr",
]
if edition != "base":
    hiddenimports.insert(0, "gui.desktop_app")  # language launchers import the shared app

a = Analysis(  # noqa: F821 - PyInstaller spec globals
    [str(GUI / ed["entry"])],
    pathex=[str(ROOT)],
    binaries=[],
    # No config/: users and the secret key are created per installation on
    # first run. Shipping config/secret.key would give every install the same
    # (public) Flask session key, so anyone could forge an admin session.
    datas=[
        (str(ROOT / "src"), "src"),
        (str(ROOT / "examples"), "examples"),
        (str(ASSETS), os.path.join("gui", "assets")),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=ed["name"],
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ASSETS / ed["icon"])],
    version=str(GUI / "version_info.txt") if ed["version"] else None,
)
