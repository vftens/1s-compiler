#!/usr/bin/env python3
"""
1S: ERP Free Edition — Command-line interface
Usage:
    python -m src.cli compile hello.1s           # → hello.py
    python -m src.cli run     hello.1s
    python -m src.cli tokens  hello.1s           # dump token stream
    python -m src.cli ast     hello.1s           # dump AST
"""
import sys
import os
import argparse
from pathlib import Path

# Force UTF-8 output on Windows
import io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)

def _make_compiler():
    from .lexer import Lexer
    from .parser import Parser
    from .transpiler import PythonTranspiler
    return Lexer, Parser, PythonTranspiler

def cmd_tokens(path: Path):
    from .lexer import Lexer
    source = path.read_text(encoding="utf-8")
    lexer = Lexer(source, path.name)
    for tok in lexer.tokenize():
        print(tok)

def cmd_ast(path: Path):
    import pprint
    from .lexer import Lexer
    from .parser import Parser
    source = path.read_text(encoding="utf-8")
    tokens = Lexer(source, path.name).tokenize()
    ast = Parser(tokens).parse()
    pprint.pprint(ast)

def cmd_compile(path: Path, cython: bool = False, out: Path | None = None):
    Lexer, Parser, PythonTranspiler = _make_compiler()
    source = path.read_text(encoding="utf-8")
    tokens = Lexer(source, path.name).tokenize()
    ast    = Parser(tokens).parse()
    py_src = PythonTranspiler(cython_mode=cython).transpile(ast)
    out_path = out or path.with_suffix(".pyx" if cython else ".py")
    out_path.write_text(py_src, encoding="utf-8")
    print(f"Compiled → {out_path}")


def cmd_cython_gen(path: Path, out: Path | None = None) -> Path:
    """Generate .pyx (Cython-annotated) source from a .1s file."""
    from .lexer import Lexer
    from .parser import Parser
    from .transpiler import CythonTranspiler, generate_setup

    source = path.read_text(encoding="utf-8")
    tokens = Lexer(source, path.name).tokenize()
    ast    = Parser(tokens).parse()
    pyx_src = CythonTranspiler().transpile(ast)

    pyx_path = out or path.with_suffix(".pyx")
    pyx_path.write_text(pyx_src, encoding="utf-8")
    print(f"Generated  → {pyx_path}")

    setup_src, runner_src = generate_setup(pyx_path)
    setup_path  = path.parent / "setup_1s.py"
    runner_path = path.with_stem(path.stem + "_run").with_suffix(".py")
    setup_path.write_text(setup_src,  encoding="utf-8")
    runner_path.write_text(runner_src, encoding="utf-8")
    print(f"Build file → {setup_path}")
    print(f"Runner     → {runner_path}")
    return pyx_path


def cmd_cython_build(path: Path, run_after: bool = False):
    """Generate .pyx and compile it with Cython + C compiler."""
    import subprocess, shutil

    # Check Cython is available before doing any work
    if not shutil.which("cython") and not _cython_importable():
        print("ERROR: Cython not found.  Install it with:\n"
              "    pip install cython\n"
              "Then re-run:  python -m src.cli cython-build <file.1s>",
              file=sys.stderr)
        sys.exit(1)

    pyx_path = cmd_cython_gen(path)
    setup_path = path.parent / "setup_1s.py"

    print("\nBuilding Cython extension…")
    result = subprocess.run(
        [sys.executable, str(setup_path), "build_ext", "--inplace"],
        capture_output=False,
    )
    if result.returncode != 0:
        print("\nBuild FAILED.  Check compiler output above.", file=sys.stderr)
        sys.exit(result.returncode)

    print("\nBuild OK.")

    if run_after:
        runner = path.with_stem(path.stem + "_run").with_suffix(".py")
        print(f"Running {runner} …\n")
        subprocess.run([sys.executable, str(runner)])


def _cython_importable() -> bool:
    try:
        import Cython  # noqa: F401
        return True
    except ImportError:
        return False

def cmd_run(path: Path):
    Lexer, Parser, PythonTranspiler = _make_compiler()
    source = path.read_text(encoding="utf-8")
    tokens = Lexer(source, path.name).tokenize()
    ast    = Parser(tokens).parse()
    py_src = PythonTranspiler().transpile(ast)
    # Inject runtime into exec namespace
    import importlib, sys
    # Ensure the repo root is on sys.path so 'src.runtime' resolves
    repo_root = str(Path(__file__).parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    runtime_mod = importlib.import_module("src.runtime")
    ns = {k: getattr(runtime_mod, k) for k in dir(runtime_mod) if not k.startswith("__")}
    exec(compile(py_src, str(path), "exec"), ns)

def main():
    parser = argparse.ArgumentParser(prog="1s", description="1S: ERP Free Edition compiler")
    sub = parser.add_subparsers(dest="command")

    p_compile = sub.add_parser("compile", help="Transpile .1s → .py / .pyx")
    p_compile.add_argument("file")
    p_compile.add_argument("--cython", action="store_true")
    p_compile.add_argument("-o", "--output")

    p_run = sub.add_parser("run", help="Compile and run a .1s file")
    p_run.add_argument("file")

    p_tok = sub.add_parser("tokens", help="Dump token stream")
    p_tok.add_argument("file")

    p_ast = sub.add_parser("ast", help="Dump AST")
    p_ast.add_argument("file")

    p_cygen = sub.add_parser("cython-gen",
                              help="Transpile .1s → typed Cython .pyx (no compilation)")
    p_cygen.add_argument("file")
    p_cygen.add_argument("-o", "--output", help="Output .pyx path")

    p_cybld = sub.add_parser("cython-build",
                              help="Transpile .1s → .pyx and compile with Cython+C")
    p_cybld.add_argument("file")
    p_cybld.add_argument("--run", action="store_true",
                          help="Execute the compiled module after building")

    p_serve = sub.add_parser("serve", help="Запустить веб-интерфейс")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=5000)
    p_serve.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    if args.command == "compile":
        cmd_compile(Path(args.file), args.cython,
                    Path(args.output) if args.output else None)
    elif args.command == "run":
        cmd_run(Path(args.file))
    elif args.command == "tokens":
        cmd_tokens(Path(args.file))
    elif args.command == "ast":
        cmd_ast(Path(args.file))
    elif args.command == "cython-gen":
        cmd_cython_gen(Path(args.file),
                       Path(args.output) if args.output else None)
    elif args.command == "cython-build":
        cmd_cython_build(Path(args.file), run_after=args.run)
    elif args.command == "serve":
        from .server import run_server
        run_server(host=args.host, port=args.port, debug=args.debug)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
