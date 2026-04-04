from __future__ import annotations

import pytest

from src.domain.models import ConfidenceLevel, MeaningEvidence
from src.scoring.comment_classifier import CommentClassifier
from src.scoring.confidence import ConfidenceScorer
from src.scoring.normalizer import CobolNameNormalizer


@pytest.mark.parametrize(
    "name,expected_tokens",
    [
        ("WS-CUST-STATUS", ["customer", "status"]),
        ("LK-ACCOUNT-NBR", ["account", "number"]),
        ("CLI-ID", ["client", "identifier"]),
    ],
)
def test_normalizer_strips_prefixes_and_abbreviations(name: str, expected_tokens: list[str]) -> None:
    normalizer = CobolNameNormalizer()
    assert normalizer.normalize_tokens(name) == expected_tokens


def test_comment_classifier_separates_doc_and_code_comments() -> None:
    classifier = CommentClassifier()
    assert classifier.classify("* Current status of the customer") == "doc_comment"
    assert classifier.classify("* MOVE A TO B C.") == "commented_out_code"


@pytest.mark.parametrize(
    "scores,expected_level",
    [
        ([0.1, 0.05], ConfidenceLevel.LOW),
        ([0.25, 0.2], ConfidenceLevel.MEDIUM),
        ([0.25, 0.25, 0.25], ConfidenceLevel.HIGH),
    ],
)
def test_confidence_score_levels(scores: list[float], expected_level: ConfidenceLevel) -> None:
    scorer = ConfidenceScorer()
    evidence = [
        MeaningEvidence(source="test", score=score, label="test", details="rationale")
        for score in scores
    ]

    _, level = scorer.score(evidence)
    assert level == expected_level


def test_confidence_score_clamps_negative_scores() -> None:
    scorer = ConfidenceScorer()
    evidence = [MeaningEvidence(source="test", score=-0.5, label="negative", details="bad")]

    total, level = scorer.score(evidence)
    assert total == 0.0
    assert level == ConfidenceLevel.LOW
