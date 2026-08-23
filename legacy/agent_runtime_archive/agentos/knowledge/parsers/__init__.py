from __future__ import annotations

from typing import Optional

from agentos.knowledge.models import KnowledgeSourceType
from agentos.knowledge.parsers.base import DocumentParser
from agentos.knowledge.parsers.markdown import MarkdownParser
from agentos.knowledge.parsers.plain_text import PlainTextParser


def get_parser(
    source_type: Optional[KnowledgeSourceType | str] = None,
    filename: Optional[str] = None,
) -> DocumentParser:
    """Resolve appropriate document parser based on source_type or file extension."""
    ext = (filename or "").lower().split(".")[-1] if filename and "." in filename else ""
    st_val = source_type.value if isinstance(source_type, KnowledgeSourceType) else str(source_type or "").upper()

    if ext in ("md", "markdown") or st_val in ("DOC", "WIKI", "POLICY", "MANUAL", "SPEC"):
        return MarkdownParser()
    return PlainTextParser()


__all__ = [
    "DocumentParser",
    "MarkdownParser",
    "PlainTextParser",
    "get_parser",
]
