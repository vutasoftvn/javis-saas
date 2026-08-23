from pathlib import Path

import pytest

from agentos.skills.supply_chain.artifact_store import ArtifactAlreadyExistsError, ImmutableArtifactStore


def _make_source_skill(root: Path) -> Path:
    source_dir = root / "source"
    source_dir.mkdir()
    (source_dir / "manifest.yaml").write_text("id: x", encoding="utf-8")
    (source_dir / "SKILL.md").write_text("do it", encoding="utf-8")
    return source_dir


def test_store_copies_source_into_artifact_dir(tmp_path: Path):
    source_dir = _make_source_skill(tmp_path)
    store = ImmutableArtifactStore(tmp_path / "registry" / "skills")

    stored_dir = store.store("community.faq-writer", "4bc9a82c", source_dir)

    assert stored_dir == tmp_path / "registry" / "skills" / "community.faq-writer" / "4bc9a82c"
    assert (stored_dir / "manifest.yaml").read_text(encoding="utf-8") == "id: x"


def test_store_refuses_to_overwrite_existing_commit(tmp_path: Path):
    source_dir = _make_source_skill(tmp_path)
    store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    store.store("community.faq-writer", "4bc9a82c", source_dir)

    with pytest.raises(ArtifactAlreadyExistsError):
        store.store("community.faq-writer", "4bc9a82c", source_dir)
