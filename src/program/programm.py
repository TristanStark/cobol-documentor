from typing import List
from src.memory_stack import MemoryStack
from src.statements import Statement


class Programm:
    def __init__(self, name: str):
        self.name = name
        self.callStack = []
        self.paragraphs: List[Statement] = []
        self.memory_stack: MemoryStack = MemoryStack()

    def evaluate(self):
        for paragraph in self.paragraphs:
            paragraph.evaluate(self)

    def parse(self):
        new_paragraphs = []
        for paragraph in self.paragraphs:
            new_paragraphs.append(paragraph.parse())
        self.paragraphs = new_paragraphs

    def __str__(self):
        """
        Affiche une représentation textuelle du programme, avec les variables et les paragraphes.
        """
        s = f"Programm(name={self.name}, Paragraphs={len(self.paragraphs)}, Variables={self.memory_stack.length()})"
        s += "\nVariables:\n"
        s += f"{self.memory_stack}"
        s += "\nParagraphs:\n"
        for paragraph in self.paragraphs:
            s += f"\n  {paragraph.to_tree_string()}"
        return s
    
