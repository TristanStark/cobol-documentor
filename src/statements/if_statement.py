from .base_statement import Statement
from typing import List
import re

class IfStatement(Statement):
    def __init__(self, statement: str):
        super().__init__(statement=statement)
        self.typeStatement = "if"
        self.condition = self._extract_condition(statement)
        self.then_statements: List[Statement] = []
        self.else_statements: List[Statement] = []
        self.has_else = False
        self._parsed = False

    @staticmethod
    def _extract_condition(statement: str) -> str:
        s = statement.strip()
        return s[3:].strip() if s.upper().startswith("IF ") else s

    def parse(self):
        if self._parsed:
            return self
        self._parsed = True
        self.then_statements = []
        self.else_statements = []
        self.has_else = False

        target = self.then_statements

        for st in self.statements:
            text = st.statement.strip().upper()

            if text == "ELSE":
                self.has_else = True
                target = self.else_statements
                continue

            if text == "END-IF":
                continue

            parsed_child = st.parse() if hasattr(st, "parse") and st.parse is not None else st
            target.append(parsed_child or st)

        return self
    
    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        lines = [f"{prefix}{connector}IF : {self.condition}"]

        new_prefix = prefix + ("    " if is_last else "│   ")

        lines.append(f"{new_prefix}├── THEN")
        then_prefix = new_prefix + "│   "
        for i, child in enumerate(self.then_statements):
            lines.append(child.to_tree_string(then_prefix, i == len(self.then_statements) - 1))

        if self.has_else:
            lines.append(f"{new_prefix}└── ELSE")
            else_prefix = new_prefix + "    "
            for i, child in enumerate(self.else_statements):
                lines.append(child.to_tree_string(else_prefix, i == len(self.else_statements) - 1))

        return "\n".join(lines)
    
    @staticmethod
    def evaluate_single_condition(variable_a, operator, variable_b, memory_stack) -> bool:
        value_a = memory_stack.get_value(variable_a) if memory_stack.does_variable_exist(variable_a) else variable_a
        value_b = memory_stack.get_value(variable_b) if memory_stack.does_variable_exist(variable_b) else variable_b
        if operator == "=":
            return value_a == value_b
        if operator == "!=" or operator == "<>":
            return value_a != value_b
        if operator == ">":
            return value_a > value_b
        if operator == "<":
            return value_a < value_b
        if operator == ">=":
            return value_a >= value_b
        if operator == "<=":
            return value_a <= value_b
        raise ValueError(f"Unsupported operator '{operator}' in condition.")


    @staticmethod
    def evaluate_condition(entire_condition: str, memory_stack) -> bool:
        """
        Évalue la condition string en utilisant les valeurs actuelles des variables dans le memory_stack.
        La condition peut contenir :
        - comparaisons : A = B, A > B, A <= B...
        - booléens simples : A  =>  A = True
        - opérateurs logiques : AND, OR, NOT
        - parenthèses
        """

        COMPARISON_OPERATORS = {"=", "==", "!=", "<>", ">", "<", ">=", "<="}

        def tokenize_condition(condition: str) -> list[str]:
            token_pattern = re.compile(
                r"""
                \s*(
                    \(|\)                    |   # parenthèses
                    >=|<=|<>|!=|==|=|>|<     |   # comparateurs
                    \bAND\b|\bOR\b|\bNOT\b   |   # opérateurs logiques
                    '(?:[^']|\\')*'          |   # chaîne entre quotes simples
                    "(?:[^"]|\\")*"          |   # chaîne entre quotes doubles
                    [^\s()<>!=]+                 # identifiant / nombre / mot
                )
                """,
                re.IGNORECASE | re.VERBOSE
            )

            tokens = [match.group(1) for match in token_pattern.finditer(condition)]
            if not tokens:
                raise ValueError("Condition vide ou invalide.")
            return tokens

        tokens = tokenize_condition(entire_condition)
        pos = 0

        def current():
            return tokens[pos] if pos < len(tokens) else None

        def consume(expected: str | None = None):
            nonlocal pos
            token = current()
            if token is None:
                raise ValueError("Unexpected end of condition.")

            if expected is not None and token.upper() != expected.upper():
                raise ValueError(f"Expected token '{expected}', got '{token}'.")

            pos += 1
            return token

        def match(*values: str) -> bool:
            nonlocal pos
            token = current()
            if token is None:
                return False

            token_upper = token.upper()
            for value in values:
                if token_upper == value.upper():
                    pos += 1
                    return True
            return False

        def parse_or() -> bool:
            result = parse_and()
            while match("OR"):
                right = parse_and()
                result = result or right
            return result

        def parse_and() -> bool:
            result = parse_not()
            while match("AND"):
                right = parse_not()
                result = result and right
            return result

        def parse_not() -> bool:
            if match("NOT"):
                return not parse_not()
            return parse_primary()

        def parse_primary() -> bool:
            if match("("):
                result = parse_or()
                consume(")")
                return result

            return parse_atomic_condition()

        def parse_atomic_condition() -> bool:
            left = consume()
            next_token = current()

            # Cas comparaison explicite
            if next_token is not None:
                if next_token in COMPARISON_OPERATORS:
                    operator = consume()

                    # Uniformisation éventuelle de ==
                    if operator == "==":
                        operator = "="

                    right = consume()
                    return IfStatement.evaluate_single_condition(left, operator, right, memory_stack)

            # Cas condition simple : IF A  =>  A = True
            return IfStatement.evaluate_single_condition(left, "=", "True", memory_stack)

        result = parse_or()

        if pos != len(tokens):
            remaining = " ".join(tokens[pos:])
            raise ValueError(f"Unexpected remaining tokens: {remaining}")

        return result
