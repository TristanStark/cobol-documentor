#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Tuple

from .cobol_ast_nodes import Program
from .cobol_execution import PathState, perform_paragraph, parse_value
from .cobol_parser import CobolParser
from .ibm_preprocess import preprocess_ibm, keep_only_procedure_division


def parse_vars(kvs: Sequence[str]) -> Dict[str, Any]:
    """Convert CLI var assignments like 'A=1' into an uppercase environment map."""
    env: Dict[str, Any] = {}
    for kv in kvs:
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        env[k.strip().upper()] = parse_value(v.strip())
    return env


class EntryNotFound(Exception):
    def __init__(self, entry: str, available: Sequence[str]):
        super().__init__(entry)
        self.entry = entry
        self.available = available



def load_program(cbl: str, copy_dirs: Sequence[str], copy_exts: Sequence[str]) -> Program:
    """Read and preprocess a COBOL source file into a Program AST."""
    with open(cbl, "r", encoding="utf-8", errors="replace") as f:
        raw = f.readlines()
    lines = preprocess_ibm(raw, list(copy_dirs), list(copy_exts))
    lines = keep_only_procedure_division(lines)
    print("=== LINES GIVEN TO PARSER ===")
    for i, line in enumerate(lines[:40], 1):
        print(f"{i:03d}: {line}")
    return CobolParser(lines).parse()


def dedup_paths(paths: List[PathState]) -> List[PathState]:
    """Return only unique path states by comparing calls/decisions/flags signatures."""
    unique: List[PathState] = []
    seen = set()
    for p in paths:
        sig = json.dumps(
            {
                "calls": p.calls,
                "decisions": p.decisions,
                "flags": p.flags,
            },
            sort_keys=True,
            default=str,
        )
        if sig not in seen:
            seen.add(sig)
            unique.append(p)
    return unique


def trace_file(
    cbl: str,
    entry: str = "__IMPLICIT__",
    vars: Sequence[str] = (),
    copy_dirs: Sequence[str] = (),
    copy_exts: Sequence[str] = ("", ".cpy", ".CPY", ".copy", ".COPY"),
    max_steps: int = 3000,
    max_paths: int = 80,
) -> Tuple[str, List[PathState]]:
    """Run the tracer against a file and return the entry point plus unique paths."""
    prog = load_program(cbl, copy_dirs, copy_exts)
    entry = entry.upper() if entry else None

    if entry is None:
        # priorité à un vrai MAIN si présent
        preferred = ["0000-MAIN", "MAIN", "000-MAIN", "1000-MAIN"]
        for cand in preferred:
            if cand in prog.paragraphs:
                entry = cand
                break

        # sinon premier paragraphe réel
        if entry is None:
            real_paras = [p for p in prog.order if p != "__IMPLICIT__"]
            if real_paras:
                entry = real_paras[0]
            else:
                entry = "__IMPLICIT__"    
    if entry not in prog.paragraphs:
        raise EntryNotFound(entry, prog.order)
    init = PathState(env=parse_vars(vars))
    paths: List[PathState] = []
    perform_paragraph(prog, entry, init, max_steps, max_paths, paths)
    print("Paragraphs found:", prog.order)
    return entry, dedup_paths(paths)
