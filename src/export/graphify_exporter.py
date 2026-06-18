from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from src.program.programm import Programm
from src.statements import Statement
from src.statements.zcallpgm_statement import ZCallPgmStatement
from src.var import Variable

Graph = dict[str, list[dict[str, Any]]]


def export_program_to_graphify(program: Programm, *, source_file: str | None = None) -> Graph:
    """Return a Graphify-compatible graph for a parsed COBOL program."""
    graph: Graph = {"nodes": [], "edges": []}
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    program_label = Path(source_file or program.name).stem.upper()
    program_id = _id("program", program_label)
    _node(graph, seen_nodes, program_id, label=program_label, type="program", source_file=source_file or program.name)

    for variable in getattr(program.memory_stack, "stack", []) or []:
        variable_id = _export_variable(graph, seen_nodes, seen_edges, variable)
        _edge(graph, seen_edges, program_id, variable_id, "declares")

    known_variables = set(getattr(program.memory_stack, "known_variables", []) or [])

    for paragraph_index, paragraph in enumerate(program.paragraphs):
        paragraph_label = _clean(getattr(paragraph, "statement", f"paragraph-{paragraph_index}"))
        paragraph_id = _id("paragraph", f"{program_label}:{paragraph_label}:{paragraph_index}")
        _node(graph, seen_nodes, paragraph_id, label=paragraph_label, type="paragraph", source_file=source_file or program.name)
        _edge(graph, seen_edges, program_id, paragraph_id, "contains")

        for statement_index, statement in enumerate(_children(paragraph)):
            _export_statement(
                graph,
                seen_nodes,
                seen_edges,
                paragraph_id,
                statement,
                statement_index,
                known_variables,
                source_file or program.name,
            )

    return graph


def write_graphify_export(program: Programm, output_path: str | Path, *, source_file: str | None = None) -> Path:
    """Write the Graphify-compatible export as JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph = export_program_to_graphify(program, source_file=source_file)
    path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _export_variable(graph: Graph, seen_nodes: set[str], seen_edges: set[tuple[str, str, str]], variable: Variable) -> str:
    variable_name = variable.name or variable.statement
    variable_id = _id("variable", variable_name)
    _node(
        graph,
        seen_nodes,
        variable_id,
        label=variable_name,
        type="variable",
        level=variable.number,
        pic=variable.pic,
        usage=variable.usage,
        redefines=variable.redefines,
        occurs=variable.occurs,
        occurs_min=variable.occurs_min,
        occurs_max=variable.occurs_max,
        depends_on=variable.depends_on,
        is_group=variable.is_group,
    )

    if variable.redefines:
        target_id = _id("variable", variable.redefines)
        _node(graph, seen_nodes, target_id, label=variable.redefines, type="variable", inferred=True)
        _edge(graph, seen_edges, variable_id, target_id, "redefines")

    if variable.depends_on:
        target_id = _id("variable", variable.depends_on)
        _node(graph, seen_nodes, target_id, label=variable.depends_on, type="variable", inferred=True)
        _edge(graph, seen_edges, variable_id, target_id, "occurs_depends_on")

    for definition in variable.definitions:
        child_id = _export_variable(graph, seen_nodes, seen_edges, definition)
        _edge(graph, seen_edges, variable_id, child_id, "defines_condition")

    for child in variable.variables:
        child_id = _export_variable(graph, seen_nodes, seen_edges, child)
        _edge(graph, seen_edges, variable_id, child_id, "contains")

    return variable_id


def _export_statement(
    graph: Graph,
    seen_nodes: set[str],
    seen_edges: set[tuple[str, str, str]],
    parent_id: str,
    statement: Statement,
    statement_index: int,
    known_variables: set[str],
    source_file: str,
) -> str:
    raw = getattr(statement, "statement", "") or getattr(statement, "raw_text", "") or str(statement)
    statement_id = _id("statement", f"{parent_id}:{statement_index}:{raw}")
    statement_type = getattr(statement, "typeStatement", None) or statement.__class__.__name__.replace("Statement", "").lower()

    _node(graph, seen_nodes, statement_id, label=_short(raw), type="statement", statement_type=statement_type, source_file=source_file)
    _edge(graph, seen_edges, parent_id, statement_id, "contains")
    _semantic_edges(graph, seen_nodes, seen_edges, statement_id, statement, raw)

    for variable_name in _referenced_variables(raw, known_variables):
        variable_id = _id("variable", variable_name)
        _node(graph, seen_nodes, variable_id, label=variable_name, type="variable", inferred=True)
        _edge(graph, seen_edges, statement_id, variable_id, "references")

    for child_index, child in enumerate(_children(statement)):
        _export_statement(graph, seen_nodes, seen_edges, statement_id, child, child_index, known_variables, source_file)

    return statement_id


def _semantic_edges(graph: Graph, seen_nodes: set[str], seen_edges: set[tuple[str, str, str]], statement_id: str, statement: Statement, raw: str) -> None:
    upper = raw.strip().upper()

    if isinstance(statement, ZCallPgmStatement) or _is_zcallpgm(raw):
        target = getattr(statement, "target_pgm", None) or _zcallpgm_target(raw)
        if target:
            target_id = _id("program", target)
            _node(graph, seen_nodes, target_id, label=target, type="program", inferred=True)
            _edge(graph, seen_edges, statement_id, target_id, "calls")
        for copy_name in getattr(statement, "copies", []) or []:
            copy_id = _id("copy", copy_name)
            _node(graph, seen_nodes, copy_id, label=copy_name, type="copy", inferred=True)
            _edge(graph, seen_edges, statement_id, copy_id, "uses_copy_argument")
        return

    if upper.startswith("CALL "):
        target = _call_target(raw)
        if target:
            target_id = _id("program", target)
            _node(graph, seen_nodes, target_id, label=target, type="program", inferred=True)
            _edge(graph, seen_edges, statement_id, target_id, "calls")
        return

    if upper.startswith("PERFORM "):
        for target in _perform_targets(raw):
            target_id = _id("paragraph", target)
            _node(graph, seen_nodes, target_id, label=target, type="paragraph", inferred=True)
            _edge(graph, seen_edges, statement_id, target_id, "performs")
        return

    if upper.startswith("READ "):
        target = _first_operand(raw)
        if target:
            file_id = _id("file", target)
            _node(graph, seen_nodes, file_id, label=target, type="file", inferred=True)
            _edge(graph, seen_edges, statement_id, file_id, "reads_from")

    if upper.startswith("WRITE ") or upper.startswith("REWRITE "):
        target = _first_operand(raw)
        if target:
            file_id = _id("file", target)
            _node(graph, seen_nodes, file_id, label=target, type="file", inferred=True)
            _edge(graph, seen_edges, statement_id, file_id, "writes_to")


def _children(statement: Statement) -> Iterable[Statement]:
    for child in getattr(statement, "statements", []) or []:
        yield child
    for child in getattr(statement, "then_statements", []) or []:
        yield child
    for child in getattr(statement, "else_statements", []) or []:
        yield child
    for branch in getattr(statement, "whens", []) or []:
        for child in getattr(branch, "statements", []) or []:
            yield child
    for child in getattr(statement, "when_other", []) or []:
        yield child


def _id(kind: str, label: str) -> str:
    value = _clean(str(label)).lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value).strip("-") or "unknown"
    return f"{kind}:{value}"


def _node(graph: Graph, seen: set[str], node_id: str, **attrs: Any) -> None:
    if node_id in seen:
        return
    seen.add(node_id)
    graph["nodes"].append({"id": node_id, **{key: value for key, value in attrs.items() if value is not None}})


def _edge(graph: Graph, seen: set[tuple[str, str, str]], source: str, target: str, relation: str) -> None:
    key = (source, target, relation)
    if key in seen:
        return
    seen.add(key)
    graph["edges"].append({"source": source, "target": target, "relation": relation})


def _clean(value: str) -> str:
    return value.strip().rstrip(".")


def _short(value: str, max_length: int = 120) -> str:
    value = value.strip()
    return value if len(value) <= max_length else value[: max_length - 1] + "…"


def _is_zcallpgm(raw: str) -> bool:
    tokens = raw.strip().split()
    return len(tokens) >= 3 and tokens[0].upper() == "CALL" and tokens[1].strip("'\"").upper() == "ZCALLPGM"


def _zcallpgm_target(raw: str) -> str | None:
    tokens = raw.strip().split()
    if len(tokens) >= 4 and tokens[2].upper() == "USING":
        return tokens[3].strip("'\"")
    return None


def _call_target(raw: str) -> str | None:
    tokens = raw.strip().split()
    return tokens[1].strip("'\"") if len(tokens) >= 2 else None


def _perform_targets(raw: str) -> list[str]:
    tokens = raw.strip().rstrip(".").split()
    if len(tokens) < 2 or tokens[1].upper() in {"UNTIL", "VARYING", "TIMES"}:
        return []
    targets = [tokens[1]]
    for keyword in ("THRU", "THROUGH"):
        for index, token in enumerate(tokens):
            if token.upper() == keyword and index + 1 < len(tokens):
                targets.append(tokens[index + 1])
    return [_clean(target) for target in targets]


def _first_operand(raw: str) -> str | None:
    tokens = raw.strip().rstrip(".").split()
    return tokens[1] if len(tokens) >= 2 else None


def _referenced_variables(raw: str, variable_names: set[str]) -> list[str]:
    upper_raw = raw.upper()
    found: list[str] = []
    for variable_name in sorted(variable_names, key=len, reverse=True):
        pattern = rf"(?<![A-Z0-9-]){re.escape(variable_name.upper())}(?![A-Z0-9-])"
        if re.search(pattern, upper_raw):
            found.append(variable_name)
    return found
