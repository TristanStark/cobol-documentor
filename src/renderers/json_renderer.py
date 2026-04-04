from __future__ import annotations

import json
from dataclasses import asdict

from src.domain.models import VariableDocumentation


class JsonRenderer:
    def render(self, docs: list[VariableDocumentation]) -> str:
        payload = [asdict(doc) for doc in docs]
        return json.dumps(payload, indent=2, ensure_ascii=False)
