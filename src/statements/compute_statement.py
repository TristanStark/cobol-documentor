from .base_statement import Statement


class ComputeStatement(Statement):
    def __init__(self, type = "compute", statement = None):
        super().__init__(type, statement)
        verbs = statement.split(' ')
        self.target = verbs[1]
        self.expression = verbs[3:]

    def display(self) -> str:
        return f"COMPUTED NEW VALUE FOR : {self.target}: NEW VALUE IS >{self.expression}<"
