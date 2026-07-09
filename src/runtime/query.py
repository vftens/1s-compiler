"""
1S: ERP Free Edition — Query engine
Executes 1S query language against in-memory tables (via sqlite3).
Bilingual SQL is pre-translated by the transpiler; runtime receives clean SQL.
"""
from __future__ import annotations
import os
import sqlite3
import re
from decimal import Decimal
from pathlib import Path
from typing import Any
from .types import _ValueTable, _Undefined, Undefined
from ..lexer.tokens import QUERY_KEYWORDS

# Project root — two levels up from this file (src/runtime/ → project root)
_RUNTIME_ROOT = Path(__file__).resolve().parent.parent.parent
_ALLOWED_DB_DIR = _RUNTIME_ROOT / "data"


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

    def Choose(self) -> "_QuerySelection":
        """Alias for Select() — mirrors 1C's Выбрать() / Вибрати() naming."""
        return self.Select()

    # Russian aliases
    Количество  = Count
    Пустой      = IsEmpty
    Выбрать     = Select
    Выгрузить   = Unload

    # Ukrainian aliases
    Кількість   = Count
    Порожній    = IsEmpty
    Вибрати     = Select
    Вивантажити = Unload


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

    def Value(self, name: str) -> Any:
        if self._current is None:
            return Undefined
        try:
            idx = self._columns.index(name)
            return self._current[idx]
        except ValueError:
            return Undefined

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        return self.Value(name)

    # Russian aliases
    Следующий = Next
    Значение  = Value

    # Ukrainian aliases
    Наступний = Next
    Значення  = Value


# ── Query object ─────────────────────────────────────────────────────────────

class _Query:
    """
    Запрос / Запит / Query — the 1S query object.
    Usage:
        q = Query("SELECT * FROM org_nodes WHERE org_name = :name")
        q.AttachDB("erp.db")          # optional: query persisted ERP tables
        q.SetParam("name", "MyHolding")
        result = q.Execute()
    """

    def __init__(self, text: str = ""):
        self._text = text
        self._params: dict[str, Any] = {}
        self._tables: dict[str, list[dict]] = {}
        self._db_path: str | None = None

    def AttachDB(self, db_path: str) -> "_Query":
        """
        Attach a SQLite DB file so the query can read its tables.
        Path is resolved relative to the project data/ directory.
        Pass just "erp.db" or the full "data/erp.db" — both work.
        Set env var 1S_ALLOW_ANY_DB_PATH=1 to bypass the data/ restriction
        (CLI mode / CI use only).
        """
        resolved = _resolve_db_path(db_path)
        self._db_path = resolved
        return self

    def SetParam(self, name: str, value: Any) -> "_Query":
        if isinstance(value, _ValueTable):
            self.RegisterTable(name, value)
        else:
            self._params[name] = value
        return self

    def RegisterTable(self, name: str, data: "_ValueTable | list[dict]") -> "_Query":
        """Register an in-memory ValueTable that can be joined with attached DB tables."""
        if isinstance(data, _ValueTable):
            rows = [dict(zip(data.Columns._cols, [row[c] for c in data.Columns._cols]))
                    for row in data]
            self._tables[name] = rows
        else:
            self._tables[name] = list(data)
        return self

    def Execute(self) -> "QueryResult":
        if self._db_path:
            return self._execute_with_db()
        return self._execute_memory()

    def _execute_memory(self) -> "QueryResult":
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        self._load_virtual_tables(conn)
        return self._run_query(conn)

    def _execute_with_db(self) -> "QueryResult":
        db_path = self._db_path
        if not os.path.exists(db_path):
            import warnings
            warnings.warn(f"AttachDB: database not found at '{db_path}' — returning empty result", stacklevel=3)
            return QueryResult(rows=[], columns=[])
        try:
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._load_virtual_tables(conn)
            return self._run_query(conn)
        except sqlite3.DatabaseError as exc:
            raise RuntimeError(f"AttachDB: database at '{db_path}' is corrupt or unreadable: {exc}") from exc

    def _load_virtual_tables(self, conn: sqlite3.Connection) -> None:
        for table_name, rows in self._tables.items():
            if not rows:
                continue
            cols = list(rows[0].keys())
            col_defs = ", ".join(f'"{c}" {_sqlite_type_for_col(rows, c)}' for c in cols)
            conn.execute(f'CREATE TEMP TABLE IF NOT EXISTS "{table_name}" ({col_defs})')
            for row in rows:
                placeholders = ", ".join("?" * len(cols))
                values = [_coerce_value(row.get(c)) for c in cols]
                conn.execute(f'INSERT INTO "{table_name}" VALUES ({placeholders})', values)
        conn.commit()

    def _run_query(self, conn: sqlite3.Connection) -> "QueryResult":
        sql = _translate_query(self._text)
        params_converted = {
            k: str(v) if isinstance(v, Decimal) else v
            for k, v in self._params.items()
        }
        try:
            cursor = conn.execute(sql, params_converted)
            columns = [desc[0] for desc in cursor.description or []]
            rows_out = cursor.fetchall()
            return QueryResult(rows=[tuple(r) for r in rows_out], columns=columns)
        except sqlite3.Error as e:
            raise RuntimeError(f"1S Query error: {e}\nSQL: {sql}") from e
        finally:
            conn.close()

    @property
    def Text(self) -> str: return self._text
    @Text.setter
    def Text(self, v: str): self._text = v

    # Russian aliases
    УстановитьПараметр      = SetParam
    ЗарегистрироватьТаблицу = RegisterTable
    Выполнить               = Execute
    ПрисоединитьБД          = AttachDB
    ПрисоединитьБазу        = AttachDB
    Текст = property(lambda s: s._text, lambda s, v: setattr(s, "_text", v))

    # Ukrainian aliases
    УстановитиПараметр      = SetParam
    ЗареєструватиТаблицю    = RegisterTable
    Виконати                = Execute
    ПриєднатиБД             = AttachDB
    ПриєднатиБазу           = AttachDB


def _resolve_db_path(db_path: str) -> str:
    """
    Resolve a user-supplied DB path.
    - "erp.db" → <project>/data/erp.db
    - "data/erp.db" → <project>/data/erp.db
    - absolute path → allowed only if 1S_ALLOW_ANY_DB_PATH=1
    Raises ValueError for path traversal attempts.
    """
    p = Path(db_path)
    if not p.is_absolute():
        # Strip leading "data/" if the caller included it
        parts = p.parts
        if parts and parts[0] == "data":
            p = Path(*parts[1:]) if len(parts) > 1 else Path(parts[0])
        resolved = (_ALLOWED_DB_DIR / p).resolve()
    else:
        resolved = p.resolve()

    allow_any = os.environ.get("1S_ALLOW_ANY_DB_PATH", "").strip() == "1"
    if not allow_any:
        allowed = _ALLOWED_DB_DIR.resolve()
        if not str(resolved).startswith(str(allowed)):
            raise ValueError(
                f"AttachDB path '{db_path}' is outside the allowed directory.\n"
                f"  Allowed: {allowed}\n"
                f"  Received: {resolved}\n"
                f"  Set 1S_ALLOW_ANY_DB_PATH=1 to override (CLI/CI mode only)."
            )
    return str(resolved)


def _sqlite_type_for_col(rows: list[dict], col: str) -> str:
    """Scan all rows for first non-None value to determine SQLite type."""
    for row in rows:
        val = row.get(col)
        if val is None or isinstance(val, _Undefined):
            continue
        if isinstance(val, bool):    return "INTEGER"
        if isinstance(val, int):     return "INTEGER"
        if isinstance(val, float):   return "REAL"
        if isinstance(val, Decimal): return "REAL"
        return "TEXT"
    return "NUMERIC"  # fallback — SQLite coerces correctly


def _coerce_value(v: Any) -> Any:
    if isinstance(v, Decimal): return float(v)
    if v is None or isinstance(v, _Undefined): return None
    return v


Запрос = _Query
Запит  = _Query
Query  = _Query
