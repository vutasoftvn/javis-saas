from __future__ import annotations

import os
import time
from typing import Optional

from agentos.core.policy import TenantPolicyDecision
from agentos.tools.encore_client import EncoreClient, EncoreClientError

DEFAULT_CACHE_TTL_SECONDS = 30.0

# `services/` được tách thành 2 Encore app độc lập (2026-08-23): `company`
# (identity/operations/commercial/finance-legal, local) và `cosa` (tenancy/
# license/agent-policy, VPS). `/platform/internal/agent-policy` sống ở `cosa`,
# KHÔNG phải ở `company` — không được dùng chung `ENCORE_SERVICE_URL` (trỏ về
# `company`, mặc định cổng 4000) như 4 cluster nghiệp vụ khác trong
# agentos/tools/clusters/*, nếu không mọi request đều 404 và tenant policy
# override luôn bị fail-open về None một cách âm thầm.
_DEFAULT_PLATFORM_URL = "http://localhost:4001"


class TenantPolicyClient:
    """Đọc TenantPolicy read-only từ `services/control-plane` (roadmap Phase
    10a.3): "TenantPolicy đọc từ services/control-plane qua API, không có bản
    sao policy lưu cứng trong agentos/". Business policy là business truth,
    thuộc `services/control-plane`, không thuộc Agent Plane.

    Cache TTL ngắn (in-memory, per-process) để tránh gọi HTTP cho mọi tool
    call — chấp nhận staleness tối đa `cache_ttl_seconds` giữa lúc operator
    đổi policy và lúc agent áp dụng đúng policy mới; không phải nguồn sự thật
    lâu dài (không persist qua restart).
    """

    def __init__(
        self,
        encore_client: Optional[EncoreClient] = None,
        *,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._client = encore_client or EncoreClient(
            base_url=os.getenv("PLATFORM_API_BASE_URL", _DEFAULT_PLATFORM_URL)
        )
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[tuple[str, str], tuple[float, Optional[TenantPolicyDecision]]] = {}

    async def get_decision(self, *, company_id: str, tool_name: str) -> Optional[TenantPolicyDecision]:
        """Trả `None` nếu company chưa cấu hình policy nào cho tool này, hoặc
        nếu control-plane không thể truy vấn được (fail-open về None — tương
        đương "không có tenant policy dimension", không phải fail-open thành
        ALLOW/DENY; các chiều governance khác của `evaluate_access()` vẫn áp
        dụng bình thường)."""
        cache_key = (company_id, tool_name)
        cached = self._cache.get(cache_key)
        if cached is not None:
            cached_at, decision = cached
            if time.monotonic() - cached_at < self._cache_ttl_seconds:
                return decision

        try:
            res = await self._client.get(
                "/platform/internal/agent-policy",
                params={"companyId": company_id, "toolName": tool_name},
            )
        except EncoreClientError:
            return None

        raw_decision = res.get("decision")
        decision = TenantPolicyDecision(raw_decision) if raw_decision else None
        self._cache[cache_key] = (time.monotonic(), decision)
        return decision

    def clear_cache(self) -> None:
        self._cache.clear()
