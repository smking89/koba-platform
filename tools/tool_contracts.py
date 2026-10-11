"""Tool Contract definitions (master spec section 6). A contract is the
only thing an agent (or the CLI) is allowed to know about a tool — it
never calls an adapter function directly. Each contract carries its own
input/output schema, capability requirements, and the list of callers
authorized to invoke it.
"""
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class ToolContract:
    tool_id: str
    name: str
    version: str
    implementation: Callable
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    required_capabilities: list = field(default_factory=list)   # tool names core.detection must confirm first
    allowed_callers: list = field(default_factory=lambda: ["cli"])
    timeout: Optional[float] = None
    required_artifact_types: list = field(default_factory=list)  # informational for now
    produced_artifact_types: list = field(default_factory=list)  # informational for now
