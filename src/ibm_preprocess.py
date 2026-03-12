import os
import re
from typing import List, Optional

PARA_RE = re.compile(r"^\s*([A-Z0-9][A-Z0-9-]*)\.\s*$", re.IGNORECASE)

RESERVED_NON_PARAGRAPHS = {
    "END-IF",
    "END-EVALUATE",
    "END-EXEC",
    "ELSE",
    "WHEN",
    "GOBACK",
    "EXIT",
    "STOP",
    "RUN",
    "CONTINUE",
}

COPY_RE = re.compile(r"^\s*COPY\s+([A-Z0-9_.-]+)\s*\.?\s*$", re.IGNORECASE)

def is_paragraph_label(line: str) -> Optional[str]:
    m = PARA_RE.match(line)
    if not m:
        return None

    name = m.group(1).upper()

    if name in RESERVED_NON_PARAGRAPHS:
        return None

    return name

def ibm_strip_fixed_format(line: str) -> str:
    """Return the code that lives in columns 8-72 of an IBM fixed-format line."""
    ln = line.rstrip("\n")
    if len(ln) >= 7:
        indicator = ln[6:7]
        if indicator in ("*", "/"):
            return ""
    if len(ln) >= 8:
        code = ln[7:72] if len(ln) >= 72 else ln[7:]
        return code.rstrip()
    return ln.strip()


def normalize_line(line: str) -> str:
    """Remove inline *> comments and strip whitespace."""
    return re.sub(r"\*\>.*$", "", line).strip()


def is_blank_or_comment(line: str) -> bool:
    """Report whether the line is empty after stripping whitespace."""
    return not line.strip()


def find_copybook(copy_name: str, copy_dirs: List[str], exts: List[str]) -> Optional[str]:
    """Return the first existing copybook path matching the base name and extensions."""
    candidates = [copy_name]
    for ext in exts:
        candidates.append(copy_name + ext)
    variants = set()
    for c in candidates:
        variants.add(c)
        variants.add(c.upper())
        variants.add(c.lower())
    for d in copy_dirs:
        for v in variants:
            path = os.path.join(d, v)
            if os.path.isfile(path):
                return path
    return None


def expand_copybooks(
    lines: List[str],
    copy_dirs: List[str],
    copy_exts: List[str],
    max_depth: int = 30,
    _stack: Optional[List[str]] = None,
) -> List[str]:
    """Inline COPY statements recursively, honoring a maximum nesting depth."""
    if _stack is None:
        _stack = []
    if len(_stack) > max_depth:
        return lines

    out: List[str] = []
    for ln in lines:
        m = COPY_RE.match(ln)
        if not m:
            out.append(ln)
            continue

        name = m.group(1)
        path = find_copybook(name, copy_dirs, copy_exts)
        if path is None:
            out.append(f"*UNRESOLVED_COPY* {name}.")
            continue

        key = os.path.abspath(path)
        if key in _stack:
            out.append(f"*RECURSIVE_COPY* {name}.")
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = f.readlines()
        except Exception:
            out.append(f"*COPY_READ_ERROR* {name}.")
            continue

        inc: List[str] = []
        for r in raw:
            s = ibm_strip_fixed_format(r)
            if not s:
                continue
            s = normalize_line(s)
            if is_blank_or_comment(s):
                continue
            inc.append(s)

        out.extend(expand_copybooks(inc, copy_dirs, copy_exts, max_depth=max_depth, _stack=_stack + [key]))
    return out


def preprocess_ibm(raw_lines: List[str], copy_dirs: List[str], copy_exts: List[str]) -> List[str]:
    """Normalize a COBOL source file and expand COPYs when directories are provided."""
    lines: List[str] = []
    for r in raw_lines:
        s = ibm_strip_fixed_format(r)
        if not s:
            continue
        s = normalize_line(s)
        if is_blank_or_comment(s):
            continue
        lines.append(s)

    if copy_dirs:
        lines = expand_copybooks(lines, copy_dirs, copy_exts)
    return lines

def keep_only_procedure_division(lines: List[str]) -> List[str]:
    out = []
    in_proc = False

    for line in lines:
        u = line.upper().strip()

        if not in_proc:
            if u.startswith("PROCEDURE DIVISION"):
                in_proc = True
                out.append(line)
            continue

        out.append(line)

    return out