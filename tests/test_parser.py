"""
Tests for the 1S Parser.
"""
import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser, ParseError
from src.parser.ast_nodes import (
    Module, VarDecl, AssignStmt, CallStmt, ReturnStmt,
    IfStmt, WhileStmt, ForStmt, ForEachStmt, TryStmt,
    FunctionDef, ProcedureDef, Param,
    Literal, Identifier, BinOp, UnaryOp, CallExpr, MemberExpr, IndexExpr,
    BreakStmt, ContinueStmt, RaiseStmt,
)


def parse(src: str) -> Module:
    tokens = Lexer(src).tokenize()
    return Parser(tokens).parse()


def first(src: str):
    return parse(src).body[0]


# ── Variable declarations ─────────────────────────────────────────────────────

class TestVarDecl:
    def test_single_var(self):
        node = first("Перем А;")
        assert isinstance(node, VarDecl)
        assert node.names == ["А"]

    def test_multiple_vars(self):
        node = first("Перем А, Б, В;")
        assert isinstance(node, VarDecl)
        assert node.names == ["А", "Б", "В"]

    def test_var_english(self):
        node = first("Var X;")
        assert isinstance(node, VarDecl)
        assert "X" in node.names


# ── Assignments ───────────────────────────────────────────────────────────────

class TestAssignment:
    def test_integer_assign(self):
        node = first("А = 5;")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.target, Identifier)
        assert node.target.name == "А"
        assert isinstance(node.value, Literal)
        assert node.value.value == 5

    def test_string_assign(self):
        node = first('Имя = "Иван";')
        assert isinstance(node, AssignStmt)
        assert node.value.value == "Иван"

    def test_float_assign(self):
        node = first("Х = 3.14;")
        assert isinstance(node.value, Literal)
        assert abs(node.value.value - 3.14) < 1e-9

    def test_chained_member_assign(self):
        node = first("Таблица.Поле = 1;")
        assert isinstance(node, AssignStmt)
        assert isinstance(node.target, MemberExpr)


# ── Arithmetic expressions ────────────────────────────────────────────────────

class TestExpressions:
    def test_addition(self):
        node = first("А = 1 + 2;")
        binop = node.value
        assert isinstance(binop, BinOp)
        assert binop.op == "+"
        assert binop.left.value == 1
        assert binop.right.value == 2

    def test_subtraction(self):
        node = first("А = 10 - 3;")
        assert node.value.op == "-"

    def test_multiplication(self):
        node = first("А = 4 * 5;")
        assert node.value.op == "*"

    def test_division(self):
        node = first("А = 10 / 2;")
        assert node.value.op == "/"

    def test_unary_minus(self):
        node = first("А = -5;")
        assert isinstance(node.value, UnaryOp)
        assert node.value.op == "-"

    def test_comparison_eq(self):
        node = first("А = (Б = В);")
        assert isinstance(node.value, BinOp)
        assert node.value.op == "=="

    def test_comparison_neq(self):
        node = first("А = (Б <> В);")
        assert node.value.op == "!="

    def test_operator_precedence_mul_before_add(self):
        node = first("А = 2 + 3 * 4;")
        # Should be: 2 + (3 * 4), i.e. top-level op is +
        assert node.value.op == "+"
        assert node.value.right.op == "*"

    def test_parentheses_override_precedence(self):
        node = first("А = (2 + 3) * 4;")
        assert node.value.op == "*"


# ── Call statements ───────────────────────────────────────────────────────────

class TestCallStmt:
    def test_procedure_call_no_args(self):
        node = first("МояПроцедура();")
        assert isinstance(node, CallStmt)
        assert isinstance(node.call, CallExpr)

    def test_procedure_call_with_args(self):
        node = first('Сообщить("text");')
        assert isinstance(node, CallStmt)
        assert len(node.call.args) == 1

    def test_method_call(self):
        node = first("Объект.Метод(1, 2);")
        assert isinstance(node, CallStmt)


# ── If / ElseIf / Else ────────────────────────────────────────────────────────

class TestIf:
    def test_simple_if(self):
        src = "Если А > 0 Тогда\n  Б = 1;\nКонецЕсли;"
        node = first(src)
        assert isinstance(node, IfStmt)
        assert len(node.branches) == 1
        assert node.else_body == []

    def test_if_else(self):
        src = "Если А > 0 Тогда\n  Б = 1;\nИначе\n  Б = 0;\nКонецЕсли;"
        node = first(src)
        assert isinstance(node, IfStmt)
        assert len(node.else_body) == 1

    def test_if_elseif_else(self):
        src = ("Если А > 0 Тогда\n  Б = 1;\n"
               "ИначеЕсли А < 0 Тогда\n  Б = -1;\n"
               "Иначе\n  Б = 0;\nКонецЕсли;")
        node = first(src)
        assert len(node.branches) == 2

    def test_ukrainian_keywords(self):
        src = "Якщо А > 0 Тоді\n  Б = 1;\nКінецьЯкщо;"
        node = first(src)
        assert isinstance(node, IfStmt)


# ── Loops ─────────────────────────────────────────────────────────────────────

class TestLoops:
    def test_while_loop(self):
        src = "Пока А > 0 Цикл\n  А = А - 1;\nКонецЦикла;"
        node = first(src)
        assert isinstance(node, WhileStmt)

    def test_for_numeric(self):
        src = "Для А = 1 По 10 Цикл\n  Б = А;\nКонецЦикла;"
        node = first(src)
        assert isinstance(node, ForStmt)
        assert node.var == "А"
        assert node.start.value == 1
        assert node.end.value == 10

    def test_for_each(self):
        src = "Для Каждого Э Из Список Цикл\n  А = Э;\nКонецЦикла;"
        node = first(src)
        assert isinstance(node, ForEachStmt)
        assert node.var == "Э"

    def test_break_in_loop(self):
        src = "Пока Истина Цикл\n  Прервать;\nКонецЦикла;"
        while_node = first(src)
        assert any(isinstance(s, BreakStmt) for s in while_node.body)

    def test_continue_in_loop(self):
        src = "Пока Истина Цикл\n  Продолжить;\nКонецЦикла;"
        while_node = first(src)
        assert any(isinstance(s, ContinueStmt) for s in while_node.body)


# ── Functions and Procedures ──────────────────────────────────────────────────

class TestFunctions:
    def test_procedure_def(self):
        src = "Процедура МояПроц()\n  А = 1;\nКонецПроцедуры;"
        node = first(src)
        assert isinstance(node, ProcedureDef)
        assert node.name == "МояПроц"
        assert node.params == []

    def test_function_def_with_return(self):
        src = "Функция Квадрат(Н)\n  Возврат Н * Н;\nКонецФункции;"
        node = first(src)
        assert isinstance(node, FunctionDef)
        assert node.name == "Квадрат"
        assert len(node.params) == 1
        assert node.params[0].name == "Н"

    def test_function_with_multiple_params(self):
        src = "Функция Сумма(А, Б)\n  Возврат А + Б;\nКонецФункции;"
        node = first(src)
        assert len(node.params) == 2

    def test_function_param_by_value(self):
        src = "Процедура Тест(Знач А)\n  А = 1;\nКонецПроцедуры;"
        node = first(src)
        assert node.params[0].by_value is True

    def test_function_param_default(self):
        src = "Процедура Тест(А = 0)\n  Б = А;\nКонецПроцедуры;"
        node = first(src)
        assert node.params[0].default is not None

    def test_return_stmt(self):
        src = "Функция Ф()\n  Возврат 42;\nКонецФункции;"
        func = first(src)
        ret = func.body[0]
        assert isinstance(ret, ReturnStmt)
        assert ret.value.value == 42

    def test_return_no_value(self):
        src = "Процедура П()\n  Возврат;\nКонецПроцедуры;"
        proc = first(src)
        ret = proc.body[0]
        assert isinstance(ret, ReturnStmt)
        assert ret.value is None


# ── Try / Except ──────────────────────────────────────────────────────────────

class TestTryCatch:
    def test_basic_try(self):
        src = "Попытка\n  А = 1;\nИсключение\n  А = 0;\nКонецПопытки;"
        node = first(src)
        assert isinstance(node, TryStmt)
        assert len(node.body) >= 1
        assert len(node.except_body) >= 1

    def test_raise_in_try(self):
        src = "Попытка\n  ВызватьИсключение \"err\";\nИсключение\nКонецПопытки;"
        node = first(src)
        raise_stmt = node.body[0]
        assert isinstance(raise_stmt, RaiseStmt)


# ── Member access and indexing ────────────────────────────────────────────────

class TestMemberAccess:
    def test_member_expr(self):
        node = first("А = Объект.Свойство;")
        assert isinstance(node.value, MemberExpr)
        assert node.value.member == "Свойство"

    def test_nested_member(self):
        node = first("А = А.Б.В;")
        outer = node.value
        assert isinstance(outer, MemberExpr)
        assert outer.member == "В"

    def test_index_expr(self):
        node = first("А = Массив[0];")
        assert isinstance(node.value, IndexExpr)

    def test_call_on_member(self):
        node = first("А.Метод();")
        assert isinstance(node, CallStmt)


# ── Boolean literals ──────────────────────────────────────────────────────────

class TestBoolLiterals:
    def test_true(self):
        node = first("А = Истина;")
        assert node.value.kind == "bool"
        assert node.value.value is True

    def test_false(self):
        node = first("А = Ложь;")
        assert node.value.value is False

    def test_undefined(self):
        node = first("А = Неопределено;")
        assert node.value.kind == "undefined"


# ── Multiple statements ───────────────────────────────────────────────────────

class TestMultipleStatements:
    def test_two_statements(self):
        mod = parse("А = 1; Б = 2;")
        assert len(mod.body) == 2

    def test_nested_function_call_in_assign(self):
        node = first("А = Функция1(Функция2(Х));")
        assert isinstance(node.value, CallExpr)
        assert isinstance(node.value.args[0], CallExpr)
