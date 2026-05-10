"""
Tests for the 1S Lexer.
"""
import pytest
from src.lexer.lexer import Lexer, LexerError
from src.lexer.tokens import TokenType


def tokenize(src: str):
    """Helper: return list of (type, value) tuples, dropping EOF."""
    toks = Lexer(src).tokenize()
    return [(t.type, t.value) for t in toks if t.type != TokenType.EOF]


def tok_types(src: str):
    return [t for t, _ in tokenize(src)]


# ── Whitespace and comments ──────────────────────────────────────────────────

class TestWhitespace:
    def test_empty(self):
        assert tokenize("") == []

    def test_spaces_only(self):
        assert tokenize("   \t\r\n  ") == []

    def test_comment_ignored(self):
        assert tokenize("// hello world") == [(TokenType.COMMENT, "// hello world")]

    def test_comment_does_not_consume_next_line(self):
        toks = tokenize("// comment\n42")
        values = [v for _, v in toks if v is not None]
        assert 42 in values


# ── Integer literals ─────────────────────────────────────────────────────────

class TestIntegers:
    def test_single_digit(self):
        assert tokenize("5") == [(TokenType.INTEGER, 5)]

    def test_multi_digit(self):
        assert tokenize("12345") == [(TokenType.INTEGER, 12345)]

    def test_zero(self):
        assert tokenize("0") == [(TokenType.INTEGER, 0)]

    def test_integer_type(self):
        toks = Lexer("42").tokenize()
        assert toks[0].type == TokenType.INTEGER
        assert isinstance(toks[0].value, int)


# ── Float literals ───────────────────────────────────────────────────────────

class TestFloats:
    def test_basic_float(self):
        assert tokenize("3.14") == [(TokenType.FLOAT, 3.14)]

    def test_float_type(self):
        toks = Lexer("2.5").tokenize()
        assert toks[0].type == TokenType.FLOAT
        assert isinstance(toks[0].value, float)

    def test_no_leading_digit_float(self):
        # "3." is not a float — the dot after integer has no following digit
        toks = tokenize("3.")
        assert toks[0] == (TokenType.INTEGER, 3)


# ── String literals ──────────────────────────────────────────────────────────

class TestStrings:
    def test_double_quoted(self):
        assert tokenize('"hello"') == [(TokenType.STRING, "hello")]

    def test_single_quoted(self):
        assert tokenize("'hello'") == [(TokenType.STRING, "hello")]

    def test_empty_string(self):
        assert tokenize('""') == [(TokenType.STRING, "")]

    def test_escaped_double_quote(self):
        # 1C: "" inside string = literal "
        assert tokenize('"say ""hi"""') == [(TokenType.STRING, 'say "hi"')]

    def test_multiline_pipe_continuation(self):
        src = '"line1\n|line2"'
        assert tokenize(src) == [(TokenType.STRING, "line1\nline2")]

    def test_unterminated_string_at_eof_produces_token(self):
        # Lexer exits gracefully at EOF — no error, just returns partial string
        toks = Lexer('"unterminated').tokenize()
        assert toks[0].type == TokenType.STRING
        assert toks[0].value == "unterminated"

    def test_unterminated_string_with_newline_raises(self):
        # A newline inside a string without | continuation IS a lex error
        with pytest.raises(LexerError):
            Lexer('"line1\nline2"').tokenize()


# ── Date literals ─────────────────────────────────────────────────────────────

class TestDateLiterals:
    def test_8_digit_string_is_date(self):
        assert tokenize("'20250101'") == [(TokenType.DATE, "20250101")]

    def test_7_digit_not_date(self):
        assert tokenize("'1234567'") == [(TokenType.STRING, "1234567")]

    def test_9_digit_not_date(self):
        assert tokenize("'123456789'") == [(TokenType.STRING, "123456789")]

    def test_10_digit_not_date(self):
        # ЄДРПОУ codes are 10 digits — must not be parsed as dates
        assert tokenize("'1234567890'") == [(TokenType.STRING, "1234567890")]

    def test_8_alpha_not_date(self):
        assert tokenize('"abcdefgh"') == [(TokenType.STRING, "abcdefgh")]


# ── Identifiers and keywords ─────────────────────────────────────────────────

class TestIdentifiers:
    def test_latin_identifier(self):
        assert tokenize("myVar") == [(TokenType.IDENTIFIER, "myVar")]

    def test_underscore_prefix(self):
        assert tokenize("_private") == [(TokenType.IDENTIFIER, "_private")]

    def test_alphanumeric(self):
        assert tokenize("var1") == [(TokenType.IDENTIFIER, "var1")]

    def test_cyrillic_identifier(self):
        assert tokenize("Переменная") == [(TokenType.IDENTIFIER, "Переменная")]

    def test_ukrainian_identifier(self):
        assert tokenize("Змінна") == [(TokenType.IDENTIFIER, "Змінна")]

    def test_keyword_if(self):
        toks = tok_types("Если")
        assert TokenType.IF in toks

    def test_keyword_procedure(self):
        toks = tok_types("Процедура")
        assert TokenType.PROCEDURE in toks

    def test_keyword_function(self):
        toks = tok_types("Функция")
        assert TokenType.FUNCTION in toks

    def test_keyword_case_insensitive(self):
        # Keywords are matched case-insensitively
        assert tok_types("если") == tok_types("ЕСЛИ")


# ── Operators ────────────────────────────────────────────────────────────────

class TestOperators:
    def test_plus(self):
        assert tokenize("+") == [(TokenType.PLUS, "+")]

    def test_minus(self):
        assert tokenize("-") == [(TokenType.MINUS, "-")]

    def test_multiply(self):
        assert tokenize("*") == [(TokenType.MULTIPLY, "*")]

    def test_divide(self):
        assert tokenize("/") == [(TokenType.DIVIDE, "/")]

    def test_modulo(self):
        assert tokenize("%") == [(TokenType.MODULO, "%")]

    def test_eq(self):
        assert tokenize("=") == [(TokenType.EQ, "=")]

    def test_neq(self):
        assert tokenize("<>") == [(TokenType.NEQ, "<>")]

    def test_lt(self):
        assert tokenize("<") == [(TokenType.LT, "<")]

    def test_lte(self):
        assert tokenize("<=") == [(TokenType.LTE, "<=")]

    def test_gt(self):
        assert tokenize(">") == [(TokenType.GT, ">")]

    def test_gte(self):
        assert tokenize(">=") == [(TokenType.GTE, ">=")]

    def test_parens(self):
        assert tok_types("()") == [TokenType.LPAREN, TokenType.RPAREN]

    def test_brackets(self):
        assert tok_types("[]") == [TokenType.LBRACKET, TokenType.RBRACKET]

    def test_comma(self):
        assert tokenize(",") == [(TokenType.COMMA, ",")]

    def test_semicolon(self):
        assert tokenize(";") == [(TokenType.SEMICOLON, ";")]

    def test_dot(self):
        assert tokenize(".") == [(TokenType.DOT, ".")]

    def test_unknown_char_raises(self):
        with pytest.raises(LexerError):
            Lexer("@").tokenize()


# ── BOM stripping ─────────────────────────────────────────────────────────────

class TestBOM:
    def test_bom_stripped(self):
        bom = "﻿"
        assert tokenize(f"{bom}42") == [(TokenType.INTEGER, 42)]


# ── Line tracking ────────────────────────────────────────────────────────────

class TestLineTracking:
    def test_first_token_line_1(self):
        toks = Lexer("42").tokenize()
        assert toks[0].line == 1

    def test_second_line_after_newline(self):
        toks = Lexer("// comment\n42").tokenize()
        int_tok = next(t for t in toks if t.type == TokenType.INTEGER)
        assert int_tok.line == 2


# ── Full expression tokenization ─────────────────────────────────────────────

class TestExpressionTokenization:
    def test_simple_assignment(self):
        types = tok_types("А = 5;")
        assert types == [TokenType.IDENTIFIER, TokenType.EQ,
                         TokenType.INTEGER, TokenType.SEMICOLON]

    def test_function_call(self):
        types = tok_types("Сообщить(\"text\");")
        assert types[0] == TokenType.IDENTIFIER
        assert TokenType.LPAREN in types
        assert TokenType.STRING in types
        assert TokenType.RPAREN in types
