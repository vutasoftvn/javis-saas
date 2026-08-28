from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.evals.promotion import PromotionEvidence
from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = [
    "InMemoryPromotionEvidenceRepository",
    "PostgresPromotionEvidenceRepository",
    "PromotionEvidenceRepository",
]


@runtime_checkable
class PromotionEvidenceRepository(Protocol):
    """Protocol cho persistence PromotionEvidence (agent_evals.
    promotion_evidence, migration 014, Wave M4)."""

    async def create(self, evidence: PromotionEvidence) -> PromotionEvidence: ...
    async def get(self, evidence_id: str) -> PromotionEvidence | None: ...
    async def list_by_target(self, target_ref: PinnedSpecIdentity) -> list[PromotionEvidence]: ...


class InMemoryPromotionEvidenceRepository:
    """In-memory implementation — chỉ dùng test/local dev, không dùng
    production (không durable qua restart)."""

    def __init__(self) -> None:
        self._evidence: dict[str, PromotionEvidence] = {}

    async def create(self, evidence: PromotionEvidence) -> PromotionEvidence:
        stored = evidence.model_copy(deep=True)
        self._evidence[stored.evidence_id] = stored
        return stored.model_copy(deep=True)

    async def get(self, evidence_id: str) -> PromotionEvidence | None:
        r = self._evidence.get(evidence_id)
        return r.model_copy(deep=True) if r else None

    async def list_by_target(self, target_ref: PinnedSpecIdentity) -> list[PromotionEvidence]:
        return [
            e.model_copy(deep=True) for e in self._evidence.values() if e.target_ref == target_ref
        ]


class PostgresPromotionEvidenceRepository:
    """PostgreSQL implementation — persist vào agent_evals.promotion_evidence
    (migration 014)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError(
                "PostgresPromotionEvidenceRepository requires a valid db_session_factory."
            )
        self._session_factory = db_session_factory

    async def create(self, evidence: PromotionEvidence) -> PromotionEvidence:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.promotion_evidence (
                        evidence_id, target_kind, target_id, target_version, target_definition_hash,
                        required_eval_run_ids, observed_fingerprints, policy_version, policy_checks_passed,
                        check_details, created_at
                    ) VALUES (
                        :evidence_id, :target_kind, :target_id, :target_version, :target_definition_hash,
                        :required_eval_run_ids, :observed_fingerprints, :policy_version, :policy_checks_passed,
                        :check_details, :created_at
                    )
                    """
                ),
                {
                    "evidence_id": evidence.evidence_id,
                    "target_kind": evidence.target_ref.spec_kind,
                    "target_id": evidence.target_ref.spec_id,
                    "target_version": evidence.target_ref.spec_version,
                    "target_definition_hash": evidence.target_ref.definition_hash,
                    "required_eval_run_ids": json.dumps(evidence.required_eval_run_ids),
                    "observed_fingerprints": json.dumps(evidence.observed_fingerprints),
                    "policy_version": evidence.policy_version,
                    "policy_checks_passed": evidence.policy_checks_passed,
                    "check_details": json.dumps(evidence.check_details),
                    "created_at": evidence.created_at,
                },
            )
            await session.commit()
        return evidence

    @staticmethod
    def _parse_json(val: Any) -> Any:
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            return json.loads(val)
        return val

    @classmethod
    def _row_to_evidence(cls, row: Any) -> PromotionEvidence:
        return PromotionEvidence(
            evidence_id=row["evidence_id"],
            target_ref=PinnedSpecIdentity(
                spec_kind=row["target_kind"],
                spec_id=row["target_id"],
                spec_version=row["target_version"],
                definition_hash=row["target_definition_hash"],
            ),
            required_eval_run_ids=cls._parse_json(row["required_eval_run_ids"]) or [],
            observed_fingerprints=cls._parse_json(row["observed_fingerprints"]) or {},
            policy_version=row["policy_version"],
            policy_checks_passed=row["policy_checks_passed"],
            check_details=cls._parse_json(row["check_details"]) or {},
            created_at=row["created_at"],
        )

    async def get(self, evidence_id: str) -> PromotionEvidence | None:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT evidence_id, target_kind, target_id, target_version, target_definition_hash,
                           required_eval_run_ids, observed_fingerprints, policy_version, policy_checks_passed,
                           check_details, created_at
                    FROM agent_evals.promotion_evidence
                    WHERE evidence_id = :evidence_id
                    """
                ),
                {"evidence_id": evidence_id},
            )
            row = res.mappings().first()
            return self._row_to_evidence(row) if row else None

    async def list_by_target(self, target_ref: PinnedSpecIdentity) -> list[PromotionEvidence]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT evidence_id, target_kind, target_id, target_version, target_definition_hash,
                           required_eval_run_ids, observed_fingerprints, policy_version, policy_checks_passed,
                           check_details, created_at
                    FROM agent_evals.promotion_evidence
                    WHERE target_kind = :target_kind AND target_id = :target_id
                          AND target_version = :target_version AND target_definition_hash = :target_definition_hash
                    ORDER BY created_at ASC
                    """
                ),
                {
                    "target_kind": target_ref.spec_kind,
                    "target_id": target_ref.spec_id,
                    "target_version": target_ref.spec_version,
                    "target_definition_hash": target_ref.definition_hash,
                },
            )
            return [self._row_to_evidence(r) for r in res.mappings().all()]
