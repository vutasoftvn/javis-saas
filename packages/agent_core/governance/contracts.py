from __future__ import annotations

import enum
import uuid
from typing import Literal, Union

from pydantic import BaseModel, Field


class PinnedSpecIdentity(BaseModel):
    """Định danh bất biến của 1 artifact đã publish (AgentSpec/WorkflowSpec/
    SkillSpec/PromptSpec/ModelPolicySpec/ToolContractSpec/EvalSuite) mà 1 Run đã
    resolve tới hoặc 1 EvalRun tham chiếu tới. `definition_hash` (không phải chỉ
    `spec_version`) là thứ chống silent drift — xem PHẦN I §1 của
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md và ADR-ARTIFACT-IDENTITY-001
    (không tạo ArtifactIdentity/ArtifactRef riêng, tổng quát hóa type này thay vào đó).

    EvalSuite (Wave M3) dùng spec_kind="eval_suite" nhưng KHÔNG bao giờ ghi vào
    SpecResolutionManifest/agent_core_governance.spec_resolution_manifest_entries
    (bảng đó chỉ dành cho identity một Run đã resolve — eval là offline artifact,
    không phải runtime resolution) — vì vậy KHÔNG cần mở rộng CHECK constraint
    của bảng đó, khác với "skill"/"prompt"/"model_policy"/"tool_contract" đã mở
    rộng ở Wave M1 (đúng ADR-ARTIFACT-IDENTITY-001 §2.4)."""

    spec_kind: Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract", "eval_suite"]
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
    NON_APPROVABLE = "NON_APPROVABLE"


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



class AutonomyLevel(str, enum.Enum):
    """Mức tự chủ của Agent theo Master Guide §13.1 (không phải RBAC của user)."""
    L0 = "L0"  # Observe / Read only
    L1 = "L1"  # Propose / Draft
    L2 = "L2"  # Execute with approval
    L3 = "L3"  # Autonomous execution

    # Aliases cho khả năng tương thích
    L0_OBSERVE = "L0"
    L1_PROPOSE = "L1"
    L2_EXECUTE = "L2"
    L2_EXECUTE_WITH_APPROVAL = "L2"
    L3_AUTONOMOUS = "L3"
    L3_EXECUTE = "L3"


class CapabilityRisk(str, enum.Enum):
    """Mức độ rủi ro nội tại của Capability/Action theo Master Guide §13.2."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalPolicy(str, enum.Enum):
    """Chính sách phê duyệt cho Capability/Step theo Master Guide §13.3."""
    NEVER = "never"
    ALWAYS = "always"
    CONDITIONAL = "conditional"
    POLICY_DRIVEN = "policy_driven"


class PrincipalAuthorization(str, enum.Enum):
    """Phạm vi phân quyền của Principal đối với công cụ/hành vi."""
    READ_ONLY = "read_only"
    SCOPED_WRITE = "scoped_write"
    ADMIN_WRITE = "admin_write"


class ExecutionMode(str, enum.Enum):
    """Chế độ thực thi của Run/Agent."""
    AUTONOMOUS = "autonomous"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    SUPERVISED = "supervised"
    APPROVED_WORKFLOW = "approved_workflow"
    WORKFLOW = "workflow"
    AGENT = "agent"




class DataScope(str, enum.Enum):
    """Phạm vi truy cập dữ liệu của Run/Capability."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    WORKSPACE_LOCAL = "workspace_local"


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

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    approver: str
    scope: str
    decided_at: str
    valid_until: str | None = None


class SpecDependencyEdge(BaseModel):
    """Một cạnh lineage: `owner` phụ thuộc vào `dependency` với quan hệ
    `relation` (vd "uses_prompt", "pins_skill", "uses_model_policy",
    "uses_tool_contract") — theo ADR-ARTIFACT-IDENTITY-001 §2.5. Dùng ở Wave
    M2 khi publish AgentSpec để ghi lại dependency graph phục vụ audit/lineage
    query, KHÔNG dùng để lưu vào SpecResolutionManifest của một Run (hai khái
    niệm khác nhau: manifest là identity một Run đã resolve tới; edge này là
    quan hệ tĩnh giữa hai artifact đã publish)."""

    model_config = {"frozen": True}

    owner: PinnedSpecIdentity
    dependency: PinnedSpecIdentity
    relation: str

