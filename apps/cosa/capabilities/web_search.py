from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from agent_core.artifacts.models import WorkspaceArtifact
from agent_core.artifacts.repository import ArtifactRepository
from agent_core.capabilities.web_search.budget import (
    InMemoryWebSearchBudgetStore,
    WebSearchBudgetStore,
)
from agent_core.capabilities.web_search.provider import (
    NullWebSearchProvider,
    WebSearchProvider,
    build_web_search_provider,
)
from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk

logger = logging.getLogger(__name__)

__all__ = [
    "WEB_SEARCH_SPEC",
    "create_web_search_handler",
]

WEB_SEARCH_SPEC = CapabilitySpec(
    id="web.search",
    description="Tìm kiếm thông tin trên internet qua provider web search (Tavily), phục vụ nghiên cứu thị trường, phân tích đối thủ và kiểm tra tin tức.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "Nội dung hoặc từ khóa tìm kiếm"},
            "max_results": {
                "type": "integer",
                "description": "Số lượng kết quả tối đa (mặc định: 5)",
                "default": 5,
            },
            "allow_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Danh sách domain cho phép tìm kiếm",
            },
            "deny_domains": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Danh sách domain cấm/bỏ qua",
            },
            "workspace_id": {"type": "string", "description": "Workspace ID (tùy chọn)"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "source_url": {"type": "string"},
                        "title": {"type": "string"},
                        "snippet": {"type": "string"},
                        "raw_excerpt": {"type": "string"},
                        "published_at": {"type": "string"},
                        "provider": {"type": "string"},
                        "retrieved_at": {"type": "string"},
                        "untrusted": {"type": "boolean"},
                    },
                },
            },
            "provider": {"type": "string"},
            "retrieved_at": {"type": "string"},
            "query": {"type": "string"},
        },
    },
)


def create_web_search_handler(
    provider: WebSearchProvider | None = None,
    *,
    workspace_policy_client: Any | None = None,
    budget_store: WebSearchBudgetStore | None = None,
    artifact_repository: ArtifactRepository | None = None,
):
    search_provider = provider or build_web_search_provider()
    store = budget_store or InMemoryWebSearchBudgetStore()

    async def handle_web_search(payload: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
        query = str(payload.get("query") or "").strip()
        if not query:
            return {
                "results": [],
                "provider": getattr(search_provider, "provider_name", "null"),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "query": "",
            }

        workspace_id = str(payload.get("workspace_id") or ctx.get("workspace_id") or "1")
        max_results = int(payload.get("max_results") or 5)

        allow_domains = list(payload.get("allow_domains") or [])
        deny_domains = list(payload.get("deny_domains") or [])

        # Merge with workspace tenant policy if client provides policy methods
        if workspace_policy_client is not None:
            policy_getter = getattr(workspace_policy_client, "get_web_search_policy", None)
            if callable(policy_getter):
                try:
                    policy = await policy_getter(workspace_id)
                    if isinstance(policy, dict):
                        if policy.get("allow_domains"):
                            allow_domains.extend(policy["allow_domains"])
                        if policy.get("deny_domains"):
                            deny_domains.extend(policy["deny_domains"])
                except Exception as e:
                    logger.warning(
                        f"Failed to fetch workspace search policy for {workspace_id}: {e}"
                    )

        # Check and consume quota
        await store.check_and_consume(workspace_id, cost=1.0, query_count=1)

        # Execute search with graceful fallback if provider fails or is offline
        actual_provider_name = getattr(
            search_provider,
            "provider_name",
            "tavily" if not isinstance(search_provider, NullWebSearchProvider) else "null",
        )
        try:
            results = await search_provider.search(
                query,
                max_results=max_results,
                allow_domains=allow_domains if allow_domains else None,
                deny_domains=deny_domains if deny_domains else None,
            )
        except Exception as search_err:
            logger.warning(
                f"[WebSearch] Primary search provider failed ({search_err}). Falling back to NullWebSearchProvider."
            )
            fallback = NullWebSearchProvider()
            actual_provider_name = "null"
            results = await fallback.search(query, max_results=max_results)

        # Emit optional WorkspaceArtifact for evidence (SEARCH.3)
        write_evidence = os.environ.get("WEB_SEARCH_WRITE_EVIDENCE", "").lower() in (
            "true",
            "1",
            "yes",
        )
        if write_evidence and artifact_repository is not None:
            try:
                conv_id = str(ctx.get("conversation_id") or "default")
                run_id = ctx.get("run_id")
                artifact = WorkspaceArtifact(
                    workspace_id=workspace_id,
                    conversation_id=conv_id,
                    run_id=str(run_id) if run_id else None,
                    artifact_kind="report",
                    display_name=f"Web Search Evidence: {query[:40]}",
                    media_type="application/json",
                    object_ref=f"artifact://evidence/web_search/{uuid.uuid4().hex[:12]}",
                    status="available",
                )
                await artifact_repository.create(artifact)
            except Exception as ae:
                logger.warning(f"Failed to save web search artifact: {ae}")

        now_iso = datetime.now(UTC).isoformat()
        return {
            "results": [r.model_dump(mode="json") for r in results],
            "provider": actual_provider_name,
            "retrieved_at": now_iso,
            "query": query,
        }

    return handle_web_search
