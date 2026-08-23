from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DocumentParser(Protocol):
    """Interface for document format parsers converting raw content to text."""

    def parse(self, content: str | bytes, filename: Optional[str] = None) -> str:
        """Parse raw text or byte stream into clean plain text."""
        ...
