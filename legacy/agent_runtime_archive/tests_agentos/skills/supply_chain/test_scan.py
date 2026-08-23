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
from agentos.skills.supply_chain.scan import scan_manifest


def _make_manifest(
    *,
    business_write: bool = False,
    network: str = "none",
    risk_level: str = "low",
    tier: TrustTier = TrustTier.T0,
) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id="x", name="x", version="1.0.0", description="d"),
        publisher=SkillPublisher(name="community", type="community"),
        source=SkillSource(type="git", path="skills/x"),
        capability=SkillCapability(domain="core", category="general", intents=["x"]),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network=network, business_write=business_write),
        risk=SkillRisk(level=risk_level),
        trust=SkillTrust(tier=tier, security_scan="pending"),
        quality=SkillQuality(eval_score=0.5, success_rate=0.5),
    )


def test_scan_passes_low_risk_manifest():
    result = scan_manifest(_make_manifest())
    assert result.passed is True
    assert result.findings == []


def test_scan_flags_business_write_from_low_trust_tier():
    result = scan_manifest(_make_manifest(business_write=True, tier=TrustTier.T3))
    assert result.passed is False
    assert any("business_write" in f for f in result.findings)


def test_scan_flags_network_write_combined_with_business_write():
    result = scan_manifest(_make_manifest(business_write=True, network="write", tier=TrustTier.T0))
    assert result.passed is False


def test_scan_flags_high_risk_from_low_trust_publisher():
    result = scan_manifest(_make_manifest(risk_level="high", tier=TrustTier.T4))
    assert result.passed is False
