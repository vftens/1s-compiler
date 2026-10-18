"""GridCraft bridge (Rust spreadsheet engine via gridcraft-cli) and trial balance reconciliation.

Most tests need no GridCraft: the comparison is plain Python and the CLI wrapper
is tested against a fake process. Tests marked `live` run only when
gridcraft-cli is found (GRIDCRAFT_CLI, PATH or bin/).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.migrate import gridcraft as gcmod
from src.migrate.gridcraft import GridCraft, GridCraftError, find_cli
from src.migrate.reconcile import (
    TBRow, build_steps, load_trial_balance, reconcile, rows_to_trial_balance, summary, write_reconciliation,
)

ROOT = Path(__file__).resolve().parent.parent
CLI = find_cli()
live = pytest.mark.skipif(CLI is None, reason="gridcraft-cli not installed")

TB_ROWS = [
    ["ОБОРОТНО-САЛЬДОВАЯ ВЕДОМОСТЬ · Январь 2025"],
    [],
    ["Сч.", "Наименование", "Нач.Дт", "Нач.Кт", "Об.Дт", "Об.Кт", "Кон.Дт", "Кон.Кт"],
    [10.0, "Осн.средства", 150000.0, 0.0, 0.0, 0.0, 150000.0, 0.0],
    ["41.010", "Товары", "1 000,50", None, "", 0, "1 000,50", 0],
    ["Итого", None, 151000.5, 0, 0, 0, 151000.5, 0],
    ["Подписи:", "", "", "", "", "", "", ""],
]


# ── reading ──────────────────────────────────────────────────────────────────

def test_rows_to_trial_balance_finds_header_and_skips_totals():
    rows = rows_to_trial_balance(TB_ROWS)
    assert [r.account for r in rows] == ["10", "41.010"]           # 10.0 -> "10", text kept
    assert rows[1].close_dt == 1000.5 and rows[1].open_ct == 0.0   # "1 000,50", None, ""


def test_rows_without_header_raise():
    with pytest.raises(ValueError):
        rows_to_trial_balance([["a", "b"], [1, 2]])


@pytest.mark.parametrize("head", ["Счёт", "Рахунок", "Account", "﻿Счёт"])
def test_header_words(head):
    assert rows_to_trial_balance([[head, "n", 1, 2, 3, 4, 5, 6], ["10", "x", 1, 2, 3, 4, 5, 6]])[0].account == "10"


def test_load_semicolon_csv_with_bom():
    rows = load_trial_balance(ROOT / "osv_yanvar_2025.csv")
    assert len(rows) == 9 and rows[0].account == "10" and rows[0].close_dt == 150000.0


# ── comparing ────────────────────────────────────────────────────────────────

def _tb(acc, close_dt=0.0, name="x"):
    return TBRow(acc, name, 0, 0, 0, 0, close_dt, 0)


def test_reconcile_statuses_and_order():
    left = [_tb("10", 5), _tb("2", 1), _tb("41.010", 3)]
    right = [_tb("10", 5.004), _tb("41.010", 4), _tb("70", 1)]
    diffs = reconcile(left, right)
    assert [d.account for d in diffs] == ["2", "10", "41.010", "70"]   # numeric account order
    assert [d.status for d in diffs] == ["only_left", "ok", "mismatch", "only_right"]
    assert diffs[2].delta("close_dt") == -1.0
    assert summary(diffs) == {"accounts": 4, "ok": 1, "mismatch": 1, "only_left": 1, "only_right": 1}


def test_build_steps_formulas_and_formatting():
    steps = build_steps(reconcile([_tb("31", 100)], [_tb("31", 90)]), "BAS", "Odoo", "uk")
    ids = [c for c, _ in steps]
    assert ids.index("home.numberFormat") < ids.index("range.setValues")   # accounts as text first
    values = dict(steps)["range.setValues"]["values"]
    header, row, total = values
    assert header[2].startswith("BAS ") and header[6].startswith("Odoo ") and header[-1] == "Статус"
    assert row[0] == "31" and row[10] == "=N(C2)-N(G2)" and "РОЗБІЖНІСТЬ" in row[14]
    assert total[0] == "Разом" and total[2] == "=SUM(C2:C2)"
    rules = [p["rule"] for c, p in steps if c == "home.conditionalFormat"]
    assert rules[0]["operator"] == "notBetween"


# ── the CLI wrapper, against a fake process ──────────────────────────────────

class _Proc:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout, self.returncode, self.stderr = stdout, returncode, stderr


def test_run_writes_jsonl_script_and_parses_results(monkeypatch, tmp_path):
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"] = argv
        script = Path(argv[argv.index("--script") + 1])
        seen["lines"] = [json.loads(line) for line in script.read_text(encoding="utf-8").splitlines()]
        return _Proc('wrote out.xlsx\n{"command":"sheet.read","result":{"values":[[1,"=x"]]}}\n')

    monkeypatch.setattr(gcmod.subprocess, "run", fake_run)
    exe = tmp_path / "gridcraft-cli"
    exe.write_text("")
    gc = GridCraft(exe)
    res = gc.run([("cell.set", {"cell": "A1", "input": "=1+1; rm -rf /"})], src="in.xlsx", out="out.xlsx")
    assert seen["argv"][1:3] == ["run", "--in"] and seen["argv"][-2:] == ["--out", "out.xlsx"]
    assert seen["lines"] == [{"command": "cell.set", "params": {"cell": "A1", "input": "=1+1; rm -rf /"}}]
    assert res == [{"command": "sheet.read", "result": {"values": [[1, "=x"]]}}]


def test_failure_raises_with_stderr(monkeypatch, tmp_path):
    monkeypatch.setattr(gcmod.subprocess, "run", lambda *a, **k: _Proc("", 1, "bad file"))
    exe = tmp_path / "g"
    exe.write_text("")
    with pytest.raises(GridCraftError, match="bad file"):
        GridCraft(exe).read("x.xlsx")


def test_missing_cli_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GRIDCRAFT_CLI", raising=False)
    monkeypatch.setattr(gcmod.shutil, "which", lambda _n: None)
    monkeypatch.setattr(gcmod, "ROOT", Path("/nonexistent"))
    assert find_cli() is None
    with pytest.raises(GridCraftError, match="cargo install"):
        GridCraft()


# ── live: the real gridcraft-cli ─────────────────────────────────────────────

@live
def test_live_read_xlsx_trial_balance():
    rows = load_trial_balance(ROOT / "otchet_yanvar_2025.xlsx", GridCraft())
    assert len(rows) == 9 and rows[2].account == "31" and rows[2].close_dt == 70000.0


@live
def test_live_reconciliation_workbook(tmp_path):
    gc = GridCraft()
    left = load_trial_balance(ROOT / "osv_yanvar_2025.csv")
    right = load_trial_balance(ROOT / "otchet_yanvar_2025.xlsx", gc)
    right[2].close_dt += 100          # account 31 off by 100
    right = right[:-1]                # account 92 missing
    out = write_reconciliation(reconcile(left, right), tmp_path / "r.xlsx", gc=gc)
    values = gc.read(out)
    by_acc = {r[0]: r for r in values[1:-1]}
    assert by_acc["31"][12] == -100.0 and by_acc["31"][14] == "РАСХОЖДЕНИЕ"
    assert by_acc["36"][14] == "OK" and by_acc["92"][14] == "РАСХОЖДЕНИЕ"
    check = subprocess.run([str(gc.cli), "check", str(out)], capture_output=True, text=True, timeout=60)
    assert check.returncode == 0, check.stdout[-500:]       # formulas recalc + Excel-valid package


@live
def test_live_cli_command(tmp_path):
    out = tmp_path / "r.xlsx"
    res = subprocess.run(
        [sys.executable, "-m", "src.cli", "migrate", "reconcile", str(ROOT / "osv_yanvar_2025.csv"),
         str(ROOT / "otchet_yanvar_2025.xlsx"), "-o", str(out), "--lang", "en"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert res.returncode == 0, res.stderr                 # identical trial balances
    assert "9 accounts: 9 ok" in res.stdout and out.exists()
