"""
1S: ERP Free Edition — Build script.
Runs PyInstaller and creates a distributable zip package.

Usage:
    python installer/build.py          # build .exe only
    python installer/build.py --zip    # build .exe + installer zip
"""
import sys
import subprocess
import zipfile
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST = ROOT / "dist"
SPEC = ROOT / "1S-ERP.spec"


def build_exe():
    print("\n=== Building 1S-ERP.exe with PyInstaller ===\n")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--clean", "--noconfirm"],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("\n[ERROR] PyInstaller failed.")
        sys.exit(1)
    exe = DIST / "1S-ERP.exe"
    size_mb = exe.stat().st_size / 1_048_576
    print(f"\nOK Built: {exe}  ({size_mb:.1f} MB)")
    return exe


def build_zip(exe: Path):
    """Create a distributable zip: exe + install.bat + uninstall.bat + README."""
    zip_path = DIST / "1S-ERP-v0.3-windows.zip"
    print(f"\n=== Creating installer zip: {zip_path.name} ===\n")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Main executable
        zf.write(exe, "1S-ERP.exe")

        # Installer scripts
        zf.write(ROOT / "installer" / "install.bat",   "install.bat")
        zf.write(ROOT / "installer" / "uninstall.bat", "uninstall.bat")

        # Readme
        readme = (
            "1S: ERP Free Edition v0.3\n"
            "==========================\n\n"
            "УСТАНОВКА / INSTALL:\n"
            "  1. Запустите install.bat   (Windows)\n"
            "  2. Или просто запустите 1S-ERP.exe напрямую\n\n"
            "УДАЛЕНИЕ / UNINSTALL:\n"
            "  Запустите uninstall.bat\n\n"
            "GitHub: https://github.com/vftens/1s-compiler\n"
            "License: GNU GPL v3\n"
        )
        zf.writestr("README.txt", readme)

    size_mb = zip_path.stat().st_size / 1_048_576
    print(f"OK Package: {zip_path}  ({size_mb:.1f} MB)")
    return zip_path


if __name__ == "__main__":
    exe = build_exe()
    if "--zip" in sys.argv:
        pkg = build_zip(exe)
        print(f"\n  Ready to distribute: {pkg.name}")
    else:
        print("\n  Tip: run with --zip to also create installer package")

    print("\n=== Done ===\n")
