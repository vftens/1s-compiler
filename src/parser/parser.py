"""
1S: ERP Free Edition — Recursive-descent parser
Builds an AST from the token stream produced by the Lexer.
"""
from __future__ import annotations
from typing import Optional
from ..lexer.tokens import Token, TokenType
from .ast_nodes import *


class ParseError(Exception):
    def __init__(self, msg: str, token: Token):
        super().__init__(f"[Parser] {msg} at {token.line}:{token.col} (got {token.type.name} {token.value!r})")
        self.token = token


class Parser:
    def __init__(self, tokens: list[Token]):
        # Filter comments — keep everything else
        self.tokens = [t for t in tokens if t.type != TokenType.COMMENT]
        self.pos = 0

    # ── Token navigation ────────────────────────────────────────────────────

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]   # EOF
        return self.tokens[idx]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return t

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, ttype: TokenType, hint: str = "") -> Token:
        if self._check(ttype):
            return self._advance()
        tok = self._peek()
        msg = hint or f"Expected {ttype.name}"
        raise ParseError(msg, tok)

    def _skip_semis(self):
        while self._match(TokenType.SEMICOLON):
            pass

    def _loc(self) -> tuple[int, int]:
        t = self._peek()
        return t.line, t.col

    # ── Entry point ─────────────────────────────────────────────────────────

    def parse(self) -> Module:
        mod = Module(body=[])
        self._skip_semis()
        while not self._check(TokenType.EOF):
            stmt = self._parse_top_level()
            if stmt:
                mod.body.append(stmt)
            self._skip_semis()
        return mod

    # ── Top-level ────────────────────────────────────────────────────────────

    def _parse_top_level(self) -> Optional[Node]:
        t = self._peek()

        if t.type == TokenType.PP_REGION:
            return self._parse_pp_region()
        if t.type == TokenType.PP_IF:
            return self._parse_pp_if()
        if t.type in (TokenType.PP_ENDREGION, TokenType.PP_ELSE, TokenType.PP_ELSIF, TokenType.PP_ENDIF):
            return None  # handled by caller

        if t.type == TokenType.VAR:
            return self._parse_var_decl()
        if t.type == TokenType.PROCEDURE:
            return self._parse_procedure()
        if t.type == TokenType.FUNCTION:
            return self._parse_function()

        return self._parse_statement()

    # ── Preprocessor ────────────────────────────────────────────────────────

    def _parse_pp_region(self) -> PPRegion:
        line, col = self._loc()
        t = self._advance()   # consume #Region
        name = t.value or ""
        body = []
        self._skip_semis()
        while not self._check(TokenType.EOF, TokenType.PP_ENDREGION):
            n = self._parse_top_level()
            if n:
                body.append(n)
            self._skip_semis()
        self._match(TokenType.PP_ENDREGION)
        return PPRegion(line=line, col=col, name=name, body=body)

    def _parse_pp_if(self) -> PPIfBlock:
        line, col = self._loc()
        self._advance()   # consume #If
        # collect raw condition text until #Then
        parts = []
        while not self._check(TokenType.PP_THEN, TokenType.EOF):
            parts.append(self._advance().value or "")
        self._match(TokenType.PP_THEN)
        cond_str = " ".join(str(p) for p in parts)
        body: list[Node] = []
        else_body: list[Node] = []
        self._skip_semis()
        while not self._check(TokenType.PP_ELSE, TokenType.PP_ENDIF, TokenType.EOF):
            n = self._parse_top_level()
            if n:
                body.append(n)
            self._skip_semis()
        if self._match(TokenType.PP_ELSE):
            self._skip_semis()
            while not self._check(TokenType.PP_ENDIF, TokenType.EOF):
                n = self._parse_top_level()
                if n:
                    else_body.append(n)
                self._skip_semis()
        self._match(TokenType.PP_ENDIF)
        return PPIfBlock(line=line, col=col, condition_str=cond_str, body=body, else_body=else_body)

    # ── Variable declaration ─────────────────────────────────────────────────

    def _parse_var_decl(self) -> VarDecl:
        line, col = self._loc()
        self._advance()   # consume Var / Перем
        names = []
        while True:
            name_tok = self._expect(TokenType.IDENTIFIER, "Expected variable name")
            names.append(name_tok.value)
            if not self._match(TokenType.COMMA):
                break
        export = bool(self._match(TokenType.EXPORT))
        self._match(TokenType.SEMICOLON)
        return VarDecl(line=line, col=col, names=names, export=export)

    # ── Procedure / Function ─────────────────────────────────────────────────

    def _parse_procedure(self) -> ProcedureDef:
        line, col = self._loc()
        self._advance()   # Procedure / Процедура
        name = self._expect(TokenType.IDENTIFIER).value
        params = self._parse_param_list()
        export = bool(self._match(TokenType.EXPORT))
        self._match(TokenType.SEMICOLON)
        body = self._parse_body(TokenType.ENDPROCEDURE)
        self._expect(TokenType.ENDPROCEDURE)
        return ProcedureDef(line=line, col=col, name=name, params=params, body=body, export=export)

    def _parse_function(self) -> FunctionDef:
        line, col = self._loc()
        self._advance()   # Function / Функция
        name = self._expect(TokenType.IDENTIFIER).value
        params = self._parse_param_list()
        export = bool(self._match(TokenType.EXPORT))
        self._match(TokenType.SEMICOLON)
        body = self._parse_body(TokenType.ENDFUNCTION)
        self._expect(TokenType.ENDFUNCTION)
        return FunctionDef(line=line, col=col, name=name, params=params, body=body, export=export)

    def _parse_param_list(self) -> list[Param]:
        self._expect(TokenType.LPAREN)
        params: list[Param] = []
        if self._check(TokenType.RPAREN):
            self._advance()
            return params
        while True:
            line, col = self._loc()
            by_value = bool(self._match(TokenType.VAL))
            name = self._expect(TokenType.IDENTIFIER).value
            default = None
            if self._match(TokenType.EQ):
                default = self._parse_expression()
            params.append(Param(line=line, col=col, name=name, by_value=by_value, default=default))
            if not self._match(TokenType.COMMA):
                break
        self._expect(TokenType.RPAREN)
        return params

    # ── Statement body ───────────────────────────────────────────────────────

    BODY_TERMINATORS = {
        TokenType.ENDPROCEDURE,
        TokenType.ENDFUNCTION,
        TokenType.ENDIF,
        TokenType.ENDDO,
        TokenType.ENDTRY,
        TokenType.ELSE,
        TokenType.ELSIF,
        TokenType.EXCEPT,
        TokenType.EOF,
    }

    def _parse_body(self, *extra_stops: TokenType) -> list[Node]:
        stops = self.BODY_TERMINATORS | set(extra_stops)
        body: list[Node] = []
        self._skip_semis()
        while self._peek().type not in stops:
            stmt = self._parse_statement()
            if stmt:
                body.append(stmt)
            self._skip_semis()
        return body

    # ── Statements ───────────────────────────────────────────────────────────

    def _parse_statement(self) -> Optional[Node]:
        t = self._peek()
        line, col = t.line, t.col

        if t.type == TokenType.VAR:
            return self._parse_var_decl()
        if t.type == TokenType.IF:
            return self._parse_if()
        if t.type == TokenType.WHILE:
            return self._parse_while()
        if t.type == TokenType.FOR:
            return self._parse_for()
        if t.type == TokenType.TRY:
            return self._parse_try()
        if t.type == TokenType.RETURN:
            return self._parse_return()
        if t.type == TokenType.BREAK:
            self._advance()
            self._match(TokenType.SEMICOLON)
            return BreakStmt(line=line, col=col)
        if t.type == TokenType.CONTINUE:
            self._advance()
            self._match(TokenType.SEMICOLON)
            return ContinueStmt(line=line, col=col)
        if t.type == TokenType.RAISE:
            return self._parse_raise()
        if t.type == TokenType.GOTO:
            self._advance()
            label = self._expect(TokenType.IDENTIFIER).value
            self._match(TokenType.SEMICOLON)
            return GotoStmt(line=line, col=col, label=label)
        if t.type == TokenType.LABEL:
            # ~LabelName
            self._advance()
            name = self._expect(TokenType.IDENTIFIER).value
            self._match(TokenType.COLON)
            return LabelStmt(line=line, col=col, name=name)
        if t.type == TokenType.PP_REGION:
            return self._parse_pp_region()
        if t.type == TokenType.PP_IF:
            return self._parse_pp_if()

        # Assignment or call
        if t.type == TokenType.IDENTIFIER:
            return self._parse_assign_or_call()

        self._skip_semis()
        return None

    def _parse_if(self) -> IfStmt:
        line, col = self._loc()
        self._advance()   # If / Если
        branches = []
        cond = self._parse_expression()
        self._expect(TokenType.THEN, "Expected 'Then'/'Тогда' after condition")
        self._match(TokenType.SEMICOLON)
        body = self._parse_body()
        branches.append(IfBranch(line=line, col=col, condition=cond, body=body))

        while self._check(TokenType.ELSIF):
            el_line, el_col = self._loc()
            self._advance()
            el_cond = self._parse_expression()
            self._expect(TokenType.THEN)
            self._match(TokenType.SEMICOLON)
            el_body = self._parse_body()
            branches.append(IfBranch(line=el_line, col=el_col, condition=el_cond, body=el_body))

        else_body: list[Node] = []
        if self._match(TokenType.ELSE):
            self._match(TokenType.SEMICOLON)
            else_body = self._parse_body()

        self._expect(TokenType.ENDIF)
        return IfStmt(line=line, col=col, branches=branches, else_body=else_body)

    def _parse_while(self) -> WhileStmt:
        line, col = self._loc()
        self._advance()   # While / Пока
        cond = self._parse_expression()
        self._expect(TokenType.DO, "Expected 'Do'/'Цикл'")
        self._match(TokenType.SEMICOLON)
        body = self._parse_body()
        self._expect(TokenType.ENDDO)
        return WhileStmt(line=line, col=col, condition=cond, body=body)

    def _parse_for(self) -> ForStmt | ForEachStmt:
        line, col = self._loc()
        self._advance()   # For / Для

        # ForEach: Для Каждого / For Each
        if self._match(TokenType.EACH):
            var = self._expect(TokenType.IDENTIFIER).value
            self._expect(TokenType.IN, "Expected 'In'/'Из'")
            coll = self._parse_expression()
            self._expect(TokenType.DO, "Expected 'Do'/'Цикл'")
            self._match(TokenType.SEMICOLON)
            body = self._parse_body()
            self._expect(TokenType.ENDDO)
            return ForEachStmt(line=line, col=col, var=var, collection=coll, body=body)

        # Numeric For: Для А = 1 По 10 Цикл
        var = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.EQ, "Expected '=' after loop variable")
        start = self._parse_expression()
        self._expect(TokenType.TO, "Expected 'To'/'По'")
        end = self._parse_expression()
        self._expect(TokenType.DO, "Expected 'Do'/'Цикл'")
        self._match(TokenType.SEMICOLON)
        body = self._parse_body()
        self._expect(TokenType.ENDDO)
        return ForStmt(line=line, col=col, var=var, start=start, end=end, body=body)

    def _parse_try(self) -> TryStmt:
        line, col = self._loc()
        self._advance()   # Try / Попытка
        self._match(TokenType.SEMICOLON)
        body = self._parse_body()
        self._expect(TokenType.EXCEPT)
        self._match(TokenType.SEMICOLON)
        except_body = self._parse_body()
        self._expect(TokenType.ENDTRY)
        return TryStmt(line=line, col=col, body=body, except_body=except_body)

    def _parse_return(self) -> ReturnStmt:
        line, col = self._loc()
        self._advance()
        value = None
        if not self._check(TokenType.SEMICOLON, TokenType.ENDFUNCTION, TokenType.ENDPROCEDURE, TokenType.EOF):
            value = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return ReturnStmt(line=line, col=col, value=value)

    def _parse_raise(self) -> RaiseStmt:
        line, col = self._loc()
        self._advance()
        value = None
        if not self._check(TokenType.SEMICOLON, TokenType.EOF):
            value = self._parse_expression()
        self._match(TokenType.SEMICOLON)
        return RaiseStmt(line=line, col=col, value=value)

    def _parse_assign_or_call(self) -> Node:
        """
        Can be:  Identifier = expr   (assignment)
                 Identifier.Member = expr
                 Identifier[Index] = expr
                 Identifier(...)    (call stmt)
                 Identifier.Method(...)
        """
        line, col = self._loc()
        left = self._parse_postfix()

        if self._match(TokenType.EQ):
            value = self._parse_expression()
            self._match(TokenType.SEMICOLON)
            return AssignStmt(line=line, col=col, target=left, value=value)

        # Must be a call expression
        self._match(TokenType.SEMICOLON)
        return CallStmt(line=line, col=col, call=left)

    # ── Expressions ──────────────────────────────────────────────────────────

    def _parse_expression(self) -> Node:
        return self._parse_ternary()

    def _parse_ternary(self) -> Node:
        """Cond ? TrueVal : FalseVal  (1S extension over classic 1C)"""
        node = self._parse_or()
        if self._match(TokenType.QUESTION):
            line, col = self._loc()
            if_true = self._parse_or()
            self._expect(TokenType.COLON)
            if_false = self._parse_or()
            return Ternary(line=line, col=col, condition=node, if_true=if_true, if_false=if_false)
        return node

    def _parse_or(self) -> Node:
        left = self._parse_and()
        while self._check(TokenType.OR):
            op = self._advance().value
            right = self._parse_and()
            left = BinOp(op="or", left=left, right=right)
        return left

    def _parse_and(self) -> Node:
        left = self._parse_not()
        while self._check(TokenType.AND):
            self._advance()
            right = self._parse_not()
            left = BinOp(op="and", left=left, right=right)
        return left

    def _parse_not(self) -> Node:
        if self._match(TokenType.NOT):
            line, col = self._loc()
            operand = self._parse_not()
            return UnaryOp(line=line, col=col, op="not", operand=operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> Node:
        left = self._parse_addition()
        CMP = {
            TokenType.EQ: "==",
            TokenType.NEQ: "!=",
            TokenType.LT: "<",
            TokenType.GT: ">",
            TokenType.LTE: "<=",
            TokenType.GTE: ">=",
        }
        while self._peek().type in CMP:
            op_tok = self._advance()
            right = self._parse_addition()
            left = BinOp(op=CMP[op_tok.type], left=left, right=right)
        return left

    def _parse_addition(self) -> Node:
        left = self._parse_multiplication()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            right = self._parse_multiplication()
            left = BinOp(op=op, left=left, right=right)
        return left

    def _parse_multiplication(self) -> Node:
        left = self._parse_unary()
        while self._check(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op = self._advance().value
            right = self._parse_unary()
            left = BinOp(op=op, left=left, right=right)
        return left

    def _parse_unary(self) -> Node:
        if self._check(TokenType.MINUS):
            line, col = self._loc()
            self._advance()
            return UnaryOp(line=line, col=col, op="-", operand=self._parse_unary())
        if self._check(TokenType.PLUS):
            self._advance()
            return self._parse_unary()
        return self._parse_postfix()

    def _parse_postfix(self) -> Node:
        node = self._parse_primary()
        while True:
            if self._check(TokenType.DOT):
                self._advance()
                member = self._expect(TokenType.IDENTIFIER).value
                if self._check(TokenType.LPAREN):
                    args = self._parse_args()
                    node = CallExpr(callee=MemberExpr(obj=node, member=member), args=args)
                else:
                    node = MemberExpr(obj=node, member=member)
            elif self._check(TokenType.LBRACKET):
                self._advance()
                idx = self._parse_expression()
                self._expect(TokenType.RBRACKET)
                node = IndexExpr(obj=node, index=idx)
            elif self._check(TokenType.LPAREN) and isinstance(node, Identifier):
                args = self._parse_args()
                node = CallExpr(callee=node, args=args)
            else:
                break
        return node

    def _parse_primary(self) -> Node:
        t = self._peek()
        line, col = t.line, t.col

        if t.type == TokenType.INTEGER:
            self._advance()
            return Literal(line=line, col=col, value=t.value, kind="integer")
        if t.type == TokenType.FLOAT:
            self._advance()
            return Literal(line=line, col=col, value=t.value, kind="float")
        if t.type == TokenType.STRING:
            self._advance()
            return Literal(line=line, col=col, value=t.value, kind="string")
        if t.type == TokenType.DATE:
            self._advance()
            return Literal(line=line, col=col, value=t.value, kind="date")
        if t.type == TokenType.TRUE:
            self._advance()
            return Literal(line=line, col=col, value=True, kind="bool")
        if t.type == TokenType.FALSE:
            self._advance()
            return Literal(line=line, col=col, value=False, kind="bool")
        if t.type == TokenType.NULL:
            self._advance()
            return Literal(line=line, col=col, value=None, kind="null")
        if t.type == TokenType.UNDEFINED:
            self._advance()
            return Literal(line=line, col=col, value=None, kind="undefined")
        if t.type == TokenType.NEW:
            return self._parse_new()
        if t.type == TokenType.IDENTIFIER:
            self._advance()
            return Identifier(line=line, col=col, name=t.value)
        if t.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr

        raise ParseError(f"Unexpected token in expression", t)

    def _parse_new(self) -> NewExpr:
        line, col = self._loc()
        self._advance()   # New / Новый
        type_name = self._expect(TokenType.IDENTIFIER).value
        args: list[Node] = []
        if self._check(TokenType.LPAREN):
            args = self._parse_args()
        return NewExpr(line=line, col=col, type_name=type_name, args=args)

    def _parse_args(self) -> list[Node]:
        self._expect(TokenType.LPAREN)
        args: list[Node] = []
        if self._check(TokenType.RPAREN):
            self._advance()
            return args
        while True:
            # Allow empty args: Func(,Second)  →  Func(None, Second) like 1C
            if self._check(TokenType.COMMA):
                args.append(Literal(value=None, kind="undefined"))
            else:
                args.append(self._parse_expression())
            if not self._match(TokenType.COMMA):
                break
        self._expect(TokenType.RPAREN)
        return args
