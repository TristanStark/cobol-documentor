from ast import List
from src.var import Variable, ZoneGroup

class MemoryStack:
    def __init__(self):
        self.stack: List[Variable] = []
        self._length = 0
        self.known_variables = []
        # Liste des opérations effectuées sur la pile de variables, pour le debug
        self.operation_history = []

    def compute(self) -> None:
        """
        Récupère le nom de chacune des variables connues dans la
         pile de variables, y compris les définitions 
         (pour les variables de niveau 88) et les variables imbriquées 
         (pour les zones groupées), 
         et les stocke dans la liste self.known_variables.
         Cette liste est utilisée pour vérifier l'existence d'une variable
         (lookup_table)
         """
        for var in self.stack:
            self.known_variables.extend(var.get_known_values())

    def length(self) -> int:
        """
        Calcule la longueur totale de la pile de variables, 
        en sommant la longueur de chaque variable dans la pile.
         La longueur d'une variable est calculée en comptant 1 pour 
         elle-même, plus celle de ses définitions 
         (pour les variables de niveau 88) et de ses variables imbriquées (pour les zones groupées).
         Renvoie la longueur totale de la pile de variables.
        """
        if self._length != 0:
            return self._length
        for var in self.stack:
            self._length += var.length()
        return self._length
    
    def __str__(self):
        s = ""
        for var in self.stack:
            s += f"{var.to_tree_string()}\n"
        return s

    def does_variable_exist(self, var_name: str) -> bool:
        """
        Vérifie si une variable existe dans la pile de variables, en commençant par les variables les plus récentes (en haut de la pile).
        Si la variable est trouvée, True est retourné. Sinon, False est retourné.
        """
        return var_name in self.known_variables

    def get_value(self, var_name: str):
        """
        Recherche la valeur d'une variable dans la pile de variables, en commençant par les variables les plus récentes (en haut de la pile).
        Si la variable est trouvée, sa valeur est retournée. Sinon, None est retourné.
        """
        if not self.does_variable_exist:
            raise ValueError(f"Variable '{var_name}' not found in stack. Cannot get value.")
        for var in self.stack:
            value = var.get_value(var_name)
            if value is not None:
                return value
        return None
    
    def set_value(self, var_name: str, value):
        """
        Met à jour la valeur d'une variable dans la pile de variables. Si la variable existe déjà, sa valeur est mise à jour. Sinon, une nouvelle variable est créée et ajoutée à la pile.
        """
        self.operation_history.append(f"SET_VALUE: {var_name} = {value}")
        if not self.does_variable_exist:
            raise ValueError(f"Variable '{var_name}' not found in stack. Cannot get value.")
        for var in self.stack:
            returned_value = var.set_value(var_name, value)
            if returned_value is not None:
                print(f"[!!!!!!]Variable '{var_name}' found in stack. Value updated to '{value}'.")
                return returned_value
        # Si la variable n'existe pas, c'est un immense problème et on plante
        raise ValueError(f"Variable '{var_name}' not found in stack. Cannot set value '{value}'.")

    @staticmethod
    def create_memory_stack(var_stack: list[str]) -> "MemoryStack":
        memory = MemoryStack()
        memory_stack: list[Variable] = []
        group_stack: list[tuple[int, ZoneGroup]] = []
        last_variable: Variable | None = None

        for line in var_stack:
            level = Variable.get_level(line)
            if level == 0:
                continue
            if level == 88:
                if last_variable is None:
                    raise ValueError(f"Variable with level 88 found without a parent variable: '{line}'")
                v = Variable(line)
                v.init()
                last_variable.definitions.append(v)
                continue

            if Variable.is_zone_groupe(line):
                v: Variable = ZoneGroup(line)
            else:
                v = Variable(line)
            v.init()

            while group_stack and group_stack[-1][0] >= level:
                group_stack.pop()

            if group_stack:
                group_stack[-1][1].variables.append(v)
            else:
                memory_stack.append(v)

            last_variable = v

            if isinstance(v, ZoneGroup):
                group_stack.append((level, v))

        memory.stack = memory_stack
        memory.compute()
        return memory

