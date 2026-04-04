from typing import List
from .base_statement import Statement


class ReadStatement(Statement):
    def __init__(self, statement: str):
        super().__init__(statement=statement)
        self.typeStatement = "read"
        self.at_end_statements: List[Statement] = []
        self.not_at_end_statements: List[Statement] = []
        self.has_at_end = False
        self.has_not_at_end = False
        self._parsed = False

    def parse(self):
        if self._parsed:
            return self
        self._parsed = True
        self.at_end_statements = []
        self.not_at_end_statements = []
        self.has_at_end = False
        self.has_not_at_end = False

        target = None

        for st in self.statements:
            text = st.statement.strip().upper()

            if text == "AT END":
                self.has_at_end = True
                target = self.at_end_statements
                continue

            if text == "NOT AT END":
                self.has_not_at_end = True
                target = self.not_at_end_statements
                continue

            if text == "END-READ":
                continue

            parsed_child = st.parse() if hasattr(st, "parse") and st.parse is not None else st
            child = parsed_child or st

            if target is self.at_end_statements:
                self.at_end_statements.append(child)
            elif target is self.not_at_end_statements:
                self.not_at_end_statements.append(child)
            else:
                # Default to NOT AT END flow if no marker was seen.
                self.has_not_at_end = True
                self.not_at_end_statements.append(child)

        return self

    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        lines = [f"{prefix}{connector}READ : {self.statement}"]

        new_prefix = prefix + ("    " if is_last else "│   ")

        branches = []
        if self.has_at_end or self.at_end_statements:
            branches.append(("AT END", self.at_end_statements))
        if self.has_not_at_end or self.not_at_end_statements:
            branches.append(("NOT AT END", self.not_at_end_statements))

        for i, (label, children) in enumerate(branches):
            is_last_branch = i == len(branches) - 1
            branch_connector = "└── " if is_last_branch else "├── "
            lines.append(f"{new_prefix}{branch_connector}{label}")
            branch_prefix = new_prefix + ("    " if is_last_branch else "│   ")
            for j, child in enumerate(children):
                lines.append(child.to_tree_string(branch_prefix, j == len(children) - 1))

        return "\n".join(lines)
