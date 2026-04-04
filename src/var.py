

class Variable:
    def __init__(self, statement):
        self.statement = statement
        self.value = None
        self.name = None
        # Le numéro de niveau de la variable, par exemple 01, 77, 05, etc.
        self.number = None
        # Le type peut être 'group' pour les variables de niveau 01 ou 77, ou un type de données pour les autres variables
        self.type = None
        # Les variables de niveau 88 sont des conditions associées à la variable précédente, elles n'ont pas de type ni de valeur propre, mais une définition qui est ajoutée à la variable précédente
        self.definitions = []
        # Pour les zones groupées, on peut avoir des variables imbriquées à l'intérieur
        self.variables = []

    def length(self) -> int:
        """
        Calcule la longueur totale de la variable, en comptant 1 pour elle-même, plus la longueur de ses définitions (pour les variables de niveau 88) et de ses variables imbriquées (pour les zones groupées).
        """
        length = 1
        for definition in self.definitions:
            length += definition.length()
        for variable in self.variables:
            length += variable.length()
        return length
    
    def get_known_values(self) -> list[str]:
        """
        Renvoie la liste des noms connus de la variable,
        y compris celles des définitions (pour les variables de niveau 88) et des variables imbriquées (pour les zones groupées).
        """
        values = []
        if self.name is not None:
            values.append(self.name)
        for definition in self.definitions:
            values.extend(definition.get_known_values())
        for variable in self.variables:
            values.extend(variable.get_known_values())
        return values

    def init(self):
        splits = self.statement.split(' ')
        splits = [s for s in splits if len(s) > 0]
        if len(splits) == 2:
            # C'est une zone groupée
            self.type = 'group'
            self.name = splits[1]
            self.number = splits[0]
            return
        
        if len(splits) < 3:
            raise ValueError(f"Invalid variable declaration: '{self.statement}'")
        self.number = splits[0]
        self.name = splits[1]
        # split 2 c'est PIC
        if self.number != '88':
            assert splits[2].upper() == 'PIC', f"Expected 'PIC' in variable declaration: '{self.statement}', instead got '{splits}'"
        self.type = splits[3]
        if len(splits) > 4:
            self.value = ' '.join(splits[4:])

    def display(self) -> str:
        level = str(self.number) if self.number is not None else ""
        if level == "88":
            return self.statement.strip()
        parts = []
        if level:
            parts.append(level)
        if self.name:
            parts.append(self.name)
        if self.type:
            if self.type == "group":
                parts.append("(GROUP)")
            else:
                parts.append(f"PIC {self.type}")
        if self.value:
            parts.append(self.value)
        return " ".join(parts) if parts else self.statement.strip()

    def _children(self):
        return self.definitions

    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        lines = [prefix + connector + self.display()]
        children = self._children() or []
        if children:
            new_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(children):
                lines.append(child.to_tree_string(new_prefix, i == len(children) - 1))
        return "\n".join(lines)

    def get_value(self, var_name: str):
        """
        Recherche la valeur d'une variable dans la pile de variables, 
        en commençant par les variables les plus récentes (en haut de la pile).
        Si la variable est trouvée, sa valeur est retournée. 
        Sinon, None est retourné (la variable n'est pas chez nous).
        """
        if self.name == var_name:
            return self.value
        for definition in self.definitions:
            if definition.name == var_name:
                return definition.value
        for variable in self.variables:
            if variable.get_value(var_name) is not None:
                return variable.get_value(var_name)
        return None
    
    def set_value(self, var_name: str, value):
        """
        Met à jour la valeur d'une variable dans la pile de variables. 
        Si la variable existe déjà, sa valeur est mise à jour. 
        Sinon, on return None (la variable n'est pas chez nous).
        """
        if self.name == var_name:
            self.value = value
            return value
        for definition in self.definitions:
            if definition.name == var_name:
                definition.value = value
                return value
        for variable in self.variables:
            if variable.set_value(var_name, value) is not None:
                return variable.set_value(var_name, value)
        return None

    @staticmethod
    def get_level(statement) -> int:
        splits = statement.split(' ')
        return int(splits[0]) if splits[0].isdigit() else 0

    @staticmethod
    def is_zone_groupe(statement) -> bool:
        splits = statement.split(' ')
        splits = [s for s in splits if len(s) > 0]
        return len(splits) == 2
    
class ZoneGroup(Variable):
    def __init__(self, statement):
        super().__init__(statement)
        self.type = 'group'

    def _children(self):
        children = []
        if self.definitions:
            children.extend(self.definitions)
        if self.variables:
            children.extend(self.variables)
        return children


