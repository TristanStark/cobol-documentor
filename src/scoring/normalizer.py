from __future__ import annotations

import re

from src.utils.lexicon import ABBREVIATIONS, COMMON_PREFIXES, ROLE_KEYWORDS


class CobolNameNormalizer:
    def normalize_tokens(self, name: str) -> list[str]:
        parts = [part for part in re.split(r"[-_\s]+", name.upper()) if part]
        cleaned: list[str] = []
        for part in parts:
            if part in COMMON_PREFIXES and len(parts) > 1:
                continue
            cleaned.append(ABBREVIATIONS.get(part, part.lower()))
        return cleaned

    def infer_semantic_tags(self, name: str, parent_name: str | None = None) -> list[str]:
        tokens = self.normalize_tokens(name)
        if parent_name:
            tokens.extend(self.normalize_tokens(parent_name))

        tags: set[str] = set()
        lowered = set(tokens)
        for role, keywords in ROLE_KEYWORDS.items():
            if lowered.intersection(keywords):
                tags.add(role)

        if "customer" in lowered or "client" in lowered:
            tags.add("domain_customer")
        if "contract" in lowered:
            tags.add("domain_contract")
        if "file" in lowered or "record" in lowered:
            tags.add("technical_io")
        return sorted(tags)
