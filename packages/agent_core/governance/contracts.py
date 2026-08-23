from __future__ import annotations

import enum
from typing import Literal, Union

from pydantic import BaseModel, Field


class PinnedSpecIdentity(BaseModel):
    """Định danh bất biến của 1 executable spec (AgentSpec/WorkflowSpec) mà
    1 Run đã resolve tới. `definition_hash` (không phải chỉ `spec_version`)
    là thứ chống silent drift — xem PHẦN I §1 của
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md."""

    spec_kind: Literal["agent", "workflow"]
    spec_id: str
    spec_version: str
    definition_hash: str


class SpecResolutionManifest(BaseModel):
    """Tập PinnedSpecIdentity mà 1 Run/checkpoint đã resolve tới thời điểm
    đó. Chỉ tăng dần (agent-as-tool delegate thêm 1 AgentSpec giữa chừng
    Run là ví dụ điển hình) — không bao giờ xoá entry đã có."""

    entries: tuple[PinnedSpecIdentity, ...] = Field(default_factory=tuple)

    def with_entry(self, entry: PinnedSpecIdentity) -> "SpecResolutionManifest":
        if entry in self.entries:
            return self
        return SpecResolutionManifest(entries=(*self.entries, entry))


class PolicyOutcome(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class RoleApproval(BaseModel):
    kind: Literal["role_approval"] = "role_approval"
    role: str


class UserApproval(BaseModel):
    kind: Literal["user_approval"] = "user_approval"
    user_id: str


class AllOf(BaseModel):
    """Predicate 'phải thoả TẤT CẢ' — dùng để AND hai requirement không so
    sánh được (vd FounderApproval và FinanceAdminApproval), thay vì chọn 1
    trong 2 theo kiểu stricter(a, b) (giả định sai: 2 requirement luôn so
    sánh được theo 1 thang duy nhất)."""

    kind: Literal["all"] = "all"
    predicates: tuple["ApprovalRequirement", ...]


class AnyOf(BaseModel):
    kind: Literal["any"] = "any"
    predicates: tuple["ApprovalRequirement", ...]


class Quorum(BaseModel):
    kind: Literal["quorum"] = "quorum"
    count: int
    roles: tuple[str, ...]


ApprovalRequirement = Union[RoleApproval, UserApproval, AllOf, AnyOf, Quorum]

AllOf.model_rebuild()
AnyOf.model_rebuild()


class PolicyDecision(BaseModel):
    outcome: PolicyOutcome
    requirement: ApprovalRequirement | None = None
    reasons: tuple[str, ...] = Field(default_factory=tuple)


class ApprovalEvidence(BaseModel):
    """Bằng chứng con người đã approve — tách khỏi ApprovalRequirement (dự
    kiến sẽ thoả predicate nào) vì evidence có thể expire (`valid_until`),
    trong khi requirement đã tích luỹ vào G_acc thì không tự hết hạn theo
    thời gian (xem PHẦN I §2.1/§5 của tài liệu governance temporal model).
    `scope` bind evidence vào đúng 1 invocation (thường là tool_call_id)."""

    approver: str
    scope: str
    decided_at: str
    valid_until: str | None = None
