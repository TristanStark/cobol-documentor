from __future__ import annotations

import re

COBOL_CODE_HINTS = {
    "MOVE", "IF", "PERFORM", "CALL", "OPEN", "READ", "WRITE", "REWRITE", "COMPUTE",
    "PIC", "VALUE", "SECTION", "DIVISION", "DISPLAY", "ACCEPT", "EXEC", "SQL"
}


class CommentClassifier:
    def classify(self, text: str) -> str:
        normalized = text.strip().lstrip("*>").lstrip("*").strip()
        upper = normalized.upper()

        if not normalized:
            return "unknown"

        token_hits = sum(1 for token in COBOL_CODE_HINTS if re.search(rf"\b{re.escape(token)}\b", upper))
        has_code_shape = bool(re.search(r"\bTO\b|\bFROM\b|\bTHRU\b|\bEND-IF\b|\bWHEN\b", upper))
        natural_language_hint = bool(re.search(r"[a-z]{3,} [a-z]{3,}", normalized.lower()))

        if token_hits >= 2 or (token_hits >= 1 and has_code_shape):
            return "commented_out_code"
        if natural_language_hint:
            return "doc_comment"
        if token_hits == 0:
            return "doc_comment"
        return "unknown"
