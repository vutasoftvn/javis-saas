"""EventRunEnvelope & contract helpers for event-driven agent runs (R1 / F04).

Defines the exact immutable envelope schema between event intake/producer,
control plane scheduler, and worker execution plane.
"""

from __future__ import annotations

from typing import Any, Literal
import fastuuid
from pydantic import BaseModel, ConfigDict


class EventRunEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    task_type: Literal["run"] = "run"
    run_id: str
    workspace_id: str
    event_id: str
    trigger_rule_id: str
    agent_profile: str
    agent_spec_id: str
    agent_spec_version: str
    agent_spec_hash: str
    aggregate_type: str
    aggregate_id: str
    correlation_id: str


SPEC_ID_TO_AGENT_PROFILE: dict[str, str] = {
    "cosa.agents.customer_support": "customer_support",
    "cosa.agents.customer_support_autopilot": "customer_support_autopilot",
    "cosa.agents.operations": "operations",
    "cosa.agents.finance": "finance",
    "cosa.agents.marketing": "marketing",
}

SUPPORTED_AGENT_PROFILES: set[str] = set(SPEC_ID_TO_AGENT_PROFILE.values())


def resolve_agent_profile(spec_id: str) -> str | None:
    return SPEC_ID_TO_AGENT_PROFILE.get(spec_id)


def compute_deterministic_run_id() -> str:
    """Generate a UUIDv7 run_id for new runs."""
    return f"run_{fastuuid.uuid7().hex[:16]}"


def build_event_run_envelope(
    *,
    rule: Any,
    env: Any,
    run_id: str | None = None,
) -> EventRunEnvelope:
    spec_id = getattr(getattr(rule, "agent_spec", None), "id", None) or ""
    spec_ver = getattr(getattr(rule, "agent_spec", None), "version", None) or "1.0.0"
    spec_hash = getattr(getattr(rule, "agent_spec", None), "definition_hash", None) or ""

    agent_profile = resolve_agent_profile(spec_id)
    if not agent_profile:
        raise ValueError(f"unsupported agent spec id: {spec_id!r}")

    assigned_run_id = run_id or compute_deterministic_run_id()

    return EventRunEnvelope(
        schema_version=1,
        task_type="run",
        run_id=assigned_run_id,
        workspace_id=str(getattr(env, "workspaceId", "")),
        event_id=str(getattr(env, "eventId", "")),
        trigger_rule_id=str(getattr(rule, "rule_id", "")),
        agent_profile=agent_profile,
        agent_spec_id=spec_id,
        agent_spec_version=spec_ver,
        agent_spec_hash=spec_hash,
        aggregate_type=str(getattr(env, "aggregateType", "")),
        aggregate_id=str(getattr(env, "aggregateId", "")),
        correlation_id=str(getattr(env, "correlationId", "")),
    )


def adapt_event_task_payload(
    payload: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    """Adapts an incoming scheduler task payload into an execution-ready run payload.

    Supports:
    - schema_version=1 EventRunEnvelope payloads
    - Legacy kind='event_trigger' payloads (with sufficient references)

    Returns:
    - (adapted_payload, None) on success
    - (None, rejection_reason) if profile is unsupported or essential data missing (quarantine)
    """
    is_v1 = payload.get("schema_version") == 1
    is_legacy = payload.get("kind") == "event_trigger"
    is_event_trigger = (
        is_v1 or is_legacy or ("event_id" in payload and "trigger_rule_id" in payload)
    )

    if not is_event_trigger:
        return payload, None

    # Workspace validation
    workspace_id = payload.get("workspace_id")
    if not workspace_id:
        return None, "quarantined: missing workspace_id in event payload"

    # Profile & Spec resolution
    agent_profile = payload.get("agent_profile")
    spec_id = payload.get("agent_spec_id")
    if not spec_id and isinstance(payload.get("agent_spec"), dict):
        spec_id = payload["agent_spec"].get("id")

    if not agent_profile and spec_id:
        agent_profile = resolve_agent_profile(spec_id)

    if not agent_profile or agent_profile not in SUPPORTED_AGENT_PROFILES:
        return None, f"unsupported agent profile {agent_profile!r} (spec_id: {spec_id!r})"

    # Run ID resolution
    run_id = payload.get("run_id")
    if not run_id:
        event_id = payload.get("event_id")
        rule_id = payload.get("trigger_rule_id")
        if not event_id or not rule_id:
            return None, "quarantined: missing event_id or trigger_rule_id to resolve run_id"
        run_id = compute_deterministic_run_id()

    adapted = dict(payload)
    adapted["task_type"] = "run"
    adapted["run_id"] = run_id
    adapted["agent_profile"] = agent_profile
    adapted["workspace_id"] = workspace_id
    if spec_id and "agent_spec_id" not in adapted:
        adapted["agent_spec_id"] = spec_id

    # Aggregate resolution
    agg_type = payload.get("aggregate_type")
    if not agg_type and isinstance(payload.get("aggregate_ref"), dict):
        agg_type = payload["aggregate_ref"].get("type")
    agg_id = payload.get("aggregate_id")
    if not agg_id and isinstance(payload.get("aggregate_ref"), dict):
        agg_id = payload["aggregate_ref"].get("id")

    if agg_type in ("engagement.thread", "engagement_thread", "thread") and agg_id:
        if "thread_ref" not in adapted:
            adapted["thread_ref"] = {"thread_id": agg_id}

    if "principal" not in adapted:
        adapted["principal"] = f"system:{agent_profile}:{workspace_id}"

    if "conversation_id" not in adapted:
        adapted["conversation_id"] = f"conv_{run_id}"

    # IA24: event Operations/Finance/Marketing không có ai "gõ" user_prompt —
    # trước đây payload này thiếu hẳn field user_prompt, và
    # apps/cosa/worker/handlers.py::_execute_run_task_inner đọc
    # payload["user_prompt"] trực tiếp (không .get()), nên run KeyError trước
    # khi chạm nghiệp vụ. Tổng hợp một prompt tối thiểu nêu rõ aggregate nào
    # đã kích hoạt run — agent tự dùng capability đọc phù hợp (đã đăng ký cho
    # từng agent_profile) để lấy chi tiết đầy đủ, thay vì nhồi toàn bộ dữ liệu
    # aggregate vào đây (điều đó cần "shared preparation" resolve theo từng
    # loại aggregate — phạm vi lớn hơn, chưa làm ở đây).
    if "user_prompt" not in adapted or not adapted.get("user_prompt"):
        adapted["user_prompt"] = (
            f"Sự kiện nghiệp vụ đã kích hoạt run này: aggregate_type={agg_type!r}, "
            f"aggregate_id={agg_id!r}, trigger_rule_id={payload.get('trigger_rule_id')!r}. "
            "Dùng capability đọc phù hợp để lấy đầy đủ chi tiết trước khi hành động."
        )

    return adapted, None
