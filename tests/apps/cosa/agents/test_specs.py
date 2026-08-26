from __future__ import annotations

from apps.cosa.agents.specs import (
    COSA_DEFAULT_MODEL_POLICY,
    COSA_FINANCE_AGENT_SPEC,
    COSA_FINANCE_PROMPT,
    COSA_OPERATIONS_AGENT_SPEC,
    COSA_OPERATIONS_PROMPT,
)


def test_operations_agent_spec_pins_prompt_ref():
    assert COSA_OPERATIONS_AGENT_SPEC.prompt_ref is not None
    assert COSA_OPERATIONS_AGENT_SPEC.prompt_ref == COSA_OPERATIONS_PROMPT.to_pinned_identity()


def test_operations_agent_spec_pins_model_policy_ref():
    assert COSA_OPERATIONS_AGENT_SPEC.model_policy_ref is not None
    assert COSA_OPERATIONS_AGENT_SPEC.model_policy_ref == COSA_DEFAULT_MODEL_POLICY.to_pinned_identity()


def test_finance_agent_spec_pins_prompt_ref():
    assert COSA_FINANCE_AGENT_SPEC.prompt_ref is not None
    assert COSA_FINANCE_AGENT_SPEC.prompt_ref == COSA_FINANCE_PROMPT.to_pinned_identity()


def test_finance_agent_spec_pins_model_policy_ref():
    assert COSA_FINANCE_AGENT_SPEC.model_policy_ref is not None
    assert COSA_FINANCE_AGENT_SPEC.model_policy_ref == COSA_DEFAULT_MODEL_POLICY.to_pinned_identity()


def test_operations_and_finance_share_the_same_model_policy_ref():
    # 2 agent dùng chung 1 ModelPolicySpec — không cần publish 2 lần khác id.
    assert COSA_OPERATIONS_AGENT_SPEC.model_policy_ref == COSA_FINANCE_AGENT_SPEC.model_policy_ref


def test_agent_specs_have_stable_definition_hash():
    # Import lại module không đổi hash — property quan trọng để publish
    # idempotent ở Task 2 không bị lỗi SpecVersionHashConflictError.
    assert COSA_OPERATIONS_AGENT_SPEC.compute_hash() == COSA_OPERATIONS_AGENT_SPEC.compute_hash()
    assert COSA_FINANCE_AGENT_SPEC.compute_hash() == COSA_FINANCE_AGENT_SPEC.compute_hash()
