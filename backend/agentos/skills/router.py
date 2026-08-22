# backend/agentos/skills/router.py
from __future__ import annotations

import re

from agentos.skills.manifest import SkillLifecycleStatus, SkillManifest, TrustTier
from agentos.skills.registry import SkillRegistry

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

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
    """MVP subset of the blueprint §26 score formula:
    Score = Relevance + Trust + EvalQuality (Cost/Risk/HistoricalSuccess/
    BusinessFit are not tracked yet — later phases add them).
    """
    goal_tokens = _tokenize(goal)
    intent_tokens: set[str] = set()
    for intent in manifest.capability.intents:
        intent_tokens |= _tokenize(intent)
    intent_tokens |= _tokenize(manifest.metadata.description)

    relevance = 0.0
    if goal_tokens and intent_tokens:
        relevance = len(goal_tokens & intent_tokens) / len(goal_tokens)

    if relevance == 0.0:
        return 0.0

    trust = _TRUST_WEIGHT.get(manifest.trust.tier, 0.0)
    return relevance * 0.5 + trust * 0.3 + manifest.quality.eval_score * 0.2


class SkillRouter:
    def __init__(self, registry: SkillRegistry, min_trust: TrustTier = TrustTier.T2) -> None:
        self._registry = registry
        self._min_trust = min_trust

    def select(self, goal: str, *, allow_business_write: bool = False) -> SkillManifest | None:
        candidates = [
            record.manifest
            for record in self._registry.list(status=SkillLifecycleStatus.ACTIVE)
            if self._is_eligible(record.manifest, allow_business_write=allow_business_write)
        ]
        scored = [(score_skill(goal, manifest), manifest) for manifest in candidates]
        relevant = [(score, manifest) for score, manifest in scored if score > 0]
        if not relevant:
            return None
        relevant.sort(key=lambda pair: pair[0], reverse=True)
        return relevant[0][1]

    def _is_eligible(self, manifest: SkillManifest, *, allow_business_write: bool) -> bool:
        trust_order = list(TrustTier)
        if trust_order.index(manifest.trust.tier) > trust_order.index(self._min_trust):
            return False
        if manifest.permissions.business_write and not allow_business_write:
            return False
        return True
