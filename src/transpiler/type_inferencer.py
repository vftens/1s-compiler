"""
1S Cython type inferencer — single-pass AST analysis.

Produces per-scope type maps used by the Cython backend to emit
`cdef` declarations and typed function signatures.

Supported Cython types:
  long    – integer literals, For-loop counters
  double  – float literals, any arithmetic with float
  bint    – boolean (Cython typed bool)
  object  – Python object (string, collection, date, Undefined, etc.)

Widening rules:
  long + long   → long
  long + double → double   (any float widens)
  * + object    → object   (any Python object widens to object)
"""
from __future__ import annotations
from ..parser.ast_nodes import (
    Module, Node, AssignStmt, VarDecl, ForStmt, ForEachStmt,
    WhileStmt, IfStmt, TryStmt, FunctionDef, ProcedureDef,
    ReturnStmt, Literal, Identifier, BinOp, UnaryOp, Ternary,
    CallExpr, MemberExpr, IndexExpr, NewExpr, Param,
)

# Cython type constants
_LONG   = "long"
_DOUBLE = "double"
_BINT   = "bint"
_OBJECT = "object"

# Arithmetic ops where both operands numeric → numeric result
_NUM_OPS = frozenset({"+", "-", "*", "%"})
# Division always yields float
_DIV_OPS = frozenset({"/", "//"})
# Comparison / logical → bint
_CMP_OPS = frozenset({"==", "!=", "<", "<=", ">", ">=", "and", "or", "not"})

# 1S / Python built-in calls whose return is always numeric
_NUMERIC_BUILTINS = frozenset({
    "Abs", "Int", "Round", "Окр", "Цел", "Округлити", "Ціле",
    "Max", "Min", "Макс", "Мін", "abs", "int", "round",
    "len", "СтрДлина", "ДовжинаРядка",
    "DayOfWeek", "ДеньНедели", "ДеньТижня",
    "WorkingDays", "РабочихДней",
})

_FLOAT_BUILTINS = frozenset({
    "Round", "Окр", "Округлити",
    "WorkingHours", "РабочихЧасов",
    "Format", "Формат",
})


def _widen(a: str, b: str) -> str:
    if a == b:
        return a
    if {a, b} <= {_LONG, _DOUBLE}:
        return _DOUBLE
    return _OBJECT


_UNSET = "__unset__"   # declared but not yet assigned — not a real Cython type


class ScopeTypes:
    """Type map for one scope (module or function)."""
    def __init__(self, parent: "ScopeTypes | None" = None):
        self.vars: dict[str, str] = {}   # name → type (or _UNSET)
        self.parent = parent

    def get(self, name: str) -> str:
        v = self.vars.get(name)
        if v is not None:
            return v if v != _UNSET else _OBJECT
        if self.parent:
            return self.parent.get(name)
        return _OBJECT

    def assign(self, name: str, ty: str):
        current = self.vars.get(name, _UNSET)
        if current == _UNSET:
            # First real assignment — accept the inferred type
            self.vars[name] = ty
        else:
            self.vars[name] = _widen(current, ty)

    def declare(self, name: str):
        if name not in self.vars:
            self.vars[name] = _UNSET   # placeholder; real type comes from assign()


class TypeInferencer:
    """
    Two-pass AST visitor.
    Pass 1 collects assignment types within each scope.
    Returns a ScopeTypes for the module and one per function.
    """

    def __init__(self):
        self.module_scope: ScopeTypes = ScopeTypes()
        self.func_scopes: dict[str, ScopeTypes] = {}

    # ── Public API ───────────────────────────────────────────────────────────

    def infer(self, module: Module) -> "TypeInferencer":
        self._walk_stmts(module.body, self.module_scope)
        return self

    def scope_for(self, func_name: str) -> ScopeTypes:
        return self.func_scopes.get(func_name, self.module_scope)

    # ── Statement walker ─────────────────────────────────────────────────────

    def _walk_stmts(self, stmts: list[Node], scope: ScopeTypes):
        for s in stmts:
            self._walk_stmt(s, scope)

    def _walk_stmt(self, stmt: Node, scope: ScopeTypes):
        match stmt:
            case VarDecl(names=names):
                for n in names:
                    scope.declare(n)

            case AssignStmt(target=Identifier(name=n), value=v):
                ty = self._expr_type(v, scope)
                scope.assign(n, ty)

            case AssignStmt(target=_, value=v):
                # subscript/member assign — value still has a type we might care about
                pass

            case ForStmt(var=v, start=s, end=e, body=body):
                scope.assign(v, _LONG)  # loop counter is always integer
                self._walk_stmts(body, scope)

            case ForEachStmt(var=v, body=body):
                scope.assign(v, _OBJECT)  # element type unknown
                self._walk_stmts(body, scope)

            case WhileStmt(body=body):
                self._walk_stmts(body, scope)

            case IfStmt(branches=branches, else_body=else_body):
                for branch in branches:
                    self._walk_stmts(branch.body, scope)
                if else_body:
                    self._walk_stmts(else_body, scope)

            case TryStmt(body=b, except_body=e):
                self._walk_stmts(b, scope)
                self._walk_stmts(e, scope)

            case FunctionDef(name=name, params=params, body=body) | \
                 ProcedureDef(name=name, params=params, body=body):
                func_scope = ScopeTypes(parent=self.module_scope)
                # Initial type: from default value if numeric, else UNSET
                for p in params:
                    if p.default:
                        dt = self._expr_type(p.default, func_scope)
                        func_scope.assign(p.name, dt)
                    else:
                        func_scope.declare(p.name)  # _UNSET — refined by usage below
                self._walk_stmts(body, func_scope)
                # Refine UNSET params by usage: if only used in arithmetic → double
                for p in params:
                    if func_scope.vars.get(p.name) == _UNSET:
                        usage = self._infer_param_usage(p.name, body, func_scope)
                        func_scope.vars[p.name] = usage
                self.func_scopes[name] = func_scope

    # ── Expression type inference ────────────────────────────────────────────

    def _expr_type(self, node: Node, scope: ScopeTypes) -> str:
        match node:
            case Literal(kind="integer"):
                return _LONG
            case Literal(kind="float"):
                return _DOUBLE
            case Literal(kind="bool"):
                return _BINT
            case Literal():
                return _OBJECT  # string, date, null, undefined

            case Identifier(name=n):
                return scope.get(n)

            case BinOp(op=op, left=l, right=r):
                if op in _DIV_OPS:
                    return _DOUBLE
                if op in _CMP_OPS:
                    return _BINT
                lt = self._expr_type(l, scope)
                rt = self._expr_type(r, scope)
                if op in _NUM_OPS and lt in (_LONG, _DOUBLE) and rt in (_LONG, _DOUBLE):
                    return _DOUBLE if (_DOUBLE in (lt, rt)) else _LONG
                return _OBJECT

            case UnaryOp(op="-"|"+", operand=o):
                t = self._expr_type(o, scope)
                return t if t in (_LONG, _DOUBLE) else _OBJECT
            case UnaryOp(op="not", operand=_):
                return _BINT

            case Ternary(if_true=t, if_false=f):
                return _widen(self._expr_type(t, scope), self._expr_type(f, scope))

            case CallExpr(callee=Identifier(name=n)):
                if n in _NUMERIC_BUILTINS:
                    return _LONG
                if n in _FLOAT_BUILTINS:
                    return _DOUBLE
                return _OBJECT

            case _:
                return _OBJECT

    # ── Parameter usage inference ────────────────────────────────────────────

    def _infer_param_usage(self, name: str, body: list[Node],
                           scope: ScopeTypes) -> str:
        """
        Walk body and see how `name` is used.
        If only in numeric contexts (arithmetic, comparison with literal) → double.
        Otherwise → object.
        """
        uses: list[str] = []
        self._collect_param_uses(name, body, scope, uses)
        if not uses:
            return _OBJECT
        if all(u in (_LONG, _DOUBLE) for u in uses):
            return _DOUBLE if _DOUBLE in uses else _LONG
        return _OBJECT

    def _collect_param_uses(self, name: str, stmts, scope: ScopeTypes,
                            out: list[str]):
        for s in stmts:
            self._collect_param_uses_expr(name, s, scope, out)

    def _collect_param_uses_expr(self, name: str, node: Node,
                                 scope: ScopeTypes, out: list[str]):
        match node:
            case BinOp(op=op, left=l, right=r):
                # If `name` appears directly in arithmetic → numeric usage
                if (isinstance(l, Identifier) and l.name == name) or \
                   (isinstance(r, Identifier) and r.name == name):
                    if op in _NUM_OPS | _DIV_OPS | _CMP_OPS:
                        out.append(_DOUBLE if op in _DIV_OPS else _LONG)
                self._collect_param_uses_expr(name, l, scope, out)
                self._collect_param_uses_expr(name, r, scope, out)
            case UnaryOp(op="-"|"+", operand=o):
                if isinstance(o, Identifier) and o.name == name:
                    out.append(_DOUBLE)
                self._collect_param_uses_expr(name, o, scope, out)
            case ReturnStmt(value=v) if v is not None:
                self._collect_param_uses_expr(name, v, scope, out)
            case AssignStmt(value=v):
                self._collect_param_uses_expr(name, v, scope, out)
            case CallExpr(args=args):
                for a in args:
                    # If used as arg to numeric builtin, it's numeric
                    match node:
                        case CallExpr(callee=Identifier(name=fn)) if fn in _NUMERIC_BUILTINS | _FLOAT_BUILTINS:
                            if isinstance(a, Identifier) and a.name == name:
                                out.append(_LONG)
                        case _:
                            pass
                    self._collect_param_uses_expr(name, a, scope, out)
            case IfStmt(branches=branches, else_body=else_body):
                for b in branches:
                    self._collect_param_uses_expr(name, b.condition, scope, out)
                    self._collect_param_uses(name, b.body, scope, out)
                if else_body:
                    self._collect_param_uses(name, else_body, scope, out)
            case WhileStmt(condition=c, body=b):
                self._collect_param_uses_expr(name, c, scope, out)
                self._collect_param_uses(name, b, scope, out)
            case ForStmt(body=b):
                self._collect_param_uses(name, b, scope, out)
            case TryStmt(body=b, except_body=e):
                self._collect_param_uses(name, b, scope, out)
                self._collect_param_uses(name, e, scope, out)

    # ── Return type of a function body ───────────────────────────────────────

    def infer_return_type(self, body: list[Node], scope: ScopeTypes) -> str:
        """Scan all ReturnStmt nodes; widen together."""
        returns: list[str] = []
        self._collect_returns(body, scope, returns)
        if not returns:
            return "void"
        result = returns[0]
        for r in returns[1:]:
            result = _widen(result, r)
        return result

    def _collect_returns(self, stmts: list[Node], scope: ScopeTypes, out: list[str]):
        for s in stmts:
            match s:
                case ReturnStmt(value=None):
                    out.append("void")
                case ReturnStmt(value=v):
                    out.append(self._expr_type(v, scope))
                case IfStmt(branches=branches, else_body=else_body):
                    for b in branches:
                        self._collect_returns(b.body, scope, out)
                    if else_body:
                        self._collect_returns(else_body, scope, out)
                case WhileStmt(body=body) | ForStmt(body=body) | ForEachStmt(body=body):
                    self._collect_returns(body, scope, out)
                case TryStmt(body=b, except_body=e):
                    self._collect_returns(b, scope, out)
                    self._collect_returns(e, scope, out)
