from .base_statement import Statement


class MathemathicOperatorStatement(Statement):
    def __init__(self, type = None, statement = None):
        verbs = statement.split(' ')
        type = verbs[0]
        super().__init__(type, statement)
        self.operator: str = type
        self.target: str = verbs[3]
        self.modifier: str = verbs[1]

    def display(self) -> str:
        return f"{self.operator}: {self.modifier} TO {self.target}"
    
    @staticmethod
    def perform_operation(operator: str, target_value, modifier_value):
        if operator == "ADD" or operator == "+":
            return target_value + modifier_value
        elif operator == "SUBTRACT" or operator == "-":
            return target_value - modifier_value
        elif operator == "MULTIPLY" or operator == "*":
            return target_value * modifier_value
        elif operator == "DIVIDE" or operator == "/":
            if modifier_value == 0:
                raise ValueError("Division by zero is not allowed.")
            return target_value / modifier_value
        else:
            raise ValueError(f"Unsupported operator '{operator}'.")

    def evaluate(self, programm):
        # Est-ce que le modifier est une variable connue ?
        # Si oui, on prend sa valeur
        # Sinon: est-ce que c'est numérique?
        #   - Si c'est une valeur littérale numérique (ex: ADD 5 TO X), on considère que la valeur est 5
        #   - Si c'est une variable inconnue ou une valeur littérale non numérique, 
        # on plante car S0C7
        if programm.memory_stack.does_variable_exist(self.modifier):
            modifier_value = programm.memory_stack.get_value(self.modifier)
        elif self.modifier.isdigit():
            modifier_value = int(self.modifier)
        else:
            raise ValueError(f"Modifier '{self.modifier}' is not a known variable or a numeric literal. Cannot determine value to use in '{self.operator}' operation for target '{self.target}'.")
        if isinstance(modifier_value, (int, float)):
            new_value = MathemathicOperatorStatement.perform_operation(self.operator, programm.memory_stack.get_value(self.target), modifier_value)
            programm.memory_stack.set_value(self.target, new_value)

