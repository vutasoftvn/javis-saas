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


class WorkspaceContextOperation:
    """Task 9 — ghép citation tri thức đã authorized cho câu hỏi founder đang
    hỏi. `question` KHÔNG tự động mở rộng sang business adapter cụ thể nào —
    plan liệt kê "read-only, capability-backed business adapters" nhưng không
    khai rõ 1 contract cụ thể nào (không có capability read tổng hợp toàn
    workspace nào tồn tại sẵn để gọi mà không tự bịa schema); cố tình KHÔNG
    tự chế 1 business summary chưa được đặc tả — `business` để rỗng tường
    minh, không giả lập. Founder assistant (Task 10) vẫn dùng được citations
    đã có; mở rộng business context là việc tương lai, không phải hồi quy."""

    allowed_variables = frozenset({"question"})

    async def execute(
        self, variables: dict[str, Any], identity: IdentityLike, plane: Any
    ) -> dict[str, Any]:
        knowledge_op = EnterpriseKnowledgeSearchOperation()
        knowledge_result = await knowledge_op.execute(
            {"query": variables.get("question")}, identity, plane
        )
        return {
            "workspace_id": identity.workspace_id,
            "business": {},
            "citations": knowledge_result["citations"],
        }


PERSISTED_OPERATIONS: dict[str, PersistedOperation] = {
    "workspaceContext": WorkspaceContextOperation(),
    "enterpriseKnowledgeSearch": EnterpriseKnowledgeSearchOperation(),
}
