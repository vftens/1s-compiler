"""
1S: ERP Free Edition — Token definitions
Trilingual keyword table: Russian (1C-compatible) + Ukrainian + English
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Any


class TokenType(Enum):
    # ── Literals ────────────────────────────────────────────────────────────
    INTEGER     = auto()
    FLOAT       = auto()
    STRING      = auto()
    DATE        = auto()        # 'YYYYMMDD'  or  '20230101'

    # ── Identifiers / Names ─────────────────────────────────────────────────
    IDENTIFIER  = auto()

    # ── Control flow ────────────────────────────────────────────────────────
    IF          = auto()   # Если / Якщо / If
    THEN        = auto()   # Тогда / Тоді / Then
    ELSE        = auto()   # Иначе / Інакше / Else
    ELSIF       = auto()   # ИначеЕсли / ІнакшеЯкщо / ElseIf
    ENDIF       = auto()   # КонецЕсли / КінецьЯкщо / EndIf

    FOR         = auto()   # Для / Для / For
    EACH        = auto()   # Каждого / Кожного / Each
    IN          = auto()   # Из / З / In
    TO          = auto()   # По / До / To
    WHILE       = auto()   # Пока / Поки / While
    DO          = auto()   # Цикл / Цикл / Do
    ENDDO       = auto()   # КонецЦикла / КінецьЦиклу / EndDo
    BREAK       = auto()   # Прервать / Перервати / Break
    CONTINUE    = auto()   # Продолжить / Продовжити / Continue
    RETURN      = auto()   # Возврат / Повернути / Return

    # ── Subroutines ─────────────────────────────────────────────────────────
    PROCEDURE      = auto()  # Процедура / Процедура / Procedure
    ENDPROCEDURE   = auto()  # КонецПроцедуры / КінецьПроцедури / EndProcedure
    FUNCTION       = auto()  # Функция / Функція / Function
    ENDFUNCTION    = auto()  # КонецФункции / КінецьФункції / EndFunction
    EXPORT         = auto()  # Экспорт / Експорт / Export
    VAL            = auto()  # Знач / Знач / Val

    # ── Variable declaration ─────────────────────────────────────────────────
    VAR         = auto()   # Перем / Змін / Var

    # ── Error handling ──────────────────────────────────────────────────────
    TRY         = auto()   # Попытка / Спроба / Try
    EXCEPT      = auto()   # Исключение / Виняток / Except
    RAISE       = auto()   # ВызватьИсключение / ВикинутиВиняток / Raise
    ENDTRY      = auto()   # КонецПопытки / КінецьСпроби / EndTry

    # ── Boolean / special values ────────────────────────────────────────────
    TRUE        = auto()   # Истина / Істина / True
    FALSE       = auto()   # Ложь / Хибність / False
    UNDEFINED   = auto()   # Неопределено / Невизначено / Undefined
    NULL        = auto()   # Null

    # ── Logical operators ───────────────────────────────────────────────────
    AND         = auto()   # И / І / And
    OR          = auto()   # Или / Або / Or
    NOT         = auto()   # Не / Не / Not

    # ── Object construction ─────────────────────────────────────────────────
    NEW         = auto()   # Новый / Новий / New

    # ── Goto (legacy 1C compat) ─────────────────────────────────────────────
    GOTO        = auto()   # Перейти / Перейти / Goto
    LABEL       = auto()   # ~Метка / ~Мітка (label marker)

    # ── Preprocessor directives ─────────────────────────────────────────────
    PP_IF        = auto()  # #Если        / #If
    PP_THEN      = auto()  # #Тогда       / #Then
    PP_ELSE      = auto()  # #Иначе       / #Else
    PP_ELSIF     = auto()  # #ИначеЕсли   / #ElseIf
    PP_ENDIF     = auto()  # #КонецЕсли   / #EndIf
    PP_REGION    = auto()  # #Область     / #Region
    PP_ENDREGION = auto()  # #КонецОбласти / #EndRegion
    PP_USE       = auto()  # #Использовать / #Use  (module import)
    PP_INSERT    = auto()  # #Вставка     / #Insert
    PP_ENDINSERT = auto()  # #КонецВставки / #EndInsert
    PP_DELETE    = auto()  # #Удаление    / #Delete
    PP_ENDDELETE = auto()  # #КонецУдаления / #EndDelete

    # ── Arithmetic operators ────────────────────────────────────────────────
    PLUS        = auto()   # +
    MINUS       = auto()   # -
    MULTIPLY    = auto()   # *
    DIVIDE      = auto()   # /
    MODULO      = auto()   # %

    # ── Comparison / assignment ─────────────────────────────────────────────
    ASSIGN      = auto()   # =  (statement context)
    EQ          = auto()   # =  (expression context — same lexeme, parser decides)
    NEQ         = auto()   # <>
    LT          = auto()   # <
    GT          = auto()   # >
    LTE         = auto()   # <=
    GTE         = auto()   # >=

    # ── Delimiters ───────────────────────────────────────────────────────────
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    LBRACKET    = auto()   # [
    RBRACKET    = auto()   # ]
    LBRACE      = auto()   # {
    RBRACE      = auto()   # }
    COMMA       = auto()   # ,
    SEMICOLON   = auto()   # ;
    DOT         = auto()   # .
    QUESTION    = auto()   # ?  (ternary:  Условие ? ДаЗначение : НетЗначение)
    COLON       = auto()   # :

    # ── Query sublanguage ───────────────────────────────────────────────────
    QUERY_BEGIN = auto()   # opening  | of inline query block
    QUERY_TEXT  = auto()   # raw query text before parsing
    QUERY_END   = auto()   # closing  | of inline query block

    # ── Special ─────────────────────────────────────────────────────────────
    EOF         = auto()
    NEWLINE     = auto()
    COMMENT     = auto()   # // ...  (kept for IDE tools; skipped by parser)


# ── Trilingual keyword table ─────────────────────────────────────────────────
# Maps lowercase keyword string → TokenType
# Columns: Russian (1C-compatible) | Ukrainian | English

KEYWORDS: dict[str, TokenType] = {
    # ── Control flow ────────────────────────────────────────────────────────
    # If
    "если":               TokenType.IF,
    "якщо":               TokenType.IF,
    "if":                 TokenType.IF,
    # Then
    "тогда":              TokenType.THEN,
    "тоді":               TokenType.THEN,
    "then":               TokenType.THEN,
    # Else
    "иначе":              TokenType.ELSE,
    "інакше":             TokenType.ELSE,
    "else":               TokenType.ELSE,
    # ElseIf
    "иначеесли":          TokenType.ELSIF,
    "інакшеякщо":         TokenType.ELSIF,
    "elseif":             TokenType.ELSIF,
    "elsif":              TokenType.ELSIF,
    # EndIf
    "конецесли":          TokenType.ENDIF,
    "кінецьякщо":         TokenType.ENDIF,
    "endif":              TokenType.ENDIF,

    # For
    "для":                TokenType.FOR,   # same in Ru + Uk
    "for":                TokenType.FOR,
    # Each
    "каждого":            TokenType.EACH,
    "кожного":            TokenType.EACH,
    "each":               TokenType.EACH,
    # In (collection iterator / from)
    "из":                 TokenType.IN,
    "з":                  TokenType.IN,    # Ukrainian "з" (from/with)
    "in":                 TokenType.IN,
    # To (numeric range)
    "по":                 TokenType.TO,
    "до":                 TokenType.TO,    # Ukrainian "до" (to/until)
    "to":                 TokenType.TO,
    # While
    "пока":               TokenType.WHILE,
    "поки":               TokenType.WHILE,
    "while":              TokenType.WHILE,
    # Do (loop body opener)
    "цикл":               TokenType.DO,   # same in Ru + Uk
    "do":                 TokenType.DO,
    # EndDo
    "конеццикла":         TokenType.ENDDO,
    "кінецьциклу":        TokenType.ENDDO,
    "enddo":              TokenType.ENDDO,
    # Break
    "прервать":           TokenType.BREAK,
    "перервати":          TokenType.BREAK,
    "break":              TokenType.BREAK,
    # Continue
    "продолжить":         TokenType.CONTINUE,
    "продовжити":         TokenType.CONTINUE,
    "continue":           TokenType.CONTINUE,
    # Return
    "возврат":            TokenType.RETURN,
    "повернути":          TokenType.RETURN,
    "return":             TokenType.RETURN,

    # ── Subroutines ─────────────────────────────────────────────────────────
    # Procedure
    "процедура":          TokenType.PROCEDURE,   # same in Ru + Uk
    "procedure":          TokenType.PROCEDURE,
    # EndProcedure
    "конецпроцедуры":     TokenType.ENDPROCEDURE,
    "кінецьпроцедури":    TokenType.ENDPROCEDURE,
    "endprocedure":       TokenType.ENDPROCEDURE,
    # Function
    "функция":            TokenType.FUNCTION,
    "функція":            TokenType.FUNCTION,
    "function":           TokenType.FUNCTION,
    # EndFunction
    "конецфункции":       TokenType.ENDFUNCTION,
    "кінецьфункції":      TokenType.ENDFUNCTION,
    "endfunction":        TokenType.ENDFUNCTION,
    # Export
    "экспорт":            TokenType.EXPORT,
    "експорт":            TokenType.EXPORT,
    "export":             TokenType.EXPORT,
    # Val (pass by value)
    "знач":               TokenType.VAL,   # same in Ru + Uk
    "val":                TokenType.VAL,

    # ── Variable declaration ─────────────────────────────────────────────────
    "перем":              TokenType.VAR,
    "змін":               TokenType.VAR,   # Ukrainian: short for "змінна" (variable)
    "var":                TokenType.VAR,

    # ── Error handling ──────────────────────────────────────────────────────
    # Try
    "попытка":            TokenType.TRY,
    "спроба":             TokenType.TRY,
    "try":                TokenType.TRY,
    # Except
    "исключение":         TokenType.EXCEPT,
    "виняток":            TokenType.EXCEPT,
    "except":             TokenType.EXCEPT,
    # Raise
    "вызватьисключение":  TokenType.RAISE,
    "викинутивиняток":    TokenType.RAISE,
    "raise":              TokenType.RAISE,
    # EndTry
    "конецпопытки":       TokenType.ENDTRY,
    "кінецьспроби":       TokenType.ENDTRY,
    "endtry":             TokenType.ENDTRY,

    # ── Boolean / special values ────────────────────────────────────────────
    "истина":             TokenType.TRUE,
    "істина":             TokenType.TRUE,
    "true":               TokenType.TRUE,

    "ложь":               TokenType.FALSE,
    "хибність":           TokenType.FALSE,
    "хибно":              TokenType.FALSE,   # alternative Ukrainian form
    "false":              TokenType.FALSE,

    "неопределено":       TokenType.UNDEFINED,
    "невизначено":        TokenType.UNDEFINED,
    "undefined":          TokenType.UNDEFINED,

    "null":               TokenType.NULL,

    # ── Logical operators ───────────────────────────────────────────────────
    "и":                  TokenType.AND,
    "і":                  TokenType.AND,    # Ukrainian "і" (and)  [same letter, different Unicode]
    "та":                 TokenType.AND,    # Ukrainian alternative "та" (and)
    "and":                TokenType.AND,

    "или":                TokenType.OR,
    "або":                TokenType.OR,     # Ukrainian "або" (or)
    "or":                 TokenType.OR,

    "не":                 TokenType.NOT,    # same in Ru + Uk
    "not":                TokenType.NOT,

    # ── Object construction ─────────────────────────────────────────────────
    "новый":              TokenType.NEW,
    "новий":              TokenType.NEW,    # Ukrainian "новий" (new)
    "new":                TokenType.NEW,

    # ── Goto (legacy compat) ────────────────────────────────────────────────
    "перейти":            TokenType.GOTO,   # same in Ru + Uk
    "goto":               TokenType.GOTO,
}

# ── Preprocessor keyword table (prefixed with #) ────────────────────────────
PP_KEYWORDS: dict[str, TokenType] = {
    # #If
    "#если":              TokenType.PP_IF,
    "#якщо":              TokenType.PP_IF,
    "#if":                TokenType.PP_IF,
    # #Then
    "#тогда":             TokenType.PP_THEN,
    "#тоді":              TokenType.PP_THEN,
    "#then":              TokenType.PP_THEN,
    # #Else
    "#иначе":             TokenType.PP_ELSE,
    "#інакше":            TokenType.PP_ELSE,
    "#else":              TokenType.PP_ELSE,
    # #ElseIf
    "#иначеесли":         TokenType.PP_ELSIF,
    "#інакшеякщо":        TokenType.PP_ELSIF,
    "#elseif":            TokenType.PP_ELSIF,
    # #EndIf
    "#конецесли":         TokenType.PP_ENDIF,
    "#кінецьякщо":        TokenType.PP_ENDIF,
    "#endif":             TokenType.PP_ENDIF,
    # #Region
    "#область":           TokenType.PP_REGION,
    "#область":           TokenType.PP_REGION,   # same in Ru + Uk
    "#region":            TokenType.PP_REGION,
    # #EndRegion
    "#конецобласти":      TokenType.PP_ENDREGION,
    "#кінецьобласті":     TokenType.PP_ENDREGION,
    "#endregion":         TokenType.PP_ENDREGION,
    # #Use
    "#использовать":      TokenType.PP_USE,
    "#використати":       TokenType.PP_USE,
    "#use":               TokenType.PP_USE,
    # #Insert
    "#вставка":           TokenType.PP_INSERT,
    "#вставка":           TokenType.PP_INSERT,   # same in Ru + Uk
    "#insert":            TokenType.PP_INSERT,
    # #EndInsert
    "#конецвставки":      TokenType.PP_ENDINSERT,
    "#кінецьвставки":     TokenType.PP_ENDINSERT,
    "#endinsert":         TokenType.PP_ENDINSERT,
    # #Delete
    "#удаление":          TokenType.PP_DELETE,
    "#видалення":         TokenType.PP_DELETE,
    "#delete":            TokenType.PP_DELETE,
    # #EndDelete
    "#конецудаления":     TokenType.PP_ENDDELETE,
    "#кінецьвидалення":   TokenType.PP_ENDDELETE,
    "#enddelete":         TokenType.PP_ENDDELETE,
}

# ── Query sub-language keyword table (UPPERCASE SQL-like) ────────────────────
# Trilingual: Russian | Ukrainian | English  →  standard SQL token
QUERY_KEYWORDS: dict[str, str] = {
    # ── SELECT clause ────────────────────────────────────────────────────────
    "выбрать":            "SELECT",   # Ru
    "вибрати":            "SELECT",   # Uk
    "select":             "SELECT",

    "различные":          "DISTINCT", # Ru
    "різні":              "DISTINCT", # Uk
    "distinct":           "DISTINCT",

    "первые":             "TOP",      # Ru
    "перші":              "TOP",      # Uk
    "top":                "TOP",

    "разрешенные":        "ALLOWED",  # Ru  (1C-specific, no Uk equiv)
    "дозволені":          "ALLOWED",  # Uk
    "allowed":            "ALLOWED",

    # ── FROM ─────────────────────────────────────────────────────────────────
    "из":                 "FROM",     # Ru
    "з":                  "FROM",     # Uk  (short form — context: query body)
    "від":                "FROM",     # Uk  alternative
    "from":               "FROM",

    # ── JOINs ────────────────────────────────────────────────────────────────
    "соединение":         "JOIN",     # Ru
    "зєднання":           "JOIN",     # Uk  (з'єднання without apostrophe for lexer)
    "join":               "JOIN",

    "левое":              "LEFT",     # Ru
    "ліве":               "LEFT",     # Uk
    "left":               "LEFT",

    "правое":             "RIGHT",    # Ru
    "праве":              "RIGHT",    # Uk
    "right":              "RIGHT",

    "полное":             "FULL",     # Ru
    "повне":              "FULL",     # Uk
    "full":               "FULL",

    "внутреннее":         "INNER",    # Ru
    "внутрішнє":          "INNER",    # Uk
    "inner":              "INNER",

    "внешнее":            "OUTER",    # Ru
    "зовнішнє":           "OUTER",    # Uk
    "outer":              "OUTER",

    "перекрестное":       "CROSS",    # Ru
    "перехресне":         "CROSS",    # Uk
    "cross":              "CROSS",

    "по":                 "ON",       # Ru  (JOIN ... ПО)
    "за":                 "ON",       # Uk  (JOIN ... ЗА)
    "on":                 "ON",

    # ── WHERE / GROUP / ORDER / HAVING ──────────────────────────────────────
    "где":                "WHERE",    # Ru
    "де":                 "WHERE",    # Uk
    "where":              "WHERE",

    "сгруппироватьпо":    "GROUP BY", # Ru compound
    "згрупуватипо":       "GROUP BY", # Uk compound
    "groupby":            "GROUP BY",

    "упорядочитьпо":      "ORDER BY", # Ru compound
    "впорядкуватипо":     "ORDER BY", # Uk compound
    "orderby":            "ORDER BY",

    "имеющие":            "HAVING",   # Ru
    "маючи":              "HAVING",   # Uk
    "having":             "HAVING",

    "убыванию":           "DESC",     # Ru
    "спаданням":          "DESC",     # Uk
    "desc":               "DESC",

    "возрастанию":        "ASC",      # Ru
    "зростанням":         "ASC",      # Uk
    "asc":                "ASC",

    # ── UNION ────────────────────────────────────────────────────────────────
    "объединить":         "UNION",    # Ru
    "обєднати":           "UNION",    # Uk
    "union":              "UNION",

    "все":                "ALL",      # Ru
    "всі":                "ALL",      # Uk
    "all":                "ALL",

    # ── LOGICAL ──────────────────────────────────────────────────────────────
    "и":                  "AND",      # Ru
    "і":                  "AND",      # Uk
    "та":                 "AND",      # Uk alt
    "and":                "AND",

    "или":                "OR",       # Ru
    "або":                "OR",       # Uk
    "or":                 "OR",

    "не":                 "NOT",      # Ru + Uk same
    "not":                "NOT",

    "в":                  "IN",       # Ru
    "у":                  "IN",       # Uk
    "in":                 "IN",

    "между":              "BETWEEN",  # Ru
    "між":                "BETWEEN",  # Uk
    "between":            "BETWEEN",

    "подобно":            "LIKE",     # Ru
    "подібно":            "LIKE",     # Uk
    "like":               "LIKE",
    "есть":               "IS",
    # IS / REFS / NULL
    "есть":               "IS",       # Ru
    "є":                  "IS",       # Uk
    "is":                 "IS",
    "ссылка":             "REFS",     # Ru
    "посилання":          "REFS",     # Uk
    "refs":               "REFS",
    "null":               "NULL",

    # ── AGGREGATE functions ──────────────────────────────────────────────────
    "сумма":              "SUM",      # Ru
    "сума":               "SUM",      # Uk
    "sum":                "SUM",

    "количество":         "COUNT",    # Ru  (NOTE: PascalCase = column, lowercase = COUNT)
    "кількість":          "COUNT",    # Uk
    "count":              "COUNT",

    "максимум":           "MAX",      # Ru + Uk same
    "max":                "MAX",

    "минимум":            "MIN",      # Ru
    "мінімум":            "MIN",      # Uk
    "min":                "MIN",

    "среднее":            "AVG",      # Ru
    "середнє":            "AVG",      # Uk
    "avg":                "AVG",

    # ── CASE / WHEN ──────────────────────────────────────────────────────────
    "выбор":              "CASE",     # Ru
    "вибір":              "CASE",     # Uk
    "case":               "CASE",

    "когда":              "WHEN",     # Ru
    "коли":               "WHEN",     # Uk
    "when":               "WHEN",

    "тогда":              "THEN",     # Ru
    "тоді":               "THEN",     # Uk
    "then":               "THEN",

    "иначе":              "ELSE",     # Ru
    "інакше":             "ELSE",     # Uk
    "else":               "ELSE",

    "конец":              "END",      # Ru
    "кінець":             "END",      # Uk
    "end":                "END",

    # ── CAST / AS ────────────────────────────────────────────────────────────
    "выразить":           "CAST",     # Ru
    "виразити":           "CAST",     # Uk
    "cast":               "CAST",

    "как":                "AS",       # Ru
    "як":                 "AS",       # Uk
    "as":                 "AS",

    # ── 1S-specific query extensions ─────────────────────────────────────────
    "иерархии":           "HIERARCHY",   # Ru
    "ієрархії":           "HIERARCHY",   # Uk
    "hierarchy":          "HIERARCHY",

    "итогипо":            "TOTALS BY",   # Ru compound
    "підсумкипо":         "TOTALS BY",   # Uk compound
    "totalsby":           "TOTALS BY",

    "периодами":          "PERIODS",     # Ru
    "періодами":          "PERIODS",     # Uk
    "periods":            "PERIODS",

    "автоупорядочивание": "AUTOORDER",   # Ru
    "автовпорядкування":  "AUTOORDER",   # Uk
    "autoorder":          "AUTOORDER",

    "индексировать":      "INDEX BY",    # Ru
    "індексувати":        "INDEX BY",    # Uk
    "indexby":            "INDEX BY",
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"
