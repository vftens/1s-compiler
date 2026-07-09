"""
WorkflowConfig — YAML-configurable multi-level approval routing.
Rules match by: amount_lt, amount_gte, category_eq, org_eq.
First matching rule wins (SAP condition technique order).
"""
from __future__ import annotations
import os
import warnings
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass
class WFRule:
    condition: dict
    approvers: List[str]

    def matches(self, amount: Decimal, category: str = "", org_id: str = "") -> bool:
        c = self.condition
        if "amount_lt" in c and not (amount < Decimal(str(c["amount_lt"]))):
            return False
        if "amount_gte" in c and not (amount >= Decimal(str(c["amount_gte"]))):
            return False
        if "amount_lte" in c and not (amount <= Decimal(str(c["amount_lte"]))):
            return False
        if "amount_gt" in c and not (amount > Decimal(str(c["amount_gt"]))):
            return False
        if "category_eq" in c and category != c["category_eq"]:
            return False
        if "org_eq" in c and org_id != c["org_eq"]:
            return False
        return True

    def __repr__(self) -> str:
        return f"WFRule({self.condition} → {self.approvers})"


class WorkflowConfig:
    """
    Configurable approval routing loaded from YAML or dict.

    Usage:
        cfg = WorkflowConfig.load("profiles/workflow/default.yaml")
        approvers = cfg.get_approvers("purchase_order", amount=75000, category="capex")
        # → ["dept_head", "cfo"]
    """

    _DEFAULT_RULES: Dict[str, List[WFRule]] = {
        "purchase_order": [
            WFRule({"amount_lt": 50000},   ["dept_head"]),
            WFRule({"amount_lt": 500000},  ["dept_head", "cfo"]),
            WFRule({"amount_gte": 500000}, ["dept_head", "cfo", "ceo"]),
        ],
        "repair_order": [
            WFRule({"amount_lt": 100000},  ["maintenance_manager"]),
            WFRule({"amount_gte": 100000}, ["maintenance_manager", "cfo"]),
        ],
        "*": [
            WFRule({}, ["manager"]),
        ],
    }

    def __init__(self, rules: Optional[Dict[str, List[WFRule]]] = None):
        self._rules: Dict[str, List[WFRule]] = rules if rules is not None else {}

    @classmethod
    def default(cls) -> "WorkflowConfig":
        return cls(rules=dict(cls._DEFAULT_RULES))

    @classmethod
    def load(cls, yaml_path: str) -> "WorkflowConfig":
        """Load from YAML file, fall back to default if file missing."""
        if not os.path.isfile(yaml_path):
            warnings.warn(f"WorkflowConfig: {yaml_path!r} not found, using defaults")
            return cls.default()
        try:
            import yaml
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            warnings.warn(f"WorkflowConfig: error loading {yaml_path}: {e} — using defaults")
            return cls.default()

        rules: Dict[str, List[WFRule]] = {}
        for doc_type, rule_list in data.items():
            rules[doc_type] = []
            for entry in rule_list:
                cond      = entry.get("condition", {})
                approvers = entry.get("approvers", ["manager"])
                rules[doc_type].append(WFRule(condition=cond, approvers=approvers))
        return cls(rules=rules)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowConfig":
        rules: Dict[str, List[WFRule]] = {}
        for doc_type, rule_list in data.items():
            rules[doc_type] = []
            for entry in rule_list:
                rules[doc_type].append(
                    WFRule(condition=entry.get("condition", {}),
                           approvers=entry.get("approvers", ["manager"]))
                )
        return cls(rules=rules)

    def get_approvers(
        self,
        doc_type: str,
        amount:   Decimal | float | int = 0,
        category: str = "",
        org_id:   str = "",
    ) -> List[str]:
        """Return the ordered approver list for this document."""
        amount = Decimal(str(amount))

        # Exact doc type first
        for rule_list_key in (doc_type, "*"):
            rule_list = self._rules.get(rule_list_key, [])
            for rule in rule_list:
                if rule.matches(amount, category, org_id):
                    return list(rule.approvers)

        # Fallback: single manager level
        return ["manager"]

    def describe(self, doc_type: Optional[str] = None) -> str:
        lines = ["WorkflowConfig routing rules:"]
        keys  = [doc_type] if doc_type else list(self._rules.keys())
        for key in keys:
            lines.append(f"  {key}:")
            for rule in self._rules.get(key, []):
                lines.append(f"    {rule.condition} → {rule.approvers}")
        return "\n".join(lines)

    def add_rule(self, doc_type: str, condition: dict, approvers: List[str]) -> None:
        self._rules.setdefault(doc_type, []).append(WFRule(condition=condition, approvers=approvers))

    # ── English method aliases ───────────────────────────────────────────────
    GetApprovers = get_approvers
    AddRule      = add_rule
    Describe     = describe

    # ── Russian method aliases ───────────────────────────────────────────────
    def ПолучитьУтверждающих(self, doc_type, amount=0, category="", org_id=""):
        return self.get_approvers(doc_type, amount, category, org_id)
    def ДобавитьПравило(self, doc_type, condition, approvers):
        return self.add_rule(doc_type, condition, approvers)
    def Описание(self, doc_type=None): return self.describe(doc_type)

    # ── Ukrainian method aliases ─────────────────────────────────────────────
    def ОтриматиЗатверджуючих(self, doc_type, amount=0, category="", org_id=""):
        return self.get_approvers(doc_type, amount, category, org_id)
    def ДодатиПравило(self, doc_type, condition, approvers):
        return self.add_rule(doc_type, condition, approvers)

    def __repr__(self) -> str:
        return f"WorkflowConfig({list(self._rules.keys())})"


# ── Trilingual class aliases ─────────────────────────────────────────────────
НастройкиМаршрута    = WorkflowConfig
НалаштуванняМаршруту = WorkflowConfig


# ── Module-level loader helpers (for .1s scripts: НастройкиМаршрута.Загрузить) ──
# Attach as classmethods after class definition
WorkflowConfig.Загрузить    = classmethod(lambda cls, p: cls.load(p))
WorkflowConfig.По_умолчанию = classmethod(lambda cls: cls.default())
WorkflowConfig.Завантажити  = classmethod(lambda cls, p: cls.load(p))
WorkflowConfig.За_замовчанням = classmethod(lambda cls: cls.default())
