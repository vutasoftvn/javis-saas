"""Task 9 (plan local-first-enterprise-knowledge) — request schema cho local
persisted-operations GraphQL BFF.

Đây KHÔNG phải GraphQL engine thật (không parse query document, không có
resolver graph động) — chỉ 1 registry hữu hạn các "operation" đã định nghĩa
cứng (persisted operations), client CHỈ được chọn `operationId` + truyền
`variables` phẳng (không object/array lồng — selection set do server sở hữu
tuyệt đối, không phải client). `extra="forbid"` + variables value type hẹp
(str/int/float/bool/None) tự động reject request mang `query`/`mutation`
string tuỳ ý (422 validation error, không tới được resolver nào)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["GraphQLRequest", "OperationId"]

OperationId = Literal["workspaceContext", "enterpriseKnowledgeSearch", "workspaceAuthorityOverview"]

# Giá trị variable chỉ nhận scalar phẳng — dict/list lồng bị pydantic reject
# thẳng ở validation (422), không cần tự viết depth-walker riêng.
_VariableValue = str | int | float | bool | None


class GraphQLRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    operation_id: OperationId = Field(alias="operationId")
    variables: dict[str, _VariableValue] = Field(default_factory=dict)
