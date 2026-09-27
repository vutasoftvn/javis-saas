"""Eval chất lượng agent (G-9): định tuyến WGA chạy trong CI, rubric chạy nightly."""

from __future__ import annotations

import os

import pytest

from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS
from apps.cosa.agents.goal_decomposition import parse_plan_output, validate_plan_capabilities
from apps.cosa.evals.agent_quality import (
    ROUTING_CASES,
    RUBRIC_CASES,
    RubricCase,
    score_rubric,
)
from apps.cosa.worker import wga_run


@pytest.mark.parametrize("case", ROUTING_CASES, ids=lambda c: c.name)
def test_routing_golden_case(case):
    items = validate_plan_capabilities(
        parse_plan_output(case.raw_plan), wga_run._capability_catalog()
    )
    got = {it.title: (it.expected_capability, it.suggested_domain) for it in items}
    assert got == case.expected


def test_rubric_cases_target_real_profiles():
    for case in RUBRIC_CASES:
        assert case.profile in AGENT_PROFILE_SPECS, case.name


def test_score_rubric_rewards_compliant_answer_and_flags_violations():
    case = RubricCase(
        name="t",
        profile="legal",
        prompt="?",
        must_include_any=(("luật sư",),),
        must_not_include=("tôi đã ký",),
    )
    assert score_rubric("Đây không phải tư vấn; hãy hỏi Luật  sư.", case).score == 1.0
    bad = score_rubric("Tôi đã ký hợp đồng cho bạn.", case)
    assert bad.score == 0.0
    assert len(bad.failures) == 2


_LIVE_KEY = os.environ.get("DEEPSEEK_API_KEY")


@pytest.mark.live_provider
@pytest.mark.skipif(not _LIVE_KEY, reason="DEEPSEEK_API_KEY not set — live eval skipped")
@pytest.mark.asyncio
@pytest.mark.parametrize("case", RUBRIC_CASES, ids=lambda c: c.name)
async def test_live_rubric(case):
    import litellm

    spec = AGENT_PROFILE_SPECS[case.profile]
    resp = await litellm.acompletion(
        model=os.environ.get("COSA_EVAL_MODEL", "deepseek/deepseek-chat"),
        messages=[
            {"role": "system", "content": spec.instructions},
            {"role": "user", "content": case.prompt},
        ],
        temperature=0.0,
        seed=7,
    )
    text = resp.choices[0].message.content or ""
    result = score_rubric(text, case)
    assert result.score >= case.min_score, (result.failures, text[:500])
