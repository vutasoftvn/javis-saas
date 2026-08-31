"""Tests for Agent Platform MVP response envelope models and helpers."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from apps.cosa.api.mvp_response import (
    MvpResponseMeta,
    MvpSourceRef,
    MvpSuccess,
    mvp_list,
    mvp_item,
)


def test_mvp_list_never_accepts_unavailable_as_success() -> None:
    with pytest.raises(ValidationError):
        MvpResponseMeta(
            data_state="unavailable",  # type: ignore[arg-type]
            observed_at=datetime.now(timezone.utc),
            sources=[],
        )


def test_mvp_list_with_empty_items_sets_empty_data_state() -> None:
    now = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
    sources = [MvpSourceRef(kind="agent_db", ref="agent.workforce_assignments")]
    res = mvp_list([], sources=sources, observed_at=now)
    assert res.data == []
    assert res.meta.data_state == "empty"
    assert res.meta.observed_at == now
    assert len(res.meta.sources) == 1
    assert res.meta.sources[0].kind == "agent_db"


def test_mvp_item_sets_populated_data_state() -> None:
    now = datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)
    sources = [MvpSourceRef(kind="agent_db", ref="agent.runs")]
    res = mvp_item({"id": "run_1"}, sources=sources, observed_at=now)
    assert res.data == {"id": "run_1"}
    assert res.meta.data_state == "populated"
