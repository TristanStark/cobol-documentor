from typing import List



class Statement:
    def __init__(self, type: str = None, statement: str = None):
        self.statements: List[Statement] = []
        self.raw_text: str = statement or ""
        self.statement: str = statement or ""   # temporary compatibility
        self.typeStatement: str = type

    def parse(self):
        pass

    def __str__(self) -> str:
        return self.to_pretty_string()
    
    def evaluate(self, programm):
        for st in self.statements:
            st.evaluate(programm)

    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        label = self.display()
        lines = [prefix + connector + label]

        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(self.statements):
            lines.append(child.to_tree_string(new_prefix, i == len(self.statements) - 1))

        return "\n".join(lines)

    def is_leaf(self) -> bool:
        return self.typeStatement == "line" or not self.statements or len(self.statements) == 0

    def __repr__(self) -> str:
        return (
            f"Statement(typeStatement={self.typeStatement!r}, "
            f"statement={self.statement!r}, "
            f"children={len(self.statements)})"
        )
    
    def display(self) -> str:
        return f"{self.typeStatement.upper()} : {self.statement}"

    def to_pretty_string(self, level: int = 0, indent_unit: str = "    ") -> str:
        indent = indent_unit * level

        if self.is_leaf():
            #print(f"WARNING: CALLED DISPLAY WITH {self.typeStatement.upper()}")
            return f"{indent}{self.display()}"

        lines = [
            f"{indent}{self.typeStatement.upper()}, statements={len(self.statements)}, statement={self.statement!r}"
        ]

        for st in self.statements:
            lines.append(st.to_pretty_string(level + 1, indent_unit))

        lines.append(f"{indent}END STATEMENT {self.typeStatement.upper()} {self.statement}")
        return "\n".join(lines)

