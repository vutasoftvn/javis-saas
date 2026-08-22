from __future__ import annotations

from pydantic import BaseModel, Field

from agentos.skills.manifest import SkillManifest, TrustTier

_HIGH_RISK_TRUST_TIERS = {TrustTier.T3, TrustTier.T4}


class ScanResult(BaseModel):
    passed: bool
    findings: list[str] = Field(default_factory=list)


def scan_manifest(manifest: SkillManifest) -> ScanResult:
    """Deterministic static scan + permission analysis (blueprint §27
    STATIC SCAN / PERMISSION ANALYSIS stages). Rule-based by design — no
    LLM call, so results are reproducible and auditable. A real static
    analyzer of skill *code* (not just declared manifest permissions) is
    later hardening.
    """
    findings: list[str] = []

    if manifest.permissions.business_write and manifest.trust.tier in _HIGH_RISK_TRUST_TIERS:
        findings.append("business_write permission requested by a low-trust-tier skill")

    if manifest.permissions.network == "write" and manifest.permissions.business_write:
        findings.append("combines network write and business_write — high blast radius")

    if manifest.risk.level == "high" and manifest.trust.tier in _HIGH_RISK_TRUST_TIERS:
        findings.append("declared high risk from a low-trust-tier publisher")

    return ScanResult(passed=len(findings) == 0, findings=findings)
