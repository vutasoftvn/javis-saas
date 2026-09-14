from __future__ import annotations

import hashlib
import json
import os
from datetime import timedelta
from typing import Any, Literal

from agent.skills.improvement_repository import SkillIdentity
from pydantic import BaseModel, Field

__all__ = [
    "EffectiveSkillImprovementPolicy",
    "SkillImprovementMode",
    "check_improvement_eligibility",
    "compute_policy_hash",
    "load_effective_improvement_policy",
]

SkillImprovementMode = Literal["OFF", "OBSERVE", "CANDIDATE"]


def compute_policy_hash(
    mode: str,
    allowed_identities: frozenset[SkillIdentity],
    min_feedback_samples: int,
    feedback_window_size: int,
    low_score_threshold: float,
    minimum_degradation_delta: float,
    cooldown_seconds: float,
    max_rounds: int,
    max_candidates_per_request: int,
) -> str:
    sorted_ids = sorted(list(allowed_identities))
    data = {
        "mode": mode,
        "allowed_identities": [list(item) for item in sorted_ids],
        "min_feedback_samples": min_feedback_samples,
        "feedback_window_size": feedback_window_size,
        "low_score_threshold": low_score_threshold,
        "minimum_degradation_delta": minimum_degradation_delta,
        "cooldown_seconds": cooldown_seconds,
        "max_rounds": max_rounds,
        "max_candidates_per_request": max_candidates_per_request,
    }
    raw = json.dumps(data, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EffectiveSkillImprovementPolicy(BaseModel):
    """Server-owned policy governing feedback-driven skill candidate optimization."""

    mode: SkillImprovementMode = "OFF"
    allowed_identities: frozenset[SkillIdentity] = Field(default_factory=frozenset)
    min_feedback_samples: int = 3
    feedback_window_size: int = 10
    low_score_threshold: float = 0.60
    minimum_degradation_delta: float = 0.15
    cooldown: timedelta = Field(default_factory=lambda: timedelta(days=7))
    max_rounds: int = 2
    max_candidates_per_request: int = 1
    policy_hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.policy_hash:
            computed = compute_policy_hash(
                mode=self.mode,
                allowed_identities=self.allowed_identities,
                min_feedback_samples=self.min_feedback_samples,
                feedback_window_size=self.feedback_window_size,
                low_score_threshold=self.low_score_threshold,
                minimum_degradation_delta=self.minimum_degradation_delta,
                cooldown_seconds=self.cooldown.total_seconds(),
                max_rounds=self.max_rounds,
                max_candidates_per_request=self.max_candidates_per_request,
            )
            object.__setattr__(self, "policy_hash", computed)


def parse_allowed_identities(raw_input: Any) -> frozenset[SkillIdentity]:
    if not raw_input:
        return frozenset()
    if isinstance(raw_input, str):
        try:
            parsed = json.loads(raw_input)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed COSA_SKILL_IMPROVEMENT_ALLOWLIST JSON: {exc}") from exc
    elif isinstance(raw_input, (list, set, frozenset, tuple)):
        parsed = raw_input
    else:
        raise ValueError("Invalid format for allowed_identities")

    identities = set()
    for item in parsed:
        if isinstance(item, (list, tuple)) and len(item) == 3:
            s_id, ver, def_h = item
        elif isinstance(item, dict):
            s_id = item.get("skill_id")
            ver = item.get("version")
            def_h = item.get("definition_hash")
        else:
            raise ValueError(f"Invalid identity entry in allow-list: {item!r}")

        if not s_id or not isinstance(s_id, str):
            raise ValueError(f"Missing or invalid skill_id in identity: {item!r}")
        if not ver or not isinstance(ver, str):
            raise ValueError(f"Missing or invalid version in identity: {item!r}")
        if not def_h or not isinstance(def_h, str):
            raise ValueError(f"Missing or invalid definition_hash in identity: {item!r}")

        identities.add((s_id, ver, def_h))

    return frozenset(identities)


def load_effective_improvement_policy(
    mode: str | None = None,
    allowed_identities: Any | None = None,
    min_feedback_samples: int | None = None,
    feedback_window_size: int | None = None,
    low_score_threshold: float | None = None,
    minimum_degradation_delta: float | None = None,
    cooldown: timedelta | None = None,
    max_rounds: int | None = None,
    max_candidates_per_request: int | None = None,
) -> EffectiveSkillImprovementPolicy:
    env_mode = (mode or os.getenv("COSA_SKILL_IMPROVEMENT_MODE", "OFF")).upper()
    if env_mode not in ("OFF", "OBSERVE", "CANDIDATE"):
        raise ValueError(f"Unsupported COSA_SKILL_IMPROVEMENT_MODE: {env_mode}")

    if allowed_identities is not None:
        identities = parse_allowed_identities(allowed_identities)
    else:
        raw_env_allow = os.getenv("COSA_SKILL_IMPROVEMENT_ALLOWLIST")
        identities = parse_allowed_identities(raw_env_allow)

    policy_kwargs: dict[str, Any] = {
        "mode": env_mode,
        "allowed_identities": identities,
    }
    if min_feedback_samples is not None:
        policy_kwargs["min_feedback_samples"] = min_feedback_samples
    if feedback_window_size is not None:
        policy_kwargs["feedback_window_size"] = feedback_window_size
    if low_score_threshold is not None:
        policy_kwargs["low_score_threshold"] = low_score_threshold
    if minimum_degradation_delta is not None:
        policy_kwargs["minimum_degradation_delta"] = minimum_degradation_delta
    if cooldown is not None:
        policy_kwargs["cooldown"] = cooldown
    if max_rounds is not None:
        policy_kwargs["max_rounds"] = max_rounds
    if max_candidates_per_request is not None:
        policy_kwargs["max_candidates_per_request"] = max_candidates_per_request

    return EffectiveSkillImprovementPolicy(**policy_kwargs)


def check_improvement_eligibility(
    policy: EffectiveSkillImprovementPolicy,
    identity: SkillIdentity,
    *,
    is_executive_skill: bool = False,
    evaluator_registered: bool = True,
    suite_hash_matches: bool = True,
    has_live_request: bool = False,
) -> tuple[bool, str | None]:
    """Evaluates strict server-owned eligibility for candidate optimization."""
    if policy.mode == "OFF":
        return False, "POLICY_OFF"
    if policy.mode == "OBSERVE":
        return False, "POLICY_OBSERVE_ONLY"
    if identity not in policy.allowed_identities:
        return False, "EVALUATOR_IDENTITY_MISMATCH"
    if is_executive_skill:
        return False, "EXECUTIVE_SKILL_PROTECTED"
    if not evaluator_registered or not suite_hash_matches:
        return False, "EVALUATOR_IDENTITY_MISMATCH"
    if has_live_request:
        return False, "REQUEST_ALREADY_ACTIVE"

    return True, None
