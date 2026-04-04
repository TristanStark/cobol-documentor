from __future__ import annotations

from typing import Any

from src.domain.models import CobolVariable


class CobolAstAdapter:
    """
    Adapter placeholder.

    Replace this with a mapper from your existing parser output to Automatic-Doc domain models.
    The only hard requirement is to produce `CobolVariable`, `VariableUsage`, and `NearbyComment` objects.
    """

    def extract_variables(self, ast_root: Any) -> list[CobolVariable]:
        raise NotImplementedError("Implement extraction from your current AST format.")
