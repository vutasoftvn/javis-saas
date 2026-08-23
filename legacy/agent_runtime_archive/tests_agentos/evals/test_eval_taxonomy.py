from __future__ import annotations

import pytest

from agentos.core.models import AgentRun, AgentRunStatus
from agentos.evals.runner import EvalRunner
from agentos.improvement.gap_detection import CapabilityOutcome, GapDetector


def test_eval_runner_executes_all_7_categories():
    runner = EvalRunner()

    # 1. Agent Eval
    run = AgentRun(agent_key="co_founder", goal="Test task", status=AgentRunStatus.COMPLETED)
    outcome_agent = runner.run_agent_eval(run, [])
    assert outcome_agent.succeeded is True
    assert outcome_agent.capability == "agent.task_completion"

    # 2. Tool Eval
    outcome_tool = runner.run_tool_eval(
        actual_tool="commercial.lead.create",
        actual_args={"name": "Alice", "workspaceId": "ws1"},
        expected_tool="commercial.lead.create",
        required_keys=["name"],
    )
    assert outcome_tool.succeeded is True
    assert outcome_tool.capability == "tool.selection"

    # 3. Skill Eval
    outcome_skill = runner.run_skill_eval("strategy_market_sizing", success=True)
    assert outcome_skill.succeeded is True

    # 4. Business Outcome Eval
    outcome_biz = runner.run_business_outcome_eval("mrr_growth", target=10000, actual=12000)
    assert outcome_biz.succeeded is True

    # 5. Safety Governance Eval
    outcome_safety = runner.run_safety_eval(
        total_sensitive=5,
        blocked=2,
        attempted_unauthorized=2,
        requested=3,
        required=3,
    )
    assert outcome_safety.succeeded is True

    # 6. Retrieval Eval
    outcome_retrieval = runner.run_retrieval_eval(
        query="retention policy",
        retrieved_ids=["chunk-1", "chunk-2"],
        expected_ids=["chunk-1", "chunk-2"],
    )
    assert outcome_retrieval.succeeded is True
    assert outcome_retrieval.eval_score == 1.0

    # 7. Model Eval
    model_run = AgentRun(agent_key="co_founder", goal="Test task", status=AgentRunStatus.COMPLETED)
    model_spans = [
        {"name": "model_generation.completed", "model": "test-model", "input_tokens": 100, "output_tokens": 50}
    ]
    outcome_model = runner.run_model_eval([(model_run, model_spans)], model="test-model")
    assert outcome_model.succeeded is True
    assert outcome_model.capability == "model.test-model"

    assert len(runner.results) == 7


def test_eval_runner_feeds_gap_detector_to_surface_capability_gaps():
    runner = EvalRunner()
    gap_detector = GapDetector(min_failures=2, eval_threshold=0.5)

    outcomes = []

    # Simulate multiple failures in tool selection
    for _ in range(3):
        out = runner.run_tool_eval(
            actual_tool="wrong.tool",
            actual_args={},
            expected_tool="commercial.lead.create",
            required_keys=["name"],
        )
        outcomes.append(out)

    # Detect gaps
    gaps = gap_detector.detect(outcomes)

    assert len(gaps) == 1
    assert gaps[0].capability == "tool.selection"
    assert gaps[0].evidence.failed_tasks == 3
    assert gaps[0].evidence.average_eval < 0.5
