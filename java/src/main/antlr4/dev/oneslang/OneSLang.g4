/**
 * 1S: ERP Free Edition — ANTLR4 Grammar
 * Trilingual: Russian / Ukrainian / English keywords.
 *
 * Conventions used in this file:
 *   - Lexer rules that are keywords use fragment helpers per language.
 *   - All keyword rules are case-insensitive for Latin letters.
 *   - Cyrillic keywords match their canonical capitalised form (e.g. "Якщо")
 *     AND their lowercase equivalent.
 *   - Identifiers may contain any Unicode letter or digit, allowing Cyrillic
 *     names in code (column names, variable names, procedure names).
 */
grammar OneSLang;

// ════════════════════════════════════════════════════════════════════════════
// PARSER RULES
// ════════════════════════════════════════════════════════════════════════════

// ── Top-level ────────────────────────────────────────────────────────────────

module
    : topLevel* EOF
    ;

topLevel
    : varDecl
    | procedureDef
    | functionDef
    | ppRegion
    | ppIfBlock
    | statement
    ;

// ── Preprocessor ─────────────────────────────────────────────────────────────

ppRegion
    : PP_REGION ppStatement* PP_ENDREGION
    ;

ppIfBlock
    : PP_IF ppExprText PP_THEN ppStatement*
      (PP_ELSIF ppExprText PP_THEN ppStatement*)*
      (PP_ELSE ppStatement*)?
      PP_ENDIF
    ;

ppExprText : ~(PP_THEN | PP_ENDIF | PP_ELSE | PP_ELSIF | EOF)+ ;

ppStatement : topLevel ;

// ── Variable declaration ──────────────────────────────────────────────────────

varDecl
    : VAR IDENTIFIER (COMMA IDENTIFIER)* EXPORT? SEMI?
    ;

// ── Subroutines ───────────────────────────────────────────────────────────────

procedureDef
    : PROCEDURE IDENTIFIER paramList EXPORT? SEMI?
      statement*
      ENDPROCEDURE
    ;

functionDef
    : FUNCTION IDENTIFIER paramList EXPORT? SEMI?
      statement*
      ENDFUNCTION
    ;

paramList
    : LPAREN (param (COMMA param)*)? RPAREN
    ;

param
    : VAL? IDENTIFIER (EQ expression)?
    ;

// ── Statements ────────────────────────────────────────────────────────────────

statement
    : varDecl
    | assignStmt    SEMI?
    | callStmt      SEMI?
    | returnStmt    SEMI?
    | breakStmt     SEMI?
    | continueStmt  SEMI?
    | raiseStmt     SEMI?
    | gotoStmt      SEMI?
    | labelStmt
    | ifStmt
    | whileStmt
    | forStmt
    | forEachStmt
    | tryStmt
    | ppRegion
    | ppIfBlock
    | SEMI
    ;

assignStmt
    : lvalue EQ expression
    ;

callStmt
    : callExpr
    ;

returnStmt
    : RETURN expression?
    ;

breakStmt
    : BREAK
    ;

continueStmt
    : CONTINUE
    ;

raiseStmt
    : RAISE expression?
    ;

gotoStmt
    : GOTO IDENTIFIER
    ;

labelStmt
    : TILDE IDENTIFIER COLON?
    ;

// ── If ────────────────────────────────────────────────────────────────────────

ifStmt
    : IF expression THEN SEMI?
      statement*
      (ELSIF expression THEN SEMI? statement*)*
      (ELSE SEMI? statement*)?
      ENDIF
    ;

// ── Loops ─────────────────────────────────────────────────────────────────────

whileStmt
    : WHILE expression DO SEMI?
      statement*
      ENDDO
    ;

forStmt
    : FOR IDENTIFIER EQ expression TO expression DO SEMI?
      statement*
      ENDDO
    ;

forEachStmt
    : FOR EACH IDENTIFIER IN expression DO SEMI?
      statement*
      ENDDO
    ;

// ── Try / Except ──────────────────────────────────────────────────────────────

tryStmt
    : TRY SEMI?
      statement*
      EXCEPT SEMI?
      statement*
      ENDTRY
    ;

// ── Expressions ───────────────────────────────────────────────────────────────

expression
    : ternaryExpr
    ;

ternaryExpr
    : orExpr (QUESTION orExpr COLON orExpr)?
    ;

orExpr
    : andExpr (OR andExpr)*
    ;

andExpr
    : notExpr (AND notExpr)*
    ;

notExpr
    : NOT notExpr
    | comparisonExpr
    ;

comparisonExpr
    : addExpr ((EQ | NEQ | LT | GT | LTE | GTE) addExpr)*
    ;

addExpr
    : mulExpr ((PLUS | MINUS) mulExpr)*
    ;

mulExpr
    : unaryExpr ((MULTIPLY | DIVIDE | MODULO) unaryExpr)*
    ;

unaryExpr
    : MINUS unaryExpr
    | PLUS  unaryExpr
    | postfixExpr
    ;

postfixExpr
    : primaryExpr postfixOp*
    ;

postfixOp
    : DOT IDENTIFIER (argList)?   // member access or method call
    | LBRACKET expression RBRACKET  // index
    | argList                       // direct call (primaryExpr must be Identifier)
    ;

primaryExpr
    : INTEGER_LIT
    | FLOAT_LIT
    | STRING_LIT
    | DATE_LIT
    | TRUE
    | FALSE
    | NULL_KW
    | UNDEFINED
    | newExpr
    | IDENTIFIER
    | LPAREN expression RPAREN
    ;

newExpr
    : NEW IDENTIFIER argList?
    ;

callExpr
    : postfixExpr
    ;

lvalue
    : IDENTIFIER (DOT IDENTIFIER | LBRACKET expression RBRACKET)*
    ;

argList
    : LPAREN (argItem (COMMA argItem)*)? RPAREN
    ;

argItem
    : expression
    |                   // empty slot (1C allows Func(,second) style)
    ;


// ════════════════════════════════════════════════════════════════════════════
// LEXER RULES — Keywords (trilingual, case-insensitive for ASCII)
// ════════════════════════════════════════════════════════════════════════════

// ── Control flow ─────────────────────────────────────────────────────────────

IF        : 'если' | 'Если' | 'ЕСЛИ'
           | 'якщо' | 'Якщо' | 'ЯКЩО'
           | [Ii][Ff]
           ;

THEN      : 'тогда' | 'Тогда' | 'ТОГДА'
           | 'тоді'  | 'Тоді'  | 'ТОДІ'
           | [Tt][Hh][Ee][Nn]
           ;

ELSE      : 'иначе' | 'Иначе' | 'ИНАЧЕ'
           | 'інакше' | 'Інакше' | 'ІНАКШЕ'
           | [Ee][Ll][Ss][Ee]
           ;

ELSIF     : 'иначеесли'    | 'ИначеЕсли'    | 'ИНАЧЕЕСЛИ'
           | 'інакшеякщо'   | 'ІнакшеЯкщо'   | 'ІНАКШЕЯКЩО'
           | [Ee][Ll][Ss][Ee][Ii][Ff]
           | [Ee][Ll][Ss][Ii][Ff]
           ;

ENDIF     : 'конецесли'    | 'КонецЕсли'    | 'КОНЕЦЕСЛИ'
           | 'кінецьякщо'   | 'КінецьЯкщо'   | 'КІНЕЦЬЯКЩО'
           | [Ee][Nn][Dd][Ii][Ff]
           ;

FOR       : 'для' | 'Для' | 'ДЛЯ'        // same Ru + Uk
           | [Ff][Oo][Rr]
           ;

EACH      : 'каждого' | 'Каждого' | 'КАЖДОГО'
           | 'кожного'  | 'Кожного'  | 'КОЖНОГО'
           | [Ee][Aa][Cc][Hh]
           ;

IN        : 'из' | 'Из' | 'ИЗ'
           | 'з'  | 'З'
           | [Ii][Nn]
           ;

TO        : 'по' | 'По' | 'ПО'
           | 'до' | 'До' | 'ДО'
           | [Tt][Oo]
           ;

WHILE     : 'пока' | 'Пока' | 'ПОКА'
           | 'поки' | 'Поки' | 'ПОКИ'
           | [Ww][Hh][Ii][Ll][Ee]
           ;

DO        : 'цикл' | 'Цикл' | 'ЦИКЛ'    // same Ru + Uk
           | [Dd][Oo]
           ;

ENDDO     : 'конеццикла'  | 'КонецЦикла'  | 'КОНЕЦЦИКЛА'
           | 'кінецьциклу' | 'КінецьЦиклу' | 'КІНЕЦЬЦИКЛУ'
           | [Ee][Nn][Dd][Dd][Oo]
           ;

BREAK     : 'прервать'  | 'Прервать'  | 'ПРЕРВАТЬ'
           | 'перервати' | 'Перервати' | 'ПЕРЕРВАТИ'
           | [Bb][Rr][Ee][Aa][Kk]
           ;

CONTINUE  : 'продолжить'  | 'Продолжить'  | 'ПРОДОЛЖИТЬ'
           | 'продовжити'  | 'Продовжити'  | 'ПРОДОВЖИТИ'
           | [Cc][Oo][Nn][Tt][Ii][Nn][Uu][Ee]
           ;

RETURN    : 'возврат'    | 'Возврат'    | 'ВОЗВРАТ'
           | 'повернути'  | 'Повернути'  | 'ПОВЕРНУТИ'
           | [Rr][Ee][Tt][Uu][Rr][Nn]
           ;

// ── Subroutines ───────────────────────────────────────────────────────────────

PROCEDURE    : 'процедура' | 'Процедура' | 'ПРОЦЕДУРА'    // same Ru + Uk
              | [Pp][Rr][Oo][Cc][Ee][Dd][Uu][Rr][Ee]
              ;

ENDPROCEDURE : 'конецпроцедуры'   | 'КонецПроцедуры'   | 'КОНЕЦПРОЦЕДУРЫ'
              | 'кінецьпроцедури'  | 'КінецьПроцедури'  | 'КІНЕЦЬПРОЦЕДУРИ'
              | [Ee][Nn][Dd][Pp][Rr][Oo][Cc][Ee][Dd][Uu][Rr][Ee]
              ;

FUNCTION     : 'функция' | 'Функция' | 'ФУНКЦИЯ'
              | 'функція' | 'Функція' | 'ФУНКЦІЯ'
              | [Ff][Uu][Nn][Cc][Tt][Ii][Oo][Nn]
              ;

ENDFUNCTION  : 'конецфункции'   | 'КонецФункции'   | 'КОНЕЦФУНКЦИИ'
              | 'кінецьфункції'  | 'КінецьФункції'  | 'КІНЕЦЬФУНКЦІЇ'
              | [Ee][Nn][Dd][Ff][Uu][Nn][Cc][Tt][Ii][Oo][Nn]
              ;

EXPORT       : 'экспорт' | 'Экспорт' | 'ЭКСПОРТ'
              | 'експорт' | 'Експорт' | 'ЕКСПОРТ'
              | [Ee][Xx][Pp][Oo][Rr][Tt]
              ;

VAL          : 'знач' | 'Знач' | 'ЗНАЧ'    // same Ru + Uk
              | [Vv][Aa][Ll]
              ;

// ── Variable ──────────────────────────────────────────────────────────────────

VAR          : 'перем' | 'Перем' | 'ПЕРЕМ'
              | 'змін'  | 'Змін'  | 'ЗМІН'
              | [Vv][Aa][Rr]
              ;

// ── Error handling ────────────────────────────────────────────────────────────

TRY          : 'попытка' | 'Попытка' | 'ПОПЫТКА'
              | 'спроба'  | 'Спроба'  | 'СПРОБА'
              | [Tt][Rr][Yy]
              ;

EXCEPT       : 'исключение' | 'Исключение' | 'ИСКЛЮЧЕНИЕ'
              | 'виняток'    | 'Виняток'    | 'ВИНЯТОК'
              | [Ee][Xx][Cc][Ee][Pp][Tt]
              ;

RAISE        : 'вызватьисключение'  | 'ВызватьИсключение'  | 'ВЫЗВАТЬИСКЛЮЧЕНИЕ'
              | 'викинутивиняток'    | 'ВикинутиВиняток'    | 'ВИКИНУТИВИНЯТОК'
              | [Rr][Aa][Ii][Ss][Ee]
              ;

ENDTRY       : 'конецпопытки'  | 'КонецПопытки'  | 'КОНЕЦПОПЫТКИ'
              | 'кінецьспроби'  | 'КінецьСпроби'  | 'КІНЕЦЬСПРОБИ'
              | [Ee][Nn][Dd][Tt][Rr][Yy]
              ;

// ── Boolean / special values ──────────────────────────────────────────────────

TRUE         : 'истина'  | 'Истина'  | 'ИСТИНА'
              | 'істина'  | 'Істина'  | 'ІСТИНА'
              | [Tt][Rr][Uu][Ee]
              ;

FALSE        : 'ложь'      | 'Ложь'      | 'ЛОЖЬ'
              | 'хибність'  | 'Хибність'  | 'ХИБНІСТЬ'
              | 'хибно'     | 'Хибно'     | 'ХИБНО'
              | [Ff][Aa][Ll][Ss][Ee]
              ;

UNDEFINED    : 'неопределено' | 'Неопределено' | 'НЕОПРЕДЕЛЕНО'
              | 'невизначено'  | 'Невизначено'  | 'НЕВИЗНАЧЕНО'
              | [Uu][Nn][Dd][Ee][Ff][Ii][Nn][Ee][Dd]
              ;

NULL_KW      : [Nn][Uu][Ll][Ll]
              ;

// ── Logical operators ─────────────────────────────────────────────────────────

AND          : 'и' | 'И'
              | 'і' | 'І'
              | 'та' | 'Та' | 'ТА'
              | [Aa][Nn][Dd]
              ;

OR           : 'или' | 'Или' | 'ИЛИ'
              | 'або' | 'Або' | 'АБО'
              | [Oo][Rr]
              ;

NOT          : 'не' | 'Не' | 'НЕ'    // same Ru + Uk
              | [Nn][Oo][Tt]
              ;

// ── Object construction ───────────────────────────────────────────────────────

NEW          : 'новый' | 'Новый' | 'НОВЫЙ'
              | 'новий' | 'Новий' | 'НОВИЙ'
              | [Nn][Ee][Ww]
              ;

// ── Goto ──────────────────────────────────────────────────────────────────────

GOTO         : 'перейти' | 'Перейти' | 'ПЕРЕЙТИ'    // same Ru + Uk
              | [Gg][Oo][Tt][Oo]
              ;

// ── Preprocessor directives ───────────────────────────────────────────────────

PP_IF        : '#' WS? ( 'если' | 'Если' | 'якщо' | 'Якщо' | [Ii][Ff] ) ;
PP_THEN      : '#' WS? ( 'тогда' | 'Тогда' | 'тоді' | 'Тоді' | [Tt][Hh][Ee][Nn] ) ;
PP_ELSE      : '#' WS? ( 'иначе' | 'Иначе' | 'інакше' | 'Інакше' | [Ee][Ll][Ss][Ee] ) ;
PP_ELSIF     : '#' WS? ( 'иначеесли' | 'ИначеЕсли' | 'інакшеякщо' | 'ІнакшеЯкщо' | [Ee][Ll][Ss][Ee][Ii][Ff] ) ;
PP_ENDIF     : '#' WS? ( 'конецесли' | 'КонецЕсли' | 'кінецьякщо' | 'КінецьЯкщо' | [Ee][Nn][Dd][Ii][Ff] ) ;
PP_REGION    : '#' WS? ( 'область' | 'Область' | [Rr][Ee][Gg][Ii][Oo][Nn] ) REST_OF_LINE ;
PP_ENDREGION : '#' WS? ( 'конецобласти' | 'КонецОбласти' | 'кінецьобласті' | 'КінецьОбласті'
                       | [Ee][Nn][Dd][Rr][Ee][Gg][Ii][Oo][Nn] ) ;
PP_USE       : '#' WS? ( 'использовать' | 'Использовать' | 'використати' | 'Використати'
                       | [Uu][Ss][Ee] ) REST_OF_LINE ;

// ════════════════════════════════════════════════════════════════════════════
// LEXER RULES — Literals
// ════════════════════════════════════════════════════════════════════════════

INTEGER_LIT  : DIGIT+ ;

FLOAT_LIT    : DIGIT+ '.' DIGIT+ ;

DATE_LIT     : '\'' DIGIT DIGIT DIGIT DIGIT DIGIT DIGIT DIGIT DIGIT '\'' ;

STRING_LIT   : '"' STRING_CHAR* '"'
             | '\'' STRING_CHAR* '\''
             ;

fragment STRING_CHAR
    : ~["\\\n]
    | '""'           // 1C double-quote escape
    | '\n' [ \t]* '|'  // 1C multiline continuation
    ;

// ════════════════════════════════════════════════════════════════════════════
// LEXER RULES — Identifiers
// ════════════════════════════════════════════════════════════════════════════

IDENTIFIER   : LETTER (LETTER | DIGIT | '_')* ;

fragment LETTER
    : [a-zA-Z_]
    | 'Ѐ'..'ӿ'   // Cyrillic (covers Russian + Ukrainian + others)
    | 'Ԁ'..'ԯ'   // Cyrillic supplement
    ;

fragment DIGIT : [0-9] ;

// ════════════════════════════════════════════════════════════════════════════
// LEXER RULES — Operators and delimiters
// ════════════════════════════════════════════════════════════════════════════

PLUS      : '+' ;
MINUS     : '-' ;
MULTIPLY  : '*' ;
DIVIDE    : '/' ;
MODULO    : '%' ;

EQ        : '=' ;
NEQ       : '<>' ;
LT        : '<' ;
GT        : '>' ;
LTE       : '<=' ;
GTE       : '>=' ;

LPAREN    : '(' ;
RPAREN    : ')' ;
LBRACKET  : '[' ;
RBRACKET  : ']' ;
LBRACE    : '{' ;
RBRACE    : '}' ;
COMMA     : ',' ;
SEMI      : ';' ;
DOT       : '.' ;
QUESTION  : '?' ;
COLON     : ':' ;
TILDE     : '~' ;
AMPERSAND : '&' ;    // query parameter prefix: &ParamName

// ════════════════════════════════════════════════════════════════════════════
// LEXER RULES — Whitespace and comments
// ════════════════════════════════════════════════════════════════════════════

COMMENT  : '//' ~[\r\n]* -> channel(HIDDEN) ;
WS       : [ \t\r\n]+    -> skip ;

fragment REST_OF_LINE : ~[\r\n]* ;
