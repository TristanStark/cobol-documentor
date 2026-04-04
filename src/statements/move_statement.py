from .base_statement import Statement

class MoveStatement(Statement):
    def __init__(self, statement: str):
        super().__init__(statement=statement)
        self.typeStatement = "move"
        pos = statement.find(" TO ") + 4
        self.destination = statement[pos:]
        self.modifier = statement[5:pos - 4]

    def display(self) -> str:
        return f"MOVE: {self.modifier}< -> >{self.destination}<"
    
    def evaluate(self, programm):
        # Est-ce que le modifier est une variable connue ? 
        # Si oui, on prend sa valeur
        # Sinon:
        #   - Si c'est une valeur littérale (ex: MOVE 'A' TO X), on prend la valeur littérale
        #   - Si c'est une variable inconnue, on considère que la valeur est "Unknown" (car on ne peut pas savoir)
        #   - Si c'est une variable littérale numérique (ex: MOVE 5 TO X), on considère que la valeur est 5
        if programm.memory_stack.does_variable_exist(self.modifier):
            value = programm.memory_stack.get_value(self.modifier)
            programm.memory_stack.set_value(self.destination, value)
        elif self.modifier.startswith("'") and self.modifier.endswith("'"):
            value = self.modifier[1:-1]  # Remove the surrounding quotes
            programm.memory_stack.set_value(self.destination, value)
        elif self.modifier.isdigit():
            programm.memory_stack.set_value(self.destination, int(self.modifier))
        elif self.modifier.upper() == "SPACES":
            programm.memory_stack.set_value(self.destination, " ")
        elif self.modifier.upper() == "ZEROS" or self.modifier.upper() == "ZERO":
            programm.memory_stack.set_value(self.destination, 0)
        elif self.modifier.upper() == "LOW-VALUES":
            programm.memory_stack.set_value(self.destination, "LOW-VALUES")
        elif self.modifier.upper() == "HIGH-VALUES":
            programm.memory_stack.set_value(self.destination, "HIGH-VALUES")
        else:
            raise ValueError(f"Modifier '{self.modifier}' is not a known variable, a quoted literal, or a numeric literal. Cannot determine value to move to '{self.destination}'.")

