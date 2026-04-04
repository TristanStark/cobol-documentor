from __future__ import annotations

from src.domain.models import (
    CobolVariable,
    Condition88,
    ConfidenceLevel,
    NearbyComment,
    VariableUsage,
)
from src.pipeline.documenter import AutomaticDocumenter


def test_documenter_generates_customer_status_doc() -> None:
    variable = CobolVariable(
        name="WS-CUST-STATUS",
        level=5,
        picture="X(01)",
        parent_name="CUSTOMER-RECORD",
        conditions_88=[
            Condition88(name="CUSTOMER-ACTIVE", values=["A"]),
            Condition88(name="CUSTOMER-SUSPENDED", values=["S"]),
        ],
    )

    usages = [
        VariableUsage(
            variable_name="WS-CUST-STATUS",
            usage_type="sql_into",
            snippet="SELECT CUSTOMER_STATUS INTO :WS-CUST-STATUS",
            linked_entity="CUSTOMER_STATUS",
        ),
        VariableUsage(
            variable_name="WS-CUST-STATUS",
            usage_type="if_compare",
            snippet="IF WS-CUST-STATUS = 'A'",
            literals=["A"],
        ),
    ]

    comments = [
        NearbyComment(
            variable_name="WS-CUST-STATUS",
            text="* Current status of the customer record",
            distance=1,
            position="before",
        )
    ]

    doc = AutomaticDocumenter().document_variables(
        [variable],
        usages=usages,
        comments=comments,
    )[0]

    assert doc.normalized_tokens == ["customer", "status"]
    assert "status" in doc.semantic_tags
    assert "domain_customer" in doc.semantic_tags
    assert doc.description.technical.startswith("Declared as PIC X(01)")
    assert "customer" in doc.description.business.lower()
    assert doc.confidence_level == ConfidenceLevel.HIGH
    assert any(e.source == "usage" for e in doc.evidence)


def test_documenter_penalizes_commented_out_code() -> None:
    variable = CobolVariable(name="WS-RESULT", level=5)
    comment = NearbyComment(
        variable_name="WS-RESULT",
        text="* MOVE WS-RESULT TO WS-OUT.",
        distance=2,
        position="before",
    )

    doc = AutomaticDocumenter().document_variables(
        [variable],
        comments=[comment],
    )[0]

    assert any(e.label == "commented_code_penalty" for e in doc.evidence)
