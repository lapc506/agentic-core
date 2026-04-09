"""Coding agent tool primitives — the 5 fundamental tools every coding agent needs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


class FileReadTool:
    """Read file contents with optional line range."""

    name = "read_file"

    async def execute(self, path: str, start_line: int = 0, end_line: int = 0) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        if not p.is_file():
            return {"error": f"Not a file: {path}"}

        lines = p.read_text().splitlines()
        if start_line or end_line:
            lines = lines[start_line:end_line or len(lines)]

        return {
            "content": "\n".join(lines),
            "total_lines": len(p.read_text().splitlines()),
            "path": str(p.resolve()),
        }


class FileEditTool:
    """Edit files using exact-match substring replacement."""

    name = "edit_file"

    async def execute(self, path: str, old_str: str, new_str: str) -> dict[str, Any]:
        p = Path(path)

        if not old_str:
            # Create new file or append
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                content = p.read_text() + new_str
            else:
                content = new_str
            p.write_text(content)
            return {"status": "OK", "action": "create" if not p.exists() else "append"}

        if not p.exists():
            return {"error": f"File not found: {path}"}

        content = p.read_text()
        count = content.count(old_str)

        if count == 0:
            return {"error": "old_str not found in file"}
        if count > 1:
            return {"error": f"old_str appears {count} times — must be unique"}

        content = content.replace(old_str, new_str, 1)
        p.write_text(content)
        return {"status": "OK", "action": "edit"}


class ListFilesTool:
    """List files in a directory with optional glob pattern."""

    name = "list_files"

    async def execute(self, path: str = ".", pattern: str = "*") -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return {"error": f"Directory not found: {path}"}

        files = sorted(str(f.relative_to(p)) for f in p.rglob(pattern) if f.is_file())
        return {"files": files[:200], "total": len(files), "truncated": len(files) > 200}


class CodeSearchTool:
    """Search code using ripgrep (or fallback to grep)."""

    name = "search_code"

    async def execute(self, pattern: str, path: str = ".", file_type: str = "") -> dict[str, Any]:
        cmd = ["rg", "--json", "-n", pattern, path]
        if file_type:
            cmd.extend(["-t", file_type])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = [l for l in result.stdout.strip().split("\n") if l]
            return {"matches": lines[:100], "total": len(lines), "truncated": len(lines) > 100}
        except FileNotFoundError:
            # Fallback to grep
            cmd = ["grep", "-rn", pattern, path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            lines = result.stdout.strip().split("\n")
            return {"matches": lines[:100], "total": len(lines)}
        except subprocess.TimeoutExpired:
            return {"error": "Search timed out after 30s"}


class BashTool:
    """Execute a bash command with timeout and output capture."""

    name = "bash"

    async def execute(self, command: str, timeout: int = 60) -> dict[str, Any]:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=timeout,
            )
            return {
                "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,
                "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                "exit_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "exit_code": -1}


# Registry of all coding primitives
CODING_TOOLS = [FileReadTool(), FileEditTool(), ListFilesTool(), CodeSearchTool(), BashTool()]
