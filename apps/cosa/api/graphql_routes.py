"""Task 9 (plan local-first-enterprise-knowledge) — local persisted-operations
GraphQL BFF. `POST /agent/graphql` CHỈ nhận `{operationId, variables}` (xem
apps.cosa.graphql.schema.GraphQLRequest) — không bao giờ nhận GraphQL query
document string. Không có mutation nào được đăng ký (chỉ đọc)."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Request

from apps.cosa.auth.dependency import AuthenticatedIdentity, get_authenticated_identity
from apps.cosa.graphql.persisted_operations import execute_persisted_operation
from apps.cosa.graphql.schema import GraphQLRequest

logger = logging.getLogger("cosa.api.graphql")

router = APIRouter(prefix="/agent/graphql", tags=["graphql"])


def _get_plane(request: Request) -> Any:
    plane = getattr(request.app.state, "plane", None)
    if plane is None:
        raise RuntimeError("CosaAgentPlane chưa sẵn sàng — app.state.plane rỗng.")
    return plane


@router.post("", response_model=None)
async def execute_operation(
    request: Request,
    req: GraphQLRequest,
    identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
) -> dict[str, Any]:
    plane = _get_plane(request)
    started_at = time.monotonic()
    result = await execute_persisted_operation(req.operation_id, req.variables, identity, plane)
    duration_ms = round((time.monotonic() - started_at) * 1000, 1)

    # Audit — id trích dẫn + thời lượng, KHÔNG BAO GIỜ nội dung snippet/business
    # payload (đó là dữ liệu doanh nghiệp, không phải thứ đưa vào log).
    citation_ids = [c.get("chunk_id") for c in result.get("citations", []) if isinstance(c, dict)]
    logger.info(
        "graphql.persisted_operation",
        extra={
            "operation_id": req.operation_id,
            "principal_id": identity.principal_id,
            "workspace_id": identity.workspace_id,
            "citation_ids": citation_ids,
            "duration_ms": duration_ms,
        },
    )

    return {"data": {req.operation_id: result}}
