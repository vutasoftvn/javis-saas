from __future__ import annotations

import re
from typing import Optional

from agentos.knowledge.parsers.base import DocumentParser


class MarkdownParser(DocumentParser):
    """Parser for Markdown (.md) documents.
    
    Extracts structured plain text while preserving headings, section context,
    and lists for chunking.
    """

    def parse(self, content: str | bytes, filename: Optional[str] = None) -> str:
        if isinstance(content, bytes):
            text = content.decode("utf-8", errors="replace")
        else:
            text = str(content)

        text = text.strip()
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip HTML comments <!-- ... -->
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # Normalize multiple blank lines to double newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
