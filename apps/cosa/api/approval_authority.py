"""Approval reviewer authority — kiểm tra quyền quyết định approval theo
`requirement.role`, tách biệt hoàn toàn khỏi `ApprovalService` (service đó chỉ
làm CAS persistence, không phải identity authority — xem
`packages/agent/capabilities/approval_service.py`).

Bug đang vá: `decide_approval` (`apps/cosa/api/workforce_routes.py`) trước đây
chỉ kiểm tra tenant/workspace khớp qua `get_scoped_approval`, KHÔNG hề so sánh
`identity.role_id` với `existing_approval.requirement["role"]` — nghĩa là BẤT
KỲ member nào của đúng workspace đều quyết định được approval yêu cầu role
`founder`. Module này thêm bước kiểm tra đó như một adapter độc lập, mockable.

## Vì sao KHÔNG gọi lại Company Identity ở đây

`AuthenticatedIdentity.role_id` (apps/cosa/auth/dependency.py) ĐÃ LÀ membership
role được server-verify: nó được gán tại `get_authenticated_identity()` từ
`resolved.membership_role`, kết quả một lời gọi thật mỗi request tới
`POST /identity/tenant-context/resolve` (services/company) qua
`WorkspaceTenantContextClient` — client header/body không bao giờ được tin
trực tiếp (xem docstring `AuthenticatedIdentity`, dòng 40-51). Tức là dữ liệu
"role đã resolve server-side" mà một `ApprovalAuthority` cross-plane thật cần
đã có sẵn trên `identity` tại thời điểm handler chạy — gọi thêm một HTTP
round-trip tới Company Identity ở đây chỉ lặp lại đúng việc
`get_authenticated_identity()` vừa làm, không thêm độ tin cậy nào, mà lại tốn
thêm 1 network call mỗi lần quyết định approval. Vì vậy adapter mặc định
(`IdentityRoleApprovalAuthority`) đọc role trực tiếp từ `identity.role_id` (đã
server-verified), KHÔNG đọc từ request body/header/`approval.evidence`.

## Thiết kế Protocol vs. constructor injection

Chữ ký `ApprovalAuthority.allows()` trong bản đặc tả chỉ nhận
`workspace_id`/`principal_id`/`requirement` — không nhận role hay identity đầy
đủ. Vì role cần cho quyết định phải đến từ `identity.role_id` (per-request,
đã server-verified) chứ không thể là singleton wire 1 lần ở plane, adapter cụ
thể (`IdentityRoleApprovalAuthority`) nhận `role_id` qua constructor — hàm gọi
(`decide_approval` trong `workforce_routes.py`) khởi tạo authority mới cho mỗi
request bằng `IdentityRoleApprovalAuthority(role_id=identity.role_id)`. Nhờ
vậy `Protocol` vẫn dùng được để mock/test độc lập (bơm 1 authority giả trả
True/False bất kỳ) mà không cần đụng tới cơ chế auth thật, đúng tinh thần
"pluggable/mockable strategy" của bản đặc tả — không cần wiring ở
`apps/cosa/composition/agent_plane.py` vì không có state nào cần chia sẻ giữa
các request (mỗi request tự tạo authority của riêng nó từ identity của nó).

## Policy default khi `requirement.role` thiếu/malformed/unknown

Không có ADR governance nào định nghĩa sẵn default này — quyết định tại đây,
ghi lại tường minh vì brief yêu cầu:

- `requirement` không phải dict, hoặc không có key `"role"`, hoặc giá trị rỗng
  → FAIL-CLOSED: coi như yêu cầu một trong các role vận hành workspace
  (`_WORKSPACE_OPERATOR_ROLES` = `{"founder", "co-founder", "admin"}`, tái
  dùng từ `apps/cosa/auth/dependency.py`, không định nghĩa lại). Không bao giờ
  implicit-allow cho `member` chỉ vì thiếu thông tin.
- `requirement["role"]` là một chuỗi không nằm trong tập role hệ thống thực sự
  phát hành (`_WORKSPACE_OPERATOR_ROLES ∪ {"member"}`) → coi là malformed/
  unknown, áp dụng CÙNG default fail-closed ở trên (không đoán ý nghĩa của một
  role lạ).
- `requirement["role"]` là một role hợp lệ đã biết → so khớp CHÍNH XÁC
  (case-insensitive) với `identity.role_id` đã normalize. KHÔNG có phân cấp
  ngầm kiểu "operator nào cũng vượt qua yêu cầu role operator khác" — một
  approval yêu cầu đúng `founder` thì `admin` (dù cũng là operator role) vẫn
  bị từ chối, vì `requirement.role` là quyết định nghiệp vụ tường minh của
  người tạo approval, không phải một ngưỡng rủi ro chung chung.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException, status

from apps.cosa.auth.dependency import _WORKSPACE_OPERATOR_ROLES, AuthenticatedIdentity

__all__ = [
    "ApprovalAuthority",
    "IdentityRoleApprovalAuthority",
    "require_approval_authority",
]

# Role hệ thống thực sự phát hành (xem `_WORKSPACE_OPERATOR_ROLES` +
# "member") — dùng để phân biệt "role hợp lệ nhưng không khớp" (từ chối rõ
# ràng) với "role lạ/malformed" (fail-closed theo default).
_KNOWN_ROLES = frozenset(_WORKSPACE_OPERATOR_ROLES | {"member"})


class ApprovalAuthority(Protocol):
    """Chiến lược quyết định "reviewer này có đủ quyền quyết định approval
    này không" — tách khỏi FastAPI layer để mock/test độc lập."""

    async def allows(
        self, *, workspace_id: str, principal_id: str, requirement: dict[str, object]
    ) -> bool: ...


class IdentityRoleApprovalAuthority:
    """Adapter mặc định: so khớp `requirement["role"]` với membership role đã
    server-verify của reviewer hiện tại (`identity.role_id`).

    `role_id` được truyền qua constructor (không qua `allows()`) vì đây là
    role của MỘT identity cụ thể tại thời điểm request — không phải state
    dùng chung giữa nhiều request, nên không cần (và không nên) wiring ở
    `CosaAgentPlane`. Xem docstring module để biết vì sao không gọi lại
    Company Identity ở đây."""

    def __init__(self, *, role_id: str | None) -> None:
        self._reviewer_role = (role_id or "").strip().lower()

    async def allows(
        self, *, workspace_id: str, principal_id: str, requirement: dict[str, object]
    ) -> bool:
        del workspace_id, principal_id  # không cần cho quyết định role — giữ trong
        # chữ ký để tuân thủ Protocol và cho phép audit log ở call site khác dùng
        # adapter tương lai (vd. adapter cross-plane thật sự cần các field này).
        required_role = _resolve_required_role(requirement)
        return self._reviewer_role in required_role


def _resolve_required_role(requirement: dict[str, object]) -> frozenset[str]:
    """Trả về tập role được CHẤP NHẬN để quyết định approval này.

    - Role hợp lệ, đã biết → tập chỉ gồm chính role đó (so khớp chính xác).
    - Thiếu/malformed/unknown → fail-closed về `_WORKSPACE_OPERATOR_ROLES`.
    """
    raw_role = requirement.get("role") if isinstance(requirement, dict) else None
    if not isinstance(raw_role, str) or not raw_role.strip():
        return _WORKSPACE_OPERATOR_ROLES
    normalized = raw_role.strip().lower()
    if normalized not in _KNOWN_ROLES:
        return _WORKSPACE_OPERATOR_ROLES
    return frozenset({normalized})


async def require_approval_authority(
    authority: ApprovalAuthority, identity: AuthenticatedIdentity, requirement: dict[str, object]
) -> None:
    """Raise 403 nếu `authority` từ chối cho `identity` quyết định approval có
    `requirement` này. Gọi TRƯỚC bất kỳ side effect nào (`submit_decision`)."""
    allowed = await authority.allows(
        workspace_id=identity.workspace_id,
        principal_id=identity.principal_id,
        requirement=requirement,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="reviewer does not have required role for this approval",
        )
