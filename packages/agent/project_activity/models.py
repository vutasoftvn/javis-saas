from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

__all__ = ["ProjectActivityEventRecord"]


class ProjectActivityEventRecord(BaseModel):
    """Bản ghi append-only, đánh số tuần tự theo Project trong
    `agent.project_activity_events` (migration 005) — nguồn sự thật durable
    cho Activity Feed API (Task 5) đọc lại, KHÔNG phải RAM/SSE queue.

    Đây là generic infra tại `packages/agent` — không biết gì về COSA
    (agent_profile, capability_id cụ thể, v.v.). `kind` chỉ là một chuỗi tự
    do do composition layer (`apps/cosa/project_activity/service.py`) quyết
    định theo safe vocabulary của nó; repository không validate vocabulary.

    KHÔNG được thêm cột prompt/content/Vault/tool payload thô vào model này —
    `summary` là allowlist đã redact do caller (service layer) dựng sẵn,
    `payload_hash` chỉ là hash tham chiếu, không phải payload gốc.
    """

    event_id: str = Field(default_factory=lambda: f"pact_{uuid.uuid4().hex[:16]}")
    workspace_id: str
    project_id: str
    # Đánh số tuần tự riêng theo (workspace_id, project_id) — do
    # append_if_absent() gán, KHÔNG set tay. None trước khi ghi.
    project_sequence: int | None = None
    # Khóa idempotency ổn định caller tự dựng, ví dụ
    # f"{source_type}:{source_id}:{kind}:{source_version}" — 1 lần deliver
    # trùng khóa này trả về đúng row gốc, không tiêu tốn sequence mới. Chỉ
    # tồn tại trong `agent.project_activity_idempotency` (claim table), KHÔNG
    # lưu lại trên `agent.project_activity_events` — khi đọc lại record từ
    # bảng events (list_since/PostgresProjectActivityRepository), field này
    # rỗng ("").
    idempotency_key: str = ""
    kind: str
    phase: str | None = None
    status: str | None = None
    actor_kind: str | None = None
    actor_id: str | None = None
    correlation_id: str | None = None
    source_type: str
    source_id: str
    source_version: str
    summary: dict[str, Any] = Field(default_factory=dict)
    classification: str = "internal"
    payload_hash: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
