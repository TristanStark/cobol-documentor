from .base_statement import Statement

class OpenStatement(Statement):
    def __init__(self, type="open", statement=None):
        super().__init__(type, statement)
        self.file = statement.split(' ')[1]

    def display(self) -> str:
        return f"OPENED FILE: {self.file}"