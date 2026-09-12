from __future__ import annotations

from datetime import timedelta
import pytest

from apps.cosa.skills.improvement_policy import (
    EffectiveSkillImprovementPolicy,
    check_improvement_eligibility,
    compute_policy_hash,
    load_effective_improvement_policy,
)

HASH_A = "a" * 64
HASH_B = "b" * 64


def test_policy_load_defaults() -> None:
    policy = load_effective_improvement_policy(mode="OFF")
    assert policy.mode == "OFF"
    assert policy.allowed_identities == frozenset()
    assert policy.min_feedback_samples == 3
    assert policy.policy_hash != ""


def test_policy_load_invalid_mode_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported COSA_SKILL_IMPROVEMENT_MODE"):
        load_effective_improvement_policy(mode="UNKNOWN")


def test_policy_load_allowed_identities_parsing() -> None:
    identities_list = [
        ("brief", "1.0.0", HASH_A),
        {"skill_id": "review", "version": "1.0.0", "definition_hash": HASH_B},
    ]
    policy = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=identities_list,
    )
    assert policy.mode == "CANDIDATE"
    assert ("brief", "1.0.0", HASH_A) in policy.allowed_identities
    assert ("review", "1.0.0", HASH_B) in policy.allowed_identities


def test_policy_load_malformed_identity_raises() -> None:
    with pytest.raises(ValueError, match="Missing or invalid definition_hash"):
        load_effective_improvement_policy(
            mode="CANDIDATE",
            allowed_identities=[{"skill_id": "brief", "version": "1.0.0"}],
        )


def test_policy_hash_is_deterministic() -> None:
    p1 = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[("brief", "1.0.0", HASH_A)],
    )
    p2 = load_effective_improvement_policy(
        mode="CANDIDATE",
        allowed_identities=[("brief", "1.0.0", HASH_A)],
    )
    assert p1.policy_hash == p2.policy_hash


def test_check_eligibility_modes_and_boundaries() -> None:
    identity = ("brief", "1.0.0", HASH_A)
    p_off = load_effective_improvement_policy(mode="OFF", allowed_identities=[identity])
    ok, reason = check_improvement_eligibility(p_off, identity)
    assert not ok
    assert reason == "POLICY_OFF"

    p_obs = load_effective_improvement_policy(mode="OBSERVE", allowed_identities=[identity])
    ok, reason = check_improvement_eligibility(p_obs, identity)
    assert not ok
    assert reason == "POLICY_OBSERVE_ONLY"

    p_cand = load_effective_improvement_policy(mode="CANDIDATE", allowed_identities=[identity])
    # Different identity not in allowlist
    ok, reason = check_improvement_eligibility(p_cand, ("other", "1.0.0", HASH_B))
    assert not ok
    assert reason == "EVALUATOR_IDENTITY_MISMATCH"

    # Executive skill protected
    ok, reason = check_improvement_eligibility(p_cand, identity, is_executive_skill=True)
    assert not ok
    assert reason == "EXECUTIVE_SKILL_PROTECTED"

    # Evaluator not registered
    ok, reason = check_improvement_eligibility(p_cand, identity, evaluator_registered=False)
    assert not ok
    assert reason == "EVALUATOR_IDENTITY_MISMATCH"

    # Already active request
    ok, reason = check_improvement_eligibility(p_cand, identity, has_live_request=True)
    assert not ok
    assert reason == "REQUEST_ALREADY_ACTIVE"

    # Eligible
    ok, reason = check_improvement_eligibility(p_cand, identity)
    assert ok
    assert reason is None
