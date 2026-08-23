# tests/agentos/evals/test_strategy_skills_eval.py
from pathlib import Path
import pytest

from agentos.evals.strategy.eval_cases import STRATEGY_EVAL_CASES, run_strategy_skill_eval
from agentos.skills.registry import SkillRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"


@pytest.fixture(scope="module")
def skill_registry():
    registry = SkillRegistry()
    registry.discover(SKILLPACKS_ROOT)
    return registry


def test_strategy_eval_cases_cover_all_seven_skills():
    assert len(STRATEGY_EVAL_CASES) == 7
    case_skill_ids = [c.skill_id for c in STRATEGY_EVAL_CASES]
    expected_skills = [
        "strategy.stage-assessment",
        "strategy.assumption-discovery",
        "strategy.experiment-design",
        "strategy.evidence-synthesis",
        "strategy.gate-evaluation",
        "strategy.decision-capture",
        "strategy.next-best-action",
    ]
    assert sorted(case_skill_ids) == sorted(expected_skills)


@pytest.mark.parametrize("eval_case", STRATEGY_EVAL_CASES, ids=lambda c: c.id)
def test_strategy_skill_eval_case_execution(skill_registry, eval_case):
    result = run_strategy_skill_eval(skill_registry, eval_case)
    assert result.success is True, f"Eval case {eval_case.id} failed for skill {eval_case.skill_id}"
    assert result.updated_eval_score > 0.0
    assert result.latency_seconds > 0.0
