# AgentOS Phase 4 — Skill Layer (Manifest, Registry, Router, Loader, Permissions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the canonical Skill Manifest model, a filesystem manifest/instructions loader, an in-process `SkillRegistry` with lifecycle status, a `SkillRouter` that scores and selects a skill for a goal (with permission-based filtering), a progressive-disclosure `SkillInstructionLoader`, one real internal skillpack proving the whole pipeline against actual files, and — finally — wiring into the existing `ContextBuilder` so `AgentContext` carries selected skill instructions alongside the memory snippets from Phase 3. Per Phase 4 of the roadmap in `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4 (external supply chain / awesome-agent-skills discovery is explicitly Phase 6, out of scope here — this phase is internal skillpacks only).

**Architecture:** New subpackage `backend/agentos/skills/` implementing the blueprint's Canonical Skill Manifest (§3.3, exact YAML shape from the spec) as pydantic models, a loader that parses `manifest.yaml` + reads `SKILL.md` from a skill directory, a `SkillRegistry` that discovers skills under a root directory and tracks each one's `SkillLifecycleStatus` (internal skills default straight to `ACTIVE` — no external supply-chain pipeline exists yet), a `SkillRouter` implementing an MVP subset of the blueprint's scoring formula (`Score = Relevance + Trust + EvalQuality`, dropping Cost/Risk/HistoricalSuccess/BusinessFit until later phases track them) plus a permission gate (skills declaring `business_write: true` are excluded unless the caller explicitly opts in), and a `SkillInstructionLoader` that only reads a skill's `SKILL.md` body when a skill is actually selected (progressive disclosure, blueprint §24 — the registry's `discover()` never reads instruction bodies). One real skillpack is added at `skillpacks/core/weekly-review/` (repo-root, matching the blueprint's top-level layout) to prove discovery works against real files, not just `tmp_path` fixtures. The only change to already-committed code is `ContextBuilder`/`AgentContext` (Phase 0/1, extended again by Phase 3 for memory) — this phase adds an optional `skill_router`/`skill_instruction_loader` pair and a new `skill_instructions: list[str]` field, following the same additive pattern Phase 3 used for `memory_snippets`.

**Tech Stack:** Python 3.11, pydantic 2.13, PyYAML 6.0 (already in `backend/requirements.txt`), pytest + pytest-asyncio — no new dependencies.

## Global Constraints

- New code lives under `backend/agentos/skills/` and `backend/tests/agentos/skills/`, plus one real skillpack at `skillpacks/core/weekly-review/` (repo root, sibling to `backend/`). The one exception is `backend/agentos/core/context.py` and `backend/agentos/core/context_builder.py`, which Task 7 modifies again — do not touch any other file under `backend/agentos/core/`.
- **Prerequisite:** this plan assumes Phase 3 (Memory) has already landed — `ContextBuilder.build()` is `async` and already takes an optional `memory_retriever` parameter, and `AgentContext` already has a `memory_snippets` field. Task 7 adds to that existing shape; it does not re-introduce the sync→async change (already done) and must not drop the `memory_retriever` wiring while editing these files. If Phase 3 has not landed yet when you reach Task 7, stop and land it first — do not reinvent memory wiring here.
- `SkillRegistry.discover()` silently skips a skill directory whose `manifest.yaml` fails to parse (logs nothing beyond returning it out of the discovered list) — this is an explicit MVP simplification; a real supply-chain SCAN/VERIFY step that surfaces and quarantines bad manifests is Phase 6 scope, not this one.
- Manifest field names follow the blueprint's canonical YAML exactly (`apiVersion`, nested `metadata`/`publisher`/`source`/`capability`/`runtime`/`permissions`/`risk`/`trust`/`quality` objects) — pydantic models use `populate_by_name=True` with `Field(alias=...)` only where the YAML key isn't valid Python (`apiVersion`), so tests can construct manifests with either the alias or the snake_case field name.
- `SkillLifecycleStatus` is registry-managed state, not part of the static `manifest.yaml` file — a manifest has no `status` field; the registry assigns it on `discover()`/`register()`.
- Every async test needs `@pytest.mark.asyncio` (`backend/pytest.ini` has `asyncio_mode = strict`); the skill-layer tests themselves (Tasks 1–6) are all synchronous except where noted — only Task 7's `ContextBuilder` tests are async.
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/<file> -v` (and `tests/agentos/test_context_builder.py` for Task 7).
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §3.3 (Skill Ecosystem), §4 (Phase 4 scope).

---

## File Structure

```text
backend/agentos/skills/
├── __init__.py
├── manifest.py             # TrustTier, SkillLifecycleStatus, SkillManifest + sub-models
├── loader.py                 # load_skill_manifest, load_skill_instructions, SkillManifestError
├── registry.py                 # SkillRegistry, SkillRecord, SkillNotFoundError
├── router.py                     # score_skill, SkillRouter
└── instruction_loader.py           # SkillInstructionLoader

backend/tests/agentos/skills/
├── __init__.py
├── test_manifest.py
├── test_loader.py
├── test_registry.py
├── test_router.py
├── test_instruction_loader.py
└── test_skillpacks_integration.py

skillpacks/core/weekly-review/
├── manifest.yaml
└── SKILL.md

backend/agentos/core/context.py            # MODIFIED (Task 7)
backend/agentos/core/context_builder.py     # MODIFIED (Task 7)
backend/tests/agentos/test_context_builder.py   # MODIFIED (Task 7)
```

---

### Task 1: Canonical `SkillManifest` model

**Files:**
- Create: `backend/agentos/skills/__init__.py`
- Create: `backend/agentos/skills/manifest.py`
- Create: `backend/tests/agentos/skills/__init__.py`
- Test: `backend/tests/agentos/skills/test_manifest.py`

**Interfaces:**
- Produces: `TrustTier` (str enum: `T0`, `T1`, `T2`, `T3`, `T4`); `SkillLifecycleStatus` (str enum: `DISCOVERED`, `IMPORTED`, `SCANNED`, `VERIFIED`, `STAGED`, `ACTIVE`, `DEPRECATED`, `QUARANTINED`, `REJECTED`); `SkillMetadata(id, name, version, description)`; `SkillPublisher(name, type)`; `SkillSource(type, path, repository=None, commit=None, license=None)`; `SkillCapability(domain, category, intents: list[str])`; `SkillRuntime(entrypoint="SKILL.md", tools: list[str])`; `SkillPermissions(filesystem="none", network="none", business_write=False)`; `SkillRisk(level="low")`; `SkillTrust(tier=TrustTier.T2, security_scan="pending")`; `SkillQuality(eval_score=0.0, success_rate=0.0)`; `SkillManifest(api_version [alias apiVersion], kind, metadata, publisher, source, capability, runtime, permissions, risk, trust, quality)`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/test_manifest.py
import pytest
from pydantic import ValidationError

from agentos.skills.manifest import SkillManifest, TrustTier


def _minimal_manifest_dict() -> dict:
    return {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": "core.weekly-review", "name": "Weekly Review", "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": "skillpacks/core/weekly-review"},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }


def test_manifest_parses_from_canonical_dict():
    manifest = SkillManifest(**_minimal_manifest_dict())
    assert manifest.api_version == "agentos.ai/v1"
    assert manifest.metadata.id == "core.weekly-review"
    assert manifest.trust.tier == TrustTier.T0


def test_manifest_risk_level_defaults_to_low_when_omitted():
    data = _minimal_manifest_dict()
    data["risk"] = {}
    manifest = SkillManifest(**data)
    assert manifest.risk.level == "low"


def test_manifest_requires_metadata_id():
    data = _minimal_manifest_dict()
    del data["metadata"]["id"]
    with pytest.raises(ValidationError):
        SkillManifest(**data)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_manifest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills'`

- [ ] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/skills/__init__.py
```

```python
# backend/tests/agentos/skills/__init__.py
```

```python
# backend/agentos/skills/manifest.py
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class TrustTier(str, enum.Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"


class SkillLifecycleStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    IMPORTED = "IMPORTED"
    SCANNED = "SCANNED"
    VERIFIED = "VERIFIED"
    STAGED = "STAGED"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"


class SkillMetadata(BaseModel):
    id: str
    name: str
    version: str
    description: str


class SkillPublisher(BaseModel):
    name: str
    type: str


class SkillSource(BaseModel):
    type: str
    path: str
    repository: str | None = None
    commit: str | None = None
    license: str | None = None


class SkillCapability(BaseModel):
    domain: str
    category: str
    intents: list[str] = Field(default_factory=list)


class SkillRuntime(BaseModel):
    entrypoint: str = "SKILL.md"
    tools: list[str] = Field(default_factory=list)


class SkillPermissions(BaseModel):
    filesystem: str = "none"
    network: str = "none"
    business_write: bool = False


class SkillRisk(BaseModel):
    level: str = "low"


class SkillTrust(BaseModel):
    tier: TrustTier = TrustTier.T2
    security_scan: str = "pending"


class SkillQuality(BaseModel):
    eval_score: float = Field(default=0.0, ge=0.0, le=1.0)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class SkillManifest(BaseModel):
    model_config = {"populate_by_name": True}

    api_version: str = Field(alias="apiVersion")
    kind: str
    metadata: SkillMetadata
    publisher: SkillPublisher
    source: SkillSource
    capability: SkillCapability
    runtime: SkillRuntime
    permissions: SkillPermissions
    risk: SkillRisk
    trust: SkillTrust
    quality: SkillQuality
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_manifest.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/__init__.py backend/agentos/skills/manifest.py backend/tests/agentos/skills/__init__.py backend/tests/agentos/skills/test_manifest.py
git commit -m "feat(agentos): add canonical SkillManifest model"
```

---

### Task 2: Manifest + `SKILL.md` filesystem loader

**Files:**
- Create: `backend/agentos/skills/loader.py`
- Test: `backend/tests/agentos/skills/test_loader.py`

**Interfaces:**
- Consumes: `SkillManifest` from `agentos.skills.manifest` (Task 1).
- Produces: `MANIFEST_FILENAME = "manifest.yaml"`; `INSTRUCTIONS_FILENAME = "SKILL.md"`; `SkillManifestError(skill_dir: Path, reason: str)`; `load_skill_manifest(skill_dir: Path) -> SkillManifest`; `load_skill_instructions(skill_dir: Path) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/test_loader.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.loader import SkillManifestError, load_skill_instructions, load_skill_manifest


def _write_valid_skill(skill_dir: Path) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": "core.weekly-review", "name": "Weekly Review", "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(skill_dir)},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("# Weekly Review\n\nDo the weekly review.\n", encoding="utf-8")


def test_load_skill_manifest_parses_valid_manifest(tmp_path: Path):
    _write_valid_skill(tmp_path)
    manifest = load_skill_manifest(tmp_path)
    assert manifest.metadata.id == "core.weekly-review"


def test_load_skill_manifest_raises_when_manifest_missing(tmp_path: Path):
    with pytest.raises(SkillManifestError):
        load_skill_manifest(tmp_path)


def test_load_skill_instructions_reads_skill_md(tmp_path: Path):
    _write_valid_skill(tmp_path)
    instructions = load_skill_instructions(tmp_path)
    assert "Do the weekly review." in instructions


def test_load_skill_instructions_raises_when_missing(tmp_path: Path):
    tmp_path.mkdir(exist_ok=True)
    with pytest.raises(SkillManifestError):
        load_skill_instructions(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.loader'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/loader.py
from __future__ import annotations

from pathlib import Path

import yaml

from agentos.skills.manifest import SkillManifest

MANIFEST_FILENAME = "manifest.yaml"
INSTRUCTIONS_FILENAME = "SKILL.md"


class SkillManifestError(Exception):
    def __init__(self, skill_dir: Path, reason: str) -> None:
        super().__init__(f"Invalid skill at {skill_dir}: {reason}")
        self.skill_dir = skill_dir


def load_skill_manifest(skill_dir: Path) -> SkillManifest:
    manifest_path = skill_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise SkillManifestError(skill_dir, f"missing {MANIFEST_FILENAME}")
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    try:
        return SkillManifest(**raw)
    except Exception as exc:
        raise SkillManifestError(skill_dir, str(exc)) from exc


def load_skill_instructions(skill_dir: Path) -> str:
    instructions_path = skill_dir / INSTRUCTIONS_FILENAME
    if not instructions_path.is_file():
        raise SkillManifestError(skill_dir, f"missing {INSTRUCTIONS_FILENAME}")
    return instructions_path.read_text(encoding="utf-8")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_loader.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/loader.py backend/tests/agentos/skills/test_loader.py
git commit -m "feat(agentos): add skill manifest and SKILL.md filesystem loader"
```

---

### Task 3: `SkillRegistry`

**Files:**
- Create: `backend/agentos/skills/registry.py`
- Test: `backend/tests/agentos/skills/test_registry.py`

**Interfaces:**
- Consumes: `SkillManifestError`, `load_skill_manifest` from `agentos.skills.loader` (Task 2); `SkillLifecycleStatus`, `SkillManifest` from `agentos.skills.manifest` (Task 1).
- Produces: `SkillNotFoundError(skill_id: str)`; `SkillRecord(manifest: SkillManifest, status: SkillLifecycleStatus, skill_dir: Path)` (dataclass); `SkillRegistry` with `.discover(root: Path) -> list[str]`, `.register(manifest: SkillManifest, skill_dir: Path, status: SkillLifecycleStatus = ACTIVE) -> None`, `.get(skill_id: str) -> SkillRecord`, `.list(*, status: SkillLifecycleStatus | None = None) -> list[SkillRecord]`, `.set_status(skill_id: str, status: SkillLifecycleStatus) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/test_registry.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillNotFoundError, SkillRegistry


def _write_skill(root: Path, skill_id: str) -> Path:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(skill_dir)},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("do it", encoding="utf-8")
    return skill_dir


def test_discover_registers_valid_skill_as_active(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review")
    registry = SkillRegistry()

    discovered = registry.discover(tmp_path)

    assert discovered == ["core.weekly-review"]
    record = registry.get("core.weekly-review")
    assert record.status == SkillLifecycleStatus.ACTIVE
    assert record.manifest.metadata.id == "core.weekly-review"


def test_discover_skips_directory_with_broken_manifest(tmp_path: Path):
    broken_dir = tmp_path / "broken-skill"
    broken_dir.mkdir()
    (broken_dir / "manifest.yaml").write_text("not: [valid, manifest", encoding="utf-8")
    registry = SkillRegistry()

    discovered = registry.discover(tmp_path)

    assert discovered == []


def test_get_missing_skill_raises():
    registry = SkillRegistry()
    with pytest.raises(SkillNotFoundError):
        registry.get("missing")


def test_set_status_updates_record(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review")
    registry = SkillRegistry()
    registry.discover(tmp_path)

    registry.set_status("core.weekly-review", SkillLifecycleStatus.DEPRECATED)

    assert registry.get("core.weekly-review").status == SkillLifecycleStatus.DEPRECATED


def test_list_filters_by_status(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review")
    _write_skill(tmp_path, "core.daily-plan")
    registry = SkillRegistry()
    registry.discover(tmp_path)
    registry.set_status("core.daily-plan", SkillLifecycleStatus.DEPRECATED)

    active = registry.list(status=SkillLifecycleStatus.ACTIVE)

    assert [r.manifest.metadata.id for r in active] == ["core.weekly-review"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.registry'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_registry.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/registry.py backend/tests/agentos/skills/test_registry.py
git commit -m "feat(agentos): add SkillRegistry with lifecycle status"
```

---

### Task 4: `score_skill` + `SkillRouter`

**Files:**
- Create: `backend/agentos/skills/router.py`
- Test: `backend/tests/agentos/skills/test_router.py`

**Interfaces:**
- Consumes: `SkillManifest`, `TrustTier`, `SkillLifecycleStatus` from `agentos.skills.manifest` (Task 1); `SkillRegistry` from `agentos.skills.registry` (Task 3).
- Produces: `score_skill(goal: str, manifest: SkillManifest) -> float`; `SkillRouter(registry: SkillRegistry, min_trust: TrustTier = TrustTier.T2)` with `.select(goal: str, *, allow_business_write: bool = False) -> SkillManifest | None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/test_router.py
from pathlib import Path

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
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter, score_skill


def _make_manifest(
    skill_id: str,
    intents: list[str],
    *,
    tier: TrustTier = TrustTier.T0,
    eval_score: float = 0.8,
    business_write: bool = False,
) -> SkillManifest:
    return SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=" ".join(intents)),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path=skill_id),
        capability=SkillCapability(domain="core", category="general", intents=intents),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=business_write),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=tier, security_scan="passed"),
        quality=SkillQuality(eval_score=eval_score, success_rate=0.8),
    )


def test_score_skill_rewards_matching_intents():
    manifest = _make_manifest("core.weekly-review", ["weekly review", "reflection"])
    assert score_skill("do the weekly review", manifest) > score_skill("unrelated task", manifest)


def test_router_selects_highest_scoring_active_skill():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.weekly-review", ["weekly review"]), skill_dir=Path("."))
    registry.register(_make_manifest("core.other", ["something else"]), skill_dir=Path("."))
    router = SkillRouter(registry)

    selected = router.select("please run my weekly review")

    assert selected is not None
    assert selected.metadata.id == "core.weekly-review"


def test_router_returns_none_when_nothing_relevant():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.other", ["something else"]), skill_dir=Path("."))
    router = SkillRouter(registry)

    assert router.select("do the weekly review") is None


def test_router_excludes_skills_below_min_trust():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.risky", ["weekly review"], tier=TrustTier.T3), skill_dir=Path("."))
    router = SkillRouter(registry, min_trust=TrustTier.T2)

    assert router.select("weekly review") is None


def test_router_excludes_business_write_skill_unless_allowed():
    registry = SkillRegistry()
    registry.register(_make_manifest("core.writer", ["weekly review"], business_write=True), skill_dir=Path("."))
    router = SkillRouter(registry)

    assert router.select("weekly review") is None
    assert router.select("weekly review", allow_business_write=True) is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.router'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/router.py
from __future__ import annotations

import re

from agentos.skills.manifest import SkillLifecycleStatus, SkillManifest, TrustTier
from agentos.skills.registry import SkillRegistry

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

_TRUST_WEIGHT: dict[TrustTier, float] = {
    TrustTier.T0: 1.0,
    TrustTier.T1: 0.8,
    TrustTier.T2: 0.5,
    TrustTier.T3: 0.1,
    TrustTier.T4: 0.0,
}


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower()))


def score_skill(goal: str, manifest: SkillManifest) -> float:
    """MVP subset of the blueprint §26 score formula:
    Score = Relevance + Trust + EvalQuality (Cost/Risk/HistoricalSuccess/
    BusinessFit are not tracked yet — later phases add them).
    """
    goal_tokens = _tokenize(goal)
    intent_tokens: set[str] = set()
    for intent in manifest.capability.intents:
        intent_tokens |= _tokenize(intent)
    intent_tokens |= _tokenize(manifest.metadata.description)

    relevance = 0.0
    if goal_tokens and intent_tokens:
        relevance = len(goal_tokens & intent_tokens) / len(goal_tokens)

    trust = _TRUST_WEIGHT.get(manifest.trust.tier, 0.0)
    return relevance * 0.5 + trust * 0.3 + manifest.quality.eval_score * 0.2


class SkillRouter:
    def __init__(self, registry: SkillRegistry, min_trust: TrustTier = TrustTier.T2) -> None:
        self._registry = registry
        self._min_trust = min_trust

    def select(self, goal: str, *, allow_business_write: bool = False) -> SkillManifest | None:
        candidates = [
            record.manifest
            for record in self._registry.list(status=SkillLifecycleStatus.ACTIVE)
            if self._is_eligible(record.manifest, allow_business_write=allow_business_write)
        ]
        scored = [(score_skill(goal, manifest), manifest) for manifest in candidates]
        relevant = [(score, manifest) for score, manifest in scored if score > 0]
        if not relevant:
            return None
        relevant.sort(key=lambda pair: pair[0], reverse=True)
        return relevant[0][1]

    def _is_eligible(self, manifest: SkillManifest, *, allow_business_write: bool) -> bool:
        trust_order = list(TrustTier)
        if trust_order.index(manifest.trust.tier) > trust_order.index(self._min_trust):
            return False
        if manifest.permissions.business_write and not allow_business_write:
            return False
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_router.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/router.py backend/tests/agentos/skills/test_router.py
git commit -m "feat(agentos): add skill scoring and SkillRouter"
```

---

### Task 5: `SkillInstructionLoader` (progressive disclosure)

**Files:**
- Create: `backend/agentos/skills/instruction_loader.py`
- Test: `backend/tests/agentos/skills/test_instruction_loader.py`

**Interfaces:**
- Consumes: `load_skill_instructions` from `agentos.skills.loader` (Task 2); `SkillNotFoundError`, `SkillRegistry` from `agentos.skills.registry` (Task 3).
- Produces: `SkillInstructionLoader(registry: SkillRegistry)` with `.load(skill_id: str) -> str` (raises `SkillNotFoundError` for an unregistered id).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/skills/test_instruction_loader.py
from pathlib import Path

import pytest
import yaml

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillNotFoundError, SkillRegistry


def _write_skill(root: Path, skill_id: str, instructions: str) -> None:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(skill_dir)},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(instructions, encoding="utf-8")


def test_load_returns_skill_md_contents(tmp_path: Path):
    _write_skill(tmp_path, "core.weekly-review", "# Weekly Review\n\nStep 1: reflect.\n")
    registry = SkillRegistry()
    registry.discover(tmp_path)
    loader = SkillInstructionLoader(registry)

    instructions = loader.load("core.weekly-review")

    assert "Step 1: reflect." in instructions


def test_load_raises_for_unregistered_skill():
    registry = SkillRegistry()
    loader = SkillInstructionLoader(registry)

    with pytest.raises(SkillNotFoundError):
        loader.load("missing")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_instruction_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.skills.instruction_loader'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/skills/instruction_loader.py
from __future__ import annotations

from agentos.skills.loader import load_skill_instructions
from agentos.skills.registry import SkillRegistry


class SkillInstructionLoader:
    """Level 1 progressive disclosure (blueprint §24): only reads a skill's
    SKILL.md when explicitly requested for a selected skill — registry
    discovery (Level 0) never reads instruction bodies.
    """

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    def load(self, skill_id: str) -> str:
        record = self._registry.get(skill_id)
        return load_skill_instructions(record.skill_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_instruction_loader.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/skills/instruction_loader.py backend/tests/agentos/skills/test_instruction_loader.py
git commit -m "feat(agentos): add SkillInstructionLoader for progressive disclosure"
```

---

### Task 6: Real internal skillpack + end-to-end discovery test

**Files:**
- Create: `skillpacks/core/weekly-review/manifest.yaml`
- Create: `skillpacks/core/weekly-review/SKILL.md`
- Test: `backend/tests/agentos/skills/test_skillpacks_integration.py`

**Interfaces:** None new — this task proves Tasks 1–5 work end-to-end against a real file, not a `tmp_path` fixture.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/agentos/skills/test_skillpacks_integration.py
from pathlib import Path

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import SkillRouter

# backend/tests/agentos/skills/test_skillpacks_integration.py -> parents[4] is the repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLPACKS_ROOT = REPO_ROOT / "skillpacks"


def test_weekly_review_skillpack_discovers_and_routes_end_to_end():
    registry = SkillRegistry()
    discovered = registry.discover(SKILLPACKS_ROOT)

    assert "core.weekly-review" in discovered

    router = SkillRouter(registry)
    selected = router.select("help me run my weekly review")
    assert selected is not None
    assert selected.metadata.id == "core.weekly-review"

    loader = SkillInstructionLoader(registry)
    instructions = loader.load("core.weekly-review")
    assert "weekly review" in instructions.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_skillpacks_integration.py -v`
Expected: FAIL — `assert "core.weekly-review" in discovered` fails because `skillpacks/` doesn't exist yet

- [ ] **Step 3: Create the real skillpack**

```yaml
# skillpacks/core/weekly-review/manifest.yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: core.weekly-review
  name: Weekly Review
  version: 1.0.0
  description: Guide a structured weekly review of goals, tasks, and blockers

publisher:
  name: internal
  type: official

source:
  type: local
  path: skillpacks/core/weekly-review

capability:
  domain: core
  category: review
  intents:
    - weekly review
    - reflect on the week
    - review progress

runtime:
  entrypoint: SKILL.md
  tools: []

permissions:
  filesystem: workspace
  network: none
  business_write: false

risk:
  level: low

trust:
  tier: T0
  security_scan: passed

quality:
  eval_score: 0.9
  success_rate: 0.85
```

```markdown
# skillpacks/core/weekly-review/SKILL.md
# Weekly Review

Run a structured weekly review:

1. List what was completed this week.
2. List what is blocked, and why.
3. List the top 3 priorities for next week.
4. Note any recurring blockers worth raising to the founder.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/skills/test_skillpacks_integration.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add skillpacks/core/weekly-review/manifest.yaml skillpacks/core/weekly-review/SKILL.md backend/tests/agentos/skills/test_skillpacks_integration.py
git commit -m "feat(skillpacks): add core.weekly-review internal skillpack"
```

---

### Task 7: Wire `SkillRouter` + `SkillInstructionLoader` into `ContextBuilder`

**Files:**
- Modify: `backend/agentos/core/context.py`
- Modify: `backend/agentos/core/context_builder.py`
- Modify: `backend/tests/agentos/test_context_builder.py`

**Interfaces:**
- Consumes: `SkillRouter` (Task 4), `SkillInstructionLoader` (Task 5).
- Produces (changed): `AgentContext` gains `skill_instructions: list[str] = Field(default_factory=list)`; `ContextBuilder.__init__` gains `skill_router: SkillRouter | None = None, skill_instruction_loader: SkillInstructionLoader | None = None`; `ContextBuilder.build` populates `skill_instructions` by calling `skill_router.select(task.goal)` and, if a skill is selected, `skill_instruction_loader.load(selected.metadata.id)`.

- [ ] **Step 1: Write the failing tests (append to the existing file from Phase 3)**

```python
# backend/tests/agentos/test_context_builder.py — add these imports at the top,
# alongside the existing Phase 3 imports (do not remove them):
import yaml

from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.registry import SkillRegistry as SkillRegistryForRouter
from agentos.skills.router import SkillRouter


def _write_skill(root, skill_id: str, instructions: str) -> None:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {"id": skill_id, "name": skill_id, "version": "1.0.0", "description": "d"},
        "publisher": {"name": "internal", "type": "official"},
        "source": {"type": "local", "path": str(skill_dir)},
        "capability": {"domain": "core", "category": "review", "intents": ["weekly review"]},
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.9, "success_rate": 0.8},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text(instructions, encoding="utf-8")


@pytest.mark.asyncio
async def test_build_without_skill_router_returns_empty_skill_instructions():
    registry = ToolRegistry()
    builder = ContextBuilder(registry)
    task = TaskContext(goal="say hi", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.skill_instructions == []


@pytest.mark.asyncio
async def test_build_populates_skill_instructions_when_router_matches(tmp_path):
    _write_skill(tmp_path, "core.weekly-review", "Do the weekly review steps.")
    skill_registry = SkillRegistryForRouter()
    skill_registry.discover(tmp_path)
    router = SkillRouter(skill_registry)
    loader = SkillInstructionLoader(skill_registry)
    tool_registry = ToolRegistry()
    builder = ContextBuilder(tool_registry, skill_router=router, skill_instruction_loader=loader)
    task = TaskContext(goal="run my weekly review", agent_key="fake", workspace_id="ws1")

    context = await builder.build(task)

    assert context.skill_instructions == ["Do the weekly review steps."]
```

(`SkillRegistryForRouter` is just an import alias to avoid shadowing any local variable named `registry` already used for the `ToolRegistry` in the existing tests in this file — keep both imports distinct.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_context_builder.py -v`
Expected: FAIL — `ContextBuilder() got an unexpected keyword argument 'skill_router'`

- [ ] **Step 3: Modify `AgentContext`**

```python
# backend/agentos/core/context.py
from __future__ import annotations

from pydantic import BaseModel, Field

from agentos.core.models import TaskContext


class AgentContext(BaseModel):
    task: TaskContext
    system_policy: str
    tool_names: list[str] = Field(default_factory=list)
    memory_snippets: list[str] = Field(default_factory=list)
    skill_instructions: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Modify `ContextBuilder`**

```python
# backend/agentos/core/context_builder.py
from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.models import TaskContext
from agentos.memory.retriever import MemoryRetriever
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry

DEFAULT_SYSTEM_POLICY = (
    "You are an AI Agent OS agent. Use only the tools listed. "
    "Never fabricate tool results."
)


class ContextBuilder:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        system_policy: str = DEFAULT_SYSTEM_POLICY,
        memory_retriever: MemoryRetriever | None = None,
        skill_router: SkillRouter | None = None,
        skill_instruction_loader: SkillInstructionLoader | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._system_policy = system_policy
        self._memory_retriever = memory_retriever
        self._skill_router = skill_router
        self._skill_instruction_loader = skill_instruction_loader

    async def build(self, task: TaskContext) -> AgentContext:
        memory_snippets = await self._memory_retriever.retrieve(task) if self._memory_retriever else []
        return AgentContext(
            task=task,
            system_policy=self._system_policy,
            tool_names=self._tool_registry.names(),
            memory_snippets=memory_snippets,
            skill_instructions=self._select_skill_instructions(task),
        )

    def _select_skill_instructions(self, task: TaskContext) -> list[str]:
        if self._skill_router is None or self._skill_instruction_loader is None:
            return []
        selected = self._skill_router.select(task.goal)
        if selected is None:
            return []
        return [self._skill_instruction_loader.load(selected.metadata.id)]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/test_context_builder.py -v`
Expected: 5 passed (3 from Phase 3 + 2 new)

- [ ] **Step 6: Check for and fix any other caller affected by the constructor signature change**

Run: `grep -rn "ContextBuilder(" backend/agentos backend/tests/agentos`
Expected: matches only inside `context_builder.py`, `runtime.py`, and the test files above — `ContextBuilder(tool_registry)` positional-only calls (e.g. in `runtime.py`) remain valid since the two new parameters are keyword-only-by-default with `None` defaults; no other change needed there.

- [ ] **Step 7: Run the full `agentos` suite to confirm no regressions**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v`
Expected: all passing (Phase 0/1 + Phase 3 tests, plus Phase 4's 20 new skill-layer tests: 3 manifest + 4 loader + 5 registry + 5 router + 2 instruction_loader + 1 skillpacks_integration, plus the updated `test_context_builder.py` now at 5 tests)

- [ ] **Step 8: Commit**

```bash
git add backend/agentos/core/context.py backend/agentos/core/context_builder.py backend/tests/agentos/test_context_builder.py
git commit -m "feat(agentos): wire SkillRouter and SkillInstructionLoader into ContextBuilder"
```

---

## Verification (end of Phase 4)

1. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — all tests pass.
2. Run the full existing backend suite to confirm zero impact outside `agentos/`: `cd backend && PYTHONPATH=. ./.venv/bin/pytest -q` — no existing test outside `backend/agentos/`/`backend/tests/agentos/` newly fails.
3. Confirm the skill layer still isn't wired into any production call site: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results.
4. Manually inspect `skillpacks/core/weekly-review/manifest.yaml` and confirm it validates against `SkillManifest` by re-running Task 6's integration test in isolation.

## Next steps (not part of this plan)

Per `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4: Phase 5 (Marketing Skill Pack — a second, business-domain skillpack pilot proving the Skill Layer generalizes beyond one internal example) is next, followed by Phase 6 (External Skill Supply Chain — DISCOVER→...→PROMOTE pipeline, `awesome-agent-skills` as a discovery source). Each should get its own plan via `superpowers:writing-plans` once this one is merged and reviewed.
