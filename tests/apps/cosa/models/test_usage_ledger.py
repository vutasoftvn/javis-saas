"""Sổ cái usage + chặn ngân sách (review 2026-09-27, G-3)."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from apps.cosa.models.contracts import ProviderType, ResolvedModelRoute
from apps.cosa.models.usage import (
    InMemoryUsageLedger,
    PostgresUsageLedger,
    UsageBudgetExceeded,
    UsageEntry,
    check_usage_budget,
    estimate_cost_usd,
)

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


def _entry(ws="ws1", profile="p-deepseek", tokens=(100, 50), cost="0.01", when=None):
    return UsageEntry(
        workspace_id=ws,
        run_id=f"run_{uuid.uuid4().hex[:8]}",
        profile_id=profile,
        prompt_tokens=tokens[0],
        completion_tokens=tokens[1],
        cost_usd=Decimal(cost) if cost is not None else None,
        created_at=when or datetime.now(UTC),
    )


async def test_estimate_cost_known_and_unknown_model():
    cost = estimate_cost_usd(ProviderType.DEEPSEEK_API, "deepseek-chat", 1000, 1000)
    assert cost is not None and cost > 0
    assert estimate_cost_usd(ProviderType.LOCAL_OPENAI_COMPATIBLE, "my-local-7b", 10, 10) is None


async def test_no_limits_configured_passes(monkeypatch):
    monkeypatch.delenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", raising=False)
    await check_usage_budget(InMemoryUsageLedger(), _route(), profile_budget_usd=None)
    await check_usage_budget(None, _route(), profile_budget_usd=None)


async def test_workspace_token_quota_counts_only_this_month_and_workspace(monkeypatch):
    monkeypatch.setenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", "300")
    ledger = InMemoryUsageLedger()
    last_month = datetime.now(UTC).replace(day=1) - timedelta(days=2)
    await ledger.record(_entry(tokens=(1000, 1000), when=last_month))
    await ledger.record(_entry(ws="ws2", tokens=(1000, 1000)))
    await ledger.record(_entry(tokens=(100, 100)))
    await check_usage_budget(ledger, _route(), profile_budget_usd=None)  # 200 < 300

    await ledger.record(_entry(tokens=(50, 50)))
    with pytest.raises(UsageBudgetExceeded) as exc:
        await check_usage_budget(ledger, _route(), profile_budget_usd=None)
    assert exc.value.code == "workspace_token_quota_exceeded"


async def test_invalid_quota_config_fails_closed(monkeypatch):
    monkeypatch.setenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", "lots")
    with pytest.raises(UsageBudgetExceeded):
        await check_usage_budget(InMemoryUsageLedger(), _route(), profile_budget_usd=None)


async def test_profile_budget_only_counts_that_profile(monkeypatch):
    monkeypatch.delenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", raising=False)
    ledger = InMemoryUsageLedger()
    await ledger.record(_entry(profile="other", cost="5"))
    await ledger.record(_entry(cost="0.40"))
    await check_usage_budget(ledger, _route(), profile_budget_usd=0.5)
    await ledger.record(_entry(cost="0.10"))
    with pytest.raises(UsageBudgetExceeded) as exc:
        await check_usage_budget(ledger, _route(), profile_budget_usd=0.5)
    assert exc.value.code == "profile_budget_exceeded"


async def test_budget_on_unpriced_model_fails_closed(monkeypatch):
    monkeypatch.delenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", raising=False)
    route = _route(provider_type=ProviderType.LOCAL_OPENAI_COMPATIBLE, model_id="my-local-7b")
    with pytest.raises(UsageBudgetExceeded) as exc:
        await check_usage_budget(InMemoryUsageLedger(), route, profile_budget_usd=10)
    assert exc.value.code == "profile_budget_unpriced_model"


async def test_limit_without_ledger_fails_closed(monkeypatch):
    monkeypatch.setenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", "1000")
    with pytest.raises(UsageBudgetExceeded) as exc:
        await check_usage_budget(None, _route(), profile_budget_usd=None)
    assert exc.value.code == "usage_ledger_unavailable"


async def test_run_kernel_blocks_before_building_client_and_records_usage(monkeypatch):
    from apps.cosa.worker import run_core

    monkeypatch.setenv("COSA_WORKSPACE_MONTHLY_TOKEN_QUOTA", "1000")
    route = _route()
    ledger = InMemoryUsageLedger()
    created: list[str] = []

    class _Factory:
        async def create(self, r):
            created.append(r.profile_id)
            return object()

    class _Kernel:
        async def run(self, req, spec):
            return SimpleNamespace(
                status="completed", usage={"prompt_tokens": 400, "completion_tokens": 200}
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
        model_provider_factory=_Factory(),
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
        spec=SimpleNamespace(id="cosa.agents.operations"),
        req=SimpleNamespace(workspace_id="ws1", model_policy={}, metadata={"project_id": "proj1"}),
    )

    await run_core.run_kernel(plane, prep, workspace_id="ws1", run_id="r1")
    [entry] = ledger.entries
    assert (entry.profile_id, entry.project_id, entry.prompt_tokens, entry.completion_tokens) == (
        "p-deepseek",
        "proj1",
        400,
        200,
    )
    assert entry.cost_usd is not None and entry.cost_usd > 0

    await run_core.run_kernel(plane, prep, workspace_id="ws1", run_id="r2")  # 600 < 1000
    created.clear()
    with pytest.raises(run_core.RunCoreError) as exc:
        await run_core.run_kernel(plane, prep, workspace_id="ws1", run_id="r3")  # 1200 >= 1000
    assert exc.value.reason_code == "usage_budget_exceeded"
    assert exc.value.compliance_code == "workspace_token_quota_exceeded"
    assert created == []  # chặn TRƯỚC khi dựng model client


def _async(value):
    async def _f(*a, **k):
        return value

    return _f


_RAW = os.environ.get("AGENT_TEST_DATABASE_URL") or ""
_PG = (
    _RAW.replace("postgresql://", "postgresql+asyncpg://", 1)
    if _RAW.startswith("postgresql://")
    else _RAW
)


@pytest.mark.skipif(not _PG, reason="AGENT_TEST_DATABASE_URL not set")
async def test_postgres_ledger_matches_in_memory():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(_PG)
    try:
        pg = PostgresUsageLedger(async_sessionmaker(engine, expire_on_commit=False))
        mem = InMemoryUsageLedger()
        ws = f"ws_{uuid.uuid4().hex[:8]}"
        since = datetime.now(UTC) - timedelta(minutes=1)
        for ledger in (pg, mem):
            await ledger.record(_entry(ws=ws, tokens=(10, 5), cost="0.25"))
            await ledger.record(_entry(ws=ws, profile="other", tokens=(1, 1), cost=None))
        for ledger in (pg, mem):
            assert await ledger.total_tokens(ws, since) == 17
            assert await ledger.total_cost_usd(ws, since) == Decimal("0.25")
            assert await ledger.total_cost_usd(ws, since, "other") == Decimal(0)
            assert await ledger.total_cost_usd(ws, since, "p-deepseek") == Decimal("0.25")
    finally:
        await engine.dispose()


async def test_usage_without_durable_initiative_id_is_recorded_unattributed_not_guessed():
    ledger = InMemoryUsageLedger()
    entry = await ledger.record(_entry())
    assert entry.initiative_id is None


async def test_usage_with_durable_initiative_id_is_recorded_and_aggregated():
    ledger = InMemoryUsageLedger()
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-1",
            run_id="run-1",
            profile_id="p1",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=Decimal("0.15"),
        )
    )
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-1",
            run_id="run-2",
            profile_id="p1",
            prompt_tokens=200,
            completion_tokens=100,
            cost_usd=Decimal("0.35"),
        )
    )
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-2",
            run_id="run-3",
            profile_id="p1",
            prompt_tokens=50,
            completion_tokens=25,
            cost_usd=Decimal("0.05"),
        )
    )
    total_init1 = await ledger.total_cost_for_initiative("ws1", "proj1", "init-1")
    assert total_init1 == Decimal("0.50")
    total_init2 = await ledger.total_cost_for_initiative("ws1", "proj1", "init-2")
    assert total_init2 == Decimal("0.05")


async def test_initiative_budget_allow_warn_and_hard_pause():
    from apps.cosa.models.usage import (
        InitiativeBudgetAction,
        check_initiative_budget,
    )

    ledger = InMemoryUsageLedger()
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-1",
            run_id="run-1",
            profile_id="p1",
            cost_usd=Decimal("5.00"),
        )
    )
    # Below soft limit: ALLOW
    decision = await check_initiative_budget(
        ledger,
        workspace_id="ws1",
        project_id="proj1",
        initiative_id="init-1",
        soft_budget_usd=10.0,
        hard_budget_usd=20.0,
    )
    assert decision.action == InitiativeBudgetAction.ALLOW

    # Above soft limit: WARN
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-1",
            run_id="run-2",
            profile_id="p1",
            cost_usd=Decimal("6.00"),
        )
    )
    decision_warn = await check_initiative_budget(
        ledger,
        workspace_id="ws1",
        project_id="proj1",
        initiative_id="init-1",
        soft_budget_usd=10.0,
        hard_budget_usd=20.0,
    )
    assert decision_warn.action == InitiativeBudgetAction.WARN

    # Above hard limit: PAUSE_INITIATIVE / UsageBudgetExceeded
    await ledger.record(
        UsageEntry(
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-1",
            run_id="run-3",
            profile_id="p1",
            cost_usd=Decimal("10.00"),
        )
    )
    with pytest.raises(UsageBudgetExceeded, match="initiative_budget_paused"):
        await check_initiative_budget(
            ledger,
            workspace_id="ws1",
            project_id="proj1",
            initiative_id="init-1",
            soft_budget_usd=10.0,
            hard_budget_usd=20.0,
        )
