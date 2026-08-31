from __future__ import annotations

import os
from typing import Any

from agent.capabilities.gateway import CapabilityGateway
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.kernel import ExecutionKernel
from agent.contracts.run import RunRequest
from agent.contracts.spec import AgentSpec
from agent.kernel.openai_agents_kernel import ManualToolLoopKernel
from agent.registry.repository import SpecRegistryRepository
from agent.runs.repository import RunRepository
from agent_integrations.openai_agents_sdk.kernel import RealOpenAIAgentsSDKKernel

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.policies.evaluator import CosaPolicyEngine


class _MockAiComplianceClient:
    """Mock compliance client for test / dev."""

    async def resolve_snapshot(
        self,
        workspace_id: str,
        run_id: str,
        system_key: str,
        capability_ids: list[str],
        delegation_token: str,
        policy_snapshot_hash: str = "",
    ):
        from datetime import UTC, datetime, timedelta

        from apps.cosa.compliance.contracts import ComplianceSnapshot

        return ComplianceSnapshot(
            workspace_id=workspace_id,
            deployment_id=f"dep_{workspace_id}",
            assessment_id=f"assess_{workspace_id}",
            mode="ADVISORY_ONLY",
            status="APPROVED_FOR_USE",
            allowed_capabilities=frozenset(capability_ids),
            provider_profile_version="mock-1.0.0",
            data_profile_version="mock-1.0.0",
            provider_key="mock-provider",
            model_key="mock-model",
            purpose_id="mock-purpose",
            retention_policy_id="mock-retention",
            snapshot_hash="sha256:" + "0" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )


class _MockComplianceResolverWithDefaultClaim:
    """CHỈ dùng trong nhánh test/dev-mock (`use_mock_compliance_client`)."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner

    async def resolve_for_run(
        self, request: RunRequest, spec: AgentSpec
    ) -> dict[str, Any]:
        result = dict(await self._inner.resolve_for_run(request, spec))
        if "data_access_claim" not in result and "claim" not in result:
            from apps.cosa.compliance.data_access_claim import DataAccessClaim

            snap = result.get("compliance_snapshot") or {}
            result["data_access_claim"] = DataAccessClaim(
                workspace_id=str(
                    request.workspace_id or snap.get("workspace_id") or ""
                ),
                deployment_id=str(
                    snap.get("deployment_id") or f"dep_{request.workspace_id}"
                ),
                capability_id="model.input",
                source_ref="mock://compliance/default-claim",
                source_hash="sha256:" + "0" * 64,
                categories=frozenset(["BUSINESS_CONFIDENTIAL"]),
                purpose_id="advisory",
                provider_key="deepseek",
                model_key="deepseek-chat",
            )
        return result


def build_execution_kernel(
    *,
    runtime: str,
    repository: RunRepository,
    spec_registry: SpecRegistryRepository,
    capability_registry: CapabilityRegistry,
    gateway: CapabilityGateway,
    policy_engine: CosaPolicyEngine,
    company_client: CompanyServiceClient,
    model: Any | None = None,
) -> tuple[ExecutionKernel, Any | None]:
    """Khởi tạo ExecutionKernel và ComplianceResolver theo runtime configuration.

    Trả về tuple (kernel, compliance_resolver).
    """
    compliance_resolver: Any | None = None

    if runtime == "langchain":
        from agent_integrations.langchain.kernel import LangChainKernel

        kernel: ExecutionKernel = LangChainKernel(
            repository=repository,
            spec_registry=spec_registry,
            capability_registry=capability_registry,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    elif runtime == "openai_agents":
        if model is not None:
            resolved_model: Any = model
        else:
            from apps.cosa.composition.model_provider import build_deepseek_model

            resolved_model = build_deepseek_model()

        from apps.cosa.compliance import AiComplianceClient, ComplianceResolver
        from apps.cosa.compliance.data_model_gate import CosaDataModelGate

        use_mock_compliance_client = model is not None or os.getenv(
            "COSA_COMPLIANCE_MOCK", ""
        ).strip().lower() in ("1", "true", "yes")

        if use_mock_compliance_client:
            compliance_resolver = _MockComplianceResolverWithDefaultClaim(
                ComplianceResolver(client=_MockAiComplianceClient())  # type: ignore[arg-type]
            )
        else:
            base_url = getattr(company_client, "base_url", None) or getattr(
                company_client, "_base_url", None
            )
            if base_url is None:
                base_url = os.getenv("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
            compliance_resolver = ComplianceResolver(AiComplianceClient(base_url=str(base_url)))

        model_input_guard = CosaDataModelGate(client=company_client)

        kernel = RealOpenAIAgentsSDKKernel(
            repository=repository,
            spec_registry=spec_registry,
            capability_registry=capability_registry,
            model=resolved_model,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
            compliance_resolver=compliance_resolver,
            model_input_guard=model_input_guard,
        )
    elif runtime == "manual_tool_loop":
        kernel = ManualToolLoopKernel(
            repository=repository,
            spec_registry=spec_registry,
            capability_executor=gateway.execute,
            policy_evaluator=policy_engine.evaluate,
        )
    else:
        raise ValueError(
            f"Unknown runtime '{runtime}' — expected 'openai_agents', 'manual_tool_loop', or 'langchain'"
        )

    return kernel, compliance_resolver
