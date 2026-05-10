"""
1S: ERP Free Edition — AST node definitions
All nodes are dataclasses for easy traversal and serialization.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Base ─────────────────────────────────────────────────────────────────────

@dataclass
class Node:
    line: int = field(default=0, repr=False)
    col: int  = field(default=0, repr=False)


# ── Top-level ────────────────────────────────────────────────────────────────

@dataclass
class Module(Node):
    """Root node: a .1s file or inline module."""
    body: list[Node] = field(default_factory=list)
    name: str = "<module>"


# ── Declarations ────────────────────────────────────────────────────────────

@dataclass
class VarDecl(Node):
    """Перем / Var  statement."""
    names: list[str] = field(default_factory=list)
    export: bool = False


@dataclass
class Param(Node):
    name: str = ""
    by_value: bool = False          # Знач / Val
    default: Optional[Node] = None


@dataclass
class ProcedureDef(Node):
    name: str = ""
    params: list[Param] = field(default_factory=list)
    body: list[Node] = field(default_factory=list)
    export: bool = False


@dataclass
class FunctionDef(Node):
    name: str = ""
    params: list[Param] = field(default_factory=list)
    body: list[Node] = field(default_factory=list)
    export: bool = False


# ── Statements ───────────────────────────────────────────────────────────────

@dataclass
class AssignStmt(Node):
    target: Node = field(default_factory=lambda: Identifier())
    value: Node  = field(default_factory=lambda: Identifier())


@dataclass
class CallStmt(Node):
    """Procedure call as a statement (return value discarded)."""
    call: Node = field(default_factory=lambda: Identifier())


@dataclass
class ReturnStmt(Node):
    value: Optional[Node] = None


@dataclass
class BreakStmt(Node):
    pass


@dataclass
class ContinueStmt(Node):
    pass


@dataclass
class RaiseStmt(Node):
    value: Optional[Node] = None   # None = re-raise current exception


@dataclass
class GotoStmt(Node):
    label: str = ""


@dataclass
class LabelStmt(Node):
    name: str = ""


# ── If statement ─────────────────────────────────────────────────────────────

@dataclass
class IfBranch(Node):
    condition: Node = field(default_factory=lambda: Identifier())
    body: list[Node] = field(default_factory=list)


@dataclass
class IfStmt(Node):
    branches: list[IfBranch] = field(default_factory=list)   # if + elseifs
    else_body: list[Node] = field(default_factory=list)


# ── Loops ────────────────────────────────────────────────────────────────────

@dataclass
class WhileStmt(Node):
    condition: Node = field(default_factory=lambda: Identifier())
    body: list[Node] = field(default_factory=list)


@dataclass
class ForStmt(Node):
    """Для А = 1 По 10 Цикл / For A = 1 To 10 Do"""
    var: str = ""
    start: Node = field(default_factory=lambda: Literal())
    end: Node   = field(default_factory=lambda: Literal())
    body: list[Node] = field(default_factory=list)


@dataclass
class ForEachStmt(Node):
    """Для Каждого Э Из Коллекция Цикл / For Each E In Collection Do"""
    var: str = ""
    collection: Node = field(default_factory=lambda: Identifier())
    body: list[Node] = field(default_factory=list)


# ── Try / Except ─────────────────────────────────────────────────────────────

@dataclass
class TryStmt(Node):
    body: list[Node] = field(default_factory=list)
    except_body: list[Node] = field(default_factory=list)


# ── Expressions ──────────────────────────────────────────────────────────────

@dataclass
class Literal(Node):
    value: Any = None
    kind: str = "integer"   # integer | float | string | date | bool | null | undefined


@dataclass
class Identifier(Node):
    name: str = ""


@dataclass
class BinOp(Node):
    op: str = ""
    left: Node  = field(default_factory=lambda: Literal())
    right: Node = field(default_factory=lambda: Literal())


@dataclass
class UnaryOp(Node):
    op: str = ""
    operand: Node = field(default_factory=lambda: Literal())


@dataclass
class Ternary(Node):
    """Условие ? ДаЗначение : НетЗначение"""
    condition: Node = field(default_factory=lambda: Literal())
    if_true: Node   = field(default_factory=lambda: Literal())
    if_false: Node  = field(default_factory=lambda: Literal())


@dataclass
class CallExpr(Node):
    callee: Node = field(default_factory=lambda: Identifier())
    args: list[Node] = field(default_factory=list)


@dataclass
class IndexExpr(Node):
    obj: Node   = field(default_factory=lambda: Identifier())
    index: Node = field(default_factory=lambda: Literal())


@dataclass
class MemberExpr(Node):
    obj: Node  = field(default_factory=lambda: Identifier())
    member: str = ""


@dataclass
class NewExpr(Node):
    """Новый ТипОбъекта(...)  /  New ObjectType(...)"""
    type_name: str = ""
    args: list[Node] = field(default_factory=list)


# ── Query literal ────────────────────────────────────────────────────────────

@dataclass
class QueryExpr(Node):
    """
    Embedded query passed to Запрос() / Query() constructor.
    raw_text is the original bilingual SQL-like string.
    params are &ИмяПараметра / &ParamName substitutions.
    """
    raw_text: str = ""
    params: list[str] = field(default_factory=list)


# ── Preprocessor ─────────────────────────────────────────────────────────────

@dataclass
class PPRegion(Node):
    name: str = ""
    body: list[Node] = field(default_factory=list)


@dataclass
class PPIfBlock(Node):
    condition_str: str = ""          # raw string; evaluated at compile time
    body: list[Node] = field(default_factory=list)
    else_body: list[Node] = field(default_factory=list)
