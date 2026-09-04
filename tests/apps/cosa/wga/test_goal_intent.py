from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from apps.cosa.agents import goal_intent as gi
from apps.cosa.agents.goal_intent import (
    classify_weekly_goal_llm,
    detect_weekly_goal_suggestion,
    looks_like_weekly_goal,
)


@pytest.mark.parametrize(
    "msg",
    [
        "Tuần này tôi muốn chốt 3 buổi phỏng vấn khách hàng và hoàn thành landing page",
        "Mục tiêu tuần tới: triển khai chiến dịch quảng cáo thử nghiệm cho kênh Facebook",
        "This week we need to close the onboarding SOP and ship the pricing page",
        "Trọng tâm tuần này là hoàn thành tài liệu định vị sản phẩm",
    ],
)
def test_positive_goal_statements(msg):
    s = detect_weekly_goal_suggestion(msg)
    assert s.should_suggest is True
    assert s.normalized_goal


@pytest.mark.parametrize(
    "msg",
    [
        "Ai đang phụ trách task này vậy?",
        "Cảm ơn bạn nhiều nhé",
        "Chào buổi sáng",
        "Báo cáo doanh thu quý trước thế nào?",
        "ok",
        "Tuần này thời tiết đẹp",  # goal cue but no commit verb -> score 2
    ],
)
def test_negative_messages(msg):
    assert looks_like_weekly_goal(msg) is False
    assert detect_weekly_goal_suggestion(msg).should_suggest is False


def test_too_short_message_is_ignored():
    assert looks_like_weekly_goal("mục tiêu tuần này") is False


def test_very_long_message_is_ignored():
    assert looks_like_weekly_goal("tuần này tôi muốn " + "x " * 300) is False


def test_normalized_goal_collapses_whitespace():
    s = detect_weekly_goal_suggestion("Tuần này  tôi   muốn\n\nchốt 3 phỏng vấn khách hàng")
    assert s.normalized_goal == "Tuần này tôi muốn chốt 3 phỏng vấn khách hàng"


@pytest.mark.asyncio
async def test_classify_weekly_goal_llm_parses_structured_output(monkeypatch):
    runner = AsyncMock()
    runner.run.return_value = SimpleNamespace(
        final_output='{"is_weekly_goal_statement": true, '
        '"normalized_goal": "Close 3 customer interviews", "confidence": 0.9}'
    )
    monkeypatch.setattr("agents.Runner", runner)
    res = await classify_weekly_goal_llm("deepseek/deepseek-chat", "tuần này tôi muốn chốt 3 phỏng vấn")
    assert res.is_weekly_goal_statement is True
    assert res.normalized_goal == "Close 3 customer interviews"
    assert res.confidence == 0.9


@pytest.mark.asyncio
async def test_classify_weekly_goal_llm_handles_fenced_json(monkeypatch):
    runner = AsyncMock()
    runner.run.return_value = SimpleNamespace(
        final_output='```json\n{"is_weekly_goal_statement": false, '
        '"normalized_goal": "", "confidence": 0.2}\n```'
    )
    monkeypatch.setattr("agents.Runner", runner)
    res = await classify_weekly_goal_llm("deepseek/deepseek-chat", "ai đang làm task này?")
    assert res.is_weekly_goal_statement is False
    assert res.confidence == 0.2


@pytest.mark.asyncio
async def test_classify_weekly_goal_llm_raises_on_bad_json(monkeypatch):
    runner = AsyncMock()
    runner.run.return_value = SimpleNamespace(final_output="not json")
    monkeypatch.setattr("agents.Runner", runner)
    with pytest.raises(Exception):
        await classify_weekly_goal_llm("deepseek/deepseek-chat", "x")
