from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from agent.skills.contracts import SkillSpec

logger = logging.getLogger(__name__)

__all__ = [
    "CandidateMutatorProtocol",
    "ModelBackedCandidateMutator",
    "validate_candidate_mutation",
]


def validate_candidate_mutation(
    base_skill: SkillSpec, mutated_skill: SkillSpec
) -> tuple[bool, str | None]:
    """Validates that a mutated skill candidate does not expand autonomy or capabilities.

    Invariants:
    - Skill ID must remain identical.
    - Required capabilities must NOT be added or changed.
    - Autonomy ceiling must NOT be expanded.
    - Side effect class must NOT be expanded.
    """
    if mutated_skill.id != base_skill.id:
        return False, "MUTATION_BOUNDARY_VIOLATION"

    if sorted(mutated_skill.required_capabilities) != sorted(base_skill.required_capabilities):
        logger.warning(
            "Candidate mutation attempted capability change: base=%s, mutated=%s",
            base_skill.required_capabilities,
            mutated_skill.required_capabilities,
        )
        return False, "MUTATION_BOUNDARY_VIOLATION"

    if mutated_skill.autonomy.ceiling != base_skill.autonomy.ceiling:
        logger.warning(
            "Candidate mutation attempted autonomy ceiling expansion: base=%s, mutated=%s",
            base_skill.autonomy.ceiling,
            mutated_skill.autonomy.ceiling,
        )
        return False, "MUTATION_BOUNDARY_VIOLATION"

    if mutated_skill.autonomy.side_effect_class != base_skill.autonomy.side_effect_class:
        logger.warning(
            "Candidate mutation attempted side effect class change: base=%s, mutated=%s",
            base_skill.autonomy.side_effect_class,
            mutated_skill.autonomy.side_effect_class,
        )
        return False, "MUTATION_BOUNDARY_VIOLATION"

    return True, None


@runtime_checkable
class CandidateMutatorProtocol(Protocol):
    async def __call__(
        self, skill: SkillSpec, feedback_summary: str | None = None
    ) -> tuple[SkillSpec, str]: ...


class ModelBackedCandidateMutator:
    """Production candidate mutator using an approved model route and bounded token budget."""

    def __init__(
        self,
        *,
        model_client: Any,
        model_id: str = "deepseek-chat",
        temperature: float = 0.2,
    ) -> None:
        self._client = model_client
        self._model_id = model_id
        self._temperature = temperature

    async def __call__(
        self, skill: SkillSpec, feedback_summary: str | None = None
    ) -> tuple[SkillSpec, str]:
        # Mutator prompt strictly asks to improve instructions and clarity without adding tools
        prompt = (
            f"You are a skill optimization assistant. Improve the following instructions for skill '{skill.id}'.\n"
            f"Current instructions:\n{skill.instructions}\n\n"
            f"Feedback context: {feedback_summary or 'Improve clarity and failure case handling.'}\n\n"
            f"Provide ONLY the revised instructions."
        )
        try:
            response = await self._client.chat.completions.create(
                model=self._model_id,
                temperature=self._temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            revised_instructions = response.choices[0].message.content.strip()
            mutated = skill.model_copy(
                update={"instructions": revised_instructions},
                deep=True,
            )
            diff_summary = f"Revised instructions for {skill.id} via {self._model_id}"
            return mutated, diff_summary
        except Exception as exc:
            logger.error("ModelBackedCandidateMutator invocation failed: %s", exc)
            # Revert to base on failure
            return skill.model_copy(deep=True), f"mutation_failed: {exc}"
