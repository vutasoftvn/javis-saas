"""Document + SOP lifecycle — M3 §5.

Trạng thái lifecycle là **structured enum + bảng transition xác định** (guardrail 7:
không suy diễn từ văn bản tự nhiên, không `if "published" in text`).

Document: `QUARANTINED → SCANNED → REVIEW_PENDING → PUBLISHED → ARCHIVED → PURGED`.
Sau `PUBLISHED`, file nguồn phải được copy có kiểm chứng từ quarantine vào Vault và
`source_uri` phải mang workspace/object identity (không dùng URI thiếu workspace) —
`assert_publishable()` chặn publish khi thiếu.

SOP là first-class resource với ID = SpineId Snowflake (do `services/company` sinh —
ở đây chỉ model là `int`). Status: `DRAFT → REVIEW → ACTIVE → RETIRED`.
CHỈ SOP `ACTIVE` được đưa vào procedural instructions/capability context —
`select_procedural_sops()` là chỗ lọc duy nhất.

Không import `services/*`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "DocumentState",
    "LifecycleError",
    "SopDefinition",
    "SopStatus",
    "SopVersion",
    "advance_document_state",
    "advance_sop_status",
    "assert_publishable",
    "select_procedural_sops",
]


class LifecycleError(Exception):
    """Transition lifecycle không hợp lệ hoặc vi phạm tiền điều kiện."""


class DocumentState(StrEnum):
    QUARANTINED = "QUARANTINED"
    SCANNED = "SCANNED"
    REVIEW_PENDING = "REVIEW_PENDING"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    PURGED = "PURGED"


# Transition cho phép. Forward theo chuỗi chuẩn + vài nhánh nghiệp vụ:
# - SCANNED → QUARANTINED: lần scan sau phát hiện vấn đề, đưa lại cách ly.
# - REVIEW_PENDING → QUARANTINED: reviewer từ chối, trả về cách ly.
# - PUBLISHED → REVIEW_PENDING: có version mới cần duyệt lại.
_DOCUMENT_TRANSITIONS: dict[DocumentState, frozenset[DocumentState]] = {
    DocumentState.QUARANTINED: frozenset({DocumentState.SCANNED, DocumentState.PURGED}),
    DocumentState.SCANNED: frozenset(
        {DocumentState.REVIEW_PENDING, DocumentState.QUARANTINED, DocumentState.PURGED}
    ),
    DocumentState.REVIEW_PENDING: frozenset(
        {DocumentState.PUBLISHED, DocumentState.QUARANTINED, DocumentState.ARCHIVED}
    ),
    DocumentState.PUBLISHED: frozenset({DocumentState.ARCHIVED, DocumentState.REVIEW_PENDING}),
    DocumentState.ARCHIVED: frozenset({DocumentState.PURGED}),
    DocumentState.PURGED: frozenset(),
}


def advance_document_state(current: DocumentState, target: DocumentState) -> DocumentState:
    """Kiểm tra transition hợp lệ, trả về `target`. Không hợp lệ ⇒ `LifecycleError`."""
    if not isinstance(current, DocumentState) or not isinstance(target, DocumentState):
        raise LifecycleError("current/target phải là DocumentState")
    if target == current:
        return current  # no-op idempotent
    allowed = _DOCUMENT_TRANSITIONS[current]
    if target not in allowed:
        raise LifecycleError(
            f"transition {current.value} → {target.value} không hợp lệ "
            f"(cho phép: {sorted(s.value for s in allowed)})"
        )
    return target


def assert_publishable(*, vault_object_ref: str | None, source_uri: str | None) -> None:
    """Tiền điều kiện để chuyển sang `PUBLISHED`: file nguồn đã nằm trong Vault
    (có `vault_object_ref`) và `source_uri` mang workspace/object identity
    (`workspaces/<id>/…`). Thiếu ⇒ `LifecycleError`."""
    if not vault_object_ref:
        raise LifecycleError(
            "không thể PUBLISHED: chưa có vault_object_ref (file nguồn phải copy "
            "có kiểm chứng từ quarantine vào Vault trước)"
        )
    if not source_uri or "workspaces/" not in source_uri:
        raise LifecycleError(
            "không thể PUBLISHED: source_uri phải mang workspace/object identity "
            "('workspaces/<id>/…'), không dùng URI thiếu workspace"
        )


class SopStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


# - DRAFT → REVIEW → ACTIVE → RETIRED (chuẩn)
# - REVIEW → DRAFT: reviewer trả về sửa.
# - ACTIVE → REVIEW: soạn bản thay thế, bản cũ vẫn ACTIVE tới khi bản mới ACTIVE.
# - RETIRED → DRAFT: mở lại để soạn phiên bản kế thừa.
_SOP_TRANSITIONS: dict[SopStatus, frozenset[SopStatus]] = {
    SopStatus.DRAFT: frozenset({SopStatus.REVIEW, SopStatus.RETIRED}),
    SopStatus.REVIEW: frozenset({SopStatus.ACTIVE, SopStatus.DRAFT, SopStatus.RETIRED}),
    SopStatus.ACTIVE: frozenset({SopStatus.RETIRED, SopStatus.REVIEW}),
    SopStatus.RETIRED: frozenset({SopStatus.DRAFT}),
}


@dataclass
class SopVersion:
    id: int  # SpineId Snowflake
    workspace_id: int
    sop_id: int
    content_object_ref: str
    normalized_object_ref: str | None = None
    checksum: str | None = None
    effective_from: str | None = None
    approved_by: int | None = None  # workforce_member_id; None ⇒ chưa duyệt

    @property
    def is_approved(self) -> bool:
        return self.approved_by is not None


@dataclass
class SopDefinition:
    id: int  # SpineId Snowflake
    workspace_id: int
    title: str
    owner_member_id: int
    status: SopStatus = SopStatus.DRAFT
    current_version_id: int | None = None
    risk_class: str = "standard"
    approval_policy: str | None = None
    versions: list[SopVersion] = field(default_factory=list)

    def _version(self, version_id: int) -> SopVersion | None:
        return next((v for v in self.versions if v.id == version_id), None)


def advance_sop_status(sop: SopDefinition, target: SopStatus) -> SopStatus:
    """Chuyển status SOP. Sang `ACTIVE` yêu cầu `current_version_id` trỏ tới một
    `SopVersion` đã được duyệt (`approved_by` != None) và cùng workspace."""
    current = sop.status
    if not isinstance(target, SopStatus):
        raise LifecycleError("target phải là SopStatus")
    if target == current:
        return current
    if target not in _SOP_TRANSITIONS[current]:
        raise LifecycleError(
            f"SOP transition {current.value} → {target.value} không hợp lệ "
            f"(cho phép: {sorted(s.value for s in _SOP_TRANSITIONS[current])})"
        )
    if target == SopStatus.ACTIVE:
        if sop.current_version_id is None:
            raise LifecycleError("không thể ACTIVE: SOP chưa có current_version_id")
        version = sop._version(sop.current_version_id)
        if version is None:
            raise LifecycleError(
                f"không thể ACTIVE: current_version_id={sop.current_version_id} "
                "không có trong versions"
            )
        if version.workspace_id != sop.workspace_id:
            raise LifecycleError("không thể ACTIVE: version khác workspace với SOP")
        if not version.is_approved:
            raise LifecycleError("không thể ACTIVE: current version chưa được duyệt (approved_by)")
    sop.status = target
    return target


def select_procedural_sops(
    sops: Iterable[SopDefinition], *, workspace_id: int | None = None
) -> list[SopDefinition]:
    """Lọc SOP được phép đưa vào procedural instructions/capability context.

    CHỈ status `ACTIVE`. `DRAFT`/`REVIEW`/`RETIRED` KHÔNG được agent coi là policy
    đang hiệu lực. Nếu truyền `workspace_id` thì lọc luôn theo workspace (chặn
    rò rỉ SOP cross-workspace vào context)."""
    out: list[SopDefinition] = []
    for sop in sops:
        if sop.status != SopStatus.ACTIVE:
            continue
        if workspace_id is not None and sop.workspace_id != workspace_id:
            continue
        out.append(sop)
    return out


def active_sop_titles(
    sops: Sequence[SopDefinition], *, workspace_id: int | None = None
) -> list[str]:
    """Tiện ích: tiêu đề các SOP ACTIVE (đã lọc) — dùng khi dựng prompt context."""
    return [s.title for s in select_procedural_sops(sops, workspace_id=workspace_id)]
