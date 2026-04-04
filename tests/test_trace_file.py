from __future__ import annotations

from pathlib import Path

from src.cobol_ast_trace import load_program
from src.condenser import condense_cobol_text


def test_condense_expands_multitarget_statements() -> None:
    """The condenser should split MOVE/SET statements with multiple targets."""
    sample = "\n".join(
        [
            "       PROCEDURE DIVISION.",
            "       MAIN.",
            "           MOVE A TO B C.",
            "           SET FLAG1 FLAG2 TO TRUE.",
            "",
        ]
    )

    expected = [
        " PROCEDURE DIVISION.",
        " MAIN.",
        "     MOVE A TO B",
        "     MOVE A TO C.",
        "     SET FLAG1 TO TRUE",
        "     SET FLAG2 TO TRUE.",
    ]

    assert condense_cobol_text(sample) == expected


def test_load_program_parses_paragraphs_and_memory(tmp_path: Path) -> None:
    document = "\n".join(
        [
            "       IDENTIFICATION DIVISION.",
            "       PROGRAM-ID. SAMPLE.",
            "       DATA DIVISION.",
            "       WORKING-STORAGE SECTION.",
            "       77 WS-COUNTER PIC 9(02) VALUE 0.",
            "       PROCEDURE DIVISION.",
            "       MAIN-PARA.",
            "           MOVE 1 TO WS-COUNTER.",
            "           GOBACK.",
            "",
        ]
    )

    source = tmp_path / "sample.cbl"
    source.write_text(document)

    program = load_program(str(source))

    assert len(program.paragraphs) == 1
    paragraph = program.paragraphs[0]
    assert paragraph.statement == "MAIN-PARA."

    statements = [statement.statement for statement in paragraph.statements]
    assert statements == ["MOVE 1 TO WS-COUNTER.", "GOBACK."]
    assert program.memory_stack.does_variable_exist("WS-COUNTER")
