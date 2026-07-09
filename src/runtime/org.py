"""
OrgUnit — organizational hierarchy (Holding → LegalEntity → Plant → Department → CostCenter → ProfitCenter).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict


class OrgType(str, Enum):
    HOLDING       = "holding"
    LEGAL_ENTITY  = "legal_entity"
    PLANT         = "plant"
    DEPARTMENT    = "department"
    COST_CENTER   = "cost_center"
    PROFIT_CENTER = "profit_center"


@dataclass
class OrgNode:
    id:       str
    name:     str
    org_type: OrgType
    parent:   Optional["OrgNode"] = field(default=None, repr=False)
    children: List["OrgNode"]     = field(default_factory=list, repr=False)

    def __repr__(self) -> str:
        return f"OrgNode({self.id!r}, {self.org_type.value}, {self.name!r})"

    # ── path to root ────────────────────────────────────────────────────────
    def path_to_root(self) -> List["OrgNode"]:
        path, node = [self], self.parent
        while node:
            path.append(node)
            node = node.parent
        return list(reversed(path))

    def full_path(self) -> str:
        return " / ".join(n.name for n in self.path_to_root())

    # ── English property aliases ─────────────────────────────────────────────
    @property
    def Id(self):   return self.id
    @property
    def Name(self): return self.name
    @property
    def Type(self): return self.org_type
    @property
    def Parent(self): return self.parent
    @property
    def Children(self): return self.children

    # ── Russian property aliases ─────────────────────────────────────────────
    @property
    def Код(self):           return self.id
    @property
    def Наименование(self):  return self.name
    @property
    def Тип(self):           return self.org_type
    @property
    def Родитель(self):      return self.parent
    @property
    def Подчиненные(self):   return self.children
    @property
    def ПолныйПуть(self):   return self.full_path()

    # ── Ukrainian property aliases ───────────────────────────────────────────
    @property
    def Назва(self):         return self.name
    @property
    def Батько(self):        return self.parent
    @property
    def Підлеглі(self):      return self.children
    @property
    def ПовнийШлях(self):   return self.full_path()


class OrgChart:
    """Organizational chart — holds the full hierarchy of OrgNodes."""

    def __init__(self, company_name: str = "Company"):
        root = OrgNode(id="root", name=company_name, org_type=OrgType.HOLDING)
        self._nodes: Dict[str, OrgNode] = {"root": root}
        self._root = root

    # ── node management ──────────────────────────────────────────────────────
    def add_node(
        self,
        node_id:   str,
        name:      str,
        org_type:  OrgType | str,
        parent_id: str = "root",
    ) -> OrgNode:
        if isinstance(org_type, str):
            org_type = OrgType(org_type)
        parent = self._nodes.get(parent_id)
        if parent is None:
            raise ValueError(f"Parent node {parent_id!r} not found")
        if node_id in self._nodes:
            raise ValueError(f"Node {node_id!r} already exists")
        node = OrgNode(id=node_id, name=name, org_type=org_type, parent=parent)
        parent.children.append(node)
        self._nodes[node_id] = node
        return node

    def find(self, node_id: str) -> Optional[OrgNode]:
        return self._nodes.get(node_id)

    def get(self, node_id: str) -> OrgNode:
        node = self._nodes.get(node_id)
        if node is None:
            raise KeyError(f"OrgNode {node_id!r} not found")
        return node

    @property
    def root(self) -> OrgNode:
        return self._root

    def all_nodes(self) -> List[OrgNode]:
        return list(self._nodes.values())

    def report(self) -> str:
        lines = []
        def _walk(node: OrgNode, depth: int = 0):
            prefix = "  " * depth + ("└─ " if depth else "")
            lines.append(f"{prefix}[{node.org_type.value}] {node.name} ({node.id})")
            for child in node.children:
                _walk(child, depth + 1)
        _walk(self._root)
        return "\n".join(lines)

    # ── English method aliases ───────────────────────────────────────────────
    AddNode  = add_node
    Find     = find
    Get      = get
    Report   = report
    AllNodes = all_nodes

    # ── Russian method aliases ───────────────────────────────────────────────
    def ДобавитьУзел(self, id, name, typ, parent="root"):
        return self.add_node(id, name, typ, parent)
    def НайтиУзел(self, id):   return self.find(id)
    def ПолучитьУзел(self, id): return self.get(id)
    def Отчет(self):            return self.report()
    def ВсеУзлы(self):         return self.all_nodes()

    # ── Ukrainian method aliases ─────────────────────────────────────────────
    def ДодатиВузол(self, id, name, typ, parent="root"):
        return self.add_node(id, name, typ, parent)
    def ЗнайтиВузол(self, id):    return self.find(id)
    def ОтриматиВузол(self, id):  return self.get(id)
    def Звіт(self):               return self.report()
    def УсіВузли(self):           return self.all_nodes()

    def __repr__(self) -> str:
        return f"OrgChart({self._root.name!r}, {len(self._nodes)} nodes)"


# ── module-level type constants (for .1s scripts) ───────────────────────────
HOLDING       = OrgType.HOLDING
LEGAL_ENTITY  = OrgType.LEGAL_ENTITY
PLANT         = OrgType.PLANT
DEPARTMENT    = OrgType.DEPARTMENT
COST_CENTER   = OrgType.COST_CENTER
PROFIT_CENTER = OrgType.PROFIT_CENTER

# Russian constants
ХОЛДИНГ          = OrgType.HOLDING
ЮРИДИЧЕСКОЕ_ЛИЦО = OrgType.LEGAL_ENTITY
ЗАВОД            = OrgType.PLANT
ОТДЕЛ            = OrgType.DEPARTMENT
МВЗ              = OrgType.COST_CENTER   # Место возникновения затрат
ЦЕНТР_ПРИБЫЛИ    = OrgType.PROFIT_CENTER

# Ukrainian constants
ПІДПРИЄМСТВО = OrgType.LEGAL_ENTITY
ЦЕХ          = OrgType.PLANT
ВІДДІЛ       = OrgType.DEPARTMENT
МВВ          = OrgType.COST_CENTER    # Місце виникнення витрат

# Trilingual class aliases
ОрганизационнаяСтруктура = OrgChart
ОрганізаційнаСтруктура   = OrgChart
