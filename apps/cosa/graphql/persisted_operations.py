"""Task 9 (plan local-first-enterprise-knowledge) — dispatch persisted
operation. Guardrail (plan Step 4): unknown operation id -> 404, biến lạ
(ngoài whitelist của chính operation đó) hoặc string quá dài -> 422 — tất cả
xảy ra TRƯỚC khi gọi resolver, resolver không bao giờ thấy input chưa được
validate."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from apps.cosa.graphql.resolvers import PERSISTED_OPERATIONS, IdentityLike

__all__ = ["execute_persisted_operation"]

_MAX_STRING_VARIABLE_LENGTH = 500


async def execute_persisted_operation(
    operation_id: str,
    variables: dict[str, Any],
    identity: IdentityLike,
    plane: Any,
) -> dict[str, Any]:
    operation = PERSISTED_OPERATIONS.get(operation_id)
    if operation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="operation not found")

    unknown = set(variables) - operation.allowed_variables
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown variables: {sorted(unknown)}",
        )

    for key, value in variables.items():
        if isinstance(value, str) and len(value) > _MAX_STRING_VARIABLE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"variable '{key}' exceeds max length",
            )

    return await operation.execute(variables, identity, plane)
