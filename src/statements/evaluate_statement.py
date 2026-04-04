from .base_statement import Statement
from typing import List

class EvaluateWhenBranch:
    def __init__(self, condition: str):
        self.condition = condition
        self.statements: List[Statement] = []

class EvaluateStatement(Statement):
    def __init__(self, statement: str):
        super().__init__(statement=statement)
        self.typeStatement = "evaluate"
        self.subject = self._extract_subject(statement)
        self.whens: List[EvaluateWhenBranch] = []
        self.when_other: List[Statement] = []
        self._parsed = False

    @staticmethod
    def _extract_subject(statement: str) -> str:
        s = statement.strip()
        return s[len("EVALUATE "):].strip() if s.upper().startswith("EVALUATE ") else s

    def parse(self):
        if self._parsed:
            return self
        self._parsed = True
        self.whens = []
        self.when_other = []

        current_branch: EvaluateWhenBranch | None = None
        in_when_other = False

        for st in self.statements:
            raw = st.statement.strip()
            upper = raw.upper()

            if upper.startswith("WHEN "):
                cond = raw[len("WHEN "):].strip()
                if cond.upper() == "OTHER":
                    current_branch = None
                    in_when_other = True
                else:
                    current_branch = EvaluateWhenBranch(cond)
                    self.whens.append(current_branch)
                    in_when_other = False
                continue

            if upper == "END-EVALUATE":
                continue

            parsed_child = st.parse() if hasattr(st, "parse") and st.parse is not None else st
            child = parsed_child or st

            if in_when_other:
                self.when_other.append(child)
            elif current_branch is not None:
                current_branch.statements.append(child)

        return self

    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        lines = [f"{prefix}{connector}EVALUATE : {self.subject}"]

        new_prefix = prefix + ("    " if is_last else "│   ")

        for i, branch in enumerate(self.whens):
            is_last_when = (i == len(self.whens) - 1) and not self.when_other
            when_connector = "└── " if is_last_when else "├── "
            lines.append(f"{new_prefix}{when_connector}WHEN {branch.condition}")
            branch_prefix = new_prefix + ("    " if is_last_when else "│   ")
            for j, child in enumerate(branch.statements):
                lines.append(child.to_tree_string(branch_prefix, j == len(branch.statements) - 1))

        if self.when_other:
            lines.append(f"{new_prefix}└── WHEN OTHER")
            other_prefix = new_prefix + "    "
            for i, child in enumerate(self.when_other):
                lines.append(child.to_tree_string(other_prefix, i == len(self.when_other) - 1))

        return "\n".join(lines)
