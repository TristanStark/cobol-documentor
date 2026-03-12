import copy
import re
import ast as pyast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union

from .cobol_ast_nodes import (
    CallStmt,
    EvaluateStmt,
    GotoStmt,
    IfStmt,
    MoveStmt,
    PerformStmt,
    Program,
    ReadStmt,
    SetToStmt,
    SetUpDownByStmt,
    Stmt,
    StopStmt,
    ZCallPgmStmt,
    ComputeStmt
)

class _UnknownType:
    def __repr__(self):
        return "UNKNOWN"
    def __deepcopy__(self, memo):
        return self

Unknown = _UnknownType()

@dataclass
class PathState:
    env: Dict[str, Any]
    callstack: List[str] = field(default_factory=list)
    calls: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    steps: int = 0


def parse_value(v: str) -> Any:
    """Interpret CLI var assignments into bool/int/string heuristics."""
    v = v.strip()
    if re.fullmatch(r"(?i)true|false", v):
        return v.lower() == "true"
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    m = re.match(r"^(['\"])(.*)\\1$", v)
    if m:
        return m.group(2)
    return v


def eval_atom(token: str, env: Dict[str, Any]) -> Any:
    token = token.strip().upper()

    if not token:
        return Unknown

    if token in ("ZERO", "ZEROS", "ZEROES"):
        return 0

    if token in ("SPACE", "SPACES"):
        return ""

    if token in ("TRUE",):
        return True

    if token in ("FALSE",):
        return False

    if re.fullmatch(r"-?\d+", token):
        return int(token)

    m = re.match(r"^(['\"])(.*)\1$", token)
    if m:
        return m.group(2)

    return env.get(token, Unknown)

def safe_eval_arith(expr: str, env: Dict[str, Any]) -> Any:
    """Evaluate simple arithmetic expressions, returning Unknown on failure."""
    tokens = re.findall(r"[A-Z0-9-]+|\\d+|[()+\\-*/]", expr.upper())
    py_parts: List[str] = []
    for tok in tokens:
        if re.fullmatch(r"\\d+", tok):
            py_parts.append(tok)
        elif tok in ("+", "-", "*", "/", "(", ")"):
            py_parts.append(tok)
        else:
            val = env.get(tok, Unknown)
            if val is Unknown:
                return Unknown
            if not isinstance(val, (int, float, bool)):
                return Unknown
            py_parts.append(str(int(val) if isinstance(val, bool) else val))

    py_expr = " ".join(py_parts)
    try:
        tree = pyast.parse(py_expr, mode="eval")
        for node in pyast.walk(tree):
            if not isinstance(
                node,
                (
                    pyast.Expression,
                    pyast.BinOp,
                    pyast.UnaryOp,
                    pyast.Constant,
                    pyast.Add,
                    pyast.Sub,
                    pyast.Mult,
                    pyast.Div,
                    pyast.UAdd,
                    pyast.USub,
                ),
            ):
                return Unknown
        val = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})
        if isinstance(val, (int, float)):
            return int(val) if isinstance(val, bool) else val
        return Unknown
    except Exception:
        return Unknown


def eval_condition(cond: str, env: Dict[str, Any]) -> Union[bool, object]:
    """Evaluate comparison chains with AND/OR, yielding Unknown for indeterminate values."""
    s = cond.strip()
    if not s:
        return Unknown

    parts = re.split(r"\s+(AND|OR)\s+", s, flags=re.IGNORECASE)

    def eval_simple(chunk: str) -> Union[bool, object]:
        chunk = chunk.strip()
        if not chunk:
            return Unknown
        if chunk.upper().startswith("NOT "):
            r = eval_simple(chunk[4:])
            return Unknown if r is Unknown else (not bool(r))

        m = re.match(r"^\s*(\S+)\s*(=|<>|!=|>=|<=|>|<)\s*(\S+)\s*$", chunk)
        if m:
            left, op, right = m.group(1), m.group(2), m.group(3)
            lv = eval_atom(left, env)
            rv = eval_atom(right, env)
            if lv is Unknown or rv is Unknown:
                return Unknown
            try:
                if op == "=":
                    return lv == rv
                if op in ("<>", "!="):
                    return lv != rv
                if op == ">":
                    return lv > rv
                if op == "<":
                    return lv < rv
                if op == ">=":
                    return lv >= rv
                if op == "<=":
                    return lv <= rv
            except Exception:
                return Unknown
            return Unknown

        toks = chunk.split()
        if len(toks) == 1:
            v = eval_atom(toks[0], env)
            return Unknown if v is Unknown else bool(v)
        return Unknown

    val = eval_simple(parts[0])
    i = 1
    while i < len(parts):
        op = parts[i].upper()
        rhs = eval_simple(parts[i + 1])
        if val is Unknown or rhs is Unknown:
            if op == "AND":
                if val is False or rhs is False:
                    val = False
                else:
                    val = Unknown
            else:
                if val is True or rhs is True:
                    val = True
                else:
                    val = Unknown
        else:
            val = (bool(val) and bool(rhs)) if op == "AND" else (bool(val) or bool(rhs))
        i += 2
    return val


def eval_when(expr_val: Any, when_cond: str, env: Dict[str, Any]) -> Union[bool, object]:
    """Determine whether a WHEN clause matches the supplied EVALUATE expressionode."""
    wc = when_cond.strip()
    if wc.upper() == "OTHER":
        return Unknown
    if expr_val is Unknown:
        return Unknown

    m = re.match(r"^(\S+)\s+THRU\s+(\S+)$", wc, flags=re.IGNORECASE)
    if m:
        a = eval_atom(m.group(1), env)
        b = eval_atom(m.group(2), env)
        if a is Unknown or b is Unknown:
            return Unknown
        try:
            return a <= expr_val <= b
        except Exception:
            return Unknown

    parts = wc.split()
    if len(parts) == 1:
        v = eval_atom(parts[0], env)
        if v is Unknown:
            return Unknown
        return expr_val == v

    vals: List[Any] = []
    for p in parts:
        if p.upper() in ("OR", ","):
            continue
        v = eval_atom(p, env)
        if v is Unknown:
            return Unknown
        vals.append(v)
    return expr_val in vals


def set_unknown_from_external(stmt_raw_upper: str, state: PathState):
    """Mark the state whenever a statement likely depends on external data."""
    txt = " ".join(stmt_raw_upper.split())

    if "EXEC SQL" in txt:
        state.flags.append("EXTERNAL_DATA_DEPENDENCY")
        return

    if txt.startswith("READ "):
        state.flags.append("EXTERNAL_DATA_DEPENDENCY")
        return

    # éventuellement FETCH seulement si SQL
    if txt.startswith("FETCH "):
        state.flags.append("EXTERNAL_DATA_DEPENDENCY")
        return

def exec_nodes(prog: Program, nodes: List[Stmt], state: PathState, max_steps: int, max_paths: int, out_paths: List[PathState]):
    """Symbolically execute a node list while populating paths and respecting limits."""
    if len(out_paths) >= max_paths:
        return
    if state.steps >= max_steps:
        state.flags.append("MAX_STEPS_REACHED")
        out_paths.append(state)
        return

    idx = 0
    while idx < len(nodes):
        if len(out_paths) >= max_paths:
            return
        state.steps += 1
        node = nodes[idx]

        if isinstance(node, StopStmt):
            state.decisions.append({"type": "STOP"})
            out_paths.append(state)
            return

        if isinstance(node, Stmt):
            set_unknown_from_external(node.raw.upper(), state)
            idx += 1
            continue

        if isinstance(node, ReadStmt):
            if node.into:
                state.env[node.into.upper()] = Unknown
                state.flags.append("UNKNOWN_FROM_READ")
                state.decisions.append({"type": "READ", "file": node.file, "into": node.into, "value": "UNKNOWN"})
            else:
                state.flags.append("UNKNOWN_FROM_READ")
                state.decisions.append({"type": "READ", "file": node.file})
            idx += 1
            continue

        if isinstance(node, MoveStmt):
            v = eval_atom(node.src, state.env)
            for d in node.dests:
                state.env[d] = v
            state.decisions.append({"type": "MOVE", "src": node.src, "dests": node.dests, "value": ("UNKNOWN" if v is Unknown else v)})
            idx += 1
            continue

        if isinstance(node, SetToStmt):
            v = eval_atom(node.value, state.env)
            for t in node.targets:
                state.env[t] = v
            state.decisions.append({"type": "SET_TO", "targets": node.targets, "value": ("UNKNOWN" if v is Unknown else v), "raw_value": node.value})
            idx += 1
            continue

        if isinstance(node, SetUpDownByStmt):
            cur = state.env.get(node.target, Unknown)
            inc = eval_atom(node.by, state.env)
            if cur is Unknown or inc is Unknown or not isinstance(cur, (int, float)) or not isinstance(inc, (int, float)):
                state.env[node.target] = Unknown
                state.decisions.append({"type": "SET_UPDOWN_BY", "target": node.target, "direction": node.direction, "by": node.by, "result": "UNKNOWN"})
            else:
                res = cur + inc if node.direction == "UP" else cur - inc
                state.env[node.target] = res
                state.decisions.append({"type": "SET_UPDOWN_BY", "target": node.target, "direction": node.direction, "by": inc, "result": res})
            idx += 1
            continue

        if isinstance(node, ComputeStmt):
            val = safe_eval_arith(node.expr, state.env)
            state.env[node.target] = val
            state.decisions.append({"type": "COMPUTE", "target": node.target, "expr": node.expr, "value": ("UNKNOWN" if val is Unknown else val)})
            idx += 1
            continue

        if isinstance(node, ZCallPgmStmt):
            pgm = eval_atom(node.program_name, state.env)
            pgm_out = node.program_name if pgm is Unknown else pgm
            state.calls.append({"type": "ZCALLPGM", "program": pgm_out, "using": node.using})
            state.decisions.append({"type": "CALL", "callee": "ZCALLPGM", "program": pgm_out, "using": node.using})
            state.flags.append("EXTERNAL_CALL")
            idx += 1
            continue

        if isinstance(node, CallStmt):
            state.calls.append({"type": "CALL", "target": node.target, "using": node.using, "indirect": node.is_indirect})
            state.decisions.append({"type": "CALL", "target": node.target, "using": node.using, "indirect": node.is_indirect})
            state.flags.append("EXTERNAL_CALL")
            idx += 1
            continue

        if isinstance(node, GotoStmt):
            tgt = node.target.upper()
            state.decisions.append({"type": "GOTO", "target": tgt})
            perform_paragraph(prog, tgt, state, max_steps, max_paths, out_paths, as_goto=True)
            return

        if isinstance(node, PerformStmt):
            times = node.times if node.times is not None else 1
            cap = min(times, 3)

            if node.until:
                r = eval_condition(node.until, state.env)
                if r is Unknown:
                    s0 = copy.deepcopy(state)
                    s0.flags.append("UNKNOWN_CONDITION")
                    s0.decisions.append({"type": "PERFORM_UNTIL", "until": node.until, "branch": "SKIP", "target": (node.target, node.target_thru)})

                    s1 = copy.deepcopy(state)
                    s1.flags.append("UNKNOWN_CONDITION")
                    s1.decisions.append({"type": "PERFORM_UNTIL", "until": node.until, "branch": "DO_ONCE", "target": (node.target, node.target_thru)})
                    perform_target(prog, node, s1, max_steps, max_paths, out_paths, iterations=1)

                    state = s0
                    idx += 1
                    continue
                if r is True:
                    state.decisions.append({"type": "PERFORM_UNTIL", "until": node.until, "branch": "SKIP", "target": (node.target, node.target_thru)})
                    idx += 1
                    continue
                else:
                    state.decisions.append({"type": "PERFORM_UNTIL", "until": node.until, "branch": "DO_ONCE", "target": (node.target, node.target_thru)})
                    perform_target(prog, node, state, max_steps, max_paths, out_paths, iterations=1)
                    idx += 1
                    continue

            state.decisions.append({"type": "PERFORM", "target": (node.target, node.target_thru), "times": times, "executed": cap})
            perform_target(prog, node, state, max_steps, max_paths, out_paths, iterations=cap)
            idx += 1
            continue

        if isinstance(node, IfStmt):
            r = eval_condition(node.cond, state.env)
            if r is Unknown:
                s_then = copy.deepcopy(state)
                s_then.flags.append("UNKNOWN_CONDITION")
                s_then.decisions.append({"type": "IF", "cond": node.cond, "branch": "THEN", "unknown": True})
                exec_nodes(prog, node.then_body, s_then, max_steps, max_paths, out_paths)

                s_else = copy.deepcopy(state)
                s_else.flags.append("UNKNOWN_CONDITION")
                s_else.decisions.append({"type": "IF", "cond": node.cond, "branch": "ELSE", "unknown": True})
                exec_nodes(prog, node.else_body, s_else, max_steps, max_paths, out_paths)
                return
            else:
                branch = "THEN" if r else "ELSE"
                state.decisions.append({"type": "IF", "cond": node.cond, "branch": branch, "unknown": False})
                exec_nodes(prog, node.then_body if r else node.else_body, state, max_steps, max_paths, out_paths)
                idx += 1
                continue

        if isinstance(node, EvaluateStmt):
            expr_val = eval_atom(node.expr, state.env) if node.expr else Unknown
            matched_any = False

            for when_cond, body in node.whens:
                possible = eval_when(expr_val, when_cond, state.env)
                if possible is Unknown:
                    s = copy.deepcopy(state)
                    s.flags.append("UNKNOWN_CONDITION")
                    s.decisions.append({"type": "EVALUATE", "expr": node.expr, "when": when_cond, "possible": "UNKNOWN"})
                    exec_nodes(prog, body, s, max_steps, max_paths, out_paths)
                    matched_any = True
                elif possible is True:
                    matched_any = True
                    state.decisions.append({"type": "EVALUATE", "expr": node.expr, "when": when_cond, "possible": True})
                    exec_nodes(prog, body, state, max_steps, max_paths, out_paths)
                    return
                else:
                    continue

            if not matched_any:
                if node.when_other is not None:
                    state.decisions.append({"type": "EVALUATE", "expr": node.expr, "when": "OTHER", "possible": True})
                    exec_nodes(prog, node.when_other, state, max_steps, max_paths, out_paths)
                    return
                else:
                    state.decisions.append({"type": "EVALUATE", "expr": node.expr, "when": "NO_MATCH"})
                    idx += 1
                    continue

            return

        idx += 1

    out_paths.append(state)


def perform_target(prog: Program, perform_stmt: PerformStmt, state: PathState, max_steps: int, max_paths: int, out_paths: List[PathState], iterations: int):
    """Invoke a paragraph range or repeated paragraph based on a PERFORM statement."""
    if perform_stmt.target_thru:
        run_thru(prog, perform_stmt.target, perform_stmt.target_thru, state, max_steps, max_paths, out_paths, iterations)
    else:
        for _ in range(iterations):
            perform_paragraph(prog, perform_stmt.target, state, max_steps, max_paths, out_paths)


def run_thru(prog: Program, start: str, end: str, state: PathState, max_steps: int, max_paths: int, out_paths: List[PathState], iterations: int):
    """Run all paragraphs between two labels in order, updating the state each iteration."""
    start_key = start.upper()
    end_key = end.upper()
    if start_key not in prog.order or end_key not in prog.order:
        state.flags.append("UNKNOWN_PERFORM_THRU_RANGE")
        state.decisions.append({"type": "PERFORM_THRU", "start": start_key, "end": end_key, "status": "MISSING_LABEL"})
        return
    i0 = prog.order.index(start_key)
    i1 = prog.order.index(end_key)
    if i1 < i0:
        state.flags.append("PERFORM_THRU_REVERSED")
        i0, i1 = i1, i0

    paragraph_sequence = prog.order[i0:i1 + 1]
    for _ in range(iterations):
        for paragraph_key in paragraph_sequence:
            perform_paragraph(prog, paragraph_key, state, max_steps, max_paths, out_paths)


def perform_paragraph(prog: Program, para_name: str, state: PathState, max_steps: int, max_paths: int, out_paths: List[PathState], as_goto: bool = False):
    """Execute a named paragraph, checking for missing labels and recursion limits."""
    paragraph_key = para_name.upper()
    if paragraph_key not in prog.paragraphs:
        state.flags.append(f"UNKNOWN_PARAGRAPH:{paragraph_key}")
        state.decisions.append({"type": "GOTO" if as_goto else "PERFORM", "target": paragraph_key, "status": "MISSING"})
        return

    if state.callstack.count(paragraph_key) > 5:
        state.flags.append("RECURSION_LIMIT")
        return

    state.callstack.append(paragraph_key)
    exec_nodes(prog, prog.paragraphs[paragraph_key].body, state, max_steps, max_paths, out_paths)
    if state.callstack and state.callstack[-1] == paragraph_key:
        state.callstack.pop()
