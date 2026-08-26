from __future__ import annotations

from agent_core.contracts.identity import PinnedSkillRef
from agent_core.contracts.spec import AgentSpec


def test_agent_spec_fingerprint_changes_when_a_pinned_skill_is_added():
    base = AgentSpec(id="test.agent.fixture_1", version="1.0.0", instructions="Base")
    with_skill = base.model_copy(
        update={
            "pinned_skills": [
                PinnedSkillRef(skill_id="research", version="1", definition_hash="b" * 64)
            ]
        }
    )

    assert base.compute_hash() != with_skill.compute_hash()


def test_agent_spec_fingerprint_changes_when_pinned_skill_hash_drifts():
    v1 = AgentSpec(
        id="test.agent.fixture_2",
        version="1.0.0",
        pinned_skills=[PinnedSkillRef(skill_id="research", version="1", definition_hash="a" * 64)],
    )
    drifted = v1.model_copy(
        update={"pinned_skills": [PinnedSkillRef(skill_id="research", version="1", definition_hash="c" * 64)]}
    )

    assert v1.compute_hash() != drifted.compute_hash()


def test_agent_spec_fingerprint_stable_when_metadata_dict_key_order_differs():
    a = AgentSpec(id="test.agent.fixture_3", version="1.0.0", metadata={"a": 1, "b": 2})
    b = AgentSpec(id="test.agent.fixture_3", version="1.0.0", metadata={"b": 2, "a": 1})

    assert a.compute_hash() == b.compute_hash()


def test_agent_spec_fingerprint_stable_across_repeated_calls():
    spec = AgentSpec(id="test.agent.fixture_4", version="1.0.0", instructions="Stable")

    assert spec.compute_hash() == spec.compute_hash()
