from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.cobol_ast_nodes import (
    CallStmt,
    GotoStmt,
    MoveStmt,
    Paragraph,
    PerformStmt,
    Program,
    ReadStmt,
    SetToStmt,
)
from src.cobol_execution import PathState, Unknown, exec_nodes
from src.cobol_ast_trace import load_program, trace_file
from src.ibm_preprocess import expand_copybooks


def _cobol_program_lines(lines: Iterable[str]) -> str:
    padded = []
    for line in lines:
        padded.append(f"       {line}")
    return "\n".join(padded) + "\n"


def test_parser_discovers_paragraph_order(tmp_path: Path) -> None:
    program = _cobol_program_lines(
        [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. SIMPLE.",
            "PROCEDURE DIVISION.",
            "0000-MAIN.",
            "    PERFORM 1000-STEP THRU 1000-STEP.",
            "1000-STEP.",
            "    MOVE 1 TO RESULT.",
            "    GOBACK.",
        ]
    )

    path = tmp_path / "simple.cbl"
    path.write_text(program)

    prog = load_program(str(path), copy_dirs=[], copy_exts=[""])
    assert prog.order == ["0000-MAIN", "1000-STEP"]

    entry, paths = trace_file(str(path), entry=None)
    assert entry == "0000-MAIN"
    assert paths
    assert paths[0].flags == []


def test_trace_file_env_seeding_resolves_branches(tmp_path: Path) -> None:
    program = _cobol_program_lines(
        [
            "IDENTIFICATION DIVISION.",
            "PROGRAM-ID. BRANCH.",
            "PROCEDURE DIVISION.",
            "0000-MAIN.",
            "    IF SWITCH = 1.",
            "        MOVE 1 TO RESULT.",
            "    ELSE.",
            "        MOVE 0 TO RESULT.",
            "    END-IF.",
            "    GOBACK.",
        ]
    )

    path = tmp_path / "branch.cbl"
    path.write_text(program)

    _, unknown_paths = trace_file(str(path), entry=None)
    assert len(unknown_paths) == 2
    assert any("UNKNOWN_CONDITION" in path.flags for path in unknown_paths)

    _, seeded_paths = trace_file(str(path), entry=None, vars=["SWITCH=1"])
    assert len(seeded_paths) == 1
    assert seeded_paths[0].env.get("RESULT") == 1


def test_copybook_expansion_resolves_copies() -> None:
    copy_dirs = ["datas/CPY"]
    copy_exts = [".cpy"]
    expanded = expand_copybooks(["COPY SampleDataRow."], copy_dirs, copy_exts)
    assert any("struct-row" in line.lower() for line in expanded), "Expected copybook contents in output"

    unresolved = expand_copybooks(["COPY DOES-NOT-EXIST."], copy_dirs, copy_exts)
    assert "*UNRESOLVED_COPY* DOES-NOT-EXIST." in unresolved


def test_exec_nodes_tracks_move_set_read_call() -> None:
    prog = Program()
    main_body = [
        MoveStmt(src="1", dests=["TARGET"]),
        SetToStmt(targets=["FLAG"], value="2"),
        ReadStmt(file="INFILE", into="DATA"),
        CallStmt(target="'PGM'", using=["TARGET"]),
    ]
    prog.paragraphs["MAIN"] = Paragraph(name="MAIN", body=main_body)
    prog.order.append("MAIN")

    state = PathState(env={})
    paths: list[PathState] = []

    exec_nodes(prog, main_body, state, max_steps=50, max_paths=10, out_paths=paths)

    assert state.env["TARGET"] == 1
    assert state.env["FLAG"] == 2
    assert state.env["DATA"] is Unknown
    assert "UNKNOWN_FROM_READ" in state.flags
    assert any(call["target"] == "'PGM'" for call in state.calls)
    assert "EXTERNAL_CALL" in state.flags
    assert paths


def test_exec_nodes_goto_perform_updates_env() -> None:
    prog = Program()
    prog.paragraphs["MAIN"] = Paragraph(name="MAIN", body=[GotoStmt(target="JUMP")])
    prog.paragraphs["JUMP"] = Paragraph(name="JUMP", body=[PerformStmt(target="DO-STEP")])
    prog.paragraphs["DO-STEP"] = Paragraph(name="DO-STEP", body=[MoveStmt(src="5", dests=["VALUE"])])
    prog.order.extend(["MAIN", "JUMP", "DO-STEP"])

    state = PathState(env={})
    paths: list[PathState] = []

    exec_nodes(prog, prog.paragraphs["MAIN"].body, state, max_steps=50, max_paths=10, out_paths=paths)

    assert state.env["VALUE"] == 5
    assert any(dec["type"] == "GOTO" for dec in state.decisions)
    assert any(dec["type"] == "PERFORM" for dec in state.decisions)
    assert paths


def test_exec_nodes_respects_max_steps_limit() -> None:
    prog = Program()
    main_para = Paragraph(name="MAIN", body=[MoveStmt(src="1", dests=["X"])])
    prog.paragraphs["MAIN"] = main_para
    prog.order.append("MAIN")

    state = PathState(env={})
    state.steps = 1
    paths: list[PathState] = []

    exec_nodes(prog, main_para.body, state, max_steps=1, max_paths=10, out_paths=paths)

    assert "MAX_STEPS_REACHED" in state.flags
    assert len(paths) == 1


def test_exec_nodes_respects_max_paths_limit() -> None:
    prog = Program()
    main_para = Paragraph(name="MAIN", body=[MoveStmt(src="1", dests=["X"])])
    prog.paragraphs["MAIN"] = main_para
    prog.order.append("MAIN")

    state = PathState(env={})
    paths: list[PathState] = [PathState(env={}), PathState(env={})]

    exec_nodes(prog, main_para.body, state, max_steps=10, max_paths=2, out_paths=paths)

    assert len(paths) == 2
