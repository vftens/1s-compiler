# -*- mode: python ; coding: utf-8 -*-
"""1S: ERP — command-line build for Linux servers (and any POSIX box).

Produces dist/1s/ with the `1s` executable: migrate audit, run, compile,
serve ... without installing Python. Folder mode (onedir), not one file: the
app keeps config/ and data/ next to its code, and a one-file build would
unpack into a temporary folder that is wiped on exit (users, secret key and
ERP database would be lost every run).

Build (from the repository root):
    python -m pip install pyinstaller flask pyyaml
    python -m PyInstaller packaging/linux.spec --clean --noconfirm
    dist/1s/1s about
    tar -C dist -czf 1s-linux-x86_64.tar.gz 1s
"""
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH is set by PyInstaller
SRC = ROOT / "src"

# Every module under src/: the CLI imports server, migrate, Cython helpers
# lazily, which PyInstaller's static analysis does not see.
hiddenimports = sorted(
    ".".join(p.relative_to(ROOT).with_suffix("").parts).removesuffix(".__init__")
    for p in SRC.rglob("*.py")
)

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "entry_cli.py")],
    pathex=[str(ROOT)],
    binaries=[],
    # Templates for `1s serve`. No config/: users and the secret key are
    # created per installation on first run (never ship a shared secret.key).
    datas=[(str(SRC / "templates"), "src/templates")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "webview", "pystray", "matplotlib", "numpy", "pandas", "gui"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="1s",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="1s",
)
