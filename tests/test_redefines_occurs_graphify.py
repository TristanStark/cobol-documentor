from __future__ import annotations

from src.export import export_program_to_graphify
from src.memory_stack import MemoryStack
from src.program.programm import Programm
from src.statements import Statement
from src.statements.paragraph_statement import ParagraphStatement
from src.statements.zcallpgm_statement import ZCallPgmStatement
from src.var import Variable


def test_variable_parses_redefines_and_occurs_clauses() -> None:
    redefined = Variable("05 WS-ALT REDEFINES WS-BASE PIC X(10).")
    redefined.init()

    assert redefined.name == "WS-ALT"
    assert redefined.pic == "X(10)"
    assert redefined.redefines == "WS-BASE"
    assert not redefined.is_group

    occurs = Variable("05 WS-ITEM OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT PIC X(05).")
    occurs.init()

    assert occurs.name == "WS-ITEM"
    assert occurs.pic == "X(05)"
    assert occurs.occurs == "1 TO 10 TIMES DEPENDING ON WS-COUNT"
    assert occurs.occurs_min == 1
    assert occurs.occurs_max == 10
    assert occurs.depends_on == "WS-COUNT"


def test_memory_stack_keeps_grouped_redefines_and_occurs_items() -> None:
    memory = MemoryStack.create_memory_stack(
        [
            "01 CUSTOMER-AREA.",
            " 05 WS-COUNT PIC 9(02).",
            " 05 WS-BASE PIC X(10).",
            " 05 WS-ALT REDEFINES WS-BASE PIC X(10).",
            " 05 WS-ITEMS OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT.",
            "  10 WS-ITEM-CODE PIC X(03).",
            "  10 WS-ITEM-AMOUNT PIC S9(7)V99 COMP-3.",
        ]
    )

    assert memory.does_variable_exist("CUSTOMER-AREA")
    assert memory.does_variable_exist("WS-ALT")
    assert memory.does_variable_exist("WS-ITEM-CODE")

    root = memory.stack[0]
    children_by_name = {child.name: child for child in root.variables}

    assert children_by_name["WS-ALT"].redefines == "WS-BASE"
    assert children_by_name["WS-ITEMS"].is_group
    assert children_by_name["WS-ITEMS"].occurs_min == 1
    assert children_by_name["WS-ITEMS"].occurs_max == 10
    assert children_by_name["WS-ITEMS"].depends_on == "WS-COUNT"
    assert children_by_name["WS-ITEMS"].variables[1].usage == "COMP-3"


def test_graphify_export_contains_cobol_edges() -> None:
    program = Programm("sample.cbl")
    program.memory_stack = MemoryStack.create_memory_stack(
        [
            "01 CUSTOMER-AREA.",
            " 05 WS-COUNT PIC 9(02).",
            " 05 WS-BASE PIC X(10).",
            " 05 WS-ALT REDEFINES WS-BASE PIC X(10).",
            " 05 WS-ITEMS OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT.",
            "  10 WS-ITEM-CODE PIC X(03).",
        ]
    )

    paragraph = ParagraphStatement("0000-MAIN.")
    paragraph.statements.append(Statement(type="line", statement="PERFORM 1000-INIT THRU 1999-END."))
    paragraph.statements.append(ZCallPgmStatement(statement="CALL 'ZCALLPGM' USING TARGET-PGM CPY-REQUEST."))
    paragraph.statements.append(Statement(type="line", statement="MOVE WS-ALT TO WS-COUNT."))
    program.paragraphs.append(paragraph)

    graph = export_program_to_graphify(program, source_file="sample.cbl")

    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = {(edge["source"], edge["target"], edge["relation"]) for edge in graph["edges"]}

    assert "program:sample" in nodes
    assert nodes["variable:ws-alt"]["redefines"] == "WS-BASE"
    assert nodes["variable:ws-items"]["occurs_min"] == 1
    assert nodes["variable:ws-items"]["occurs_max"] == 10

    assert ("variable:ws-alt", "variable:ws-base", "redefines") in edges
    assert ("variable:ws-items", "variable:ws-count", "occurs_depends_on") in edges
    assert any(edge[1] == "program:target-pgm" and edge[2] == "calls" for edge in graph["edges"])
    assert any(edge[1] == "paragraph:1000-init" and edge[2] == "performs" for edge in graph["edges"])
    assert any(edge[1] == "paragraph:1999-end" and edge[2] == "performs" for edge in graph["edges"])
    assert any(edge[1] == "variable:ws-alt" and edge[2] == "references" for edge in graph["edges"])
