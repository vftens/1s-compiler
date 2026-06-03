"""
1S: ERP Free Edition — Build script.
Runs PyInstaller for all 3 language editions and creates distributable zips.

Usage:
    python installer/build.py              # build all 3 .exe
    python installer/build.py --zip        # build all 3 + zip each
    python installer/build.py --lang ru    # build only Russian edition
    python installer/build.py --lang uk    # build only Ukrainian edition
    python installer/build.py --lang en    # build only English edition
"""
import sys
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / "dist"

# Language edition definitions
EDITIONS = {
    "ru": {
        "spec":    "1S-ERP-RU.spec",
        "exe":     "1S-ERP-RU.exe",
        "readme":  (
            "1S: ERP Free Edition v0.3 — Russian Edition\n"
            "=============================================\n\n"
            "УСТАНОВКА:\n"
            "  Запустите install.bat или просто 1S-ERP-RU.exe\n\n"
            "GitHub: https://github.com/vftens/1s-compiler\n"
            "License: GNU GPL v3\n"
        ),
    },
    "uk": {
        "spec":    "1S-ERP-UK.spec",
        "exe":     "1S-ERP-UK.exe",
        "readme":  (
            "1S: ERP Free Edition v0.3 — Ukrainian Edition\n"
            "==============================================\n\n"
            "ВСТАНОВЛЕННЯ:\n"
            "  Запустіть install.bat або просто 1S-ERP-UK.exe\n\n"
            "GitHub: https://github.com/vftens/1s-compiler\n"
            "License: GNU GPL v3\n"
        ),
    },
    "en": {
        "spec":    "1S-ERP-EN.spec",
        "exe":     "1S-ERP-EN.exe",
        "readme":  (
            "1S: ERP Free Edition v0.3 — English Edition\n"
            "============================================\n\n"
            "INSTALL:\n"
            "  Run install.bat or simply launch 1S-ERP-EN.exe\n\n"
            "GitHub: https://github.com/vftens/1s-compiler\n"
            "License: GNU GPL v3\n"
        ),
    },
}


def build_edition(lang: str) -> Path:
    ed = EDITIONS[lang]
    spec = ROOT / ed["spec"]
    print(f"\n=== Building {ed['exe']} [{lang.upper()}] ===\n")

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--clean", "--noconfirm"],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"[ERROR] Build failed for {lang.upper()}")
        sys.exit(1)

    exe = DIST / ed["exe"]
    size_mb = exe.stat().st_size / 1_048_576
    print(f"OK  {exe.name}  ({size_mb:.1f} MB)")
    return exe


def build_zip(lang: str, exe: Path) -> Path:
    ed = EDITIONS[lang]
    zip_name = f"1S-ERP-{lang.upper()}-v0.3-windows.zip"
    zip_path = DIST / zip_name
    print(f"    Packaging → {zip_name}")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe, exe.name)
        zf.write(ROOT / "installer" / "install.bat",   "install.bat")
        zf.write(ROOT / "installer" / "uninstall.bat", "uninstall.bat")
        zf.writestr("README.txt", ed["readme"])

    size_mb = zip_path.stat().st_size / 1_048_576
    print(f"OK  {zip_name}  ({size_mb:.1f} MB)")
    return zip_path


if __name__ == "__main__":
    want_zip  = "--zip"  in sys.argv
    lang_flag = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        if idx + 1 < len(sys.argv):
            lang_flag = sys.argv[idx + 1].lower()

    langs = [lang_flag] if lang_flag in EDITIONS else list(EDITIONS)

    print(f"\n1S: ERP Free Edition — Building {', '.join(l.upper() for l in langs)} edition(s)\n")

    results = {}
    for lang in langs:
        exe = build_edition(lang)
        if want_zip:
            build_zip(lang, exe)
        results[lang] = exe

    print("\n=== Summary ===")
    for lang, exe in results.items():
        size_mb = exe.stat().st_size / 1_048_576
        print(f"  {exe.name:<20} {size_mb:.1f} MB  [{lang.upper()}]")

    print("\n=== Done ===\n")
