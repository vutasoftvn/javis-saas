"""Tests for COSA Context Assembler (Phase 7).

Theo Hermes/LangGraph Integration Plan §3 (Phase 7):
- Assemble context cho intent thật trả về ContextSnapshot đúng lifetime (STABLE, RUN, CURRENT, EPHEMERAL).
- Đảm bảo tuân thủ Governance-before-fetch.
- Kiểm tra không import SQLAlchemy ORM models.
"""

from __future__ import annotations

import pytest

from agent.contracts.context import ContextIntent, ContextLifetime
from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.composition.context_assembler import COSAContextAssembler, ContextAssemblerPort
from apps.cosa.policies.evaluator import CosaPolicyEngine


class MockCompanyClient(CompanyServiceClient):
    async def list_tasks(self, workspace_id: str):
        return {
            "status": "success",
            "tasks": [
                {"id": "t1", "title": "Deploy Phase 7"},
                {"id": "t2", "title": "Run Integration Suite"},
            ],
        }


@pytest.mark.asyncio
async def test_context_assembler_intent_and_lifetimes():
    client = MockCompanyClient()
    policy_engine = CosaPolicyEngine()
    assembler = COSAContextAssembler(client, policy_engine)

    assert isinstance(assembler, ContextAssemblerPort)

    # 1. Test Strategic Review Intent -> STABLE + RUN fragments
    intent_strat = ContextIntent(kind="strategic_review", domain="operations")
    snapshot_strat = await assembler.assemble(
        run_id="run_strat_01",
        principal_id="founder_alice",
        tenant_id="ws_acme",
        intent=intent_strat,
        metadata={"user_query": "Review Q3 goals"},
    )

    assert snapshot_strat.run_id == "run_strat_01"
    assert snapshot_strat.tenant_id == "ws_acme"
    
    lifetimes = {f.lifetime: f for f in snapshot_strat.fragments}
    assert ContextLifetime.STABLE in lifetimes
    assert ContextLifetime.RUN in lifetimes
    assert ContextLifetime.EPHEMERAL in lifetimes
    assert "Deploy Phase 7" in lifetimes[ContextLifetime.RUN].content
    assert snapshot_strat.budget_tokens_remaining < 16000

    # 2. Test Finance Decision Intent -> STABLE + RUN + CURRENT + EPHEMERAL
    intent_fin = ContextIntent(kind="founder_decision", domain="finance")
    snapshot_fin = await assembler.assemble(
        run_id="run_fin_01",
        principal_id="founder_alice",
        tenant_id="ws_acme",
        intent=intent_fin,
    )

    fin_lifetimes = {f.lifetime for f in snapshot_fin.fragments}
    assert ContextLifetime.STABLE in fin_lifetimes
    assert ContextLifetime.RUN in fin_lifetimes
    assert ContextLifetime.CURRENT in fin_lifetimes


def test_boundary_audit_no_sqlalchemy_in_assembler():
    """Kiểm tra boundary audit: context_assembler.py tuyệt đối không import SQLAlchemy ORM models."""
    with open("apps/cosa/composition/context_assembler.py", "r", encoding="utf-8") as f:
        content = f.read()

    assert "import sqlalchemy" not in content.lower()
    assert "from sqlalchemy" not in content.lower()
