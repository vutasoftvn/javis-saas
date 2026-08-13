from app.core.snowflake import generate_snowflake_id
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.db.models import AIRun
from app.modules.platform.usage_service import get_usage_summary


def _run(workspace_id, *, provider, model="whatever", input_tokens=0, output_tokens=0, cost=0.0, finished_at=None):
    return AIRun(
        workspace_id=workspace_id,
        provider=provider,
        model=model,
        status="completed",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_estimate=cost,
        finished_at=finished_at,
    )


def test_usage_summary_splits_rolling_window_and_groups_by_provider_and_model():
    workspace_id = generate_snowflake_id()
    now = datetime.utcnow()
    runs = [
        _run(workspace_id, provider="deepseek", model="deepseek-chat", input_tokens=10, output_tokens=5, cost=0.001, finished_at=now),
        _run(
            workspace_id,
            provider="openrouter",
            model="anthropic/claude-sonnet-4.5",
            input_tokens=100,
            output_tokens=50,
            cost=0.02,
            finished_at=now - timedelta(days=5),
        ),
        _run(
            workspace_id,
            provider="openrouter",
            model="deepseek/deepseek-chat",
            input_tokens=200,
            output_tokens=100,
            cost=0.005,
            finished_at=now - timedelta(days=45),
        ),
    ]
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = runs

    summary = get_usage_summary(db, workspace_id)

    assert summary["rolling_30d"]["runs"] == 2
    assert summary["rolling_30d"]["input_tokens"] == 110
    assert summary["all_time"]["runs"] == 3
    assert summary["all_time"]["input_tokens"] == 310
    assert set(summary["by_provider"].keys()) == {"deepseek", "openrouter"}
    
    # Check openrouter per-model breakdown
    openrouter_models = summary["by_provider"]["openrouter"]["models"]
    assert "anthropic/claude-sonnet-4.5" in openrouter_models
    assert openrouter_models["anthropic/claude-sonnet-4.5"]["runs"] == 1
    assert openrouter_models["anthropic/claude-sonnet-4.5"]["cost_estimate"] == 0.02

    # Check key info presence
    assert "openrouter_key_info" in summary


def test_usage_summary_with_no_runs_is_all_zero():
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []

    summary = get_usage_summary(db, generate_snowflake_id())

    assert summary["rolling_30d"] == {"runs": 0, "input_tokens": 0, "output_tokens": 0, "cost_estimate": 0.0}
    assert summary["by_provider"] == {}
    assert "openrouter_key_info" in summary

