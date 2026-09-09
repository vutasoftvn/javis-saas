from __future__ import annotations

import os
from uuid import uuid4

import pytest
from agent.workforce.repository import (
    DuplicateEmployeeCodeError,
    EmployeeNotAssignableError,
    InMemoryWorkforceRepository,
    PostgresWorkforceRepository,
    WorkforceRepository,
)


def get_workforce_repo(kind: str) -> WorkforceRepository:
    if kind == "in_memory":
        return InMemoryWorkforceRepository()
    elif kind == "postgres":
        db_url = os.environ.get("AGENT_TEST_DATABASE_URL") or os.environ.get("AGENT_DATABASE_URL")
        if not db_url:
            pytest.skip("AGENT_DATABASE_URL not set for PostgresWorkforceRepository test")
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        asyncpg_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(asyncpg_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        return PostgresWorkforceRepository(session_factory)
    raise ValueError(f"Unknown kind: {kind}")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_employee_code_is_unique_and_identity_is_not_reused(kind: str) -> None:
    repo = get_workforce_repo(kind)
    first = await repo.create_employee("ws_a", "AGT-FIN-001", "Finance Analyst #1", "founder_a")
    assert first.status == "ACTIVE"
    assert first.workspace_id == "ws_a"

    with pytest.raises(DuplicateEmployeeCodeError):
        await repo.create_employee("ws_a", "AGT-FIN-001", "Other", "founder_a")

    retired = await repo.retire_employee("ws_a", first.agent_instance_id)
    assert retired is not None
    assert retired.status == "RETIRED"
    assert retired.retired_at is not None
    assert await repo.get_employee("ws_a", first.agent_instance_id) == retired

    # employee_code stays reserved; a fresh create with the same code still fails
    with pytest.raises(DuplicateEmployeeCodeError):
        await repo.create_employee("ws_a", "AGT-FIN-001", "Reincarnation", "founder_a")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_same_code_allowed_in_a_different_workspace(kind: str) -> None:
    repo = get_workforce_repo(kind)
    a = await repo.create_employee("ws_a", "AGT-OPS-001", "Ops #1", "founder_a")
    b = await repo.create_employee("ws_b", "AGT-OPS-001", "Ops #1", "founder_b")
    assert a.agent_instance_id != b.agent_instance_id
    assert await repo.get_employee("ws_a", b.agent_instance_id) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_suspend_and_retire_are_scoped_and_lifecycle_only(kind: str) -> None:
    repo = get_workforce_repo(kind)
    emp = await repo.create_employee("ws_a", "AGT-MKT-001", "Marketing #1", "founder_a")

    assert await repo.suspend_employee("ws_b", emp.agent_instance_id) is None
    assert await repo.retire_employee("ws_b", emp.agent_instance_id) is None

    suspended = await repo.suspend_employee("ws_a", emp.agent_instance_id)
    assert suspended is not None
    assert suspended.status == "SUSPENDED"
    assert suspended.suspended_at is not None
    assert suspended.agent_instance_id == emp.agent_instance_id

    active_only = await repo.list_employees("ws_a", status="ACTIVE")
    assert all(e.agent_instance_id != emp.agent_instance_id for e in active_only)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_assignment_requires_an_active_employee_when_linked(kind: str) -> None:
    repo = get_workforce_repo(kind)
    emp = await repo.create_employee("ws_a", "AGT-OPS-050", "Ops #50", "founder_a")

    # Happy path: ACTIVE employee can be linked to an assignment.
    ok = await repo.create_assignment(
        workspace_id="ws_a",
        functional_key="operations",
        spec_id="functional.operations",
        spec_version="1.0.0",
        definition_hash="sha256:ops",
        configured_by="founder_a",
        agent_instance_id=emp.agent_instance_id,
    )
    assert str(ok.agent_instance_id) == str(emp.agent_instance_id)

    await repo.suspend_employee("ws_a", emp.agent_instance_id)
    with pytest.raises(EmployeeNotAssignableError):
        await repo.create_assignment(
            workspace_id="ws_a",
            functional_key="operations",
            spec_id="functional.operations",
            spec_version="2.0.0",
            definition_hash="sha256:ops-v2",
            configured_by="founder_a",
            agent_instance_id=emp.agent_instance_id,
        )

    await repo.retire_employee("ws_a", emp.agent_instance_id)
    with pytest.raises(EmployeeNotAssignableError):
        await repo.create_assignment(
            workspace_id="ws_a",
            functional_key="operations",
            spec_id="functional.operations",
            spec_version="3.0.0",
            definition_hash="sha256:ops-v3",
            configured_by="founder_a",
            agent_instance_id=emp.agent_instance_id,
        )

    # Unknown employee id is rejected too.
    with pytest.raises(EmployeeNotAssignableError):
        await repo.create_assignment(
            workspace_id="ws_a",
            functional_key="operations",
            spec_id="functional.operations",
            spec_version="9.0.0",
            definition_hash="sha256:ops-v9",
            configured_by="founder_a",
            agent_instance_id=str(uuid4()),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["in_memory"])
async def test_legacy_assignment_without_employee_link_still_allowed(kind: str) -> None:
    repo = get_workforce_repo(kind)
    legacy = await repo.create_assignment(
        workspace_id="ws_a",
        functional_key="operations",
        spec_id="functional.operations",
        spec_version="1.0.0",
        definition_hash="sha256:legacy",
        configured_by="founder_a",
    )
    assert legacy.agent_instance_id is None
