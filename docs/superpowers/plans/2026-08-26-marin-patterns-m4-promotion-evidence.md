# COSA Marin Patterns — M4 Promotion Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến "test pass" thành bằng chứng có cấu trúc (`PromotionEvidence`) mà một gate có thể kiểm tra khách quan (stale/dependency drift/eval chưa pass) trước khi bất kỳ ai — người hay hệ thống — quyết định promote 1 artifact lên production.

**Architecture:** `PromotionEvidence` (bất biến) gom `target_ref` (`PinnedSpecIdentity`, Wave M1) + `observed_fingerprints` (target và toàn bộ dependency đã resolve qua `SpecDependencyEdge`/`AgentSpecResolution`, Wave M2) + `required_eval_run_ids` (trỏ tới `EvalRun`, Wave M3) + kết quả policy check. `build_promotion_evidence()` là builder pure-function nối 3 wave lại: nhận `AgentSpecResolution.edges` (M2) + list `EvalRun` (M3) đã chạy, tính fingerprint quan sát + policy_checks_passed. `PromotionGate.check()` chỉ TRẢ VỀ kết quả kiểm tra (`PromotionGateResult`) — không tự activate/promote gì. Persistence là bảng MỚI `agent_evals.promotion_evidence` (không có bảng nào từ trước map được — khác Wave M3, không phải ALTER). Ranh giới kiến trúc: `agent_core` CHỈ tạo evidence + expose read API, `PromotionDecision`/activation thuộc `services/cosa` — viết thành doc tường minh ở Task 6, không code phần đó ở plan này.

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio, PostgreSQL (docker-compose `cosa_postgres`, cùng pattern Task 4 các Wave trước).

## Global Constraints

- **Phụ thuộc cứng vào Wave M3 đã merge trước** (`docs/superpowers/plans/2026-08-26-marin-patterns-m3-eval-artifacts.md`) — Task 2/5 của plan này import `EvalRun`/`EvalRepository` từ `packages/agent_core/evals/artifacts.py`/`repositories.py`. KHÔNG bắt đầu plan này nếu Wave M3 chưa commit xong (`EvalRun` sẽ không tồn tại, import fail ngay).
- Không tạo `ArtifactIdentity`/`ArtifactRef` dataclass mới — dùng `PinnedSpecIdentity`.
- KHÔNG xây `PromotionDecision` hay bất kỳ code nào tự set trạng thái production/activation trong `agent_core` — đó là quyền của `services/cosa` (CLAUDE.md 4 vùng kiến trúc, quyết định người dùng đã chốt từ Wave M0/M1). `PromotionGate.check()` chỉ trả kết quả kiểm tra, không có side effect nào.
- Không chạm `apps/cosa/*`/`services/*` trong plan này — chỉ tài liệu hoá ranh giới (Task 6), không code phía `services/cosa`.
- `required_eval_run_ids`/`observed_fingerprints`/`check_details` lưu dạng JSONB (không dùng Postgres `TEXT[]`) — nhất quán với cách các repository khác trong codebase này lưu list/dict (`json.dumps`/`json.loads` qua raw `text()` SQL), tránh rủi ro binding kiểu mảng Postgres qua SQLAlchemy `text()` không tường minh.
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do; tên định danh giữ tiếng Anh.

---

### Task 1: `PromotionEvidence` contract

**Files:**
- Create: `packages/agent_core/evals/promotion.py`
- Test: `tests/agent_core/evals/test_promotion_evidence.py` (mới)

**Interfaces:**
- Consumes: `PinnedSpecIdentity` (Wave M1, đã có).
- Produces: `PromotionEvidence(evidence_id: str, target_ref: PinnedSpecIdentity, required_eval_run_ids: list[str] = [], observed_fingerprints: dict[str, str] = {}, policy_version: str, policy_checks_passed: bool, check_details: dict[str, Any] = {}, created_at: datetime)` với `is_stale(current_fingerprints: dict[str, str]) -> bool`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/evals/test_promotion_evidence.py` (thư mục `tests/agent_core/evals/` đã tồn tại từ Wave M3 — không cần tạo `__init__.py`):

```python
from __future__ import annotations

from agent_core.evals.promotion import PromotionEvidence
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


def test_promotion_evidence_has_sensible_defaults():
    evidence = PromotionEvidence(target_ref=_target_ref(), policy_version="1", policy_checks_passed=True)

    assert evidence.required_eval_run_ids == []
    assert evidence.observed_fingerprints == {}
    assert evidence.check_details == {}
    assert evidence.evidence_id.startswith("promoevid_")


def test_promotion_evidence_two_instances_get_distinct_ids():
    a = PromotionEvidence(target_ref=_target_ref(), policy_version="1", policy_checks_passed=True)
    b = PromotionEvidence(target_ref=_target_ref(), policy_version="1", policy_checks_passed=True)

    assert a.evidence_id != b.evidence_id


def test_is_stale_returns_false_when_all_fingerprints_match():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64, "cofounder/system": "b" * 64},
    )

    assert evidence.is_stale({"cofounder": "a" * 64, "cofounder/system": "b" * 64}) is False


def test_is_stale_returns_true_when_target_fingerprint_changed():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64},
    )

    assert evidence.is_stale({"cofounder": "c" * 64}) is True


def test_is_stale_returns_true_when_dependency_fingerprint_changed():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64, "cofounder/system": "b" * 64},
    )

    assert evidence.is_stale({"cofounder": "a" * 64, "cofounder/system": "c" * 64}) is True


def test_is_stale_returns_true_when_observed_name_missing_from_current():
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        policy_version="1",
        policy_checks_passed=True,
        observed_fingerprints={"cofounder": "a" * 64, "cofounder/system": "b" * 64},
    )

    assert evidence.is_stale({"cofounder": "a" * 64}) is True
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_evidence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.evals.promotion'`.

- [ ] **Step 3: Viết `PromotionEvidence`**

Tạo `packages/agent_core/evals/promotion.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = ["PromotionEvidence"]


class PromotionEvidence(BaseModel):
    """Bằng chứng bất biến cho quyết định promotion — Wave M4, theo
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md §12.2.
    `agent_core` CHỈ tạo evidence này, KHÔNG tự quyết promote —
    PromotionDecision (quyền activate production) thuộc `services/cosa`, xem
    docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md."""

    evidence_id: str = Field(default_factory=lambda: f"promoevid_{uuid.uuid4().hex[:12]}")
    target_ref: PinnedSpecIdentity
    required_eval_run_ids: list[str] = Field(default_factory=list)
    observed_fingerprints: dict[str, str] = Field(default_factory=dict)
    policy_version: str
    policy_checks_passed: bool
    check_details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, current_fingerprints: dict[str, str]) -> bool:
        """True nếu bất kỳ fingerprint nào (target hoặc dependency) đã quan
        sát tại thời điểm tạo evidence KHÔNG còn khớp fingerprint hiện tại —
        nghĩa là artifact đã đổi sau khi eval pass, evidence không còn tin
        cậy được cho quyết định promote (§12.2 pseudo-invariant
        `evaluated_fingerprint == current_candidate_fingerprint`)."""
        for name, observed_hash in self.observed_fingerprints.items():
            if current_fingerprints.get(name) != observed_hash:
                return True
        return False
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_evidence.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/evals/promotion.py tests/agent_core/evals/test_promotion_evidence.py
git commit -m "feat(evals): add PromotionEvidence with staleness detection"
```

---

### Task 2: `build_promotion_evidence()` — nối AgentSpecResolution (M2) + EvalRun (M3)

**Files:**
- Modify: `packages/agent_core/evals/promotion.py`
- Test: `tests/agent_core/evals/test_promotion_evidence.py`

**Interfaces:**
- Consumes: `SpecDependencyEdge` (`agent_core.governance.contracts`, Wave M1), `EvalRun` (`agent_core.evals.artifacts`, Wave M3 — **PHỤ THUỘC M3 đã merge**).
- Produces: `build_promotion_evidence(*, target_ref: PinnedSpecIdentity, dependency_edges: tuple[SpecDependencyEdge, ...] = (), eval_runs: list[EvalRun], policy_version: str, pass_rate_threshold: float) -> PromotionEvidence`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/evals/test_promotion_evidence.py`:

```python
from agent_core.evals.artifacts import EvalRun
from agent_core.evals.promotion import build_promotion_evidence
from agent_core.governance.contracts import SpecDependencyEdge


def test_build_promotion_evidence_includes_target_and_dependency_fingerprints():
    target_ref = _target_ref()
    dep_ref = PinnedSpecIdentity(
        spec_kind="prompt", spec_id="cofounder/system", spec_version="1", definition_hash="b" * 64
    )
    edge = SpecDependencyEdge(owner=target_ref, dependency=dep_ref, relation="uses_prompt")
    run = EvalRun(target_ref=target_ref, status="completed", pass_rate=1.0)

    evidence = build_promotion_evidence(
        target_ref=target_ref,
        dependency_edges=(edge,),
        eval_runs=[run],
        policy_version="1",
        pass_rate_threshold=0.8,
    )

    assert evidence.observed_fingerprints["cofounder"] == "a" * 64
    assert evidence.observed_fingerprints["cofounder/system"] == "b" * 64
    assert evidence.required_eval_run_ids == [run.run_id]


def test_build_promotion_evidence_passes_when_all_runs_completed_above_threshold():
    target_ref = _target_ref()
    run = EvalRun(target_ref=target_ref, status="completed", pass_rate=0.95)

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[run], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is True


def test_build_promotion_evidence_fails_when_any_run_below_threshold():
    target_ref = _target_ref()
    run = EvalRun(target_ref=target_ref, status="completed", pass_rate=0.5)

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[run], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is False


def test_build_promotion_evidence_fails_when_run_not_completed():
    target_ref = _target_ref()
    run = EvalRun(target_ref=target_ref, status="running", pass_rate=None)

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[run], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is False


def test_build_promotion_evidence_fails_when_no_eval_runs_at_all():
    target_ref = _target_ref()

    evidence = build_promotion_evidence(
        target_ref=target_ref, eval_runs=[], policy_version="1", pass_rate_threshold=0.8
    )

    assert evidence.policy_checks_passed is False
    assert evidence.required_eval_run_ids == []
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_evidence.py -v -k build_promotion_evidence`
Expected: FAIL — `ImportError: cannot import name 'build_promotion_evidence'` (hoặc `ModuleNotFoundError: No module named 'agent_core.evals.artifacts'` nếu Wave M3 chưa merge — nếu vậy STOP, quay lại thực thi Wave M3 trước).

- [ ] **Step 3: Thêm `build_promotion_evidence()`**

Sửa `packages/agent_core/evals/promotion.py` — thêm import đầu file:

```python
from agent_core.evals.artifacts import EvalRun
from agent_core.governance.contracts import PinnedSpecIdentity, SpecDependencyEdge
```

(thay cho `from agent_core.governance.contracts import PinnedSpecIdentity` hiện có), và sửa `__all__` thành `["PromotionEvidence", "build_promotion_evidence"]`.

Thêm hàm vào cuối file:

```python
def build_promotion_evidence(
    *,
    target_ref: PinnedSpecIdentity,
    dependency_edges: tuple[SpecDependencyEdge, ...] = (),
    eval_runs: list[EvalRun],
    policy_version: str,
    pass_rate_threshold: float,
) -> PromotionEvidence:
    """Nối AgentSpecResolution.edges (Wave M2, SpecResolver.resolve_agent_spec_
    dependencies) + danh sách EvalRun đã chạy (Wave M3) thành 1
    PromotionEvidence. `policy_checks_passed` = True chỉ khi CÓ ít nhất 1
    eval_run VÀ toàn bộ đều status="completed" với pass_rate đạt ngưỡng —
    không có eval run nào KHÔNG được coi là "đã kiểm tra"."""
    observed_fingerprints: dict[str, str] = {target_ref.spec_id: target_ref.definition_hash}
    for edge in dependency_edges:
        observed_fingerprints[edge.dependency.spec_id] = edge.dependency.definition_hash

    policy_checks_passed = bool(eval_runs) and all(
        run.status == "completed" and (run.pass_rate or 0.0) >= pass_rate_threshold for run in eval_runs
    )
    check_details: dict[str, Any] = {
        "pass_rate_threshold": pass_rate_threshold,
        "eval_run_statuses": {run.run_id: run.status for run in eval_runs},
        "eval_run_pass_rates": {run.run_id: run.pass_rate for run in eval_runs},
    }

    return PromotionEvidence(
        target_ref=target_ref,
        required_eval_run_ids=[run.run_id for run in eval_runs],
        observed_fingerprints=observed_fingerprints,
        policy_version=policy_version,
        policy_checks_passed=policy_checks_passed,
        check_details=check_details,
    )
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_evidence.py -v`
Expected: 11 PASSED (6 từ Task 1 + 5 mới).

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/evals/promotion.py tests/agent_core/evals/test_promotion_evidence.py
git commit -m "feat(evals): add build_promotion_evidence linking AgentSpecResolution edges and EvalRun"
```

---

### Task 3: `PromotionGate`

**Files:**
- Create: `packages/agent_core/evals/promotion_gate.py`
- Test: `tests/agent_core/evals/test_promotion_gate.py` (mới)

**Interfaces:**
- Consumes: `PromotionEvidence` (Task 1/2).
- Produces: `PromotionGateResult(approved: bool, blocking_issues: list[str] = [], target_ref: PinnedSpecIdentity, evidence_id: str)`; `PromotionGate(policy_version: str)` với `check(evidence: PromotionEvidence, current_fingerprints: dict[str, str]) -> PromotionGateResult`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/evals/test_promotion_gate.py`:

```python
from __future__ import annotations

from agent_core.evals.promotion import PromotionEvidence
from agent_core.evals.promotion_gate import PromotionGate
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


def _valid_evidence() -> PromotionEvidence:
    return PromotionEvidence(
        target_ref=_target_ref(),
        required_eval_run_ids=["evalrun_1"],
        observed_fingerprints={"cofounder": "a" * 64},
        policy_version="1",
        policy_checks_passed=True,
    )


def test_promotion_gate_approves_valid_fresh_evidence():
    gate = PromotionGate(policy_version="1")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is True
    assert result.blocking_issues == []


def test_promotion_gate_rejects_stale_evidence():
    gate = PromotionGate(policy_version="1")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "c" * 64})

    assert result.approved is False
    assert any("stale" in issue.lower() for issue in result.blocking_issues)


def test_promotion_gate_rejects_when_policy_checks_not_passed():
    evidence = _valid_evidence().model_copy(update={"policy_checks_passed": False})
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert any("chưa pass" in issue for issue in result.blocking_issues)


def test_promotion_gate_rejects_when_no_eval_run_ids():
    evidence = _valid_evidence().model_copy(update={"required_eval_run_ids": []})
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False


def test_promotion_gate_rejects_when_policy_version_mismatches():
    gate = PromotionGate(policy_version="2")

    result = gate.check(_valid_evidence(), current_fingerprints={"cofounder": "a" * 64})

    assert result.approved is False
    assert any("policy_version" in issue for issue in result.blocking_issues)


def test_promotion_gate_result_carries_target_ref_and_evidence_id():
    evidence = _valid_evidence()
    gate = PromotionGate(policy_version="1")

    result = gate.check(evidence, current_fingerprints={"cofounder": "a" * 64})

    assert result.target_ref == evidence.target_ref
    assert result.evidence_id == evidence.evidence_id
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.evals.promotion_gate'`.

- [ ] **Step 3: Viết `PromotionGate`**

Tạo `packages/agent_core/evals/promotion_gate.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, Field

from agent_core.evals.promotion import PromotionEvidence
from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = ["PromotionGate", "PromotionGateResult"]


class PromotionGateResult(BaseModel):
    """Kết quả kiểm tra — CHỈ là dữ liệu, không có side effect. Caller
    (services/cosa) tự quyết định làm gì với `approved`/`blocking_issues`."""

    approved: bool
    blocking_issues: list[str] = Field(default_factory=list)
    target_ref: PinnedSpecIdentity
    evidence_id: str


class PromotionGate:
    """Kiểm tra PromotionEvidence có đủ điều kiện promote hay không — CHỈ
    trả kết quả kiểm tra, KHÔNG tự activate/promote gì. Quyền quyết định
    cuối cùng (PromotionDecision) thuộc services/cosa, xem
    docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md."""

    def __init__(self, policy_version: str) -> None:
        self._policy_version = policy_version

    def check(self, evidence: PromotionEvidence, current_fingerprints: dict[str, str]) -> PromotionGateResult:
        issues: list[str] = []

        if evidence.policy_version != self._policy_version:
            issues.append(
                f"Evidence dùng policy_version '{evidence.policy_version}', "
                f"gate hiện yêu cầu '{self._policy_version}'"
            )
        if not evidence.required_eval_run_ids:
            issues.append("Evidence không có eval_run_id nào — chưa từng eval")
        if not evidence.policy_checks_passed:
            issues.append("Eval checks trong evidence chưa pass (policy_checks_passed=False)")
        if evidence.is_stale(current_fingerprints):
            issues.append("Evidence stale — fingerprint (target hoặc dependency) đã đổi kể từ khi tạo evidence")

        return PromotionGateResult(
            approved=len(issues) == 0,
            blocking_issues=issues,
            target_ref=evidence.target_ref,
            evidence_id=evidence.evidence_id,
        )
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_gate.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/evals/promotion_gate.py tests/agent_core/evals/test_promotion_gate.py
git commit -m "feat(evals): add PromotionGate — check-only, no promote side effect"
```

---

### Task 4: Migration `agent_evals.promotion_evidence`

**Files:**
- Create: `packages/agent_core/migrations/014_promotion_evidence.sql`

**Interfaces:** Không có API Python — bảng mới thuần.

- [ ] **Step 1: Viết migration**

Tạo `packages/agent_core/migrations/014_promotion_evidence.sql`:

```sql
-- Migration: 014_promotion_evidence.sql
-- Description: Bảng agent_evals.promotion_evidence — bằng chứng bất biến
--   cho quyết định promotion, Wave M4. Khác 013 (ALTER bảng có sẵn), đây là
--   bảng MỚI vì chưa migration nào trước đó map được khái niệm này.
--
-- Ranh giới sở hữu: packages/agent_core/evals/ ghi bảng này (tạo evidence).
-- PromotionDecision/activation (quyền đổi trạng thái production) KHÔNG có
-- bảng tương ứng ở đây — thuộc services/cosa, xem
-- docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md.

CREATE TABLE IF NOT EXISTS agent_evals.promotion_evidence (
    evidence_id VARCHAR(64) PRIMARY KEY,
    target_kind VARCHAR(32) NOT NULL,
    target_id VARCHAR(128) NOT NULL,
    target_version VARCHAR(32) NOT NULL,
    target_definition_hash VARCHAR(64) NOT NULL,
    required_eval_run_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    observed_fingerprints JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy_version VARCHAR(32) NOT NULL,
    policy_checks_passed BOOLEAN NOT NULL,
    check_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_promotion_evidence_target
    ON agent_evals.promotion_evidence(target_kind, target_id, target_version);
```

- [ ] **Step 2: Đảm bảo Postgres đang chạy**

Run: `docker ps --filter "name=cosa_postgres" --format "{{.Status}}"`
Expected: dòng `Up ... (healthy)`. Nếu không có output, chạy `docker compose up -d postgres` từ `/Volumes/SSD/javis-saas` trước khi tiếp tục.

- [ ] **Step 3: Chạy migration thật**

Run: `cd /Volumes/SSD/javis-saas && export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://javis_app:<mật khẩu thật trong .env DATABASE_URL>@localhost:5432/javis" && ./.venv/bin/python -m packages.agent_core.scripts.migrate`
Expected: log hiển thị `014_promotion_evidence.sql` được áp dụng — yêu cầu `013_eval_suite_run_fingerprints.sql` (Wave M3 Task 4) đã áp dụng trước đó (migration chạy theo thứ tự tên file).

- [ ] **Step 4: Verify bằng psql**

Run: `docker exec cosa_postgres psql -U javis_app -d javis -c "\d agent_evals.promotion_evidence"`
Expected: đủ các cột `evidence_id, target_kind, target_id, target_version, target_definition_hash, required_eval_run_ids, observed_fingerprints, policy_version, policy_checks_passed, check_details, created_at`.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/migrations/014_promotion_evidence.sql
git commit -m "migrate(evals): add agent_evals.promotion_evidence table"
```

---

### Task 5: `PromotionEvidenceRepository`

**Files:**
- Create: `packages/agent_core/evals/promotion_repository.py`
- Test: `tests/agent_core/evals/test_promotion_repository.py` (mới)

**Interfaces:**
- Consumes: `PromotionEvidence` (Task 1/2), `PinnedSpecIdentity`.
- Produces: `PromotionEvidenceRepository` Protocol + `InMemoryPromotionEvidenceRepository` + `PostgresPromotionEvidenceRepository`, mỗi cái có: `create(evidence) -> PromotionEvidence`, `get(evidence_id) -> Optional[PromotionEvidence]`, `list_by_target(target_ref: PinnedSpecIdentity) -> list[PromotionEvidence]`.

- [ ] **Step 1: Viết test thất bại (InMemory trước — Postgres verify ở Step 6)**

Tạo `tests/agent_core/evals/test_promotion_repository.py`:

```python
from __future__ import annotations

import pytest

from agent_core.evals.promotion import PromotionEvidence
from agent_core.evals.promotion_repository import InMemoryPromotionEvidenceRepository
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref(hash_suffix: str = "a") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(
        spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash=hash_suffix * 64
    )


@pytest.mark.asyncio
async def test_create_and_get_evidence_roundtrip():
    repo = InMemoryPromotionEvidenceRepository()
    evidence = PromotionEvidence(
        target_ref=_target_ref(),
        required_eval_run_ids=["evalrun_1"],
        observed_fingerprints={"cofounder": "a" * 64},
        policy_version="1",
        policy_checks_passed=True,
    )

    created = await repo.create(evidence)
    fetched = await repo.get(created.evidence_id)

    assert fetched is not None
    assert fetched.evidence_id == created.evidence_id
    assert fetched.observed_fingerprints == {"cofounder": "a" * 64}


@pytest.mark.asyncio
async def test_get_returns_none_when_not_found():
    repo = InMemoryPromotionEvidenceRepository()

    result = await repo.get("does_not_exist")

    assert result is None


@pytest.mark.asyncio
async def test_list_by_target_returns_only_matching_target():
    repo = InMemoryPromotionEvidenceRepository()
    matching = PromotionEvidence(target_ref=_target_ref("a"), policy_version="1", policy_checks_passed=True)
    other = PromotionEvidence(target_ref=_target_ref("f"), policy_version="1", policy_checks_passed=True)
    await repo.create(matching)
    await repo.create(other)

    results = await repo.list_by_target(_target_ref("a"))

    assert len(results) == 1
    assert results[0].evidence_id == matching.evidence_id
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.evals.promotion_repository'`.

- [ ] **Step 3: Viết `PromotionEvidenceRepository` (Protocol + InMemory + Postgres)**

Tạo `packages/agent_core/evals/promotion_repository.py`:

```python
from __future__ import annotations

import json
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.evals.promotion import PromotionEvidence
from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = [
    "PromotionEvidenceRepository",
    "InMemoryPromotionEvidenceRepository",
    "PostgresPromotionEvidenceRepository",
]


@runtime_checkable
class PromotionEvidenceRepository(Protocol):
    """Protocol cho persistence PromotionEvidence (agent_evals.
    promotion_evidence, migration 014, Wave M4)."""

    async def create(self, evidence: PromotionEvidence) -> PromotionEvidence: ...
    async def get(self, evidence_id: str) -> Optional[PromotionEvidence]: ...
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

    async def get(self, evidence_id: str) -> Optional[PromotionEvidence]:
        r = self._evidence.get(evidence_id)
        return r.model_copy(deep=True) if r else None

    async def list_by_target(self, target_ref: PinnedSpecIdentity) -> list[PromotionEvidence]:
        return [
            e.model_copy(deep=True)
            for e in self._evidence.values()
            if e.target_ref == target_ref
        ]


class PostgresPromotionEvidenceRepository:
    """PostgreSQL implementation — persist vào agent_evals.promotion_evidence
    (migration 014)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresPromotionEvidenceRepository requires a valid db_session_factory.")
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

    async def get(self, evidence_id: str) -> Optional[PromotionEvidence]:
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
```

- [ ] **Step 4: Chạy lại test InMemory, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_repository.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Đảm bảo migration 014 (Task 4) đã apply**

Run: `docker exec cosa_postgres psql -U javis_app -d javis -c "\d agent_evals.promotion_evidence"`
Expected: bảng tồn tại. Nếu không, chạy lại Task 4 Step 3 trước khi tiếp tục.

- [ ] **Step 6: Viết + chạy test Postgres thật**

Thêm vào cuối `tests/agent_core/evals/test_promotion_repository.py`:

```python
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.evals.promotion_repository import PostgresPromotionEvidenceRepository


def _pg_session_factory():
    url = os.environ.get(
        "AGENT_CORE_DATABASE_URL",
        "postgresql+asyncpg://javis_app:CHANGE_ME@localhost:5432/javis",
    )
    engine = create_async_engine(url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_postgres_promotion_evidence_repository_roundtrip():
    repo = PostgresPromotionEvidenceRepository(_pg_session_factory())
    evidence = PromotionEvidence(
        target_ref=_target_ref("d"),
        required_eval_run_ids=["evalrun_pg_1"],
        observed_fingerprints={"cofounder": "d" * 64},
        policy_version="1",
        policy_checks_passed=True,
        check_details={"pass_rate_threshold": 0.8},
    )

    created = await repo.create(evidence)
    fetched = await repo.get(created.evidence_id)
    listed = await repo.list_by_target(_target_ref("d"))

    assert fetched is not None
    assert fetched.observed_fingerprints == {"cofounder": "d" * 64}
    assert fetched.required_eval_run_ids == ["evalrun_pg_1"]
    assert any(e.evidence_id == created.evidence_id for e in listed)
```

Run: `cd /Volumes/SSD/javis-saas && export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://javis_app:<mật khẩu thật>@localhost:5432/javis" && ./.venv/bin/python -m pytest tests/agent_core/evals/test_promotion_repository.py -v`
Expected: 4 PASSED (3 InMemory + 1 Postgres).

- [ ] **Step 7: Commit**

```bash
git add packages/agent_core/evals/promotion_repository.py tests/agent_core/evals/test_promotion_repository.py
git commit -m "feat(evals): add PromotionEvidenceRepository (InMemory + Postgres)"
```

---

### Task 6: Tài liệu ranh giới Control Plane

**Files:**
- Create: `docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md`

**Interfaces:** Không có API Python — tài liệu thuần.

- [ ] **Step 1: Viết tài liệu**

Tạo `docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md`:

```markdown
# M4 — Ranh giới Promotion giữa agent_core và services/cosa

**Ngày:** 2026-08-26
**Nguồn:** Wave M4 (`docs/superpowers/plans/2026-08-26-marin-patterns-m4-promotion-evidence.md`), theo
`COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` §12.3 và CLAUDE.md
"Bốn vùng kiến trúc".

## Quyết định

`packages/agent_core/evals/` (Wave M4) sở hữu:

- `PromotionEvidence` — bằng chứng bất biến (target ref + fingerprint quan sát + eval run refs + policy check result).
- `PromotionGate.check()` — hàm THUẦN kiểm tra (stale/dependency drift/eval chưa pass), trả `PromotionGateResult`, KHÔNG side effect.
- `PromotionEvidenceRepository` — persistence CHO evidence (`agent_evals.promotion_evidence`, migration 014).

`agent_core` **KHÔNG** sở hữu và **KHÔNG BAO GIỜ** tự triển khai:

- `PromotionDecision` — bản ghi quyền quyết định "artifact X@version Y được phép chạy production" — đây là business/platform authority, thuộc `services/cosa` (đã chốt từ ADR-CONTROLPLANE-001, CLAUDE.md rule 1: "Business truth thuộc `services/*`, không thuộc LLM runtime / Agent Platform").
- Activation/deployment record — việc AgentSpec nào đang thật sự phục vụ traffic production.
- Bất kỳ code nào tự động set trạng thái "promoted"/"active" dựa trên `PromotionGateResult.approved == True` — `approved=True` chỉ là 1 input cho quyết định của `services/cosa`, không phải quyết định tự nó.

## Luồng dự kiến (services/cosa gọi vào agent_core, KHÔNG phải chiều ngược lại)

```text
services/cosa nhận yêu cầu promote (người dùng/API)
   │
   ▼
Query agent_core: PromotionEvidenceRepository.list_by_target(target_ref)
   │
   ▼
Query agent_core: PromotionGate(policy_version).check(evidence, current_fingerprints)
   │
   ├── approved == False → services/cosa từ chối, trả blocking_issues cho người dùng
   │
   └── approved == True
          │
          ▼
   services/cosa TỰ QUYẾT: ghi PromotionDecision (bảng của services/cosa, KHÔNG phải
   agent_evals.*), gọi activation logic riêng của nó — code này KHÔNG nằm trong
   agent_core, không nằm trong phạm vi Wave M4.
```

`current_fingerprints` mà `services/cosa` truyền vào `PromotionGate.check()` phải tự tính
tại thời điểm gọi (vd qua `SpecResolver.resolve_agent_spec_dependencies()`, Wave M2, để lấy
fingerprint MỚI NHẤT của target + dependency) — KHÔNG dùng lại `observed_fingerprints` đã
lưu sẵn trong evidence (đó là "lúc xưa", không phải "bây giờ") cho tham số này.

## Vì sao ranh giới này quan trọng

- **Compliance/audit**: 1 quyết định "đưa gì lên production" phải truy vết được về đúng 1
  bản ghi thuộc hệ thống ghi nhận business truth (`services/cosa`), không rải rác trong
  Python runtime state của `agent_core` (có thể restart, có nhiều instance chạy song song).
- **Không để LLM/agent runtime tự cấp quyền cho chính nó** — nếu `agent_core` tự activate
  dựa trên `PromotionGateResult`, một agent chạy trong chính runtime đó (vd Skill Optimization
  Lab) về lý thuyết có đường trực tiếp tới production mà không qua approval con người/business
  policy thật — vi phạm CLAUDE.md rule 5/8.

## Trạng thái triển khai

- `agent_core` phía (Task 1-5, Wave M4): **triển khai xong** khi plan
  `2026-08-26-marin-patterns-m4-promotion-evidence.md` hoàn tất.
- `services/cosa` phía (query evidence, ghi PromotionDecision, activation): **CHƯA triển
  khai** — không nằm trong phạm vi Marin Patterns addendum hiện tại, cần plan riêng khi có
  yêu cầu cụ thể (API nào expose evidence-query, schema PromotionDecision trong
  `services/cosa`, UI/flow người dùng bấm "promote").
```

- [ ] **Step 2: Commit**

```bash
git add docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md
git commit -m "docs(evals): document agent_core/services-cosa promotion boundary"
```

---

## Sau khi hoàn thành plan này

Wave M4 (phần agent_core) xong khi cả 6 task trên commit và `AGENT_CORE_DATABASE_URL=... ./.venv/bin/python -m pytest tests/agent_core/ -v` xanh toàn bộ. Toàn bộ Marin Patterns Wave M0-M4 (agent_core-only, không tính M2b runtime wiring đã xong ở `apps/cosa`) hoàn tất. Việc còn lại ngoài phạm vi:

- **`services/cosa` phía promotion** — query evidence + ghi `PromotionDecision` + activation, theo đúng ranh giới Task 6 đã tài liệu hoá. Cần plan riêng, TypeScript/Encore, khác hoàn toàn stack Python của các plan trước.
- **Wave M5 (Offline DAG)** — theo `docs/implementation/marin-patterns-adjusted-plan.md`, chỉ nên bắt đầu sau khi audit `packages/agent_core/workflows/engine.py` xác nhận có đủ năng lực tái dùng làm offline eval/build DAG hay không (nguyên tắc "reuse trước, build sau" — chưa audit trong phạm vi các plan M0-M4 đã có).

Không tự ý mở rộng phạm vi task hiện tại sang các mục trên khi thực thi plan này.
