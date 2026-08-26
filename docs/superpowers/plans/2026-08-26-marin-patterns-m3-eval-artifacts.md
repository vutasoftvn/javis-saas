# COSA Marin Patterns — M3 Eval Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến `EvalSuite`/`EvalRun`/`EvalCaseResult` thành reproducible evidence có version + fingerprint + exact target/suite reference + persistence thật — hoàn thành phần agent_core-only của Wave M3 (`docs/implementation/marin-patterns-adjusted-plan.md`).

**Architecture:** `EvalSuite` theo đúng pattern `PromptSpec`/`ModelPolicySpec` đã có (Wave M2): `compute_hash()`/`with_hash()`/`to_pinned_identity() -> PinnedSpecIdentity` (spec_kind="eval_suite", mở rộng thêm ở Task 1 — chỉ mở rộng Python Literal, KHÔNG đụng CHECK constraint của `spec_resolution_manifest_entries` vì eval artifact không đi qua bảng đó, đúng ADR-ARTIFACT-IDENTITY-001 §2.4). `EvalRun.target_ref`/`suite_ref` đều là `PinnedSpecIdentity` — `suite_ref` là `Optional` vì Skill Optimization Lab chạy eval ad-hoc theo case list truyền trực tiếp, không phải lúc nào cũng có 1 `EvalSuite` đã publish đứng sau. Persistence mở rộng schema `agent_evals.*` đã có từ trước (migration 008) thay vì tạo bảng mới — chỉ thêm cột version/fingerprint còn thiếu. Không tạo `EvalCaseSet` riêng (case list chỉ tham chiếu qua `case_ids: list[str]`, KHÔNG persist nội dung case trong plan này — case content đã có bảng `agent_evals.cases` từ migration 008 nhưng việc publish case vào đó nằm ngoài phạm vi plan này, dùng ID tham chiếu là đủ cho fingerprint/lineage).

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio, PostgreSQL (asyncpg + SQLAlchemy async qua docker-compose `cosa_postgres` cho Task 4, giống pattern đã dùng ở Wave M0/M1 Task 4).

## Global Constraints

- Không tạo `ArtifactIdentity`/`ArtifactRef` dataclass mới — dùng `PinnedSpecIdentity` (`packages/agent_core/governance/contracts.py`).
- Không tạo bảng DB mới cho suite/run/result — chỉ `ALTER TABLE` mở rộng `agent_evals.suites`/`agent_evals.runs`/`agent_evals.skill_mutations` (migration 008, đã có sẵn từ trước) bằng migration MỚI (013 — bất biến, không sửa 008).
- KHÔNG xây `PromotionDecision`/`PromotionEvidence`/promotion authority trong plan này — đó là Wave M4, agent_core chỉ tạo evidence, không tự quyết promote (quyết định người dùng đã chốt).
- Class mới đặt trong `packages/agent_core/evals/artifacts.py` (file mới) — KHÔNG đặt trùng tên với `packages/agent_core/evals/models.py` đã có (`EvalCategory`/`EvalTestCase`/`EvalResult`/`EvalSuiteSummary` — đó là domain "4 nhóm eval nền tảng platform conformance" khác hoàn toàn, không đụng). Kết quả per-case đặt tên `EvalCaseResult` (không phải `EvalResult`) để tránh trùng tên khi cả 2 module cùng export qua `agent_core.evals`.
- Case định nghĩa (`EvalCase`: input_payload/expected_outcome/is_holdout) TÁI DÙNG `agent_core.skills.lab.models.EvalCase` đã có — không tạo `EvalCase` thứ hai.
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do; tên định danh giữ tiếng Anh.
- Không chạm `apps/cosa/*`/`services/*` trong plan này.

---

### Task 1: Mở rộng `PinnedSpecIdentity.spec_kind` thêm `"eval_suite"`

**Files:**
- Modify: `packages/agent_core/governance/contracts.py`
- Test: `tests/agent_core/governance/test_contracts.py`

**Interfaces:**
- Produces: `PinnedSpecIdentity.spec_kind` chấp nhận thêm `"eval_suite"` — Literal đầy đủ: `["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract", "eval_suite"]`.

- [x] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/governance/test_contracts.py`:

```python
def test_pinned_spec_identity_accepts_eval_suite_kind():
    identity = PinnedSpecIdentity(
        spec_kind="eval_suite", spec_id="cofounder-core", spec_version="24", definition_hash="a" * 64
    )
    assert identity.spec_kind == "eval_suite"
```

(File này đã import `PinnedSpecIdentity` và `pytest`/`ValidationError` từ Wave M0/M1 Task 3 — không cần thêm import mới.)

- [x] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/governance/test_contracts.py -v -k eval_suite_kind`
Expected: FAIL — `pydantic.ValidationError`.

- [x] **Step 3: Sửa `PinnedSpecIdentity.spec_kind`**

Trong `packages/agent_core/governance/contracts.py`, sửa dòng khai báo field (hiện tại: `spec_kind: Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract"]`) thành:

```python
    spec_kind: Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract", "eval_suite"]
```

Cập nhật docstring class, thêm 1 câu: `EvalSuite` (Wave M3) dùng `spec_kind="eval_suite"` nhưng KHÔNG bao giờ ghi vào `SpecResolutionManifest`/`agent_core_governance.spec_resolution_manifest_entries` (bảng đó chỉ dành cho identity một *Run* đã resolve — eval là offline artifact, không phải runtime resolution) — vì vậy KHÔNG cần mở rộng CHECK constraint của bảng đó, khác với `"skill"/"prompt"/"model_policy"/"tool_contract"` đã mở rộng ở Wave M1 (đúng ADR-ARTIFACT-IDENTITY-001 §2.4).

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/governance/test_contracts.py -v`
Expected: tất cả PASS.

- [x] **Step 5: Chạy toàn bộ `tests/agent_core/governance/ tests/agent_core/contracts/ tests/agent_core/registry/` để xác nhận không phá vỡ consumer khác**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/governance/ tests/agent_core/contracts/ tests/agent_core/registry/ -v`
Expected: tất cả PASS.

- [x] **Step 6: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_contracts.py
git commit -m "feat(governance): widen PinnedSpecIdentity.spec_kind to eval_suite"
```

---

### Task 2: `EvalSuite` contract

**Files:**
- Create: `packages/agent_core/evals/artifacts.py`
- Modify: `packages/agent_core/evals/__init__.py` (thêm export)
- Test: `tests/agent_core/evals/test_eval_suite.py` (mới — tạo `tests/agent_core/evals/__init__.py` nếu thư mục chưa là package; kiểm tra bằng `ls tests/agent_core/evals/` trước)

**Interfaces:**
- Consumes: `PinnedSpecIdentity` (Task 1, đã mở rộng `eval_suite`).
- Produces: `EvalSuite(id: str, version: str = "1.0.0", target_kind: str, target_id: str, name: str = "", case_ids: list[str] = [], scorer_version: str = "1.0", pass_thresholds: dict[str, float] = {}, description: str = "", metadata: dict = {}, definition_hash: Optional[str] = None)` với `compute_hash()`, `with_hash()`, `to_pinned_identity() -> PinnedSpecIdentity`.

- [x] **Step 1: Kiểm tra layout test hiện có**

Run: `ls /Volumes/SSD/javis-saas/tests/agent_core/evals/ 2>/dev/null || echo "not found"`

Nếu chưa tồn tại, tạo `tests/agent_core/evals/__init__.py` rỗng.

- [x] **Step 2: Viết test thất bại**

Tạo `tests/agent_core/evals/test_eval_suite.py`:

```python
from __future__ import annotations

from agent_core.evals.artifacts import EvalSuite
from agent_core.governance.contracts import PinnedSpecIdentity


def test_eval_suite_has_sensible_defaults():
    suite = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder")

    assert suite.version == "1.0.0"
    assert suite.case_ids == []
    assert suite.scorer_version == "1.0"
    assert suite.definition_hash is None


def test_eval_suite_compute_hash_is_deterministic():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])

    assert a.compute_hash() == b.compute_hash()


def test_eval_suite_compute_hash_ignores_case_ids_order():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c2", "c1"])

    assert a.compute_hash() == b.compute_hash()


def test_eval_suite_compute_hash_changes_when_case_ids_change():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1"])
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", case_ids=["c1", "c2"])

    assert a.compute_hash() != b.compute_hash()


def test_eval_suite_compute_hash_changes_when_scorer_version_changes():
    a = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", scorer_version="1.0")
    b = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder", scorer_version="2.0")

    assert a.compute_hash() != b.compute_hash()


def test_eval_suite_with_hash_returns_a_copy_with_definition_hash_set():
    suite = EvalSuite(id="cofounder-core", target_kind="agent", target_id="cofounder")

    pinned = suite.with_hash()

    assert suite.definition_hash is None
    assert pinned.definition_hash == suite.compute_hash()


def test_eval_suite_to_pinned_identity_uses_eval_suite_kind():
    suite = EvalSuite(id="cofounder-core", version="24", target_kind="agent", target_id="cofounder").with_hash()

    identity = suite.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="eval_suite", spec_id="cofounder-core", spec_version="24", definition_hash=suite.definition_hash
    )
```

- [x] **Step 3: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_eval_suite.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.evals.artifacts'`.

- [x] **Step 4: Viết `EvalSuite`**

Tạo `packages/agent_core/evals/artifacts.py`:

```python
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["EvalSuite"]


class EvalSuite(BaseModel):
    """Đặc tả eval suite có thể publish/pin độc lập — theo
    ADR-ARTIFACT-IDENTITY-001 (spec_kind="eval_suite", Wave M3). `case_ids`
    chỉ tham chiếu ID case đã có trong `agent_evals.cases` (migration 008),
    KHÔNG persist nội dung case ở đây — publish case là việc ngoài phạm vi
    Wave M3 này. Fingerprint bao gồm case_ids (không phân biệt thứ tự —
    một suite là 1 TẬP case, đổi thứ tự không đổi ý nghĩa) + scorer_version +
    pass_thresholds — loại trừ runtime execution context (worker/region/...)."""

    id: str
    version: str = "1.0.0"
    target_kind: str  # "agent" | "skill" | "workflow" — khớp agent_evals.suites.target_kind
    target_id: str
    name: str = ""
    case_ids: list[str] = Field(default_factory=list)
    scorer_version: str = "1.0"
    pass_thresholds: dict[str, float] = Field(default_factory=dict)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá — case_ids được sort để đảm bảo thứ tự
        không ảnh hưởng fingerprint (unordered set semantics)."""
        data = self.model_dump(exclude={"definition_hash"})
        data["case_ids"] = sorted(data["case_ids"])
        return definition_hash(data)

    def with_hash(self) -> "EvalSuite":
        """Trả về bản sao của EvalSuite đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào EvalRun.suite_ref."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="eval_suite",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
```

Sau đó mở `packages/agent_core/evals/__init__.py`, thêm:

```python
from agent_core.evals.artifacts import EvalSuite
```

(đặt trước dòng `from agent_core.evals.models import (...)`, giữ thứ tự alphabet theo module path: `artifacts` < `models` < `runner`), và thêm `"EvalSuite",` vào `__all__` (giữ thứ tự alphabet, sau `"CanonicalEvalRunner"`, trước `"EvalCategory"`).

- [x] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_eval_suite.py -v`
Expected: 7 PASSED.

- [x] **Step 6: Chạy `tests/agent_core/evals/ tests/agent_core/p1/test_evals_suite.py` để xác nhận `__init__.py` không vỡ import cũ**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/ tests/agent_core/p1/test_evals_suite.py -v`
Expected: tất cả PASS.

- [x] **Step 7: Commit**

```bash
git add packages/agent_core/evals/artifacts.py packages/agent_core/evals/__init__.py tests/agent_core/evals/
git commit -m "feat(evals): add EvalSuite as a pinnable, publishable artifact"
```

---

### Task 3: `EvalRun` + `EvalCaseResult` contracts

**Files:**
- Modify: `packages/agent_core/evals/artifacts.py`
- Modify: `packages/agent_core/evals/__init__.py`
- Test: `tests/agent_core/evals/test_eval_run.py` (mới)

**Interfaces:**
- Consumes: `PinnedSpecIdentity` (đã có), `EvalSuite.to_pinned_identity()` (Task 2).
- Produces: `EvalRun(run_id: str, target_ref: PinnedSpecIdentity, suite_ref: Optional[PinnedSpecIdentity] = None, status: str = "running", pass_rate: Optional[float] = None, started_at: datetime, completed_at: Optional[datetime] = None)`; `EvalCaseResult(result_id: str, eval_run_id: str, case_id: str, passed: bool, score: float = 0.0, details: str = "", error: Optional[str] = None, evaluated_at: datetime)`.

- [x] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/evals/test_eval_run.py`:

```python
from __future__ import annotations

from agent_core.evals.artifacts import EvalCaseResult, EvalRun
from agent_core.governance.contracts import PinnedSpecIdentity


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


def test_eval_run_defaults_to_running_status_and_no_suite_ref():
    run = EvalRun(target_ref=_target_ref())

    assert run.status == "running"
    assert run.suite_ref is None
    assert run.pass_rate is None
    assert run.run_id.startswith("evalrun_")


def test_eval_run_accepts_optional_suite_ref():
    suite_ref = PinnedSpecIdentity(
        spec_kind="eval_suite", spec_id="cofounder-core", spec_version="24", definition_hash="b" * 64
    )

    run = EvalRun(target_ref=_target_ref(), suite_ref=suite_ref)

    assert run.suite_ref == suite_ref


def test_eval_run_two_instances_get_distinct_run_ids():
    a = EvalRun(target_ref=_target_ref())
    b = EvalRun(target_ref=_target_ref())

    assert a.run_id != b.run_id


def test_eval_case_result_holds_run_and_case_reference():
    result = EvalCaseResult(eval_run_id="evalrun_abc123", case_id="case_1", passed=True, score=1.0)

    assert result.eval_run_id == "evalrun_abc123"
    assert result.case_id == "case_1"
    assert result.passed is True
    assert result.result_id.startswith("evalresult_")


def test_eval_case_result_defaults_error_to_none():
    result = EvalCaseResult(eval_run_id="evalrun_abc123", case_id="case_1", passed=False, score=0.0)

    assert result.error is None
```

- [x] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_eval_run.py -v`
Expected: FAIL — `ImportError: cannot import name 'EvalRun'`.

- [x] **Step 3: Thêm `EvalRun`/`EvalCaseResult` vào `packages/agent_core/evals/artifacts.py`**

Sửa import đầu file (thêm `uuid` và `datetime`):

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["EvalSuite", "EvalRun", "EvalCaseResult"]
```

Thêm 2 class vào cuối file (sau `EvalSuite`):

```python
class EvalRun(BaseModel):
    """Một lần thực thi eval — khác `EvalSuite` (định nghĩa tái dùng được) ở
    chỗ EvalRun là execution instance. `suite_ref` là Optional vì Skill
    Optimization Lab (Wave M3 Task 6) chạy eval ad-hoc theo case list truyền
    trực tiếp vào `optimize()`, không phải lúc nào cũng gắn với 1 EvalSuite
    đã publish — chỉ suite thật (dùng cho promotion evidence, Wave M4) mới
    có suite_ref khác None."""

    run_id: str = Field(default_factory=lambda: f"evalrun_{uuid.uuid4().hex[:12]}")
    target_ref: PinnedSpecIdentity
    suite_ref: Optional[PinnedSpecIdentity] = None
    status: str = "running"  # running | completed | failed
    pass_rate: Optional[float] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class EvalCaseResult(BaseModel):
    """Kết quả 1 case trong 1 EvalRun — đặt tên khác `EvalResult`
    (agent_core.evals.models, domain platform-conformance khác) để tránh
    trùng khi cùng export qua `agent_core.evals`."""

    result_id: str = Field(default_factory=lambda: f"evalresult_{uuid.uuid4().hex[:12]}")
    eval_run_id: str
    case_id: str
    passed: bool
    score: float = 0.0
    details: str = ""
    error: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Sửa `packages/agent_core/evals/__init__.py`, đổi dòng:

```python
from agent_core.evals.artifacts import EvalSuite
```

thành:

```python
from agent_core.evals.artifacts import EvalCaseResult, EvalRun, EvalSuite
```

và thêm `"EvalCaseResult",`, `"EvalRun",` vào `__all__` (giữ thứ tự alphabet: `EvalCaseResult` < `EvalCategory` < `EvalResult` < `EvalRun` < `EvalSuite` < `EvalSuiteSummary` < `EvalTestCase`).

- [x] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_eval_run.py -v`
Expected: 5 PASSED.

- [x] **Step 5: Chạy toàn bộ `tests/agent_core/evals/`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/ -v`
Expected: tất cả PASS.

- [x] **Step 6: Commit**

```bash
git add packages/agent_core/evals/artifacts.py packages/agent_core/evals/__init__.py tests/agent_core/evals/test_eval_run.py
git commit -m "feat(evals): add EvalRun and EvalCaseResult artifacts"
```

---

### Task 4: Migration mở rộng `agent_evals.*`

**Files:**
- Create: `packages/agent_core/migrations/013_eval_suite_run_fingerprints.sql`

**Interfaces:** Không có API Python — thay đổi DB schema thuần.

- [x] **Step 1: Viết migration**

Tạo `packages/agent_core/migrations/013_eval_suite_run_fingerprints.sql`:

```sql
-- Migration: 013_eval_suite_run_fingerprints.sql
-- Description: Mở rộng agent_evals.suites/runs/skill_mutations (migration
--   008) để hỗ trợ EvalSuite version+fingerprint, EvalRun suite_ref
--   fingerprint, và Skill Optimization Lab eval_run_id lineage —
--   Wave M3 (ADR-ARTIFACT-IDENTITY-001, docs/implementation/
--   marin-patterns-adjusted-plan.md).
--
-- 008_agent_evals.sql đã apply là bất biến — không sửa file đó, ALTER bằng
-- migration mới này thay vào đó.

ALTER TABLE agent_evals.suites
    ADD COLUMN IF NOT EXISTS version VARCHAR(32) NOT NULL DEFAULT '1.0.0';

ALTER TABLE agent_evals.suites
    ADD COLUMN IF NOT EXISTS definition_hash VARCHAR(64);

-- `suites` hiện chỉ có suite_id/name/target_kind/target_id/description —
-- KHÔNG đủ để tái tạo đầy đủ EvalSuite (thiếu case_ids/scorer_version/
-- pass_thresholds/metadata). Thêm content JSONB để lưu snapshot đầy đủ tại
-- thời điểm publish — cùng pattern agent_registry.published_specs.content
-- (migration 007) đã dùng cho AgentSpec/PromptSpec/ModelPolicySpec.
ALTER TABLE agent_evals.suites
    ADD COLUMN IF NOT EXISTS content JSONB;

ALTER TABLE agent_evals.runs
    ADD COLUMN IF NOT EXISTS suite_version VARCHAR(32);

ALTER TABLE agent_evals.runs
    ADD COLUMN IF NOT EXISTS suite_definition_hash VARCHAR(64);

-- `runs.suite_id` hiện là NOT NULL FK bắt buộc trỏ tới agent_evals.suites —
-- xung đột với EvalRun.suite_ref là Optional (Task 3): Skill Optimization
-- Lab tạo EvalRun ad-hoc (suite_ref=None, không gắn EvalSuite đã publish).
-- Bỏ NOT NULL + bỏ FK — sau thay đổi này, `suite_id` trở thành cột mô tả
-- thuần (lưu suite logical id khi có), CÙNG kiểu với `target_kind`/
-- `target_id`/`target_version`/`target_definition_hash` ở 4 dòng trên vốn
-- cũng KHÔNG có FK — nhất quán trong cùng bảng, exact identity đã được đảm
-- bảo qua `suite_version`+`suite_definition_hash` (2 cột mới ở trên), không
-- cần FK để xác thực. Tên constraint chuẩn Postgres cho REFERENCES khai báo
-- inline là `<table>_<column>_fkey` — dùng `IF EXISTS` nên an toàn dù tên
-- thật khác (không lỗi nếu constraint không tồn tại với tên đó).
ALTER TABLE agent_evals.runs
    DROP CONSTRAINT IF EXISTS runs_suite_id_fkey;

ALTER TABLE agent_evals.runs
    ALTER COLUMN suite_id DROP NOT NULL;

-- Wire Skill Optimization Lab eval evidence lineage — SkillMutationRecord
-- (packages/agent_core/skills/lab/models.py) giờ có thể tham chiếu đúng
-- EvalRun đã tạo cho round mutation đó (Wave M3 Task 6).
ALTER TABLE agent_evals.skill_mutations
    ADD COLUMN IF NOT EXISTS eval_run_id VARCHAR(64);
```

- [x] **Step 2: Đảm bảo Postgres đang chạy**

Run: `docker ps --filter "name=cosa_postgres" --format "{{.Status}}"`
Expected: dòng `Up ... (healthy)`. Nếu không có output, chạy `docker compose up -d postgres` từ `/Volumes/SSD/javis-saas` trước khi tiếp tục (container `cosa_postgres` đã được set up từ Wave M0/M1 Task 4 — port `127.0.0.1:5432`, credential trong `.env` gốc `DATABASE_URL=postgresql://javis_app:<password>@postgres:5432/javis`, dùng `localhost` thay `postgres` khi kết nối từ host).

- [x] **Step 3: Chạy migration thật**

Run: `cd /Volumes/SSD/javis-saas && export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://javis_app:<mật khẩu thật trong .env DATABASE_URL>@localhost:5432/javis" && ./.venv/bin/python -m packages.agent_core.scripts.migrate`
Expected: log hiển thị `013_eval_suite_run_fingerprints.sql` được áp dụng.

- [x] **Step 4: Verify bằng psql**

Run:
```bash
docker exec cosa_postgres psql -U javis_app -d javis -c "\d agent_evals.suites"
docker exec cosa_postgres psql -U javis_app -d javis -c "\d agent_evals.runs"
docker exec cosa_postgres psql -U javis_app -d javis -c "\d agent_evals.skill_mutations"
```
Expected: `agent_evals.suites` có cột `version`/`definition_hash`/`content`; `agent_evals.runs` có `suite_version`/`suite_definition_hash`, cột `suite_id` KHÔNG còn `not null`, và phần "Foreign-key constraints" KHÔNG còn dòng nào tham chiếu `agent_evals.suites` cho `suite_id` (nếu vẫn còn — tên constraint thật khác `runs_suite_id_fkey` — đọc tên chính xác từ output rồi thêm 1 dòng `ALTER TABLE agent_evals.runs DROP CONSTRAINT IF EXISTS <tên_thật>;` vào CUỐI file migration 013 đã tạo ở Step 1, chạy lại Step 3; KHÔNG sửa nội dung đã có trong file, chỉ thêm dòng mới — file migration chưa commit nên vẫn sửa được tự do ở giai đoạn này); `agent_evals.skill_mutations` có `eval_run_id`.

- [x] **Step 5: Commit**

```bash
git add packages/agent_core/migrations/013_eval_suite_run_fingerprints.sql
git commit -m "migrate(evals): add version/fingerprint columns to agent_evals.suites/runs/skill_mutations"
```

---

### Task 5: `EvalRepository` — persistence cho Suite/Run/CaseResult

**Files:**
- Create: `packages/agent_core/evals/repositories.py`
- Test: `tests/agent_core/evals/test_repositories.py` (mới)

**Interfaces:**
- Consumes: `EvalSuite`/`EvalRun`/`EvalCaseResult` (Task 2/3), `SpecVersionHashConflictError` (đã có ở `agent_core.registry.repository`, tái dùng — không tạo error type mới cho "publish suite version conflict").
- Produces: `EvalRepository` Protocol + `InMemoryEvalRepository` + `PostgresEvalRepository`, mỗi cái có: `publish_suite(suite) -> EvalSuite`, `get_suite(suite_id, version) -> Optional[EvalSuite]`, `create_run(run) -> EvalRun`, `update_run_status(run_id, status, pass_rate=None) -> EvalRun`, `get_run(run_id) -> Optional[EvalRun]`, `record_case_result(result) -> EvalCaseResult`, `list_case_results(eval_run_id) -> list[EvalCaseResult]`.

- [x] **Step 1: Viết test thất bại (chỉ InMemory — Postgres verify ở Step 6 dùng DB thật)**

Tạo `tests/agent_core/evals/test_repositories.py`:

```python
from __future__ import annotations

import pytest

from agent_core.evals.artifacts import EvalCaseResult, EvalRun, EvalSuite
from agent_core.evals.repositories import InMemoryEvalRepository
from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.registry.repository import SpecVersionHashConflictError


def _target_ref() -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64)


@pytest.mark.asyncio
async def test_publish_suite_is_immutable_and_idempotent():
    repo = InMemoryEvalRepository()
    suite = EvalSuite(id="cofounder-core", version="1", target_kind="agent", target_id="cofounder", case_ids=["c1"])

    published1 = await repo.publish_suite(suite)
    assert published1.definition_hash == suite.with_hash().definition_hash

    published2 = await repo.publish_suite(suite)
    assert published2.definition_hash == published1.definition_hash

    changed = EvalSuite(id="cofounder-core", version="1", target_kind="agent", target_id="cofounder", case_ids=["c2"])
    with pytest.raises(SpecVersionHashConflictError):
        await repo.publish_suite(changed)


@pytest.mark.asyncio
async def test_get_suite_returns_none_when_not_published():
    repo = InMemoryEvalRepository()

    result = await repo.get_suite("does.not.exist", "1")

    assert result is None


@pytest.mark.asyncio
async def test_create_run_and_get_run_roundtrip():
    repo = InMemoryEvalRepository()
    run = EvalRun(target_ref=_target_ref())

    created = await repo.create_run(run)
    fetched = await repo.get_run(created.run_id)

    assert fetched is not None
    assert fetched.run_id == created.run_id
    assert fetched.status == "running"


@pytest.mark.asyncio
async def test_update_run_status_changes_status_and_pass_rate():
    repo = InMemoryEvalRepository()
    run = await repo.create_run(EvalRun(target_ref=_target_ref()))

    updated = await repo.update_run_status(run.run_id, "completed", pass_rate=0.9)

    assert updated.status == "completed"
    assert updated.pass_rate == 0.9
    refetched = await repo.get_run(run.run_id)
    assert refetched.status == "completed"


@pytest.mark.asyncio
async def test_record_case_result_and_list_by_run():
    repo = InMemoryEvalRepository()
    run = await repo.create_run(EvalRun(target_ref=_target_ref()))

    await repo.record_case_result(EvalCaseResult(eval_run_id=run.run_id, case_id="c1", passed=True, score=1.0))
    await repo.record_case_result(EvalCaseResult(eval_run_id=run.run_id, case_id="c2", passed=False, score=0.0))

    results = await repo.list_case_results(run.run_id)

    assert len(results) == 2
    assert {r.case_id for r in results} == {"c1", "c2"}
```

- [x] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_repositories.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.evals.repositories'`.

- [x] **Step 3: Viết `EvalRepository` (Protocol + InMemory + Postgres)**

Tạo `packages/agent_core/evals/repositories.py`:

```python
from __future__ import annotations

import json
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.evals.artifacts import EvalCaseResult, EvalRun, EvalSuite
from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.registry.repository import SpecVersionHashConflictError

__all__ = ["EvalRepository", "InMemoryEvalRepository", "PostgresEvalRepository"]


@runtime_checkable
class EvalRepository(Protocol):
    """Protocol cho persistence Eval artifact (EvalSuite/EvalRun/
    EvalCaseResult) theo agent_evals.* (migration 008 + 013, Wave M3)."""

    async def publish_suite(self, suite: EvalSuite) -> EvalSuite: ...
    async def get_suite(self, suite_id: str, version: str) -> Optional[EvalSuite]: ...
    async def create_run(self, run: EvalRun) -> EvalRun: ...
    async def update_run_status(
        self, run_id: str, status: str, pass_rate: Optional[float] = None
    ) -> EvalRun: ...
    async def get_run(self, run_id: str) -> Optional[EvalRun]: ...
    async def record_case_result(self, result: EvalCaseResult) -> EvalCaseResult: ...
    async def list_case_results(self, eval_run_id: str) -> list[EvalCaseResult]: ...


class InMemoryEvalRepository:
    """In-memory implementation — chỉ dùng test/local dev, không dùng
    production (không durable qua restart)."""

    def __init__(self) -> None:
        self._suites: dict[tuple[str, str], EvalSuite] = {}
        self._runs: dict[str, EvalRun] = {}
        self._results: dict[str, list[EvalCaseResult]] = {}

    async def publish_suite(self, suite: EvalSuite) -> EvalSuite:
        pinned = suite.with_hash() if suite.definition_hash is None else suite
        key = (pinned.id, pinned.version)
        existing = self._suites.get(key)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "eval_suite", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing.model_copy(deep=True)
        stored = pinned.model_copy(deep=True)
        self._suites[key] = stored
        return stored.model_copy(deep=True)

    async def get_suite(self, suite_id: str, version: str) -> Optional[EvalSuite]:
        r = self._suites.get((suite_id, version))
        return r.model_copy(deep=True) if r else None

    async def create_run(self, run: EvalRun) -> EvalRun:
        stored = run.model_copy(deep=True)
        self._runs[stored.run_id] = stored
        self._results[stored.run_id] = []
        return stored.model_copy(deep=True)

    async def update_run_status(
        self, run_id: str, status: str, pass_rate: Optional[float] = None
    ) -> EvalRun:
        existing = self._runs[run_id]
        updated = existing.model_copy(update={"status": status, "pass_rate": pass_rate})
        self._runs[run_id] = updated
        return updated.model_copy(deep=True)

    async def get_run(self, run_id: str) -> Optional[EvalRun]:
        r = self._runs.get(run_id)
        return r.model_copy(deep=True) if r else None

    async def record_case_result(self, result: EvalCaseResult) -> EvalCaseResult:
        stored = result.model_copy(deep=True)
        self._results.setdefault(stored.eval_run_id, []).append(stored)
        return stored.model_copy(deep=True)

    async def list_case_results(self, eval_run_id: str) -> list[EvalCaseResult]:
        return [r.model_copy(deep=True) for r in self._results.get(eval_run_id, [])]


class PostgresEvalRepository:
    """PostgreSQL implementation — persist vào agent_evals.suites/runs/
    results (migration 008 + 013)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresEvalRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def publish_suite(self, suite: EvalSuite) -> EvalSuite:
        pinned = suite.with_hash() if suite.definition_hash is None else suite
        existing = await self.get_suite(pinned.id, pinned.version)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "eval_suite", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.suites (
                        suite_id, name, target_kind, target_id, description, version, definition_hash, content
                    ) VALUES (
                        :suite_id, :name, :target_kind, :target_id, :description, :version, :definition_hash, :content
                    )
                    ON CONFLICT (suite_id) DO NOTHING
                    """
                ),
                {
                    "suite_id": pinned.id,
                    "name": pinned.name or pinned.id,
                    "target_kind": pinned.target_kind,
                    "target_id": pinned.target_id,
                    "description": pinned.description,
                    "version": pinned.version,
                    "definition_hash": pinned.definition_hash,
                    "content": json.dumps(pinned.model_dump(mode="json")),
                },
            )
            await session.commit()

        stored = await self.get_suite(pinned.id, pinned.version)
        if stored is not None:
            if stored.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "eval_suite", pinned.id, pinned.version, stored.definition_hash, pinned.definition_hash
                )
            return stored

        # Không tìm thấy sau INSERT: suite_id (PK) đã bị chiếm bởi 1 version
        # KHÁC của cùng suite — agent_evals.suites hiện chỉ giữ 1 row/suite_id
        # (giới hạn đã biết của Wave M3, xem "Sau khi hoàn thành plan này"
        # cuối file — hỗ trợ nhiều version cùng tồn tại cần đổi PK, ngoài
        # phạm vi Task 5). Raise rõ ràng thay vì âm thầm coi publish thành
        # công trong khi không ghi được gì.
        raise RuntimeError(
            f"EvalSuite '{pinned.id}' đã publish với version khác trong "
            f"agent_evals.suites — bảng này hiện chỉ giữ 1 version/suite_id."
        )

    async def get_suite(self, suite_id: str, version: str) -> Optional[EvalSuite]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT suite_id, name, target_kind, target_id, description, version, definition_hash, content
                    FROM agent_evals.suites
                    WHERE suite_id = :suite_id AND version = :version
                    """
                ),
                {"suite_id": suite_id, "version": version},
            )
            row = res.mappings().first()
            if row is None:
                return None
            content = row["content"]
            if content is not None:
                # content JSONB đã có toàn bộ field (case_ids/scorer_version/
                # pass_thresholds/metadata) — ưu tiên reconstruct từ đây để
                # đúng tuyệt đối với definition_hash đã lưu.
                if isinstance(content, str):
                    content = json.loads(content)
                return EvalSuite(**content)
            # Fallback cho row cũ (publish trước khi content column tồn tại) —
            # chỉ tái tạo được identity, không tái tạo được case_ids/config.
            return EvalSuite(
                id=row["suite_id"],
                version=row["version"],
                target_kind=row["target_kind"],
                target_id=row["target_id"],
                name=row["name"] or "",
                description=row["description"] or "",
                definition_hash=row["definition_hash"],
            )

    async def create_run(self, run: EvalRun) -> EvalRun:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.runs (
                        eval_run_id, suite_id, target_kind, target_id, target_version, target_definition_hash,
                        suite_version, suite_definition_hash, status, pass_rate, started_at
                    ) VALUES (
                        :eval_run_id, :suite_id, :target_kind, :target_id, :target_version, :target_definition_hash,
                        :suite_version, :suite_definition_hash, :status, :pass_rate, :started_at
                    )
                    """
                ),
                {
                    "eval_run_id": run.run_id,
                    "suite_id": run.suite_ref.spec_id if run.suite_ref else None,
                    "target_kind": run.target_ref.spec_kind,
                    "target_id": run.target_ref.spec_id,
                    "target_version": run.target_ref.spec_version,
                    "target_definition_hash": run.target_ref.definition_hash,
                    "suite_version": run.suite_ref.spec_version if run.suite_ref else None,
                    "suite_definition_hash": run.suite_ref.definition_hash if run.suite_ref else None,
                    "status": run.status,
                    "pass_rate": run.pass_rate,
                    "started_at": run.started_at,
                },
            )
            await session.commit()
        return run

    async def update_run_status(
        self, run_id: str, status: str, pass_rate: Optional[float] = None
    ) -> EvalRun:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    UPDATE agent_evals.runs
                    SET status = :status, pass_rate = :pass_rate,
                        completed_at = CASE WHEN :status IN ('completed', 'failed') THEN NOW() ELSE completed_at END
                    WHERE eval_run_id = :run_id
                    """
                ),
                {"run_id": run_id, "status": status, "pass_rate": pass_rate},
            )
            await session.commit()
        updated = await self.get_run(run_id)
        if updated is None:
            raise ValueError(f"EvalRun '{run_id}' not found after update")
        return updated

    async def get_run(self, run_id: str) -> Optional[EvalRun]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT eval_run_id, target_kind, target_id, target_version, target_definition_hash,
                           suite_id, suite_version, suite_definition_hash, status, pass_rate, started_at, completed_at
                    FROM agent_evals.runs
                    WHERE eval_run_id = :run_id
                    """
                ),
                {"run_id": run_id},
            )
            row = res.mappings().first()
            if row is None:
                return None
            suite_ref = None
            if row["suite_version"] and row["suite_definition_hash"]:
                suite_ref = PinnedSpecIdentity(
                    spec_kind="eval_suite",
                    spec_id=row["suite_id"],
                    spec_version=row["suite_version"],
                    definition_hash=row["suite_definition_hash"],
                )
            return EvalRun(
                run_id=row["eval_run_id"],
                target_ref=PinnedSpecIdentity(
                    spec_kind=row["target_kind"],
                    spec_id=row["target_id"],
                    spec_version=row["target_version"] or "",
                    definition_hash=row["target_definition_hash"] or "",
                ),
                suite_ref=suite_ref,
                status=row["status"],
                pass_rate=row["pass_rate"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
            )

    async def record_case_result(self, result: EvalCaseResult) -> EvalCaseResult:
        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO agent_evals.results (
                        result_id, eval_run_id, case_id, passed, score, details, error_message, evaluated_at
                    ) VALUES (
                        :result_id, :eval_run_id, :case_id, :passed, :score, :details, :error_message, :evaluated_at
                    )
                    """
                ),
                {
                    "result_id": result.result_id,
                    "eval_run_id": result.eval_run_id,
                    "case_id": result.case_id,
                    "passed": result.passed,
                    "score": result.score,
                    "details": result.details,
                    "error_message": result.error,
                    "evaluated_at": result.evaluated_at,
                },
            )
            await session.commit()
        return result

    async def list_case_results(self, eval_run_id: str) -> list[EvalCaseResult]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT result_id, eval_run_id, case_id, passed, score, details, error_message, evaluated_at
                    FROM agent_evals.results
                    WHERE eval_run_id = :eval_run_id
                    ORDER BY evaluated_at ASC
                    """
                ),
                {"eval_run_id": eval_run_id},
            )
            return [
                EvalCaseResult(
                    result_id=r["result_id"],
                    eval_run_id=r["eval_run_id"],
                    case_id=r["case_id"],
                    passed=r["passed"],
                    score=r["score"],
                    details=r["details"] or "",
                    error=r["error_message"],
                    evaluated_at=r["evaluated_at"],
                )
                for r in res.mappings().all()
            ]
```

Lưu ý: `EvalCaseResult` không có field `case_id` trỏ tới `agent_evals.cases` bằng FK thật trong Postgres implementation này — bảng `agent_evals.results.case_id` có `REFERENCES agent_evals.cases(case_id)` (migration 008), nghĩa là `case_id` PHẢI đã tồn tại trong `agent_evals.cases` trước khi insert. Việc publish case vào bảng đó nằm ngoài phạm vi Task 5 (xem Global Constraints) — test Postgres thật ở Step 6 phải tự insert case trước khi gọi `record_case_result()`.

- [x] **Step 4: Chạy lại test InMemory, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/evals/test_repositories.py -v`
Expected: 5 PASSED.

- [x] **Step 5: Đảm bảo migration 013 (Task 4) đã apply trên Postgres đang chạy**

Run: `docker exec cosa_postgres psql -U javis_app -d javis -c "\d agent_evals.suites" | grep definition_hash`
Expected: có dòng `definition_hash`. Nếu không, chạy lại Task 4 Step 3 trước khi tiếp tục.

- [x] **Step 6: Viết + chạy test Postgres thật cho `PostgresEvalRepository`**

Thêm vào cuối `tests/agent_core/evals/test_repositories.py`:

```python
import os
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.evals.repositories import PostgresEvalRepository


def _pg_session_factory():
    url = os.environ.get(
        "AGENT_CORE_DATABASE_URL",
        "postgresql+asyncpg://javis_app:CHANGE_ME@localhost:5432/javis",
    )
    engine = create_async_engine(url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_postgres_eval_repository_publish_and_get_suite_roundtrip():
    repo = PostgresEvalRepository(_pg_session_factory())
    suite = EvalSuite(
        id="test.eval_suite.pg_1", version="1", target_kind="agent", target_id="cofounder", case_ids=["c1"]
    )

    published = await repo.publish_suite(suite)
    fetched = await repo.get_suite("test.eval_suite.pg_1", "1")

    assert fetched is not None
    assert fetched.definition_hash == published.definition_hash


@pytest.mark.asyncio
async def test_postgres_eval_repository_run_and_case_result_roundtrip():
    repo = PostgresEvalRepository(_pg_session_factory())
    session_factory = _pg_session_factory()

    # Seed 1 case thật để thoả FK agent_evals.results.case_id (ngoài phạm vi
    # EvalRepository publish — chỉ cần tồn tại cho test integration này).
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO agent_evals.suites (suite_id, name, target_kind, target_id, version)
                VALUES ('test.eval_suite.pg_2', 'test', 'agent', 'cofounder', '1')
                ON CONFLICT (suite_id) DO NOTHING
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO agent_evals.cases (case_id, suite_id)
                VALUES ('test.case.pg_1', 'test.eval_suite.pg_2')
                ON CONFLICT (case_id) DO NOTHING
                """
            )
        )
        await session.commit()

    target_ref = PinnedSpecIdentity(
        spec_kind="agent", spec_id="cofounder", spec_version="17", definition_hash="a" * 64
    )
    run = await repo.create_run(EvalRun(target_ref=target_ref))

    updated = await repo.update_run_status(run.run_id, "completed", pass_rate=1.0)
    assert updated.status == "completed"

    result = await repo.record_case_result(
        EvalCaseResult(eval_run_id=run.run_id, case_id="test.case.pg_1", passed=True, score=1.0)
    )
    results = await repo.list_case_results(run.run_id)

    assert result.eval_run_id == run.run_id
    assert len(results) == 1
    assert results[0].case_id == "test.case.pg_1"
```

Run: `cd /Volumes/SSD/javis-saas && export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://javis_app:<mật khẩu thật>@localhost:5432/javis" && ./.venv/bin/python -m pytest tests/agent_core/evals/test_repositories.py -v`
Expected: 7 PASSED (5 InMemory + 2 Postgres).

- [x] **Step 7: Commit**

```bash
git add packages/agent_core/evals/repositories.py tests/agent_core/evals/test_repositories.py
git commit -m "feat(evals): add EvalRepository (InMemory + Postgres) for suite/run/result persistence"
```

---

### Task 6: Wire Skill Optimization Lab ghi `eval_run_id` lineage

**Files:**
- Modify: `packages/agent_core/skills/lab/models.py`
- Modify: `packages/agent_core/skills/lab/executor.py`
- Modify: `packages/agent_core/skills/lab/lab.py`
- Test: `tests/agent_core/skills/lab/test_lab_eval_lineage.py` (mới — kiểm tra layout `tests/agent_core/skills/lab/` trước, nếu chưa có test cho lab thì đây là file test lab đầu tiên trong session này, không phải nghĩa là lab chưa có test khác — tìm bằng `ls tests/agent_core/skills/lab/ 2>/dev/null`, nếu file test khác đã tồn tại đọc qua để giữ đúng convention)

**Interfaces:**
- Consumes: `EvalRepository` (Task 5), `EvalRun`/`EvalCaseResult` (Task 2/3).
- Produces: `SkillMutationRecord.eval_run_id: Optional[str] = None` (field mới); `SkillCandidateExecutor.run_suite()` trả thêm `eval_run_id: Optional[str]` khi có `eval_repository` được tiêm; `SkillOptimizationLab` gán `eval_run_id` vào từng `SkillMutationRecord`.

- [x] **Step 1: Kiểm tra layout test hiện có**

Run: `ls /Volumes/SSD/javis-saas/tests/agent_core/skills/lab/ 2>/dev/null || echo "not found"`

Nếu chưa tồn tại, tạo `tests/agent_core/skills/lab/__init__.py` rỗng (nếu thư mục `tests/agent_core/skills/` đã là package, chỉ cần thêm `lab/__init__.py`; kiểm tra bằng `find tests/agent_core/skills -name "__init__.py"`).

- [x] **Step 2: Viết test thất bại**

Tạo `tests/agent_core/skills/lab/test_lab_eval_lineage.py`:

```python
from __future__ import annotations

import pytest

from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.evals.repositories import InMemoryEvalRepository
from agent_core.governance.contracts import AutonomyLevel
from agent_core.skills.contracts import SkillSpec
from agent_core.skills.lab.executor import SkillCandidateExecutor
from agent_core.skills.lab.lab import SkillOptimizationLab
from agent_core.skills.lab.models import EvalCase


class _AlwaysCompleteKernel:
    """Kernel giả tối thiểu — chỉ trả RunResult COMPLETED, không thực thi gì
    thật. Đủ cho test lineage wiring, không phải test executor scoring."""

    async def run(self, request: RunRequest, spec: AgentSpec) -> RunResult:
        return RunResult(run_id="fake_run", status=RunStatus.COMPLETED, final_output={"response": "ok"})

    async def resume(self, run_id: str, checkpoint_ref: str, updates: dict) -> RunResult:
        raise NotImplementedError

    async def cancel(self, run_id: str, reason: str | None = None) -> bool:
        raise NotImplementedError

    async def stream(self, request: RunRequest, spec: AgentSpec):
        raise NotImplementedError
        yield  # pragma: no cover


def _base_agent_spec() -> AgentSpec:
    return AgentSpec(id="test.agent.lab_lineage", version="1.0.0", autonomy_level=AutonomyLevel.L1)


def _base_skill() -> SkillSpec:
    return SkillSpec(id="test.skill.lab_lineage", version="1.0.0", instructions="Base instructions")


@pytest.mark.asyncio
async def test_skill_mutation_record_has_no_eval_run_id_by_default():
    executor = SkillCandidateExecutor(kernel=_AlwaysCompleteKernel(), base_agent_spec=_base_agent_spec())
    lab = SkillOptimizationLab(executor=executor, max_rounds=1)

    record = await lab.optimize(_base_skill(), [EvalCase(input_payload={"x": 1})])

    mutations = lab.list_mutations(record.candidate_id)
    assert len(mutations) == 1
    assert mutations[0].eval_run_id is None


@pytest.mark.asyncio
async def test_skill_mutation_record_gets_eval_run_id_when_repository_injected():
    eval_repo = InMemoryEvalRepository()
    executor = SkillCandidateExecutor(
        kernel=_AlwaysCompleteKernel(), base_agent_spec=_base_agent_spec(), eval_repository=eval_repo
    )
    lab = SkillOptimizationLab(executor=executor, max_rounds=1)

    record = await lab.optimize(_base_skill(), [EvalCase(input_payload={"x": 1})])

    mutations = lab.list_mutations(record.candidate_id)
    assert len(mutations) == 1
    eval_run_id = mutations[0].eval_run_id
    assert eval_run_id is not None
    assert eval_run_id.startswith("evalrun_")

    stored_run = await eval_repo.get_run(eval_run_id)
    assert stored_run is not None
    assert stored_run.target_ref.spec_kind == "skill"
    assert stored_run.suite_ref is None  # ad-hoc, không gắn EvalSuite đã publish

    results = await eval_repo.list_case_results(eval_run_id)
    assert len(results) == 1
```

- [x] **Step 3: Chạy test, xác nhận FAIL với `TypeError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/skills/lab/test_lab_eval_lineage.py -v`
Expected: FAIL — `TypeError: SkillCandidateExecutor.__init__() got an unexpected keyword argument 'eval_repository'`.

- [x] **Step 4: Thêm `eval_run_id` vào `SkillMutationRecord`**

Trong `packages/agent_core/skills/lab/models.py`, thêm field vào cuối class `SkillMutationRecord` (sau `accepted: bool = False`):

```python
    accepted: bool = False
    eval_run_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

(field `created_at` đã có sẵn ngay sau `accepted` — chỉ chèn dòng `eval_run_id` vào giữa, không xoá `created_at`).

- [x] **Step 5: Sửa `SkillCandidateExecutor` để tạo `EvalRun` + `EvalCaseResult` khi có `eval_repository`**

Trong `packages/agent_core/skills/lab/executor.py`, sửa import đầu file — thêm:

```python
from typing import Callable, Optional

from agent_core.contracts.kernel import ExecutionKernel
from agent_core.contracts.run import RunRequest, RunResult, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.evals.artifacts import EvalCaseResult, EvalRun
from agent_core.evals.repositories import EvalRepository
from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.skills.contracts import SkillSpec
from agent_core.skills.lab.models import EvalCase
```

Sửa `__init__`:

```python
    def __init__(
        self,
        *,
        kernel: ExecutionKernel,
        base_agent_spec: AgentSpec,
        score_fn: ScoreFn = default_score_fn,
        eval_repository: Optional[EvalRepository] = None,
    ) -> None:
        self._kernel = kernel
        self._base_agent_spec = base_agent_spec
        self._score_fn = score_fn
        self._eval_repository = eval_repository
```

Sửa `run_suite()` — chữ ký trả thêm `Optional[str]` (eval_run_id):

```python
    async def run_suite(
        self,
        candidate_skill: SkillSpec,
        cases: list[EvalCase],
        *,
        run_label: str,
        include_holdout: bool = True,
    ) -> tuple[float, list[float], Optional[str]]:
        eval_agent_spec = self._build_eval_agent_spec(candidate_skill, run_label)

        eval_run_id: Optional[str] = None
        if self._eval_repository is not None:
            target_ref = PinnedSpecIdentity(
                spec_kind="skill",
                spec_id=candidate_skill.id,
                spec_version=candidate_skill.version,
                definition_hash=candidate_skill.definition_hash or candidate_skill.compute_hash(),
            )
            created = await self._eval_repository.create_run(EvalRun(target_ref=target_ref))
            eval_run_id = created.run_id

        scores: list[float] = []
        for case in cases:
            if not include_holdout and case.is_holdout:
                continue
            req = RunRequest(
                principal="skill_optimization_lab",
                root_executable_ref=eval_agent_spec.to_pinned_identity(),
                input=case.input_payload,
            )
            result = await self._kernel.run(req, eval_agent_spec)
            score = self._score_fn(result, case)
            scores.append(score)

            if eval_run_id is not None:
                await self._eval_repository.record_case_result(
                    EvalCaseResult(
                        eval_run_id=eval_run_id,
                        case_id=case.case_id,
                        passed=score >= 1.0,
                        score=score,
                    )
                )

        avg = sum(scores) / len(scores) if scores else 0.0

        if eval_run_id is not None:
            await self._eval_repository.update_run_status(eval_run_id, "completed", pass_rate=avg)

        return avg, scores, eval_run_id
```

- [x] **Step 6: Sửa `SkillOptimizationLab.optimize()` để nhận `eval_run_id` từ `run_suite()` và gán vào `SkillMutationRecord`**

Trong `packages/agent_core/skills/lab/lab.py`, sửa 3 chỗ gọi `self._executor.run_suite(...)` — mỗi lời gọi giờ trả 3 giá trị thay vì 2:

Dòng `baseline_score, _ = await self._executor.run_suite(...)` (r0-baseline) → `baseline_score, _, _ = await self._executor.run_suite(...)` (giữ nguyên logic, baseline round không tạo `SkillMutationRecord` nên không cần dùng `eval_run_id` ở đây).

Dòng trong vòng lặp round (`new_score, _ = await self._executor.run_suite(...)`) → sửa thành:

```python
            new_score, _, eval_run_id = await self._executor.run_suite(
                mutated_skill, cases, run_label=f"r{round_no}", include_holdout=False
            )

            accepted = new_score > (record.latest_score or 0.0)
            self._mutations.append(
                SkillMutationRecord(
                    candidate_id=record.candidate_id,
                    round_no=round_no,
                    diff_summary=rationale,
                    pre_score=record.latest_score,
                    post_score=new_score,
                    accepted=accepted,
                    eval_run_id=eval_run_id,
                )
            )
```

Dòng `final_score, _ = await self._executor.run_suite(...)` (final-regression) → `final_score, _, _ = await self._executor.run_suite(...)` (giữ nguyên logic — full regression không tạo `SkillMutationRecord` riêng).

- [x] **Step 7: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/skills/lab/test_lab_eval_lineage.py -v`
Expected: 2 PASSED.

- [x] **Step 8: Chạy toàn bộ `tests/agent_core/` để xác nhận cả Wave M3 không phá vỡ gì (kể cả test executor/lab cũ)**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/ -q`
Expected: tất cả PASS — baseline trước Wave M3 là 268 passed, 17 skipped; sau 6 task số PASSED tăng thêm đúng bằng số test mới đã viết ở Task 1-6 (2 Postgres test ở Task 5 Step 6 chỉ chạy khi `AGENT_CORE_DATABASE_URL` được set — nếu chạy `pytest tests/agent_core/ -q` KHÔNG set biến đó, 2 test Postgres đó FAIL với connection error thay vì skip; chạy lại có `export AGENT_CORE_DATABASE_URL=...` trước lệnh này để bao gồm cả 2 test đó trong lần verify cuối).

- [x] **Step 9: Commit**

```bash
git add packages/agent_core/skills/lab/models.py packages/agent_core/skills/lab/executor.py packages/agent_core/skills/lab/lab.py tests/agent_core/skills/lab/
git commit -m "feat(skills): wire Skill Optimization Lab to persist EvalRun/EvalCaseResult and record eval_run_id lineage"
```

---

## Sau khi hoàn thành plan này

Wave M3 (phần agent_core) xong khi cả 6 task trên commit và `AGENT_CORE_DATABASE_URL=... ./.venv/bin/python -m pytest tests/agent_core/ -v` xanh toàn bộ. Việc còn lại ngoài phạm vi plan này:

- **Wave M4 (Promotion Evidence)** — `PromotionEvidence` (evidence_id, target ref, required eval_run_ids, observed_fingerprints, policy_version, is_stale()) + `PromotionGate` logic, KHÔNG chứa `PromotionDecision`/activation (thuộc `services/cosa`, theo CLAUDE.md 4 vùng kiến trúc). Cần plan riêng.
- **Case content persistence** — publish `agent_core.skills.lab.models.EvalCase` thật vào `agent_evals.cases` (hiện Task 5 chỉ tham chiếu case_id, không publish nội dung case) — chỉ cần nếu có nhu cầu audit case content lịch sử, chưa có yêu cầu cụ thể.
- **EvalSuite thật cho promotion** (không phải ad-hoc như Skill Lab) — publish 1 `EvalSuite` cố định (vd `cofounder-core@1`) dùng cho benchmark định kỳ, wiring vào 1 pipeline chạy suite đó — thuộc phạm vi Wave M5 (Offline DAG) hoặc M4, chưa quyết định thứ tự.
- **Nhiều version cùng tồn tại cho 1 EvalSuite trong Postgres** — `agent_evals.suites.suite_id` (migration 008) là PK đơn cột, chưa hỗ trợ composite `(suite_id, version)` như `agent_registry.published_specs`. Task 5's `PostgresEvalRepository.publish_suite()` publish version thứ 2 của cùng 1 suite_id đã tồn tại sẽ raise `RuntimeError` rõ ràng (không âm thầm mất dữ liệu) thay vì hỗ trợ đúng — chỉ cần đổi PK (và propagate qua FK ở `agent_evals.cases`) khi có nhu cầu versioning thật (M4/M5 promotion evidence benchmark định kỳ nhiều version).

Không tự ý mở rộng phạm vi task hiện tại sang các mục trên khi thực thi plan này.
