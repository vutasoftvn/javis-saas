from pathlib import Path

from scripts.check_doc_links import check_doc_links


def test_checker_resolves_repo_links_with_a_code_line_suffix(tmp_path: Path) -> None:
    source = tmp_path / "services" / "company" / "example.ts"
    source.parent.mkdir(parents=True)
    source.write_text("export const example = true;\n")

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "notes.md").write_text(
        "See [example](/services/company/example.ts:12).\n"
    )

    assert check_doc_links(tmp_path) == 0
