from .base_statement import Statement

class CloseStatement(Statement):
    def __init__(self, type="close", statement=None):
        super().__init__(type, statement)
        self.file = statement.split(' ')[1]

    def display(self) -> str:
        return f"CLOSED FILE: {self.file}"