from .base_statement import Statement

class ZCallPgmStatement(Statement):
    def __init__(self, type="zcallpgm", statement=None):
        super().__init__(type, statement)
        verbs = statement.split(" ")
        if len(verbs) >= 4 and verbs[2].upper() == "USING":
            self.target_pgm = verbs[3]
            self.copies = verbs[4:]
        else:
            self.target_pgm = ""
            self.copies = []

    def display(self) -> str:
        return f"""CALLED: {self.target_pgm} with 
        {len(self.copies)} copies: {self.copies}"""