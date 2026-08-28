from __future__ import annotations

import pytest
from agent_core.evals.runner import CanonicalEvalRunner
from apps.cosa.agents.specs import COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC
from apps.cosa.evals.customer_support_autopilot_cases import (
    CUSTOMER_SUPPORT_AUTOPILOT_EVAL_CASES,
    register_customer_support_autopilot_evals,
)


@pytest.mark.asyncio
async def test_customer_support_autopilot_eval_suite():
    runner = CanonicalEvalRunner()
    cases = register_customer_support_autopilot_evals(runner)

    assert len(cases) == 5
    summary = await runner.run_all()

    failed_details = [(r.case_id, r.details, r.error) for r in summary.results if not r.passed]
    assert summary.failed_cases == 0, f"Failed cases: {failed_details}"
    assert summary.total_cases == 5
    assert summary.passed_cases == 5
    assert summary.pass_rate == 1.0


def test_autopilot_eval_evidence_wiring():
    pinned_prompt = COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC.prompt_ref
    assert pinned_prompt is not None
    assert pinned_prompt.definition_hash is not None
    assert len(pinned_prompt.definition_hash) > 0
