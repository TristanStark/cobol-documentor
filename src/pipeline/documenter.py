from __future__ import annotations

from collections import defaultdict

from src.domain.models import CobolVariable, NearbyComment, VariableDocumentation, VariableUsage
from src.scoring.confidence import ConfidenceScorer
from src.scoring.description_generator import DescriptionGenerator
from src.scoring.evidence_builder import VariableEvidenceBuilder


class AutomaticDocumenter:
    def __init__(self) -> None:
        self._evidence_builder = VariableEvidenceBuilder()
        self._description_generator = DescriptionGenerator()
        self._confidence_scorer = ConfidenceScorer()

    def document_variables(
        self,
        variables: list[CobolVariable],
        usages: list[VariableUsage] | None = None,
        comments: list[NearbyComment] | None = None,
    ) -> list[VariableDocumentation]:
        usages = usages or []
        comments = comments or []

        usages_by_var: dict[str, list[VariableUsage]] = defaultdict(list)
        for usage in usages:
            usages_by_var[usage.variable_name].append(usage)

        comments_by_var: dict[str, list[NearbyComment]] = defaultdict(list)
        for comment in comments:
            comments_by_var[comment.variable_name].append(comment)

        docs: list[VariableDocumentation] = []
        for variable in variables:
            normalized_tokens, semantic_tags, evidence = self._evidence_builder.build(
                variable,
                usages_by_var.get(variable.name, []),
                comments_by_var.get(variable.name, []),
            )
            description = self._description_generator.generate(variable, semantic_tags, evidence)
            confidence_score, confidence_level = self._confidence_scorer.score(evidence)
            docs.append(
                VariableDocumentation(
                    variable=variable,
                    normalized_tokens=normalized_tokens,
                    semantic_tags=semantic_tags,
                    evidence=sorted(evidence, key=lambda x: x.score, reverse=True),
                    description=description,
                    confidence_score=confidence_score,
                    confidence_level=confidence_level,
                )
            )
        return docs
