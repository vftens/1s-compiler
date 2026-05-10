"""
Auto-generated Cython build script for 1S: ERP Free Edition.
Usage:
    python setup_1s.py build_ext --inplace

Requirements:
    pip install cython setuptools

The compiled extension will appear as:
    hello.cpython-<ver>-<platform>.pyd  (Windows)
    hello.cpython-<ver>-<platform>.so   (Linux/macOS)
"""
import sys
from pathlib import Path
from setuptools import setup, Extension

try:
    from Cython.Build import cythonize
    from Cython.Compiler import Options
except ImportError:
    print("ERROR: Cython is not installed.  Run:  pip install cython", file=sys.stderr)
    sys.exit(1)

Options.docstrings = False

PYX_FILE = "C:/Users/DrVITAL/1s-compiler/examples/hello.pyx"
REPO_ROOT = str(Path(__file__).parent.parent)  # so 'src.runtime' is importable

ext = Extension(
    name="hello",
    sources=[PYX_FILE],
    extra_compile_args=["/O2"] if sys.platform == "win32" else ["-O3", "-march=native"],
)

setup(
    name="1s_compiled",
    ext_modules=cythonize(
        [ext],
        compiler_directives={
            "language_level": "3",
            "boundscheck":    False,
            "wraparound":     False,
            "cdivision":      True,
            "nonecheck":      False,
        },
        quiet=False,
    ),
    script_args=["build_ext", "--inplace", "--build-lib", REPO_ROOT],
)
