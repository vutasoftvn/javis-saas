# backend/tests/agentos/skills/test_manifest.py
import pytest
from pydantic import ValidationError

from agentos.skills.manifest import SkillManifest, TrustTier


def _minimal_manifest_dict() -> dict:
    return {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": "core.weekly-review", "name": "Weekly Review", "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": "skillpacks/core/weekly-review"},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }


def test_manifest_parses_from_canonical_dict():
    manifest = SkillManifest(**_minimal_manifest_dict())
    assert manifest.api_version == "agentos.ai/v1"
    assert manifest.metadata.id == "core.weekly-review"
    assert manifest.trust.tier == TrustTier.T0


def test_manifest_risk_level_defaults_to_low_when_omitted():
    data = _minimal_manifest_dict()
    data["risk"] = {}
    manifest = SkillManifest(**data)
    assert manifest.risk.level == "low"


def test_manifest_requires_metadata_id():
    data = _minimal_manifest_dict()
    del data["metadata"]["id"]
    with pytest.raises(ValidationError):
        SkillManifest(**data)
