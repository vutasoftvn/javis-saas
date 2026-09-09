"""Founder-controlled Outcome Analysis policy + Skill Governance lifecycle
(Task 7A, spec §10).

Founder tạo DRAFT gồm changed field + analyst binding + pinned skill +
capability allowlist. CHỈ version PUBLISHED (qua founder approval + validation
capability/schema) mới bind cho request MỚI; publish không rewrite request
đang queue/running hay assessment lịch sử. Rollback đổi binding cho request
mới, không xóa evidence.

Manager KHÔNG publish được và KHÔNG thêm được capability write vào Outcome
skill (InvalidCapabilityBoundary).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agent.workforce.outcome_analysis import (
    OUTCOME_ANALYSIS_SKILL_ID,
    OUTCOME_ANALYST_CAPABILITY_REFS,
)

Policy = Literal["AUTO_ALL_TASKS", "AUTO_BY_RULE", "MANUAL"]


class FounderApprovalRequired(PermissionError):
    """Publish/rollback policy cần founder."""


class InvalidCapabilityBoundary(ValueError):
    """Capability allowlist chứa ref ngoài 6-item Outcome Analyst boundary."""


class StalePolicyDraft(ValueError):
    """expected_version không khớp draft hiện tại (optimistic concurrency)."""


class PolicyValidationError(ValueError):
    """Employee không ACTIVE / assignment không effective / skill chưa PUBLISHED."""


@dataclass(frozen=True)
class OutcomeAnalysisPolicyDraft:
    draft_id: UUID
    workspace_id: str
    analysis_kind: str
    policy: str
    analyst_employee_id: UUID
    analyst_assignment_id: UUID
    skill_id: str
    skill_version: str
    definition_hash: str
    capability_allowlist: tuple[str, ...]
    depth_rules: dict[str, object]
    status: str
    version: int
    created_by: str


@dataclass(frozen=True)
class OutcomeAnalysisPolicyVersion:
    policy_version_id: UUID
    workspace_id: str
    analysis_kind: str
    version_no: int
    policy: str
    analyst_employee_id: UUID
    analyst_assignment_id: UUID
    skill_id: str
    skill_version: str
    definition_hash: str
    capability_allowlist: tuple[str, ...]
    effective_at: datetime
    created_by: str
    approved_by: str
    rollback_target_version_id: UUID | None = None


def validate_capability_allowlist(refs: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    extra = [r for r in refs if r not in OUTCOME_ANALYST_CAPABILITY_REFS]
    if extra:
        raise InvalidCapabilityBoundary(
            f"capability refs outside the Outcome Analyst boundary: {', '.join(extra)}"
        )
    return tuple(refs)


class SkillGovernanceValidators(Protocol):
    async def is_founder(self, workspace_id: str, principal_id: str) -> bool: ...
    async def employee_is_active(self, workspace_id: str, employee_id: UUID) -> bool: ...
    async def assignment_is_effective(self, workspace_id: str, assignment_id: UUID) -> bool: ...
    async def skill_version_is_published(self, skill_id: str, skill_version: str) -> bool: ...


class SkillGovernanceRepository(Protocol):
    async def create_policy_draft(
        self, draft: OutcomeAnalysisPolicyDraft
    ) -> OutcomeAnalysisPolicyDraft: ...
    async def get_policy_draft(
        self, workspace_id: str, draft_id: UUID | str
    ) -> OutcomeAnalysisPolicyDraft | None: ...
    async def mark_draft_published(self, draft_id: UUID | str) -> None: ...
    async def next_version_no(self, workspace_id: str, analysis_kind: str) -> int: ...
    async def insert_policy_version(
        self, version: OutcomeAnalysisPolicyVersion
    ) -> OutcomeAnalysisPolicyVersion: ...
    async def latest_policy_version(
        self, workspace_id: str, analysis_kind: str
    ) -> OutcomeAnalysisPolicyVersion | None: ...
    async def get_policy_version(
        self, workspace_id: str, version_id: UUID | str
    ) -> OutcomeAnalysisPolicyVersion | None: ...
    async def append_event(
        self, workspace_id: str, analysis_kind: str, event_type: str, actor_id: str
    ) -> None: ...


@dataclass
class InMemorySkillGovernanceRepository:
    drafts: dict[UUID, OutcomeAnalysisPolicyDraft] = field(default_factory=dict)
    versions: list[OutcomeAnalysisPolicyVersion] = field(default_factory=list)
    events: list[tuple[str, str, str]] = field(default_factory=list)

    async def create_policy_draft(
        self, draft: OutcomeAnalysisPolicyDraft
    ) -> OutcomeAnalysisPolicyDraft:
        self.drafts[draft.draft_id] = draft
        return draft

    async def get_policy_draft(
        self, workspace_id: str, draft_id: UUID | str
    ) -> OutcomeAnalysisPolicyDraft | None:
        try:
            did = UUID(str(draft_id))
        except ValueError:
            return None
        d = self.drafts.get(did)
        return d if d and d.workspace_id == workspace_id else None

    async def mark_draft_published(self, draft_id: UUID | str) -> None:
        did = UUID(str(draft_id))
        d = self.drafts.get(did)
        if d:
            self.drafts[did] = OutcomeAnalysisPolicyDraft(**{**d.__dict__, "status": "PUBLISHED"})

    async def next_version_no(self, workspace_id: str, analysis_kind: str) -> int:
        existing = [
            v
            for v in self.versions
            if v.workspace_id == workspace_id and v.analysis_kind == analysis_kind
        ]
        return len(existing) + 1

    async def insert_policy_version(
        self, version: OutcomeAnalysisPolicyVersion
    ) -> OutcomeAnalysisPolicyVersion:
        self.versions.append(version)
        return version

    async def latest_policy_version(
        self, workspace_id: str, analysis_kind: str
    ) -> OutcomeAnalysisPolicyVersion | None:
        matches = [
            v
            for v in self.versions
            if v.workspace_id == workspace_id and v.analysis_kind == analysis_kind
        ]
        return matches[-1] if matches else None

    async def get_policy_version(
        self, workspace_id: str, version_id: UUID | str
    ) -> OutcomeAnalysisPolicyVersion | None:
        return next(
            (
                v
                for v in self.versions
                if str(v.policy_version_id) == str(version_id) and v.workspace_id == workspace_id
            ),
            None,
        )

    async def append_event(
        self, workspace_id: str, analysis_kind: str, event_type: str, actor_id: str
    ) -> None:
        self.events.append((analysis_kind, event_type, actor_id))


def _draft_row(d: OutcomeAnalysisPolicyDraft) -> dict[str, Any]:
    return {
        "draft_id": str(d.draft_id),
        "workspace_id": d.workspace_id,
        "analysis_kind": d.analysis_kind,
        "policy": d.policy,
        "analyst_employee_id": str(d.analyst_employee_id),
        "analyst_assignment_id": str(d.analyst_assignment_id),
        "skill_id": d.skill_id,
        "skill_version": d.skill_version,
        "definition_hash": d.definition_hash,
        "capability_allowlist": json.dumps(list(d.capability_allowlist)),
        "depth_rules": json.dumps(d.depth_rules),
        "status": d.status,
        "version": d.version,
        "created_by": d.created_by,
    }


def _to_draft(row: Any) -> OutcomeAnalysisPolicyDraft:
    def _j(v: Any, default: Any) -> Any:
        return default if v is None else (v if isinstance(v, (dict, list)) else json.loads(v))

    return OutcomeAnalysisPolicyDraft(
        draft_id=UUID(str(row["draft_id"])),
        workspace_id=row["workspace_id"],
        analysis_kind=row["analysis_kind"],
        policy=row["policy"],
        analyst_employee_id=UUID(str(row["analyst_employee_id"])),
        analyst_assignment_id=UUID(str(row["analyst_assignment_id"])),
        skill_id=row["skill_id"],
        skill_version=row["skill_version"],
        definition_hash=row["definition_hash"],
        capability_allowlist=tuple(_j(row["capability_allowlist"], [])),
        depth_rules=_j(row["depth_rules"], {}),
        status=row["status"],
        version=row["version"],
        created_by=row["created_by"],
    )


def _to_version(row: Any) -> OutcomeAnalysisPolicyVersion:
    def _j(v: Any, default: Any) -> Any:
        return default if v is None else (v if isinstance(v, (dict, list)) else json.loads(v))

    return OutcomeAnalysisPolicyVersion(
        policy_version_id=UUID(str(row["policy_version_id"])),
        workspace_id=row["workspace_id"],
        analysis_kind=row["analysis_kind"],
        version_no=row["version_no"],
        policy=row["policy"],
        analyst_employee_id=UUID(str(row["analyst_employee_id"])),
        analyst_assignment_id=UUID(str(row["analyst_assignment_id"])),
        skill_id=row["skill_id"],
        skill_version=row["skill_version"],
        definition_hash=row["definition_hash"],
        capability_allowlist=tuple(_j(row["capability_allowlist"], [])),
        effective_at=row["effective_at"],
        created_by=row["created_by"],
        approved_by=row["approved_by"],
        rollback_target_version_id=(
            UUID(str(row["rollback_target_version_id"]))
            if row["rollback_target_version_id"]
            else None
        ),
    )


class PostgresSkillGovernanceRepository:
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_policy_draft(
        self, draft: OutcomeAnalysisPolicyDraft
    ) -> OutcomeAnalysisPolicyDraft:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.outcome_analysis_policy_drafts (
                        draft_id, workspace_id, analysis_kind, policy, analyst_employee_id,
                        analyst_assignment_id, skill_id, skill_version, definition_hash,
                        capability_allowlist, depth_rules, status, version, created_by
                    ) VALUES (
                        :draft_id, :workspace_id, :analysis_kind, :policy, :analyst_employee_id,
                        :analyst_assignment_id, :skill_id, :skill_version, :definition_hash,
                        :capability_allowlist, :depth_rules, :status, :version, :created_by
                    )
                    """
                ),
                _draft_row(draft),
            )
            await session.commit()
        return draft

    async def get_policy_draft(
        self, workspace_id: str, draft_id: UUID | str
    ) -> OutcomeAnalysisPolicyDraft | None:
        try:
            did = UUID(str(draft_id))
        except ValueError:
            return None
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    "SELECT * FROM agent.outcome_analysis_policy_drafts "
                    "WHERE workspace_id = :w AND draft_id = :d"
                ),
                {"w": workspace_id, "d": str(did)},
            )
            row = res.mappings().first()
            return _to_draft(row) if row else None

    async def mark_draft_published(self, draft_id: UUID | str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    "UPDATE agent.outcome_analysis_policy_drafts "
                    "SET status = 'PUBLISHED', updated_at = now() WHERE draft_id = :d"
                ),
                {"d": str(draft_id)},
            )
            await session.commit()

    async def next_version_no(self, workspace_id: str, analysis_kind: str) -> int:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    "SELECT COALESCE(MAX(version_no), 0) + 1 AS n "
                    "FROM agent.outcome_analysis_policy_versions "
                    "WHERE workspace_id = :w AND analysis_kind = :k"
                ),
                {"w": workspace_id, "k": analysis_kind},
            )
            return int(res.scalar_one())

    async def insert_policy_version(
        self, version: OutcomeAnalysisPolicyVersion
    ) -> OutcomeAnalysisPolicyVersion:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.outcome_analysis_policy_versions (
                        policy_version_id, workspace_id, analysis_kind, version_no, policy,
                        analyst_employee_id, analyst_assignment_id, skill_id, skill_version,
                        definition_hash, capability_allowlist, depth_rules, effective_at,
                        created_by, approved_by, rollback_target_version_id
                    ) VALUES (
                        :policy_version_id, :workspace_id, :analysis_kind, :version_no, :policy,
                        :analyst_employee_id, :analyst_assignment_id, :skill_id, :skill_version,
                        :definition_hash, :capability_allowlist, '{}'::jsonb, :effective_at,
                        :created_by, :approved_by, :rollback_target_version_id
                    )
                    """
                ),
                {
                    "policy_version_id": str(version.policy_version_id),
                    "workspace_id": version.workspace_id,
                    "analysis_kind": version.analysis_kind,
                    "version_no": version.version_no,
                    "policy": version.policy,
                    "analyst_employee_id": str(version.analyst_employee_id),
                    "analyst_assignment_id": str(version.analyst_assignment_id),
                    "skill_id": version.skill_id,
                    "skill_version": version.skill_version,
                    "definition_hash": version.definition_hash,
                    "capability_allowlist": json.dumps(list(version.capability_allowlist)),
                    "effective_at": version.effective_at,
                    "created_by": version.created_by,
                    "approved_by": version.approved_by,
                    "rollback_target_version_id": (
                        str(version.rollback_target_version_id)
                        if version.rollback_target_version_id
                        else None
                    ),
                },
            )
            await session.commit()
        return version

    async def latest_policy_version(
        self, workspace_id: str, analysis_kind: str
    ) -> OutcomeAnalysisPolicyVersion | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    "SELECT * FROM agent.outcome_analysis_policy_versions "
                    "WHERE workspace_id = :w AND analysis_kind = :k "
                    "ORDER BY version_no DESC LIMIT 1"
                ),
                {"w": workspace_id, "k": analysis_kind},
            )
            row = res.mappings().first()
            return _to_version(row) if row else None

    async def get_policy_version(
        self, workspace_id: str, version_id: UUID | str
    ) -> OutcomeAnalysisPolicyVersion | None:
        try:
            vid = UUID(str(version_id))
        except ValueError:
            return None
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    "SELECT * FROM agent.outcome_analysis_policy_versions "
                    "WHERE workspace_id = :w AND policy_version_id = :v"
                ),
                {"w": workspace_id, "v": str(vid)},
            )
            row = res.mappings().first()
            return _to_version(row) if row else None

    async def append_event(
        self, workspace_id: str, analysis_kind: str, event_type: str, actor_id: str
    ) -> None:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent.outcome_analysis_policy_events (
                        event_id, workspace_id, analysis_kind, event_type, actor_id, payload
                    ) VALUES (:e, :w, :k, :t, :a, '{}'::jsonb)
                    """
                ),
                {
                    "e": str(uuid4()),
                    "w": workspace_id,
                    "k": analysis_kind,
                    "t": event_type,
                    "a": actor_id,
                },
            )
            await session.commit()


async def create_policy_draft(
    *,
    repository: SkillGovernanceRepository,
    workspace_id: str,
    created_by: str,
    payload: dict[str, Any],
    analysis_kind: str = "TASK_OUTCOME",
) -> OutcomeAnalysisPolicyDraft:
    """Founder-owned draft. Không side-effect lên binding hiện hành."""
    allowlist = validate_capability_allowlist(
        list(payload.get("capability_allowlist") or list(OUTCOME_ANALYST_CAPABILITY_REFS))
    )
    skill_id = str(payload.get("skill_id", OUTCOME_ANALYSIS_SKILL_ID))
    if skill_id != OUTCOME_ANALYSIS_SKILL_ID:
        raise PolicyValidationError(f"skill_id must be {OUTCOME_ANALYSIS_SKILL_ID}")

    draft = OutcomeAnalysisPolicyDraft(
        draft_id=uuid4(),
        workspace_id=workspace_id,
        analysis_kind=analysis_kind,
        policy=str(payload["policy"]),
        analyst_employee_id=UUID(str(payload["analyst_employee_id"])),
        analyst_assignment_id=UUID(str(payload["analyst_assignment_id"])),
        skill_id=skill_id,
        skill_version=str(payload.get("skill_version", "1.0.0")),
        definition_hash=str(payload.get("definition_hash", "sha256:pending")),
        capability_allowlist=allowlist,
        depth_rules=dict(payload.get("depth_rules") or {}),
        status="DRAFT",
        version=1,
        created_by=created_by,
    )
    await repository.create_policy_draft(draft)
    await repository.append_event(workspace_id, analysis_kind, "draft_created", created_by)
    return draft


async def create_skill_change_draft(
    *,
    repository: SkillGovernanceRepository,
    workspace_id: str,
    created_by: str,
    change: dict[str, Any],
    analysis_kind: str = "TASK_OUTCOME",
) -> OutcomeAnalysisPolicyDraft:
    """Đề xuất đổi capability của Outcome skill. `add_capability` ngoài boundary
    -> InvalidCapabilityBoundary NGAY, không tạo draft."""
    add = change.get("add_capability")
    base = list(OUTCOME_ANALYST_CAPABILITY_REFS)
    if add:
        base = [*base, str(add)]
    validate_capability_allowlist(base)
    return await create_policy_draft(
        repository=repository,
        workspace_id=workspace_id,
        created_by=created_by,
        payload={
            "policy": "AUTO_ALL_TASKS",
            "analyst_employee_id": change["analyst_employee_id"],
            "analyst_assignment_id": change["analyst_assignment_id"],
            "capability_allowlist": base,
        },
        analysis_kind=analysis_kind,
    )


async def publish_outcome_analysis_policy(
    *,
    repository: SkillGovernanceRepository,
    validators: SkillGovernanceValidators,
    workspace_id: str,
    draft_id: UUID | str,
    expected_version: int,
    actor_id: str,
    analysis_kind: str = "TASK_OUTCOME",
) -> OutcomeAnalysisPolicyVersion:
    if not await validators.is_founder(workspace_id, actor_id):
        raise FounderApprovalRequired("only a founder may publish an analysis policy")

    draft = await repository.get_policy_draft(workspace_id, draft_id)
    if draft is None:
        raise ValueError("policy draft not found in workspace")
    if draft.version != expected_version:
        raise StalePolicyDraft(
            f"stale draft version: expected {expected_version}, got {draft.version}"
        )
    if draft.status != "DRAFT":
        raise ValueError(f"draft is {draft.status}, not DRAFT")

    # Re-validate boundary + upstream facts trước khi publish.
    validate_capability_allowlist(draft.capability_allowlist)
    if not await validators.employee_is_active(workspace_id, draft.analyst_employee_id):
        raise PolicyValidationError("analyst employee is not ACTIVE")
    if not await validators.assignment_is_effective(workspace_id, draft.analyst_assignment_id):
        raise PolicyValidationError("analyst assignment is not effective")
    if not await validators.skill_version_is_published(draft.skill_id, draft.skill_version):
        raise PolicyValidationError("pinned skill version is not PUBLISHED")

    version_no = await repository.next_version_no(workspace_id, analysis_kind)
    version = OutcomeAnalysisPolicyVersion(
        policy_version_id=uuid4(),
        workspace_id=workspace_id,
        analysis_kind=analysis_kind,
        version_no=version_no,
        policy=draft.policy,
        analyst_employee_id=draft.analyst_employee_id,
        analyst_assignment_id=draft.analyst_assignment_id,
        skill_id=draft.skill_id,
        skill_version=draft.skill_version,
        definition_hash=draft.definition_hash,
        capability_allowlist=draft.capability_allowlist,
        effective_at=datetime.now(UTC),
        created_by=draft.created_by,
        approved_by=actor_id,
    )
    await repository.insert_policy_version(version)
    await repository.mark_draft_published(draft.draft_id)
    await repository.append_event(workspace_id, analysis_kind, "published", actor_id)
    return version


async def rollback_outcome_analysis_policy(
    *,
    repository: SkillGovernanceRepository,
    validators: SkillGovernanceValidators,
    workspace_id: str,
    target_version_id: UUID | str,
    actor_id: str,
    analysis_kind: str = "TASK_OUTCOME",
) -> OutcomeAnalysisPolicyVersion:
    if not await validators.is_founder(workspace_id, actor_id):
        raise FounderApprovalRequired("only a founder may roll back an analysis policy")

    target = await repository.get_policy_version(workspace_id, target_version_id)
    if target is None:
        raise ValueError("rollback target version not found")

    version_no = await repository.next_version_no(workspace_id, analysis_kind)
    rolled = OutcomeAnalysisPolicyVersion(
        policy_version_id=uuid4(),
        workspace_id=workspace_id,
        analysis_kind=analysis_kind,
        version_no=version_no,
        policy=target.policy,
        analyst_employee_id=target.analyst_employee_id,
        analyst_assignment_id=target.analyst_assignment_id,
        skill_id=target.skill_id,
        skill_version=target.skill_version,
        definition_hash=target.definition_hash,
        capability_allowlist=target.capability_allowlist,
        effective_at=datetime.now(UTC),
        created_by=actor_id,
        approved_by=actor_id,
        rollback_target_version_id=target.policy_version_id,
    )
    await repository.insert_policy_version(rolled)
    await repository.append_event(workspace_id, analysis_kind, "rolled_back", actor_id)
    return rolled
