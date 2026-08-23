from __future__ import annotations

import pytest

from agentos.knowledge.models import KnowledgeSourceType
from agentos.knowledge.parsers import (
    DocumentParser,
    MarkdownParser,
    PlainTextParser,
    get_parser,
)


def test_plain_text_parser():
    parser = PlainTextParser()
    assert issubclass(PlainTextParser, DocumentParser)

    # String input
    assert parser.parse("  Hello world!  ") == "Hello world!"
    # Bytes input
    assert parser.parse(b"  Byte content \xc3\xa0  ") == "Byte content à"


def test_markdown_parser():
    parser = MarkdownParser()
    assert issubclass(MarkdownParser, DocumentParser)

    md_content = """# Title of Document
<!-- Hidden comment to ignore -->

This is paragraph 1.

## Section 2
- Item A
- Item B
"""
    parsed = parser.parse(md_content)
    assert "Hidden comment" not in parsed
    assert "# Title of Document" in parsed
    assert "## Section 2" in parsed
    assert "- Item A" in parsed


def test_get_parser_resolution():
    assert isinstance(get_parser(KnowledgeSourceType.POLICY), MarkdownParser)
    assert isinstance(get_parser(KnowledgeSourceType.DOC), MarkdownParser)
    assert isinstance(get_parser(filename="guide.md"), MarkdownParser)
    assert isinstance(get_parser(filename="data.txt"), PlainTextParser)
