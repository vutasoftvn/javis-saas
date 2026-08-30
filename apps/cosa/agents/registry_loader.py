"""Load một AgentSpec đã publish trong spec registry thành model có kiểu.

Worker chỉ cần AgentSpec để guard defense-in-depth (đọc capability_refs),
không cần exact-hash resolution như SpecResolver. Trả về reason code có cấu
trúc thay vì nuốt lỗi bằng `except` (CLAUDE.md rule 7)."""

from __future__ import annotations

from typing import Any

from agent.contracts.spec import AgentSpec

__all__ = ["load_registered_agent_spec"]


async def load_registered_agent_spec(
    spec_registry: Any,
    spec_id: str,
    *,
    version: str,
) -> tuple[AgentSpec | None, str | None]:
    record = await spec_registry.get("agent", spec_id, version)
    if record is None:
        return None, "agent_spec_not_registered"
    try:
        return AgentSpec.model_validate(record.content), None
    except Exception:  # pydantic ValidationError + mọi lỗi dựng model
        return None, "agent_spec_content_invalid"
