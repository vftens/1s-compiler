"""Bridge to GridCraft (Rust spreadsheet engine) through its command line.

GridCraft (https://github.com/storytold/gridcraft, MIT OR Apache-2.0) is a
clean-room Excel reimplementation in Rust. 1S talks to it as a separate
process, `gridcraft-cli`, with JSON in and out:

    1S (Python) --script.jsonl / argv--> gridcraft-cli --JSON lines--> 1S

Why a process and not a Python extension (PyO3): no Rust toolchain, wheels or
ABI for 1S users and CI; GridCraft upgrades are a binary swap; a crash in the
engine cannot take the 1S process down. The cost is ~10-50 ms per call, which
is nothing for reports and reconciliations. See docs/gridcraft-integration.md.

What it gives 1S: reading .xls/.xlsb/.ods/.xlsx (1C/BAS export reports as .xls),
500+ Excel functions, and writing real .xlsx with live formulas, tables,
number formats and conditional formatting.

Locating the binary: $GRIDCRAFT_CLI, then `gridcraft-cli` on PATH, then
bin/gridcraft-cli[.exe] in the repository (where packaged builds put it).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
EXE_NAME = "gridcraft-cli.exe" if os.name == "nt" else "gridcraft-cli"

Step = tuple[str, dict[str, Any]]


class GridCraftError(RuntimeError):
    """gridcraft-cli is missing, failed, or returned something unreadable."""


def find_cli() -> Path | None:
    env = os.environ.get("GRIDCRAFT_CLI")
    if env and Path(env).is_file():
        return Path(env)
    found = shutil.which("gridcraft-cli")
    if found:
        return Path(found)
    bundled = ROOT / "bin" / EXE_NAME
    return bundled if bundled.is_file() else None


class GridCraft:
    """One gridcraft-cli executable. Every call is a separate, stateless process."""

    def __init__(self, cli: Path | str | None = None, timeout: float = 120.0):
        path = Path(cli) if cli else find_cli()
        if path is None:
            raise GridCraftError(
                "gridcraft-cli not found: set GRIDCRAFT_CLI, put it on PATH, or place it in bin/. "
                "Build: cargo install --git https://github.com/storytold/gridcraft --tag v0.8.0 gridcraft-cli"
            )
        self.cli = path
        self.timeout = timeout

    # ── low level ────────────────────────────────────────────────────────────

    def _call(self, *args: str) -> str:
        try:
            proc = subprocess.run(
                [str(self.cli), *args], capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=self.timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise GridCraftError(f"gridcraft-cli {args[0] if args else ''}: {exc}") from exc
        if proc.returncode != 0:
            raise GridCraftError(f"gridcraft-cli {' '.join(args[:1])} failed: {proc.stderr.strip()[:500]}")
        return proc.stdout

    def version(self) -> str:
        return self._call("version").strip()

    def run(self, steps: list[Step], src: Path | str | None = None,
            out: Path | str | None = None) -> list[dict[str, Any]]:
        """Run commands on a workbook (blank if no src), optionally save; return the results.

        Steps go through a JSONL script file, so values never pass through a
        shell and there is no argv length limit.
        """
        with tempfile.TemporaryDirectory(prefix="1s-gridcraft-") as tmp:
            script = Path(tmp) / "steps.jsonl"
            script.write_text(
                "\n".join(json.dumps({"command": c, "params": p}, ensure_ascii=False) for c, p in steps),
                encoding="utf-8",
            )
            args = ["run"]
            if src is not None:
                args += ["--in", str(src)]
            args += ["--script", str(script)]
            if out is not None:
                args += ["--out", str(out)]
            stdout = self._call(*args)
        results = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # GridCraft also prints "wrote …" style lines
        return results

    # ── high level ───────────────────────────────────────────────────────────

    def read(self, path: Path | str, range_: str | None = None, sheet: str | None = None) -> list[list[Any]]:
        """Computed values of a range (default: the used range) as rows."""
        params: dict[str, Any] = {}
        if range_:
            params["range"] = range_
        if sheet:
            params["sheet"] = sheet
        for res in self.run([("sheet.read", params)], src=path):
            if res.get("command") == "sheet.read":
                return res.get("result", {}).get("values", [])
        raise GridCraftError(f"sheet.read returned nothing for {path}")

    def info(self, path: Path | str) -> dict[str, Any]:
        out = self._call("info", str(path), "--json")
        try:
            return json.loads(out)
        except json.JSONDecodeError as exc:
            raise GridCraftError(f"info --json: unreadable output: {out[:200]}") from exc

    def evaluate(self, formula: str, path: Path | str | None = None, sheet: str | None = None) -> Any:
        args = ["eval", formula, "--json"]
        if path is not None:
            args += ["--in", str(path)]
        if sheet:
            args += ["--sheet", sheet]
        out = self._call(*args).strip()
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return out
        return data.get("value", data) if isinstance(data, dict) else data

    def convert(self, src: Path | str, out: Path | str, sheet: str | None = None) -> Path:
        """.xls/.xlsb/.ods/.xlsx -> .xlsx/.csv/.tsv/.json/.html, by extension."""
        args = ["convert", str(src), str(out)]
        if sheet:
            args += ["--sheet", sheet]
        self._call(*args)
        return Path(out)
