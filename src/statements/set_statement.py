from .base_statement import Statement

class SetStatement(Statement):
    def __init__(self, type="set", statement=None):
        super().__init__(type, statement)
        verbs = statement.split(' ')
        self.target_var = verbs[1]
        self.value = verbs[3]

    def display(self) -> str:
        return f"SET: {self.target_var} is now {self.value}"

    def evaluate(self, programm):
        programm.memory_stack.set_value(self.target_var, self.value)