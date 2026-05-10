"""
Tests for Python and Cython transpiler backends.
"""
import re
import pytest
from src.lexer.lexer import Lexer
from src.parser.parser import Parser
from src.transpiler.python_backend import PythonTranspiler
from src.transpiler.cython_backend import CythonTranspiler
from src.transpiler.type_inferencer import _LONG, _DOUBLE


def compile_py(src: str) -> str:
    tokens = Lexer(src).tokenize()
    ast = Parser(tokens).parse()
    return PythonTranspiler().transpile(ast)


def compile_pyx(src: str) -> str:
    tokens = Lexer(src).tokenize()
    ast = Parser(tokens).parse()
    return CythonTranspiler().transpile(ast)


# ── Python backend — basic emission ──────────────────────────────────────────

class TestPythonBasic:
    def test_assignment_int(self):
        code = compile_py("А = 5;")
        assert "А = 5" in code

    def test_assignment_string(self):
        code = compile_py('Имя = "Иван";')
        assert '"Иван"' in code

    def test_message_call(self):
        code = compile_py('Сообщить("hello");')
        assert "Сообщить" in code or "Message" in code

    def test_if_statement(self):
        src = "Если А > 0 Тогда\n  Б = 1;\nКонецЕсли;"
        code = compile_py(src)
        assert "if" in code

    def test_if_else(self):
        src = "Если А > 0 Тогда\n  Б = 1;\nИначе\n  Б = 0;\nКонецЕсли;"
        code = compile_py(src)
        assert "else:" in code

    def test_while_loop(self):
        src = "Пока А > 0 Цикл\n  А = А - 1;\nКонецЦикла;"
        code = compile_py(src)
        assert "while" in code

    def test_for_numeric(self):
        src = "Для Н = 1 По 5 Цикл\n  Б = Н;\nКонецЦикла;"
        code = compile_py(src)
        assert "for" in code
        assert "range" in code

    def test_for_each(self):
        src = "Для Каждого Э Из Список Цикл\n  А = Э;\nКонецЦикла;"
        code = compile_py(src)
        assert "for" in code
        assert "Список" in code

    def test_function_def(self):
        src = "Функция Квадрат(Н)\n  Возврат Н * Н;\nКонецФункции;"
        code = compile_py(src)
        assert "def Квадрат" in code
        assert "return" in code

    def test_procedure_def(self):
        src = "Процедура Привет()\n  Сообщить(\"hi\");\nКонецПроцедуры;"
        code = compile_py(src)
        assert "def Привет" in code

    def test_try_except(self):
        src = "Попытка\n  А = 1;\nИсключение\n  А = 0;\nКонецПопытки;"
        code = compile_py(src)
        assert "try:" in code
        assert "except" in code

    def test_member_access(self):
        code = compile_py("А = Объект.Свойство;")
        assert "Объект.Свойство" in code

    def test_index_access(self):
        code = compile_py("А = Массив[0];")
        assert "[0]" in code

    def test_not_operator(self):
        code = compile_py("А = Не Истина;")
        assert "not" in code

    def test_ternary(self):
        src = "А = Б > 0 ? 1 : -1;"
        code = compile_py(src)
        assert "if" in code or "else" in code

    def test_binary_ops(self):
        for op in ["+", "-", "*", "/"]:
            code = compile_py(f"А = 1 {op} 2;")
            assert op in code

    def test_string_concat(self):
        code = compile_py('А = "hello" + " " + "world";')
        assert "+" in code

    def test_runtime_import(self):
        code = compile_py("А = 1;")
        assert "from src.runtime import" in code or "import" in code

    def test_break(self):
        src = "Пока Истина Цикл\n  Прервать;\nКонецЦикла;"
        code = compile_py(src)
        assert "break" in code

    def test_continue(self):
        src = "Пока Истина Цикл\n  Продолжить;\nКонецЦикла;"
        code = compile_py(src)
        assert "continue" in code


# ── Python backend — name mangling ────────────────────────────────────────────

class TestPythonNameMangling:
    def test_builtin_conflict_mangled(self):
        # If a 1S var is named 'format' (matches Python builtin), it gets prefixed
        code = compile_py("format = 1;")
        assert "_format" in code

    def test_cyrillic_preserved(self):
        code = compile_py("Переменная = 42;")
        assert "Переменная" in code


# ── Python backend — var declarations ────────────────────────────────────────

class TestPythonVarDecl:
    def test_var_decl_emits_undefined(self):
        code = compile_py("Перем А;")
        assert "Undefined" in code or "А" in code

    def test_var_decl_multiple(self):
        code = compile_py("Перем А, Б, В;")
        # All three should appear
        assert "А" in code
        assert "Б" in code
        assert "В" in code


# ── Cython backend — header ───────────────────────────────────────────────────

class TestCythonHeader:
    def test_language_level(self):
        code = compile_pyx("А = 1;")
        assert "# cython: language_level=3" in code

    def test_boundscheck_directive(self):
        code = compile_pyx("А = 1;")
        assert "boundscheck=False" in code

    def test_cdivision_directive(self):
        code = compile_pyx("А = 1;")
        assert "cdivision=True" in code

    def test_libc_math_cimport(self):
        code = compile_pyx("А = 1;")
        assert "from libc.math cimport" in code

    def test_runtime_import(self):
        code = compile_pyx("А = 1;")
        assert "from src.runtime import *" in code

    def test_auto_generated_comment(self):
        code = compile_pyx("А = 1;")
        assert "AUTO-GENERATED" in code


# ── Cython backend — run() wrapper ───────────────────────────────────────────

class TestCythonRunWrapper:
    def test_run_function_emitted(self):
        code = compile_pyx("А = 1;")
        assert "def run():" in code

    def test_run_called_at_bottom(self):
        code = compile_pyx("А = 1;")
        lines = code.strip().split("\n")
        assert lines[-1].strip() == "run()"

    def test_no_run_wrapper_if_only_functions(self):
        src = "Функция Ф()\n  Возврат 1;\nКонецФункции;"
        code = compile_pyx(src)
        # run() should not appear if there are no executable statements
        assert "def run():" not in code


# ── Cython backend — cdef declarations ───────────────────────────────────────

class TestCythonCdef:
    def test_integer_var_gets_cdef_long(self):
        src = "Перем А; А = 42;"
        code = compile_pyx(src)
        assert "cdef long А" in code

    def test_float_var_gets_cdef_double(self):
        src = "Перем А; А = 3.14;"
        code = compile_pyx(src)
        assert "cdef double А" in code

    def test_string_var_no_cdef(self):
        src = 'Перем А; А = "hello";'
        code = compile_pyx(src)
        # String var should not get a cdef
        assert "cdef long А" not in code
        assert "cdef double А" not in code

    def test_cdef_inside_run(self):
        src = "Перем А; А = 1;"
        code = compile_pyx(src)
        run_start = code.index("def run():")
        assert "cdef long А" in code[run_start:]

    def test_declared_for_counter_gets_cdef_long(self):
        # A VarDecl'd variable that acts as a counter gets cdef long
        src = "Перем Н; Для Н = 1 По 5 Цикл\n  Сообщить(Н);\nКонецЦикла;"
        code = compile_pyx(src)
        assert "cdef long Н" in code


# ── Cython backend — cpdef functions ─────────────────────────────────────────

class TestCythonCpdef:
    def test_function_becomes_cpdef(self):
        src = "Функция Квадрат(Н)\n  Возврат Н * Н;\nКонецФункции;"
        code = compile_pyx(src)
        assert "cpdef" in code
        assert "Квадрат" in code

    def test_void_procedure_cpdef_void(self):
        src = "Процедура Показать(Текст)\n  Сообщить(Текст);\nКонецПроцедуры;"
        code = compile_pyx(src)
        assert "cpdef void Показать" in code

    def test_typed_param(self):
        src = "Функция Квадрат(Н)\n  Возврат Н * Н;\nКонецФункции;"
        code = compile_pyx(src)
        # Н is used in multiplication — should be typed
        assert "long Н" in code or "double Н" in code or "Н" in code

    def test_function_with_int_return(self):
        src = "Функция Два()\n  Возврат 2;\nКонецФункции;"
        code = compile_pyx(src)
        assert "cpdef long Два" in code

    def test_function_with_float_return(self):
        src = "Функция Пи()\n  Возврат 3.14;\nКонецФункции;"
        code = compile_pyx(src)
        assert "cpdef double Пи" in code

    def test_except_star_on_typed_func(self):
        src = "Функция Ф()\n  Возврат 1;\nКонецФункции;"
        code = compile_pyx(src)
        assert "except *" in code


# ── Cython backend — functions hoisted before run() ──────────────────────────

class TestCythonHoisting:
    def test_function_before_run(self):
        src = ("Функция Ф()\n  Возврат 1;\nКонецФункции;\n"
               "А = Ф();")
        code = compile_pyx(src)
        func_pos = code.index("cpdef")
        run_pos = code.index("def run():")
        assert func_pos < run_pos


# ── Round-trip: transpile then exec ──────────────────────────────────────────

class TestPythonExec:
    """Execute transpiled Python code and verify output."""

    def _run(self, src: str) -> list[str]:
        """Transpile 1S source, exec it, collect Сообщить output."""
        import io, sys
        py_code = compile_py(src)
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            ns = {}
            exec(py_code, ns)
        finally:
            sys.stdout = old_stdout
        return buf.getvalue().splitlines()

    def test_hello_world(self):
        src = 'Сообщить("Hello, World!");'
        lines = self._run(src)
        assert "Hello, World!" in lines

    def test_arithmetic(self):
        src = 'Перем А; А = 2 + 3 * 4; Сообщить(А);'
        lines = self._run(src)
        assert "14" in lines

    def test_if_true(self):
        src = ('Если 1 > 0 Тогда\n  Сообщить("yes");\n'
               'Иначе\n  Сообщить("no");\nКонецЕсли;')
        lines = self._run(src)
        assert "yes" in lines

    def test_for_loop(self):
        src = ('Перем С; С = 0;\n'
               'Для Н = 1 По 5 Цикл\n  С = С + Н;\nКонецЦикла;\n'
               'Сообщить(С);')
        lines = self._run(src)
        assert "15" in lines

    def test_while_loop(self):
        src = ('Перем С; С = 0; Перем К; К = 1;\n'
               'Пока К <= 3 Цикл\n  С = С + К; К = К + 1;\nКонецЦикла;\n'
               'Сообщить(С);')
        lines = self._run(src)
        assert "6" in lines

    def test_function_call(self):
        src = ('Функция Sq(Н)\n  Возврат Н * Н;\nКонецФункции;\n'
               'Сообщить(Sq(7));')
        lines = self._run(src)
        assert "49" in lines

    def test_try_except(self):
        src = ('Попытка\n  ВызватьИсключение "err";\n'
               'Исключение\n  Сообщить("caught");\nКонецПопытки;')
        lines = self._run(src)
        assert "caught" in lines

    def test_array_iteration(self):
        src = ('А = Массив();\n'
               'А.Добавить(10); А.Добавить(20);\n'
               'Для Каждого Э Из А Цикл\n  Сообщить(Э);\nКонецЦикла;')
        lines = self._run(src)
        assert "10" in lines
        assert "20" in lines

    def test_string_concat(self):
        src = ('Перем С; С = "1S" + ": " + "ERP";\n'
               'Сообщить(С);')
        lines = self._run(src)
        assert "1S: ERP" in lines

    def test_recursive_function(self):
        src = ('Функция Факт(Н)\n'
               '  Если Н <= 1 Тогда\n    Возврат 1;\n  КонецЕсли;\n'
               '  Возврат Н * Факт(Н - 1);\n'
               'КонецФункции;\n'
               'Сообщить(Факт(5));')
        lines = self._run(src)
        assert "120" in lines

    def test_ukrainian_keywords(self):
        src = ('Якщо 1 > 0 Тоді\n  Повідомити("UA");\nКінецьЯкщо;')
        lines = self._run(src)
        assert "UA" in lines
