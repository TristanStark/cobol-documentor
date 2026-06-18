from __future__ import annotations

import re
from typing import Optional


_CLAUSE_KEYWORDS = {
    "ASCENDING",
    "BLANK",
    "COMP",
    "COMP-1",
    "COMP-2",
    "COMP-3",
    "COMP-4",
    "COMP-5",
    "COMPUTATIONAL",
    "COMPUTATIONAL-1",
    "COMPUTATIONAL-2",
    "COMPUTATIONAL-3",
    "COMPUTATIONAL-4",
    "COMPUTATIONAL-5",
    "DEPENDING",
    "DESCENDING",
    "DISPLAY",
    "INDEXED",
    "JUST",
    "JUSTIFIED",
    "OCCURS",
    "PACKED-DECIMAL",
    "PIC",
    "PICTURE",
    "REDEFINES",
    "SIGN",
    "SYNC",
    "SYNCHRONIZED",
    "TO",
    "USAGE",
    "VALUE",
    "VALUES",
    "WHEN",
}

_USAGE_KEYWORDS = {
    "BINARY",
    "COMP",
    "COMP-1",
    "COMP-2",
    "COMP-3",
    "COMP-4",
    "COMP-5",
    "COMPUTATIONAL",
    "COMPUTATIONAL-1",
    "COMPUTATIONAL-2",
    "COMPUTATIONAL-3",
    "COMPUTATIONAL-4",
    "COMPUTATIONAL-5",
    "DISPLAY",
    "INDEX",
    "PACKED-DECIMAL",
}


class Variable:
    """Represents one COBOL data declaration.

    The parser intentionally stays permissive: legacy COBOL data descriptions are
    often only partially standard, and this project needs to document them rather
    than reject them.  The object therefore captures the most useful clauses
    (`PIC`, `VALUE`, `REDEFINES`, `OCCURS`, `USAGE`) without pretending to be a
    complete COBOL compiler.
    """

    def __init__(self, statement: str):
        self.statement = statement
        self.value: Optional[str] = None
        self.name: Optional[str] = None
        self.number: Optional[str] = None
        self.type: Optional[str] = None
        self.pic: Optional[str] = None
        self.usage: Optional[str] = None
        self.redefines: Optional[str] = None
        self.occurs: Optional[str] = None
        self.occurs_min: Optional[int] = None
        self.occurs_max: Optional[int] = None
        self.depends_on: Optional[str] = None
        self.indexed_by: list[str] = []
        self.raw_clauses: dict[str, str] = {}
        self.is_group: bool = False
        self.definitions: list[Variable] = []
        self.variables: list[Variable] = []

    def length(self) -> int:
        """Return the number of declaration nodes below this variable."""
        length = 1
        for definition in self.definitions:
            length += definition.length()
        for variable in self.variables:
            length += variable.length()
        return length

    def get_known_values(self) -> list[str]:
        """Return every variable/condition name declared in this subtree."""
        values = []
        if self.name is not None:
            values.append(self.name)
        for definition in self.definitions:
            values.extend(definition.get_known_values())
        for variable in self.variables:
            values.extend(variable.get_known_values())
        return values

    def init(self) -> None:
        """Parse the raw COBOL declaration into structured fields.

        Supported examples include:
        - ``05 WS-NAME PIC X(30).``
        - ``05 WS-ALT REDEFINES WS-BASE PIC X(30).``
        - ``05 WS-ITEM OCCURS 1 TO 10 TIMES DEPENDING ON WS-COUNT.``
        - ``88 WS-OK VALUE 'Y'.``
        """
        tokens = self._tokenize(self.statement)
        if len(tokens) < 2:
            raise ValueError(f"Invalid variable declaration: '{self.statement}'")

        self.number = tokens[0]
        self.name = tokens[1]

        if self.number == "88":
            self.type = "condition"
            self.value = self._extract_value(tokens)
            self.raw_clauses = self._extract_raw_clauses(tokens)
            return

        self.redefines = self._token_after(tokens, "REDEFINES")
        self.pic = self._extract_pic(tokens)
        self.usage = self._extract_usage(tokens)
        self.value = self._extract_value(tokens)
        self._extract_occurs(tokens)
        self.indexed_by = self._extract_indexed_by(tokens)
        self.raw_clauses = self._extract_raw_clauses(tokens)

        self.is_group = self.pic is None
        self.type = "group" if self.is_group else self.pic

    def display(self) -> str:
        """Return a compact human-readable representation."""
        level = str(self.number) if self.number is not None else ""
        if level == "88":
            return self.statement.strip()

        parts = []
        if level:
            parts.append(level)
        if self.name:
            parts.append(self.name)
        if self.redefines:
            parts.extend(["REDEFINES", self.redefines])
        if self.is_group:
            parts.append("(GROUP)")
        elif self.pic:
            parts.append(f"PIC {self.pic}")
        if self.usage:
            parts.append(self.usage)
        if self.occurs:
            parts.append(f"OCCURS {self.occurs}")
        if self.value:
            parts.append(f"VALUE {self.value}")
        return " ".join(parts) if parts else self.statement.strip()

    def _children(self) -> list[Variable]:
        return self.definitions

    def to_tree_string(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        lines = [prefix + connector + self.display()]
        children = self._children() or []
        if children:
            new_prefix = prefix + ("    " if is_last else "│   ")
            for i, child in enumerate(children):
                lines.append(child.to_tree_string(new_prefix, i == len(children) - 1))
        return "\n".join(lines)

    def get_value(self, var_name: str):
        """Return the value associated with ``var_name`` in this subtree."""
        if self.name == var_name:
            return self.value
        for definition in self.definitions:
            if definition.name == var_name:
                return definition.value
        for variable in self.variables:
            value = variable.get_value(var_name)
            if value is not None:
                return value
        return None

    def set_value(self, var_name: str, value):
        """Update the value associated with ``var_name`` in this subtree."""
        if self.name == var_name:
            self.value = value
            return value
        for definition in self.definitions:
            if definition.name == var_name:
                definition.value = value
                return value
        for variable in self.variables:
            returned_value = variable.set_value(var_name, value)
            if returned_value is not None:
                return returned_value
        return None

    @staticmethod
    def get_level(statement: str) -> int:
        tokens = Variable._tokenize(statement)
        return int(tokens[0]) if tokens and tokens[0].isdigit() else 0

    @staticmethod
    def is_zone_groupe(statement: str) -> bool:
        """Return whether the declaration is a group item.

        Kept for backward compatibility with the existing codebase.  It now
        recognises grouped declarations even when they carry clauses such as
        ``REDEFINES`` or ``OCCURS``.
        """
        tokens = Variable._tokenize(statement)
        if len(tokens) < 2 or not tokens[0].isdigit() or tokens[0] == "88":
            return False
        return "PIC" not in (token.upper() for token in tokens) and "PICTURE" not in (
            token.upper() for token in tokens
        )

    @staticmethod
    def _tokenize(statement: str) -> list[str]:
        normalized = statement.strip().rstrip(".")
        if not normalized:
            return []
        return re.findall(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"|\S+", normalized)

    @staticmethod
    def _token_after(tokens: list[str], keyword: str) -> Optional[str]:
        keyword_upper = keyword.upper()
        for index, token in enumerate(tokens):
            if token.upper() == keyword_upper and index + 1 < len(tokens):
                return tokens[index + 1]
        return None

    @staticmethod
    def _find_keyword(tokens: list[str], *keywords: str) -> Optional[int]:
        wanted = {keyword.upper() for keyword in keywords}
        for index, token in enumerate(tokens):
            if token.upper() in wanted:
                return index
        return None

    @staticmethod
    def _collect_until_clause(tokens: list[str], start: int) -> list[str]:
        collected: list[str] = []
        for token in tokens[start:]:
            if collected and token.upper() in _CLAUSE_KEYWORDS:
                break
            collected.append(token)
        return collected

    def _extract_pic(self, tokens: list[str]) -> Optional[str]:
        index = self._find_keyword(tokens, "PIC", "PICTURE")
        if index is None or index + 1 >= len(tokens):
            return None
        pic_tokens = self._collect_until_clause(tokens, index + 1)
        return " ".join(pic_tokens) if pic_tokens else None

    def _extract_usage(self, tokens: list[str]) -> Optional[str]:
        usage_index = self._find_keyword(tokens, "USAGE")
        if usage_index is not None:
            start = usage_index + 1
            if start < len(tokens) and tokens[start].upper() == "IS":
                start += 1
            usage_tokens = self._collect_until_clause(tokens, start)
            return " ".join(usage_tokens) if usage_tokens else None

        for token in tokens[2:]:
            if token.upper() in _USAGE_KEYWORDS:
                return token.upper()
        return None

    def _extract_value(self, tokens: list[str]) -> Optional[str]:
        index = self._find_keyword(tokens, "VALUE", "VALUES")
        if index is None:
            return None
        start = index + 1
        if start < len(tokens) and tokens[start].upper() in {"IS", "ARE"}:
            start += 1
        value_tokens = self._collect_until_clause(tokens, start)
        return " ".join(value_tokens) if value_tokens else None

    def _extract_occurs(self, tokens: list[str]) -> None:
        index = self._find_keyword(tokens, "OCCURS")
        if index is None:
            return

        raw_tokens: list[str] = []
        position = index + 1
        while position < len(tokens):
            token = tokens[position]
            upper = token.upper()
            if raw_tokens and upper in {"PIC", "PICTURE", "VALUE", "VALUES", "REDEFINES", "USAGE"}:
                break
            raw_tokens.append(token)
            position += 1

        self.occurs = " ".join(raw_tokens) if raw_tokens else None

        if index + 1 >= len(tokens):
            return

        first_bound = self._parse_int(tokens[index + 1])
        if first_bound is None:
            return

        self.occurs_min = first_bound
        self.occurs_max = first_bound

        if index + 3 < len(tokens) and tokens[index + 2].upper() == "TO":
            max_bound = self._parse_int(tokens[index + 3])
            if max_bound is not None:
                self.occurs_max = max_bound

        depending_index = self._find_keyword(tokens, "DEPENDING")
        if depending_index is not None and depending_index + 2 < len(tokens):
            if tokens[depending_index + 1].upper() == "ON":
                self.depends_on = tokens[depending_index + 2]

    def _extract_indexed_by(self, tokens: list[str]) -> list[str]:
        indexed_index = self._find_keyword(tokens, "INDEXED")
        if indexed_index is None or indexed_index + 1 >= len(tokens):
            return []

        start = indexed_index + 1
        if tokens[start].upper() == "BY":
            start += 1

        index_tokens = self._collect_until_clause(tokens, start)
        return [token for token in index_tokens if token.upper() != "BY"]

    def _extract_raw_clauses(self, tokens: list[str]) -> dict[str, str]:
        clauses: dict[str, str] = {}
        for keyword in ("REDEFINES", "OCCURS", "PIC", "PICTURE", "USAGE", "VALUE", "VALUES"):
            index = self._find_keyword(tokens, keyword)
            if index is None:
                continue
            values = self._collect_until_clause(tokens, index + 1)
            clauses[keyword] = " ".join(values)
        return clauses

    @staticmethod
    def _parse_int(value: str) -> Optional[int]:
        try:
            return int(value)
        except ValueError:
            return None


class ZoneGroup(Variable):
    """COBOL group item, possibly carrying REDEFINES/OCCURS clauses."""

    def __init__(self, statement: str):
        super().__init__(statement)
        self.type = "group"
        self.is_group = True

    def _children(self) -> list[Variable]:
        children: list[Variable] = []
        if self.definitions:
            children.extend(self.definitions)
        if self.variables:
            children.extend(self.variables)
        return children
