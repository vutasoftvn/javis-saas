"""Dựng `event_intake_deps` production cho `/agent/internal/events`.

P0 để `event_intake_deps=None` ngoài test — vòng lặp event→inbox→trigger→run
không chạy production. `build_event_intake_deps()` assemble tất cả từ
`AGENT_CORE_DATABASE_URL` + registry của plane, gọi ở `app.py` lifespan sau
`build_cosa_agent_plane()` (giống `seed_cosa_agent_specs`).
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from typing import Any

from apps.cosa.config.planes import resolve_execution_plane_url
from apps.cosa.events.capability_checker import RegistryBackedCapabilityChecker
from apps.cosa.events.execution_plane_client import LocalExecutionPlaneScheduleClient
from apps.cosa.events.fingerprints import SpecFingerprintProvider
from apps.cosa.events.local_auth import LocalServiceAuth
from apps.cosa.events.rule_store import PostgresTriggerRuleStore
from apps.cosa.events.run_counter import PostgresRunCounter
from apps.cosa.events.trigger_policy import TriggerPolicyService

__all__ = ["EventIntakeDeps", "build_event_intake_deps"]


def _raw_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")


class _AsyncpgTx:
    """Adapter cho `deps.db` — `.begin()` async ctx yield một asyncpg connection
    trong transaction (khớp `apps/cosa/events/inbox.py` dùng conn.fetchrow/execute)."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    @contextlib.asynccontextmanager
    async def begin(self):
        async with self._pool.acquire() as conn:
            tx = conn.transaction()
            await tx.start()
            try:
                yield conn
            except Exception:
                await tx.rollback()
                raise
            else:
                await tx.commit()

    async def aclose(self) -> None:
        await self._pool.close()


@dataclass
class EventIntakeDeps:
    local_auth: Any
    db: Any
    trigger_policy: Any
    execution_plane: Any
    rule_store: Any
    evidence_store: Any
    fingerprint_provider: Any
    caller_workspace_id: str | None = None

    async def aclose(self) -> None:
        for c in (self.db, self.execution_plane):
            fn = getattr(c, "aclose", None)
            if fn is not None:
                await fn()


async def build_event_intake_deps(
    *,
    database_url: str,
    spec_registry: Any,
    capability_registry: Any,
) -> EventIntakeDeps:
    import asyncpg
    from agent_core.evals.promotion_repository import PostgresPromotionEvidenceRepository
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    pool = await asyncpg.create_pool(_raw_dsn(database_url), min_size=1, max_size=8)

    engine = create_async_engine(
        database_url
        if "+asyncpg" in database_url
        else database_url.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    evidence_store = PostgresPromotionEvidenceRepository(session_factory)

    rule_store = PostgresTriggerRuleStore(pool)
    fingerprint_provider = SpecFingerprintProvider(spec_registry)
    trigger_policy = TriggerPolicyService(
        rule_store,
        RegistryBackedCapabilityChecker(capability_registry),
        PostgresRunCounter(pool),
        evidence_store=evidence_store,
        fingerprint_provider=fingerprint_provider,
        policy_version=os.environ.get("COSA_POLICY_VERSION", "p1"),
    )

    return EventIntakeDeps(
        local_auth=LocalServiceAuth(),
        db=_AsyncpgTx(pool),
        trigger_policy=trigger_policy,
        execution_plane=LocalExecutionPlaneScheduleClient(
            resolve_execution_plane_url(), os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        ),
        rule_store=rule_store,
        evidence_store=evidence_store,
        fingerprint_provider=fingerprint_provider,
        caller_workspace_id=None,  # node đa-workspace; HMAC là ranh giới tin cậy
    )
