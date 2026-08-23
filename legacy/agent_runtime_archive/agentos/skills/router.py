# agentos/skills/router.py
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional, Union

from agentos.core.policy import (
    PermissionClass,
    PermissionLevel,
    PolicyDecision,
    ToolPermission,
    ToolRiskLevel,
    evaluate_access,
)
from agentos.skills.manifest_schema import (
    SkillLifecycleStatus,
    SkillManifest,
    TrustTier,
)
from agentos.skills.registry import SkillRegistry

_TOKEN_PATTERN = re.compile(r"[\w\u00C0-\u1EF9]+", re.UNICODE)

_TRUST_WEIGHT: dict[TrustTier, float] = {
    TrustTier.T0: 1.0,
    TrustTier.T1: 0.8,
    TrustTier.T2: 0.5,
    TrustTier.T3: 0.1,
    TrustTier.T4: 0.0,
}


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_skill(goal: str, manifest: SkillManifest) -> float:
    """Score a skill's relevance to a goal text:
    Score = Relevance * 0.5 + Trust * 0.3 + EvalQuality * 0.2
    """
    goal_tokens = _tokenize(goal)
    if not goal_tokens:
        return 0.0

    intent_tokens: set[str] = set()
    for intent in manifest.capability.intents:
        intent_tokens |= _tokenize(intent)
    intent_tokens |= _tokenize(manifest.metadata.description)
    intent_tokens |= _tokenize(manifest.metadata.name)

    if not intent_tokens:
        return 0.0

    overlap = goal_tokens & intent_tokens
    if not overlap:
        return 0.0

    relevance = len(overlap) / len(goal_tokens)
    trust = _TRUST_WEIGHT.get(manifest.trust.tier, 0.0)
    eval_score = getattr(manifest.quality, "eval_score", 0.0)

    return relevance * 0.5 + trust * 0.3 + eval_score * 0.2


@dataclass
class SkillCandidate:
    manifest: SkillManifest
    score: float
    is_available: bool = True
    unavailable_reason: Optional[str] = None


def evaluate_skill_access(
    manifest: SkillManifest,
    *,
    role: Optional[str] = None,
    agent_permission_level: Optional[Union[PermissionLevel, str]] = None,
) -> tuple[bool, Optional[str]]:
    """Evaluate whether the given role/agent_permission_level is permitted to run this skill.
    Uses pure RBAC decision kernel evaluate_access().
    """
    if role is None:
        return True, None

    perm_level = (
        PermissionLevel(agent_permission_level)
        if isinstance(agent_permission_level, str)
        else (agent_permission_level or PermissionLevel.L2_DRAFT)
    )

    # Check risk level
    risk_level_str = (manifest.risk.level or "low").lower()
    try:
        risk_level = ToolRiskLevel(risk_level_str)
    except ValueError:
        risk_level = ToolRiskLevel.LOW

    # Check permissions required
    req_perms = manifest.permissions.required or []
    has_write = manifest.permissions.business_write or any(
        p in ("MODIFY_BUSINESS_DATA", "WRITE_WORKSPACE", "EXTERNAL_WRITE", "DELETE_DATA", "FINANCIAL_ACTION")
        for p in req_perms
    )

    tool_perm = ToolPermission.SCOPED_WRITE if has_write else ToolPermission.READ_ONLY

    decision = evaluate_access(
        role=role,
        agent_permission_level=perm_level,
        tool_risk_level=risk_level,
        tool_permission=tool_perm,
    )

    if decision == PolicyDecision.DENY:
        reason = f"Role '{role}' is denied permissions required by skill '{manifest.metadata.id}'"
        return False, reason

    return True, None


class SkillRouter:
    def __init__(self, registry: SkillRegistry, min_trust: TrustTier = TrustTier.T2) -> None:
        self._registry = registry
        self._min_trust = min_trust

    def select_candidates(
        self,
        goal: str,
        *,
        role: Optional[str] = None,
        agent_permission_level: Optional[Union[PermissionLevel, str]] = None,
        allowed_skills: Optional[list[str]] = None,
        domain: Optional[str] = None,
        allow_business_write: bool = False,
        min_trust: Optional[TrustTier] = None,
    ) -> list[SkillCandidate]:
        effective_min_trust = min_trust or self._min_trust
        trust_order = list(TrustTier)

        candidates: list[SkillCandidate] = []
        for record in self._registry.list(status=SkillLifecycleStatus.ACTIVE):
            manifest = record.manifest
            # Filter by allowed_skills if provided
            if allowed_skills is not None and manifest.metadata.id not in allowed_skills:
                continue
            # Filter by trust
            if trust_order.index(manifest.trust.tier) > trust_order.index(effective_min_trust):
                continue
            # Filter by domain
            if domain is not None and manifest.capability.domain != domain:
                continue
            # Filter by business write
            if manifest.permissions.business_write and not allow_business_write and role is None:
                continue

            score = score_skill(goal, manifest)
            if score <= 0.0:
                continue

            is_available, reason = evaluate_skill_access(
                manifest,
                role=role,
                agent_permission_level=agent_permission_level,
            )

            candidates.append(
                SkillCandidate(
                    manifest=manifest,
                    score=score,
                    is_available=is_available,
                    unavailable_reason=reason,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def select(
        self,
        goal: str,
        *,
        role: Optional[str] = None,
        agent_permission_level: Optional[Union[PermissionLevel, str]] = None,
        allowed_skills: Optional[list[str]] = None,
        domain: Optional[str] = None,
        allow_business_write: bool = False,
        min_trust: Optional[TrustTier] = None,
    ) -> Optional[SkillManifest]:
        candidates = self.select_candidates(
            goal=goal,
            role=role,
            agent_permission_level=agent_permission_level,
            allowed_skills=allowed_skills,
            domain=domain,
            allow_business_write=allow_business_write,
            min_trust=min_trust,
        )
        available = [c for c in candidates if c.is_available]
        if not available:
            return None
        return available[0].manifest
