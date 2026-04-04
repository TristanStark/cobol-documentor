from automatic_doc.domain.models import CobolVariable, Condition88, NearbyComment, VariableUsage
from automatic_doc.pipeline.documenter import AutomaticDocumenter


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

    docs = AutomaticDocumenter().document_variables([variable], usages=usages, comments=comments)
    doc = docs[0]

    assert doc.confidence_score >= 0.70
    assert "status" in doc.semantic_tags
    assert "customer" in doc.description.business.lower()
