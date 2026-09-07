"""Task 9 (plan local-first-enterprise-knowledge) — resolver cho từng persisted
operation. Mỗi resolver tự khai `allowed_variables` (whitelist tên biến —
biến lạ bị `execute_persisted_operation()` reject 422 trước khi vào đây) và
LUÔN nhận `identity` (workspace_id/principal_id/role_id đã xác thực) — không
bao giờ tin 1 `workspace_id`/`principal_id` do client tự khai trong
`variables`.

`identity` chỉ cần duck-type `IdentityLike` (không phải cụ thể
`AuthenticatedIdentity` của HTTP boundary) — Task 10 gọi các operation này từ
capability `workspace.context.read` (kernel/gateway context, không có JWT/
bearer_token nào để dựng `AuthenticatedIdentity` đầy đủ, chỉ có
workspace_id/principal/role_id đã resolve từ run payload)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "PERSISTED_OPERATIONS",
    "EnterpriseKnowledgeSearchOperation",
    "IdentityLike",
    "WorkspaceContextOperation",
]

_MAX_LIMIT = 20


@runtime_checkable
class IdentityLike(Protocol):
    @property
    def principal_id(self) -> str: ...

    @property
    def workspace_id(self) -> str: ...

    @property
    def role_id(self) -> str: ...


class PersistedOperation(Protocol):
    allowed_variables: frozenset[str]

    async def execute(
        self, variables: dict[str, Any], identity: IdentityLike, plane: Any
    ) -> dict[str, Any]: ...


def _role_ids(identity: IdentityLike) -> set[str]:
    return {identity.role_id} if identity.role_id else set()


def _citation_out(c: Any) -> dict[str, Any]:
    return {
        "document_id": c.document_id,
        "vault_version_id": c.vault_version_id,
        "chunk_id": c.chunk_id,
        "section": c.page_or_section,
        "snippet": c.snippet,
        "score": c.similarity_score,
    }


class EnterpriseKnowledgeSearchOperation:
    """`retrieve_authorized_citations()` MỚI (Task 8) — lọc theo authorization
    của đúng `identity` gọi, không suy diễn từ nội dung câu hỏi."""

    allowed_variables = frozenset({"query", "limit"})

    async def execute(
        self, variables: dict[str, Any], identity: IdentityLike, plane: Any
    ) -> dict[str, Any]:
        service = getattr(plane, "knowledge_ingestion_service", None)
        if service is None:
            return {"citations": []}

        query = str(variables.get("query") or "").strip()
        limit = min(int(variables.get("limit") or 10), _MAX_LIMIT)

        citations = await service.retrieve_authorized_citations(
            workspace_id=identity.workspace_id,
            principal_id=identity.principal_id,
            role_ids=_role_ids(identity),
            query=query,
            limit=limit,
        )
        return {"citations": [_citation_out(c) for c in citations]}


async def _business_task_summary(identity: IdentityLike, plane: Any) -> list[dict[str, Any]]:
    """`operations.task.list` — capability read-only đã có sẵn, workspace-scoped
    (không cần `project_id` như phần lớn capability strategy/analytics khác,
    xem đánh giá lúc đóng gap này trong plan Task 9 Step 3 annotation). Gọi
    THẲNG handler (không qua `CapabilityGateway` riêng — cùng cách
    `EnterpriseKnowledgeSearchOperation` đã làm cho citations: 1 lần gọi
    `workspace.context.read` = 1 entry audit, các nguồn đọc bên trong là chi
    tiết triển khai, không phải capability call riêng biệt cần audit thêm)."""
    client = getattr(plane, "company_client", None)
    if client is None:
        return []
    from apps.cosa.capabilities.operations_read import create_operations_task_list_handler

    handler = create_operations_task_list_handler(client)
    try:
        result = await handler({}, {"workspace_id": identity.workspace_id})
    except Exception:
        # Business adapter là phần MỞ RỘNG của workspaceContext — lỗi ở đây
        # (company service down, workspace chưa có operations module...)
        # không được làm hỏng toàn bộ câu trả lời (citations vẫn còn giá trị).
        return []
    tasks = result.get("tasks") if isinstance(result, dict) else None
    return tasks[:5] if isinstance(tasks, list) else []


class WorkspaceContextOperation:
    """Task 9 — ghép citation tri thức đã authorized + tóm tắt business
    read-only cho câu hỏi founder đang hỏi.

    `business` hiện CHỈ gồm `tasks` (từ `operations.task.list`, workspace-
    scoped). Các capability strategy/analytics khác (`strategy.next_best_
    action.get`, `strategy.project.get`, `analytics.pmf_scoreboard.get`...)
    ĐỀU yêu cầu `project_id` cụ thể — `workspaceContext` chỉ nhận `question`+
    workspace, không có project nào được chọn sẵn, và tự đoán "project đầu
    tiên/chính" sẽ suy diễn sai khi workspace có nhiều project. Cố tình KHÔNG
    wire các capability đó cho tới khi có quyết định rõ cách chọn project
    (hoặc `variables` được mở rộng nhận `project_id` tường minh từ caller)."""

    allowed_variables = frozenset({"question"})

    async def execute(
        self, variables: dict[str, Any], identity: IdentityLike, plane: Any
    ) -> dict[str, Any]:
        knowledge_op = EnterpriseKnowledgeSearchOperation()
        knowledge_result = await knowledge_op.execute(
            {"query": variables.get("question")}, identity, plane
        )
        tasks = await _business_task_summary(identity, plane)
        return {
            "workspace_id": identity.workspace_id,
            "business": {"tasks": tasks},
            "citations": knowledge_result["citations"],
        }


PERSISTED_OPERATIONS: dict[str, PersistedOperation] = {
    "workspaceContext": WorkspaceContextOperation(),
    "enterpriseKnowledgeSearch": EnterpriseKnowledgeSearchOperation(),
}
