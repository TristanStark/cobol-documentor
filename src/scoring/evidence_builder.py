from __future__ import annotations

from collections import defaultdict

from src.domain.models import CobolVariable, MeaningEvidence, NearbyComment, VariableUsage
from src.scoring.comment_classifier import CommentClassifier
from src.scoring.normalizer import CobolNameNormalizer


class VariableEvidenceBuilder:
    def __init__(self) -> None:
        self._comment_classifier = CommentClassifier()
        self._normalizer = CobolNameNormalizer()

    def build(
        self,
        variable: CobolVariable,
        usages: list[VariableUsage],
        comments: list[NearbyComment],
    ) -> tuple[list[str], list[str], list[MeaningEvidence]]:
        normalized_tokens = self._normalizer.normalize_tokens(variable.name)
        semantic_tags = self._normalizer.infer_semantic_tags(variable.name, variable.parent_name)
        evidence: list[MeaningEvidence] = []

        if normalized_tokens:
            evidence.append(
                MeaningEvidence(
                    source="name",
                    score=0.22,
                    label="lexical_name",
                    details=f"Name tokens inferred from '{variable.name}': {', '.join(normalized_tokens)}.",
                )
            )

        if variable.parent_name:
            parent_tokens = self._normalizer.normalize_tokens(variable.parent_name)
            evidence.append(
                MeaningEvidence(
                    source="parent",
                    score=0.15,
                    label="hierarchical_context",
                    details=f"Parent/group context '{variable.parent_name}' suggests: {', '.join(parent_tokens)}.",
                )
            )

        for condition in variable.conditions_88:
            evidence.append(
                MeaningEvidence(
                    source="condition88",
                    score=0.30,
                    label="enumerated_values",
                    details=f"Level 88 '{condition.name}' defines values {condition.values}.",
                    metadata={"condition_name": condition.name, "values": condition.values},
                )
            )

        for comment in comments:
            classification = self._comment_classifier.classify(comment.text)
            if classification == "doc_comment":
                score = max(0.10, 0.35 - (0.03 * max(comment.distance - 1, 0)))
                evidence.append(
                    MeaningEvidence(
                        source="comment",
                        score=score,
                        label="adjacent_comment",
                        details=f"Nearby documentation comment: {comment.text.strip()}",
                        metadata={"distance": comment.distance, "position": comment.position},
                    )
                )
            elif classification == "commented_out_code":
                evidence.append(
                    MeaningEvidence(
                        source="comment",
                        score=-0.20,
                        label="commented_code_penalty",
                        details="Nearby comment resembles disabled COBOL code and is down-weighted.",
                    )
                )

        grouped_usages: dict[str, list[VariableUsage]] = defaultdict(list)
        for usage in usages:
            grouped_usages[usage.usage_type].append(usage)

        evidence.extend(self._build_usage_evidence(grouped_usages))
        return normalized_tokens, semantic_tags, evidence

    def _build_usage_evidence(self, grouped_usages: dict[str, list[VariableUsage]]) -> list[MeaningEvidence]:
        evidence: list[MeaningEvidence] = []

        usage_weights = {
            "sql_into": (0.28, "sql_mapping"),
            "sql_where": (0.26, "sql_filter"),
            "file_key": (0.27, "file_key_usage"),
            "display": (0.14, "display_usage"),
            "if_compare": (0.18, "conditional_usage"),
            "compute": (0.18, "computed_value"),
            "call_using": (0.16, "parameter_usage"),
            "read_into": (0.20, "read_usage"),
            "write_from": (0.20, "write_usage"),
        }

        for usage_type, usages in grouped_usages.items():
            if usage_type not in usage_weights:
                continue
            score, label = usage_weights[usage_type]
            linked_entities = sorted({u.linked_entity for u in usages if u.linked_entity})
            literals = sorted({lit for u in usages for lit in u.literals})
            snippet = usages[0].snippet.strip()
            details = f"Observed {usage_type} usage. Example: {snippet}"
            if linked_entities:
                details += f" Linked entities: {', '.join(linked_entities)}."
            if literals:
                details += f" Observed literals: {', '.join(literals)}."
            evidence.append(
                MeaningEvidence(
                    source="usage",
                    score=score,
                    label=label,
                    details=details,
                    metadata={
                        "usage_type": usage_type,
                        "count": len(usages),
                        "linked_entities": linked_entities,
                        "literals": literals,
                    },
                )
            )
        return evidence
