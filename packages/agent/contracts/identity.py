from __future__ import annotations

from pydantic import BaseModel

from agent.governance.contracts import PinnedSpecIdentity, SpecResolutionManifest

__all__ = [
    "InvocationIdentity",
    "PinnedSkillRef",
    "PinnedSpecIdentity",
    "SpecResolutionManifest",
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
    connector_id: str | None = None
    connection_id: str | None = None
    idempotency_key: str | None = None
    checkpoint_ref: str | None = None


class PinnedSkillRef(BaseModel):
    """Tham chiếu bất biến từ `AgentSpec.pinned_skills` tới 1 SkillSpec đã publish
    (ADR-SKILL-IDENTITY §4, Phương án A — kích hoạt 2026-08-24). `definition_hash`
    BẮT BUỘC khớp tuyệt đối tại thời điểm resolve — không cho phép floating
    reference (load skill "mới nhất" theo id, không kiểm hash). Đặt ở đây (không
    phải packages/agent/skills/) vì `contracts/` là tầng nền, không phụ
    thuộc ngược vào subsystem `skills/`."""

    skill_id: str
    version: str
    definition_hash: str

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Adapter sang PinnedSpecIdentity(spec_kind="skill") — dùng khi cần
        đưa 1 pinned skill vào SpecDependencyEdge chung với các dependency
        kind khác (prompt/model_policy/tool_contract), theo
        ADR-ARTIFACT-IDENTITY-001 §3. Không đổi PinnedSkillRef hiện có —
        AgentSpec.pinned_skills vẫn dùng type gốc."""
        return PinnedSpecIdentity(
            spec_kind="skill",
            spec_id=self.skill_id,
            spec_version=self.version,
            definition_hash=self.definition_hash,
        )
