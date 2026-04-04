from __future__ import annotations

from src.domain.models import CobolVariable, MeaningEvidence, VariableDescription


class DescriptionGenerator:
    def generate(
        self,
        variable: CobolVariable,
        semantic_tags: list[str],
        evidence: list[MeaningEvidence],
    ) -> VariableDescription:
        short = self._build_short_description(variable, semantic_tags)
        technical = self._build_technical_description(variable, evidence)
        business = self._build_business_description(variable, semantic_tags, evidence)
        return VariableDescription(short=short, technical=technical, business=business)

    def _build_short_description(self, variable: CobolVariable, semantic_tags: list[str]) -> str:
        if "status" in semantic_tags:
            return "Status field."
        if "identifier" in semantic_tags:
            return "Identifier field."
        if "amount" in semantic_tags:
            return "Amount-related field."
        if "date" in semantic_tags:
            return "Date-related field."
        if "counter" in semantic_tags:
            return "Counter or quantity field."
        if variable.parent_name:
            return f"Field belonging to {variable.parent_name}."
        return "COBOL variable with inferred meaning."

    def _build_technical_description(self, variable: CobolVariable, evidence: list[MeaningEvidence]) -> str:
        parts: list[str] = []
        if variable.picture:
            parts.append(f"Declared as PIC {variable.picture}")
        if variable.value:
            parts.append(f"defaulting to {variable.value}")
        if variable.parent_name:
            parts.append(f"under group {variable.parent_name}")
        top_usage = next((e for e in sorted(evidence, key=lambda x: x.score, reverse=True) if e.source == "usage"), None)
        if top_usage:
            parts.append(f"with strong evidence from {top_usage.metadata.get('usage_type', 'usage')}")
        if not parts:
            return "Technical meaning could not yet be refined from declaration data alone."
        return ", ".join(parts) + "."

    def _build_business_description(self, variable: CobolVariable, semantic_tags: list[str], evidence: list[MeaningEvidence]) -> str:
        linked_entities: list[str] = []
        enum_names: list[str] = []
        for item in evidence:
            linked_entities.extend(item.metadata.get("linked_entities", []))
            condition_name = item.metadata.get("condition_name")
            if condition_name:
                enum_names.append(condition_name)

        fragments: list[str] = []
        if "domain_customer" in semantic_tags:
            fragments.append("Appears to belong to customer-oriented processing")
        if "domain_contract" in semantic_tags:
            fragments.append("Appears to belong to contract-oriented processing")
        if linked_entities:
            fragments.append(f"and is linked to {', '.join(sorted(set(linked_entities)))}")
        if enum_names:
            fragments.append(f"with explicit semantic states such as {', '.join(enum_names)}")

        if not fragments:
            return "Business meaning remains tentative and mostly inferred from naming and local structure."
        sentence = " ".join(fragments).strip()
        if not sentence.endswith("."):
            sentence += "."
        return sentence
