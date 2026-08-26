from __future__ import annotations

from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.governance.contracts import PinnedSpecIdentity


def test_model_policy_spec_has_sensible_defaults():
    spec = ModelPolicySpec(id="default-deepseek-policy")

    assert spec.version == "1.0.0"
    assert spec.model == "deepseek-chat"
    assert spec.temperature == 0.0
    assert spec.definition_hash is None


def test_model_policy_spec_compute_hash_changes_with_model():
    a = ModelPolicySpec(id="default-deepseek-policy", model="deepseek-chat")
    b = ModelPolicySpec(id="default-deepseek-policy", model="deepseek-reasoner")

    assert a.compute_hash() != b.compute_hash()


def test_model_policy_spec_compute_hash_changes_with_temperature():
    a = ModelPolicySpec(id="default-deepseek-policy", temperature=0.0)
    b = ModelPolicySpec(id="default-deepseek-policy", temperature=0.7)

    assert a.compute_hash() != b.compute_hash()


def test_model_policy_spec_with_hash_returns_a_copy_with_definition_hash_set():
    spec = ModelPolicySpec(id="default-deepseek-policy")

    pinned = spec.with_hash()

    assert spec.definition_hash is None
    assert pinned.definition_hash == spec.compute_hash()


def test_model_policy_spec_to_pinned_identity_uses_model_policy_kind():
    spec = ModelPolicySpec(id="default-deepseek-policy", version="7").with_hash()

    identity = spec.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="model_policy",
        spec_id="default-deepseek-policy",
        spec_version="7",
        definition_hash=spec.definition_hash,
    )
