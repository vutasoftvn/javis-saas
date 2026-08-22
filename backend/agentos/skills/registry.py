# backend/agentos/skills/registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentos.skills.loader import SkillManifestError, load_skill_manifest
from agentos.skills.manifest import SkillLifecycleStatus, SkillManifest


class SkillNotFoundError(Exception):
    def __init__(self, skill_id: str) -> None:
        super().__init__(f"Skill not registered: {skill_id}")
        self.skill_id = skill_id


@dataclass
class SkillRecord:
    manifest: SkillManifest
    status: SkillLifecycleStatus
    skill_dir: Path


class SkillRegistry:
    """In-process registry for internal skillpacks (blueprint §3.3/§20).
    discover() only reads manifest.yaml (Level 0 metadata) — it never reads
    SKILL.md eagerly; that's the loader's job (progressive disclosure,
    blueprint §24). External supply chain (DISCOVER->...->PROMOTE) is
    Phase 6 — internal skills default straight to ACTIVE.
    """

    def __init__(self) -> None:
        self._records: dict[str, SkillRecord] = {}

    def discover(self, root: Path) -> list[str]:
        discovered: list[str] = []
        for manifest_path in sorted(root.glob("**/manifest.yaml")):
            skill_dir = manifest_path.parent
            try:
                manifest = load_skill_manifest(skill_dir)
            except SkillManifestError:
                continue
            self._records[manifest.metadata.id] = SkillRecord(
                manifest=manifest, status=SkillLifecycleStatus.ACTIVE, skill_dir=skill_dir
            )
            discovered.append(manifest.metadata.id)
        return discovered

    def register(
        self,
        manifest: SkillManifest,
        skill_dir: Path,
        status: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE,
    ) -> None:
        self._records[manifest.metadata.id] = SkillRecord(manifest=manifest, status=status, skill_dir=skill_dir)

    def get(self, skill_id: str) -> SkillRecord:
        try:
            return self._records[skill_id]
        except KeyError:
            raise SkillNotFoundError(skill_id) from None

    def list(self, *, status: SkillLifecycleStatus | None = None) -> list[SkillRecord]:
        records = list(self._records.values())
        if status is not None:
            records = [r for r in records if r.status == status]
        return records

    def set_status(self, skill_id: str, status: SkillLifecycleStatus) -> None:
        self.get(skill_id).status = status
