from __future__ import annotations

import re
from typing import List, Tuple


COBOL_VERBS = {
    "ACCEPT", "ADD", "CALL", "CANCEL", "CLOSE", "COMPUTE", "CONTINUE",
    "DELETE", "DISPLAY", "DIVIDE", "EVALUATE", "EXIT", "GO", "GOBACK",
    "IF", "INITIALIZE", "INSPECT", "MOVE", "MULTIPLY", "OPEN", "PERFORM",
    "READ", "REWRITE", "SEARCH", "SET", "SORT", "START", "STOP",
    "STRING", "SUBTRACT", "UNSTRING", "WRITE", "EXEC"
}

BLOCK_ENDERS = {
    "END-IF",
    "END-PERFORM",
    "END-EVALUATE",
    "END-READ",
    "END-WRITE",
    "END-REWRITE",
    "END-SEARCH",
    "END-START",
    "END-STRING",
    "END-UNSTRING",
    "END-CALL",
    "END-COMPUTE",
    "END-ADD",
    "END-SUBTRACT",
    "END-MULTIPLY",
    "END-DIVIDE",
}

MID_BLOCK_KEYWORDS = {
    "ELSE",
    "WHEN",
}

def is_mid_block_line(line: str) -> bool:
    stripped = collapse_internal_spaces(line).lstrip().upper()
    if not stripped:
        return False

    if stripped == "AT END" or stripped == "NOT AT END":
        return True

    first = stripped.split()[0]
    return first in MID_BLOCK_KEYWORDS

def is_block_ender_line(line: str) -> bool:
    stripped = collapse_internal_spaces(line).lstrip().upper()
    if not stripped:
        return False

    first = stripped.split()[0]
    return first in BLOCK_ENDERS

def strip_sequence_area(line: str) -> str:
    """
    Remove COBOL sequence number area only.
    Keep everything from column 7 onward exactly as-is, including leading spaces.
    """
    line = line.rstrip("\n")
    if len(line) >= 7:
        return line[6:]
    return line


def is_comment_line(original_line: str) -> bool:
    """
    Fixed-format COBOL comment line: '*' in indicator column (column 7 => index 6).
    """
    return len(original_line) >= 7 and original_line[6] == "*"


def collapse_internal_spaces(text: str) -> str:
    """
    Collapse repeated whitespace inside the text, but preserve leading indentation.
    Also trims trailing whitespace.
    Example:
        '    MOVE   A   TO   B   C'
    becomes:
        '    MOVE A TO B C'
    """
    if not text:
        return text

    leading = re.match(r"^\s*", text).group(0)
    body = text[len(leading):]
    body = re.sub(r"\s+", " ", body).rstrip()
    return leading + body


def get_indent(text: str) -> str:
    return re.match(r"^\s*", text).group(0)


def first_token_upper(text: str) -> str:
    stripped = text.lstrip()
    if not stripped:
        return ""
    return stripped.split()[0].upper()


def is_new_statement(line: str) -> bool:
    first = first_token_upper(line)
    if first in COBOL_VERBS or first in BLOCK_ENDERS:
        return True

    stripped = line.lstrip().upper()
    if stripped.startswith("EXEC "):
        return True

    return False

def is_label_or_header(line: str) -> bool:
    """
    Preserve labels/headers as standalone lines.
    Useful for later paragraph/section detection.

    Examples:
        IDENTIFICATION DIVISION.
        PROCEDURE DIVISION USING ...
        WORKING-STORAGE SECTION.
        MY-PARAGRAPH.
    """
    stripped = collapse_internal_spaces(line).lstrip()
    upper = stripped.upper()

    if not stripped:
        return False

    if upper.endswith(" DIVISION."):
        return True

    if upper.endswith(" SECTION."):
        return True

    # Paragraph/section-style label:
    # single token ending with '.'
    if stripped.endswith(".") and " " not in stripped[:-1]:
        return True

    return False


def ends_with_period(line: str) -> bool:
    return collapse_internal_spaces(line).rstrip().endswith(".")


def join_multiline_statements(lines: List[str]) -> List[str]:
    statements: List[str] = []
    current = ""

    for raw in lines:
        original = raw.rstrip("\n")

        if is_comment_line(original):
            continue

        line = strip_sequence_area(original)

        if not line.strip():
            continue

        normalized = collapse_internal_spaces(line)

        # Labels / divisions / sections
        if is_label_or_header(line):
            if current:
                statements.append(collapse_internal_spaces(current))
                current = ""
            statements.append(normalized)
            continue

        # END-IF / END-PERFORM / ...
        if is_block_ender_line(line):
            if current:
                statements.append(collapse_internal_spaces(current))
                current = ""
            statements.append(normalized)
            continue

        # ELSE / WHEN / WHEN OTHER
        if is_mid_block_line(line):
            if current:
                statements.append(collapse_internal_spaces(current))
                current = ""
            statements.append(normalized)
            continue

        # New normal statement
        if is_new_statement(line):
            if current:
                statements.append(collapse_internal_spaces(current))
            current = line.rstrip()
        else:
            if current:
                current = current.rstrip() + " " + line.lstrip()
            else:
                current = line.rstrip()

        if current and ends_with_period(current):
            statements.append(collapse_internal_spaces(current))
            current = ""

    if current:
        statements.append(collapse_internal_spaces(current))

    return statements

def split_trailing_period(text: str) -> Tuple[str, bool]:
    text = text.rstrip()
    has_period = text.endswith(".")
    if has_period:
        text = text[:-1].rstrip()
    return text, has_period


def expand_move(stmt: str) -> List[str]:
    """
    Expand:
        MOVE A TO B C D
    into:
        MOVE A TO B
        MOVE A TO C
        MOVE A TO D

    Preserves the leading indentation of the original statement.
    """
    indent = get_indent(stmt)
    stripped = stmt.lstrip()

    m = re.match(r"(?i)^MOVE\s+(.+?)\s+TO\s+(.+?)\s*$", stripped)
    if not m:
        return [stmt]

    source = m.group(1).strip()
    targets_raw = m.group(2).strip()
    targets_raw, has_period = split_trailing_period(targets_raw)

    targets = re.split(r"\s+", targets_raw)
    targets = [t for t in targets if t]

    if len(targets) <= 1:
        return [stmt]

    expanded = [f"{indent}MOVE {source} TO {target}" for target in targets]

    if has_period:
        expanded[-1] += "."

    return expanded


def expand_set(stmt: str) -> List[str]:
    """
    Expand:
        SET A B C TO TRUE
    into:
        SET A TO TRUE
        SET B TO TRUE
        SET C TO TRUE

    Preserves the leading indentation of the original statement.
    """
    indent = get_indent(stmt)
    stripped = stmt.lstrip()

    m = re.match(r"(?i)^SET\s+(.+?)\s+TO\s+(.+?)\s*$", stripped)
    if not m:
        return [stmt]

    lhs = m.group(1).strip()
    rhs = m.group(2).strip()
    rhs, has_period = split_trailing_period(rhs)

    items = re.split(r"\s+", lhs)
    items = [x for x in items if x]

    if len(items) <= 1:
        return [stmt]

    expanded = [f"{indent}SET {item} TO {rhs}" for item in items]

    if has_period:
        expanded[-1] += "."

    return expanded


def condense_statement(stmt: str) -> List[str]:
    """
    Condense to one line while preserving leading indentation.
    Then expand selected statement types.
    """
    stmt = collapse_internal_spaces(stmt)

    for expander in (expand_move, expand_set):
        expanded = expander(stmt)
        if expanded != [stmt]:
            return expanded

    return [stmt]


def condense_cobol_lines(lines: List[str]) -> List[str]:
    logical_statements = join_multiline_statements(lines)

    out_lines: List[str] = []
    for stmt in logical_statements:
        out_lines.extend(condense_statement(stmt))

    return out_lines


def condense_cobol_text(text: str) -> List[str]:
    lines = text.splitlines()
    return condense_cobol_lines(lines)


def condense_cobol_file(lines: List[str]) -> List[str]:
    '''Receive already-read COBOL file content as a list of lines.'''
    return condense_cobol_lines(lines)
