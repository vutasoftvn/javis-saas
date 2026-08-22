# AgentOS Phase 10 — Self-Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the loop the blueprint describes end-to-end (§34: observe → detect repeated failure → identify capability gap → search skill → evaluate candidates → recommend → human approval → stage → canary → promote) by composing pieces already built in Phases 1–9 — `SkillRegistry`/`SkillRouter` scoring (Phase 4/5), `SupplyChainPipeline` (Phase 6), and `ApprovalService` (Phase 8) — behind three new primitives: capability-gap detection, an improvement proposal + human-approval gate, and a deterministic Improvement Hierarchy guard (§36) that refuses a "change the core code" proposal until every cheaper level has actually been tried. A companion Skill Distillation primitive (§37) drafts a new internal skill from repeated successful runs, stopping short of publishing it — a human still decides whether to run the draft through Phase 6's real supply chain. This is the last phase in the roadmap (`docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4).

**Architecture:** New `backend/agentos/improvement/` subpackage, matching the blueprint's own top-level `agentos/` layout (§2). `GapDetector` takes a list of `CapabilityOutcome` records (capability name, succeeded, eval_score — the caller's job to produce these from real `AgentEvalResult`/`WorkflowEvalResult` history, Phase 9; this phase doesn't add that wiring) and flags any capability whose failure count and average eval score cross configurable thresholds, producing a `CapabilityGap` shaped exactly like the blueprint's §35 YAML example (`capability`, `evidence.failed_tasks`, `evidence.average_eval`). `propose_candidates()` reuses `agentos.skills.router.score_skill` (Phase 4/5) to rank every registered skill — regardless of lifecycle status, since a `VERIFIED`-but-not-yet-`ACTIVE` Phase 6 supply-chain candidate is a legitimate proposal target — against the gap's capability name, producing an `ImprovementProposal` (§76: candidate, expected_gain, risk, status). `request_proposal_approval()`/`apply_approval_decision()`/`mark_promoted()` route that proposal through Phase 8's real `ApprovalService` — there is no separate approval mechanism invented for self-improvement, it's the same one everything else in the system uses. `ImprovementLevel` + `require_cheaper_levels_exhausted()` is a pure, deterministic guard implementing §36's ordered hierarchy (Context/retrieval → Skill selection → Tool selection → Workflow → Prompt/instructions → Memory policy → Model choice → Business rule → Agent role → Core code): calling it with `ImprovementLevel.CORE_CODE` and an incomplete `tried_levels` list raises — this can't be talked past by an LLM, it's a plain list-membership check. `distill_skill()` (§37) takes a set of `SuccessfulEpisode` records for one agent, requires a minimum sample size, and drafts a `SkillManifest` + `SKILL.md` body — trust tier `T2` (not auto-trusted `T0`) and `quality.eval_score = 0.0`, since the draft itself hasn't been evaluated yet even though its source episodes succeeded. The final integration task runs the whole loop — gap → real Phase 6 candidate → proposal → approval → promotion — end to end, plus a second test proving the hierarchy guard actually blocks an unjustified core-code escalation.

**Tech Stack:** Python 3.11, pydantic 2.13, PyYAML 6.0, pytest + pytest-asyncio — same as prior `agentos` phases, no new dependencies.

## Global Constraints

- New files only, entirely under `backend/agentos/improvement/` and `backend/tests/agentos/improvement/`. Do not modify any file outside this new subpackage — everything this phase needs from `agentos.skills`, `agentos.core.approval`, and `agentos.skills.supply_chain` (Phases 4/5/6/8) is consumed as-is.
- **Prerequisite:** this plan assumes Phase 4/5 (`SkillManifest`, `SkillRegistry`, `score_skill`), Phase 6 (`SupplyChainPipeline`, `ImmutableArtifactStore`, `ExternalSkillCandidate`), and Phase 8 (`ApprovalService`) have already landed. Task 6 exercises all three directly.
- `GapDetector`'s thresholds (`min_failures`, `eval_threshold`) are constructor parameters with sensible defaults, never hardcoded magic numbers scattered through the detection logic.
- `propose_candidates()` deliberately does not filter to `ACTIVE`-only skills — that's what makes it useful for finding a Phase-6-verified-but-not-yet-promoted candidate. Do not "simplify" this to match `SkillRouter`'s `ACTIVE`-only behavior; they serve different purposes (routing a live task vs. proposing what to activate next).
- `require_cheaper_levels_exhausted()` is the one piece of this phase that must stay strict: it is the code that stands between "an agent decided core code needs to change" and that change actually being proposed. Do not add a bypass parameter, a default that skips the check, or a way to call it with an empty `tried_levels` list for any level above `CONTEXT_RETRIEVAL`.
- `distill_skill()` never writes to `skillpacks/` or calls anything in `agentos.skills.supply_chain` — it only returns a `DistilledSkillDraft` object. Publishing a distilled skill is the caller's decision, made through the existing Phase 6 pipeline, not a new path invented here.
- Every async test needs `@pytest.mark.asyncio` (`backend/pytest.ini` has `asyncio_mode = strict`); most of this phase's functions are synchronous, so most tests are not async — Task 6's integration test is the exception (it drives `SupplyChainPipeline`, whose methods are async).
- Run tests via: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/<file> -v`.
- Source spec: `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §34 (Self-Improvement), §35 (Capability Gap Detection), §36 (Improvement Hierarchy), §37 (Skill Distillation), §76 (ImprovementProposal object), §4 (Phase 10 scope).

---

## File Structure

```text
backend/agentos/improvement/
├── __init__.py
├── gap_detection.py       # CapabilityOutcome, CapabilityGapEvidence, CapabilityGap, GapDetector
├── proposal.py               # ProposalStatus, ImprovementProposal, propose_candidates
├── approval_gate.py             # ProposalNotApprovedError, request_proposal_approval, apply_approval_decision, mark_promoted
├── hierarchy.py                    # ImprovementLevel, PrematureCoreCodeChangeError, rank, require_cheaper_levels_exhausted
└── distillation.py                    # SuccessfulEpisode, DistilledSkillDraft, NotEnoughEvidenceError, distill_skill

backend/tests/agentos/improvement/
├── __init__.py
├── test_gap_detection.py
├── test_proposal.py
├── test_approval_gate.py
├── test_hierarchy.py
├── test_distillation.py
└── test_full_self_improvement_loop.py
```

---

### Task 1: `GapDetector`

**Files:**
- Create: `backend/agentos/improvement/__init__.py`
- Create: `backend/agentos/improvement/gap_detection.py`
- Create: `backend/tests/agentos/improvement/__init__.py`
- Test: `backend/tests/agentos/improvement/test_gap_detection.py`

**Interfaces:**
- Produces: `CapabilityOutcome(capability: str, succeeded: bool, eval_score: float)`; `CapabilityGapEvidence(failed_tasks: int, average_eval: float)`; `CapabilityGap(capability: str, evidence: CapabilityGapEvidence)`; `GapDetector(*, min_failures: int = 3, eval_threshold: float = 0.6)` with `.detect(outcomes: list[CapabilityOutcome]) -> list[CapabilityGap]`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/improvement/test_gap_detection.py
from agentos.improvement.gap_detection import CapabilityOutcome, GapDetector


def _outcomes(capability: str, *, successes: int, failures: int, eval_score: float) -> list[CapabilityOutcome]:
    return [
        CapabilityOutcome(capability=capability, succeeded=True, eval_score=eval_score) for _ in range(successes)
    ] + [
        CapabilityOutcome(capability=capability, succeeded=False, eval_score=eval_score) for _ in range(failures)
    ]


def test_detect_flags_capability_with_enough_failures_and_low_average_eval():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("marketing.keyword-clustering", successes=2, failures=8, eval_score=0.54)

    gaps = detector.detect(outcomes)

    assert len(gaps) == 1
    assert gaps[0].capability == "marketing.keyword-clustering"
    assert gaps[0].evidence.failed_tasks == 8
    assert gaps[0].evidence.average_eval == 0.54


def test_detect_ignores_capability_below_failure_threshold():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("sales.qualify-lead", successes=8, failures=2, eval_score=0.3)

    gaps = detector.detect(outcomes)

    assert gaps == []


def test_detect_ignores_capability_with_good_average_eval_despite_failures():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("sales.qualify-lead", successes=1, failures=5, eval_score=0.9)

    gaps = detector.detect(outcomes)

    assert gaps == []


def test_detect_handles_multiple_capabilities_independently():
    detector = GapDetector(min_failures=3, eval_threshold=0.6)
    outcomes = _outcomes("a", successes=0, failures=5, eval_score=0.2) + _outcomes(
        "b", successes=5, failures=0, eval_score=0.9
    )

    gaps = detector.detect(outcomes)

    assert [g.capability for g in gaps] == ["a"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_gap_detection.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.improvement'`

- [ ] **Step 3: Create package scaffolding and the implementation**

```python
# backend/agentos/improvement/__init__.py
```

```python
# backend/tests/agentos/improvement/__init__.py
```

```python
# backend/agentos/improvement/gap_detection.py
from __future__ import annotations

from pydantic import BaseModel, Field


class CapabilityOutcome(BaseModel):
    capability: str
    succeeded: bool
    eval_score: float = Field(ge=0.0, le=1.0)


class CapabilityGapEvidence(BaseModel):
    failed_tasks: int
    average_eval: float


class CapabilityGap(BaseModel):
    capability: str
    evidence: CapabilityGapEvidence


class GapDetector:
    """Observe -> detect repeated failure -> identify capability gap
    (blueprint §34/§35). Thresholds are explicit constructor parameters,
    not magic numbers — callers decide how many failures and how low an
    average eval score constitutes a real gap for their context.
    """

    def __init__(self, *, min_failures: int = 3, eval_threshold: float = 0.6) -> None:
        self._min_failures = min_failures
        self._eval_threshold = eval_threshold

    def detect(self, outcomes: list[CapabilityOutcome]) -> list[CapabilityGap]:
        by_capability: dict[str, list[CapabilityOutcome]] = {}
        for outcome in outcomes:
            by_capability.setdefault(outcome.capability, []).append(outcome)

        gaps: list[CapabilityGap] = []
        for capability, records in by_capability.items():
            failed = [r for r in records if not r.succeeded]
            average_eval = sum(r.eval_score for r in records) / len(records)
            if len(failed) >= self._min_failures and average_eval < self._eval_threshold:
                gaps.append(
                    CapabilityGap(
                        capability=capability,
                        evidence=CapabilityGapEvidence(failed_tasks=len(failed), average_eval=average_eval),
                    )
                )
        return gaps
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_gap_detection.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/improvement/__init__.py backend/agentos/improvement/gap_detection.py backend/tests/agentos/improvement/__init__.py backend/tests/agentos/improvement/test_gap_detection.py
git commit -m "feat(agentos): add GapDetector (capability gap detection)"
```

---

### Task 2: `propose_candidates`

**Files:**
- Create: `backend/agentos/improvement/proposal.py`
- Test: `backend/tests/agentos/improvement/test_proposal.py`

**Interfaces:**
- Consumes: `CapabilityGap` (Task 1); `score_skill` from `agentos.skills.router` (Phase 4/5); `SkillLifecycleStatus` from `agentos.skills.manifest` (Phase 4); `SkillRegistry` from `agentos.skills.registry` (Phase 4).
- Produces: `ProposalStatus` (str enum: `PROPOSED`, `APPROVED`, `REJECTED`, `PROMOTED`); `ImprovementProposal(id: str, gap: CapabilityGap, candidate_skill_ids: list[str], expected_gain: float, risk: str, status: ProposalStatus = PROPOSED)`; `propose_candidates(gap: CapabilityGap, registry: SkillRegistry, *, limit: int = 3) -> ImprovementProposal`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/improvement/test_proposal.py
from pathlib import Path

from agentos.improvement.gap_detection import CapabilityGap, CapabilityGapEvidence
from agentos.improvement.proposal import ProposalStatus, propose_candidates
from agentos.skills.manifest import (
    SkillCapability,
    SkillLifecycleStatus,
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


def _register_skill(
    registry: SkillRegistry, skill_id: str, intents: list[str], *, status: SkillLifecycleStatus = SkillLifecycleStatus.ACTIVE
) -> None:
    manifest = SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(id=skill_id, name=skill_id, version="1.0.0", description=" ".join(intents)),
        publisher=SkillPublisher(name="internal", type="official"),
        source=SkillSource(type="local", path=skill_id),
        capability=SkillCapability(domain="marketing", category="research", intents=intents),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=False),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=TrustTier.T0, security_scan="passed"),
        quality=SkillQuality(eval_score=0.8, success_rate=0.8),
    )
    registry.register(manifest, Path("."), status=status)


def test_propose_candidates_ranks_matching_skills():
    registry = SkillRegistry()
    _register_skill(registry, "marketing.keyword-clustering", ["keyword clustering", "group keywords"])
    _register_skill(registry, "marketing.copywriting", ["write ad copy"])
    gap = CapabilityGap(
        capability="marketing.keyword-clustering",
        evidence=CapabilityGapEvidence(failed_tasks=8, average_eval=0.54),
    )

    proposal = propose_candidates(gap, registry)

    assert proposal.candidate_skill_ids[0] == "marketing.keyword-clustering"
    assert proposal.status == ProposalStatus.PROPOSED
    assert proposal.expected_gain > 0


def test_propose_candidates_returns_empty_when_nothing_matches():
    registry = SkillRegistry()
    _register_skill(registry, "marketing.copywriting", ["write ad copy"])
    gap = CapabilityGap(
        capability="finance.reconcile-invoices",
        evidence=CapabilityGapEvidence(failed_tasks=5, average_eval=0.4),
    )

    proposal = propose_candidates(gap, registry)

    assert proposal.candidate_skill_ids == []
    assert proposal.expected_gain == 0.0


def test_propose_candidates_marks_inactive_candidate_as_medium_risk():
    registry = SkillRegistry()
    _register_skill(
        registry, "marketing.keyword-clustering", ["keyword clustering"], status=SkillLifecycleStatus.VERIFIED
    )
    gap = CapabilityGap(
        capability="marketing.keyword-clustering",
        evidence=CapabilityGapEvidence(failed_tasks=8, average_eval=0.54),
    )

    proposal = propose_candidates(gap, registry)

    assert proposal.risk == "medium"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_proposal.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.improvement.proposal'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/improvement/proposal.py
from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, Field

from agentos.improvement.gap_detection import CapabilityGap
from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.router import score_skill


class ProposalStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"


class ImprovementProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    gap: CapabilityGap
    candidate_skill_ids: list[str]
    expected_gain: float
    risk: str
    status: ProposalStatus = ProposalStatus.PROPOSED


def propose_candidates(gap: CapabilityGap, registry: SkillRegistry, *, limit: int = 3) -> ImprovementProposal:
    """Search-skill / evaluate-candidates stage of the self-improvement
    loop (blueprint §34/§35). Ranks every registered skill — regardless
    of lifecycle status, since a VERIFIED-but-not-yet-ACTIVE Phase 6
    supply-chain candidate is a legitimate proposal target — against the
    gap's capability name, reusing the exact same relevance scoring as
    SkillRouter (Phase 4/5).
    """
    scored = [(score_skill(gap.capability, record.manifest), record) for record in registry.list()]
    ranked = sorted((pair for pair in scored if pair[0] > 0), key=lambda pair: pair[0], reverse=True)
    top = ranked[:limit]
    expected_gain = max((score for score, _ in top), default=0.0)
    risk = "low" if top and top[0][1].status == SkillLifecycleStatus.ACTIVE else "medium"
    return ImprovementProposal(
        gap=gap,
        candidate_skill_ids=[record.manifest.metadata.id for _, record in top],
        expected_gain=expected_gain,
        risk=risk,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_proposal.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/improvement/proposal.py backend/tests/agentos/improvement/test_proposal.py
git commit -m "feat(agentos): add propose_candidates"
```

---

### Task 3: Approval gate for proposals

**Files:**
- Create: `backend/agentos/improvement/approval_gate.py`
- Test: `backend/tests/agentos/improvement/test_approval_gate.py`

**Interfaces:**
- Consumes: `ApprovalService`, `Approval`, `ApprovalStatus` from `agentos.core.approval` (Phase 8); `ImprovementProposal`, `ProposalStatus` from `agentos.improvement.proposal` (Task 2).
- Produces: `ProposalNotApprovedError(proposal_id: str)`; `request_proposal_approval(proposal: ImprovementProposal, approval_service: ApprovalService, *, requester: str) -> Approval`; `apply_approval_decision(proposal: ImprovementProposal, approval: Approval) -> ImprovementProposal`; `mark_promoted(proposal: ImprovementProposal) -> ImprovementProposal` (raises `ProposalNotApprovedError` unless `status == APPROVED`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/improvement/test_approval_gate.py
import pytest

from agentos.core.approval import ApprovalService
from agentos.improvement.approval_gate import (
    ProposalNotApprovedError,
    apply_approval_decision,
    mark_promoted,
    request_proposal_approval,
)
from agentos.improvement.gap_detection import CapabilityGap, CapabilityGapEvidence
from agentos.improvement.proposal import ImprovementProposal, ProposalStatus


def _make_proposal() -> ImprovementProposal:
    gap = CapabilityGap(
        capability="marketing.keyword-clustering",
        evidence=CapabilityGapEvidence(failed_tasks=8, average_eval=0.54),
    )
    return ImprovementProposal(
        gap=gap, candidate_skill_ids=["marketing.keyword-clustering"], expected_gain=0.8, risk="low"
    )


def test_request_proposal_approval_creates_pending_approval():
    service = ApprovalService()
    proposal = _make_proposal()

    approval = request_proposal_approval(proposal, service, requester="improvement_agent")

    assert approval.subject == "marketing.keyword-clustering"
    assert approval.action == "promote_skill_for_capability_gap"


def test_apply_approval_decision_marks_proposal_approved():
    service = ApprovalService()
    proposal = _make_proposal()
    approval = request_proposal_approval(proposal, service, requester="improvement_agent")
    service.decide(approval.id, reviewer="founder", approved=True)

    updated = apply_approval_decision(proposal, service.get(approval.id))

    assert updated.status == ProposalStatus.APPROVED


def test_apply_approval_decision_marks_proposal_rejected():
    service = ApprovalService()
    proposal = _make_proposal()
    approval = request_proposal_approval(proposal, service, requester="improvement_agent")
    service.decide(approval.id, reviewer="founder", approved=False, reason="too risky")

    updated = apply_approval_decision(proposal, service.get(approval.id))

    assert updated.status == ProposalStatus.REJECTED


def test_mark_promoted_requires_approved_status():
    proposal = _make_proposal()
    with pytest.raises(ProposalNotApprovedError):
        mark_promoted(proposal)


def test_mark_promoted_succeeds_after_approval():
    proposal = _make_proposal()
    proposal.status = ProposalStatus.APPROVED

    updated = mark_promoted(proposal)

    assert updated.status == ProposalStatus.PROMOTED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_approval_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.improvement.approval_gate'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/improvement/approval_gate.py
from __future__ import annotations

from agentos.core.approval import Approval, ApprovalService, ApprovalStatus
from agentos.improvement.proposal import ImprovementProposal, ProposalStatus


class ProposalNotApprovedError(Exception):
    def __init__(self, proposal_id: str) -> None:
        super().__init__(f"Improvement proposal {proposal_id} has not been approved")
        self.proposal_id = proposal_id


def request_proposal_approval(
    proposal: ImprovementProposal, approval_service: ApprovalService, *, requester: str
) -> Approval:
    """Human approval stage of the self-improvement loop (blueprint §34)
    routes through the exact same ApprovalService everything else in the
    system uses (Phase 8) — there is no separate approval mechanism
    invented for self-improvement.
    """
    return approval_service.request_approval(
        action="promote_skill_for_capability_gap",
        subject=proposal.gap.capability,
        requester=requester,
    )


def apply_approval_decision(proposal: ImprovementProposal, approval: Approval) -> ImprovementProposal:
    if approval.status == ApprovalStatus.APPROVED:
        proposal.status = ProposalStatus.APPROVED
    elif approval.status == ApprovalStatus.DENIED:
        proposal.status = ProposalStatus.REJECTED
    return proposal


def mark_promoted(proposal: ImprovementProposal) -> ImprovementProposal:
    if proposal.status != ProposalStatus.APPROVED:
        raise ProposalNotApprovedError(proposal.id)
    proposal.status = ProposalStatus.PROMOTED
    return proposal
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_approval_gate.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/improvement/approval_gate.py backend/tests/agentos/improvement/test_approval_gate.py
git commit -m "feat(agentos): wire improvement proposals through Phase 8 ApprovalService"
```

---

### Task 4: `ImprovementLevel` + `require_cheaper_levels_exhausted`

**Files:**
- Create: `backend/agentos/improvement/hierarchy.py`
- Test: `backend/tests/agentos/improvement/test_hierarchy.py`

**Interfaces:**
- Produces: `ImprovementLevel` (str enum, ordered: `CONTEXT_RETRIEVAL`, `SKILL_SELECTION`, `TOOL_SELECTION`, `WORKFLOW`, `PROMPT_INSTRUCTIONS`, `MEMORY_POLICY`, `MODEL_CHOICE`, `BUSINESS_RULE`, `AGENT_ROLE`, `CORE_CODE`); `PrematureCoreCodeChangeError(missing: list[ImprovementLevel])`; `rank(level: ImprovementLevel) -> int`; `require_cheaper_levels_exhausted(target_level: ImprovementLevel, tried_levels: list[ImprovementLevel]) -> None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/improvement/test_hierarchy.py
import pytest

from agentos.improvement.hierarchy import (
    ImprovementLevel,
    PrematureCoreCodeChangeError,
    rank,
    require_cheaper_levels_exhausted,
)


def test_rank_orders_context_retrieval_first_and_core_code_last():
    assert rank(ImprovementLevel.CONTEXT_RETRIEVAL) < rank(ImprovementLevel.CORE_CODE)


def test_context_retrieval_never_requires_cheaper_levels():
    require_cheaper_levels_exhausted(ImprovementLevel.CONTEXT_RETRIEVAL, [])


def test_core_code_raises_when_cheaper_levels_not_tried():
    with pytest.raises(PrematureCoreCodeChangeError):
        require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, [ImprovementLevel.SKILL_SELECTION])


def test_core_code_passes_when_every_cheaper_level_tried():
    all_cheaper = [
        ImprovementLevel.CONTEXT_RETRIEVAL,
        ImprovementLevel.SKILL_SELECTION,
        ImprovementLevel.TOOL_SELECTION,
        ImprovementLevel.WORKFLOW,
        ImprovementLevel.PROMPT_INSTRUCTIONS,
        ImprovementLevel.MEMORY_POLICY,
        ImprovementLevel.MODEL_CHOICE,
        ImprovementLevel.BUSINESS_RULE,
        ImprovementLevel.AGENT_ROLE,
    ]
    require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, all_cheaper)


def test_workflow_level_only_requires_the_two_levels_below_it():
    with pytest.raises(PrematureCoreCodeChangeError) as exc_info:
        require_cheaper_levels_exhausted(ImprovementLevel.WORKFLOW, [ImprovementLevel.CONTEXT_RETRIEVAL])
    assert exc_info.value.missing == [ImprovementLevel.SKILL_SELECTION, ImprovementLevel.TOOL_SELECTION]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_hierarchy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.improvement.hierarchy'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/improvement/hierarchy.py
from __future__ import annotations

import enum


class ImprovementLevel(str, enum.Enum):
    CONTEXT_RETRIEVAL = "CONTEXT_RETRIEVAL"
    SKILL_SELECTION = "SKILL_SELECTION"
    TOOL_SELECTION = "TOOL_SELECTION"
    WORKFLOW = "WORKFLOW"
    PROMPT_INSTRUCTIONS = "PROMPT_INSTRUCTIONS"
    MEMORY_POLICY = "MEMORY_POLICY"
    MODEL_CHOICE = "MODEL_CHOICE"
    BUSINESS_RULE = "BUSINESS_RULE"
    AGENT_ROLE = "AGENT_ROLE"
    CORE_CODE = "CORE_CODE"


_ORDER: list[ImprovementLevel] = [
    ImprovementLevel.CONTEXT_RETRIEVAL,
    ImprovementLevel.SKILL_SELECTION,
    ImprovementLevel.TOOL_SELECTION,
    ImprovementLevel.WORKFLOW,
    ImprovementLevel.PROMPT_INSTRUCTIONS,
    ImprovementLevel.MEMORY_POLICY,
    ImprovementLevel.MODEL_CHOICE,
    ImprovementLevel.BUSINESS_RULE,
    ImprovementLevel.AGENT_ROLE,
    ImprovementLevel.CORE_CODE,
]


class PrematureCoreCodeChangeError(Exception):
    def __init__(self, missing: list[ImprovementLevel]) -> None:
        super().__init__(
            "Cannot propose this level of change until every cheaper level has been "
            f"tried and ruled out (blueprint §36): missing {[level.value for level in missing]}"
        )
        self.missing = missing


def rank(level: ImprovementLevel) -> int:
    return _ORDER.index(level)


def require_cheaper_levels_exhausted(target_level: ImprovementLevel, tried_levels: list[ImprovementLevel]) -> None:
    """Enforce blueprint §36's Improvement Hierarchy: a proposal that
    targets any level above CONTEXT_RETRIEVAL must show every cheaper
    level was tried first. Deterministic code, not a suggestion an LLM
    can talk its way past.
    """
    if target_level == ImprovementLevel.CONTEXT_RETRIEVAL:
        return
    required = set(_ORDER[: rank(target_level)])
    missing = [level for level in _ORDER if level in required and level not in tried_levels]
    if missing:
        raise PrematureCoreCodeChangeError(missing)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_hierarchy.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/improvement/hierarchy.py backend/tests/agentos/improvement/test_hierarchy.py
git commit -m "feat(agentos): add ImprovementLevel hierarchy guard"
```

---

### Task 5: `distill_skill`

**Files:**
- Create: `backend/agentos/improvement/distillation.py`
- Test: `backend/tests/agentos/improvement/test_distillation.py`

**Interfaces:**
- Consumes: `SkillManifest` and its sub-models, `TrustTier` from `agentos.skills.manifest` (Phase 4).
- Produces: `MIN_EPISODES_TO_DISTILL = 3`; `SuccessfulEpisode(agent_key: str, goal: str, output: str)`; `DistilledSkillDraft(manifest: SkillManifest, instructions_markdown: str, source_episode_count: int)`; `NotEnoughEvidenceError(agent_key: str, count: int)`; `distill_skill(agent_key: str, episodes: list[SuccessfulEpisode], *, skill_id: str, domain: str) -> DistilledSkillDraft`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/improvement/test_distillation.py
import pytest

from agentos.improvement.distillation import NotEnoughEvidenceError, SuccessfulEpisode, distill_skill
from agentos.skills.manifest import TrustTier


def test_distill_skill_raises_when_not_enough_episodes():
    episodes = [SuccessfulEpisode(agent_key="researcher", goal="research acme", output="found acme details")]
    with pytest.raises(NotEnoughEvidenceError):
        distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")


def test_distill_skill_produces_a_draft_from_matching_episodes():
    episodes = [
        SuccessfulEpisode(agent_key="researcher", goal="research acme", output="found acme details"),
        SuccessfulEpisode(agent_key="researcher", goal="research beta co", output="found beta co details"),
        SuccessfulEpisode(agent_key="researcher", goal="research gamma inc", output="found gamma inc details"),
        SuccessfulEpisode(agent_key="other_agent", goal="unrelated", output="unrelated output"),
    ]

    draft = distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")

    assert draft.source_episode_count == 3
    assert draft.manifest.metadata.id == "core.researcher-pattern"
    assert draft.manifest.trust.tier == TrustTier.T2
    assert draft.manifest.quality.eval_score == 0.0
    assert "found acme details" in draft.instructions_markdown
    assert "found beta co details" in draft.instructions_markdown


def test_distill_skill_ignores_episodes_from_other_agents():
    episodes = [
        SuccessfulEpisode(agent_key="researcher", goal="a", output="a-out"),
        SuccessfulEpisode(agent_key="researcher", goal="b", output="b-out"),
        SuccessfulEpisode(agent_key="researcher", goal="c", output="c-out"),
        SuccessfulEpisode(agent_key="other_agent", goal="d", output="d-out"),
        SuccessfulEpisode(agent_key="other_agent", goal="e", output="e-out"),
    ]

    draft = distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")

    assert draft.source_episode_count == 3
    assert "d-out" not in draft.instructions_markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_distillation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentos.improvement.distillation'`

- [ ] **Step 3: Write the implementation**

```python
# backend/agentos/improvement/distillation.py
from __future__ import annotations

from pydantic import BaseModel

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

MIN_EPISODES_TO_DISTILL = 3


class SuccessfulEpisode(BaseModel):
    agent_key: str
    goal: str
    output: str


class DistilledSkillDraft(BaseModel):
    manifest: SkillManifest
    instructions_markdown: str
    source_episode_count: int


class NotEnoughEvidenceError(Exception):
    def __init__(self, agent_key: str, count: int) -> None:
        super().__init__(
            f"Only {count} successful episode(s) for {agent_key!r} — need at least "
            f"{MIN_EPISODES_TO_DISTILL} to distill a skill (blueprint §37)"
        )
        self.agent_key = agent_key
        self.count = count


def distill_skill(
    agent_key: str, episodes: list[SuccessfulEpisode], *, skill_id: str, domain: str
) -> DistilledSkillDraft:
    """Skill Distillation, draft stage only (blueprint §37): successful
    traces -> detect repeated pattern -> extract procedure -> draft
    SKILL.md. Stops before sandbox / human approval / publish — this
    function never writes to skillpacks/ or touches
    agentos.skills.supply_chain; a human reviews the draft, and
    publishing it (if approved) goes through the existing Phase 6
    SupplyChainPipeline rather than a bespoke publish path invented here.
    Trust tier starts at T2 (not auto-trusted T0) and quality.eval_score
    at 0.0, since the draft itself hasn't been evaluated yet — only its
    source episodes succeeded.
    """
    matching = [episode for episode in episodes if episode.agent_key == agent_key]
    if len(matching) < MIN_EPISODES_TO_DISTILL:
        raise NotEnoughEvidenceError(agent_key, len(matching))

    steps = "\n".join(f"{i + 1}. {episode.output}" for i, episode in enumerate(matching))
    instructions = f"# {skill_id}\n\nDistilled from {len(matching)} successful runs by `{agent_key}`:\n\n{steps}\n"

    manifest = SkillManifest(
        apiVersion="agentos.ai/v1",
        kind="Skill",
        metadata=SkillMetadata(
            id=skill_id,
            name=skill_id,
            version="0.1.0",
            description=f"Distilled from {len(matching)} successful {agent_key} runs",
        ),
        publisher=SkillPublisher(name="internal", type="distilled"),
        source=SkillSource(type="local", path=f"skillpacks/distilled/{skill_id}"),
        capability=SkillCapability(domain=domain, category="distilled", intents=[]),
        runtime=SkillRuntime(entrypoint="SKILL.md", tools=[]),
        permissions=SkillPermissions(filesystem="workspace", network="none", business_write=False),
        risk=SkillRisk(level="low"),
        trust=SkillTrust(tier=TrustTier.T2, security_scan="pending"),
        quality=SkillQuality(eval_score=0.0, success_rate=0.0),
    )
    return DistilledSkillDraft(
        manifest=manifest, instructions_markdown=instructions, source_episode_count=len(matching)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_distillation.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/agentos/improvement/distillation.py backend/tests/agentos/improvement/test_distillation.py
git commit -m "feat(agentos): add distill_skill (Skill Distillation draft stage)"
```

---

### Task 6: Integration — the full loop, gap to promoted skill, plus the hierarchy guard blocking an unjustified escalation

**Files:**
- Test: `backend/tests/agentos/improvement/test_full_self_improvement_loop.py`

**Interfaces:** None new — assembles Tasks 1–5 plus Phase 4/5/6/8's real `SkillRegistry`, `SupplyChainPipeline`, and `ApprovalService`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/agentos/improvement/test_full_self_improvement_loop.py
from pathlib import Path

import pytest
import yaml

from agentos.core.approval import ApprovalService
from agentos.improvement.approval_gate import apply_approval_decision, mark_promoted, request_proposal_approval
from agentos.improvement.distillation import SuccessfulEpisode, distill_skill
from agentos.improvement.gap_detection import CapabilityOutcome, GapDetector
from agentos.improvement.hierarchy import ImprovementLevel, PrematureCoreCodeChangeError, require_cheaper_levels_exhausted
from agentos.improvement.proposal import ProposalStatus, propose_candidates
from agentos.skills.manifest import SkillLifecycleStatus
from agentos.skills.registry import SkillRegistry
from agentos.skills.supply_chain.artifact_store import ImmutableArtifactStore
from agentos.skills.supply_chain.catalog import ExternalSkillCandidate
from agentos.skills.supply_chain.pipeline import SupplyChainPipeline


def _write_external_skill(root: Path, skill_id: str) -> Path:
    skill_dir = root / skill_id.replace(".", "-")
    skill_dir.mkdir(parents=True)
    manifest = {
        "apiVersion": "agentos.ai/v1",
        "kind": "Skill",
        "metadata": {
            "id": skill_id,
            "name": skill_id,
            "version": "1.0.0",
            "description": "keyword clustering helper",
        },
        "publisher": {"name": "community", "type": "community"},
        "source": {
            "type": "git",
            "path": f"skills/{skill_id}",
            "repository": "https://github.com/example/skills",
            "commit": "4bc9a82c1234567890abcdef1234567890abcdef",
        },
        "capability": {
            "domain": "marketing",
            "category": "seo",
            "intents": ["keyword clustering", "group keywords"],
        },
        "runtime": {"entrypoint": "SKILL.md", "tools": []},
        "permissions": {"filesystem": "workspace", "network": "none", "business_write": False},
        "risk": {"level": "low"},
        "trust": {"tier": "T0", "security_scan": "passed"},
        "quality": {"eval_score": 0.85, "success_rate": 0.85},
    }
    (skill_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    (skill_dir / "SKILL.md").write_text("# Keyword Clustering\n\nCluster keywords.\n", encoding="utf-8")
    return skill_dir


@pytest.mark.asyncio
async def test_full_self_improvement_loop_from_gap_to_promoted_skill(tmp_path: Path):
    # 1. Observe repeated failures -> detect a capability gap.
    outcomes = [
        CapabilityOutcome(capability="marketing.keyword-clustering", succeeded=False, eval_score=0.5)
        for _ in range(5)
    ] + [CapabilityOutcome(capability="marketing.keyword-clustering", succeeded=True, eval_score=0.6)]
    gaps = GapDetector(min_failures=3, eval_threshold=0.6).detect(outcomes)
    assert len(gaps) == 1
    gap = gaps[0]

    # 2. A real supply-chain-verified candidate skill exists in the registry.
    skill_dir = _write_external_skill(tmp_path / "source", "marketing.keyword-clustering")
    registry = SkillRegistry()
    artifact_store = ImmutableArtifactStore(tmp_path / "registry" / "skills")
    pipeline = SupplyChainPipeline(registry, artifact_store)
    candidate = ExternalSkillCandidate(
        id="marketing.keyword-clustering",
        name="Keyword Clustering",
        description="d",
        repository="https://github.com/example/skills",
        path="skills/marketing.keyword-clustering",
        commit="4bc9a82c1234567890abcdef1234567890abcdef",
    )
    skill_id = pipeline.import_candidate(candidate, skill_dir)
    pipeline.scan(skill_id)  # -> VERIFIED (low risk, high trust manifest)

    # 3. Search skill — Improvement Hierarchy level SKILL_SELECTION, no
    #    core code change needed, so the guard passes trivially.
    require_cheaper_levels_exhausted(ImprovementLevel.SKILL_SELECTION, [ImprovementLevel.CONTEXT_RETRIEVAL])
    proposal = propose_candidates(gap, registry)
    assert proposal.candidate_skill_ids[0] == "marketing.keyword-clustering"
    assert proposal.risk == "medium"  # candidate is VERIFIED, not yet ACTIVE

    # 4. Human approval, then promotion — through Phase 6's real pipeline.
    approval_service = ApprovalService()
    approval = request_proposal_approval(proposal, approval_service, requester="improvement_agent")
    approval_service.decide(approval.id, reviewer="founder", approved=True, reason="looks good")
    proposal = apply_approval_decision(proposal, approval_service.get(approval.id))
    proposal = mark_promoted(proposal)
    pipeline.stage(skill_id)
    pipeline.promote_to_active(skill_id, approved_by="founder")

    assert proposal.status == ProposalStatus.PROMOTED
    assert registry.get(skill_id).status == SkillLifecycleStatus.ACTIVE


def test_distillation_produces_a_draft_and_core_code_escalation_is_blocked_without_justification():
    episodes = [
        SuccessfulEpisode(agent_key="researcher", goal="research a", output="found a"),
        SuccessfulEpisode(agent_key="researcher", goal="research b", output="found b"),
        SuccessfulEpisode(agent_key="researcher", goal="research c", output="found c"),
    ]

    draft = distill_skill("researcher", episodes, skill_id="core.researcher-pattern", domain="core")
    assert draft.source_episode_count == 3

    with pytest.raises(PrematureCoreCodeChangeError):
        require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, [ImprovementLevel.SKILL_SELECTION])
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/test_full_self_improvement_loop.py -v`
Expected: 2 passed — this is a pure integration proof over already-implemented Tasks 1–5 plus Phase 4/5/6/8, so there is no separate "watch it fail first" step: if either test fails, it points at a real incompatibility, not a missing-module error — stop and investigate rather than proceeding.

- [ ] **Step 3: Run the full `improvement` suite to confirm everything holds together**

Run: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/ -v`
Expected: all passing — 4 (gap_detection) + 3 (proposal) + 5 (approval_gate) + 5 (hierarchy) + 3 (distillation) + 2 (full loop) = 22 total

- [ ] **Step 4: Commit**

```bash
git add backend/tests/agentos/improvement/test_full_self_improvement_loop.py
git commit -m "test(agentos): prove the full self-improvement loop end-to-end"
```

---

## Verification (end of Phase 10)

1. Run the full improvement suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/improvement/ -v` — all tests pass (22 total per Task 6 Step 3).
2. Run the full `agentos` suite: `cd backend && PYTHONPATH=. ./.venv/bin/pytest tests/agentos/ -v` — no regressions in Phase 0/1/3/4/5/6/7/8/9 tests. This is the last phase in the roadmap, so this is also the first point where the entire `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4 Phase 0–10 list has at least one plan written and (per Phases 0/1/3/4/5/6/7 already being under active implementation) substantially implemented — worth running the complete suite once here rather than just the delta.
3. Confirm no production wiring was introduced: `grep -rn "import agentos\|from agentos" backend --include="*.py" | grep -v "^backend/agentos/\|^backend/tests/agentos/"` returns no results — this has been true at the end of every phase in this roadmap, and stays true here too: `agentos/` remains fully inert with respect to `cosa_core`/`workforce`, exactly as the blueprint's big-bang framing intended for this stage (build the target architecture standalone; the cutover decision is separate and comes later).
4. Manually re-read `agentos/improvement/hierarchy.py` one more time and confirm there is truly no way to call `require_cheaper_levels_exhausted(ImprovementLevel.CORE_CODE, ...)` successfully without having `tried_levels` cover every one of the nine cheaper levels — this function is the phase's one hard safety property, worth double-checking by hand rather than trusting the tests alone.

## Next steps (not part of this plan)

This closes the Phase 0–10 roadmap from `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` §4. What remains, per that spec and each phase's own "Next steps" notes, is entirely cutover/hardening work, not new roadmap phases:

- Wiring `agentos/` into an actual production call site — every phase so far has verified `agentos/` is inert with respect to `cosa_core`/`workforce`; deciding *whether and how* to cut traffic over is the big remaining decision flagged back in the original blueprint spec (§6, big-bang vs. incremental) and was deliberately left to the user.
- The Encore TypeScript `services/` layer from Phase 2 only has `tasks` and `okr` — CRM/Marketing/Finance/Billing/Workflow business services from the blueprint's Business OS (§38) are unbuilt.
- Real token/cost usage tracking on `ModelProvider` (flagged in Phase 9), real parent/child span nesting through `Executor` (also Phase 9), a real external `CatalogSource` fetcher instead of Phase 6's `StaticCatalogSource`, real sandboxed execution during Phase 6's `stage()`, and Approval-object-aware workflow eval metrics (Phase 9) are all named, specific hardening items already called out in their respective phase plans.
