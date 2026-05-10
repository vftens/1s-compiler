"""
1S: ERP Free Edition — Query engine
Executes 1S query language against in-memory tables (via sqlite3).
Bilingual SQL is pre-translated by the transpiler; runtime receives clean SQL.
"""
from __future__ import annotations
import sqlite3
import re
from decimal import Decimal
from typing import Any
from .types import _ValueTable, _Undefined, Undefined
from ..lexer.tokens import QUERY_KEYWORDS


_PHRASE_MAP = [
    # ── Russian phrases ──────────────────────────────────────────────────────
    (re.compile(r"УПОРЯДОЧИТЬ\s+ПО",        re.IGNORECASE), "ORDER BY"),
    (re.compile(r"СГРУППИРОВАТЬ\s+ПО",      re.IGNORECASE), "GROUP BY"),
    (re.compile(r"ИТОГИ\s+ПО",              re.IGNORECASE), "TOTALS BY"),
    (re.compile(r"ИНДЕКСИРОВАТЬ\s+ПО",      re.IGNORECASE), "INDEX BY"),
    (re.compile(r"ЛЕВОЕ\s+СОЕДИНЕНИЕ",      re.IGNORECASE), "LEFT JOIN"),
    (re.compile(r"ПРАВОЕ\s+СОЕДИНЕНИЕ",     re.IGNORECASE), "RIGHT JOIN"),
    (re.compile(r"ПОЛНОЕ\s+СОЕДИНЕНИЕ",     re.IGNORECASE), "FULL JOIN"),
    (re.compile(r"ВНУТРЕННЕЕ\s+СОЕДИНЕНИЕ", re.IGNORECASE), "INNER JOIN"),
    (re.compile(r"ПЕРЕКРЕСТНОЕ\s+СОЕДИНЕНИЕ", re.IGNORECASE), "CROSS JOIN"),
    (re.compile(r"НЕ\s+В\b",               re.IGNORECASE), "NOT IN"),
    (re.compile(r"НЕ\s+МЕЖДУ",             re.IGNORECASE), "NOT BETWEEN"),
    (re.compile(r"НЕ\s+ПОДОБНО",           re.IGNORECASE), "NOT LIKE"),
    (re.compile(r"ЕСТЬ\s+NULL",            re.IGNORECASE), "IS NULL"),
    (re.compile(r"НЕ\s+ЕСТЬ\s+NULL",       re.IGNORECASE), "IS NOT NULL"),
    # ── Ukrainian phrases ────────────────────────────────────────────────────
    (re.compile(r"ВПОРЯДКУВАТИ\s+ПО",       re.IGNORECASE), "ORDER BY"),
    (re.compile(r"ЗГРУПУВАТИ\s+ПО",         re.IGNORECASE), "GROUP BY"),
    (re.compile(r"ПІДСУМКИ\s+ПО",           re.IGNORECASE), "TOTALS BY"),
    (re.compile(r"ІНДЕКСУВАТИ\s+ПО",        re.IGNORECASE), "INDEX BY"),
    (re.compile(r"ЛІВЕ\s+З[''ʼ]?ЄДНАННЯ",  re.IGNORECASE), "LEFT JOIN"),
    (re.compile(r"ПРАВЕ\s+З[''ʼ]?ЄДНАННЯ", re.IGNORECASE), "RIGHT JOIN"),
    (re.compile(r"ПОВНЕ\s+З[''ʼ]?ЄДНАННЯ", re.IGNORECASE), "FULL JOIN"),
    (re.compile(r"ВНУТРІШНЄ\s+З[''ʼ]?ЄДНАННЯ", re.IGNORECASE), "INNER JOIN"),
    (re.compile(r"ПЕРЕХРЕСНЕ\s+З[''ʼ]?ЄДНАННЯ", re.IGNORECASE), "CROSS JOIN"),
    (re.compile(r"НЕ\s+У\b",               re.IGNORECASE), "NOT IN"),
    (re.compile(r"НЕ\s+МІЖ",              re.IGNORECASE), "NOT BETWEEN"),
    (re.compile(r"НЕ\s+ПОДІБНО",           re.IGNORECASE), "NOT LIKE"),
    (re.compile(r"Є\s+NULL",               re.IGNORECASE), "IS NULL"),
    (re.compile(r"НЕ\s+Є\s+NULL",          re.IGNORECASE), "IS NOT NULL"),
]

_SINGLE_WORD_MAP = {
    # SELECT
    "выбрать": "SELECT",   "вибрати": "SELECT",   "select": "SELECT",
    # DISTINCT
    "различные": "DISTINCT", "різні": "DISTINCT",  "distinct": "DISTINCT",
    # TOP
    "первые": "TOP",       "перші": "TOP",         "top": "TOP",
    # (ALLOWED is 1S-only — drop silently)
    "разрешенные": "",     "дозволені": "",
    # FROM
    "из": "FROM",          "від": "FROM",          "from": "FROM",
    # JOIN
    "соединение": "JOIN",  "зєднання": "JOIN",     "join": "JOIN",
    # OUTER
    "внешнее": "OUTER",    "зовнішнє": "OUTER",    "outer": "OUTER",
    # BY (ORDER BY / GROUP BY residual)
    "по": "BY",            "за": "BY",
    # ON (JOIN condition)
    "на": "ON",
    # AS
    "как": "AS",           "як": "AS",             "as": "AS",
    # WHERE
    "где": "WHERE",        "де": "WHERE",          "where": "WHERE",
    # HAVING
    "имеющие": "HAVING",   "маючи": "HAVING",      "having": "HAVING",
    # Logical
    "и": "AND",   "і": "AND",   "та": "AND",        "and": "AND",
    "или": "OR",  "або": "OR",                       "or": "OR",
    "не": "NOT",                                     "not": "NOT",
    "в": "IN",    "у": "IN",                         "in": "IN",
    "между": "BETWEEN",  "між": "BETWEEN",           "between": "BETWEEN",
    "подобно": "LIKE",   "подібно": "LIKE",           "like": "LIKE",
    "есть": "IS",        "є": "IS",                   "is": "IS",
    "null": "NULL",
    "ссылка": "REFS",    "посилання": "REFS",
    # ORDER direction
    "убыванию": "DESC",    "спаданням": "DESC",    "desc": "DESC",
    "возрастанию": "ASC",  "зростанням": "ASC",    "asc": "ASC",
    # UNION
    "объединить": "UNION", "обєднати": "UNION",    "union": "UNION",
    "все": "ALL",          "всі": "ALL",            "all": "ALL",
    # Aggregates
    "сумма": "SUM",        "сума": "SUM",           "sum": "SUM",
    "количество": "COUNT", "кількість": "COUNT",    "count": "COUNT",
    "максимум": "MAX",                              "max": "MAX",
    "минимум": "MIN",      "мінімум": "MIN",        "min": "MIN",
    "среднее": "AVG",      "середнє": "AVG",        "avg": "AVG",
    # CASE/WHEN
    "выбор": "CASE",       "вибір": "CASE",         "case": "CASE",
    "когда": "WHEN",       "коли": "WHEN",          "when": "WHEN",
    "тогда": "THEN",       "тоді": "THEN",          "then": "THEN",
    "иначе": "ELSE",       "інакше": "ELSE",        "else": "ELSE",
    "конец": "END",        "кінець": "END",         "end": "END",
    # CAST
    "выразить": "CAST",    "виразити": "CAST",      "cast": "CAST",
    # Misc
    "автоупорядочивание": "/* AUTOORDER */",
    "автовпорядкування":  "/* AUTOORDER */",
}

# These are column/table identifiers that shouldn't be translated
_SQL_KEYWORDS_PROTECT = frozenset({"AND", "OR", "NOT", "IN", "BETWEEN",
                                    "LIKE", "IS", "NULL", "AS", "ON", "BY"})


def _translate_query(raw: str) -> str:
    """Translate bilingual 1S query text to SQLite-compatible SQL."""
    # Strip pipe-prefix lines (1C multiline   |   SELECT...)
    sql = re.sub(r"^\s*\|", "", raw, flags=re.MULTILINE)
    # Normalize parameter refs: &Param → :Param
    sql = re.sub(r"&(\w+)", r":\1", sql)

    # Phase 1: multi-word phrases (must happen before single-word)
    for pattern, replacement in _PHRASE_MAP:
        sql = pattern.sub(replacement, sql)

    # Phase 2: single-word keywords
    # Convention: only translate ALL-UPPERCASE or all-lowercase words.
    # PascalCase / camelCase words are treated as identifiers (column/table names).
    def replace_word(m: re.Match) -> str:
        word = m.group(0)
        # Skip PascalCase / camelCase — those are identifiers, not keywords
        if len(word) > 1 and word[0].isupper() and not word.isupper():
            return word
        mapped = _SINGLE_WORD_MAP.get(word.lower())
        if mapped is None:
            return word
        return mapped

    sql = re.sub(r"[А-Яа-яёЁA-Za-z_][А-Яа-яёЁA-Za-z0-9_]*", replace_word, sql)
    return sql.strip()


# ── Query result ─────────────────────────────────────────────────────────────

class QueryResult:
    """
    РезультатЗапроса / QueryResult
    Wraps an sqlite3 result into the 1C-style selection API.
    """
    def __init__(self, rows: list[tuple], columns: list[str]):
        self._rows = rows
        self._columns = columns
        self._pos = -1

    def Count(self) -> int:
        return len(self._rows)

    def IsEmpty(self) -> bool:
        return len(self._rows) == 0

    def Select(self) -> "_QuerySelection":
        return _QuerySelection(self._rows, self._columns)

    def Unload(self) -> _ValueTable:
        """Export to ValueTable."""
        vt = _ValueTable()
        for col in self._columns:
            vt.Columns.Add(col)
        for row in self._rows:
            vt_row = vt.Add()
            for i, col in enumerate(self._columns):
                vt_row[col] = row[i]
        return vt

    # Russian aliases
    Количество  = Count
    Пустой      = IsEmpty
    Выбрать     = Select
    Выгрузить   = Unload


class _QuerySelection:
    """РезультатЗапроса.Выбрать() — forward-only cursor."""
    def __init__(self, rows, columns):
        self._rows = rows
        self._columns = columns
        self._pos = -1
        self._current: tuple | None = None

    def Next(self) -> bool:
        self._pos += 1
        if self._pos < len(self._rows):
            self._current = self._rows[self._pos]
            return True
        return False

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if self._current is None:
            return Undefined
        try:
            idx = self._columns.index(name)
            return self._current[idx]
        except ValueError:
            return Undefined

    # Russian alias
    Следующий = Next


# ── Query object ─────────────────────────────────────────────────────────────

class _Query:
    """
    Запрос / Query — the 1S query object.
    Usage:
        q = Query("SELECT * FROM Goods WHERE Price > :min_price")
        q.SetParam("min_price", 100)
        result = q.Execute()
    """

    def __init__(self, text: str = ""):
        self._text = text
        self._params: dict[str, Any] = {}
        self._tables: dict[str, list[dict]] = {}  # virtual tables

    def SetParam(self, name: str, value: Any):
        if isinstance(value, _ValueTable):
            self.RegisterTable(name, value)
        else:
            self._params[name] = value

    def RegisterTable(self, name: str, data: _ValueTable | list[dict]):
        """Register an in-memory table that can be queried by name."""
        if isinstance(data, _ValueTable):
            rows = [dict(zip(data.Columns._cols, [row[c] for c in data.Columns._cols]))
                    for row in data]
            self._tables[name] = rows
        else:
            self._tables[name] = data

    def Execute(self) -> QueryResult:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        # Create temp tables for any registered virtual tables
        for table_name, rows in self._tables.items():
            if not rows:
                continue
            cols = list(rows[0].keys())
            # Detect column types from first row
            def _sqlite_type(val) -> str:
                if isinstance(val, bool):   return "INTEGER"
                if isinstance(val, int):    return "INTEGER"
                if isinstance(val, float):  return "REAL"
                if isinstance(val, Decimal): return "REAL"
                return "TEXT"
            col_defs = ", ".join(
                f'"{c}" {_sqlite_type(rows[0].get(c))}' for c in cols
            )
            conn.execute(f'CREATE TEMP TABLE "{table_name}" ({col_defs})')
            for row in rows:
                placeholders = ", ".join("?" * len(cols))
                def _coerce(v):
                    if isinstance(v, Decimal): return float(v)
                    if v is None or isinstance(v, _Undefined): return None
                    return v
                values = [_coerce(row.get(c)) for c in cols]
                conn.execute(f'INSERT INTO "{table_name}" VALUES ({placeholders})', values)
        conn.commit()

        # Translate bilingual query text → SQLite SQL
        sql = _translate_query(self._text)
        # Map named params :ParamName → sqlite3 :ParamName style (already in that form)
        params_converted = {
            k: str(v) if isinstance(v, Decimal) else v
            for k, v in self._params.items()
        }

        try:
            cursor = conn.execute(sql, params_converted)
            columns = [desc[0] for desc in cursor.description or []]
            rows_out = cursor.fetchall()
            result = QueryResult(
                rows=[tuple(r) for r in rows_out],
                columns=columns,
            )
        except sqlite3.Error as e:
            raise RuntimeError(f"1S Query error: {e}\nSQL: {sql}") from e
        finally:
            conn.close()

        return result

    @property
    def Text(self) -> str: return self._text
    @Text.setter
    def Text(self, v: str): self._text = v

    # Russian aliases
    УстановитьПараметр  = SetParam
    ЗарегистрироватьТаблицу = RegisterTable
    Выполнить           = Execute
    Текст               = property(lambda s: s._text, lambda s, v: setattr(s, "_text", v))

Запрос = _Query
Query  = _Query
