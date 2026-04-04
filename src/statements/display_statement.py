import re
from .base_statement import Statement

class DisplayStatement(Statement):
    def __init__(self, type="display", statement=None):
        super().__init__(type, statement)
        self.displayed = self.transform_display_line(statement)

    def transform_display_line(self, line: str) -> str:
        line = re.sub(r'^\s*DISPLAY\s+', '', line).strip()
        parts = re.findall(r"'([^']*)'|([^\s]+)", line)
        result = []
        for quoted, unquoted in parts:
            if quoted:
                result.append(quoted)
            elif unquoted:
                result.append(f"{{variable_{unquoted}}}")
        return "".join(result)

    def display(self) -> str:
        return f"DISPLAY: {self.displayed}"