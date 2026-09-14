from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

from agent.contracts.spec import AgentSpec
from agent.runs.models import RunRecord
from agent.skills.contracts import PinnedSkillRef, SkillSpec
from agent.skills.improvement_repository import (
    SkillIdentity,
    SkillImprovementRepository,
    SkillUsageObservation,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class SkillUsageObserverProtocol(Protocol):
    async def record_resolved_pins(
        self,
        run_record: RunRecord,
        root_spec: AgentSpec,
        resolved_skills: list[SkillSpec],
        pinned_refs: list[PinnedSkillRef] | None = None,
    ) -> list[SkillUsageObservation]: ...


class SkillUsageObserver:
    """Records durable usage observations for resolved pinned skills."""

    def __init__(self, repository: SkillImprovementRepository | None = None) -> None:
        self._repository = repository

    async def record_resolved_pins(
        self,
        run_record: RunRecord,
        root_spec: AgentSpec,
        resolved_skills: list[SkillSpec],
        pinned_refs: list[PinnedSkillRef] | None = None,
    ) -> list[SkillUsageObservation]:
        if not resolved_skills:
            return []

        observations: list[SkillUsageObservation] = []
        root_spec_id = getattr(root_spec, "id", "") or "root_agent"
        root_hash = getattr(root_spec, "definition_hash", "") or getattr(root_spec, "version", "") or "root_hash"

        mode = os.getenv("COSA_SKILL_IMPROVEMENT_MODE", "OFF").upper()

        pinned_map = {}
        if pinned_refs:
            for pref in pinned_refs:
                pinned_map[(pref.skill_id, pref.version)] = pref.definition_hash

        for skill in resolved_skills:
            skill_version = skill.version or "1.0.0"
            def_hash = (
                skill.definition_hash
                or pinned_map.get((skill.id, skill_version))
                or (skill.compute_hash() if hasattr(skill, "compute_hash") else "sha256:unknown")
            )
            obs = SkillUsageObservation(
                workspace_id=run_record.workspace_id,
                run_id=run_record.run_id,
                skill_id=skill.id,
                skill_version=skill_version,
                definition_hash=def_hash,
                root_spec_id=root_spec_id,
                root_definition_hash=root_hash,
            )
            observations.append(obs)
            if self._repository is not None:
                try:
                    await self._repository.record_resolved_skill_use(obs)
                except Exception as exc:
                    logger.error(
                        "Failed to persist skill usage observation for run %s skill %s: %s",
                        run_record.run_id,
                        skill.id,
                        exc,
                    )
                    # In CANDIDATE mode, failure must not be swallowed
                    if mode == "CANDIDATE":
                        raise RuntimeError(
                            f"Skill usage observation persistence failed under CANDIDATE mode: {exc}"
                        ) from exc

        return observations


class InMemorySkillUsageObserver(SkillUsageObserver):
    """In-memory usage observer for unit and integration testing."""

    def __init__(self, repository: SkillImprovementRepository | None = None) -> None:
        super().__init__(repository)
        self._observations: list[SkillUsageObservation] = []

    async def record_resolved_pins(
        self,
        run_record: RunRecord,
        root_spec: AgentSpec,
        resolved_skills: list[SkillSpec],
        pinned_refs: list[PinnedSkillRef] | None = None,
    ) -> list[SkillUsageObservation]:
        res = await super().record_resolved_pins(run_record, root_spec, resolved_skills, pinned_refs)
        self._observations.extend(res)
        return res

    async def run_ids(self) -> list[str]:
        return list(dict.fromkeys(o.run_id for o in self._observations))

    async def identities(self, run_id: str) -> list[SkillIdentity]:
        return [
            (o.skill_id, o.skill_version, o.definition_hash)
            for o in self._observations
            if o.run_id == run_id
        ]

    async def all(self) -> list[SkillUsageObservation]:
        return list(self._observations)
