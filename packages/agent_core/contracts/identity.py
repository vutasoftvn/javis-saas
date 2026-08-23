from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity, SpecResolutionManifest

__all__ = [
    "PinnedSpecIdentity",
    "SpecResolutionManifest",
    "InvocationIdentity",
]


class InvocationIdentity(BaseModel):
    """Định danh L2 của 1 invocation cụ thể theo Master Guide §7.
    
    Bắt buộc phải bind tối thiểu:
    - run_id: Định danh của Run chứa invocation.
    - tool_call_id: Định danh ổn định của lần gọi tool/capability cụ thể.
    - capability_id: Định danh của Capability được gọi.
    - payload_hash: Canonical SHA-256 hash của arguments/payload.

    Mở rộng tuỳ chọn khi có:
    - connector_id / connection_id: Định danh connector và tài khoản kết nối.
    - idempotency_key: Khóa chống trùng lặp side effect.
    - checkpoint_ref: Checkpoint mà invocation này được kích hoạt hoặc tạo ra.
    """

    run_id: str
    tool_call_id: str
    capability_id: str
    payload_hash: str
    connector_id: Optional[str] = None
    connection_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    checkpoint_ref: Optional[str] = None
