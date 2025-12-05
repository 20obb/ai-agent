"""
Shell command tool.

Executes shell commands in a restricted fashion. Only whitelisted
commands may be invoked, and commands are run in a safe working
directory. Use caution when enabling this tool, as it can still
pose security risks if misconfigured.
"""

import os
import shlex
import subprocess
from typing import Any, Dict, List

from agent.tools.base import Tool


class ShellCommandTool(Tool):
    """
    Execute a shell command in a restricted environment.

    Tool input schema:
    {
        "command": "ls -la",
        "timeout": 10
    }
    """

    def __init__(self, allowed_commands: List[str], working_dir: str) -> None:
        super().__init__(
            name="shell_command",
            description=(
                "Execute a shell command (very restricted). "
                "Input: {\"command\": str, \"timeout\": int}."
            ),
        )
        self.allowed_commands = allowed_commands
        self.working_dir = os.path.abspath(working_dir)
        os.makedirs(self.working_dir, exist_ok=True)

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "ShellCommandTool":
        allowed_commands = cfg.get("allowed_commands", ["ls", "echo"])
        working_dir = cfg.get("working_dir", "workspace")
        return cls(allowed_commands=allowed_commands, working_dir=working_dir)

    def run(self, tool_input: Dict[str, Any]) -> str:
        command = tool_input.get("command", "")
        timeout = int(tool_input.get("timeout", 10))
        if not command:
            return "ShellCommandTool: 'command' is required."
        parts = shlex.split(command)
        if not parts:
            return "ShellCommandTool: empty command after parsing."
        base = parts[0]
# If allowed_commands is empty or None -> no restriction
        if self.allowed_commands and base not in self.allowed_commands:
         return f"ShellCommandTool: command '{base}' is not allowed."


        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"ShellCommandTool: command timed out after {timeout} seconds."
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        output += f"Return code: {result.returncode}"
        return output