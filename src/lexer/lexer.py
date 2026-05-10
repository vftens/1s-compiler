"""
1S: ERP Free Edition — Lexer
Handles bilingual (Russian / English) source files, UTF-8.
"""
from __future__ import annotations
import re
from typing import Iterator
from .tokens import Token, TokenType, KEYWORDS, PP_KEYWORDS


class LexerError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"[Lexer] {msg} at {line}:{col}")
        self.line = line
        self.col = col


class Lexer:
    def __init__(self, source: str, filename: str = "<unknown>"):
        self.source = source.lstrip("﻿")  # strip UTF-8 BOM if present
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.col = 1
        self._tokens: list[Token] = []

    # ── Public API ──────────────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        tokens = list(self._scan())
        tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return tokens

    # ── Internal scanner ────────────────────────────────────────────────────

    def _scan(self) -> Iterator[Token]:
        while self.pos < len(self.source):
            ch = self._peek()

            # Skip whitespace (not newlines — newlines are significant for
            # statement boundaries in some 1C dialects, but we treat ; as
            # the primary separator and skip newlines too)
            if ch in " \t\r":
                self._advance()
                continue

            if ch == "\n":
                self._advance()
                continue

            # Comment: //
            if ch == "/" and self._peek(1) == "/":
                yield self._read_comment()
                continue

            # Preprocessor directive  #...
            if ch == "#":
                tok = self._read_preprocessor()
                if tok:
                    yield tok
                continue

            # String literal  "..."  or  '...'  (1C uses double-quotes)
            if ch in ('"', "'"):
                yield self._read_string(ch)
                continue

            # Date literal  '19991231'  (single-quoted 8-digit date)
            # Handled inside _read_string — detected by content

            # Number
            if ch.isdigit():
                yield self._read_number()
                continue

            # Identifier / keyword (Latin or Cyrillic)
            if ch.isalpha() or ch == "_":
                yield self._read_word()
                continue

            # Operators and punctuation
            tok = self._read_operator()
            if tok:
                yield tok
                continue

            raise LexerError(f"Unexpected character {ch!r}", self.line, self.col)

    # ── Character helpers ────────────────────────────────────────────────────

    def _peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else "\0"

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _current_pos(self) -> tuple[int, int]:
        return self.line, self.col

    # ── Token readers ────────────────────────────────────────────────────────

    def _read_comment(self) -> Token:
        line, col = self._current_pos()
        buf = []
        while self.pos < len(self.source) and self._peek() != "\n":
            buf.append(self._advance())
        return Token(TokenType.COMMENT, "".join(buf), line, col)

    def _read_preprocessor(self) -> Token | None:
        line, col = self._current_pos()
        buf = [self._advance()]  # consume '#'
        while self.pos < len(self.source) and (self._peek().isalpha() or self._peek() in "_"):
            buf.append(self._advance())
        text = "".join(buf).lower()
        from .tokens import PP_KEYWORDS
        ttype = PP_KEYWORDS.get(text)
        if ttype is None:
            # Unknown preprocessor directive — skip rest of line
            while self.pos < len(self.source) and self._peek() != "\n":
                self._advance()
            return None
        # For #Region / #Use collect the argument
        arg = ""
        if ttype in (TokenType.PP_REGION, TokenType.PP_USE):
            while self.pos < len(self.source) and self._peek() not in ("\n", "\r"):
                arg += self._advance()
            arg = arg.strip()
        return Token(ttype, arg or None, line, col)

    def _read_string(self, quote: str) -> Token:
        line, col = self._current_pos()
        self._advance()  # opening quote
        buf = []
        while self.pos < len(self.source):
            ch = self._peek()
            if ch == quote:
                self._advance()
                # 1C: doubled quote = escape  "" → "
                if self._peek() == quote:
                    buf.append(self._advance())
                else:
                    break
            elif ch == "\n":
                # Multi-line strings: 1C uses | as line continuation prefix
                self._advance()
                # skip leading whitespace then expect |
                while self._peek() in (" ", "\t"):
                    self._advance()
                if self._peek() == "|":
                    self._advance()
                    buf.append("\n")
                else:
                    raise LexerError("Unterminated string literal", line, col)
            else:
                buf.append(self._advance())
        value = "".join(buf)
        # Detect 1C date literal: 8 digits exactly
        if re.fullmatch(r"\d{8}", value):
            return Token(TokenType.DATE, value, line, col)
        return Token(TokenType.STRING, value, line, col)

    def _read_number(self) -> Token:
        line, col = self._current_pos()
        buf = []
        while self._peek().isdigit():
            buf.append(self._advance())
        if self._peek() == "." and self._peek(1).isdigit():
            buf.append(self._advance())  # '.'
            while self._peek().isdigit():
                buf.append(self._advance())
            return Token(TokenType.FLOAT, float("".join(buf)), line, col)
        return Token(TokenType.INTEGER, int("".join(buf)), line, col)

    def _read_word(self) -> Token:
        line, col = self._current_pos()
        buf = []
        while self.pos < len(self.source) and (self._peek().isalnum() or self._peek() == "_"):
            buf.append(self._advance())
        word = "".join(buf)
        lower = word.lower()
        ttype = KEYWORDS.get(lower, TokenType.IDENTIFIER)
        return Token(ttype, word, line, col)

    def _read_operator(self) -> Token | None:
        line, col = self._current_pos()
        ch = self._advance()

        single = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.MULTIPLY,
            "/": TokenType.DIVIDE,
            "%": TokenType.MODULO,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
            ".": TokenType.DOT,
            "?": TokenType.QUESTION,
            ":": TokenType.COLON,
            "~": TokenType.LABEL,
        }

        if ch == "<":
            if self._peek() == ">":
                self._advance()
                return Token(TokenType.NEQ, "<>", line, col)
            if self._peek() == "=":
                self._advance()
                return Token(TokenType.LTE, "<=", line, col)
            return Token(TokenType.LT, "<", line, col)

        if ch == ">":
            if self._peek() == "=":
                self._advance()
                return Token(TokenType.GTE, ">=", line, col)
            return Token(TokenType.GT, ">", line, col)

        if ch == "=":
            return Token(TokenType.EQ, "=", line, col)

        if ch in single:
            return Token(single[ch], ch, line, col)

        raise LexerError(f"Unknown operator character {ch!r}", line, col)
