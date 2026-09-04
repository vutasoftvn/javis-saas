import json

import pytest

from apps.cosa.agents.kickoff_suggestion import (
    SuggestionSchemaError,
    build_suggestion_prompt,
    parse_suggestion_output,
)


def _output(**over):
    data = {
        "outcome": "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
        "actions": ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"],
    }
    data.update(over)
    return json.dumps(data)


def test_parses_valid_output():
    result = parse_suggestion_output(_output())
    assert result.outcome == "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu"
    assert result.actions == ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"]


def test_parses_output_with_markdown_fence():
    raw = "```json\n" + _output() + "\n```"
    result = parse_suggestion_output(raw)
    assert len(result.actions) == 2


def test_single_action_is_valid():
    result = parse_suggestion_output(_output(actions=["Chỉ 1 việc"]))
    assert result.actions == ["Chỉ 1 việc"]


def test_empty_output_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output("")


def test_non_json_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output("not json at all")


def test_missing_outcome_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(json.dumps({"actions": ["a"]}))


def test_empty_outcome_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(outcome=""))


def test_zero_actions_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(actions=[]))


def test_four_actions_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(actions=["a", "b", "c", "d"]))


def test_empty_action_item_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(actions=["a", ""]))


def test_outcome_over_200_chars_is_truncated_not_rejected():
    long_outcome = "x" * 250
    result = parse_suggestion_output(_output(outcome=long_outcome))
    assert len(result.outcome) == 200


def test_build_prompt_includes_context():
    prompt = build_suggestion_prompt(
        target_customer="Founder B2B SaaS",
        problem_statement="Không biết validate ý tưởng",
        evidence_level="NONE",
        selected_stage="P0_DISCOVERY",
        stage_duration_weeks=2,
    )
    assert "Founder B2B SaaS" in prompt
    assert "Không biết validate ý tưởng" in prompt
    assert "Chưa nói chuyện với khách hàng" in prompt
    assert "2 tuần" in prompt
