import pytest

from agentos.improvement.hierarchy import (
    ImprovementLevel,
    PrematureCoreCodeChangeError,
    rank,
    require_cheaper_levels_exhausted,
)


def test_rank_orders_context_retrieval_first_and_core_code_last():
    assert rank(ImprovementLevel.CONTEXT_RETRIEVAL) < rank(ImprovementLevel.CORE_CODE)


def test_context_retrieval_never_requires_cheaper_levels():
    require_cheaper_levels_exhausted(ImprovementLevel.CONTEXT_RETRIEVAL, [])


def test_core_code_raises_when_cheaper_levels_not_tried():
    with pytest.raises(PrematureCoreCodeChangeError):
        require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, [ImprovementLevel.SKILL_SELECTION])


def test_core_code_passes_when_every_cheaper_level_tried():
    all_cheaper = [
        ImprovementLevel.CONTEXT_RETRIEVAL,
        ImprovementLevel.SKILL_SELECTION,
        ImprovementLevel.TOOL_SELECTION,
        ImprovementLevel.WORKFLOW,
        ImprovementLevel.PROMPT_INSTRUCTIONS,
        ImprovementLevel.MEMORY_POLICY,
        ImprovementLevel.MODEL_CHOICE,
        ImprovementLevel.BUSINESS_RULE,
        ImprovementLevel.AGENT_ROLE,
    ]
    require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, all_cheaper)


def test_workflow_level_only_requires_the_two_levels_below_it():
    with pytest.raises(PrematureCoreCodeChangeError) as exc_info:
        require_cheaper_levels_exhausted(ImprovementLevel.WORKFLOW, [ImprovementLevel.CONTEXT_RETRIEVAL])
    assert exc_info.value.missing == [ImprovementLevel.SKILL_SELECTION, ImprovementLevel.TOOL_SELECTION]
