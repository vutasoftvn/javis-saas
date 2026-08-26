from __future__ import annotations

from agent_core.contracts.capability import CapabilityImplementationIdentity
from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec


def test_agent_spec_defaults_have_no_pinned_dependency_refs():
    spec = AgentSpec(id="test.agent.m2_1")

    assert spec.prompt_ref is None
    assert spec.model_policy_ref is None
    assert spec.tool_contract_refs == []


def test_agent_spec_fingerprint_changes_when_prompt_ref_is_set():
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    base = AgentSpec(id="test.agent.m2_2")
    with_prompt = base.model_copy(update={"prompt_ref": prompt.to_pinned_identity()})

    assert base.compute_hash() != with_prompt.compute_hash()


def test_agent_spec_fingerprint_changes_when_model_policy_ref_drifts():
    policy_v1 = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-chat").with_hash()
    policy_v2 = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-reasoner").with_hash()

    spec_v1 = AgentSpec(id="test.agent.m2_3", model_policy_ref=policy_v1.to_pinned_identity())
    spec_v2 = AgentSpec(id="test.agent.m2_3", model_policy_ref=policy_v2.to_pinned_identity())

    assert spec_v1.compute_hash() != spec_v2.compute_hash()


def test_agent_spec_fingerprint_changes_when_tool_contract_refs_change():
    base = AgentSpec(id="test.agent.m2_4")
    with_contract = base.model_copy(
        update={
            "tool_contract_refs": [
                CapabilityImplementationIdentity(capability_id="company.strategy.read", handler_version="2.0.0")
            ]
        }
    )

    assert base.compute_hash() != with_contract.compute_hash()
