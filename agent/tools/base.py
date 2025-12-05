"""
Base classes for tool plugins.

Tools are simple, self-contained actions that the model can request
via JSON instructions. Each tool validates its input, performs the
requested action, and returns a string result. Tools are registered
in a `ToolRegistry` for lookup by name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Tool:
    """
    Represents a tool that the agent can invoke.

    Each tool has a name and a human-readable description. The `run`
    method must be implemented by subclasses to execute the tool with
    given input and return a result as a string.
    """

    name: str
    description: str

    def run(self, tool_input: Dict[str, Any]) -> str:
        raise NotImplementedError

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "Tool":
        raise NotImplementedError


class ToolRegistry:
    """
    Registers and retrieves tools by name.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        return list(self._tools.values())