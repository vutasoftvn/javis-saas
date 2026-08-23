from __future__ import annotations

from typing import Optional

from agentos.knowledge.parsers.base import DocumentParser


class PlainTextParser(DocumentParser):
    """Parser for raw plain text files and documents."""

    def parse(self, content: str | bytes, filename: Optional[str] = None) -> str:
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace").strip()
        return str(content).strip()
