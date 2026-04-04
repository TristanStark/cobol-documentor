import os
from src.memory_stack import MemoryStack
from src.program.programm import Programm
from typing import List
from src.statements import Statement, ParagraphStatement
from src.condenser import condense_cobol_file
from src.program.programm_resolver import expand_program_with_copies

PROCEDURE_DIVISION = "PROCEDURE DIVISION"
WORKING_STORAGE_SECTION = "WORKING-STORAGE SECTION"
IDENTIFICATION_DIVISION = "IDENTIFICATION DIVISION"
ENVIRONMENT_DIVISION = "ENVIRONMENT DIVISION"
DATA_DIVISION = "DATA DIVISION"


def load_program(program_name: str) -> Programm:
    if not program_name.endswith('.cbl'):
        program_name += '.cbl'
    if not os.path.isfile(program_name):
        raise FileNotFoundError(f"Program file '{program_name}' not found.")
    programm = Programm(program_name)
    var_stack: List[str] = []
    inside: str | None = None
    current_line: int = 1
    extended_lines: List[str] = expand_program_with_copies(program_name)
    condensed_lines: List[str] = condense_cobol_file(extended_lines)
    current_paragraph: ParagraphStatement | None = None
    for line in condensed_lines:
        # print(f"PARSING NEW LINE: >{line}<")
        untouched_line = line.rstrip().replace('\r\n', '').replace('\n', '')
        line = line.upper().lstrip().replace('\r\n', '').replace('\n', '')
        current_line += 1
        if len(line) == 0:
            continue
        if line.startswith('IDENTIFICATION DIVISION'):
            inside = IDENTIFICATION_DIVISION
            continue
        if line.startswith('ENVIRONMENT DIVISION'):
            inside = ENVIRONMENT_DIVISION
            continue
        if line.startswith('WORKING-STORAGE SECTION'):
            inside = WORKING_STORAGE_SECTION
            continue
        if line.startswith('PROCEDURE DIVISION'):
            programm.memory_stack = MemoryStack.create_memory_stack(var_stack)
            inside = PROCEDURE_DIVISION
            continue
        if inside == WORKING_STORAGE_SECTION:
            var_stack.append(line)
            continue
        if inside != PROCEDURE_DIVISION:
            continue
        if untouched_line.startswith(' ') and untouched_line.count(' ') == 1:
            # C'est un paragraph
            #print(f"Found paragraph: '{line}' at line {current_line}")
            if current_paragraph is not None:
                #print(f"Adding paragraph with {len(current_paragraph.statements)} statements")
                programm.paragraphs.append(current_paragraph)
            current_paragraph = ParagraphStatement(statement=line)
            continue
        if current_paragraph is None:
            continue
        #if "1000-INIT" in current_paragraph.statement:
        #    break
        if not line == ".":
            current_paragraph.statements.append(Statement(type="line", statement=line))
    if current_paragraph is not None:
        programm.paragraphs.append(current_paragraph)
    #print(f"Loaded program '{programm.name}' with {len(programm.paragraphs)} paragraphs and {len(programm.memory_stack.stack)} variables.")
    return programm

                



