# -*- mode: python ; coding: utf-8 -*-
"""1S: ERP — macOS desktop app (1S-ERP.app).

The same desktop launcher as on Windows (gui/desktop_app.py): Flask on
localhost in a native WebKit window via pywebview (falls back to the default
browser if pywebview is missing).

Build on a Mac (or the macos job in .github/workflows/build.yml):
    python -m pip install pyinstaller flask pyyaml pywebview pillow
    python -m PyInstaller packaging/macos.spec --clean --noconfirm
    open dist/1S-ERP.app

Pillow converts gui/assets/icon.png to .icns. The app is not signed or
notarised: on first launch use right click -> Open.
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH is set by PyInstaller
GUI = ROOT / "gui"
SRC = ROOT / "src"

hiddenimports = sorted(
    ".".join(p.relative_to(ROOT).with_suffix("").parts).removesuffix(".__init__")
    for p in SRC.rglob("*.py")
) + ["webview", "webview.platforms.cocoa", "flask", "jinja2", "werkzeug"]

a = Analysis(  # noqa: F821
    [str(GUI / "desktop_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    # No config/: users and the secret key are created per installation.
    datas=[
        (str(SRC / "templates"), "src/templates"),
        (str(ROOT / "examples"), "examples"),
        (str(GUI / "assets"), "gui/assets"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "clr", "webview.platforms.winforms"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="1S-ERP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="1S-ERP",
)

app = BUNDLE(  # noqa: F821
    coll,
    name="1S-ERP.app",
    icon=str(GUI / "assets" / "icon.png"),
    bundle_identifier="io.github.vftens.1s-erp",
    info_plist={
        "CFBundleDisplayName": "1S: ERP",
        "CFBundleShortVersionString": "1.3.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
