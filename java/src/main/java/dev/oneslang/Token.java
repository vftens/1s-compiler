package dev.oneslang;

/**
 * 1S: ERP Free Edition — Token (Java implementation)
 * Mirrors the Python token model for a future JVM backend.
 */
public record Token(TokenType type, String value, int line, int col) {

    @Override
    public String toString() {
        return String.format("Token(%s, %s, %d:%d)", type, value, line, col);
    }
}
