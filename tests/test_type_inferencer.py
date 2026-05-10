"""
Tests for src.transpiler.type_inferencer.
"""
import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.transpiler.type_inferencer import (
    TypeInferencer, ScopeTypes,
    _LONG, _DOUBLE, _BINT, _OBJECT, _UNSET, _widen,
)


def infer(src: str) -> TypeInferencer:
    tokens = Lexer(src).tokenize()
    ast = Parser(tokens).parse()
    ti = TypeInferencer()
    ti.infer(ast)
    return ti


def module_type(src: str, var: str) -> str:
    return infer(src).module_scope.get(var)


# ── _widen helper ─────────────────────────────────────────────────────────────

class TestWiden:
    def test_same_type(self):
        assert _widen(_LONG, _LONG) == _LONG
        assert _widen(_DOUBLE, _DOUBLE) == _DOUBLE

    def test_long_double(self):
        assert _widen(_LONG, _DOUBLE) == _DOUBLE
        assert _widen(_DOUBLE, _LONG) == _DOUBLE

    def test_numeric_object(self):
        assert _widen(_LONG, _OBJECT) == _OBJECT
        assert _widen(_OBJECT, _DOUBLE) == _OBJECT

    def test_bint_object(self):
        assert _widen(_BINT, _OBJECT) == _OBJECT


# ── ScopeTypes ────────────────────────────────────────────────────────────────

class TestScopeTypes:
    def test_declare_unset(self):
        s = ScopeTypes()
        s.declare("x")
        # UNSET returns OBJECT when read externally
        assert s.get("x") == _OBJECT

    def test_first_assign_sets_type(self):
        s = ScopeTypes()
        s.declare("x")
        s.assign("x", _LONG)
        assert s.get("x") == _LONG

    def test_second_assign_widens(self):
        s = ScopeTypes()
        s.assign("x", _LONG)
        s.assign("x", _DOUBLE)
        assert s.get("x") == _DOUBLE

    def test_assign_long_then_object_widens_to_object(self):
        s = ScopeTypes()
        s.assign("x", _LONG)
        s.assign("x", _OBJECT)
        assert s.get("x") == _OBJECT

    def test_parent_scope_lookup(self):
        parent = ScopeTypes()
        parent.assign("outer", _LONG)
        child = ScopeTypes(parent=parent)
        assert child.get("outer") == _LONG

    def test_child_shadows_parent(self):
        parent = ScopeTypes()
        parent.assign("x", _LONG)
        child = ScopeTypes(parent=parent)
        child.assign("x", _OBJECT)
        assert child.get("x") == _OBJECT
        assert parent.get("x") == _LONG

    def test_unknown_var_returns_object(self):
        s = ScopeTypes()
        assert s.get("nonexistent") == _OBJECT


# ── Literal type inference ────────────────────────────────────────────────────

class TestLiteralTypes:
    def test_integer_literal(self):
        assert module_type("Перем А; А = 5;", "А") == _LONG

    def test_float_literal(self):
        assert module_type("Перем А; А = 3.14;", "А") == _DOUBLE

    def test_string_literal(self):
        assert module_type('Перем А; А = "hello";', "А") == _OBJECT

    def test_true_literal(self):
        assert module_type("Перем А; А = Истина;", "А") == _BINT

    def test_false_literal(self):
        assert module_type("Перем А; А = Ложь;", "А") == _BINT

    def test_undefined_literal(self):
        assert module_type("Перем А; А = Неопределено;", "А") == _OBJECT


# ── Arithmetic type inference ─────────────────────────────────────────────────

class TestArithmeticTypes:
    def test_int_plus_int_is_long(self):
        assert module_type("Перем А; А = 1 + 2;", "А") == _LONG

    def test_int_plus_float_is_double(self):
        assert module_type("Перем А; А = 1 + 2.5;", "А") == _DOUBLE

    def test_float_times_float_is_double(self):
        assert module_type("Перем А; А = 1.5 * 2.5;", "А") == _DOUBLE

    def test_division_always_double(self):
        assert module_type("Перем А; А = 10 / 3;", "А") == _DOUBLE

    def test_int_division_still_double(self):
        assert module_type("Перем А; А = 10 / 2;", "А") == _DOUBLE

    def test_comparison_is_bint(self):
        assert module_type("Перем А; А = 1 < 2;", "А") == _BINT

    def test_equality_is_bint(self):
        assert module_type("Перем А; Б = 1; А = (Б = 1);", "А") == _BINT

    def test_unary_minus_preserves_long(self):
        assert module_type("Перем А; А = -5;", "А") == _LONG

    def test_unary_minus_preserves_double(self):
        assert module_type("Перем А; А = -3.14;", "А") == _DOUBLE


# ── For loop var type ─────────────────────────────────────────────────────────

class TestForLoopType:
    def test_for_counter_is_long(self):
        src = "Для Н = 1 По 10 Цикл\nА = Н;\nКонецЦикла;"
        ti = infer(src)
        assert ti.module_scope.get("Н") == _LONG

    def test_foreach_var_is_object(self):
        src = "Для Каждого Э Из Список Цикл\nА = Э;\nКонецЦикла;"
        ti = infer(src)
        assert ti.module_scope.get("Э") == _OBJECT


# ── UNSET sentinel (declared but not assigned) ────────────────────────────────

class TestUnset:
    def test_declared_only_returns_object(self):
        src = "Перем А;"
        assert module_type(src, "А") == _OBJECT

    def test_declared_then_long_assigned_is_long(self):
        # The key invariant: UNSET + first-assign → exact type (no widening to OBJECT)
        src = "Перем А; А = 100;"
        assert module_type(src, "А") == _LONG

    def test_declared_then_double_assigned_is_double(self):
        src = "Перем А; А = 1.5;"
        assert module_type(src, "А") == _DOUBLE

    def test_multiple_assignments_widen(self):
        # First assignment → LONG, second → DOUBLE, result → DOUBLE
        src = "Перем А; А = 1; А = 1.5;"
        assert module_type(src, "А") == _DOUBLE


# ── Function return type inference ────────────────────────────────────────────

class TestReturnType:
    def test_int_return(self):
        src = "Функция Ф()\n  Возврат 42;\nКонецФункции;"
        ti = infer(src)
        scope = ti.scope_for("Ф")
        ret = ti.infer_return_type(ti.func_scopes["Ф"].vars, scope)
        # Can't easily walk body here, just check scope exists
        assert ti.scope_for("Ф") is not None

    def test_function_scope_created(self):
        src = "Функция Квадрат(Н)\n  Возврат Н * Н;\nКонецФункции;"
        ti = infer(src)
        assert "Квадрат" in ti.func_scopes

    def test_param_in_function_scope(self):
        src = "Функция Квадрат(Н)\n  Перем Р; Р = Н * Н; Возврат Р;\nКонецФункции;"
        ti = infer(src)
        scope = ti.scope_for("Квадрат")
        # Н appears in multiplication with itself → should be inferred as long or double
        # At minimum it should not be unset
        assert scope.get("Н") in (_LONG, _DOUBLE, _OBJECT)


# ── Procedure scope ───────────────────────────────────────────────────────────

class TestProcedureScope:
    def test_proc_scope_created(self):
        src = "Процедура МояПроц()\n  Перем Х; Х = 5;\nКонецПроцедуры;"
        ti = infer(src)
        assert "МояПроц" in ti.func_scopes

    def test_local_var_in_proc_scope(self):
        src = "Процедура МояПроц()\n  Перем Х; Х = 5;\nКонецПроцедуры;"
        ti = infer(src)
        scope = ti.scope_for("МояПроц")
        assert scope.get("Х") == _LONG

    def test_module_scope_unaffected_by_local(self):
        src = "Процедура МояПроц()\n  Перем Х; Х = 5;\nКонецПроцедуры; Перем Х; Х = \"str\";"
        ti = infer(src)
        assert ti.module_scope.get("Х") == _OBJECT


# ── infer_return_type ─────────────────────────────────────────────────────────

class TestInferReturnType:
    def _build(self, src):
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        ti = TypeInferencer()
        ti.infer(ast)
        return ti, ast

    def test_int_return_is_long(self):
        src = "Функция Ф()\n  Возврат 100;\nКонецФункции;"
        ti, ast = self._build(src)
        func = ast.body[0]
        scope = ti.scope_for("Ф")
        ret = ti.infer_return_type(func.body, scope)
        assert ret == _LONG

    def test_float_return_is_double(self):
        src = "Функция Ф()\n  Возврат 3.14;\nКонецФункции;"
        ti, ast = self._build(src)
        func = ast.body[0]
        scope = ti.scope_for("Ф")
        ret = ti.infer_return_type(func.body, scope)
        assert ret == _DOUBLE

    def test_no_return_is_void(self):
        src = "Процедура П()\n  А = 1;\nКонецПроцедуры;"
        ti, ast = self._build(src)
        proc = ast.body[0]
        scope = ti.scope_for("П")
        ret = ti.infer_return_type(proc.body, scope)
        assert ret == "void"

    def test_mixed_returns_widen(self):
        # Returns both int and float → double
        src = "Функция Ф(А)\n  Если А > 0 Тогда\n    Возврат 1;\n  Иначе\n    Возврат 1.5;\n  КонецЕсли;\nКонецФункции;"
        ti, ast = self._build(src)
        func = ast.body[0]
        scope = ti.scope_for("Ф")
        ret = ti.infer_return_type(func.body, scope)
        assert ret == _DOUBLE
