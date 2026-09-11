from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from agent.project_activity.models import ProjectActivityEventRecord
from agent.project_activity.repository import ProjectActivityRepository

__all__ = [
    "SAFE_ACTIVITY_KINDS",
    "UNKNOWN_ACTIVITY_KIND",
    "ProjectActivityService",
]

logger = logging.getLogger(__name__)

# Safe event vocabulary (task brief Step 4) — chỉ những runtime fact đã được
# xác nhận durable (message/run/checkpoint/tool call/approval record đã
# persist) mới được map vào đây. KHÔNG thêm kind mới ở đây mà không xác nhận
# nó tương ứng đúng 1 canonical record đã ghi bền.
SAFE_ACTIVITY_KINDS = frozenset(
    {
        "chat.accepted",
        "run.queued",
        "run.started",
        "run.checkpointed",
        "run.waiting_approval",
        "tool.requested",
        "tool.policy_allowed",
        "tool.policy_denied",
        "approval.requested",
        "approval.resolved",
        "run.completed",
        "run.failed",
        "run.cancelled",
    }
)

# Runtime kind không nằm trong vocabulary trên vẫn được ghi lại — nhưng chỉ
# dưới dạng "system delivery" tổng quát kèm hash tham chiếu, KHÔNG bao giờ
# mang payload thô (đúng yêu cầu "Unknown runtime events produce a redacted
# system-delivery activity row with a hash/reference, never arbitrary raw
# payload").
UNKNOWN_ACTIVITY_KIND = "system.delivery"

# Allowlist NGHIÊM NGẶT HƠN redact_ux_event_payload() (apps/cosa/api/event_stream.py)
# — đó là blocklist (loại bỏ key nhạy cảm biết trước, giữ lại phần còn lại).
# Ở đây là allowlist (chỉ những key liệt kê tường minh mới lọt qua) — bất kỳ
# key nào không có trong danh sách này (bao gồm input_payload/content/prompt/
# raw_secret/access_token/Vault reference chưa biết trước) đều bị loại, kể cả
# khi caller quên chưa liệt nó vào danh sách nhạy cảm.
_SUMMARY_ALLOWLIST = frozenset(
    {
        "status",
        "reason",
        "reason_code",
        "capability_id",
        "agent_profile",
        "role",
        "message_id",
        "checkpoint_ref",
        "tool_call_id",
        "approval_id",
        "decision",
        "outcome",
        "error_code",
        "step_name",
        "run_id",
    }
)


def _redact_summary(safe_kind: str, raw_context: dict[str, Any] | None) -> dict[str, Any]:
    """Allowlist redaction — chỉ scalar value của key đã liệt kê tường minh
    mới được giữ lại. Unknown kind (system.delivery) không giữ summary nào,
    chỉ payload_hash làm tham chiếu."""
    if not raw_context or safe_kind == UNKNOWN_ACTIVITY_KIND:
        return {}

    safe: dict[str, Any] = {}
    for key, value in raw_context.items():
        if key not in _SUMMARY_ALLOWLIST:
            continue
        if isinstance(value, (dict, list)):
            # Chỉ scalar — không cho nested structure lọt qua allowlist, tránh
            # 1 dict lồng bên trong 1 key hợp lệ mang theo payload thô.
            continue
        safe[key] = value
    return safe


def _hash_payload(raw_context: dict[str, Any] | None) -> str:
    return hashlib.sha256(
        json.dumps(raw_context or {}, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


class ProjectActivityService:
    """Composition-layer service (apps/cosa) map runtime facts (chat/run/
    checkpoint/tool/approval) thành Project Activity event an toàn, redact
    trước khi ghi qua `ProjectActivityRepository.append_if_absent`.

    `packages/agent/project_activity/*` là generic infra không biết gì về
    COSA vocabulary — mọi quyết định "kind nào an toàn, field nào lọt qua
    redaction" đều nằm ở đây, đúng ranh giới packages/agent vs apps/cosa
    (CLAUDE.md "Bốn vùng kiến trúc").
    """

    def __init__(self, repository: ProjectActivityRepository) -> None:
        self._repository = repository

    async def record_runtime_event(
        self,
        *,
        workspace_id: str,
        project_id: str,
        kind: str,
        source_type: str,
        source_id: str,
        source_version: str,
        phase: str | None = None,
        status: str | None = None,
        actor_kind: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
        raw_context: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> ProjectActivityEventRecord:
        """Ghi 1 runtime fact thành Project Activity event, idempotent theo
        (workspace_id, project_id, source_type, source_id, kind,
        source_version). Chỉ gọi hàm này SAU KHI canonical record (message/
        run/checkpoint/tool call/approval) đã persist — caller chịu trách
        nhiệm đảm bảo thứ tự này (xem apps/cosa/api/conversation_routes.py,
        apps/cosa/api/event_stream.py)."""
        if kind not in SAFE_ACTIVITY_KINDS:
            logger.info(
                "project_activity: unrecognized runtime kind '%s' from %s:%s — recording as %s",
                kind,
                source_type,
                source_id,
                UNKNOWN_ACTIVITY_KIND,
            )
            safe_kind = UNKNOWN_ACTIVITY_KIND
        else:
            safe_kind = kind

        summary = _redact_summary(safe_kind, raw_context)
        idempotency_key = f"{source_type}:{source_id}:{safe_kind}:{source_version}"

        event = ProjectActivityEventRecord(
            workspace_id=workspace_id,
            project_id=project_id,
            idempotency_key=idempotency_key,
            kind=safe_kind,
            phase=phase,
            status=status,
            actor_kind=actor_kind,
            actor_id=actor_id,
            correlation_id=correlation_id,
            source_type=source_type,
            source_id=source_id,
            source_version=source_version,
            summary=summary,
            classification="internal" if safe_kind == UNKNOWN_ACTIVITY_KIND else "activity",
            payload_hash=_hash_payload(raw_context),
            occurred_at=occurred_at or datetime.now(UTC),
        )
        return await self._repository.append_if_absent(event)
