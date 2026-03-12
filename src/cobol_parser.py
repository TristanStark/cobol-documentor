import re
from typing import List, Optional

from .cobol_ast_nodes import (
    CallStmt,
    ComputeStmt,
    EvaluateStmt,
    GotoStmt,
    IfStmt,
    MoveStmt,
    Node,
    Paragraph,
    PerformStmt,
    Program,
    ReadStmt,
    SetToStmt,
    SetUpDownByStmt,
    Stmt,
    ZCallPgmStmt,
)
from .ibm_preprocess import PARA_RE, is_paragraph_label


class ParserError(Exception):
    pass


class CobolParser:
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.lines[self.i] if self.i < len(self.lines) else None

    def pop(self) -> Optional[str]:
        if self.i >= len(self.lines):
            return None
        v = self.lines[self.i]
        self.i += 1
        return v
    
    def _consume_procedure_division_header(self, first_line: str) -> None:
        text = first_line.strip().upper()

        # Si la ligne se termine déjà par un point, rien à faire
        if text.endswith("."):
            return

        # Sinon, on consomme les lignes suivantes jusqu'au point final
        while self.peek() is not None:
            nxt = self.pop()
            if nxt is None:
                break
            if nxt.strip().endswith("."):
                break

    def parse(self) -> Program:
        prog = Program()
        current: Optional[Paragraph] = None

        while self.peek() is not None:
            line = self.pop()
            if line is None:
                break

            if line.upper().startswith("PROCEDURE DIVISION"):
                self._consume_procedure_division_header(line)
                continue
            
            name = is_paragraph_label(line)
            if name:
                current = Paragraph(name=name)
                if name not in prog.paragraphs:
                    prog.order.append(name)
                prog.paragraphs[name] = current
                continue

            if current is None:
                current = Paragraph(name="__IMPLICIT__")
                prog.paragraphs[current.name] = current
                prog.order.append(current.name)

            stripped = line.strip()
            if not stripped:
                continue

            # blocs structurés
            upper = stripped.upper()
            if upper.startswith("IF "):
                current.body.append(self.parse_if_block(stripped))
                continue

            if upper.startswith("EVALUATE "):
                current.body.append(self.parse_evaluate_block(stripped))
                continue

            if upper.startswith("EXEC SQL"):
                current.body.append(Stmt(raw=self.parse_exec_sql_block(stripped)))
                continue

            # statement simple = ligne seule
            nodes = self.parse_statement(stripped)
            current.body.extend(nodes)

        return prog

    def parse_exec_sql_block(self, first_line: str) -> str:
        lines = [first_line]

        while self.peek() is not None:
            nxt = self.pop()
            if nxt is None:
                break
            lines.append(nxt)
            if "END-EXEC" in nxt.upper():
                break

        return " ".join(lines).strip()
    
    def _gather_statement(self, first: str) -> str:
        """Accumulate multi-line statements until terminators or paragraph marker."""
        stmt_lines = [first]
        while True:
            joined = " ".join(stmt_lines).strip()
            joined_upper = joined.upper()
            if joined_upper.endswith(".") or "END-IF" in joined_upper or "END-EVALUATE" in joined_upper:
                return joined
            next_line = self.peek()
            if next_line is None or PARA_RE.match(next_line):
                return joined
            stmt_lines.append(self.pop())

    def parse_statement(self, text: str) -> List[Node]:
        """Parse a single COBOL statement or block header into AST nodes."""
        stripped_text = text.strip()
        uppercase_text = stripped_text.upper()
        text_without_dot = stripped_text[:-1].strip() if stripped_text.endswith(".") else stripped_text

        if uppercase_text.startswith("*UNRESOLVED_COPY*"):
            return [Stmt(raw=stripped_text)]

        if re.match(r"^(STOP\s+RUN|GOBACK)\b", uppercase_text):
            return [Stmt(raw=stripped_text)]

        match = re.match(r"^GO\s+TO\s+([A-Z0-9-]+)\b", uppercase_text)
        if match:
            return [GotoStmt(target=match.group(1).upper())]

        match = re.match(r"^READ\s+([A-Z0-9-]+)(?:\s+INTO\s+([A-Z0-9-]+))?", uppercase_text)
        if match:
            return [ReadStmt(file=match.group(1).upper(), into=(match.group(2).upper() if match.group(2) else None))]

        match = re.match(r"^MOVE\s+(.+?)\s+TO\s+(.+)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            src = match.group(1).strip()
            dests = [d.strip().strip(",").upper() for d in match.group(2).split()]
            return [MoveStmt(src=src, dests=dests)]

        match = re.match(r"^SET\s+(.+?)\s+TO\s+(.+)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            left = match.group(1).strip()
            val = match.group(2).strip()
            if re.search(r"\bUP\s+BY\b|\bDOWN\s+BY\b", val, flags=re.IGNORECASE):
                pass
            else:
                targets = [x.strip().strip(",").upper() for x in left.split()]
                return [SetToStmt(targets=targets, value=val)]

        match = re.match(r"^SET\s+([A-Z0-9-]+)\s+(UP|DOWN)\s+BY\s+(.+)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            return [SetUpDownByStmt(target=match.group(1).upper(), direction=match.group(2).upper(), by=match.group(3).strip())]

        match = re.match(r"^COMPUTE\s+([A-Z0-9-]+)\s*=\s*(.+)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            return [ComputeStmt(target=match.group(1).upper(), expr=match.group(2).strip())]

        match = re.match(r"^PERFORM\s+([A-Z0-9-]+)\s+THRU\s+([A-Z0-9-]+)(.*)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            target_from = match.group(1).upper()
            target_to = match.group(2).upper()
            rest = match.group(3).strip()
            times = None
            until = None
            times_match = re.search(r"\b(\d+)\s+TIMES\b", rest, flags=re.IGNORECASE)
            if times_match:
                times = int(times_match.group(1))
            until_match = re.search(r"\bUNTIL\s+(.+)$", rest, flags=re.IGNORECASE)
            if until_match:
                until = until_match.group(1).strip()
            return [PerformStmt(target=target_from, target_thru=target_to, times=times, until=until)]

        match = re.match(r"^PERFORM\s+([A-Z0-9-]+)(.*)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            target = match.group(1).upper()
            rest = match.group(2).strip()
            times = None
            until = None
            times_match = re.search(r"\b(\d+)\s+TIMES\b", rest, flags=re.IGNORECASE)
            if times_match:
                times = int(times_match.group(1))
            until_match = re.search(r"\bUNTIL\s+(.+)$", rest, flags=re.IGNORECASE)
            if until_match:
                until = until_match.group(1).strip()
            return [PerformStmt(target=target, times=times, until=until)]

        match = re.match(r"^CALL\s+('|\")ZCALLPGM\\1\s+USING\s+(.+)$", text_without_dot, flags=re.IGNORECASE)
        if match:
            tail = match.group(2).strip()
            parts = [p.strip().strip(",") for p in tail.split()]
            prog_name = parts[0] if parts else "UNKNOWN"
            using = parts[1:] if len(parts) > 1 else []
            return [ZCallPgmStmt(program_name=prog_name, using=using)]

        match = re.match(r"^CALL\s+(.+?)(?:\s+USING\s+(.+))?$", text_without_dot, flags=re.IGNORECASE)
        if match:
            target = match.group(1).strip()
            using_raw = (match.group(2) or "").strip()
            using = [x.strip().strip(",") for x in using_raw.split()] if using_raw else []
            is_indirect = not re.match(r"^(['\"]).*\1$", target.strip())
            return [CallStmt(target=target, using=using, is_indirect=is_indirect)]

        if uppercase_text.startswith("IF "):
            return [self.parse_if_block(stripped_text)]

        if uppercase_text.startswith("EVALUATE "):
            return [self.parse_evaluate_block(stripped_text)]

        return [Stmt(raw=stripped_text)]

    def parse_if_block(self, first_line: str) -> IfStmt:
        header = first_line.strip()
        cond = header[2:].strip()
        if cond.upper().startswith("IF"):
            cond = cond[2:].strip()
        cond = cond.rstrip(".")

        then_nodes = []
        else_nodes = []
        in_else = False
        depth = 1

        while self.peek() is not None:
            nxt = self.peek()
            if nxt is None:
                break

            # si on tombe sur un nouveau paragraphe alors qu'on n'a pas fermé,
            # on sort pour éviter d'engloutir tout le programme
            if depth == 1 and is_paragraph_label(nxt):
                break

            line = self.pop().strip()
            upper = line.upper()

            if upper.startswith("IF "):
                nested = self.parse_if_block(line)
                (else_nodes if in_else else then_nodes).append(nested)
                continue

            if re.match(r"^ELSE\b", upper) and depth == 1:
                in_else = True
                continue

            if "END-IF" in upper:
                depth -= 1
                if depth == 0:
                    break
                continue

            if upper.startswith("EVALUATE "):
                node = self.parse_evaluate_block(line)
                (else_nodes if in_else else then_nodes).append(node)
                continue

            if upper.startswith("EXEC SQL"):
                node = Stmt(raw=self.parse_exec_sql_block(line))
                (else_nodes if in_else else then_nodes).append(node)
                continue

            nodes = self.parse_statement(line)
            (else_nodes if in_else else then_nodes).extend(nodes)

        return IfStmt(cond=cond, then_body=then_nodes, else_body=else_nodes)

    def parse_evaluate_block(self, first_line: str) -> EvaluateStmt:
        """Parse an EVALUATE block including WHEN clauses and optional OTHER."""
        header = first_line.strip()
        expr = header[len("EVALUATE"):].strip()
        if expr.endswith("."):
            expr = expr[:-1].strip()

        whens: List[tuple[str, List[Node]]] = []
        when_other: Optional[List[Node]] = None
        current_when: Optional[str] = None
        current_body: List[Node] = []

        def flush():
            nonlocal current_when, current_body, when_other, whens
            if current_when is None:
                return
            if current_when.upper() in ("OTHER", "WHEN OTHER"):
                when_other = current_body
            else:
                whens.append((current_when, current_body))
            current_when = None
            current_body = []

        while self.peek() is not None:
            line = self.pop()
            if line is None:
                break
            line_upper = line.upper().strip()

            if "END-EVALUATE" in line_upper:
                flush()
                break
            when_match = re.match(r"^WHEN\s+(.+)$", line.strip(), flags=re.IGNORECASE)
            if when_match:
                flush()
                current_when = when_match.group(1).strip().rstrip(".")
                continue

            stmt_text = self._gather_statement(line)
            if "END-EVALUATE" in stmt_text.upper():
                part = re.split(r"\bEND-EVALUATE\b", stmt_text, flags=re.IGNORECASE)[0].strip()
                if part:
                    current_body.extend(self.parse_statement(part))
                flush()
                break

            current_body.extend(self.parse_statement(stmt_text))

        return EvaluateStmt(expr=expr, whens=whens, when_other=when_other)
