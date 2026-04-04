from .base_statement import Statement
from .line_statement import LineStatement
from .perform_statement import PerformStatement
from .if_statement import IfStatement
from .evaluate_statement import EvaluateStatement
from .goback_statement import GoBackStatement
from .read_statement import ReadStatement
from .close_statement import CloseStatement
from .open_statement import OpenStatement
from .display_statement import DisplayStatement
from .compute_statement import ComputeStatement
from .maths_statement import MathemathicOperatorStatement
from typing import List
from .move_statement import MoveStatement
from .set_statement import SetStatement
from .zcallpgm_statement import ZCallPgmStatement

class ParagraphStatement(Statement):
    def __init__(self, statement: str):
        super().__init__(statement=statement)
        self.typeStatement = "paragraph"

    def parse(self):
        new_statements = []
        current_structure: Statement = ParagraphStatement(self.statement)
        structure_stack: List[Statement] = [current_structure]
        for i, st in enumerate(self.statements):
            statement = st.statement
            if current_structure.typeStatement == "perform" and (current_structure.typePerform == "UNTIL" or current_structure.typePerform == "VARYING") and statement.startswith("END-PERFORM"):
                current_structure.statements.append(LineStatement(statement))
                new_statements.append(current_structure)
                old = current_structure
                current_structure = structure_stack.pop()
                current_structure.statements.append(old)
                continue
            if statement.startswith("PERFORM "):
                new_perform = PerformStatement(statement)
                # On doit pouvoir savoir si c'est un perform until ou pas
                if new_perform.is_perform_until():
                    structure_stack.append(current_structure)
                    current_structure = new_perform
                    continue
                current_structure.statements.append(new_perform)
                continue
            if statement.startswith("IF "):
                new_if = IfStatement(statement)
                structure_stack.append(current_structure)
                current_structure = new_if
                continue
            if statement.startswith("END-IF"):
                current_structure.statements.append(LineStatement(statement))
                current_structure.parse()
                old = current_structure
                current_structure = structure_stack.pop()
                current_structure.statements.append(old)
                continue
            if statement.startswith("EVALUATE "):
                new_evaluate = EvaluateStatement(statement)
                structure_stack.append(current_structure)
                old = current_structure
                current_structure = new_evaluate
                continue
            if statement.startswith("END-EVALUATE"):
                current_structure.statements.append(LineStatement(statement))
                current_structure.parse()
                new_statements.append(current_structure)
                old = current_structure
                current_structure = structure_stack.pop()
                current_structure.statements.append(old)
                continue
            if statement.startswith("READ "):
                new_read = ReadStatement(statement)
                structure_stack.append(current_structure)
                current_structure = new_read
                continue
            if statement.startswith("END-READ"):
                current_structure.statements.append(LineStatement(statement))
                current_structure.parse()
                old = current_structure
                current_structure = structure_stack.pop()
                current_structure.statements.append(old)
                continue
            if statement.startswith("CLOSE "):
                current_structure.statements.append(CloseStatement(statement=statement))
                continue
            if statement.startswith("OPEN "):
                current_structure.statements.append(OpenStatement(statement=statement))
                continue
            if statement.startswith("DISPLAY "):
                current_structure.statements.append(DisplayStatement(statement=statement))
                continue
            if statement.startswith("COMPUTE "):
                current_structure.statements.append(ComputeStatement(statement=statement))
                continue
            if (
                statement.startswith("ADD ")
                or statement.startswith("SUBTRACT ")
                or statement.startswith("MULTIPLY ")
                or statement.startswith("DIVIDE ")
            ):
                current_structure.statements.append(MathemathicOperatorStatement(statement=statement))
                continue
            if statement.startswith("MOVE "):
                current_structure.statements.append(MoveStatement(statement))
                continue
            if statement.startswith("SET "):
                current_structure.statements.append(SetStatement(statement=statement))
                continue
            if statement.startswith("CALL "):
                tokens = statement.strip().split()
                if len(tokens) >= 3 and tokens[1].upper() == "'ZCALLPGM'" and tokens[2].upper() == "USING":
                    current_structure.statements.append(ZCallPgmStatement(statement=statement))
                else:
                    print(f"TOKENS = {tokens} ")
                    current_structure.statements.append(LineStatement(statement))
                continue
            if statement == "GO BACK" or statement == "GOBACK":
                current_structure.statements.append(GoBackStatement(statement))
                continue

            current_structure.statements.append(LineStatement(statement))
        return current_structure
    
    def evaluate(self, programm):
        if self.typePerform == "UNTIL":
            # Tant que la condition n'est pas vérifiée, on exécute les statements du perform
            while True:
                for st in self.statements:
                    st.evaluate(programm)
                # Après avoir exécuté les statements, on vérifie la condition
                if self.evaluate_condition(programm):
                    break
            return
        for st in self.statements:
            st.evaluate(programm)
