"""Direct unit tests for skill mutator functions."""

from __future__ import annotations

import pytest

from agent.skills.contracts import SkillSpec
from agent.skills.lab.mutator import MutationFn, noop_mutator


class TestNoopMutator:
    """Direct tests for noop_mutator function."""

    def test_noop_mutator_returns_tuple(self) -> None:
        """noop_mutator returns (SkillSpec, str) tuple."""
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")
        result = noop_mutator(skill)

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_noop_mutator_returns_skill_and_message(self) -> None:
        """noop_mutator returns skill and a description message."""
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")
        mutated_skill, message = noop_mutator(skill)

        assert isinstance(mutated_skill, SkillSpec)
        assert isinstance(message, str)

    def test_noop_mutator_skill_has_same_id(self) -> None:
        """Returned skill has the same id as input."""
        skill = SkillSpec(id="test.skill.noop", version="1.0.0", instructions="Input")
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.id == skill.id

    def test_noop_mutator_skill_has_same_version(self) -> None:
        """Returned skill has the same version as input."""
        skill = SkillSpec(id="test.skill", version="2.5.3", instructions="Input")
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.version == skill.version

    def test_noop_mutator_skill_has_same_instructions(self) -> None:
        """Returned skill has unchanged instructions."""
        instructions = "Do this and that and more stuff"
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions=instructions)
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.instructions == skill.instructions
        assert mutated_skill.instructions == instructions

    def test_noop_mutator_skill_has_same_name(self) -> None:
        """Returned skill has unchanged name."""
        skill = SkillSpec(
            id="test.skill",
            version="1.0.0",
            instructions="Test",
            name="Original Name",
        )
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.name == skill.name
        assert mutated_skill.name == "Original Name"

    def test_noop_mutator_skill_has_same_description(self) -> None:
        """Returned skill has unchanged description."""
        skill = SkillSpec(
            id="test.skill",
            version="1.0.0",
            instructions="Test",
            description="Original Description",
        )
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.description == skill.description
        assert mutated_skill.description == "Original Description"

    def test_noop_mutator_message_indicates_noop(self) -> None:
        """Returned message indicates this is a no-op mutation."""
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")
        _, message = noop_mutator(skill)

        assert "no-op" in message.lower()
        assert "placeholder" in message.lower()

    def test_noop_mutator_message_exact_text(self) -> None:
        """Returned message has the exact no-op placeholder text."""
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")
        _, message = noop_mutator(skill)

        expected_msg = "no-op (placeholder mutator — no real mutation applied)"
        assert message == expected_msg

    def test_noop_mutator_returns_deep_copy(self) -> None:
        """Returned skill is a deep copy (not the same object)."""
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Original")
        mutated_skill, _ = noop_mutator(skill)

        # They should be equal
        assert mutated_skill == skill
        # But not the same object
        assert mutated_skill is not skill

    def test_noop_mutator_deep_copy_preserves_complex_fields(self) -> None:
        """Deep copy preserves complex nested fields like required_capabilities."""
        skill = SkillSpec(
            id="test.skill",
            version="1.0.0",
            instructions="Test",
            required_capabilities=["capability.read", "capability.write"],
            required_knowledge=["knowledge.domain"],
        )
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.required_capabilities == skill.required_capabilities
        assert mutated_skill.required_knowledge == skill.required_knowledge
        # Deep copy means they're different list objects
        assert mutated_skill.required_capabilities is not skill.required_capabilities

    def test_noop_mutator_preserves_references_dict(self) -> None:
        """Deep copy preserves references dict field."""
        references = {
            "doc1": "reference1",
            "doc2": "reference2",
        }
        skill = SkillSpec(
            id="test.skill",
            version="1.0.0",
            instructions="Test",
            references=references,
        )
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.references == skill.references
        # Deep copy means different dict objects
        assert mutated_skill.references is not skill.references

    def test_noop_mutator_is_mutation_fn_compatible(self) -> None:
        """noop_mutator matches MutationFn signature."""
        # MutationFn = Callable[[SkillSpec], tuple[SkillSpec, str]]
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")

        # Should be callable as a MutationFn
        mutation_func: MutationFn = noop_mutator
        result = mutation_func(skill)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], SkillSpec)
        assert isinstance(result[1], str)

    def test_noop_mutator_with_minimal_skill(self) -> None:
        """noop_mutator works with minimal skill (only required fields)."""
        skill = SkillSpec(id="minimal.skill", version="1.0.0", instructions="")
        mutated_skill, message = noop_mutator(skill)

        assert mutated_skill.id == "minimal.skill"
        assert mutated_skill.version == "1.0.0"
        assert mutated_skill.instructions == ""
        assert message == "no-op (placeholder mutator — no real mutation applied)"

    def test_noop_mutator_with_full_skill(self) -> None:
        """noop_mutator preserves all fields in a fully-populated skill."""
        from datetime import datetime
        from datetime import UTC

        now = datetime.now(UTC)
        skill = SkillSpec(
            id="full.skill",
            version="3.2.1",
            name="Full Skill",
            description="A full skill spec",
            instructions="Complex instructions",
            required_capabilities=["cap1", "cap2"],
            required_knowledge=["know1"],
            references={"key": "value"},
            publisher="custom_publisher",
            created_at=now,
        )
        mutated_skill, _ = noop_mutator(skill)

        assert mutated_skill.id == skill.id
        assert mutated_skill.version == skill.version
        assert mutated_skill.name == skill.name
        assert mutated_skill.description == skill.description
        assert mutated_skill.instructions == skill.instructions
        assert mutated_skill.required_capabilities == skill.required_capabilities
        assert mutated_skill.required_knowledge == skill.required_knowledge
        assert mutated_skill.references == skill.references
        assert mutated_skill.publisher == skill.publisher
        assert mutated_skill.created_at == skill.created_at

    def test_noop_mutator_idempotent_over_multiple_calls(self) -> None:
        """Calling noop_mutator multiple times on same skill yields same result."""
        original_skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")

        result1_skill, result1_msg = noop_mutator(original_skill)
        result2_skill, result2_msg = noop_mutator(original_skill)

        # Both results should be identical
        assert result1_skill == result2_skill
        assert result1_msg == result2_msg
        # But different objects (because deep copy)
        assert result1_skill is not result2_skill

    def test_noop_mutator_chaining(self) -> None:
        """Result of noop_mutator can be passed to noop_mutator again."""
        skill = SkillSpec(id="test.skill", version="1.0.0", instructions="Test")

        mutated1, _ = noop_mutator(skill)
        mutated2, _ = noop_mutator(mutated1)
        mutated3, _ = noop_mutator(mutated2)

        # All should be equal to original
        assert mutated1 == skill
        assert mutated2 == skill
        assert mutated3 == skill
        # But all different objects
        assert mutated1 is not skill
        assert mutated2 is not mutated1
        assert mutated3 is not mutated2
