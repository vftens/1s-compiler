package dev.oneslang;

import java.util.HashMap;
import java.util.Map;

/**
 * 1S: ERP Free Edition — Token types (Java)
 * Trilingual keyword table: Russian / Ukrainian / English
 * Mirrors the Python reference implementation in src/lexer/tokens.py.
 */
public enum TokenType {
    // ── Literals ─────────────────────────────────────────────────────────────
    INTEGER, FLOAT, STRING, DATE,

    // ── Identifier ────────────────────────────────────────────────────────────
    IDENTIFIER,

    // ── Control flow ──────────────────────────────────────────────────────────
    IF, THEN, ELSE, ELSIF, ENDIF,
    FOR, EACH, IN, TO, WHILE, DO, ENDDO,
    BREAK, CONTINUE, RETURN,

    // ── Subroutines ───────────────────────────────────────────────────────────
    PROCEDURE, ENDPROCEDURE,
    FUNCTION, ENDFUNCTION,
    EXPORT, VAL,

    // ── Variable ──────────────────────────────────────────────────────────────
    VAR,

    // ── Error handling ────────────────────────────────────────────────────────
    TRY, EXCEPT, RAISE, ENDTRY,

    // ── Values ────────────────────────────────────────────────────────────────
    TRUE, FALSE, UNDEFINED, NULL_KW,

    // ── Logical ───────────────────────────────────────────────────────────────
    AND, OR, NOT,

    // ── Object ────────────────────────────────────────────────────────────────
    NEW,

    // ── Legacy ────────────────────────────────────────────────────────────────
    GOTO, LABEL,

    // ── Preprocessor ──────────────────────────────────────────────────────────
    PP_IF, PP_THEN, PP_ELSE, PP_ELSIF, PP_ENDIF,
    PP_REGION, PP_ENDREGION, PP_USE,

    // ── Operators ─────────────────────────────────────────────────────────────
    PLUS, MINUS, MULTIPLY, DIVIDE, MODULO,
    ASSIGN, EQ, NEQ, LT, GT, LTE, GTE,

    // ── Delimiters ────────────────────────────────────────────────────────────
    LPAREN, RPAREN, LBRACKET, RBRACKET, LBRACE, RBRACE,
    COMMA, SEMICOLON, DOT, QUESTION, COLON, TILDE, AMPERSAND,

    // ── Query ─────────────────────────────────────────────────────────────────
    QUERY_BEGIN, QUERY_TEXT, QUERY_END,

    // ── Special ───────────────────────────────────────────────────────────────
    EOF, COMMENT;

    // ── Trilingual keyword lookup table ──────────────────────────────────────

    private static final Map<String, TokenType> KEYWORDS = new HashMap<>(256);

    static {
        // ── Control flow ──────────────────────────────────────────────────────
        // IF:  Russian | Ukrainian | English
        kw("если",           IF);  kw("якщо",          IF);  kw("if",           IF);
        // THEN
        kw("тогда",          THEN); kw("тоді",          THEN); kw("then",         THEN);
        // ELSE
        kw("иначе",          ELSE); kw("інакше",        ELSE); kw("else",         ELSE);
        // ELSIF
        kw("иначеесли",      ELSIF); kw("інакшеякщо",  ELSIF); kw("elseif",  ELSIF); kw("elsif", ELSIF);
        // ENDIF
        kw("конецесли",      ENDIF); kw("кінецьякщо",  ENDIF); kw("endif",        ENDIF);

        // FOR (same Ru + Uk)
        kw("для",            FOR);                            kw("for",          FOR);
        // EACH
        kw("каждого",        EACH); kw("кожного",      EACH); kw("each",         EACH);
        // IN
        kw("из",             IN);   kw("з",             IN);   kw("in",           IN);
        // TO
        kw("по",             TO);   kw("до",            TO);   kw("to",           TO);
        // WHILE
        kw("пока",           WHILE); kw("поки",         WHILE); kw("while",       WHILE);
        // DO (loop body opener, same Ru + Uk)
        kw("цикл",           DO);                            kw("do",           DO);
        // ENDDO
        kw("конеццикла",     ENDDO); kw("кінецьциклу", ENDDO); kw("enddo",       ENDDO);
        // BREAK
        kw("прервать",       BREAK); kw("перервати",   BREAK); kw("break",        BREAK);
        // CONTINUE
        kw("продолжить",     CONTINUE); kw("продовжити", CONTINUE); kw("continue", CONTINUE);
        // RETURN
        kw("возврат",        RETURN); kw("повернути",  RETURN); kw("return",      RETURN);

        // ── Subroutines ───────────────────────────────────────────────────────
        // PROCEDURE (same Ru + Uk)
        kw("процедура",      PROCEDURE);                     kw("procedure",    PROCEDURE);
        // ENDPROCEDURE
        kw("конецпроцедуры", ENDPROCEDURE); kw("кінецьпроцедури", ENDPROCEDURE); kw("endprocedure", ENDPROCEDURE);
        // FUNCTION
        kw("функция",        FUNCTION); kw("функція",    FUNCTION); kw("function",    FUNCTION);
        // ENDFUNCTION
        kw("конецфункции",   ENDFUNCTION); kw("кінецьфункції", ENDFUNCTION); kw("endfunction", ENDFUNCTION);
        // EXPORT
        kw("экспорт",        EXPORT); kw("експорт",    EXPORT); kw("export",      EXPORT);
        // VAL (same Ru + Uk)
        kw("знач",           VAL);                          kw("val",          VAL);

        // ── Variable ──────────────────────────────────────────────────────────
        kw("перем",          VAR);  kw("змін",          VAR);  kw("var",          VAR);

        // ── Error handling ────────────────────────────────────────────────────
        // TRY
        kw("попытка",        TRY);  kw("спроба",        TRY);  kw("try",          TRY);
        // EXCEPT
        kw("исключение",     EXCEPT); kw("виняток",    EXCEPT); kw("except",      EXCEPT);
        // RAISE
        kw("вызватьисключение", RAISE); kw("викинутивиняток", RAISE); kw("raise", RAISE);
        // ENDTRY
        kw("конецпопытки",   ENDTRY); kw("кінецьспроби", ENDTRY); kw("endtry",  ENDTRY);

        // ── Values ────────────────────────────────────────────────────────────
        kw("истина",         TRUE);  kw("істина",       TRUE);  kw("true",         TRUE);
        kw("ложь",           FALSE); kw("хибність",    FALSE); kw("хибно",         FALSE); kw("false", FALSE);
        kw("неопределено",   UNDEFINED); kw("невизначено", UNDEFINED); kw("undefined", UNDEFINED);
        kw("null",           NULL_KW);

        // ── Logical ───────────────────────────────────────────────────────────
        kw("и",              AND);  kw("і",             AND);  kw("та",            AND);  kw("and", AND);
        kw("или",            OR);   kw("або",           OR);   kw("or",            OR);
        kw("не",             NOT);                            kw("not",          NOT);

        // ── Object ────────────────────────────────────────────────────────────
        kw("новый",          NEW);  kw("новий",         NEW);  kw("new",           NEW);

        // ── Legacy ────────────────────────────────────────────────────────────
        kw("перейти",        GOTO);                          kw("goto",         GOTO);
    }

    private static void kw(String word, TokenType type) {
        KEYWORDS.put(word, type);
    }

    /**
     * Look up a word (already lowercased) in the keyword table.
     * Returns IDENTIFIER if not found.
     */
    public static TokenType lookup(String lowerWord) {
        return KEYWORDS.getOrDefault(lowerWord, IDENTIFIER);
    }

    /** Returns true if this token type is a keyword. */
    public boolean isKeyword() {
        return this != IDENTIFIER && this != INTEGER && this != FLOAT
            && this != STRING && this != DATE && this != EOF && this != COMMENT;
    }
}
