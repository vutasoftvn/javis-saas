import pytest
from apps.cosa.observability.initiative_metrics import (
    COSA_INITIATIVE_RUNS_TOTAL,
    COSA_INITIATIVE_RUN_DURATION_SECONDS,
    COSA_INITIATIVE_GATE_EVALUATIONS_TOTAL,
    record_initiative_run,
    record_initiative_gate_evaluation,
)


def test_initiative_metric_labels_exclude_prompt_document_and_tool_payload():
    for metric in [
        COSA_INITIATIVE_RUNS_TOTAL,
        COSA_INITIATIVE_RUN_DURATION_SECONDS,
    ]:
        label_names = set(metric._labelnames)
        assert label_names <= {
            "initiative_id",
            "workspace_id",
            "state",
            "risk_tier",
            "autonomy_tier",
        }
        # Redaction invariant: must never contain raw payload or prompt
        assert "prompt" not in label_names
        assert "document" not in label_names
        assert "tool_payload" not in label_names
        assert "messages" not in label_names


def test_record_initiative_run():
    before = COSA_INITIATIVE_RUNS_TOTAL.labels(
        initiative_id="init_1",
        workspace_id="ws_1",
        state="completed",
        risk_tier="LOW",
        autonomy_tier="A1",
    )._value.get()

    record_initiative_run(
        initiative_id="init_1",
        workspace_id="ws_1",
        state="completed",
        risk_tier="LOW",
        autonomy_tier="A1",
        duration_sec=2.5,
    )

    after = COSA_INITIATIVE_RUNS_TOTAL.labels(
        initiative_id="init_1",
        workspace_id="ws_1",
        state="completed",
        risk_tier="LOW",
        autonomy_tier="A1",
    )._value.get()

    assert after == before + 1


def test_record_initiative_gate_evaluation():
    before = COSA_INITIATIVE_GATE_EVALUATIONS_TOTAL.labels(
        initiative_id="init_1",
        workspace_id="ws_1",
        gate_result="passed",
        risk_tier="LOW",
        autonomy_tier="A1",
    )._value.get()

    record_initiative_gate_evaluation(
        initiative_id="init_1",
        workspace_id="ws_1",
        gate_result="passed",
        risk_tier="LOW",
        autonomy_tier="A1",
    )

    after = COSA_INITIATIVE_GATE_EVALUATIONS_TOTAL.labels(
        initiative_id="init_1",
        workspace_id="ws_1",
        gate_result="passed",
        risk_tier="LOW",
        autonomy_tier="A1",
    )._value.get()

    assert after == before + 1
