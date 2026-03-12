from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class Node:
    pass

@dataclass
class Program(Node):
    paragraphs: Dict[str, 'Paragraph'] = field(default_factory=dict)
    order: List[str] = field(default_factory=list)

@dataclass
class Paragraph(Node):
    name: str
    body: List[Node] = field(default_factory=list)

@dataclass
class Stmt(Node):
    raw: str

@dataclass
class IfStmt(Node):
    cond: str
    then_body: List[Node] = field(default_factory=list)
    else_body: List[Node] = field(default_factory=list)

@dataclass
class EvaluateStmt(Node):
    expr: str
    whens: List[Tuple[str, List[Node]]] = field(default_factory=list)
    when_other: Optional[List[Node]] = None

@dataclass
class PerformStmt(Node):
    target: str
    target_thru: Optional[str] = None
    times: Optional[int] = None
    until: Optional[str] = None

@dataclass
class CallStmt(Node):
    target: str
    using: List[str] = field(default_factory=list)
    is_indirect: bool = False

@dataclass
class ZCallPgmStmt(Node):
    program_name: str
    using: List[str] = field(default_factory=list)

@dataclass
class GotoStmt(Node):
    target: str

@dataclass
class StopStmt(Node):
    pass

@dataclass
class ReadStmt(Node):
    file: str
    into: Optional[str] = None

@dataclass
class MoveStmt(Node):
    src: str
    dests: List[str]

@dataclass
class SetToStmt(Node):
    targets: List[str]
    value: str

@dataclass
class SetUpDownByStmt(Node):
    target: str
    direction: str
    by: str

@dataclass
class ComputeStmt(Node):
    target: str
    expr: str
