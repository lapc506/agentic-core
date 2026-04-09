"""Context file imports — @file.md syntax for modular project instructions."""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class ContextImportResolver:
    MAX_DEPTH = 5
    IMPORT_PATTERN = re.compile(r"^@([\w./\-]+\.md)\s*$", re.MULTILINE)
    CODE_BLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)

    def __init__(self, base_dir: str = ".") -> None:
        self._base = Path(base_dir)
        self._resolved: set[str] = set()

    def resolve(self, content: str, depth: int = 0) -> str:
        if depth > self.MAX_DEPTH:
            logger.warning("Max import depth exceeded")
            return content

        # Remove code blocks to avoid matching @imports inside them
        code_blocks: list[str] = []

        def save_block(match: re.Match) -> str:
            code_blocks.append(match.group())
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        processed = self.CODE_BLOCK.sub(save_block, content)

        def replace_import(match: re.Match) -> str:
            path = match.group(1)
            abs_path = str((self._base / path).resolve())

            if abs_path in self._resolved:
                logger.warning("Circular import detected: %s", path)
                return f"<!-- circular import: {path} -->"

            self._resolved.add(abs_path)
            file_path = self._base / path
            if not file_path.exists():
                logger.warning("Import not found: %s", path)
                return f"<!-- import not found: {path} -->"

            imported = file_path.read_text()
            return self.resolve(imported, depth + 1)

        result = self.IMPORT_PATTERN.sub(replace_import, processed)

        # Restore code blocks
        for i, block in enumerate(code_blocks):
            result = result.replace(f"__CODE_BLOCK_{i}__", block)

        return result

    def get_import_tree(self, content: str) -> list[str]:
        self._resolved.clear()
        self.resolve(content)
        return sorted(self._resolved)

    def reset(self) -> None:
        self._resolved.clear()
