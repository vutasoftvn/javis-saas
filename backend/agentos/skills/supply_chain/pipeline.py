from __future__ import annotations

from pathlib import Path

from agentos.skills.loader import load_skill_manifest
from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.lifecycle import validate_transition
from agentos.skills.supply_chain.pinning import require_pinned_commit
from agentos.skills.supply_chain.scan import ScanResult, scan_manifest


class ApprovalRequiredError(Exception):
    def __init__(self, skill_id: str) -> None:
        super().__init__(f"Cannot activate skill {skill_id!r} without an approver (blueprint §49 Approval Model)")
        self.skill_id = skill_id


class SupplyChainPipeline:
    """Orchestrates the blueprint §27 pipeline for EXTERNAL skills only —
    internal skillpacks (Phase 4/5) bypass this entirely via
    SkillRegistry.discover()/register() defaulting straight to ACTIVE.
    Coarser than the blueprint's named stages: PIN VERSION / NORMALIZE
    collapse into import_candidate(); STATIC SCAN / SEMANTIC REVIEW /
    PERMISSION ANALYSIS collapse into scan(); STORE IMMUTABLE ARTIFACT /
    INSTALL / SANDBOX collapse into stage() (no real sandbox execution yet
    — that's later hardening); APPROVAL / PROMOTE are promote_to_active().
    OBSERVE (post-promotion monitoring) is out of scope for this phase.
    """

    def __init__(self, registry: SkillRegistry, artifact_store: ImmutableArtifactStore) -> None:
        self._registry = registry
        self._artifact_store = artifact_store

    def import_candidate(self, candidate: ExternalSkillCandidate, skill_dir: Path) -> str:
        require_pinned_commit(candidate.id, candidate.commit)
        manifest = load_skill_manifest(skill_dir)
        self._registry.register(manifest, skill_dir, status=SkillLifecycleStatus.DISCOVERED)
        validate_transition(SkillLifecycleStatus.DISCOVERED, SkillLifecycleStatus.IMPORTED)
        self._registry.set_status(manifest.metadata.id, SkillLifecycleStatus.IMPORTED)
        return manifest.metadata.id

    def scan(self, skill_id: str) -> ScanResult:
        record = self._registry.get(skill_id)
        validate_transition(record.status, SkillLifecycleStatus.SCANNED)
        self._registry.set_status(skill_id, SkillLifecycleStatus.SCANNED)

        result = scan_manifest(record.manifest)
        next_status = SkillLifecycleStatus.VERIFIED if result.passed else SkillLifecycleStatus.QUARANTINED
        validate_transition(SkillLifecycleStatus.SCANNED, next_status)
        self._registry.set_status(skill_id, next_status)
        return result

    def stage(self, skill_id: str) -> Path:
        record = self._registry.get(skill_id)
        validate_transition(record.status, SkillLifecycleStatus.STAGED)
        commit = require_pinned_commit(skill_id, record.manifest.source.commit)
        artifact_dir = self._artifact_store.store(skill_id, commit, record.skill_dir)
        self._registry.set_status(skill_id, SkillLifecycleStatus.STAGED)
        return artifact_dir

    def promote_to_active(self, skill_id: str, *, approved_by: str) -> None:
        if not approved_by.strip():
            raise ApprovalRequiredError(skill_id)
        record = self._registry.get(skill_id)
        validate_transition(record.status, SkillLifecycleStatus.ACTIVE)
        self._registry.set_status(skill_id, SkillLifecycleStatus.ACTIVE)
