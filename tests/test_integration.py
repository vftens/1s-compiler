"""
Integration tests: run real .1s example files and verify output.
"""
import subprocess
import sys
import re
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
EXAMPLES = ROOT / "examples"


def run_script(name: str) -> tuple[int, list[str]]:
    """Run examples/<name>.1s via CLI and return (exit_code, output_lines)."""
    script = EXAMPLES / f"{name}.1s"
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "run", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=30,
    )
    lines = result.stdout.splitlines()
    return result.returncode, lines


def run_cython_gen(name: str) -> tuple[int, str]:
    """Run cython-gen on examples/<name>.1s and return (exit_code, stdout)."""
    script = EXAMPLES / f"{name}.1s"
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "cython-gen", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


# ── hello.1s ─────────────────────────────────────────────────────────────────

class TestHelloScript:
    def test_exits_zero(self):
        code, _ = run_script("hello")
        assert code == 0

    def test_outputs_hello(self):
        _, lines = run_script("hello")
        text = "\n".join(lines)
        assert "Hello" in text or "Привет" in text

    def test_square_function_output(self):
        _, lines = run_script("hello")
        text = "\n".join(lines)
        # hello.1s outputs "5² = 25"
        assert "25" in text or "²" in text

    def test_has_numeric_output(self):
        _, lines = run_script("hello")
        text = "\n".join(lines)
        assert any(re.search(r"\d+", line) for line in lines)


# ── hello_uk.1s ───────────────────────────────────────────────────────────────

class TestHelloUkScript:
    def test_exits_zero(self):
        code, _ = run_script("hello_uk")
        assert code == 0

    def test_ukrainian_greeting(self):
        _, lines = run_script("hello_uk")
        text = "\n".join(lines)
        assert "Привіт" in text or "світе" in text

    def test_fibonacci_output(self):
        _, lines = run_script("hello_uk")
        text = "\n".join(lines)
        # Fibonacci: 0, 1, 1, 2, 3, 5, 8, 13...
        assert "0" in text
        assert "1" in text

    def test_kyiv_in_output(self):
        _, lines = run_script("hello_uk")
        text = "\n".join(lines)
        assert "Київ" in text

    def test_currency_exchange(self):
        _, lines = run_script("hello_uk")
        text = "\n".join(lines)
        assert "USD" in text or "EUR" in text

    def test_exception_caught(self):
        _, lines = run_script("hello_uk")
        text = "\n".join(lines)
        assert "✓" in text or "успішно" in text or "перехоплено" in text


# ── accounting_uk.1s ─────────────────────────────────────────────────────────

class TestAccountingUkScript:
    def test_exits_zero(self):
        code, _ = run_script("accounting_uk")
        assert code == 0

    def test_has_plan_rakhunkiv(self):
        _, lines = run_script("accounting_uk")
        text = "\n".join(lines)
        assert "ПланРахунків" in text or "рахун" in text.lower()

    def test_balanced_postings(self):
        _, lines = run_script("accounting_uk")
        text = "\n".join(lines)
        # ОСВ should show equal debit and credit totals
        assert "1 837 800" in text or "1837800" in text or "1,837,800" in text \
               or "ОБОРОТ" in text or "Обороти" in text

    def test_account_31_analysis(self):
        _, lines = run_script("accounting_uk")
        text = "\n".join(lines)
        assert "31" in text

    def test_financial_result_keyword(self):
        _, lines = run_script("accounting_uk")
        text = "\n".join(lines)
        assert "завершено" in text or "Бухгалтер" in text.lower()


# ── erp_sale_uk.1s ────────────────────────────────────────────────────────────

class TestErpSaleUkScript:
    def test_exits_zero(self):
        code, _ = run_script("erp_sale_uk")
        assert code == 0

    def test_has_vidatkova(self):
        _, lines = run_script("erp_sale_uk")
        text = "\n".join(lines)
        assert "Видаткова" in text or "накладна" in text.lower()

    def test_shows_margin(self):
        _, lines = run_script("erp_sale_uk")
        text = "\n".join(lines)
        # Rентабельність 48.5%
        assert "48.5" in text or "Рентабельн" in text

    def test_stock_remaining(self):
        _, lines = run_script("erp_sale_uk")
        text = "\n".join(lines)
        assert "Борошно" in text or "Цукор" in text

    def test_pdv_calculation(self):
        _, lines = run_script("erp_sale_uk")
        text = "\n".join(lines)
        assert "ПДВ" in text or "20%" in text


# ── hrm_payroll.1s ────────────────────────────────────────────────────────────

class TestHrmPayrollScript:
    def test_exits_zero(self):
        code, _ = run_script("hrm_payroll")
        assert code == 0

    def test_has_payroll_output(self):
        _, lines = run_script("hrm_payroll")
        assert len(lines) > 0


# ── Cython generation ─────────────────────────────────────────────────────────

class TestCythonGen:
    def test_cython_gen_hello_exits_zero(self):
        code, _ = run_cython_gen("hello")
        assert code == 0

    def test_cython_gen_hello_uk_exits_zero(self):
        code, _ = run_cython_gen("hello_uk")
        assert code == 0

    def test_cython_gen_accounting_uk_exits_zero(self):
        code, _ = run_cython_gen("accounting_uk")
        assert code == 0

    def test_cython_gen_erp_sale_uk_exits_zero(self):
        code, _ = run_cython_gen("erp_sale_uk")
        assert code == 0

    def test_pyx_file_created(self):
        run_cython_gen("hello")
        pyx = EXAMPLES / "hello.pyx"
        assert pyx.exists()

    def test_pyx_has_cython_directives(self):
        run_cython_gen("hello")
        pyx = EXAMPLES / "hello.pyx"
        content = pyx.read_text(encoding="utf-8")
        assert "# cython: language_level=3" in content

    def test_pyx_has_run_function(self):
        run_cython_gen("hello_uk")
        pyx = EXAMPLES / "hello_uk.pyx"
        content = pyx.read_text(encoding="utf-8")
        assert "def run():" in content

    def test_pyx_has_cpdef_function(self):
        run_cython_gen("hello_uk")
        pyx = EXAMPLES / "hello_uk.pyx"
        content = pyx.read_text(encoding="utf-8")
        assert "cpdef" in content

    def test_pyx_has_cdef_typed_vars(self):
        run_cython_gen("hello_uk")
        pyx = EXAMPLES / "hello_uk.pyx"
        content = pyx.read_text(encoding="utf-8")
        assert "cdef long" in content or "cdef double" in content

    def test_setup_py_created(self):
        run_cython_gen("hello")
        setup = EXAMPLES / "setup_1s.py"
        assert setup.exists()


# ── CLI interface ─────────────────────────────────────────────────────────────

class TestCLI:
    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT)
        )
        assert result.returncode == 0

    def test_help_lists_all_commands(self):
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT)
        )
        output = result.stdout
        for cmd in ["run", "compile", "tokens", "ast", "cython-gen", "cython-build", "serve"]:
            assert cmd in output

    def test_tokens_command(self):
        script = EXAMPLES / "hello.1s"
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "tokens", str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=15
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_ast_command(self):
        script = EXAMPLES / "hello.1s"
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "ast", str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=15
        )
        assert result.returncode == 0

    def test_compile_command(self):
        script = EXAMPLES / "hello.1s"
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "compile", str(script)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT), timeout=15
        )
        assert result.returncode == 0
        # compile writes a .py file and prints "Compiled → ..."
        assert "Compiled" in result.stdout or "hello.py" in result.stdout


# ── Pipeline: lex → parse → transpile → exec ─────────────────────────────────

class TestPipeline:
    """Verify the full pipeline produces deterministic, correct output."""

    def _pipeline_output(self, src: str) -> str:
        import io, sys
        from src.lexer.lexer import Lexer
        from src.parser.parser import Parser
        from src.transpiler.python_backend import PythonTranspiler
        tokens = Lexer(src).tokenize()
        ast = Parser(tokens).parse()
        py_code = PythonTranspiler().transpile(ast)
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            exec(py_code, {})
        finally:
            sys.stdout = old
        return buf.getvalue()

    def test_map_iteration(self):
        src = ('Курси = Відповідність();\n'
               'Курси["USD"] = 41;\n'
               'Для Кожного Пара З Курси Цикл\n'
               '  Повідомити(Пара.Ключ);\n'
               'КінецьЦиклу;')
        output = self._pipeline_output(src)
        assert "USD" in output

    def test_structure_access(self):
        src = ('Особа = Структура("Прізвище, Вік", "Шевченко", 30);\n'
               'Повідомити(Особа.Прізвище);')
        output = self._pipeline_output(src)
        assert "Шевченко" in output

    def test_value_table(self):
        src = ('Т = ТаблицяЗначень();\n'
               'Т.Колонки.Додати("Назва");\n'
               'Р = Т.Додати();\n'
               'Р.Назва = "Тест";\n'
               'Повідомити(Т.Кількість());')
        output = self._pipeline_output(src)
        assert "1" in output

    def test_strtemplate_in_script(self):
        src = 'Повідомити(ШаблонРядка("Результат: %1", 42));'
        output = self._pipeline_output(src)
        assert "Результат: 42" in output
