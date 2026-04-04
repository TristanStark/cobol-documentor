from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(slots=True)
class CobolVariable:
    name: str
    level: int
    picture: str | None = None
    value: str | None = None
    parent_name: str | None = None
    copybook_name: str | None = None
    redefines: str | None = None
    occurs: int | None = None
    source_file: str | None = None
    line: int | None = None
    children_names: list[str] = field(default_factory=list)
    conditions_88: list[Condition88] = field(default_factory=list)


@dataclass(slots=True)
class Condition88:
    name: str
    values: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CobolRoutine:
    name: str
    source_file: str | None = None
    line: int | None = None
    paragraph_type: str | None = None
    called_routines: list[str] = field(default_factory=list)
    variables_read: list[str] = field(default_factory=list)
    variables_written: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VariableUsage:
    variable_name: str
    usage_type: str
    snippet: str
    routine_name: str | None = None
    linked_entity: str | None = None
    literals: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NearbyComment:
    variable_name: str
    text: str
    distance: int
    position: str
    line: int | None = None


@dataclass(slots=True)
class MeaningEvidence:
    source: str
    score: float
    label: str
    details: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class VariableDescription:
    short: str
    technical: str
    business: str


@dataclass(slots=True)
class VariableDocumentation:
    variable: CobolVariable
    normalized_tokens: list[str]
    semantic_tags: list[str]
    evidence: list[MeaningEvidence]
    description: VariableDescription
    confidence_score: float
    confidence_level: ConfidenceLevel
