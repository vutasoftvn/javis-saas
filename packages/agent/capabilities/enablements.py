"""Durable Capability Enablement Registry (Tranche C / Task 1).

Theo Tranche C Plan §1 & §4:
Một capability chỉ có thể được gọi với action_class ('B', 'X', 'M', 'D') khi có bản ghi
CapabilityEnablement hợp lệ, đúng workspace, đúng skill_hash, đúng target, chưa hết hạn và chưa bị thu hồi.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

__all__ = [
    "CapabilityEnablement",
    "EnablementStore",
    "InMemoryEnablementStore",
    "PostgresEnablementStore",
    "assert_enabled_for_invocation",
]


@dataclass
class CapabilityEnablement:
    id: str = field(default_factory=lambda: f"enb_{uuid.uuid4().hex[:12]}")
    workspace_id: str = ""
    capability_id: str = ""
    skill_id: str = ""
    skill_hash: str = ""
    action_class: str = "B"  # 'R', 'A', 'B', 'X', 'M', 'D'
    target_fingerprint: str = "*"
    permitted_limits: dict[str, Any] = field(default_factory=dict)
    status: str = "ENABLED"  # 'ENABLED', 'REVOKED', 'EXPIRED'
    source_approval_id: str | None = None
    evaluation_ref: str | None = None
    rollback_ref: str | None = None
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_active(self) -> bool:
        return self.status == "ENABLED" and (
            self.expires_at is None or datetime.now(UTC) < self.expires_at
        )


@runtime_checkable
class EnablementStore(Protocol):
    async def get_enablement(
        self,
        workspace_id: str,
        capability_id: str,
        skill_hash: str,
        action_class: str,
        target_fingerprint: str = "*",
    ) -> CapabilityEnablement | None: ...

    async def save_enablement(self, enablement: CapabilityEnablement) -> None: ...

    async def revoke_enablement(self, enablement_id: str) -> None: ...


class InMemoryEnablementStore:
    def __init__(self) -> None:
        self._enablements: dict[str, CapabilityEnablement] = {}

    async def get_enablement(
        self,
        workspace_id: str,
        capability_id: str,
        skill_hash: str,
        action_class: str,
        target_fingerprint: str = "*",
    ) -> CapabilityEnablement | None:
        for enb in self._enablements.values():
            if (
                enb.workspace_id == workspace_id
                and enb.capability_id == capability_id
                and enb.skill_hash == skill_hash
                and enb.action_class == action_class
                and enb.target_fingerprint in {"*", target_fingerprint}
            ):
                return enb
        return None

    async def save_enablement(self, enablement: CapabilityEnablement) -> None:
        self._enablements[enablement.id] = enablement

    async def revoke_enablement(self, enablement_id: str) -> None:
        if enablement_id in self._enablements:
            self._enablements[enablement_id].status = "REVOKED"


class PostgresEnablementStore:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def get_enablement(
        self,
        workspace_id: str,
        capability_id: str,
        skill_hash: str,
        action_class: str,
        target_fingerprint: str = "*",
    ) -> CapabilityEnablement | None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            stmt = text(
                """
                SELECT id, workspace_id, capability_id, skill_id, skill_hash, action_class,
                       target_fingerprint, permitted_limits, status, source_approval_id,
                       evaluation_ref, rollback_ref, expires_at, created_at
                FROM agent_capability_enablements
                WHERE workspace_id = :ws_id
                  AND capability_id = :cap_id
                  AND skill_hash = :skill_hash
                  AND action_class = :action_class
                  AND (target_fingerprint = '*' OR target_fingerprint = :target_fingerprint)
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            res = await session.execute(
                stmt,
                {
                    "ws_id": workspace_id,
                    "cap_id": capability_id,
                    "skill_hash": skill_hash,
                    "action_class": action_class,
                    "target_fingerprint": target_fingerprint,
                },
            )
            row = res.mappings().first()
            if not row:
                return None
            return CapabilityEnablement(
                id=row["id"],
                workspace_id=row["workspace_id"],
                capability_id=row["capability_id"],
                skill_id=row["skill_id"],
                skill_hash=row["skill_hash"],
                action_class=row["action_class"],
                target_fingerprint=row["target_fingerprint"],
                permitted_limits=row["permitted_limits"] or {},
                status=row["status"],
                source_approval_id=row["source_approval_id"],
                evaluation_ref=row["evaluation_ref"],
                rollback_ref=row["rollback_ref"],
                expires_at=row["expires_at"],
                created_at=row["created_at"],
            )

    async def save_enablement(self, enablement: CapabilityEnablement) -> None:
        import json

        from sqlalchemy import text

        async with self._session_factory() as session:
            stmt = text(
                """
                INSERT INTO agent_capability_enablements (
                    id, workspace_id, capability_id, skill_id, skill_hash, action_class,
                    target_fingerprint, permitted_limits, status, source_approval_id,
                    evaluation_ref, rollback_ref, expires_at, created_at
                ) VALUES (
                    :id, :ws_id, :cap_id, :skill_id, :skill_hash, :action_class,
                    :target_fingerprint, :permitted_limits::jsonb, :status, :source_approval_id,
                    :evaluation_ref, :rollback_ref, :expires_at, :created_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    permitted_limits = EXCLUDED.permitted_limits,
                    expires_at = EXCLUDED.expires_at
                """
            )
            await session.execute(
                stmt,
                {
                    "id": enablement.id,
                    "ws_id": enablement.workspace_id,
                    "cap_id": enablement.capability_id,
                    "skill_id": enablement.skill_id,
                    "skill_hash": enablement.skill_hash,
                    "action_class": enablement.action_class,
                    "target_fingerprint": enablement.target_fingerprint,
                    "permitted_limits": json.dumps(enablement.permitted_limits),
                    "status": enablement.status,
                    "source_approval_id": enablement.source_approval_id,
                    "evaluation_ref": enablement.evaluation_ref,
                    "rollback_ref": enablement.rollback_ref,
                    "expires_at": enablement.expires_at,
                    "created_at": enablement.created_at,
                },
            )
            await session.commit()

    async def revoke_enablement(self, enablement_id: str) -> None:
        from sqlalchemy import text

        async with self._session_factory() as session:
            stmt = text(
                """
                UPDATE agent_capability_enablements
                SET status = 'REVOKED'
                WHERE id = :id
                """
            )
            await session.execute(stmt, {"id": enablement_id})
            await session.commit()


async def assert_enabled_for_invocation(
    enablement_store: EnablementStore,
    workspace_id: str,
    capability_id: str,
    skill_hash: str | None,
    action_class: str = "R",
    target_fingerprint: str = "*",
) -> tuple[bool, str | None]:
    """Kiểm tra điều kiện enablement cho một lần gọi capability.

    Quy tắc:
    - 'R' và 'A' được phép chạy qua tenancy/readiness cơ bản.
    - 'B', 'X', 'M', 'D' bắt buộc phải có bản ghi enablement hợp lệ và active.
    """
    if action_class in ("R", "A"):
        return True, None

    if not skill_hash:
        return (
            False,
            f"Capability '{capability_id}' requires exact skill definition_hash for action class '{action_class}'",
        )

    if not workspace_id:
        return (
            False,
            f"Capability '{capability_id}' requires workspace_id for action class '{action_class}'",
        )

    enb = await enablement_store.get_enablement(
        workspace_id=workspace_id,
        capability_id=capability_id,
        skill_hash=skill_hash,
        action_class=action_class,
        target_fingerprint=target_fingerprint,
    )

    if not enb:
        return (
            False,
            f"No enablement record found for capability '{capability_id}' in workspace '{workspace_id}' (action_class={action_class}, skill_hash={skill_hash[:12]}...)",
        )

    if not enb.is_active:
        return (
            False,
            f"Enablement record '{enb.id}' for capability '{capability_id}' is not active (status={enb.status}, expires_at={enb.expires_at})",
        )

    return True, None
