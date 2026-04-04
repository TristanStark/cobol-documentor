from __future__ import annotations

from src.domain.models import VariableDocumentation


class MarkdownRenderer:
    def render(self, docs: list[VariableDocumentation]) -> str:
        lines: list[str] = ["# Automatic variable documentation", ""]
        for doc in docs:
            lines.append(f"## {doc.variable.name}")
            lines.append("")
            lines.append(f"- **Level**: {doc.variable.level}")
            lines.append(f"- **PIC**: {doc.variable.picture or 'unknown'}")
            lines.append(f"- **Parent**: {doc.variable.parent_name or 'none'}")
            lines.append(f"- **Semantic tags**: {', '.join(doc.semantic_tags) or 'none'}")
            lines.append(f"- **Confidence**: {doc.confidence_score:.2f} ({doc.confidence_level.value})")
            lines.append("")
            lines.append(f"**Short**: {doc.description.short}")
            lines.append("")
            lines.append(f"**Technical**: {doc.description.technical}")
            lines.append("")
            lines.append(f"**Business**: {doc.description.business}")
            lines.append("")
            lines.append("### Evidence")
            lines.append("")
            for item in sorted(doc.evidence, key=lambda x: x.score, reverse=True):
                lines.append(f"- `{item.source}` / `{item.label}` / score={item.score:+.2f}: {item.details}")
            lines.append("")
        return "\n".join(lines)
