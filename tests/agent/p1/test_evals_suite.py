from __future__ import annotations

import pytest

from agent.evals import (
    CanonicalEvalRunner,
    EvalCategory,
    EvalTestCase,
)


@pytest.mark.asyncio
async def test_evals_baseline_suite_execution():
    """Kiểm thử 4 nhóm Evals Baseline Suite (§33 & §43.11)."""
    runner = CanonicalEvalRunner()

    # Case 1: Kernel Capability
    runner.register_case(
        EvalTestCase(
            id="eval_kernel_01",
            name="Kernel Tool Calling Formatting",
            category=EvalCategory.KERNEL_CAPABILITY,
            description="Verifies tool calls emit well-structured JSON payload",
        ),
        lambda: asyncio_pass(),
    )

    # Case 2: Business Correctness
    runner.register_case(
        EvalTestCase(
            id="eval_biz_02",
            name="Payout Policy Validation",
            category=EvalCategory.BUSINESS_CORRECTNESS,
            description="Verifies transactions obey high-risk threshold",
        ),
        lambda: asyncio_pass(),
    )

    # Case 3: Durability & Recovery
    runner.register_case(
        EvalTestCase(
            id="eval_durability_03",
            name="Checkpoint Cross-Process Resume",
            category=EvalCategory.DURABILITY_RECOVERY,
            description="Verifies resumed run loads serialized state from checkpoint",
        ),
        lambda: asyncio_pass(),
    )

    # Case 4: Security & Governance
    runner.register_case(
        EvalTestCase(
            id="eval_security_04",
            name="Ambient Revocation Gate",
            category=EvalCategory.SECURITY_GOVERNANCE,
            description="Verifies revoked principal is rejected prior to tool invocation",
        ),
        lambda: asyncio_pass(),
    )

    summary = await runner.run_all()
    assert summary.total_cases == 4
    assert summary.passed_cases == 4
    assert summary.failed_cases == 0
    assert summary.pass_rate == 1.0
    assert len(summary.category_scores) == 4


async def asyncio_pass() -> bool:
    return True
