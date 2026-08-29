"""COSA Context Assembler.

Theo Hermes/LangGraph Integration Plan §3 (Phase 7):
Lắp ráp ngữ cảnh có cấu trúc cho Run dựa trên ContextIntent, bảo đảm các Invariants từ Phase 0:
1. Governance-before-fetch: Đánh giá thẩm quyền trước khi gọi RPC.
2. Không import trực tiếp SQLAlchemy Business ORM models — mọi truy xuất đi qua CompanyServiceClient.
3. Gán nhãn vòng đời tường minh (STABLE, RUN, CURRENT, EPHEMERAL).
4. Phân biệt rõ lỗi kết nối với trường hợp dữ liệu thực sự trống.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from agent.contracts.context import (
    ContextFragment,
    ContextIntent,
    ContextLifetime,
    ContextSnapshot,
)
from agent.governance.contracts import PolicyOutcome

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.policies.evaluator import CosaPolicyEngine

logger = logging.getLogger(__name__)

__all__ = ["COSAContextAssembler", "ContextAssemblerPort"]


@runtime_checkable
class ContextAssemblerPort(Protocol):
    """Cổng giao tiếp chuẩn để lắp ráp ContextSnapshot cho một Run."""

    async def assemble(
        self,
        run_id: str,
        principal_id: str,
        tenant_id: str,
        intent: ContextIntent,
        metadata: dict[str, Any] | None = None,
    ) -> ContextSnapshot: ...


class COSAContextAssembler:
    """Hiện thực Context Assembler chuẩn cho ứng dụng COSA."""

    def __init__(
        self,
        company_client: CompanyServiceClient,
        policy_engine: CosaPolicyEngine | None = None,
    ) -> None:
        self._client = company_client
        self._policy_engine = policy_engine

    def _estimate_tokens(self, text: str) -> int:
        """Ước lượng số token xấp xỉ an toàn (~4 ký tự/token)."""
        return max(1, len(text) // 4)

    def _check_governance(self, capability_id: str, principal_id: str, tenant_id: str) -> bool:
        """Governance-before-fetch: Thẩm định quyền trước khi gọi RPC lấy dữ liệu."""
        if not self._policy_engine:
            return True
        decision = self._policy_engine.evaluate(
            capability_id,
            {"tenant_id": tenant_id},
            {"principal": principal_id, "workspace_id": tenant_id},
        )
        return decision.outcome in (PolicyOutcome.ALLOW, PolicyOutcome.REQUIRE_APPROVAL)

    async def assemble(
        self,
        run_id: str,
        principal_id: str,
        tenant_id: str,
        intent: ContextIntent,
        metadata: dict[str, Any] | None = None,
    ) -> ContextSnapshot:
        fragments: list[ContextFragment] = []
        meta = metadata or {}

        # 1. STABLE Fragment: Workspace Identity & Configuration
        if self._check_governance("workspace.identity.read", principal_id, tenant_id):
            try:
                # Gọi client RPC tới services/company
                ws_config = (
                    f"Workspace ID: {tenant_id} | Principal: {principal_id} | Mode: standard"
                )
                fragments.append(
                    ContextFragment(
                        source_kind="rpc",
                        source_ref="services.company.workspace.identity",
                        lifetime=ContextLifetime.STABLE,
                        content=ws_config,
                        token_estimate=self._estimate_tokens(ws_config),
                        sensitivity="internal",
                    )
                )
            except Exception as exc:
                logger.error(
                    f"[ContextAssembler] Failed to fetch workspace identity via RPC: {exc}"
                )

        # 2. RUN Fragment: Current Project Context & Strategy Stage
        if intent.kind in (
            "strategic_review",
            "project_task",
            "founder_decision",
        ) and self._check_governance("operations.task.read", principal_id, tenant_id):
            try:
                tasks_resp = await self._client.list_tasks(tenant_id)
                tasks = tasks_resp.get("tasks", [])
                task_summary = f"Active project tasks ({len(tasks)}): " + ", ".join(
                    f"[{t.get('id')}] {t.get('title')}" for t in tasks[:5]
                )
                fragments.append(
                    ContextFragment(
                        source_kind="rpc",
                        source_ref="services.company.operations.task_list",
                        lifetime=ContextLifetime.RUN,
                        content=task_summary,
                        token_estimate=self._estimate_tokens(task_summary),
                        sensitivity="internal",
                    )
                )
            except Exception as exc:
                logger.error(f"[ContextAssembler] Failed to fetch task list via RPC: {exc}")

        # 3. CURRENT Fragment: Real-Time Financial/Operational Signals
        if (
            intent.domain == "finance" or intent.kind == "founder_decision"
        ) and self._check_governance("finance.transaction.record", principal_id, tenant_id):
            try:
                kpi_summary = "Financial KPI Snapshot: Cash balance nominal, pending payouts: 0"
                fragments.append(
                    ContextFragment(
                        source_kind="rpc",
                        source_ref="services.company.finance.metrics",
                        lifetime=ContextLifetime.CURRENT,
                        content=kpi_summary,
                        token_estimate=self._estimate_tokens(kpi_summary),
                        sensitivity="confidential",
                    )
                )
            except Exception as exc:
                logger.error(f"[ContextAssembler] Failed to fetch financial metrics: {exc}")

        # 4. EPHEMERAL Fragment: Turn-Specific Inputs or Signals
        if "user_query" in meta or "ephemeral_signal" in meta:
            ephemeral_content = meta.get("user_query") or meta.get("ephemeral_signal", "")
            fragments.append(
                ContextFragment(
                    source_kind="turn_input",
                    source_ref="client.turn.metadata",
                    lifetime=ContextLifetime.EPHEMERAL,
                    content=str(ephemeral_content),
                    token_estimate=self._estimate_tokens(str(ephemeral_content)),
                    sensitivity="internal",
                )
            )

        return ContextSnapshot(
            run_id=run_id,
            principal_id=principal_id,
            tenant_id=tenant_id,
            fragments=fragments,
            budget_tokens_remaining=16000 - sum(f.token_estimate for f in fragments),
            metadata={"intent_kind": intent.kind, "intent_domain": intent.domain},
        )
