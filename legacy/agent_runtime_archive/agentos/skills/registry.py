# agentos/skills/registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agentos.skills.loader import SkillManifestError, load_skill_manifest
from agentos.skills.manifest_schema import SkillLifecycleStatus, SkillManifest


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
    discover() scans manifest.yaml, validates with SkillManifest schema,
    and fails loudly if a manifest is invalid or missing required fields.
    """

    def __init__(self) -> None:
        self._records: dict[str, SkillRecord] = {}

    def discover(self, root: Path, *, fail_loudly: bool = True) -> list[str]:
        """Scan root for all manifest.yaml files, validating each against SkillManifest."""
        discovered: list[str] = []
        for manifest_path in sorted(root.glob("**/manifest.yaml")):
            skill_dir = manifest_path.parent
            try:
                manifest = load_skill_manifest(skill_dir)
            except Exception as exc:
                if fail_loudly:
                    if isinstance(exc, SkillManifestError):
                        raise
                    raise SkillManifestError(skill_dir, str(exc)) from exc
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

    def list(self, *, status: Optional[SkillLifecycleStatus] = None) -> list[SkillRecord]:
        records = list(self._records.values())
        if status is not None:
            records = [r for r in records if r.status == status]
        return records

    def set_status(self, skill_id: str, status: SkillLifecycleStatus) -> None:
        self.get(skill_id).status = status

    def has(self, skill_id: str) -> bool:
        return skill_id in self._records
