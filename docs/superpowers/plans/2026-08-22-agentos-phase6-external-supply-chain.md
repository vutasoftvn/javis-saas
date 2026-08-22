# AgentOS Phase 6 — External Skill Supply Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the pieces the blueprint's external supply-chain pipeline (§27: DISCOVER→FETCH→PIN VERSION→NORMALIZE→STATIC SCAN→SEMANTIC REVIEW→PERMISSION ANALYSIS→EVAL→APPROVAL→STORE IMMUTABLE ARTIFACT→INSTALL→SANDBOX→STAGE→PROMOTE→OBSERVE) requires that Phase 4/5's internal-only `SkillRegistry` doesn't have: a discovery-source abstraction, commit-pinning enforcement (§28: never import from `ref: main`), a deterministic static/permission scanner, a validated lifecycle state machine, an immutable artifact store, and a pipeline orchestrator gated by a human `approved_by`. The payoff, proven in the final task: Phase 4/5's `SkillRouter` needs **zero changes** to correctly ignore any external skill that hasn't cleared the pipeline — it already only looks at `ACTIVE` skills. Per Phase 6 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4.

**Architecture:** New subpackage `backend/agentos/skills/supply_chain/`. `CatalogSource`/`StaticCatalogSource` model the DISCOVER stage as an in-memory list of `ExternalSkillCandidate` entries — standing in for a real `awesome-agent-skills`-style catalog fetcher, deliberately not built here (blueprint §22: catalog integration is a discovery source, not something to fetch live over the network inside a test suite). `require_pinned_commit()` enforces §28 deterministically (no LLM, no heuristics — just "is there a real commit sha or not"). `scan_manifest()` is a rule-based static/permission analyzer (again no LLM call — reproducible, auditable) collapsing the blueprint's STATIC SCAN + PERMISSION ANALYSIS stages into one deterministic check. `validate_transition()` is a pure state-machine guard over the `SkillLifecycleStatus` enum already defined in Phase 4, reusing the exact pattern `AgentRun.transition()` established in Phase 0 (`_ALLOWED_TRANSITIONS` dict + a typed exception). `ImmutableArtifactStore` copies a skill's files into `registry/skills/<id>/<commit>/` and refuses to overwrite an existing commit directory — the STORE IMMUTABLE ARTIFACT stage, collapsing INSTALL/SANDBOX into the same step since no real sandbox execution exists yet (flagged explicitly as later hardening). `SupplyChainPipeline` orchestrates all of the above into four calls — `import_candidate`, `scan`, `stage`, `promote_to_active` — each validating its own lifecycle transition and refusing to skip stages. `promote_to_active` requires a non-empty `approved_by` string, a minimal deterministic stand-in for the blueprint's full Approval object (§49) — no new governance subsystem is built here. No file under `agentos/skills/manifest.py`, `registry.py`, `router.py`, `loader.py`, or `instruction_loader.py` (Phase 4/5) is modified.

**Tech Stack:** Python 3.11, pydantic 2.13, PyYAML 6.0, pytest — same as Phase 4/5, no new dependencies.

## Global Constraints

- New code lives under `backend/agentos/skills/supply_chain/` and `backend/tests/agentos/skills/supply_chain/`, plus one new test file `backend/tests/agentos/skills/test_supply_chain_router_integration.py` (Task 7) and one `.gitignore` addition. Do not modify any file under `backend/agentos/skills/` outside the new `supply_chain/` subpackage — Phase 4/5's manifest/loader/registry/router/instruction_loader stay exactly as they are; this phase proves they don't need to change.
- **Prerequisite:** this plan assumes Phase 4 (Skill Layer) and Phase 5 (Marketing Skill Pack) have already landed.
- `registry/skills/` (repo root — the `ImmutableArtifactStore`'s default production root, per the blueprint's top-level layout §2: `registry/` holds "Skill Registry state store, supply-chain artifacts (immutable)") is generated at runtime, not source content — Task 7 adds it to `.gitignore`. Tests use `tmp_path` for the artifact store root, never the real `registry/` directory, so no test run ever writes into the repo tree.
- `SupplyChainPipeline` is the only way external skills reach the registry in this plan — it always starts a candidate at `SkillLifecycleStatus.DISCOVERED` and walks it forward one validated transition at a time. Internal skillpacks (Phase 4/5, via `SkillRegistry.discover()`/`register()` defaulting to `ACTIVE`) are untouched and remain a separate, simpler path — do not unify the two paths in this plan.
- `scan_manifest()` and `require_pinned_commit()` are deliberately rule-based, not LLM-based — reproducibility and auditability over sophistication. Do not add a model call to either in this plan.
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/<file> -v` (and `tests/agentos/skills/test_supply_chain_router_integration.py` for Task 7).
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.3 (Skill Ecosystem), §27 (Skill Supply Chain), §28 (no dynamic git ref), §29 (Trust Tiers), §49 (Approval Model), §4 (Phase 6 scope).

---

## File Structure

```text
backend/agentos/skills/supply_chain/
├── __init__.py
├── catalog.py             # ExternalSkillCandidate, CatalogSource, StaticCatalogSource
├── pinning.py                # require_pinned_commit, UnpinnedSkillSourceError
├── scan.py                     # ScanResult, scan_manifest
├── lifecycle.py                   # validate_transition, InvalidSkillLifecycleTransition
├── artifact_store.py                 # ImmutableArtifactStore, ArtifactAlreadyExistsError
└── pipeline.py                          # SupplyChainPipeline, ApprovalRequiredError

backend/tests/agentos/skills/supply_chain/
├── __init__.py
├── test_catalog.py
├── test_pinning.py
├── test_scan.py
├── test_lifecycle.py
├── test_artifact_store.py
└── test_pipeline.py

backend/tests/agentos/skills/test_supply_chain_router_integration.py   # NEW (Task 7)
.gitignore   # MODIFIED (Task 7)
```

---

### Task 1: `ExternalSkillCandidate` + `CatalogSource` + `StaticCatalogSource`

**Files:**
- Create: `backend/agentos/skills/supply_chain/__init__.py`
- Create: `backend/agentos/skills/supply_chain/catalog.py`
- Create: `backend/tests/agentos/skills/supply_chain/__init__.py`
- Test: `backend/tests/agentos/skills/supply_chain/test_catalog.py`

**Interfaces:**
- Produces: `ExternalSkillCandidate(id: str, name: str, description: str, repository: str, path: str, commit: str | None = None, license: str | None = None)`; `CatalogSource` (runtime-checkable `Protocol` with `.list_candidates() -> list[ExternalSkillCandidate]`); `StaticCatalogSource(candidates: list[ExternalSkillCandidate])` implementing it.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/supply_chain/test_catalog.py
from agentos.skills.supply_chain.catalog import CatalogSource, ExternalSkillCandidate, StaticCatalogSource


def test_static_catalog_source_satisfies_protocol():
    assert isinstance(StaticCatalogSource([]), CatalogSource)


def test_static_catalog_source_lists_candidates():
    candidate = ExternalSkillCandidate(
        id="community.faq-writer",
        name="FAQ Writer",
        description="Writes FAQ sections",
        repository="https://github.com/example/skills",
        path="skills/faq-writer",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    source = StaticCatalogSource([candidate])

    candidates = source.list_candidates()

    assert candidates == [candidate]


def test_static_catalog_source_returns_a_copy_not_the_internal_list():
    source = StaticCatalogSource([])
    result = source.list_candidates()
    result.append(
        ExternalSkillCandidate(id="x", name="x", description="x", repository="x", path="x")
    )

    assert source.list_candidates() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_catalog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.supply_chain'`

- [ ] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/skills/supply_chain/__init__.py
```

```python
# backend/tests/agentos/skills/supply_chain/__init__.py
```

```python
# backend/agentos/skills/supply_chain/catalog.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class ExternalSkillCandidate(BaseModel):
    id: str
    name: str
    description: str
    repository: str
    path: str
    commit: str | None = None
    license: str | None = None


@runtime_checkable
class CatalogSource(Protocol):
    def list_candidates(self) -> list[ExternalSkillCandidate]:
        ...


class StaticCatalogSource:
    """MVP discovery source: an in-memory list standing in for a parsed
    external catalog (e.g. awesome-agent-skills, blueprint §22). A real
    fetcher that parses a live GitHub-hosted catalog is later hardening —
    out of scope here; DISCOVER only needs a source of candidates, not a
    specific transport.
    """

    def __init__(self, candidates: list[ExternalSkillCandidate]) -> None:
        self._candidates = list(candidates)

    def list_candidates(self) -> list[ExternalSkillCandidate]:
        return list(self._candidates)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_catalog.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/supply_chain/__init__.py backend/agentos/skills/supply_chain/catalog.py backend/tests/agentos/skills/supply_chain/__init__.py backend/tests/agentos/skills/supply_chain/test_catalog.py
git commit -m "feat(agentos): add ExternalSkillCandidate and StaticCatalogSource"
```

---

### Task 2: `require_pinned_commit` (blueprint §28)

**Files:**
- Create: `backend/agentos/skills/supply_chain/pinning.py`
- Test: `backend/tests/agentos/skills/supply_chain/test_pinning.py`

**Interfaces:**
- Produces: `UnpinnedSkillSourceError(skill_identifier: str)`; `require_pinned_commit(skill_identifier: str, commit: str | None) -> str` (returns the normalized commit sha, raises if missing/blank/a known moving-ref name like `main`/`master`/`head`/`latest`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/supply_chain/test_pinning.py
import pytest

from agentos.skills.supply_chain.pinning import UnpinnedSkillSourceError, require_pinned_commit


def test_require_pinned_commit_accepts_a_real_sha():
    commit = require_pinned_commit("community.faq-writer", "4bc9a82c1234567890abcdef1234567890abcdef")
    assert commit == "4bc9a82c1234567890abcdef1234567890abcdef"


def test_require_pinned_commit_rejects_missing_commit():
    with pytest.raises(UnpinnedSkillSourceError):
        require_pinned_commit("community.faq-writer", None)


def test_require_pinned_commit_rejects_branch_name():
    with pytest.raises(UnpinnedSkillSourceError):
        require_pinned_commit("community.faq-writer", "main")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_pinning.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.supply_chain.pinning'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/supply_chain/pinning.py
from __future__ import annotations

_UNPINNED_REFS = {"main", "master", "head", "latest", ""}


class UnpinnedSkillSourceError(Exception):
    def __init__(self, skill_identifier: str) -> None:
        super().__init__(
            f"{skill_identifier!r} has no pinned commit — refusing to proceed "
            "from a moving ref (blueprint §28)"
        )
        self.skill_identifier = skill_identifier


def require_pinned_commit(skill_identifier: str, commit: str | None) -> str:
    """Enforce blueprint §28: never import from a dynamic git ref like
    `main`. Returns the validated commit sha for convenience.
    """
    normalized = (commit or "").strip().lower()
    if not normalized or normalized in _UNPINNED_REFS:
        raise UnpinnedSkillSourceError(skill_identifier)
    return normalized
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_pinning.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/supply_chain/pinning.py backend/tests/agentos/skills/supply_chain/test_pinning.py
git commit -m "feat(agentos): add require_pinned_commit (blueprint §28 guard)"
```

---

### Task 3: `scan_manifest` (static scan + permission analysis)

**Files:**
- Create: `backend/agentos/skills/supply_chain/scan.py`
- Test: `backend/tests/agentos/skills/supply_chain/test_scan.py`

**Interfaces:**
- Consumes: `SkillManifest`, `TrustTier` from `agentos.skills.manifest` (Phase 4).
- Produces: `ScanResult(passed: bool, findings: list[str])`; `scan_manifest(manifest: SkillManifest) -> ScanResult`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/supply_chain/test_scan.py
from agentos.skills.manifest import (
    SkillCapability,
    SkillManifest,
    SkillMetadata,
    SkillPermissions,
    SkillPublisher,
    SkillQuality,
    SkillRisk,
    SkillRuntime,
    SkillSource,
    SkillTrust,
    TrustTier,
)
from agentos.skills.supply_chain.scan import scan_manifest


def _make_manifest(
    *,
    business_write: bool = False,
    network: str = "none",
    risk_level: str = "low",
    tier: TrustTier = TrustTier.T0,
) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id="x", name="x", version="1.0.0", description="d"),
        publisher=SkillPublisher(name="community", type="community"),
        source=SkillSource(type="git", path="skills/x"),
        capability=SkillCapability(domain="core", category="general", intents=["x"]),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network=network, business_write=business_write),
        risk=SkillRisk(level=risk_level),
        trust=SkillTrust(tier=tier, security_scan="pending"),
        quality=SkillQuality(eval_score=0.5, success_rate=0.5),
    )


def test_scan_passes_low_risk_manifest():
    result = scan_manifest(_make_manifest())
    assert result.passed is True
    assert result.findings == []


def test_scan_flags_business_write_from_low_trust_tier():
    result = scan_manifest(_make_manifest(business_write=True, tier=TrustTier.T3))
    assert result.passed is False
    assert any("business_write" in f for f in result.findings)


def test_scan_flags_network_write_combined_with_business_write():
    result = scan_manifest(_make_manifest(business_write=True, network="write", tier=TrustTier.T0))
    assert result.passed is False


def test_scan_flags_high_risk_from_low_trust_publisher():
    result = scan_manifest(_make_manifest(risk_level="high", tier=TrustTier.T4))
    assert result.passed is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_scan.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.supply_chain.scan'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/supply_chain/scan.py
from __future__ import annotations

from pydantic import BaseModel, Field

from agentos.skills.manifest import SkillManifest, TrustTier

_HIGH_RISK_TRUST_TIERS = {TrustTier.T3, TrustTier.T4}


class ScanResult(BaseModel):
    passed: bool
    findings: list[str] = Field(default_factory=list)


def scan_manifest(manifest: SkillManifest) -> ScanResult:
    """Deterministic static scan + permission analysis (blueprint §27
    STATIC SCAN / PERMISSION ANALYSIS stages). Rule-based by design — no
    LLM call, so results are reproducible and auditable. A real static
    analyzer of skill *code* (not just declared manifest permissions) is
    later hardening.
    """
    findings: list[str] = []

    if manifest.permissions.business_write and manifest.trust.tier in _HIGH_RISK_TRUST_TIERS:
        findings.append("business_write permission requested by a low-trust-tier skill")

    if manifest.permissions.network == "write" and manifest.permissions.business_write:
        findings.append("combines network write and business_write — high blast radius")

    if manifest.risk.level == "high" and manifest.trust.tier in _HIGH_RISK_TRUST_TIERS:
        findings.append("declared high risk from a low-trust-tier publisher")

    return ScanResult(passed=len(findings) == 0, findings=findings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_scan.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/supply_chain/scan.py backend/tests/agentos/skills/supply_chain/test_scan.py
git commit -m "feat(agentos): add scan_manifest static/permission scan"
```

---

### Task 4: `validate_transition` (lifecycle state machine)

**Files:**
- Create: `backend/agentos/skills/supply_chain/lifecycle.py`
- Test: `backend/tests/agentos/skills/supply_chain/test_lifecycle.py`

**Interfaces:**
- Consumes: `SkillLifecycleStatus` from `agentos.skills.manifest` (Phase 4).
- Produces: `InvalidSkillLifecycleTransition(current: SkillLifecycleStatus, target: SkillLifecycleStatus)`; `validate_transition(current: SkillLifecycleStatus, target: SkillLifecycleStatus) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/supply_chain/test_lifecycle.py
import pytest

from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.supply_chain.lifecycle import InvalidSkillLifecycleTransition, validate_transition


def test_discovered_to_imported_is_valid():
    validate_transition(SkillLifecycleStatus.DISCOVERED, SkillLifecycleStatus.IMPORTED)


def test_scanned_to_verified_is_valid():
    validate_transition(SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.VERIFIED)


def test_scanned_to_quarantined_is_valid():
    validate_transition(SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.QUARANTINED)


def test_discovered_to_active_is_invalid_skips_stages():
    with pytest.raises(InvalidSkillLifecycleTransition):
        validate_transition(SkillLifecycleStatus.DISCOVERED, SkillLifecycleStatus.ACTIVE)


def test_active_to_quarantined_is_valid_can_be_pulled_after_activation():
    validate_transition(SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.QUARANTINED)


def test_rejected_is_terminal():
    with pytest.raises(InvalidSkillLifecycleTransition):
        validate_transition(SkillLifecycleStatus.REJECTED, SkillLifecycleStatus.IMPORTED)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_lifecycle.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.supply_chain.lifecycle'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/supply_chain/lifecycle.py
from __future__ import annotations

from agentos.skills.manifest import SkillLifecycleStatus

_ALLOWED_TRANSITIONS: dict[SkillLifecycleStatus, frozenset[SkillLifecycleStatus]] = {
    SkillLifecycleStatus.DISCOVERED: frozenset({SkillLifecycleStatus.IMPORTED, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.IMPORTED: frozenset({SkillLifecycleStatus.SCANNED, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.SCANNED: frozenset(
        {SkillLifecycleStatus.VERIFIED, SkillLifecycleStatus.QUARANTINED, SkillLifecycleStatus.REJECTED}
    ),
    SkillLifecycleStatus.VERIFIED: frozenset({SkillLifecycleStatus.STAGED, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.STAGED: frozenset({SkillLifecycleStatus.ACTIVE, SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.ACTIVE: frozenset({SkillLifecycleStatus.DEPRECATED, SkillLifecycleStatus.QUARANTINED}),
    SkillLifecycleStatus.DEPRECATED: frozenset(),
    SkillLifecycleStatus.QUARANTINED: frozenset({SkillLifecycleStatus.REJECTED}),
    SkillLifecycleStatus.REJECTED: frozenset(),
}


class InvalidSkillLifecycleTransition(Exception):
    def __init__(self, current: SkillLifecycleStatus, target: SkillLifecycleStatus) -> None:
        super().__init__(f"Cannot transition skill lifecycle from {current.value} to {target.value}")
        self.current = current
        self.target = target


def validate_transition(current: SkillLifecycleStatus, target: SkillLifecycleStatus) -> None:
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidSkillLifecycleTransition(current, target)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_lifecycle.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/supply_chain/lifecycle.py backend/tests/agentos/skills/supply_chain/test_lifecycle.py
git commit -m "feat(agentos): add skill lifecycle transition validator"
```

---

### Task 5: `ImmutableArtifactStore`

**Files:**
- Create: `backend/agentos/skills/supply_chain/artifact_store.py`
- Test: `backend/tests/agentos/skills/supply_chain/test_artifact_store.py`

**Interfaces:**
- Produces: `ArtifactAlreadyExistsError(skill_id: str, commit: str, artifact_dir: Path)`; `ImmutableArtifactStore(root: Path)` with `.artifact_dir(skill_id: str, commit: str) -> Path` and `.store(skill_id: str, commit: str, source_dir: Path) -> Path` (copies `source_dir` into `root/skill_id/commit/`, raises if that directory already exists).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/supply_chain/test_artifact_store.py
from pathlib import Path

import pytest

from agentos.skills.supply_chain.artifact_store import ArtifactAlreadyExistsError, ImmutableArtifactStore


def _make_source_skill(root: Path) -> Path:
    source_dir = root / "source"
    source_dir.mkdir()
    (source_dir / "manifest.yaml").write_text("id: x", encoding="utf-8")
    (source_dir / "SKILL.md").write_text("do it", encoding="utf-8")
    return source_dir


def test_store_copies_source_into_artifact_dir(tmp_path: Path):
    source_dir = _make_source_skill(tmp_path)
    store = ImmutableArtifactStore(tmp_path / "registry" / "skills")

    stored_dir = store.store("community.faq-writer", "4bc9a82c", source_dir)

    assert stored_dir == tmp_path / "registry" / "skills" / "community.faq-writer" / "4bc9a82c"
    assert (stored_dir / "manifest.yaml").read_text(encoding="utf-8") == "id: x"


def test_store_refuses_to_overwrite_existing_commit(tmp_path: Path):
    source_dir = _make_source_skill(tmp_path)
    store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    store.store("community.faq-writer", "4bc9a82c", source_dir)

    with pytest.raises(ArtifactAlreadyExistsError):
        store.store("community.faq-writer", "4bc9a82c", source_dir)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_artifact_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.supply_chain.artifact_store'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/supply_chain/artifact_store.py
from __future__ import annotations

import shutil
from pathlib import Path


class ArtifactAlreadyExistsError(Exception):
    def __init__(self, skill_id: str, commit: str, artifact_dir: Path) -> None:
        super().__init__(
            f"Immutable artifact for {skill_id}@{commit} already exists at {artifact_dir} — "
            "refusing to overwrite (blueprint §27 STORE IMMUTABLE ARTIFACT)"
        )
        self.skill_id = skill_id
        self.commit = commit
        self.artifact_dir = artifact_dir


class ImmutableArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def artifact_dir(self, skill_id: str, commit: str) -> Path:
        return self._root / skill_id / commit

    def store(self, skill_id: str, commit: str, source_dir: Path) -> Path:
        target_dir = self.artifact_dir(skill_id, commit)
        if target_dir.exists():
            raise ArtifactAlreadyExistsError(skill_id, commit, target_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)
        return target_dir
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_artifact_store.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/supply_chain/artifact_store.py backend/tests/agentos/skills/supply_chain/test_artifact_store.py
git commit -m "feat(agentos): add ImmutableArtifactStore"
```

---

### Task 6: `SupplyChainPipeline`

**Files:**
- Create: `backend/agentos/skills/supply_chain/pipeline.py`
- Test: `backend/tests/agentos/skills/supply_chain/test_pipeline.py`

**Interfaces:**
- Consumes: `load_skill_manifest` from `agentos.skills.loader` (Phase 4); `SkillLifecycleStatus` from `agentos.skills.manifest` (Phase 4); `SkillRegistry` from `agentos.skills.registry` (Phase 4); `ImmutableArtifactStore` (Task 5); `ExternalSkillCandidate` (Task 1); `validate_transition`/`InvalidSkillLifecycleTransition` (Task 4); `require_pinned_commit`/`UnpinnedSkillSourceError` (Task 2); `ScanResult`/`scan_manifest` (Task 3).
- Produces: `ApprovalRequiredError(skill_id: str)`; `SupplyChainPipeline(registry: SkillRegistry, artifact_store: ImmutableArtifactStore)` with `.import_candidate(candidate: ExternalSkillCandidate, skill_dir: Path) -> str` (returns skill id, status `IMPORTED`), `.scan(skill_id: str) -> ScanResult` (status becomes `VERIFIED` or `QUARANTINED`), `.stage(skill_id: str) -> Path` (status becomes `STAGED`, artifact stored), `.promote_to_active(skill_id: str, *, approved_by: str) -> None` (status becomes `ACTIVE`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/supply_chain/test_pipeline.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.lifecycle import InvalidSkillLifecycleTransition
from agentos.skills.supply_chain.pinning import UnpinnedSkillSourceError
from agentos.skills.supply_chain.pipeline import ApprovalRequiredError, SupplyChainPipeline


def _write_external_skill(
    root: Path,
    skill_id: str,
    *,
    commit: str = "4bc9a82c1234567890abcdef1234567890abcdef",
    business_write: bool = False,
    tier: str = "T0",
) -> Path:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "community", "type": "community"},
        "source": {
            "type": "git",
            "path": f"skills/{skill_id}",
            "repository": "https://github.com/example/skills",
            "commit": commit,
        },
        "capability": {"domain": "core", "category": "general", "intents": [skill_id]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": business_write},
        "risk": {"level": "low"},
        "trust": {"tier": tier, "security_scan": "pending"},
        "quality": {"eval_score": 0.5, "success_rate": 0.5},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(f"# {skill_id}\n\nDo it.\n", encoding="utf-8")
    return skill_dir


def _candidate(skill_id: str, commit: str | None = "4bc9a82c1234567890abcdef1234567890abcdef") -> ExternalSkillCandidate:
    return ExternalSkillCandidate(
        id=skill_id,
        name=skill_id,
        description="d",
        repository="https://github.com/example/skills",
        path=f"skills/{skill_id}",
        commit=commit,
    )


def _make_pipeline(tmp_path: Path) -> tuple[SupplyChainPipeline, SkillRegistry]:
    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    return SupplyChainPipeline(registry, artifact_store), registry


def test_happy_path_imports_scans_stages_and_activates(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, registry = _make_pipeline(tmp_path)

    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)
    assert registry.get(skill_id).status == SkillLifecycleStatus.IMPORTED

    result = pipeline.scan(skill_id)
    assert result.passed is True
    assert registry.get(skill_id).status == SkillLifecycleStatus.VERIFIED

    artifact_dir = pipeline.stage(skill_id)
    assert artifact_dir.exists()
    assert registry.get(skill_id).status == SkillLifecycleStatus.STAGED

    pipeline.promote_to_active(skill_id, approved_by="founder")
    assert registry.get(skill_id).status == SkillLifecycleStatus.ACTIVE


def test_scan_failure_quarantines_instead_of_verifying(tmp_path: Path):
    skill_dir = _write_external_skill(
        tmp_path / "source", "community.risky-writer", business_write=True, tier="T3"
    )
    pipeline, registry = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.risky-writer"), skill_dir)

    result = pipeline.scan(skill_id)

    assert result.passed is False
    assert registry.get(skill_id).status == SkillLifecycleStatus.QUARANTINED


def test_promote_without_approver_raises(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, _ = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)
    pipeline.scan(skill_id)
    pipeline.stage(skill_id)

    with pytest.raises(ApprovalRequiredError):
        pipeline.promote_to_active(skill_id, approved_by="")


def test_cannot_skip_stages_straight_to_active(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, _ = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)

    with pytest.raises(InvalidSkillLifecycleTransition):
        pipeline.promote_to_active(skill_id, approved_by="founder")


def test_import_rejects_unpinned_candidate(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    pipeline, _ = _make_pipeline(tmp_path)

    with pytest.raises(UnpinnedSkillSourceError):
        pipeline.import_candidate(_candidate("community.faq-writer", commit=None), skill_dir)


def test_stage_rejects_manifest_missing_commit(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    # Overwrite the manifest's own source.commit to simulate a manifest that
    # was hand-edited after import to drop its pin.
    manifest_path = skill_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["commit"] = None
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    pipeline, _ = _make_pipeline(tmp_path)
    skill_id = pipeline.import_candidate(_candidate("community.faq-writer"), skill_dir)
    pipeline.scan(skill_id)

    with pytest.raises(UnpinnedSkillSourceError):
        pipeline.stage(skill_id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.supply_chain.pipeline'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/supply_chain/pipeline.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/supply_chain/test_pipeline.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/supply_chain/pipeline.py backend/tests/agentos/skills/supply_chain/test_pipeline.py
git commit -m "feat(agentos): add SupplyChainPipeline orchestrator"
```

---

### Task 7: Prove `SkillRouter` needs zero changes to respect the pipeline, and gitignore the artifact store

**Files:**
- Test: `backend/tests/agentos/skills/test_supply_chain_router_integration.py`
- Modify: `.gitignore`

**Interfaces:** None new — this task only adds tests over Phase 4/5's unmodified `SkillRouter` combined with this phase's `SupplyChainPipeline`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/test_supply_chain_router_integration.py
from pathlib import Path

import yaml

from agentos.skills.manifest import TrustTier
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.pipeline import SupplyChainPipeline


def _write_external_skill(
    root: Path, skill_id: str, *, commit: str = "4bc9a82c1234567890abcdef1234567890abcdef"
) -> Path:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "community", "type": "community"},
        "source": {
            "type": "git",
            "path": f"skills/{skill_id}",
            "repository": "https://github.com/example/skills",
            "commit": commit,
        },
        "capability": {"domain": "core", "category": "general", "intents": ["faq writer", "write faq answers"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "pending"},
        "quality": {"eval_score": 0.6, "success_rate": 0.6},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(f"# {skill_id}\n\nWrite FAQ answers.\n", encoding="utf-8")
    return skill_dir


def test_router_never_selects_a_skill_before_it_is_promoted_to_active(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.faq-writer")
    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    pipeline = SupplyChainPipeline(registry, artifact_store)
    router = SkillRouter(registry)
    candidate = ExternalSkillCandidate(
        id="community.faq-writer",
        name="FAQ Writer",
        description="d",
        repository="https://github.com/example/skills",
        path="skills/community.faq-writer",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    skill_id = pipeline.import_candidate(candidate, skill_dir)

    assert router.select("write faq answers") is None  # IMPORTED

    pipeline.scan(skill_id)
    assert router.select("write faq answers") is None  # VERIFIED

    pipeline.stage(skill_id)
    assert router.select("write faq answers") is None  # STAGED

    pipeline.promote_to_active(skill_id, approved_by="founder")
    selected = router.select("write faq answers")
    assert selected is not None
    assert selected.metadata.id == "community.faq-writer"


def test_router_never_selects_a_quarantined_skill(tmp_path: Path):
    skill_dir = _write_external_skill(tmp_path / "source", "community.risky-writer")
    manifest_path = skill_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["permissions"]["business_write"] = True
    manifest["trust"]["tier"] = "T3"
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")

    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    pipeline = SupplyChainPipeline(registry, artifact_store)
    router = SkillRouter(registry, min_trust=TrustTier.T2)
    candidate = ExternalSkillCandidate(
        id="community.risky-writer",
        name="Risky Writer",
        description="d",
        repository="https://github.com/example/skills",
        path="skills/community.risky-writer",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    skill_id = pipeline.import_candidate(candidate, skill_dir)
    result = pipeline.scan(skill_id)

    assert result.passed is False
    assert router.select("write faq answers") is None
```

- [ ] **Step 2: Run tests to verify they pass immediately**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_supply_chain_router_integration.py -v`
Expected: 2 passed — this is a pure integration proof over already-implemented Tasks 1–6 plus Phase 4/5's `SkillRouter`, so unlike prior tasks there is no separate "watch it fail first" step: if either test fails here, it means Task 6's `SupplyChainPipeline` or Phase 4/5's `SkillRouter` has a real bug, not a missing-module error — stop and investigate rather than proceeding to Step 3.

- [ ] **Step 3: Add the artifact store to `.gitignore`**

Append to the end of `.gitignore`:

```gitignore

# AgentOS external skill supply-chain artifact store — generated at
# runtime by ImmutableArtifactStore, not source content (blueprint §27)
registry/skills/
```

- [ ] **Step 4: Run the full `agentos` skills suite to confirm everything holds together**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/ -v`
Expected: all passing — Phase 4's 22 tests + Phase 5's 8 tests + this phase's `supply_chain/` tests (3 + 3 + 4 + 6 + 2 + 6 = 24) + this task's 2 integration tests = 56 total

- [ ] **Step 5: Commit**

```bash
git add backend/tests/agentos/skills/test_supply_chain_router_integration.py .gitignore
git commit -m "test(agentos): prove SkillRouter respects supply-chain gating unmodified"
```

---

## Verification (end of Phase 6)

1. Run the full skills suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/ -v` — all tests pass (56 total per Task 7 Step 4).
2. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — no regressions in Phase 0/1/3/4/5 tests.
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Confirm no test run left files in the real (non-gitignored-yet-tracked) `registry/` directory: `git status registry/` shows nothing tracked, and `git status --ignored registry/` (if the directory exists locally from manual testing) shows it as ignored.
5. Re-read `backend/agentos/skills/supply_chain/pipeline.py` and confirm each of the four public methods validates its lifecycle transition *before* doing any side-effecting work (registry write, filesystem copy) — the tests in Task 6 prove this for the specific cases exercised, but a manual read is worth it given how much this phase leans on "fail before mutating."

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 7 (Multi-Agent — delegation/parallel/supervisor flows) is next. It should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed. A few things are explicitly deferred out of this phase and not yet scoped anywhere: a real `CatalogSource` that fetches and parses a live external catalog (e.g. `awesome-agent-skills`) instead of `StaticCatalogSource`'s in-memory list; real sandboxed execution during `stage()` instead of a plain file copy; a full Approval object (blueprint §49) with an audit trail instead of `promote_to_active`'s bare `approved_by: str` string; and a `Semantic Review` LLM-assisted stage to sit alongside the deterministic `scan_manifest()`.
