"""GENERATED — KHÔNG SỬA TAY.
Nguồn: shared/contracts/enums.json · Sinh bởi: scripts/gen-contracts.mjs
Đổi enum ⇒ sửa JSON nguồn rồi chạy `node scripts/gen-contracts.mjs` và commit.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "LEGACY_PROJECT_STAGE_TO_CANONICAL",
    "LEGACY_WORKSPACE_STAGE_TO_CANONICAL",
    "LegalEntityStatus",
    "ProjectLifecycleStage",
    "ProjectStatus",
    "RuntimeMode",
    "SyncPolicy",
    "SyncStatus",
    "WorkspaceLifecycleStage",
    "WorkspaceStatus",
]


class WorkspaceLifecycleStage(StrEnum):
    """Vòng đời trưởng thành của Workspace — độc lập với Project và Legal Entity. Cấm alias: company_stage, ventureStage, S0_GENESIS..S5_SCALE."""

    W0_IDEA = "W0_IDEA"
    W1_PROBLEM_VALIDATION = "W1_PROBLEM_VALIDATION"
    W2_SOLUTION_VALIDATION = "W2_SOLUTION_VALIDATION"
    W3_MVP_BUILD = "W3_MVP_BUILD"
    W4_PRODUCT_MARKET_FIT = "W4_PRODUCT_MARKET_FIT"
    W5_SCALE = "W5_SCALE"

    @classmethod
    def from_wire(cls, v: str) -> WorkspaceLifecycleStage:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown WorkspaceLifecycleStage wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class ProjectLifecycleStage(StrEnum):
    """Vòng đời của một Project bên trong Workspace — độc lập với Workspace stage. Prefix P bắt buộc."""

    P0_DISCOVERY = "P0_DISCOVERY"
    P1_PROBLEM_VALIDATION = "P1_PROBLEM_VALIDATION"
    P2_SOLUTION_VALIDATION = "P2_SOLUTION_VALIDATION"
    P3_BUILD_VALIDATE = "P3_BUILD_VALIDATE"
    P4_GO_TO_MARKET = "P4_GO_TO_MARKET"
    P5_OPERATE_GROWTH = "P5_OPERATE_GROWTH"
    P6_SCALE_GOVERN = "P6_SCALE_GOVERN"

    @classmethod
    def from_wire(cls, v: str) -> ProjectLifecycleStage:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown ProjectLifecycleStage wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class WorkspaceStatus(StrEnum):
    """Trạng thái vận hành của Workspace."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    SUSPENDED = "SUSPENDED"

    @classmethod
    def from_wire(cls, v: str) -> WorkspaceStatus:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown WorkspaceStatus wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class ProjectStatus(StrEnum):
    """Trạng thái vận hành của Project."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

    @classmethod
    def from_wire(cls, v: str) -> ProjectStatus:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown ProjectStatus wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class RuntimeMode(StrEnum):
    """Chế độ vận hành Runtime Fabric của Workspace. Không gộp thành một cờ online=true."""

    LOCAL_ONLY = "LOCAL_ONLY"
    REMOTE_ACCESS = "REMOTE_ACCESS"
    CLOUD_CONTINUITY = "CLOUD_CONTINUITY"

    @classmethod
    def from_wire(cls, v: str) -> RuntimeMode:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown RuntimeMode wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class SyncPolicy(StrEnum):
    """Phạm vi dữ liệu được sync ra ngoài host. Credentials không bao giờ sync raw."""

    CONTROL_METADATA_ONLY = "CONTROL_METADATA_ONLY"
    SELECTIVE_ENCRYPTED = "SELECTIVE_ENCRYPTED"
    FULL_ENCRYPTED = "FULL_ENCRYPTED"

    @classmethod
    def from_wire(cls, v: str) -> SyncPolicy:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown SyncPolicy wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class SyncStatus(StrEnum):
    """Trạng thái đồng bộ hiện tại của Workspace."""

    LOCAL_ONLY = "LOCAL_ONLY"
    PENDING = "PENDING"
    IN_SYNC = "IN_SYNC"
    CONFLICT = "CONFLICT"
    ERROR = "ERROR"

    @classmethod
    def from_wire(cls, v: str) -> SyncStatus:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown SyncStatus wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


class LegalEntityStatus(StrEnum):
    """Vòng đời pháp nhân — KHÔNG map thành Workspace stage. Bỏ REGISTRATION_READINESS."""

    DRAFT = "DRAFT"
    REGISTRATION_PREPARATION = "REGISTRATION_PREPARATION"
    REGISTERED_UNVERIFIED = "REGISTERED_UNVERIFIED"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"
    DISSOLVED = "DISSOLVED"

    @classmethod
    def from_wire(cls, v: str) -> LegalEntityStatus:
        try:
            return cls(v)
        except ValueError as exc:  # pragma: no cover - thông điệp lỗi
            raise ValueError(f"Unknown LegalEntityStatus wire value: {v!r}") from exc

    def to_wire(self) -> str:
        return self.value


LEGACY_WORKSPACE_STAGE_TO_CANONICAL: dict[str, str] = {
    "S0_GENESIS": "W0_IDEA",
    "S1_PROBLEM_VALIDATION": "W1_PROBLEM_VALIDATION",
    "S2_SOLUTION_VALIDATION": "W2_SOLUTION_VALIDATION",
    "S3_MVP_BUILD": "W3_MVP_BUILD",
    "S4_PRODUCT_MARKET_FIT": "W4_PRODUCT_MARKET_FIT",
    "S5_SCALE": "W5_SCALE",
}

LEGACY_PROJECT_STAGE_TO_CANONICAL: dict[str, str] = {
    "S0_EXPLORE": "P0_DISCOVERY",
    "S1_PROBLEM_VALIDATION": "P1_PROBLEM_VALIDATION",
    "S2_SOLUTION_VALIDATION": "P2_SOLUTION_VALIDATION",
    "S3_BUSINESS_VALIDATION": "P3_BUILD_VALIDATE",
    "S4_GO_TO_MARKET": "P4_GO_TO_MARKET",
    "S5_OPERATE_GROWTH": "P5_OPERATE_GROWTH",
    "S6_SCALE_GOVERN": "P6_SCALE_GOVERN",
}
