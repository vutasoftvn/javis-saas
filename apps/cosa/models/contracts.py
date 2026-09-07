"""Task 1 (plan 2026-09-07-local-first-model-routing) — typed contracts cho
model routing per-workspace: `ModelProviderProfile` (1 route model cụ thể,
thuộc đúng 1 workspace), `WorkspaceModelPolicy` (default WORKSPACE hoặc
override AGENT_PROFILE, kèm fallback tường minh) và `ResolvedModelRoute` (kết
quả resolve cuối cùng — không bao giờ chứa secret, chỉ `credential_ref`).

Khác với `packages/agent/contracts/model_policy.py::ModelPolicySpec` (spec
hashed/pin được qua AgentSpec.model_policy_ref, spec_kind="model_policy") —
2 khái niệm độc lập, không thay thế nhau. Xem ghi chú trong task report.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelProviderProfile",
    "ModelRouteNotFound",
    "PolicyScope",
    "ProfileStatus",
    "ProviderType",
    "ResolvedModelRoute",
    "SystemDefaultModelProfile",
    "WorkspaceModelPolicy",
]


class ProviderType(StrEnum):
    LOCAL_OPENAI_COMPATIBLE = "local_openai_compatible"
    ANTHROPIC_API = "anthropic_api"
    OPENAI_API = "openai_api"
    OPENROUTER_API = "openrouter_api"
    DEEPSEEK_API = "deepseek_api"
    CLAUDE_CLI = "claude_cli"
    CODEX_CLI = "codex_cli"
    GEMINI_CLI = "gemini_cli"


class ProfileStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class PolicyScope(StrEnum):
    """`WORKSPACE` = default cho toàn workspace; `AGENT_PROFILE` = override
    cho 1 agent_spec_id cụ thể (ưu tiên cao hơn WORKSPACE khi resolve)."""

    WORKSPACE = "WORKSPACE"
    AGENT_PROFILE = "AGENT_PROFILE"


class ModelProviderProfile(BaseModel):
    """1 route model cụ thể, thuộc đúng 1 workspace — không bao giờ đọc/ghi
    chéo workspace khác. `credential_ref` chỉ là ID/reference tới nơi lưu
    secret thật (Task 2) — KHÔNG BAO GIỜ là giá trị secret/API key thô."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    profile_id: str
    provider_type: ProviderType
    model_id: str
    credential_ref: str | None = None
    allowed_models: tuple[str, ...] = Field(default_factory=tuple)
    budget_usd_limit: float | None = None
    max_concurrency: int | None = None
    status: ProfileStatus = ProfileStatus.ACTIVE


class WorkspaceModelPolicy(BaseModel):
    """Policy resolve theo (workspace_id, scope, scope_key). Fallback CHỈ là
    allowlist tường minh trên chính policy — resolver không tự suy ra
    fallback nào khác ngoài danh sách này."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    scope: PolicyScope
    scope_key: str
    primary_profile_id: str
    fallback_profile_ids: tuple[str, ...] = Field(default_factory=tuple)


class SystemDefaultModelProfile(BaseModel):
    """Bootstrap injected bởi caller khi khởi tạo resolver — dùng làm route
    khi workspace CHƯA cấu hình policy/profile nào. Resolver KHÔNG tự đọc
    env (DEEPSEEK_* hay bất kỳ provider env nào) để chọn route cho
    workspace; giá trị này phải do composition layer tiêm vào (env chỉ được
    phép bootstrap một default hệ thống hoặc test double, không phải chọn
    route theo workspace)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_id: str
    provider_type: ProviderType
    model_id: str
    credential_ref: str | None = None
    allowed_models: tuple[str, ...] = Field(default_factory=tuple)


class ResolvedModelRoute(BaseModel):
    """Kết quả resolve cuối cùng cho 1 (workspace_id, agent_spec_id) — không
    bao giờ chứa secret/credential thô, chỉ `credential_ref`. `extra="forbid"`
    là rào chắn cấu trúc: thêm field bí mật vào model này sau này (vô tình)
    sẽ raise validation error ngay tại biên contract thay vì âm thầm rò rỉ."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: str
    agent_spec_id: str
    profile_id: str
    provider_type: ProviderType
    model_id: str
    credential_ref: str | None = None
    allowed_models: tuple[str, ...] = Field(default_factory=tuple)
    fallback_profile_ids: tuple[str, ...] = Field(default_factory=tuple)


class ModelRouteNotFound(Exception):
    """Fail-closed: profile được tham chiếu (primary/fallback, hoặc profile
    set làm workspace default/agent override) không tồn tại, không thuộc
    đúng workspace này, hoặc không còn ACTIVE. Không có model nào được chọn
    ngầm khi rơi vào trường hợp này."""
