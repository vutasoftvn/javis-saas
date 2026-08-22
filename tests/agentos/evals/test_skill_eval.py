import pytest

from agentos.evals.skill_eval import evaluate_skill_run
from agentos.skills.manifest import (
    SkillCapability,
    SkillManifest,
    SkillMetadata,
    SkillPermissions,
    SkillPublisher,
    SkillQuality,
    SkillRisk,
    SkillRuntime,
    SkillSource,
    SkillTrust,
    TrustTier,
)


def _make_manifest(*, eval_score: float, success_rate: float) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id="marketing.seo.keyword-research", name="Keyword Research", version="1.0.0", description="d"),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path="skillpacks/marketing/keyword-research"),
        capability=SkillCapability(domain="marketing", category="seo", intents=["keyword research"]),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=False),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=TrustTier.T0, security_scan="passed"),
        quality=SkillQuality(eval_score=eval_score, success_rate=success_rate),
    )


def test_evaluate_skill_run_raises_score_toward_one_on_success():
    manifest = _make_manifest(eval_score=0.5, success_rate=0.5)

    result = evaluate_skill_run(manifest, success=True, latency_seconds=1.2, sample_weight=0.2)

    assert result.skill_id == "marketing.seo.keyword-research"
    assert result.success is True
    assert result.updated_eval_score == pytest.approx(0.6)  # 0.5*0.8 + 1.0*0.2
    assert result.updated_success_rate == pytest.approx(0.6)


def test_evaluate_skill_run_lowers_score_toward_zero_on_failure():
    manifest = _make_manifest(eval_score=0.5, success_rate=0.5)

    result = evaluate_skill_run(manifest, success=False, latency_seconds=3.0, sample_weight=0.2)

    assert result.success is False
    assert result.updated_eval_score == 0.4  # 0.5*0.8 + 0.0*0.2
    assert result.updated_success_rate == 0.4


def test_evaluate_skill_run_does_not_mutate_the_input_manifest():
    manifest = _make_manifest(eval_score=0.5, success_rate=0.5)

    evaluate_skill_run(manifest, success=True, latency_seconds=1.0)

    assert manifest.quality.eval_score == 0.5
    assert manifest.quality.success_rate == 0.5


def test_evaluate_skill_run_rejects_out_of_range_sample_weight():
    manifest = _make_manifest(eval_score=0.5, success_rate=0.5)

    with pytest.raises(ValueError):
        evaluate_skill_run(manifest, success=True, latency_seconds=1.0, sample_weight=0.0)
    with pytest.raises(ValueError):
        evaluate_skill_run(manifest, success=True, latency_seconds=1.0, sample_weight=1.5)
