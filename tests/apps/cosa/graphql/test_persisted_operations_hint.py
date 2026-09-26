import pytest
from fastapi import HTTPException

from apps.cosa.graphql.persisted_operations import execute_persisted_operation


@pytest.mark.asyncio
async def test_unknown_variable_lists_allowed_ones() -> None:
    with pytest.raises(HTTPException) as ei:
        await execute_persisted_operation("workspaceContext", {"query": "x"}, object(), object())
    assert ei.value.status_code == 422
    assert "['query']" in ei.value.detail
    assert "question" in ei.value.detail  # biến hợp lệ được nêu
