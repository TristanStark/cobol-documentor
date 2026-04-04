from .base_statement import Statement

class PerformStatement(Statement):
    def __init__(self, type="perform", statement=None):
        super().__init__(type, statement)
        self.typePerform = "One Liner"
        self.perform_what = None
        self.until_statement = None
        self.varying_variable = None
        self.varying_start = None
        self.varying_by = None

    def __str__(self):
        if self.typePerform == "One Liner":
            return self.statement
        elif self.typePerform == "UNTIL":
            s = f"PerformStatementUntil(statements={len(self.statements)})"
            for st in self.statements:
                s += f"\n  {st}"
            return s

    def is_perform_until_or_varying(self):
        words = self.statement.split(' ')
        if len(words) > 1 and words[1] in ("VARYING", "UNTIL"):
            self.typePerform = words[1]
        else:
            self.typePerform = "One Liner"

    def extract_perform_what(self, line: str):
        thru_pos = line.upper().find("THRU ")
        through_pos = line.upper().find("THROUGH ")
        if thru_pos != -1 or through_pos != -1:
            thru_pos = max(thru_pos, through_pos)
        return line[len("PERFORM "):thru_pos].strip()

    def _determinate_condition(self):
        if self.typePerform == "UNTIL":
            pos = self.statement.upper().find("UNTIL") + len("UNTIL")
            self.until_statement = self.statement[pos:].strip()
        elif self.typePerform in ("VARYING", None):
            pos_start_varying = self.statement.upper().find("VARYING") + len("VARYING")
            pos_start_from = self.statement.upper().find("FROM", pos_start_varying) + len("FROM")
            pos_start_by = self.statement.upper().find("BY", pos_start_from) + len("BY")
            pos_start_until = self.statement.upper().find("UNTIL", pos_start_by) + len("UNTIL")
            self.varying_variable = self.statement[pos_start_varying:pos_start_from - len("FROM")].strip()
            self.varying_start = self.statement[pos_start_from:pos_start_by - len("BY")].strip()
            self.varying_by = self.statement[pos_start_by:pos_start_until - len("UNTIL")].strip()
            self.until_statement = self.statement[pos_start_until:].strip()

    def is_perform_until(self):
        words = self.statement.split(' ')
        if len(words) > 1 and words[1] in ("VARYING", "UNTIL"):
            self.is_perform_until_or_varying()
            return True
        return False

    def evaluate_condition(self, programm):
        # Implement condition evaluation logic for PerformStatement
        pass

    def evaluate(self, programm):
        self._determinate_condition()
        if self.typePerform == "One Liner":
            programm.execute_paragraph(self.perform_what)
        elif self.typePerform == "UNTIL":
            while not self.evaluate_condition(programm):
                for st in self.statements:
                    st.evaluate(programm)