"""Company-backed Project verifier dùng chung cho mọi route Founder Hub cần
Project context thật (2026-09-11 Project-scoped Founder Hub, Task 2).

`packages/agent` KHÔNG được biết gì về Company authorization (CLAUDE.md quy
tắc 1) — verifier này CỐ Ý sống ở API composition layer (`apps/cosa/api`), gọi
thẳng `CompanyServiceClient` (đã có sẵn, dùng chung với capability khác) tới
boundary đọc Project thật của `services/company`
(`GET /operations/projects/:id`, xem `services/company/operations/handlers/
project.handler.ts` + `project-access.service.ts::getProjectInWorkspace` —
404 nếu Project không tồn tại HOẶC không thuộc workspace của caller, không
phân biệt 2 trường hợp để không lộ thông tin tồn tại/không tồn tại).

KHÔNG dùng title Project, local storage phía client, danh sách workspace
chung chung, hay chuỗi exception làm bằng chứng authorization — chỉ tin phản
hồi có cấu trúc từ chính endpoint đọc Project đã cross-check workspace.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from apps.cosa.capabilities.client import CompanyServiceError

__all__ = [
    "PROJECT_CONTEXT_MISMATCH",
    "PROJECT_CONTEXT_REQUIRED",
    "PROJECT_NOT_FOUND_OR_FORBIDDEN",
    "ProjectContextHttpError",
    "VerifiedProjectContext",
    "require_project_context_match",
    "verify_project_context",
]

_WORKSPACE_NAME_TTL_S = 300.0
_WORKSPACE_NAME_CACHE_MAX = 512
# workspace_id -> (hạn dùng theo monotonic, tên)
_WORKSPACE_NAME_CACHE: dict[str, tuple[float, str]] = {}

PROJECT_CONTEXT_REQUIRED = "PROJECT_CONTEXT_REQUIRED"
PROJECT_CONTEXT_MISMATCH = "PROJECT_CONTEXT_MISMATCH"
PROJECT_NOT_FOUND_OR_FORBIDDEN = "PROJECT_NOT_FOUND_OR_FORBIDDEN"


class ProjectContextHttpError(HTTPException):
    """HTTPException với `detail` structured `{code, message}` — machine-
    readable, ổn định qua thời gian (client dựa vào `code`, không parse chuỗi
    message tự do)."""

    def __init__(self, status_code: int, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(status_code=status_code, detail={"code": code, "message": message or code})


@dataclass(frozen=True)
class VerifiedProjectContext:
    """Project đã được `services/company` xác nhận thuộc đúng workspace của
    caller — KHÔNG suy diễn/tự dựng, chỉ map từ response thật."""

    project_id: str
    workspace_id: str
    title: str | None = None
    # Chỉ để hiển thị/gọi tên trong hội thoại — không phải bằng chứng authorization.
    workspace_name: str | None = None


async def verify_project_context(
    plane: Any, identity: Any, project_id: str | None
) -> VerifiedProjectContext:
    """Bắt buộc + verify Project qua Company boundary thật.

    - `project_id` rỗng/None -> 422 PROJECT_CONTEXT_REQUIRED (fail trước khi
      chạm bất kỳ side effect nào — không gọi Company).
    - Company trả lỗi (network, 404, 403, không parse được) -> 404
      PROJECT_NOT_FOUND_OR_FORBIDDEN — cố ý KHÔNG phân biệt "không tồn tại"
      với "không thuộc workspace này" (không disclosure ownership, cùng
      nguyên tắc với `getProjectInWorkspace` phía services/company).
    """
    if not project_id or not project_id.strip():
        raise ProjectContextHttpError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            PROJECT_CONTEXT_REQUIRED,
            "project_id is required",
        )

    company_client = getattr(plane, "company_client", None)
    if company_client is None:
        raise ProjectContextHttpError(
            status.HTTP_404_NOT_FOUND,
            PROJECT_NOT_FOUND_OR_FORBIDDEN,
            "Project not found or not authorized",
        )

    try:
        resp = await company_client.get(
            f"/operations/projects/{project_id}",
            headers={
                "Authorization": f"Bearer {identity.mint_delegation()}",
                "X-Workspace-Id": identity.workspace_id,
            },
        )
    except CompanyServiceError as exc:
        raise ProjectContextHttpError(
            status.HTTP_404_NOT_FOUND,
            PROJECT_NOT_FOUND_OR_FORBIDDEN,
            "Project not found or not authorized",
        ) from exc

    # Fail-closed nếu response không đúng shape mong đợi — KHÔNG coi 1 object
    # Mock/None/truthy-nhưng-vô-nghĩa là bằng chứng authorization hợp lệ.
    if not isinstance(resp, dict):
        raise ProjectContextHttpError(
            status.HTTP_404_NOT_FOUND,
            PROJECT_NOT_FOUND_OR_FORBIDDEN,
            "Project not found or not authorized",
        )
    resolved_id = resp.get("id")
    if not resolved_id or str(resolved_id) != str(project_id):
        raise ProjectContextHttpError(
            status.HTTP_404_NOT_FOUND,
            PROJECT_NOT_FOUND_OR_FORBIDDEN,
            "Project not found or not authorized",
        )

    return VerifiedProjectContext(
        project_id=str(resolved_id),
        workspace_id=identity.workspace_id,
        title=resp.get("title"),
        workspace_name=await _read_workspace_name(company_client, identity),
    )


async def _read_workspace_name(company_client: Any, identity: Any) -> str | None:
    """Best-effort: lỗi/thiếu tên -> None, không bao giờ làm hỏng request chat.

    Chỉ cache tên (hiển thị) — quyền truy cập Project luôn verify lại mỗi request."""
    workspace_id = str(identity.workspace_id)
    cached = _WORKSPACE_NAME_CACHE.get(workspace_id)
    if cached is not None and cached[0] > time.monotonic():
        return cached[1]
    try:
        resp = await company_client.get(
            f"/identity/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {identity.mint_delegation()}"},
        )
    except Exception:
        return None
    name = resp.get("name") if isinstance(resp, dict) else None
    if not (isinstance(name, str) and name.strip()):
        return None
    name = name.strip()
    if len(_WORKSPACE_NAME_CACHE) >= _WORKSPACE_NAME_CACHE_MAX:
        _WORKSPACE_NAME_CACHE.clear()
    _WORKSPACE_NAME_CACHE[workspace_id] = (time.monotonic() + _WORKSPACE_NAME_TTL_S, name)
    return name


def require_project_context_match(
    *, request_project_id: str | None, persisted_project_id: str | None
) -> None:
    """So khớp Project client khai báo với Project ĐÃ LƯU trên
    conversation/run — mismatch là 422 PROJECT_CONTEXT_MISMATCH (khác 404
    not-found: client đang cố dùng đúng resource nhưng khai sai Project, cần
    tín hiệu phân biệt được với "Project không tồn tại")."""
    if request_project_id != persisted_project_id:
        raise ProjectContextHttpError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            PROJECT_CONTEXT_MISMATCH,
            "project_id does not match the conversation's project",
        )
