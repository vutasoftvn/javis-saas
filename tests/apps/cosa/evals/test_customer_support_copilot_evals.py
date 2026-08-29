from __future__ import annotations

import pytest
from agent.evals.runner import CanonicalEvalRunner
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AGENT_SPEC
from apps.cosa.evals.customer_support_copilot_cases import (
    CUSTOMER_SUPPORT_COPILOT_EVAL_CASES,
    register_customer_support_copilot_evals,
)


@pytest.mark.asyncio
async def test_customer_support_copilot_eval_suite():
    runner = CanonicalEvalRunner()
    cases = register_customer_support_copilot_evals(runner)

    assert len(cases) == 4
    summary = await runner.run_all()

    assert summary.total_cases == 4
    assert summary.passed_cases == 4
    assert summary.failed_cases == 0
    assert summary.pass_rate == 1.0


def test_copilot_eval_evidence_wiring():
    # Acceptance gate wiring check:
    # Definition hash can be extracted from pinned prompt_ref or spec
    pinned_prompt = COSA_CUSTOMER_SUPPORT_AGENT_SPEC.prompt_ref
    assert pinned_prompt is not None
    assert pinned_prompt.definition_hash is not None
    assert len(pinned_prompt.definition_hash) > 0
