"""Startup OS Phase 3 (plan 2026-09-18): capability onboarding hội thoại và tư vấn Goal.

Khoá các hành vi:
- scope workspace chỉ lấy từ InvocationContext, không từ tham số do model sinh ra;
- payload chiều onboarding sai hợp đồng bị chặn trước khi gọi Company;
- advisory không báo "tươi" khi chưa có dữ liệu;
- chỉ capability đọc/ghi ngữ cảnh được đăng ký cho agent, không có goal.create/triage.
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.cosa.agents.specs import COSA_COFOUNDER_ASSISTANT_AGENT_SPEC
from apps.cosa.capabilities.startup_os_goals import (
    build_goal_advisory,
    create_startup_os_goal_advisory_handler,
    create_startup_os_goal_tree_read_handler,
)
from apps.cosa.capabilities.startup_os_onboard import (
    create_startup_os_cadence_advisory_handler,
    create_startup_os_context_read_handler,
    create_startup_os_dimension_update_handler,
    create_startup_os_interview_plan_handler,
    summarize_cadence_freshness,
)
from apps.cosa.workflows.onboarding_dimensions import OnboardDimensionDataError


class _RecordingClient:
    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]] = []
        self._responses = responses or {}

    async def get(self, path: str, params: dict[str, Any] | None = None, headers=None):
        self.calls.append(("GET", path, params, None))
        return self._responses.get(path, {})

    async def post(self, path: str, json: dict[str, Any] | None = None, params=None, headers=None):
        self.calls.append(("POST", path, params, json))
        return self._responses.get(path, {"ok": True})


def _fresh(dimension: str, days: int = 1, interval: int = 14) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "cadence": "fast",
        "intervalDays": interval,
        "daysSinceLastReview": days,
        "neverReviewed": False,
        "urgency": "ok",
    }


def _never(dimension: str) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "cadence": "fast",
        "intervalDays": 14,
        "daysSinceLastReview": None,
        "neverReviewed": True,
        "urgency": "critical",
    }


@pytest.mark.asyncio
async def test_handlers_fail_closed_without_context_workspace():
    client = _RecordingClient()
    handler = create_startup_os_context_read_handler(client)
    with pytest.raises(ValueError, match="workspace_id missing"):
        await handler({"workspace_id": "ws-from-model"}, {})
    assert client.calls == []


@pytest.mark.asyncio
async def test_model_supplied_workspace_id_is_ignored():
    client = _RecordingClient()
    handler = create_startup_os_goal_tree_read_handler(client)
    await handler({"workspace_id": "ws-other-tenant"}, {"workspace_id": "ws-run"})
    assert client.calls == [("GET", "/operations/goals/tree", {"workspaceId": "ws-run"}, None)]


@pytest.mark.asyncio
async def test_dimension_update_rejects_legacy_keys_without_calling_company():
    client = _RecordingClient()
    handler = create_startup_os_dimension_update_handler(client)
    with pytest.raises(OnboardDimensionDataError, match="unknown field"):
        await handler(
            {"session_id": "1", "dimension": "stage_scale", "data": {"arr": 1, "runway_weeks": 30}},
            {"workspace_id": "ws-run"},
        )
    assert client.calls == []


@pytest.mark.asyncio
async def test_dimension_update_posts_validated_payload_for_run_workspace():
    client = _RecordingClient()
    handler = create_startup_os_dimension_update_handler(client)
    await handler(
        {
            "session_id": "42",
            "dimension": "challenges",
            "data": {"priorityMoney": 5, "avoidedDecision": "Cắt tính năng B"},
        },
        {"workspace_id": "ws-run"},
    )
    assert client.calls == [
        (
            "POST",
            "/operations/onboard/dimensions/challenges",
            None,
            {
                "workspaceId": "ws-run",
                "sessionId": "42",
                "data": {"priorityMoney": 5, "avoidedDecision": "Cắt tính năng B"},
            },
        )
    ]


@pytest.mark.asyncio
async def test_interview_plan_for_setup_and_update_with_event_trigger():
    handler = create_startup_os_interview_plan_handler()

    setup = await handler({"session_type": "initial"}, {"workspace_id": "ws-run"})
    assert [s["dimension"] for s in setup["steps"]] == [
        "stage_scale",
        "challenges",
        "goals_ambition",
        "market",
        "team_culture",
        "identity",
        "founder",
    ]
    assert "revenueArr" in setup["steps"][0]["expected_schema_keys"]
    assert setup["event_trigger"] is None

    update = await handler(
        {"session_type": "partial_update", "founder_message": "Tuần này bọn mình nhận term sheet"},
        {"workspace_id": "ws-run"},
    )
    assert [s["dimension"] for s in update["steps"]] == ["stage_scale", "challenges"]
    assert update["event_trigger"]["event_type"] == "fundraising"
    assert update["event_trigger"]["suggested_dimension"] == "stage_scale"


def test_freshness_is_not_reported_fresh_without_data():
    assert summarize_cadence_freshness([]) == {
        "freshness_score": 0.0,
        "status": "not_started",
        "recommendations": [],
    }
    summary = summarize_cadence_freshness([_never("stage_scale"), _fresh("challenges")])
    # Chiều chưa ghi nhận được 0 điểm: (0 * 0.2 + 100 * 0.2) / 0.4 = 50.
    assert summary["freshness_score"] == 50.0
    assert summary["status"] == "needs_attention"
    rec = summary["recommendations"][0]
    assert rec["dimension"] == "stage_scale"
    assert rec["never_reviewed"] is True
    assert rec["weeks_since_last_review"] is None


@pytest.mark.asyncio
async def test_cadence_advisory_handles_never_reviewed_dimensions():
    client = _RecordingClient(
        {"/operations/onboard/cadence/status": {"cadences": [_never("identity")]}}
    )
    handler = create_startup_os_cadence_advisory_handler(client)
    result = await handler({}, {"workspace_id": "ws-run"})
    assert result["freshness_score"] == 0.0
    assert (
        result["recommendations"][0]["advisory_nudge"]
        == "Chiều 'identity' chưa từng được ghi nhận."
    )


def test_goal_advisory_suggests_type_from_stage_and_passes_alignment_inputs():
    context = {
        "stage_scale": {"stage": "pre_pmf"},
        "identity": {
            "values": [
                {"valueText": "Khách hàng trước", "isFireWorthy": True},
                {"valueText": "Poster value", "isFireWorthy": False},
            ]
        },
        "challenges": {"priorityMoney": 5, "priorityProduct": 5, "priorityPeople": 2},
        "goals_ambition": {"goal12MonthsText": "100 khách trả tiền"},
    }
    advisory = build_goal_advisory(
        context,
        [_fresh("stage_scale"), _fresh("challenges")],
        [],
        proposed_goal_type="strategic",
    )
    assert advisory["suggested_goal_type"] == "tactical"
    assert advisory["context_ready"] is True
    assert [w["code"] for w in advisory["warnings"]] == ["GOAL_TYPE_MISMATCH_STAGE"]
    assert advisory["alignment_inputs"]["fire_worthy_values"] == ["Khách hàng trước"]
    assert advisory["alignment_inputs"]["top_priority_areas"] == ["money", "product"]
    assert advisory["alignment_inputs"]["goal_12_months"] == "100 khách trả tiền"


def test_goal_advisory_blocks_readiness_when_fast_context_missing():
    advisory = build_goal_advisory(
        {},
        [_never("stage_scale"), _never("challenges"), _fresh("market", interval=60)],
        [{"goalId": "1", "goalTitle": "Cũ", "goalType": "tactical"}],
    )
    codes = [w["code"] for w in advisory["warnings"]]
    assert advisory["context_ready"] is False
    assert advisory["suggested_goal_type"] is None
    assert codes.count("FAST_CONTEXT_STALE") == 2
    assert "STAGE_UNKNOWN" in codes
    assert "GOALS_NEED_REVIEW" in codes


@pytest.mark.asyncio
async def test_goal_advisory_handler_reads_company_for_run_workspace():
    client = _RecordingClient(
        {
            "/operations/onboard/context/current": {
                "fullContext": {"stage_scale": {"stage": "scaling"}}
            },
            "/operations/onboard/cadence/status": {
                "cadences": [_fresh("stage_scale"), _fresh("challenges")]
            },
            "/operations/goals/needing-review": {"goals": []},
        }
    )
    handler = create_startup_os_goal_advisory_handler(client)
    result = await handler({"workspace_id": "ignored"}, {"workspace_id": "ws-run"})
    assert result["workspace_id"] == "ws-run"
    assert result["suggested_goal_type"] == "strategic"
    assert {c[2]["workspaceId"] for c in client.calls} == {"ws-run"}


def test_registry_exposes_startup_os_read_and_context_capabilities_only():
    from unittest.mock import MagicMock

    from agent.capabilities.registry import CapabilityRegistry

    from apps.cosa.capabilities.client import CompanyServiceClient
    from apps.cosa.composition.capability_registration import register_cosa_capabilities

    registry = CapabilityRegistry()
    register_cosa_capabilities(
        registry,
        client=CompanyServiceClient(base_url="http://company.invalid"),
        tenant_policy=MagicMock(),
        search_budget=MagicMock(),
        artifact_repo=MagicMock(),
    )
    ids = {spec.id for spec in registry.list_specs()}

    expected = {
        "startup_os.onboard.interview_plan",
        "startup_os.onboard.context_read",
        "startup_os.onboard.cadence_status",
        "startup_os.onboard.cadence_advisory",
        "startup_os.onboard.session_start",
        "startup_os.onboard.dimension_update",
        "startup_os.onboard.snapshot_create",
        "startup_os.goal.tree_read",
        "startup_os.goal.needing_review",
        "startup_os.goal.advisory",
    }
    assert expected <= ids
    # Founder quyết định tạo Goal / triage Project — không mở cho agent.
    assert "startup_os.goal.create" not in ids
    assert "startup_os.project.triage" not in ids
    assert expected <= set(COSA_COFOUNDER_ASSISTANT_AGENT_SPEC.capability_refs)
