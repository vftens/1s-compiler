"""
Sprint 11 tests — SQLite persistence for Sprint 10 ERP modules + ERP query layer.
"""
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.runtime.org import OrgChart, OrgType
from src.runtime.budget import BudgetControl
from src.runtime.payroll import PayrollEngine, Employee, BonusScheme
from src.runtime.tax_engine import TaxEngine
from src.runtime.workflow_config import WorkflowConfig, WFRule
from src.runtime.persistence import (
    save_org_chart, load_org_chart,
    save_budget, load_budget,
    save_payroll_results, load_payroll_results,
    save_workflow_config, load_workflow_config,
)
from src.runtime.erp_query import ERPQuery


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_erp.db")


# ── OrgChart persistence ──────────────────────────────────────────────────────

class TestOrgChartPersistence:

    def test_save_and_load_roundtrip(self, db_path):
        org = OrgChart("Test Holding")
        org.add_node("le1", "Legal Entity 1", "legal_entity", "root")
        org.add_node("p1",  "Plant 1",        "plant",         "le1")
        org.add_node("cc1", "Cost Center 1",  "cost_center",   "p1")

        count = save_org_chart(org, db_path)
        assert count == 3  # 3 non-root nodes saved

        org2 = load_org_chart(db_path, "Test Holding")
        assert len(org2._nodes) == 4  # 3 + auto-created root
        assert org2.find("cc1").name == "Cost Center 1"
        assert org2.find("cc1").parent.id == "p1"

    def test_load_missing_db_returns_empty_org(self, tmp_path):
        org = load_org_chart(str(tmp_path / "nonexistent.db"), "X")
        assert org._root.name == "X"
        assert len(org._nodes) == 1  # only root

    def test_save_overwrites_same_org_name(self, db_path):
        org1 = OrgChart("Corp")
        org1.add_node("n1", "Node One", "plant", "root")
        save_org_chart(org1, db_path)

        org2 = OrgChart("Corp")
        org2.add_node("n2", "Node Two", "plant", "root")
        org2.add_node("n3", "Node Three", "department", "n2")
        save_org_chart(org2, db_path)

        loaded = load_org_chart(db_path, "Corp")
        assert "n1" not in loaded._nodes
        assert "n2" in loaded._nodes and "n3" in loaded._nodes

    def test_multiple_orgs_in_same_db(self, db_path):
        o1 = OrgChart("OrgA")
        o1.add_node("a1", "A-Plant", "plant", "root")
        o2 = OrgChart("OrgB")
        o2.add_node("b1", "B-Plant", "plant", "root")
        o2.add_node("b2", "B-Dept",  "department", "b1")

        save_org_chart(o1, db_path)
        save_org_chart(o2, db_path)

        loaded_a = load_org_chart(db_path, "OrgA")
        loaded_b = load_org_chart(db_path, "OrgB")
        assert len(loaded_a._nodes) == 2   # root + a1
        assert len(loaded_b._nodes) == 3   # root + b1 + b2


# ── BudgetControl persistence ─────────────────────────────────────────────────

class TestBudgetPersistence:

    def _make_budget(self):
        b = BudgetControl(hard_stop=True, warn_threshold=0.85)
        b.allocate("cc1", "2024-01", "materials", 500000)
        b.allocate("cc1", "2024-01", "services",  100000)
        b.commit("cc1", "2024-01", 200000, "PO-001", "materials")
        b.consume("cc1", "2024-01", 180000, "INV-001", "materials")
        return b

    def test_save_and_load_roundtrip(self, db_path):
        b = self._make_budget()
        count = save_budget(b, db_path)
        assert count > 0

        b2 = load_budget(db_path)
        bal = b2.balance("cc1", "2024-01", "materials")
        assert bal.allocated == Decimal("500000")
        assert bal.committed == Decimal("200000")
        assert bal.consumed == Decimal("180000")
        assert bal.available == Decimal("120000")  # 500k - 200k committed - 180k consumed

    def test_load_missing_db_returns_empty_budget(self, tmp_path):
        b = load_budget(str(tmp_path / "missing.db"))
        assert len(b._allocations) == 0
        assert len(b._entries) == 0

    def test_utilization_after_reload(self, db_path):
        b = self._make_budget()
        save_budget(b, db_path)
        b2 = load_budget(db_path)
        bal = b2.balance("cc1", "2024-01", "materials")
        # (200k committed + 180k consumed) / 500k * 100 = 76%
        assert bal.utilization_pct == pytest.approx(76.0, abs=0.1)


# ── PayrollResults persistence ────────────────────────────────────────────────

class TestPayrollPersistence:

    def _make_results(self):
        tax = TaxEngine()
        pr = PayrollEngine(tax)
        pr.add_employee(Employee("E01", "Alice Smith", "Manager", 8000, "us_2024"))
        pr.add_employee(Employee("E02", "Bob Jones",   "Dev",     6500, "us_2024"))
        pr.add_absence("E02", "sick", 2, "2024-01")
        return pr.calculate("2024-01")

    def test_save_and_load_roundtrip(self, db_path):
        results = self._make_results()
        count = save_payroll_results(results, db_path)
        assert count == 2

        loaded = load_payroll_results(db_path, "2024-01")
        assert len(loaded) == 2

        alice = next(r for r in loaded if r["emp_id"] == "E01")
        bob   = next(r for r in loaded if r["emp_id"] == "E02")

        assert alice["emp_name"] == "Alice Smith"
        assert alice["gross"] == Decimal("8000")
        assert alice["net"] < alice["gross"]  # taxes applied
        assert bob["gross"] < Decimal("6500")  # sick days deducted

    def test_load_no_period_returns_all(self, db_path):
        results = self._make_results()
        save_payroll_results(results, db_path)

        all_records = load_payroll_results(db_path)
        assert len(all_records) == 2

    def test_load_wrong_period_returns_empty(self, db_path):
        results = self._make_results()
        save_payroll_results(results, db_path)

        none = load_payroll_results(db_path, "1999-01")
        assert none == []

    def test_payroll_lines_saved(self, db_path):
        results = self._make_results()
        save_payroll_results(results, db_path)
        loaded = load_payroll_results(db_path, "2024-01")

        alice = next(r for r in loaded if r["emp_id"] == "E01")
        assert len(alice["lines"]) > 0
        line_types = {ln["line_type"] for ln in alice["lines"]}
        assert "deduction" in line_types


# ── WorkflowConfig persistence ────────────────────────────────────────────────

class TestWorkflowConfigPersistence:

    def _make_config(self):
        cfg = WorkflowConfig()
        cfg._rules["purchase_order"] = [
            WFRule({"amount_lt": 50000}, ["dept_head"]),
            WFRule({"amount_gte": 50000}, ["dept_head", "cfo"]),
        ]
        cfg._rules["repair_order"] = [
            WFRule({"amount_lt": 100000}, ["maintenance_mgr"]),
        ]
        return cfg

    def test_save_and_load_roundtrip(self, db_path):
        cfg = self._make_config()
        count = save_workflow_config(cfg, db_path)
        assert count == 2

        cfg2 = load_workflow_config(db_path)
        assert "purchase_order" in cfg2._rules
        assert "repair_order" in cfg2._rules
        assert len(cfg2._rules["purchase_order"]) == 2
        assert cfg2._rules["purchase_order"][0].approvers == ["dept_head"]
        assert cfg2._rules["repair_order"][0].condition == {"amount_lt": 100000}

    def test_get_approvers_works_after_reload(self, db_path):
        cfg = self._make_config()
        save_workflow_config(cfg, db_path)

        cfg2 = load_workflow_config(db_path)
        approvers_small = cfg2.get_approvers("purchase_order", 30000)
        approvers_large = cfg2.get_approvers("purchase_order", 75000)
        assert approvers_small == ["dept_head"]
        assert "cfo" in approvers_large


# ── ERPQuery ──────────────────────────────────────────────────────────────────

class TestERPQuery:

    def _seed_db(self, db_path):
        """Seed a DB with budget + payroll data for query tests."""
        b = BudgetControl(hard_stop=False)
        b.allocate("cc1", "2024-01", "materials", 300000)
        b.allocate("cc2", "2024-01", "materials", 200000)
        b.commit("cc1", "2024-01", 100000, "PO-001", "materials")
        b.commit("cc2", "2024-01",  80000, "PO-002", "materials")
        b.consume("cc1", "2024-01",  90000, "INV-001", "materials")
        save_budget(b, db_path)

        tax = TaxEngine()
        pr = PayrollEngine(tax)
        pr.add_employee(Employee("E01", "Carol White", "CTO", 10000, "us_2024"))
        pr.add_employee(Employee("E02", "Dave Brown",  "Dev",  7000, "us_2024"))
        results = pr.calculate("2024-01")
        save_payroll_results(results, db_path)

    def test_budget_utilization_all(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.budget_utilization()
        assert len(rows) == 2  # cc1 and cc2
        cc1 = next(r for r in rows if r["org_id"] == "cc1")
        assert cc1["committed"] == Decimal("100000")
        assert cc1["consumed"] == Decimal("90000")
        assert cc1["utilization_pct"] == pytest.approx(63.3, abs=0.1)

    def test_budget_utilization_filtered(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.budget_utilization(org_id="cc2", period="2024-01")
        assert len(rows) == 1
        assert rows[0]["org_id"] == "cc2"

    def test_po_spend_by_supplier(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.po_spend_by_supplier(period="2024-01")
        # 2 commitments (PO-001, PO-002) + 1 consumption (INV-001) = 3 distinct doc_refs
        assert len(rows) >= 2
        doc_numbers = [r["doc_number"] for r in rows]
        assert "PO-001" in doc_numbers
        assert "PO-002" in doc_numbers

    def test_payroll_history_all(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.payroll_history(period="2024-01")
        assert len(rows) == 2
        names = [r["emp_name"] for r in rows]
        assert "Carol White" in names

    def test_payroll_history_filtered(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.payroll_history(emp_id="E01", period="2024-01")
        assert len(rows) == 1
        assert rows[0]["emp_id"] == "E01"

    def test_summary_report(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        s = q.summary_report(period="2024-01")
        assert s["budget_allocated"] == Decimal("500000")
        assert s["budget_consumed"] == Decimal("90000")
        assert s["payroll_gross"] > 0
        assert s["payroll_net"] < s["payroll_gross"]
        assert s["employee_count"] == 2

    def test_missing_db_returns_empty(self, tmp_path):
        q = ERPQuery(str(tmp_path / "missing.db"))
        assert q.budget_utilization() == []
        assert q.payroll_history() == []
        assert q.po_spend_by_supplier() == []

    def test_format_report_budget(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.budget_utilization()
        text = q.format_report("budget_utilization", rows, "en")
        assert "Budget Utilization" in text
        assert "cc1" in text

    def test_format_report_payroll(self, db_path):
        self._seed_db(db_path)
        q = ERPQuery(db_path)
        rows = q.payroll_history(period="2024-01")
        text = q.format_report("payroll_history", rows, "en")
        assert "Payroll History" in text
        assert "Carol White" in text

    def test_format_report_empty_returns_no_data(self, db_path):
        q = ERPQuery(db_path)
        text = q.format_report("budget_utilization", [], "en")
        assert "No data" in text


# ── Trilingual aliases ────────────────────────────────────────────────────────

class TestTrilingualAliases:

    def test_persistence_ru_aliases(self, db_path):
        from src.runtime.persistence import (
            СохранитьОргСтруктуру, ЗагрузитьОргСтруктуру,
            СохранитьБюджет, ЗагрузитьБюджет,
        )
        org = OrgChart("Test")
        org.add_node("x1", "Node X", "plant", "root")
        СохранитьОргСтруктуру(org, db_path)
        org2 = ЗагрузитьОргСтруктуру(db_path, "Test")
        assert org2.find("x1") is not None

        b = BudgetControl()
        b.allocate("x1", "2024-01", "misc", 1000)
        СохранитьБюджет(b, db_path)
        b2 = ЗагрузитьБюджет(db_path)
        assert len(b2._allocations) == 1

    def test_persistence_uk_aliases(self, db_path):
        from src.runtime.persistence import (
            ЗберегтиОргСтруктуру, ЗавантажитиОргСтруктуру,
            ЗберегтиБюджет, ЗавантажитиБюджет,
        )
        org = OrgChart("TestUA")
        org.add_node("y1", "Вузел Y", "plant", "root")
        ЗберегтиОргСтруктуру(org, db_path)
        org2 = ЗавантажитиОргСтруктуру(db_path, "TestUA")
        assert org2.find("y1") is not None

    def test_erp_query_aliases(self, db_path):
        from src.runtime.erp_query import ЗапросERPe, ЗапитERPe
        q1 = ЗапросERPe(db_path)
        q2 = ЗапитERPe(db_path)
        assert isinstance(q1, ERPQuery)
        assert isinstance(q2, ERPQuery)
