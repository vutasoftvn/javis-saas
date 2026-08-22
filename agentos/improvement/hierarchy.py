from __future__ import annotations

import enum


class ImprovementLevel(str, enum.Enum):
    CONTEXT_RETRIEVAL = "CONTEXT_RETRIEVAL"
    SKILL_SELECTION = "SKILL_SELECTION"
    TOOL_SELECTION = "TOOL_SELECTION"
    WORKFLOW = "WORKFLOW"
    PROMPT_INSTRUCTIONS = "PROMPT_INSTRUCTIONS"
    MEMORY_POLICY = "MEMORY_POLICY"
    MODEL_CHOICE = "MODEL_CHOICE"
    BUSINESS_RULE = "BUSINESS_RULE"
    AGENT_ROLE = "AGENT_ROLE"
    CORE_CODE = "CORE_CODE"


_ORDER: list[ImprovementLevel] = [
    ImprovementLevel.CONTEXT_RETRIEVAL,
    ImprovementLevel.SKILL_SELECTION,
    ImprovementLevel.TOOL_SELECTION,
    ImprovementLevel.WORKFLOW,
    ImprovementLevel.PROMPT_INSTRUCTIONS,
    ImprovementLevel.MEMORY_POLICY,
    ImprovementLevel.MODEL_CHOICE,
    ImprovementLevel.BUSINESS_RULE,
    ImprovementLevel.AGENT_ROLE,
    ImprovementLevel.CORE_CODE,
]


class PrematureCoreCodeChangeError(Exception):
    def __init__(self, missing: list[ImprovementLevel]) -> None:
        super().__init__(
            "Cannot propose this level of change until every cheaper level has been "
            f"tried and ruled out (blueprint §36): missing {[level.value for level in missing]}"
        )
        self.missing = missing


def rank(level: ImprovementLevel) -> int:
    return _ORDER.index(level)


def require_cheaper_levels_exhausted(target_level: ImprovementLevel, tried_levels: list[ImprovementLevel]) -> None:
    """Enforce blueprint §36's Improvement Hierarchy: a proposal that
    targets any level above CONTEXT_RETRIEVAL must show every cheaper
    level was tried first. Deterministic code, not a suggestion an LLM
    can talk its way past.
    """
    if target_level == ImprovementLevel.CONTEXT_RETRIEVAL:
        return
    required = set(_ORDER[: rank(target_level)])
    missing = [level for level in _ORDER if level in required and level not in tried_levels]
    if missing:
        raise PrematureCoreCodeChangeError(missing)
