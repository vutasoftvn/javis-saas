"""Founder delegation cho workforce control (Task 6).

`require_founder_or_delegate` là điểm kiểm quyền DUY NHẤT cho các lệnh
founder-scope (evaluation, queue_control, review_override). Founder luôn pass;
principal khác chỉ pass khi có delegation ACTIVE, chưa hết hạn, đúng
action_scope và (functional_key khớp hoặc delegation không giới hạn key).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

ActionScope = Literal["evaluation", "queue_control", "review_override"]


class FounderApprovalRequired(PermissionError):
    """Principal không phải founder và không có delegation phù hợp."""


@dataclass(frozen=True)
class WorkforceDelegationRecord:
    delegation_id: UUID
    workspace_id: str
    grantor_id: str
    principal_id: str
    action_scope: str
    functional_key: str | None
    status: Literal["ACTIVE", "REVOKED"]
    granted_at: datetime
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None

    def is_effective(self, at: datetime | None = None) -> bool:
        now = at or datetime.now(UTC)
        if self.status != "ACTIVE":
            return False
        return not (self.expires_at is not None and self.expires_at <= now)


class WorkforceDelegationRepository(Protocol):
    async def grant_delegation(
        self,
        workspace_id: str,
        grantor_id: str,
        principal_id: str,
        action_scope: str,
        functional_key: str | None,
        expires_at: datetime | None,
    ) -> WorkforceDelegationRecord: ...

    async def revoke_delegation(
        self, workspace_id: str, delegation_id: UUID | str, revoked_by: str
    ) -> WorkforceDelegationRecord | None: ...

    async def list_active_delegations(
        self, workspace_id: str, principal_id: str, action_scope: str
    ) -> list[WorkforceDelegationRecord]: ...


class FounderCheck(Protocol):
    async def is_founder(self, workspace_id: str, principal_id: str) -> bool: ...


async def require_founder_or_delegate(
    *,
    repository: WorkforceDelegationRepository,
    founder_check: FounderCheck,
    workspace_id: str,
    principal_id: str,
    action: str,
    functional_key: str | None,
) -> None:
    if await founder_check.is_founder(workspace_id, principal_id):
        return

    delegations = await repository.list_active_delegations(workspace_id, principal_id, action)
    for d in delegations:
        if not d.is_effective():
            continue
        if (
            d.functional_key is not None
            and functional_key is not None
            and d.functional_key != functional_key
        ):
            continue
        return

    raise FounderApprovalRequired(
        f"principal {principal_id!r} lacks founder authority or an active "
        f"delegation for {action!r} (functional_key={functional_key!r})"
    )


class InMemoryWorkforceDelegationRepository:
    def __init__(self) -> None:
        self._rows: dict[UUID, WorkforceDelegationRecord] = {}

    async def grant_delegation(
        self,
        workspace_id: str,
        grantor_id: str,
        principal_id: str,
        action_scope: str,
        functional_key: str | None,
        expires_at: datetime | None,
    ) -> WorkforceDelegationRecord:
        did = uuid4()
        rec = WorkforceDelegationRecord(
            delegation_id=did,
            workspace_id=workspace_id,
            grantor_id=grantor_id,
            principal_id=principal_id,
            action_scope=action_scope,
            functional_key=functional_key,
            status="ACTIVE",
            granted_at=datetime.now(UTC),
            expires_at=expires_at,
        )
        self._rows[did] = rec
        return rec

    async def revoke_delegation(
        self, workspace_id: str, delegation_id: UUID | str, revoked_by: str
    ) -> WorkforceDelegationRecord | None:
        try:
            did = UUID(str(delegation_id))
        except ValueError:
            return None
        rec = self._rows.get(did)
        if not rec or rec.workspace_id != workspace_id:
            return None
        revoked = WorkforceDelegationRecord(
            **{
                **rec.__dict__,
                "status": "REVOKED",
                "revoked_at": datetime.now(UTC),
                "revoked_by": revoked_by,
            }
        )
        self._rows[did] = revoked
        return revoked

    async def list_active_delegations(
        self, workspace_id: str, principal_id: str, action_scope: str
    ) -> list[WorkforceDelegationRecord]:
        return [
            r
            for r in self._rows.values()
            if r.workspace_id == workspace_id
            and r.principal_id == principal_id
            and r.action_scope == action_scope
            and r.status == "ACTIVE"
        ]


class PostgresWorkforceDelegationRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def grant_delegation(
        self,
        workspace_id: str,
        grantor_id: str,
        principal_id: str,
        action_scope: str,
        functional_key: str | None,
        expires_at: datetime | None,
    ) -> WorkforceDelegationRecord:
        did = uuid4()
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.workforce_delegations (
                        delegation_id, workspace_id, grantor_id, principal_id, action_scope,
                        functional_key, status, granted_at, expires_at
                    ) VALUES (
                        :delegation_id, :workspace_id, :grantor_id, :principal_id, :action_scope,
                        :functional_key, 'ACTIVE', :granted_at, :expires_at
                    )
                    """
                ),
                {
                    "delegation_id": str(did),
                    "workspace_id": workspace_id,
                    "grantor_id": grantor_id,
                    "principal_id": principal_id,
                    "action_scope": action_scope,
                    "functional_key": functional_key,
                    "granted_at": now,
                    "expires_at": expires_at,
                },
            )
            await session.execute(
                text(
                    """
                    INSERT INTO agent.workforce_delegation_events (
                        event_id, delegation_id, workspace_id, event_type, actor_id, payload
                    ) VALUES (:event_id, :delegation_id, :workspace_id, 'granted', :actor_id, '{}'::jsonb)
                    """
                ),
                {
                    "event_id": str(uuid4()),
                    "delegation_id": str(did),
                    "workspace_id": workspace_id,
                    "actor_id": grantor_id,
                },
            )
            await session.commit()
        return WorkforceDelegationRecord(
            delegation_id=did,
            workspace_id=workspace_id,
            grantor_id=grantor_id,
            principal_id=principal_id,
            action_scope=action_scope,
            functional_key=functional_key,
            status="ACTIVE",
            granted_at=now,
            expires_at=expires_at,
        )

    async def revoke_delegation(
        self, workspace_id: str, delegation_id: UUID | str, revoked_by: str
    ) -> WorkforceDelegationRecord | None:
        try:
            did = UUID(str(delegation_id))
        except ValueError:
            return None
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    UPDATE agent.workforce_delegations
                    SET status = 'REVOKED', revoked_at = :now, revoked_by = :revoked_by
                    WHERE workspace_id = :workspace_id AND delegation_id = :delegation_id
                    RETURNING delegation_id, workspace_id, grantor_id, principal_id, action_scope,
                              functional_key, status, granted_at, expires_at, revoked_at, revoked_by
                    """
                ),
                {
                    "now": now,
                    "revoked_by": revoked_by,
                    "workspace_id": workspace_id,
                    "delegation_id": str(did),
                },
            )
            row = res.mappings().first()
            if row is None:
                await session.rollback()
                return None
            await session.execute(
                text(
                    """
                    INSERT INTO agent.workforce_delegation_events (
                        event_id, delegation_id, workspace_id, event_type, actor_id, payload
                    ) VALUES (:event_id, :delegation_id, :workspace_id, 'revoked', :actor_id, '{}'::jsonb)
                    """
                ),
                {
                    "event_id": str(uuid4()),
                    "delegation_id": str(did),
                    "workspace_id": workspace_id,
                    "actor_id": revoked_by,
                },
            )
            await session.commit()
            return _row_to_delegation(row)

    async def list_active_delegations(
        self, workspace_id: str, principal_id: str, action_scope: str
    ) -> list[WorkforceDelegationRecord]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT delegation_id, workspace_id, grantor_id, principal_id, action_scope,
                           functional_key, status, granted_at, expires_at, revoked_at, revoked_by
                    FROM agent.workforce_delegations
                    WHERE workspace_id = :workspace_id AND principal_id = :principal_id
                      AND action_scope = :action_scope AND status = 'ACTIVE'
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "principal_id": principal_id,
                    "action_scope": action_scope,
                },
            )
            return [_row_to_delegation(r) for r in res.mappings().all()]


def _row_to_delegation(row: Any) -> WorkforceDelegationRecord:
    return WorkforceDelegationRecord(
        delegation_id=UUID(str(row["delegation_id"])),
        workspace_id=row["workspace_id"],
        grantor_id=row["grantor_id"],
        principal_id=row["principal_id"],
        action_scope=row["action_scope"],
        functional_key=row["functional_key"],
        status=row["status"],
        granted_at=row["granted_at"],
        expires_at=row["expires_at"],
        revoked_at=row.get("revoked_at") if hasattr(row, "get") else row["revoked_at"],
        revoked_by=row.get("revoked_by") if hasattr(row, "get") else row["revoked_by"],
    )
