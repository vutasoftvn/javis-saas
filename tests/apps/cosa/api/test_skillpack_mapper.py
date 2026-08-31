from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from apps.cosa.api.skillpack_mapper import parse_skillpack_spec


def _write_minimal_pack(tmp_path: Path, *, omit: str | None = None) -> Path:
    pack_dir = tmp_path / "test-pack"
    pack_dir.mkdir()
    manifest: dict[str, object] = {
        "metadata": {
            "id": "test.pack",
            "name": "Test Pack",
            "version": "1.0.0",
            "description": "Test description",
        },
        "source": {"path": "skillpacks/test-pack"},
        "runtime": {"tools": []},
        "applicability": {
            "project_stages": ["P0_DISCOVERY"],
            "gates": [],
            "required_context": ["workspace"],
            "outputs": ["artifact"],
        },
        "autonomy": {"ceiling": "L0_OBSERVE", "side_effect_class": "R"},
        "evidence": {"min_source_refs": 0, "self_validation_forbidden": True},
        "quality": {
            "eval_suite": "evals/test-pack.yaml",
            "required_negative_cases": ["missing-workspace"],
        },
    }
    if omit:
        manifest.pop(omit)
    (pack_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (pack_dir / "SKILL.md").write_text(
        "---\nname: test-pack\ndescription: Test\n---\nInstructions.", encoding="utf-8"
    )
    return pack_dir


@pytest.mark.parametrize("omitted", ["applicability", "autonomy", "evidence", "quality"])
def test_mapper_rejects_missing_governance_metadata(tmp_path: Path, omitted: str) -> None:
    with pytest.raises(ValueError, match=omitted):
        parse_skillpack_spec(_write_minimal_pack(tmp_path, omit=omitted))
