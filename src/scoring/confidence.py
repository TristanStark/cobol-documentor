from __future__ import annotations

from src.domain.models import ConfidenceLevel, MeaningEvidence


class ConfidenceScorer:
    def score(self, evidence: list[MeaningEvidence]) -> tuple[float, ConfidenceLevel]:
        total = sum(item.score for item in evidence)
        bounded = min(1.0, max(0.0, total))
        if bounded >= 0.70:
            return bounded, ConfidenceLevel.HIGH
        if bounded >= 0.40:
            return bounded, ConfidenceLevel.MEDIUM
        return bounded, ConfidenceLevel.LOW
