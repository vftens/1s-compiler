"""
Sprint 15 — Financial Reporting Module tests.
Target: 39 tests covering report engine, REST endpoints, dashboard, 1S bindings, edge cases.
"""
from __future__ import annotations

import io
import sqlite3
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path):
    """Fresh in-memory-style SQLite DB with budget_entries and payroll_results tables."""
    path = tmp_path / "erp.db"
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE budget_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_type TEXT NOT NULL,
            org_id TEXT NOT NULL DEFAULT 'test',
            period TEXT NOT NULL,
            amount TEXT NOT NULL,
            doc_ref TEXT,
            account TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE payroll_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,
            emp_id TEXT NOT NULL,
            emp_name TEXT NOT NULL,
            gross TEXT NOT NULL,
            net TEXT NOT NULL,
            tax_profile TEXT NOT NULL DEFAULT 'default',
            deductions TEXT NOT NULL DEFAULT '0'
        )
    """)
    conn.commit()
    conn.close()
    return path


def _insert(db: Path, entries: list[tuple]) -> None:
    """Insert (entry_type, period, account, amount) tuples into budget_entries."""
    conn = sqlite3.connect(str(db))
    conn.executemany(
        "INSERT INTO budget_entries (entry_type, period, account, amount) VALUES (?,?,?,?)",
        entries,
    )
    conn.commit()
    conn.close()


def _insert_payroll(db: Path, period: str, gross: float) -> None:
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO payroll_results (period, emp_id, emp_name, gross, net, tax_profile, deductions)"
        " VALUES (?,?,?,?,?,?,?)",
        (period, "E01", "Test Employee", str(gross), str(gross * 0.8), "default", str(gross * 0.2)),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# TestTrialBalance
# ---------------------------------------------------------------------------

class TestTrialBalance:
    def test_trial_balance_returns_rows(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "10000"),
            ("credit", "2026-07", "66", "10000"),
        ])
        from src.runtime.reports import TrialBalanceReport
        data = TrialBalanceReport.compute("2026-07", db)
        assert data["report"] == "trial-balance"
        assert len(data["rows"]) == 2
        assert all("account_code" in r for r in data["rows"])

    def test_trial_balance_debit_credit_balanced(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "5000"),
            ("credit", "2026-07", "60", "5000"),
        ])
        from src.runtime.reports import TrialBalanceReport
        data = TrialBalanceReport.compute("2026-07", db)
        assert data["totals"]["total_debit"] == data["totals"]["total_credit"]
        assert data["integrity"]["balanced"] is True
        assert data["integrity"]["difference"] == 0.0

    def test_trial_balance_empty_period_returns_empty(self, db):
        _insert(db, [("debit", "2026-06", "31", "1000")])
        from src.runtime.reports import TrialBalanceReport
        data = TrialBalanceReport.compute("2026-07", db)
        assert data["rows"] == []
        assert data["integrity"]["balanced"] is True

    def test_trial_balance_xlsx_export(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "1000"),
            ("credit", "2026-07", "60", "1000"),
        ])
        from src.runtime.reports import TrialBalanceReport
        data = TrialBalanceReport.compute("2026-07", db)
        buf = TrialBalanceReport.to_excel(data)
        content = buf.read()
        assert content[:4] == b"PK\x03\x04"  # xlsx magic

    def test_trial_balance_pdf_export(self, db):
        pytest.importorskip("reportlab")
        _insert(db, [("debit", "2026-07", "31", "500")])
        from src.runtime.reports import TrialBalanceReport
        data = TrialBalanceReport.compute("2026-07", db)
        buf = TrialBalanceReport.to_pdf(data)
        content = buf.read()
        assert content[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# TestBalanceSheet
# ---------------------------------------------------------------------------

class TestBalanceSheet:
    def test_balance_sheet_assets_equals_liabilities_plus_equity(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "20000"),   # cash → current_assets
            ("credit", "2026-07", "40", "20000"),   # share capital → equity
        ])
        from src.runtime.reports import BalanceSheetReport
        data = BalanceSheetReport.compute("2026-07", db)
        t = data["totals"]
        assert abs(t["total_assets"] - t["total_liabilities_equity"]) < 0.01

    def test_balance_sheet_period_filter(self, db):
        _insert(db, [
            ("debit",  "2026-06", "31", "9999"),   # June — must be excluded
            ("debit",  "2026-07", "31", "5000"),   # July
            ("credit", "2026-07", "40", "5000"),
        ])
        from src.runtime.reports import BalanceSheetReport
        data = BalanceSheetReport.compute("2026-07", db)
        # Only July entries: asset should be 5000 not 14999
        assert data["sections"]["current_assets"] == pytest.approx(5000.0)

    def test_balance_sheet_difference_line_on_imbalance(self, db):
        # Asset-only entries — will not balance
        _insert(db, [("debit", "2026-07", "31", "7500")])
        from src.runtime.reports import BalanceSheetReport
        data = BalanceSheetReport.compute("2026-07", db)
        # No exception raised; difference captured
        assert data["balance_check"]["difference"] != 0

    def test_balance_sheet_xlsx_export(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "1000"),
            ("credit", "2026-07", "40", "1000"),
        ])
        from src.runtime.reports import BalanceSheetReport
        data = BalanceSheetReport.compute("2026-07", db)
        buf = BalanceSheetReport.to_excel(data)
        assert buf.read()[:4] == b"PK\x03\x04"


# ---------------------------------------------------------------------------
# TestIncomeStatement
# ---------------------------------------------------------------------------

class TestIncomeStatement:
    def test_income_statement_net_profit_computed(self, db):
        _insert(db, [
            ("credit", "2026-07", "70", "100000"),  # revenue
            ("debit",  "2026-07", "90", "40000"),   # COGS
            ("debit",  "2026-07", "92", "20000"),   # admin expenses
        ])
        _insert_payroll(db, "2026-07", 15000)
        from src.runtime.reports import IncomeStatement
        data = IncomeStatement.compute("2026-07", db)
        assert data["revenue"]    == pytest.approx(100000.0)
        assert data["cogs"]       == pytest.approx(40000.0)
        assert data["payroll"]    == pytest.approx(15000.0)
        assert data["net_profit"] == pytest.approx(100000.0 - 40000.0 - 20000.0 - 15000.0)

    def test_income_statement_ytd_mode(self, db):
        # Insert revenue for Jan, Apr, Jul 2026
        _insert(db, [
            ("credit", "2026-01", "70", "30000"),
            ("credit", "2026-04", "70", "30000"),
            ("credit", "2026-07", "70", "30000"),
        ])
        from src.runtime.reports import IncomeStatement
        monthly = IncomeStatement.compute("2026-07", db, "monthly")
        ytd     = IncomeStatement.compute("2026-07", db, "ytd")
        assert monthly["revenue"] == pytest.approx(30000.0)
        assert ytd["revenue"]     == pytest.approx(90000.0)

    def test_income_statement_empty_period(self, db):
        from src.runtime.reports import IncomeStatement
        data = IncomeStatement.compute("2026-07", db)
        assert data["revenue"]    == 0.0
        assert data["net_profit"] == 0.0


# ---------------------------------------------------------------------------
# TestReportEndpoints
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db, monkeypatch):
    """Flask test client authenticated via session."""
    from src.server import app, _ERP_DB_S13
    monkeypatch.setattr("src.server._ERP_DB_S13", db)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = b"test"
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user"] = {"username": "admin", "role": "admin"}
        yield c


class TestReportEndpoints:
    def test_trial_balance_json_endpoint(self, client, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "1000"),
            ("credit", "2026-07", "60", "1000"),
        ])
        r = client.get("/api/v1/reports/trial-balance?period=2026-07")
        assert r.status_code == 200
        body = r.get_json()
        assert body["report"] == "trial-balance"
        assert "rows" in body
        assert "totals" in body
        assert "integrity" in body

    def test_trial_balance_xlsx_endpoint(self, client, db):
        _insert(db, [("debit", "2026-07", "31", "500")])
        r = client.get("/api/v1/reports/trial-balance?period=2026-07&format=xlsx")
        assert r.status_code == 200
        assert b"PK\x03\x04" in r.data  # xlsx magic

    def test_trial_balance_pdf_endpoint(self, client, db):
        pytest.importorskip("reportlab")
        _insert(db, [("debit", "2026-07", "31", "500")])
        r = client.get("/api/v1/reports/trial-balance?period=2026-07&format=pdf")
        assert r.status_code == 200
        assert r.data[:4] == b"%PDF"

    def test_balance_sheet_json_endpoint(self, client, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "5000"),
            ("credit", "2026-07", "40", "5000"),
        ])
        r = client.get("/api/v1/reports/balance-sheet?period=2026-07")
        assert r.status_code == 200
        body = r.get_json()
        assert body["report"] == "balance-sheet"
        assert "balance_check" in body
        assert "integrity" not in body  # DX X3: integrity only on trial balance

    def test_income_statement_json_endpoint(self, client, db):
        r = client.get("/api/v1/reports/income-statement?period=2026-07")
        assert r.status_code == 200
        body = r.get_json()
        assert body["report"] == "income-statement"
        assert "net_profit" in body
        assert "revenue" in body

    def test_reports_index_endpoint(self, client):
        r = client.get("/api/v1/reports")
        assert r.status_code == 200
        body = r.get_json()
        names = [e["name"] for e in body["reports"]]
        assert "trial-balance"    in names
        assert "balance-sheet"    in names
        assert "income-statement" in names

    def test_reports_unauthenticated_redirects(self):
        from src.server import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            r = c.get("/api/v1/reports/trial-balance?period=2026-07",
                      headers={"Accept": "application/json"})
        assert r.status_code in (401, 302)

    def test_period_injection_blocked(self, client):
        r = client.get("/api/v1/reports/trial-balance?period=2026-13")
        assert r.status_code == 400
        body = r.get_json()
        assert "error" in body
        assert "hint"  in body

    def test_format_param_invalid_returns_400(self, client):
        r = client.get("/api/v1/reports/trial-balance?period=2026-07&format=csv")
        assert r.status_code == 400
        body = r.get_json()
        assert "error" in body
        assert "hint"  in body

    def test_new_endpoints_in_discovery(self, client):
        r = client.get("/api/v1")
        assert r.status_code == 200
        body = r.get_json()
        paths = [e["path"] for e in body["endpoints"]]
        assert "/api/v1/reports/trial-balance"    in paths
        assert "/api/v1/reports/balance-sheet"    in paths
        assert "/api/v1/reports/income-statement" in paths
        assert "/api/v1/reports"                  in paths

    def test_truncation_header(self, client, db):
        # Insert 10001 rows
        rows = [("debit", "2026-07", f"{i:05d}", "1") for i in range(10001)]
        conn = sqlite3.connect(str(db))
        conn.executemany(
            "INSERT INTO budget_entries (entry_type, period, account, amount) VALUES (?,?,?,?)",
            rows,
        )
        conn.commit()
        conn.close()
        r = client.get("/api/v1/reports/trial-balance?period=2026-07")
        assert r.status_code == 200
        assert r.headers.get("X-Truncated") == "true"


# ---------------------------------------------------------------------------
# TestReportsDashboard
# ---------------------------------------------------------------------------

class TestReportsDashboard:
    def test_reports_page_returns_200(self, client):
        r = client.get("/reports")
        assert r.status_code == 200
        text = r.data.decode("utf-8", errors="replace")
        assert "Trial Balance" in text
        assert "Balance Sheet" in text
        assert "Income Statement" in text

    def test_reports_page_unauthenticated(self):
        from src.server import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            r = c.get("/reports")
        assert r.status_code in (302, 401)


# ---------------------------------------------------------------------------
# TestNewReporterBinding
# ---------------------------------------------------------------------------

class TestNewReporterBinding:
    def test_trial_balance_binding_is_balanced(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "2000"),
            ("credit", "2026-07", "40", "2000"),
        ])
        from src.runtime.reports import NewReporter
        tb = NewReporter(db).TrialBalance("2026-07")
        assert tb.IsBalanced is True

    def test_balance_sheet_binding_total_assets(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "5000"),
            ("credit", "2026-07", "40", "5000"),
        ])
        from src.runtime.reports import NewReporter
        bs = NewReporter(db).BalanceSheet("2026-07")
        assert isinstance(bs.TotalAssets, float)
        assert bs.TotalAssets == pytest.approx(5000.0)

    def test_income_statement_binding_net_profit(self, db):
        _insert(db, [("credit", "2026-07", "70", "50000")])
        from src.runtime.reports import NewReporter
        pl = NewReporter(db).IncomeStatement("2026-07")
        assert isinstance(pl.NetProfit, float)

    def test_income_statement_binding_ytd(self, db):
        _insert(db, [
            ("credit", "2026-01", "70", "10000"),
            ("credit", "2026-07", "70", "10000"),
        ])
        from src.runtime.reports import NewReporter
        pl_ytd = NewReporter(db).IncomeStatement("2026-07", "ytd")
        assert pl_ytd.Revenue == pytest.approx(20000.0)

    def test_trilingual_ru_aliases(self, db):
        from src.runtime.reports import НовыйОтчетчик
        r = НовыйОтчетчик(db)
        assert callable(r.ОборотноСальдоваяВедомость)
        assert callable(r.Баланс)
        assert callable(r.ОтчетОПрибылях)

    def test_trilingual_uk_aliases(self, db):
        from src.runtime.reports import НовийЗвітник
        r = НовийЗвітник(db)
        assert callable(r.ОборотноСальдоваВідомість)
        assert callable(r.Баланс)
        assert callable(r.ЗвітПроПрибутки)


# ---------------------------------------------------------------------------
# TestReportEdgeCases
# ---------------------------------------------------------------------------

class TestReportEdgeCases:
    def test_missing_db_returns_503(self, client, tmp_path, monkeypatch):
        missing = tmp_path / "nonexistent.db"
        monkeypatch.setattr("src.server._ERP_DB_S13", missing)
        r = client.get("/api/v1/reports/trial-balance?period=2026-07")
        assert r.status_code == 503
        body = r.get_json()
        assert "error" in body
        assert "hint" in body

    def test_empty_db_no_500(self, client, db):
        r = client.get("/api/v1/reports/trial-balance?period=2026-07")
        assert r.status_code == 200
        body = r.get_json()
        assert body["rows"] == []

    def test_pdf_reportlab_import_error_returns_503(self, client, db):
        import builtins
        real_import = builtins.__import__
        def _block_reportlab(name, *args, **kwargs):
            if name.startswith("reportlab"):
                raise ImportError("reportlab not installed")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=_block_reportlab):
            r = client.get("/api/v1/reports/trial-balance?period=2026-07&format=pdf")
        assert r.status_code == 503

    def test_balance_sheet_yaml_missing_falls_back_to_default(self, db):
        _insert(db, [
            ("debit",  "2026-07", "31", "1000"),
            ("credit", "2026-07", "40", "1000"),
        ])
        import src.runtime.reports as rmod
        orig = rmod._account_mapping
        rmod._account_mapping = None  # force reload
        with patch.object(rmod, "_YAML_PATH", Path("/nonexistent/path.yaml")):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                data = rmod.BalanceSheetReport.compute("2026-07", db)
            assert any("hardcoded" in str(x.message).lower() or
                       "not found" in str(x.message).lower() for x in w)
        assert data["report"] == "balance-sheet"
        rmod._account_mapping = orig  # restore

    def test_balance_sheet_yaml_malformed_falls_back_to_default(self, db, tmp_path):
        import src.runtime.reports as rmod
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("accounts:\n  - [unclosed bracket\n  {{{{bad", encoding="utf-8")
        # Force re-evaluation by calling _load_account_mapping directly with cache cleared
        rmod._account_mapping = None
        with patch.object(rmod, "_YAML_PATH", bad_yaml):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = rmod._load_account_mapping()
            assert isinstance(result, dict)
            assert len(result) > 0  # fell back to hardcoded
            assert any(
                "hardcoded" in str(x.message).lower()
                or "fallback" in str(x.message).lower()
                or "malformed" in str(x.message).lower()
                or "failed" in str(x.message).lower()
                for x in w
            )
        rmod._account_mapping = None  # clear for other tests

    def test_trial_balance_text_amount_non_numeric(self, db):
        # Insert a row with a non-numeric amount — should not crash
        conn = sqlite3.connect(str(db))
        conn.execute(
            "INSERT INTO budget_entries (entry_type, period, account, amount)"
            " VALUES (?,?,?,?)",
            ("debit", "2026-07", "31", "not-a-number"),
        )
        conn.commit()
        conn.close()
        from src.runtime.reports import TrialBalanceReport
        data = TrialBalanceReport.compute("2026-07", db)
        assert data["report"] == "trial-balance"
        # non-numeric row treated as 0.0 — debit total should be 0
        assert data["totals"]["total_debit"] == pytest.approx(0.0)

    def test_income_statement_ytd_mixed_period_formats(self, db):
        _insert(db, [
            ("credit", "2026-1",  "70", "99999"),   # malformed — excluded
            ("credit", "2026-01", "70", "10000"),   # valid Jan
            ("credit", "2026-07", "70", "10000"),   # valid Jul
        ])
        from src.runtime.reports import IncomeStatement
        data = IncomeStatement.compute("2026-07", db, "ytd")
        # Only valid periods: Jan + Jul = 20000
        assert data["revenue"] == pytest.approx(20000.0)

    def test_to_excel_uses_precomputed_dict(self, db):
        """to_excel must not open a DB connection — it accepts pre-computed dict."""
        from src.runtime.reports import TrialBalanceReport
        from src.runtime import db as db_mod
        call_count = []
        original_connect = db_mod.connect
        def counting_connect(p):
            call_count.append(p)
            return original_connect(p)
        data = TrialBalanceReport.compute("2026-07", db)
        with patch.object(db_mod, "connect", side_effect=counting_connect):
            call_count.clear()
            buf = TrialBalanceReport.to_excel(data)
        assert len(call_count) == 0, "to_excel must not open DB — it receives pre-computed dict"
        assert buf.read()[:4] == b"PK\x03\x04"
