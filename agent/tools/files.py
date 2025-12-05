"""
File tools for reading and writing files within a safe workspace.

These tools ensure that the agent can only access files inside a
configured root directory to prevent path traversal attacks. File
operations are text-based and limited in scope.
"""

import os
from typing import Any, Dict

from agent.tools.base import Tool


class ReadFileTool(Tool):
    """
    ReadFileTool reads a text file from a safe directory.

    Tool input schema:
    {
        "path": "relative/path/to/file.txt",
        "max_chars": 8000
    }
    """

    def __init__(self, root_dir: str) -> None:
        super().__init__(
            name="read_file",
            description=(
                "Read a text file from a safe workspace directory. "
                "Input: {\"path\": str, \"max_chars\": int}."
            ),
        )
        self.root_dir = os.path.abspath(root_dir)

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "ReadFileTool":
        root_dir = cfg.get("root_dir", "workspace")
        os.makedirs(root_dir, exist_ok=True)
        return cls(root_dir=root_dir)

    def run(self, tool_input: Dict[str, Any]) -> str:
        rel_path = tool_input.get("path", "")
        max_chars = int(tool_input.get("max_chars", 8000))
        if not rel_path:
            return "ReadFileTool: 'path' is required."
        abs_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
        if not abs_path.startswith(self.root_dir):
            return "ReadFileTool: access denied outside workspace root."
        if not os.path.exists(abs_path):
            return f"ReadFileTool: file '{rel_path}' does not exist."
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read(max_chars)
        except Exception as exc:  # noqa: BLE001
            return f"ReadFileTool: error reading file: {exc}"
        return content


class WriteFileTool(Tool):
    """
    WriteFileTool writes text to a file within a safe directory.

    Tool input schema:
    {
        "path": "relative/path/to/file.txt",
        "content": "string content",
        "overwrite": false
    }
    """

    def __init__(self, root_dir: str) -> None:
        super().__init__(
            name="write_file",
            description=(
                "Write text content to a file in the safe workspace directory. "
                "Input: {\"path\": str, \"content\": str, \"overwrite\": bool}."
            ),
        )
        self.root_dir = os.path.abspath(root_dir)

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "WriteFileTool":
        root_dir = cfg.get("root_dir", "workspace")
        os.makedirs(root_dir, exist_ok=True)
        return cls(root_dir=root_dir)

    def run(self, tool_input: Dict[str, Any]) -> str:
        rel_path = tool_input.get("path", "")
        content = tool_input.get("content", "")
        overwrite = bool(tool_input.get("overwrite", False))
        if not rel_path:
            return "WriteFileTool: 'path' is required."
        abs_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
        if not abs_path.startswith(self.root_dir):
            return "WriteFileTool: access denied outside workspace root."
        if os.path.exists(abs_path) and not overwrite:
            return "WriteFileTool: file already exists and overwrite is false."
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as exc:  # noqa: BLE001
            return f"WriteFileTool: error writing file: {exc}"
        return f"WriteFileTool: wrote {len(content)} characters to '{rel_path}'."