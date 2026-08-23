# Governance Temporal Model — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the framework-neutral governance/identity primitives (`PinnedSpecIdentity`, `SpecResolutionManifest`, `PolicyDecision`/`ApprovalRequirement`, the temporal accumulator `combine_decisions`/`InvocationGovernanceState`) described in `COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md`, and fix the concrete bug that motivated the whole model: `agentos/workflows/definition_registry.py::WorkflowDefinitionRegistry` currently versions an opaque Python closure instead of the declarative `WorkflowSpec`, so a resumed Run has no way to prove it is still running the version it started with.

**Architecture:** New framework-neutral package `packages/agent_core/governance/` (no dependency on `agentos/`) holds the identity-hashing and temporal-accumulator primitives. `agentos/workflows/definition_registry.py` and `agentos/workflows/engine.py` are modified in place to consume `agent_core.governance.hashing.definition_hash` and to version `WorkflowSpec` objects directly — this is the existing "promote in place, don't fork" pattern already used for `agentos/workflows/` per the CrewAI Supplement A2 audit.

**Tech Stack:** Python 3.11, Pydantic v2 (`BaseModel`), pytest + pytest-asyncio (`asyncio_mode = strict`), no new third-party dependencies.

## Global Constraints

- Match existing code style exactly: `from __future__ import annotations` at the top of every new module, Pydantic `BaseModel` (not raw `@dataclass`) for data types (matches `agentos/core/models.py`, `agentos/workflows/models.py`), `str, enum.Enum` mixin for string enums.
- New/changed code comments explaining *why* (not what) go in Vietnamese; identifiers, error messages, and quoted spec text stay in English (CLAUDE.md rule 19).
- Do not touch `agentos/core/policy.py`, `agentos/core/approval.py`, `agentos/tools/registry.py`, or `agentos/workflows/tool_step.py` in this plan — rewiring those to consume the new accumulator is a separate, later plan (V4 Bước 7) that depends on this one landing first.
- Do not add Alembic or any new migration tool — this plan has no database/persistence component (that is V4 Bước 6, a separate plan).
- Every existing test under `tests/agentos/workflows/` must still pass unchanged except `tests/agentos/workflows/test_definition_registry.py`, which this plan rewrites deliberately.
- No placeholders: every step below is the literal code to write.

---

### Task 1: Package scaffolding + `definition_hash` utility

**Files:**
- Create: `packages/agent_core/__init__.py`
- Create: `packages/agent_core/governance/__init__.py`
- Create: `packages/agent_core/governance/hashing.py`
- Create: `tests/agent_core/__init__.py`
- Create: `tests/agent_core/governance/__init__.py`
- Create: `tests/agent_core/governance/test_hashing.py`
- Modify: `pytest.ini`
- Modify: `Makefile`

**Interfaces:**
- Produces: `agent_core.governance.hashing.definition_hash(model: pydantic.BaseModel) -> str` — used by Task 6 and by every later plan that pins an `AgentSpec`/`WorkflowSpec`.

- [ ] **Step 1: Create empty package `__init__.py` files**

```bash
mkdir -p packages/agent_core/governance tests/agent_core/governance
touch packages/agent_core/__init__.py packages/agent_core/governance/__init__.py
touch tests/agent_core/__init__.py tests/agent_core/governance/__init__.py
```

- [ ] **Step 2: Wire `packages/` onto the pytest path and test collection**

Modify `pytest.ini` (current content shown for reference — replace the `pythonpath` and `testpaths` lines only):

```ini
[pytest]
pythonpath = . agentos packages
testpaths = tests/agentos tests/agent_core
asyncio_mode = strict
asyncio_default_fixture_loop_scope = function
markers =
    integration: marks tests as integration tests
filterwarnings =
    ignore::DeprecationWarning
```

- [ ] **Step 3: Add a Makefile target so `packages/agent_core` tests run the same way `agentos-test` does**

In `Makefile`, immediately after the existing `agentos-test:` target, add:

```makefile
agent-core-test:
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/agent_core -q
```

And change the `verify` target line from:

```makefile
verify: boundary-check agentos-test frontend-test frontend-analyze
```

to:

```makefile
verify: boundary-check agentos-test agent-core-test frontend-test frontend-analyze
```

- [ ] **Step 4: Write the failing test for `definition_hash`**

Create `tests/agent_core/governance/test_hashing.py`:

```python
from __future__ import annotations

from pydantic import BaseModel

from agent_core.governance.hashing import definition_hash


class _Sample(BaseModel):
    id: str
    values: list[int]


def test_definition_hash_is_a_64_char_hex_sha256():
    result = definition_hash(_Sample(id="a", values=[1, 2]))

    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_definition_hash_is_identical_for_identical_content():
    a = definition_hash(_Sample(id="a", values=[1, 2]))
    b = definition_hash(_Sample(id="a", values=[1, 2]))

    assert a == b


def test_definition_hash_differs_when_content_differs():
    a = definition_hash(_Sample(id="a", values=[1, 2]))
    b = definition_hash(_Sample(id="a", values=[1, 3]))

    assert a != b


def test_definition_hash_is_not_affected_by_python_dict_construction_order():
    # Pydantic model fields are positional/keyword here, not a raw dict, but
    # the underlying JSON canonicalization must still sort keys so that two
    # equivalent models never hash differently due to incidental ordering.
    a = _Sample.model_validate({"id": "a", "values": [1, 2]})
    b = _Sample.model_validate({"values": [1, 2], "id": "a"})

    assert definition_hash(a) == definition_hash(b)
```

- [ ] **Step 5: Run the test to verify it fails with an import error**

Run: `.venv/bin/pytest tests/agent_core/governance/test_hashing.py -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'agent_core'`

- [ ] **Step 6: Implement `definition_hash`**

Create `packages/agent_core/governance/hashing.py`:

```python
from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel


def definition_hash(model: BaseModel) -> str:
    """sha256 của canonical JSON của 1 Pydantic model — dùng để pin 1
    executable spec (AgentSpec/WorkflowSpec) theo đúng nội dung thật, thay
    vì dựa vào version do con người gán (dễ quên bump, hoặc bump nhầm mà
    nội dung không đổi/đổi mà không bump — silent drift). `sort_keys=True`
    đảm bảo thứ tự field lúc construct không ảnh hưởng tới hash."""
    canonical = json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_hashing.py -v`
Expected: 4 passed

- [ ] **Step 8: Run the full `agent-core-test` Makefile target to confirm wiring works end to end**

Run: `make agent-core-test`
Expected: `1 passed` or more, `0 failed`

- [ ] **Step 9: Commit**

```bash
git add packages/agent_core tests/agent_core pytest.ini Makefile
git commit -m "feat(agent-core): add definition_hash primitive and packages/agent_core scaffolding"
```

---

### Task 2: `PinnedSpecIdentity` and `SpecResolutionManifest`

**Files:**
- Create: `packages/agent_core/governance/contracts.py`
- Create: `tests/agent_core/governance/test_contracts.py`

**Interfaces:**
- Consumes: `agent_core.governance.hashing.definition_hash` (Task 1) — used only in tests here, not by the types themselves.
- Produces: `agent_core.governance.contracts.PinnedSpecIdentity(spec_kind, spec_id, spec_version, definition_hash)`, `agent_core.governance.contracts.SpecResolutionManifest(entries).with_entry(entry) -> SpecResolutionManifest` — consumed by Task 6 and by later plans (Bước 4/6 kernel-resume wiring).

- [ ] **Step 1: Write the failing tests**

Create `tests/agent_core/governance/test_contracts.py`:

```python
from __future__ import annotations

from agent_core.governance.contracts import PinnedSpecIdentity, SpecResolutionManifest


def _identity(spec_id: str = "cofounder", version: str = "1") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(
        spec_kind="agent",
        spec_id=spec_id,
        spec_version=version,
        definition_hash="a" * 64,
    )


def test_pinned_spec_identity_holds_the_four_required_fields():
    identity = _identity()

    assert identity.spec_kind == "agent"
    assert identity.spec_id == "cofounder"
    assert identity.spec_version == "1"
    assert identity.definition_hash == "a" * 64


def test_spec_resolution_manifest_starts_empty():
    manifest = SpecResolutionManifest()

    assert manifest.entries == ()


def test_with_entry_appends_a_new_pinned_identity():
    manifest = SpecResolutionManifest()
    entry = _identity()

    updated = manifest.with_entry(entry)

    assert updated.entries == (entry,)
    assert manifest.entries == ()  # bản gốc không bị mutate


def test_with_entry_never_drops_an_earlier_entry():
    first = _identity(spec_id="supervisor")
    second = _identity(spec_id="legal")  # vd: delegate động, resolve giữa chừng Run

    manifest = SpecResolutionManifest().with_entry(first).with_entry(second)

    assert manifest.entries == (first, second)


def test_with_entry_is_idempotent_for_the_same_identity():
    entry = _identity()
    manifest = SpecResolutionManifest().with_entry(entry)

    manifest_again = manifest.with_entry(entry)

    assert manifest_again.entries == (entry,)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_contracts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.governance.contracts'`

- [ ] **Step 3: Implement the types**

Create `packages/agent_core/governance/contracts.py`:

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PinnedSpecIdentity(BaseModel):
    """Định danh bất biến của 1 executable spec (AgentSpec/WorkflowSpec) mà
    1 Run đã resolve tới. `definition_hash` (không phải chỉ `spec_version`)
    là thứ chống silent drift — xem PHẦN I §1 của
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md."""

    spec_kind: Literal["agent", "workflow"]
    spec_id: str
    spec_version: str
    definition_hash: str


class SpecResolutionManifest(BaseModel):
    """Tập PinnedSpecIdentity mà 1 Run/checkpoint đã resolve tới thời điểm
    đó. Chỉ tăng dần (agent-as-tool delegate thêm 1 AgentSpec giữa chừng
    Run là ví dụ điển hình) — không bao giờ xoá entry đã có."""

    entries: tuple[PinnedSpecIdentity, ...] = Field(default_factory=tuple)

    def with_entry(self, entry: PinnedSpecIdentity) -> "SpecResolutionManifest":
        if entry in self.entries:
            return self
        return SpecResolutionManifest(entries=(*self.entries, entry))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_contracts.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_contracts.py
git commit -m "feat(agent-core): add PinnedSpecIdentity and SpecResolutionManifest contracts"
```

---

### Task 3: `PolicyOutcome`, `ApprovalRequirement` predicate tree, `PolicyDecision`, `ApprovalEvidence`

**Files:**
- Modify: `packages/agent_core/governance/contracts.py`
- Modify: `tests/agent_core/governance/test_contracts.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `PolicyOutcome` (enum: `ALLOW`/`DENY`/`REQUIRE_APPROVAL`), `RoleApproval`, `UserApproval`, `AllOf`, `AnyOf`, `Quorum` (the `ApprovalRequirement` predicate union), `PolicyDecision(outcome, requirement, reasons)`, `ApprovalEvidence(approver, scope, decided_at, valid_until)` — consumed by Task 4/5.

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent_core/governance/test_contracts.py`:

```python
from agent_core.governance.contracts import (
    AllOf,
    AnyOf,
    ApprovalEvidence,
    PolicyDecision,
    PolicyOutcome,
    Quorum,
    RoleApproval,
    UserApproval,
)


def test_policy_outcome_has_the_three_expected_values():
    assert {o.value for o in PolicyOutcome} == {"ALLOW", "DENY", "REQUIRE_APPROVAL"}


def test_role_approval_predicate_holds_a_role():
    predicate = RoleApproval(role="founder")

    assert predicate.role == "founder"
    assert predicate.kind == "role_approval"


def test_user_approval_predicate_holds_a_user_id():
    predicate = UserApproval(user_id="alice")

    assert predicate.user_id == "alice"
    assert predicate.kind == "user_approval"


def test_all_of_wraps_multiple_predicates():
    predicate = AllOf(predicates=(RoleApproval(role="founder"), RoleApproval(role="cfo")))

    assert len(predicate.predicates) == 2
    assert predicate.kind == "all"


def test_any_of_wraps_multiple_predicates():
    predicate = AnyOf(predicates=(RoleApproval(role="security"), UserApproval(user_id="alice")))

    assert len(predicate.predicates) == 2
    assert predicate.kind == "any"


def test_quorum_holds_a_count_and_eligible_roles():
    predicate = Quorum(count=2, roles=("cfo", "coo", "finance_admin"))

    assert predicate.count == 2
    assert predicate.roles == ("cfo", "coo", "finance_admin")


def test_policy_decision_defaults_to_no_requirement_and_no_reasons():
    decision = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    assert decision.requirement is None
    assert decision.reasons == ()


def test_policy_decision_can_hold_a_composite_requirement():
    requirement = AllOf(predicates=(RoleApproval(role="founder"), RoleApproval(role="finance_admin")))

    decision = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=requirement,
        reasons=("tool_risk=CRITICAL",),
    )

    assert decision.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert decision.requirement == requirement
    assert decision.reasons == ("tool_risk=CRITICAL",)


def test_approval_evidence_holds_approver_scope_and_validity_window():
    evidence = ApprovalEvidence(
        approver="founder-1",
        scope="tool_call_42",
        decided_at="2026-08-23T10:00:00Z",
        valid_until=None,
    )

    assert evidence.approver == "founder-1"
    assert evidence.scope == "tool_call_42"
    assert evidence.valid_until is None
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_contracts.py -v`
Expected: FAIL — `ImportError: cannot import name 'PolicyOutcome' from 'agent_core.governance.contracts'`

- [ ] **Step 3: Implement the types**

Append to `packages/agent_core/governance/contracts.py`:

```python
import enum
from typing import Union


class PolicyOutcome(str, enum.Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class RoleApproval(BaseModel):
    kind: Literal["role_approval"] = "role_approval"
    role: str


class UserApproval(BaseModel):
    kind: Literal["user_approval"] = "user_approval"
    user_id: str


class AllOf(BaseModel):
    """Predicate 'phải thoả TẤT CẢ' — dùng để AND hai requirement không so
    sánh được (vd FounderApproval và FinanceAdminApproval), thay vì chọn 1
    trong 2 theo kiểu stricter(a, b) (giả định sai: 2 requirement luôn so
    sánh được theo 1 thang duy nhất)."""

    kind: Literal["all"] = "all"
    predicates: tuple["ApprovalRequirement", ...]


class AnyOf(BaseModel):
    kind: Literal["any"] = "any"
    predicates: tuple["ApprovalRequirement", ...]


class Quorum(BaseModel):
    kind: Literal["quorum"] = "quorum"
    count: int
    roles: tuple[str, ...]


ApprovalRequirement = Union[RoleApproval, UserApproval, AllOf, AnyOf, Quorum]

AllOf.model_rebuild()
AnyOf.model_rebuild()


class PolicyDecision(BaseModel):
    outcome: PolicyOutcome
    requirement: ApprovalRequirement | None = None
    reasons: tuple[str, ...] = Field(default_factory=tuple)


class ApprovalEvidence(BaseModel):
    """Bằng chứng con người đã approve — tách khỏi ApprovalRequirement (dự
    kiến sẽ thoả predicate nào) vì evidence có thể expire (`valid_until`),
    trong khi requirement đã tích luỹ vào G_acc thì không tự hết hạn theo
    thời gian (xem PHẦN I §2.1/§5 của tài liệu governance temporal model).
    `scope` bind evidence vào đúng 1 invocation (thường là tool_call_id)."""

    approver: str
    scope: str
    decided_at: str
    valid_until: str | None = None
```

Move the `import enum` and `from typing import Union` lines up to the top of the file alongside the existing `from typing import Literal` import (single import block, matching the rest of the codebase's style), and add `import enum` there too. The final top-of-file imports for `packages/agent_core/governance/contracts.py` should read:

```python
from __future__ import annotations

import enum
from typing import Literal, Union

from pydantic import BaseModel, Field
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_contracts.py -v`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_contracts.py
git commit -m "feat(agent-core): add PolicyDecision/ApprovalRequirement predicate tree and ApprovalEvidence"
```

---

### Task 4: `combine_decisions` — the temporal conjunction operator

**Files:**
- Create: `packages/agent_core/governance/accumulator.py`
- Create: `tests/agent_core/governance/test_accumulator.py`

**Interfaces:**
- Consumes: `PolicyOutcome`, `PolicyDecision`, `RoleApproval`, `AllOf` (Task 3).
- Produces: `agent_core.governance.accumulator.combine_decisions(a: PolicyDecision, b: PolicyDecision) -> PolicyDecision` — consumed by Task 5.

- [ ] **Step 1: Write the failing tests — covering the three risk-drift scenarios from the design discussion**

Create `tests/agent_core/governance/test_accumulator.py`:

```python
from __future__ import annotations

from agent_core.governance.accumulator import combine_decisions
from agent_core.governance.contracts import AllOf, PolicyDecision, PolicyOutcome, RoleApproval


def test_allow_and_allow_is_allow():
    a = PolicyDecision(outcome=PolicyOutcome.ALLOW)
    b = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    result = combine_decisions(a, b)

    assert result.outcome == PolicyOutcome.ALLOW
    assert result.requirement is None


def test_deny_dominates_allow():
    a = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("tenant_suspended",))
    b = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    result = combine_decisions(a, b)

    assert result.outcome == PolicyOutcome.DENY


def test_deny_dominates_require_approval():
    a = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    b = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("connector_revoked",))

    result = combine_decisions(a, b)

    assert result.outcome == PolicyOutcome.DENY


def test_risk_increase_after_approval_still_requires_the_new_stricter_approval():
    # Case A của tài liệu: risk MEDIUM -> CRITICAL. Approval cũ (dưới
    # MEDIUM) không được tự động đủ cho CRITICAL.
    request_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="finance_admin"),
        reasons=("risk=MEDIUM",),
    )
    resume_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="security_officer"),
        reasons=("risk=CRITICAL",),
    )

    effective = combine_decisions(request_time, resume_time)

    assert effective.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert effective.requirement == AllOf(
        predicates=(RoleApproval(role="finance_admin"), RoleApproval(role="security_officer"))
    )


def test_risk_decrease_does_not_erase_the_original_constraint():
    # Case B của tài liệu: risk CRITICAL -> LOW. Relaxation sau đó KHÔNG
    # được xoá constraint CRITICAL đã tích luỹ từ request-time.
    request_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="founder"),
        reasons=("risk=CRITICAL",),
    )
    resume_time = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("risk=LOW",))

    effective = combine_decisions(request_time, resume_time)

    assert effective.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert effective.requirement == RoleApproval(role="founder")


def test_orthogonal_requirement_change_requires_both_not_the_longer_list():
    # Case C của tài liệu: requirement đổi trực giao (không so sánh được
    # theo severity) -> phải AND cả hai, không phải "list dài hơn thắng".
    request_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="founder"),
    )
    resume_time = PolicyDecision(
        outcome=PolicyOutcome.REQUIRE_APPROVAL,
        requirement=RoleApproval(role="finance_admin"),
    )

    effective = combine_decisions(request_time, resume_time)

    assert effective.requirement == AllOf(
        predicates=(RoleApproval(role="founder"), RoleApproval(role="finance_admin"))
    )


def test_combining_identical_requirements_does_not_double_wrap():
    a = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    b = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))

    result = combine_decisions(a, b)

    assert result.requirement == RoleApproval(role="founder")


def test_reasons_are_merged_without_duplicates_preserving_order():
    a = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("r1", "r2"))
    b = PolicyDecision(outcome=PolicyOutcome.ALLOW, reasons=("r2", "r3"))

    result = combine_decisions(a, b)

    assert result.reasons == ("r1", "r2", "r3")


def test_combine_is_commutative_for_outcome_and_requirement():
    a = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    b = PolicyDecision(outcome=PolicyOutcome.DENY, reasons=("connector_revoked",))

    forward = combine_decisions(a, b)
    backward = combine_decisions(b, a)

    assert forward.outcome == backward.outcome == PolicyOutcome.DENY
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_accumulator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.governance.accumulator'`

- [ ] **Step 3: Implement `combine_decisions`**

Create `packages/agent_core/governance/accumulator.py`:

```python
from __future__ import annotations

from agent_core.governance.contracts import AllOf, ApprovalRequirement, PolicyDecision, PolicyOutcome

_OUTCOME_RANK: dict[PolicyOutcome, int] = {
    PolicyOutcome.ALLOW: 0,
    PolicyOutcome.REQUIRE_APPROVAL: 1,
    PolicyOutcome.DENY: 2,
}


def combine_decisions(a: PolicyDecision, b: PolicyDecision) -> PolicyDecision:
    """Temporal conjunction (`G_a ∧ G_b`) của 2 PolicyDecision, tái dùng
    đúng lattice DENY > REQUIRE_APPROVAL > ALLOW đã có trong
    agentos/core/policy.py::evaluate_access() — chỉ mở rộng áp dụng theo
    trục thời gian (request-time ∧ resume-time) thay vì chỉ giữa 6
    dimension trong 1 lần gọi. KHÔNG dùng `stricter(a, b)` kiểu chọn 1
    trong 2, vì requirement có thể không so sánh được (vd FounderApproval
    vs FinanceAdminApproval không có bên nào "chặt hơn" bên nào) — phải
    AND (`AllOf`) cả hai predicate lại, không chọn 1 bên. Xem PHẦN I §2 của
    COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md."""
    outcome = a.outcome if _OUTCOME_RANK[a.outcome] >= _OUTCOME_RANK[b.outcome] else b.outcome
    requirement = _combine_requirements(a.requirement, b.requirement)
    reasons = tuple(dict.fromkeys((*a.reasons, *b.reasons)))
    return PolicyDecision(outcome=outcome, requirement=requirement, reasons=reasons)


def _combine_requirements(
    a: ApprovalRequirement | None, b: ApprovalRequirement | None
) -> ApprovalRequirement | None:
    if a is None:
        return b
    if b is None:
        return a
    if a == b:
        return a
    return AllOf(predicates=(a, b))
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_accumulator.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/accumulator.py tests/agent_core/governance/test_accumulator.py
git commit -m "feat(agent-core): add combine_decisions temporal conjunction operator"
```

---

### Task 5: `InvocationGovernanceState` — the monotonic per-invocation accumulator

**Files:**
- Modify: `packages/agent_core/governance/accumulator.py`
- Modify: `tests/agent_core/governance/test_accumulator.py`

**Interfaces:**
- Consumes: `combine_decisions` (Task 4).
- Produces: `agent_core.governance.accumulator.InvocationGovernanceState(run_id, tool_call_id, accumulated)`, `.accumulate(observation: PolicyDecision) -> InvocationGovernanceState`, `.start(run_id, tool_call_id, initial) -> InvocationGovernanceState` classmethod — this is the type Bước 6/7 will persist as `invocation_governance_state` rows (see Phần II of the governance temporal model doc); this plan stops at the in-memory type.

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent_core/governance/test_accumulator.py`:

```python
from agent_core.governance.accumulator import InvocationGovernanceState


def test_start_creates_state_keyed_by_run_and_tool_call():
    initial = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    state = InvocationGovernanceState.start(run_id="run-1", tool_call_id="call-1", initial=initial)

    assert state.run_id == "run-1"
    assert state.tool_call_id == "call-1"
    assert state.accumulated == initial


def test_accumulate_folds_a_new_observation_via_combine_decisions():
    state = InvocationGovernanceState.start(
        run_id="run-1",
        tool_call_id="call-1",
        initial=PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder")),
    )

    updated = state.accumulate(
        PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="finance_admin"))
    )

    assert updated.accumulated.requirement == AllOf(
        predicates=(RoleApproval(role="founder"), RoleApproval(role="finance_admin"))
    )


def test_accumulate_does_not_mutate_the_original_state():
    state = InvocationGovernanceState.start(
        run_id="run-1", tool_call_id="call-1", initial=PolicyDecision(outcome=PolicyOutcome.ALLOW)
    )

    state.accumulate(PolicyDecision(outcome=PolicyOutcome.DENY))

    assert state.accumulated.outcome == PolicyOutcome.ALLOW


def test_three_observations_accumulate_in_order_and_never_relax():
    # Mô phỏng đúng ví dụ 3-mốc request -> decision -> resume của tài liệu:
    # policy siết ở decision-time (G1), rồi nới ở resume-time (G2) — G0
    # vẫn phải còn nguyên trong kết quả cuối.
    g0 = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="finance_admin"))
    g1 = PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder"))
    g2 = PolicyDecision(outcome=PolicyOutcome.ALLOW)

    state = InvocationGovernanceState.start(run_id="run-1", tool_call_id="call-1", initial=g0)
    state = state.accumulate(g1)
    state = state.accumulate(g2)

    assert state.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert state.accumulated.requirement == AllOf(
        predicates=(RoleApproval(role="finance_admin"), RoleApproval(role="founder"))
    )


def test_two_different_invocations_do_not_share_accumulated_state():
    # Key theo (run_id, tool_call_id) — 1 invocation rủi ro không được
    # "nhiễm" constraint sang 1 invocation khác trong cùng Run.
    state_a = InvocationGovernanceState.start(
        run_id="run-1",
        tool_call_id="call-A",
        initial=PolicyDecision(outcome=PolicyOutcome.REQUIRE_APPROVAL, requirement=RoleApproval(role="founder")),
    )
    state_b = InvocationGovernanceState.start(
        run_id="run-1", tool_call_id="call-B", initial=PolicyDecision(outcome=PolicyOutcome.ALLOW)
    )

    assert state_a.accumulated.outcome == PolicyOutcome.REQUIRE_APPROVAL
    assert state_b.accumulated.outcome == PolicyOutcome.ALLOW
    assert state_a.tool_call_id != state_b.tool_call_id
```

Add `RoleApproval` to the existing import line at the top of `tests/agent_core/governance/test_accumulator.py` (change `from agent_core.governance.contracts import AllOf, PolicyDecision, PolicyOutcome, RoleApproval` — it is already imported from Task 4's step, no change needed since `RoleApproval` was already in that import list).

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/agent_core/governance/test_accumulator.py -v`
Expected: FAIL — `ImportError: cannot import name 'InvocationGovernanceState' from 'agent_core.governance.accumulator'`

- [ ] **Step 3: Implement `InvocationGovernanceState`**

Append to `packages/agent_core/governance/accumulator.py`:

```python
from pydantic import BaseModel


class InvocationGovernanceState(BaseModel):
    """Accumulator monotonic cho 1 invocation cụ thể, key theo
    (run_id, tool_call_id) — KHÔNG theo toàn Run, để 1 tool-call rủi ro
    không "nhiễm" constraint sang tool-call khác không liên quan trong
    cùng Run. Đối lập với Run-level governance (ambient/current, không
    monotonic) — xem PHẦN I §2.3 của tài liệu governance temporal model."""

    run_id: str
    tool_call_id: str
    accumulated: PolicyDecision

    @classmethod
    def start(cls, *, run_id: str, tool_call_id: str, initial: PolicyDecision) -> "InvocationGovernanceState":
        return cls(run_id=run_id, tool_call_id=tool_call_id, accumulated=initial)

    def accumulate(self, observation: PolicyDecision) -> "InvocationGovernanceState":
        return InvocationGovernanceState(
            run_id=self.run_id,
            tool_call_id=self.tool_call_id,
            accumulated=combine_decisions(self.accumulated, observation),
        )
```

Move `from pydantic import BaseModel` up into the single top-of-file import block alongside the existing `from agent_core.governance.contracts import ...` line, so the final imports at the top of `packages/agent_core/governance/accumulator.py` read:

```python
from __future__ import annotations

from pydantic import BaseModel

from agent_core.governance.contracts import AllOf, ApprovalRequirement, PolicyDecision, PolicyOutcome
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/pytest tests/agent_core/governance/test_accumulator.py -v`
Expected: 14 passed

- [ ] **Step 5: Run the full `agent-core-test` suite**

Run: `make agent-core-test`
Expected: 33 passed (9 hashing/contracts from Tasks 1-3 + 14 accumulator + earlier — exact count not load-bearing, just confirm 0 failed)

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/governance/accumulator.py tests/agent_core/governance/test_accumulator.py
git commit -m "feat(agent-core): add InvocationGovernanceState monotonic per-invocation accumulator"
```

---

### Task 6: Fix `WorkflowDefinitionRegistry` to version `WorkflowSpec`, not a Python closure

**Files:**
- Modify: `agentos/workflows/engine.py`
- Modify: `agentos/workflows/definition_registry.py`
- Modify: `tests/agentos/workflows/test_definition_registry.py`

**Interfaces:**
- Consumes: `agent_core.governance.hashing.definition_hash` (Task 1).
- Produces: `WorkflowEngine.build_steps_from_spec(spec, custom_step_builders=None) -> list[WorkflowStep]` (public), `WorkflowDefinitionRegistry.register_version(spec: WorkflowSpec) -> WorkflowDefinition`, `.get_spec(definition) -> WorkflowSpec`, `.build_steps(definition, engine, custom_step_builders=None) -> list[WorkflowStep]`.

- [ ] **Step 1: Add a public `build_steps_from_spec` method to `WorkflowEngine`, reusing the existing private per-step builder**

In `agentos/workflows/engine.py`, add this method to the `WorkflowEngine` class, directly after `_build_executable_step` (currently ending at line 138):

```python
    def build_steps_from_spec(
        self,
        spec: WorkflowSpec,
        custom_step_builders: Optional[dict[str, Callable[[WorkflowStepSpec], WorkflowStep]]] = None,
    ) -> list[WorkflowStep]:
        """Build danh sách WorkflowStep thực thi được từ 1 WorkflowSpec khai
        báo — public vì WorkflowDefinitionRegistry cần gọi lại đúng logic
        này khi resolve steps cho 1 version đã pin, thay vì tự giữ 1
        Callable Python tách biệt (bug gốc khiến version history và spec
        khai báo không nối với nhau — xem
        COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md)."""
        return [self._build_executable_step(s, custom_step_builders) for s in spec.steps]
```

Then, inside `execute_spec` (currently around line 158-161), replace:

```python
        all_specs: dict[str, WorkflowStepSpec] = {s.id: s for s in spec.steps}
        steps_map: dict[str, WorkflowStep] = {
            s.id: self._build_executable_step(s, custom_step_builders)
            for s in spec.steps
        }
```

with:

```python
        all_specs: dict[str, WorkflowStepSpec] = {s.id: s for s in spec.steps}
        built_steps = self.build_steps_from_spec(spec, custom_step_builders)
        steps_map: dict[str, WorkflowStep] = {s.id: step for s, step in zip(spec.steps, built_steps)}
```

This is a pure refactor — same per-step builder, same iteration order, same result. It removes the duplication between `execute_spec` and the new public method.

- [ ] **Step 2: Run the existing declarative-execution tests to confirm the refactor is behavior-preserving**

Run: `.venv/bin/pytest tests/agentos/workflows/test_dag_engine.py tests/agentos/workflows/test_declarative_yaml.py tests/agentos/workflows/test_workflow_compensation.py tests/agentos/workflows/test_workflow_governance.py tests/agentos/workflows/test_checkpoint_resume.py -v`
Expected: all pass, identical to before the change (no test file touched in this step — this only verifies the Step 1 refactor didn't regress anything)

- [ ] **Step 3: Rewrite `tests/agentos/workflows/test_definition_registry.py` to use `WorkflowSpec` instead of a raw step factory**

Replace the entire contents of `tests/agentos/workflows/test_definition_registry.py` with:

```python
import pytest

from agentos.workflows.definition_registry import (
    WorkflowDefinitionNotFoundError,
    WorkflowDefinitionRegistry,
    WorkflowVersionNotFoundError,
)
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agentos.workflows.steps import DeterministicStep


async def _write_v1(state: dict) -> dict:
    return {"record_id": "rec-v1"}


async def _write_v2(state: dict) -> dict:
    return {"record_id": "rec-v2", "extra_step_ran": True}


async def _notify(state: dict) -> dict:
    return {"notified": True}


def _spec_v1() -> WorkflowSpec:
    return WorkflowSpec(id="send-flow", steps=[WorkflowStepSpec(id="write", type=StepType.DETERMINISTIC)])


def _spec_v2() -> WorkflowSpec:
    return WorkflowSpec(
        id="send-flow",
        steps=[
            WorkflowStepSpec(id="write", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="notify", type=StepType.DETERMINISTIC),
        ],
    )


_BUILDERS_V1 = {"write": lambda step_spec: DeterministicStep(step_spec.id, _write_v1)}
_BUILDERS_V2 = {
    "write": lambda step_spec: DeterministicStep(step_spec.id, _write_v2),
    "notify": lambda step_spec: DeterministicStep(step_spec.id, _notify),
}


def test_register_version_assigns_sequential_version_numbers():
    registry = WorkflowDefinitionRegistry()

    v1 = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert v1.version_no == 1
    assert v2.version_no == 2
    assert v1.id != v2.id


def test_register_version_computes_a_content_addressed_definition_hash():
    registry = WorkflowDefinitionRegistry()

    v1 = registry.register_version(_spec_v1())
    v1_repeat = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert v1.definition_hash == v1_repeat.definition_hash
    assert v1.definition_hash != v2.definition_hash


def test_current_version_returns_the_most_recently_registered_version():
    registry = WorkflowDefinitionRegistry()
    registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert registry.current_version("send-flow") == v2


def test_current_version_raises_when_name_never_registered():
    registry = WorkflowDefinitionRegistry()
    with pytest.raises(WorkflowDefinitionNotFoundError):
        registry.current_version("unknown-flow")


def test_get_version_returns_an_older_immutable_version():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    registry.register_version(_spec_v2())

    assert registry.get_version("send-flow", 1) == v1


def test_get_version_raises_for_unknown_version_number():
    registry = WorkflowDefinitionRegistry()
    registry.register_version(_spec_v1())

    with pytest.raises(WorkflowVersionNotFoundError):
        registry.get_version("send-flow", 99)


def test_history_returns_every_registered_version_in_order():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())

    assert registry.history("send-flow") == [v1, v2]


def test_registering_a_new_version_does_not_mutate_the_previous_one():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    registry.register_version(_spec_v2())

    assert registry.get_version("send-flow", 1) == v1
    assert registry.get_version("send-flow", 1).version_no == 1


def test_get_spec_returns_the_exact_workflow_spec_registered_for_that_version():
    registry = WorkflowDefinitionRegistry()
    spec_v1 = _spec_v1()
    v1 = registry.register_version(spec_v1)

    assert registry.get_spec(v1) == spec_v1


@pytest.mark.asyncio
async def test_build_steps_resolves_the_workflow_spec_for_that_specific_version():
    registry = WorkflowDefinitionRegistry()
    v1 = registry.register_version(_spec_v1())
    v2 = registry.register_version(_spec_v2())
    engine = WorkflowEngine()

    steps_v1 = registry.build_steps(v1, engine, custom_step_builders=_BUILDERS_V1)
    steps_v2 = registry.build_steps(v2, engine, custom_step_builders=_BUILDERS_V2)

    assert [s.name for s in steps_v1] == ["write"]
    assert [s.name for s in steps_v2] == ["write", "notify"]


@pytest.mark.asyncio
async def test_workflow_engine_runs_the_current_version_end_to_end():
    registry = WorkflowDefinitionRegistry()
    registry.register_version(_spec_v1())
    registry.register_version(_spec_v2())

    definition = registry.current_version("send-flow")
    engine = WorkflowEngine()
    steps = registry.build_steps(definition, engine, custom_step_builders=_BUILDERS_V2)

    workflow = await engine.start("send-flow", steps, {})

    assert workflow.status == WorkflowStatus.COMPLETED
    assert workflow.state == {"record_id": "rec-v2", "extra_step_ran": True, "notified": True}


@pytest.mark.asyncio
async def test_resume_uses_the_pinned_version_even_after_a_newer_version_is_published():
    """Bug gốc mà toàn bộ tài liệu governance temporal model xuất phát từ
    đây: nếu resume tự resolve current_version() thay vì dùng definition đã
    pin lúc Run bắt đầu, publish 1 version mới giữa chừng sẽ âm thầm đổi
    hành vi của Run cũ đang chạy dở. Test này bắt đúng lỗi đó."""
    registry = WorkflowDefinitionRegistry()
    pinned = registry.register_version(_spec_v1())
    engine = WorkflowEngine()

    steps_at_start = registry.build_steps(pinned, engine, custom_step_builders=_BUILDERS_V1)
    workflow = await engine.start("send-flow", steps_at_start, {})
    assert workflow.state == {"record_id": "rec-v1"}

    registry.register_version(_spec_v2())  # publish v2 "giữa chừng"

    steps_for_resume = registry.build_steps(pinned, engine, custom_step_builders=_BUILDERS_V1)
    assert [s.name for s in steps_for_resume] == ["write"]
```

- [ ] **Step 4: Run to verify the new tests fail (registry API not yet changed)**

Run: `.venv/bin/pytest tests/agentos/workflows/test_definition_registry.py -v`
Expected: FAIL — `TypeError: register_version() missing 1 required positional argument: 'steps_factory'` (current signature still takes `name, steps_factory`)

- [ ] **Step 5: Rewrite `WorkflowDefinitionRegistry`**

Replace the entire contents of `agentos/workflows/definition_registry.py` with:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from agent_core.governance.hashing import definition_hash
from agentos.workflows.schema import WorkflowSpec, WorkflowStepSpec
from agentos.workflows.steps import WorkflowStep

if TYPE_CHECKING:
    from typing import Callable

    from agentos.workflows.engine import WorkflowEngine


class WorkflowDefinitionNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"No workflow definition registered under name: {name}")
        self.name = name


class WorkflowVersionNotFoundError(Exception):
    def __init__(self, name: str, version_no: int) -> None:
        super().__init__(f"Workflow {name!r} has no version {version_no}")
        self.name = name
        self.version_no = version_no


class WorkflowDefinition(BaseModel):
    """1 phiên bản bất biến của định nghĩa workflow theo tên. Version hoá
    trực tiếp `WorkflowSpec` khai báo (không phải 1 Python callable tách
    biệt như trước) — `definition_hash` pin đúng nội dung thật, phát hiện
    được silent drift nếu 2 lần đăng ký cùng version_no nhưng nội dung
    khác nhau. Xem COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md
    PHẦN I §1 cho lý do đổi thiết kế này."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    version_no: int
    definition_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkflowDefinitionRegistry:
    """Theo dõi version history cho workflow definition theo tên — không
    bao giờ sửa 1 version đã đăng ký (blueprint §12.1 "Never update an
    active skill/workflow in place", áp dụng tương tự cho workflow). Đăng
    ký version mới không xóa version cũ, chỉ đổi "current" sang version mới
    nhất — cho phép truy vấn lại lịch sử hoặc chạy lại 1 version cũ nếu cần
    rollback.
    """

    def __init__(self) -> None:
        self._versions: dict[str, list[WorkflowDefinition]] = {}
        self._specs: dict[str, WorkflowSpec] = {}

    def register_version(self, spec: WorkflowSpec) -> WorkflowDefinition:
        name = spec.id
        history = self._versions.setdefault(name, [])
        definition = WorkflowDefinition(
            name=name,
            version_no=len(history) + 1,
            definition_hash=definition_hash(spec),
        )
        history.append(definition)
        self._specs[definition.id] = spec
        return definition

    def current_version(self, name: str) -> WorkflowDefinition:
        history = self._versions.get(name)
        if not history:
            raise WorkflowDefinitionNotFoundError(name)
        return history[-1]

    def get_version(self, name: str, version_no: int) -> WorkflowDefinition:
        for definition in self._versions.get(name, []):
            if definition.version_no == version_no:
                return definition
        raise WorkflowVersionNotFoundError(name, version_no)

    def history(self, name: str) -> list[WorkflowDefinition]:
        return list(self._versions.get(name, []))

    def get_spec(self, definition: WorkflowDefinition) -> WorkflowSpec:
        return self._specs[definition.id]

    def build_steps(
        self,
        definition: WorkflowDefinition,
        engine: "WorkflowEngine",
        custom_step_builders: Optional[dict[str, "Callable[[WorkflowStepSpec], WorkflowStep]"]] = None,
    ) -> list[WorkflowStep]:
        return engine.build_steps_from_spec(self._specs[definition.id], custom_step_builders)
```

- [ ] **Step 6: Run to verify all tests in the file pass**

Run: `.venv/bin/pytest tests/agentos/workflows/test_definition_registry.py -v`
Expected: 12 passed

- [ ] **Step 7: Run the complete `agentos` workflow test suite to confirm zero regressions**

Run: `.venv/bin/pytest tests/agentos/workflows -v`
Expected: all pass (same pass count as before this task, minus the old `test_definition_registry.py` tests plus the new ones — no failures anywhere else in the directory)

- [ ] **Step 8: Run the full repository verification target**

Run: `make agentos-test && make agent-core-test`
Expected: both pass, 0 failed

- [ ] **Step 9: Commit**

```bash
git add agentos/workflows/engine.py agentos/workflows/definition_registry.py tests/agentos/workflows/test_definition_registry.py
git commit -m "fix(agentos): version WorkflowSpec directly in WorkflowDefinitionRegistry instead of an opaque step factory"
```

---

## Self-review notes (already applied above)

- **Spec coverage**: Every contract named in `COSA_AGENT_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md` Bước 3/4 for the non-DB-dependent slice has a task: `PinnedSpecIdentity`/`SpecResolutionManifest` (Task 2), `PolicyDecision`/`ApprovalRequirement`/`ApprovalEvidence` (Task 3), the `∧` accumulator (Task 4), `InvocationGovernanceState` (Task 5), and the root `WorkflowDefinitionRegistry` bug fix (Task 6). `RunLevelCurrentGate`, durable persistence (Bước 6 tables), `ToolCallStep`/`AgentStep` rewiring, `satisfies()` evidence matching, and the freshness-boundary enforcement are explicitly out of scope for this plan — they depend on decisions this plan will surface during implementation (exact predicate shapes, exact hash algorithm) and on the durable-storage plan (Bước 6) landing first. They become separate plans once this one is merged.
- **Type consistency**: `PolicyDecision`, `ApprovalRequirement` (and its five variants), `combine_decisions`, and `InvocationGovernanceState` use identical field/method names across Tasks 3, 4, and 5 — verified by re-reading each task's Interfaces block against the previous task's Produces line.
- **No placeholders**: every step has literal, runnable code and an exact pytest command with an expected result.

## Next plans (not in scope here — write after this one lands)

1. **Durable persistence (V4 Bước 6)**: SQL migration for `run_pinned_specs`, `invocation_governance_state`, `approval_evidence` tables in `agentos/migrations/`; rewrite `ApprovalService` (agentos/core/approval.py) from in-memory to durable, keeping its existing method signatures.
2. **Call-site rewiring + ADR-014 cutover (V4 Bước 7)**: `ToolCallStep`/`AgentStep` (agentos/workflows/tool_step.py, steps.py) resolve `agent_permission_level`/`execution_mode` from a real `SpecResolutionManifest` instead of hardcoded constructor params, call `evaluate_access()` at each freshness boundary and fold into `InvocationGovernanceState`, and finish replacing `evaluate(PermissionClass)` call sites in `Executor`/`ApprovalGateStep`.
3. **Promotion test suite (V4 Bước 9)**: the 5 test groups listed in Phần II Bước 9 of the governance temporal model doc (durable kill/restart resume, workflow-version-drift under real persistence, AgentSpec widen/narrow, 3-case risk drift, Run-level ambient suspend/resume) — these need Plans 1 and 2 above to exist first.
