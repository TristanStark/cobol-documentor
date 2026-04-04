from .base_statement import Statement


class GoBackStatement(Statement):
    def __init__(self, type = "goback", statement = None):
        super().__init__(type, statement)
        self.typeStatement = "goback"

    def display(self) -> str:
        return "GOBACK STATEMENT"
    
    def evaluate(self):
        # GO BACK met fin à l'exécution du programme courant et retourne le 
        # contrôle au programme appelant.
        raise StopIteration("GO BACK statement executed. Ending program execution.")