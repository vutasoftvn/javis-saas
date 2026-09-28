"""Task 5 (plan 2026-09-28-stage-adaptive-ai-operating-system) — AI initiative
usage attribution and Project budget enforcement in run_core."""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
from apps.cosa.models.usage import (
    InMemoryUsageLedger,
    UsageBudgetExceeded,
    UsageEntry,
)
from apps.cosa.worker import run_core

pytestmark = pytest.mark.asyncio


def _route(**over: Any) -> ResolvedModelRoute:
    base: dict[str, Any] = dict(
        workspace_id="ws1",
        agent_spec_id="cosa.agents.operations",
        profile_id="p-deepseek",
        provider_type=ProviderType.DEEPSEEK_API,
        model_id="deepseek-chat",
        credential_ref="cred",
    )
    base.update(over)
    return ResolvedModelRoute(**base)


def _async(value: Any):
    async def _f(*a: Any, **k: Any):
        return value

    return _f


async def test_run_core_records_initiative_attribution(monkeypatch):
    route = _route()
    ledger = InMemoryUsageLedger()

    class _Kernel:
        async def run(self, req, spec):
            return SimpleNamespace(
                status="completed", usage={"prompt_tokens": 150, "completion_tokens": 50}
            )

    monkeypatch.setattr(
        "apps.cosa.composition.kernel_factory.build_execution_kernel",
        lambda **kw: (_Kernel(), None),
    )
    resolver = SimpleNamespace(resolve_route=_async(route))
    repo = SimpleNamespace(get_profile=_async(SimpleNamespace(budget_usd_limit=None)))
    plane = SimpleNamespace(
        kernel=None,
        model_route_resolver=resolver,
        model_provider_factory=SimpleNamespace(create=_async(object())),
        model_routing_repository=repo,
        usage_ledger=ledger,
        repository=None,
        spec_registry=None,
        capability_registry=None,
        gateway=None,
        policy_engine=None,
        company_client=None,
        compliance_resolver=None,
    )
    prep = SimpleNamespace(
        spec=SimpleNamespace(id="cosa.agents.operations", spec_id="cosa.agents.operations"),
        req=SimpleNamespace(
            workspace_id="ws1",
            model_policy={},
            metadata={"project_id": "proj1", "initiative_id": "init-alpha"},
        ),
    )

    await run_core.run_kernel(plane, prep, workspace_id="ws1", run_id="r1")
    [entry] = ledger.entries
    assert entry.initiative_id == "init-alpha"
    assert entry.project_id == "proj1"
    assert entry.prompt_tokens == 150
    assert entry.completion_tokens == 50


async def test_run_core_without_initiative_records_unattributed(monkeypatch):
    route = _route()
    ledger = InMemoryUsageLedger()

    class _Kernel:
        async def run(self, req, spec):
            return SimpleNamespace(
                status="completed", usage={"prompt_tokens": 100, "completion_tokens": 50}
            )

    monkeypatch.setattr(
        "apps.cosa.composition.kernel_factory.build_execution_kernel",
        lambda **kw: (_Kernel(), None),
    )
    resolver = SimpleNamespace(resolve_route=_async(route))
    repo = SimpleNamespace(get_profile=_async(SimpleNamespace(budget_usd_limit=None)))
    plane = SimpleNamespace(
        kernel=None,
        model_route_resolver=resolver,
        model_provider_factory=SimpleNamespace(create=_async(object())),
        model_routing_repository=repo,
        usage_ledger=ledger,
        repository=None,
        spec_registry=None,
        capability_registry=None,
        gateway=None,
        policy_engine=None,
        company_client=None,
        compliance_resolver=None,
    )
    prep = SimpleNamespace(
        spec=SimpleNamespace(id="cosa.agents.operations", spec_id="cosa.agents.operations"),
        req=SimpleNamespace(
            workspace_id="ws1",
            model_policy={},
            metadata={"project_id": "proj1"},
        ),
    )

    await run_core.run_kernel(plane, prep, workspace_id="ws1", run_id="r2")
    [entry] = ledger.entries
    assert entry.initiative_id is None
    assert entry.project_id == "proj1"


async def test_hard_budget_breach_prevents_model_client_creation_and_emits_pause_code(monkeypatch):
    route = _route()
    ledger = InMemoryUsageLedger()
    # Pre-record high spend on the initiative
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-heavy",
            run_id="r0",
            profile_id="p-deepseek",
            prompt_tokens=10000,
            completion_tokens=5000,
            cost_usd=Decimal("50.00"),
        )
    )

    created_clients: list[str] = []

    class _Factory:
        async def create(self, r):
            created_clients.append(r.profile_id)
            return object()

    resolver = SimpleNamespace(resolve_route=_async(route))
    repo = SimpleNamespace(get_profile=_async(SimpleNamespace(budget_usd_limit=None)))
    plane = SimpleNamespace(
        kernel=None,
        model_route_resolver=resolver,
        model_provider_factory=_Factory(),
        model_routing_repository=repo,
        usage_ledger=ledger,
    )

    # Over budget: hard_cost_threshold is 25.00, spend is 50.00
    prep = SimpleNamespace(
        spec=SimpleNamespace(id="cosa.agents.operations", spec_id="cosa.agents.operations"),
        req=SimpleNamespace(
            workspace_id="ws1",
            model_policy={},
            metadata={
                "project_id": "proj1",
                "initiative_id": "init-heavy",
                "initiative_budget_policy": {
                    "soft_cost_threshold": "10.00",
                    "hard_cost_threshold": "25.00",
                    "period": "TOTAL",
                },
            },
        ),
    )

    with pytest.raises(run_core.RunCoreError) as exc:
        await run_core.run_kernel(plane, prep, workspace_id="ws1", run_id="r3")

    assert exc.value.reason_code == "usage_budget_exceeded"
    assert exc.value.compliance_code == "initiative_budget_paused"
    assert created_clients == []  # Model client was never created!


async def test_initiative_without_project_scope_rejected():
    route = _route()
    plane = SimpleNamespace(
        model_routing_repository=SimpleNamespace(get_profile=_async(None)),
        usage_ledger=InMemoryUsageLedger(),
    )
    prep = SimpleNamespace(
        req=SimpleNamespace(
            metadata={
                "initiative_id": "init-missing-proj",
                # project_id is intentionally omitted
            }
        )
    )

    with pytest.raises(run_core.RunCoreError) as exc:
        await run_core._enforce_usage_budget(plane, route, prep=prep)

    assert exc.value.reason_code == "missing_project_scope"
    assert exc.value.compliance_code == "initiative_scope_mismatch"
