from __future__ import annotations

import os
from typing import Any

import httpx

__all__ = ["CompanyServiceClient", "CompanyServiceError"]


class CompanyServiceError(Exception):
    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class CompanyServiceClient:
    """Async HTTP Client kết nối tới Encore Business Services (services/company).

    Phục vụ các Capability của COSA:
    - Operations (/operations/...)
    - Commercial (/commercial/...)
    - Finance & Legal (/finance-legal/...)
    - Identity (/identity/...)
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 15.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("COMPANY_SERVICE_URL") or "http://localhost:4000"
        ).rstrip("/")
        self.timeout = timeout
        self.default_headers = headers or {}

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=json, params=params, headers=headers)

    async def patch(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PATCH", path, json=json, params=params, headers=headers)

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("PUT", path, json=json, params=params, headers=headers)

    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self._request("DELETE", path, params=params, headers=headers)

    async def list_tasks(self, workspace_id: str) -> dict[str, Any]:
        return await self.get("/operations/tasks", params={"workspaceId": workspace_id})

    async def resolve_data_use(
        self,
        workspace_id: str,
        deployment_id: str,
        capability_id: str,
        purpose_id: str,
        data_categories: list[str] | set[str] | frozenset[str],
        provider_key: str,
        model_key: str = "",
        subject_reference: str | None = None,
        delegation_token: str | None = None,
    ) -> Any:
        """Gọi `POST /finance-legal/ai-compliance/resolve-data-use` (Task 7).

        Đây là method mà `CosaDataModelGate.prepare_initial_input`
        (`apps/cosa/compliance/data_model_gate.py`) kiểm tra qua
        `hasattr(self._client, "resolve_data_use")` trước khi enforce
        relational check thật. Trước Task 7, `CompanyServiceClient` KHÔNG có
        method này ⇒ `hasattr` luôn `False` với client thật trong production
        ⇒ toàn bộ nhánh enforcement rơi thẳng về `redactor.sanitize()` không
        kiểm tra category/provider/authorization nào (dead code — xác nhận
        bằng audit 2026-08-30). Thêm method thật ở đây khiến `hasattr` trả về
        `True` với MỌI instance `CompanyServiceClient` thật, không chỉ với
        mock trong test.

        Lệnh gọi này xảy ra TRƯỚC khi kernel gọi model — tại thời điểm đó
        CHƯA có tool call nào đang chạy nên header ambient
        (`agent.capabilities.outbound_headers`, do kernel set quanh đúng 1
        lệnh gọi capability — xem `RealOpenAIAgentsSDKKernel._invoke_capability`)
        chưa được set. Vì vậy method này tự build header
        Authorization/X-Workspace-Id tường minh từ tham số `delegation_token`
        thay vì trông chờ ambient context, rồi truyền qua tham số `headers=`
        của `self.post()` — tham số đó vẫn thắng ambient theo đúng convention
        đã có ở `_request()` (`req_headers.update(get_outbound_headers());
        if headers: req_headers.update(headers)`).
        """
        headers: dict[str, str] = {"X-Workspace-Id": str(workspace_id)}
        if delegation_token:
            headers["Authorization"] = f"Bearer {delegation_token}"

        payload: dict[str, Any] = {
            "deploymentId": str(deployment_id),
            "capabilityId": capability_id,
            "purposeId": purpose_id,
            "dataCategories": list(data_categories),
            "providerKey": provider_key,
            "modelKey": model_key,
        }
        if subject_reference is not None:
            payload["subjectReference"] = subject_reference

        data = await self.post(
            "/finance-legal/ai-compliance/resolve-data-use",
            json=payload,
            headers=headers,
        )

        from types import SimpleNamespace

        return SimpleNamespace(
            allowed=data.get("allowed", False),
            denial_code=data.get("denialCode"),
            provider_profile_version=data.get("providerProfileVersion"),
            data_profile_version=data.get("dataProfileVersion"),
            retention_policy_id=data.get("retentionPolicyId"),
            minimization_required=data.get("minimizationRequired", False),
        )

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        from agent.capabilities.outbound_headers import get_outbound_headers

        from apps.cosa.observability.otel import inject_trace_carrier

        url = f"{self.base_url}/{path.lstrip('/')}"
        req_headers = dict(self.default_headers)
        # Task 5 — header xác thực (Authorization, X-Workspace-Id,
        # X-COSA-Run-Id, X-COSA-Capability-Id) do kernel set ambient TỪ
        # InvocationContext của tool call đang chạy (KHÔNG phải từ đối số của
        # handler/tool). Merge SAU default_headers nhưng TRƯỚC `headers`
        # tường minh (nếu caller truyền `headers=` rõ ràng cho nhu cầu khác,
        # nó vẫn thắng — không có call site nào hiện tại truyền Authorization
        # tường minh qua tham số này).
        req_headers.update(get_outbound_headers())
        if headers:
            req_headers.update(headers)
        req_headers = inject_trace_carrier(req_headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    method, url, params=params, json=json, headers=req_headers
                )
                if response.status_code >= 400:
                    try:
                        err_payload = response.json()
                        message = err_payload.get("message", response.text)
                    except Exception:
                        message = response.text
                    raise CompanyServiceError(
                        f"Company Service Error ({response.status_code}): {message}",
                        status_code=response.status_code,
                        details=response.text,
                    )
                return response.json()
            except httpx.RequestError as exc:
                raise CompanyServiceError(
                    f"Network error communicating with Company Service at {url}: {exc}"
                ) from exc
