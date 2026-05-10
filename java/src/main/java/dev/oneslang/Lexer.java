package dev.oneslang;

import java.util.ArrayList;
import java.util.List;

/**
 * 1S: ERP Free Edition — Lexer (Java)
 * Tokenises UTF-8 source with bilingual Russian/English keywords.
 */
public class Lexer {

    private final String source;
    private final String filename;
    private int pos = 0, line = 1, col = 1;

    public Lexer(String source, String filename) {
        this.source   = source;
        this.filename = filename;
    }

    // ── Public ──────────────────────────────────────────────────────────────

    public List<Token> tokenize() {
        var tokens = new ArrayList<Token>();
        while (pos < source.length()) {
            Token t = nextToken();
            if (t != null) tokens.add(t);
        }
        tokens.add(new Token(TokenType.EOF, null, line, col));
        return tokens;
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private char peek() { return pos < source.length() ? source.charAt(pos) : '\0'; }
    private char peek(int off) {
        int i = pos + off;
        return i < source.length() ? source.charAt(i) : '\0';
    }

    private char advance() {
        char c = source.charAt(pos++);
        if (c == '\n') { line++; col = 1; } else { col++; }
        return c;
    }

    private int[] curPos() { return new int[]{line, col}; }

    // ── Scanner ───────────────────────────────────────────────────────────────

    private Token nextToken() {
        // Skip whitespace and newlines
        while (pos < source.length() && " \t\r\n".indexOf(peek()) >= 0) advance();
        if (pos >= source.length()) return null;

        int[] lc = curPos();
        char c = peek();

        // Comment
        if (c == '/' && peek(1) == '/') return readComment(lc);

        // Preprocessor
        if (c == '#') return readPreprocessor(lc);

        // String
        if (c == '"' || c == '\'') return readString(lc, c);

        // Number
        if (Character.isDigit(c)) return readNumber(lc);

        // Identifier / keyword (Latin or Cyrillic)
        if (Character.isLetter(c) || c == '_') return readWord(lc);

        // Operators
        return readOperator(lc);
    }

    private Token readComment(int[] lc) {
        var buf = new StringBuilder();
        while (pos < source.length() && peek() != '\n') buf.append(advance());
        return new Token(TokenType.COMMENT, buf.toString(), lc[0], lc[1]);
    }

    private Token readPreprocessor(int[] lc) {
        var buf = new StringBuilder();
        buf.append(advance()); // '#'
        while (pos < source.length() && (Character.isLetter(peek()) || peek() == '_'))
            buf.append(advance());
        String word = buf.toString().toLowerCase();
        // Argument (e.g. region name)
        var arg = new StringBuilder();
        while (pos < source.length() && peek() != '\n' && peek() != '\r')
            arg.append(advance());
        // Resolve via a minimal inline table (matches Python PP_KEYWORDS)
        TokenType tt = switch (word) {
            case "#если",       "#if"        -> TokenType.PP_IF;
            case "#тогда",      "#then"      -> TokenType.PP_THEN;
            case "#иначе",      "#else"      -> TokenType.PP_ELSE;
            case "#иначеесли",  "#elseif"    -> TokenType.PP_ELSIF;
            case "#конецесли",  "#endif"     -> TokenType.PP_ENDIF;
            case "#область",    "#region"    -> TokenType.PP_REGION;
            case "#конецобласти","#endregion"-> TokenType.PP_ENDREGION;
            case "#использовать","#use"      -> TokenType.PP_USE;
            default                          -> null;
        };
        if (tt == null) return null;
        return new Token(tt, arg.toString().strip(), lc[0], lc[1]);
    }

    private Token readString(int[] lc, char quote) {
        advance(); // opening quote
        var buf = new StringBuilder();
        while (pos < source.length()) {
            char ch = peek();
            if (ch == quote) {
                advance();
                if (peek() == quote) { buf.append(advance()); } // doubled escape
                else break;
            } else if (ch == '\n') {
                advance();
                while (pos < source.length() && (peek() == ' ' || peek() == '\t')) advance();
                if (peek() == '|') { advance(); buf.append('\n'); }
                else throw new RuntimeException("Unterminated string at " + lc[0] + ":" + lc[1]);
            } else {
                buf.append(advance());
            }
        }
        String val = buf.toString();
        if (val.matches("\\d{8}")) return new Token(TokenType.DATE, val, lc[0], lc[1]);
        return new Token(TokenType.STRING, val, lc[0], lc[1]);
    }

    private Token readNumber(int[] lc) {
        var buf = new StringBuilder();
        while (pos < source.length() && Character.isDigit(peek())) buf.append(advance());
        if (pos < source.length() && peek() == '.' && Character.isDigit(peek(1))) {
            buf.append(advance());
            while (pos < source.length() && Character.isDigit(peek())) buf.append(advance());
            return new Token(TokenType.FLOAT, buf.toString(), lc[0], lc[1]);
        }
        return new Token(TokenType.INTEGER, buf.toString(), lc[0], lc[1]);
    }

    private Token readWord(int[] lc) {
        var buf = new StringBuilder();
        while (pos < source.length() &&
               (Character.isLetterOrDigit(peek()) || peek() == '_'))
            buf.append(advance());
        String word = buf.toString();
        TokenType tt = TokenType.lookup(word);
        return new Token(tt, word, lc[0], lc[1]);
    }

    private Token readOperator(int[] lc) {
        char c = advance();
        return switch (c) {
            case '+' -> new Token(TokenType.PLUS,      "+", lc[0], lc[1]);
            case '-' -> new Token(TokenType.MINUS,     "-", lc[0], lc[1]);
            case '*' -> new Token(TokenType.MULTIPLY,  "*", lc[0], lc[1]);
            case '/' -> new Token(TokenType.DIVIDE,    "/", lc[0], lc[1]);
            case '%' -> new Token(TokenType.MODULO,    "%", lc[0], lc[1]);
            case '(' -> new Token(TokenType.LPAREN,    "(", lc[0], lc[1]);
            case ')' -> new Token(TokenType.RPAREN,    ")", lc[0], lc[1]);
            case '[' -> new Token(TokenType.LBRACKET,  "[", lc[0], lc[1]);
            case ']' -> new Token(TokenType.RBRACKET,  "]", lc[0], lc[1]);
            case '{' -> new Token(TokenType.LBRACE,    "{", lc[0], lc[1]);
            case '}' -> new Token(TokenType.RBRACE,    "}", lc[0], lc[1]);
            case ',' -> new Token(TokenType.COMMA,     ",", lc[0], lc[1]);
            case ';' -> new Token(TokenType.SEMICOLON, ";", lc[0], lc[1]);
            case '.' -> new Token(TokenType.DOT,       ".", lc[0], lc[1]);
            case '?' -> new Token(TokenType.QUESTION,  "?", lc[0], lc[1]);
            case ':' -> new Token(TokenType.COLON,     ":", lc[0], lc[1]);
            case '=' -> new Token(TokenType.EQ,        "=", lc[0], lc[1]);
            case '<' -> {
                if (peek() == '>') { advance(); yield new Token(TokenType.NEQ, "<>", lc[0], lc[1]); }
                if (peek() == '=') { advance(); yield new Token(TokenType.LTE, "<=", lc[0], lc[1]); }
                yield new Token(TokenType.LT, "<", lc[0], lc[1]);
            }
            case '>' -> {
                if (peek() == '=') { advance(); yield new Token(TokenType.GTE, ">=", lc[0], lc[1]); }
                yield new Token(TokenType.GT, ">", lc[0], lc[1]);
            }
            default -> throw new RuntimeException(
                String.format("Unknown char '%c' at %d:%d", c, lc[0], lc[1]));
        };
    }
}
