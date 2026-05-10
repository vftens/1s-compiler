package dev.oneslang;

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/**
 * 1S: ERP Free Edition — Java CLI
 *
 * Usage:
 *   java -jar 1s-compiler.jar tokens  <file.1s>
 *   java -jar 1s-compiler.jar ast     <file.1s>
 *   java -jar 1s-compiler.jar check   <file.1s>   (parse-only, report errors)
 */
public class Main {

    public static void main(String[] args) throws IOException {
        if (args.length < 2) {
            printUsage();
            System.exit(1);
        }

        String command = args[0];
        Path   source  = Path.of(args[1]);

        if (!Files.exists(source)) {
            System.err.println("File not found: " + source);
            System.exit(1);
        }

        String text = Files.readString(source, StandardCharsets.UTF_8);

        switch (command.toLowerCase()) {
            case "tokens" -> cmdTokens(text, source.getFileName().toString());
            case "ast"    -> cmdAst(text, source.getFileName().toString());
            case "check"  -> cmdCheck(text, source.getFileName().toString());
            default       -> { printUsage(); System.exit(1); }
        }
    }

    // ── tokens: dump the ANTLR token stream ──────────────────────────────────

    static void cmdTokens(String text, String filename) {
        OneSLangLexer lexer = createLexer(text, filename);
        CommonTokenStream tokens = new CommonTokenStream(lexer);
        tokens.fill();
        OneSLangLexer refLexer = lexer; // for vocabulary
        var vocab = refLexer.getVocabulary();
        for (Token tok : tokens.getTokens()) {
            if (tok.getType() == Token.EOF) break;
            String typeName = vocab.getSymbolicName(tok.getType());
            if (typeName == null) typeName = String.valueOf(tok.getType());
            System.out.printf("Token(%-20s  %s  %d:%d)%n",
                typeName + ",",
                escape(tok.getText()),
                tok.getLine(),
                tok.getCharPositionInLine());
        }
    }

    // ── ast: print the ANTLR parse tree ──────────────────────────────────────

    static void cmdAst(String text, String filename) {
        OneSLangParser parser = createParser(text, filename);
        ParseTree tree = parser.module();
        System.out.println(tree.toStringTree(parser));
    }

    // ── check: parse and report errors ───────────────────────────────────────

    static void cmdCheck(String text, String filename) {
        CountingErrorListener errors = new CountingErrorListener();
        OneSLangLexer lexer = createLexer(text, filename);
        lexer.removeErrorListeners();
        lexer.addErrorListener(errors);

        OneSLangParser parser = createParser(text, filename);
        parser.removeErrorListeners();
        parser.addErrorListener(errors);

        parser.module();

        if (errors.count == 0) {
            System.out.println("OK — no parse errors in " + filename);
        } else {
            System.err.println(errors.count + " error(s) in " + filename);
            System.exit(1);
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    static OneSLangLexer createLexer(String text, String filename) {
        CharStream cs = CharStreams.fromString(text, filename);
        return new OneSLangLexer(cs);
    }

    static OneSLangParser createParser(String text, String filename) {
        OneSLangLexer lexer = createLexer(text, filename);
        CommonTokenStream tokens = new CommonTokenStream(lexer);
        return new OneSLangParser(tokens);
    }

    static String escape(String s) {
        return s.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
    }

    static void printUsage() {
        System.out.println("1S ERP Free Edition Compiler (Java/ANTLR4)");
        System.out.println("Usage:");
        System.out.println("  1s tokens <file.1s>  — dump token stream");
        System.out.println("  1s ast    <file.1s>  — print parse tree");
        System.out.println("  1s check  <file.1s>  — parse and report errors");
    }

    // ── Error listener ────────────────────────────────────────────────────────

    static class CountingErrorListener extends BaseErrorListener {
        int count = 0;

        @Override
        public void syntaxError(Recognizer<?, ?> recognizer, Object offendingSymbol,
                                int line, int charPos, String msg,
                                RecognitionException e) {
            count++;
            System.err.printf("[ERROR] %d:%d — %s%n", line, charPos, msg);
        }
    }
}
