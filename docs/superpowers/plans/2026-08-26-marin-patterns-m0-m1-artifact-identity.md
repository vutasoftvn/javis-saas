# COSA Marin Patterns — M0/M1 Artifact Identity Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khóa quyết định kiến trúc (M0) và tổng quát hóa `PinnedSpecIdentity` đã có sẵn thành identity primitive dùng chung cho mọi domain artifact (agent/skill/prompt/model_policy/tool_contract) mà KHÔNG tạo type `ArtifactIdentity`/`ArtifactRef` mới song song — đây là nền tảng bắt buộc trước khi Wave M2 (registry integration) có thể bắt đầu.

**Architecture:** `packages/agent_core/governance/contracts.py::PinnedSpecIdentity` (spec_kind/spec_id/spec_version/definition_hash) đã đúng hình dạng "ArtifactRef" mà `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` đề xuất tạo mới. Task ở đây chỉ mở rộng field `spec_kind` (hiện là `Literal["agent", "workflow"]`) để chấp nhận thêm `"skill"`, `"prompt"`, `"model_policy"`, `"tool_contract"`, thêm một model lineage edge tối giản, và một adapter chuyển `PinnedSkillRef` → `PinnedSpecIdentity`. Migration mới (bất biến, không sửa migration cũ) mở rộng CHECK constraint tương ứng trên bảng `agent_core_governance.spec_resolution_manifest_entries`.

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio, PostgreSQL (asyncpg qua `packages/agent_core/scripts/migrate.py`).

## Global Constraints

- Không tạo `ArtifactIdentity`/`ArtifactRef` dataclass mới — chỉ mở rộng `PinnedSpecIdentity` đã có (quyết định người dùng, xem `docs/implementation/marin-patterns-adjusted-plan.md` Wave M1).
- Migration đã apply là bất biến — checksum tracked trong `public.schema_migrations`, sửa file cũ sẽ làm `python -m packages.agent_core.scripts.migrate` fail hard (`MigrationChecksumMismatchError`). Luôn tạo file migration mới, số thứ tự kế tiếp sau `011_run_stream_events.sql` → `012_...`.
- Test file mới đặt theo layout hiện có: `tests/agent_core/governance/` cho mọi test liên quan `governance/contracts.py`.
- Không import ngược `packages/agent_core` → `services/company` (CLAUDE.md 4 vùng kiến trúc) — không task nào ở đây chạm `services/*`.
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do; tên định danh và message lỗi hệ thống giữ tiếng Anh (CLAUDE.md "Comment code").

---

### Task 1: Ghi quyết định generalization thành ADR

**Files:**
- Create: `docs/architecture/adr/ADR-ARTIFACT-IDENTITY-001-generalize-pinned-spec-identity.md`

**Interfaces:** Không có (tài liệu thuần).

- [ ] **Step 1: Viết ADR**

Tạo file với nội dung sau (đúng format các ADR hiện có trong `docs/architecture/adr/`, ví dụ `ADR-RUNTIME-002-openai-agents-sdk-primary-deepseek-provider.md`):

```markdown
# ADR-ARTIFACT-IDENTITY-001: Tổng quát hóa PinnedSpecIdentity thay vì tạo ArtifactIdentity/ArtifactRef mới

- **Trạng thái:** ACCEPTED (quyết định người dùng, phiên brainstorming đối chiếu `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` với code thật, 2026-08-26)
- **Ngày quyết định:** 2026-08-26
- **Tham chiếu:**
  - `COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md` (tài liệu gốc đề xuất `ArtifactIdentity`/`ArtifactRef`)
  - `docs/implementation/marin-patterns-adjusted-plan.md` (plan điều chỉnh, Wave M0/M1)
  - `packages/agent_core/governance/contracts.py::PinnedSpecIdentity`

---

## 1. Bối cảnh

Tài liệu Marin Patterns đề xuất tạo `ArtifactIdentity`/`ArtifactRef` (kind, name, version, fingerprint) làm primitive định danh chung cho mọi artifact (AgentSpec, PromptSpec, SkillSpec, EvalSuite, KnowledgeSnapshot, PromotionEvidence). Audit code thật (2026-08-26) phát hiện `packages/agent_core/governance/contracts.py::PinnedSpecIdentity` đã là đúng hình dạng đó: `spec_kind`, `spec_id`, `spec_version`, `definition_hash` — dùng canonical SHA-256 hash (`governance/hashing.py::definition_hash()`, sort_keys, order-independent). Tạo type mới song song sẽ vi phạm CLAUDE.md rule 4 ("Không nhân bản kiến trúc") và chính §25.6 của tài liệu gốc ("không tạo persistence mới khi hiện tại đã có ownership").

Giới hạn thật duy nhất: `PinnedSpecIdentity.spec_kind` hiện là `Literal["agent", "workflow"]`, hẹp hơn field cùng tên ở `registry/models.py::PublishedSpecRecord.spec_kind` (đã là `str` tự do, hỗ trợ `"skill"` qua `publish_skill_spec()`). DB constraint `agent_core_governance.spec_resolution_manifest_entries` cũng có `CHECK (spec_kind IN ('agent', 'workflow'))`.

## 2. Quyết định

1. **Không tạo `ArtifactIdentity`/`ArtifactRef`.** Dùng `PinnedSpecIdentity` làm identity primitive chung cho agent/skill/prompt/model_policy/tool_contract — domain nào cần resolve exact version+fingerprint vào một Run (qua `SpecResolutionManifest`) đều dùng type này.
2. Mở rộng `PinnedSpecIdentity.spec_kind` từ `Literal["agent", "workflow"]` thành `Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract"]` — enum tường minh (không dùng `str` tự do) để giữ an toàn kiểu, khác với `PublishedSpecRecord.spec_kind` (registry layer, không cần strict vì đã có DB UNIQUE constraint bảo vệ).
3. Mở rộng CHECK constraint tương ứng trên `agent_core_governance.spec_resolution_manifest_entries` bằng migration MỚI (không sửa `002_governance_temporal_model.sql` — migration đã apply là bất biến).
4. `EvalSuite`/`EvalRun`/`PromotionEvidence` (Wave M3/M4, chưa code) sẽ tham chiếu artifact khác qua field kiểu `PinnedSpecIdentity` nhúng trực tiếp trong bản ghi eval/promotion — KHÔNG đi qua `SpecResolutionManifest`/`agent_core_governance.spec_resolution_manifest_entries` (bảng đó chỉ dành cho identity mà một *Run* đã resolve, không phải cho offline eval/promotion artifact). Vì vậy `spec_kind` cho `"eval_suite"`/`"knowledge_snapshot"`/`"promotion_evidence"` KHÔNG cần thêm vào Literal này ở M1 — chỉ thêm khi một use case thật sự cần ghi entry đó vào manifest của một Run.
5. Thêm `SpecDependencyEdge` (owner/dependency/relation) làm lineage edge tối giản, tái dùng `PinnedSpecIdentity` cho cả hai đầu — không tạo `ArtifactDependency` type riêng.

## 3. Hệ quả

- `AgentSpec` (Wave M2, chưa code) sẽ thêm `prompt_ref`/`model_policy_ref`/`tool_contract_refs` kiểu `PinnedSpecIdentity` — không cần type mới.
- `PinnedSkillRef` (`contracts/identity.py`) giữ nguyên làm type ổn định cho `AgentSpec.pinned_skills` (đã có consumer thật, không refactor); thêm adapter `to_pinned_identity()` để dùng thống nhất trong lineage edge khi cần.
- Nếu về sau phát hiện một domain thật sự không tái dùng được `PinnedSpecIdentity` (ví dụ cần thêm field chỉ có ý nghĩa với domain đó), phải mở ADR mới ghi rõ lý do kỹ thuật — không tự ý tạo type song song.
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture/adr/ADR-ARTIFACT-IDENTITY-001-generalize-pinned-spec-identity.md
git commit -m "docs(adr): freeze decision to generalize PinnedSpecIdentity instead of new ArtifactRef type"
```

---

### Task 2: Golden fingerprint fixture — regression baseline trước khi đổi code

**Files:**
- Create: `tests/agent_core/governance/test_definition_hash_artifact_fixtures.py`

**Interfaces:**
- Consumes: `agent_core.governance.hashing.definition_hash` (đã tồn tại, không đổi), `agent_core.contracts.spec.AgentSpec` (đã tồn tại), `agent_core.contracts.identity.PinnedSkillRef` (đã tồn tại).
- Produces: không có API mới — đây là test thuần, khóa hành vi hiện tại làm baseline trước khi Task 3 sửa `PinnedSpecIdentity`.

- [ ] **Step 1: Viết test**

```python
from __future__ import annotations

from agent_core.contracts.identity import PinnedSkillRef
from agent_core.contracts.spec import AgentSpec


def test_agent_spec_fingerprint_changes_when_a_pinned_skill_is_added():
    base = AgentSpec(id="test.agent.fixture_1", version="1.0.0", instructions="Base")
    with_skill = base.model_copy(
        update={
            "pinned_skills": [
                PinnedSkillRef(skill_id="research", version="1", definition_hash="b" * 64)
            ]
        }
    )

    assert base.compute_hash() != with_skill.compute_hash()


def test_agent_spec_fingerprint_changes_when_pinned_skill_hash_drifts():
    v1 = AgentSpec(
        id="test.agent.fixture_2",
        version="1.0.0",
        pinned_skills=[PinnedSkillRef(skill_id="research", version="1", definition_hash="a" * 64)],
    )
    drifted = v1.model_copy(
        update={"pinned_skills": [PinnedSkillRef(skill_id="research", version="1", definition_hash="c" * 64)]}
    )

    assert v1.compute_hash() != drifted.compute_hash()


def test_agent_spec_fingerprint_stable_when_metadata_dict_key_order_differs():
    a = AgentSpec(id="test.agent.fixture_3", version="1.0.0", metadata={"a": 1, "b": 2})
    b = AgentSpec(id="test.agent.fixture_3", version="1.0.0", metadata={"b": 2, "a": 1})

    assert a.compute_hash() == b.compute_hash()


def test_agent_spec_fingerprint_stable_across_repeated_calls():
    spec = AgentSpec(id="test.agent.fixture_4", version="1.0.0", instructions="Stable")

    assert spec.compute_hash() == spec.compute_hash()
```

- [ ] **Step 2: Chạy test, xác nhận PASS ngay trên code hiện tại (baseline, chưa sửa gì)**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/governance/test_definition_hash_artifact_fixtures.py -v`
Expected: 4 PASSED — đây là baseline chứng minh `definition_hash()` đã canonical đúng §6.2 tài liệu gốc, không cần sửa thuật toán hash ở M1.

- [ ] **Step 3: Commit**

```bash
git add tests/agent_core/governance/test_definition_hash_artifact_fixtures.py
git commit -m "test(governance): lock fingerprint drift/order-independence baseline before M1 changes"
```

---

### Task 3: Mở rộng `PinnedSpecIdentity.spec_kind`

**Files:**
- Modify: `packages/agent_core/governance/contracts.py:16`
- Test: `tests/agent_core/governance/test_contracts.py`

**Interfaces:**
- Produces: `PinnedSpecIdentity.spec_kind` nay chấp nhận `Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract"]` thay vì chỉ `Literal["agent", "workflow"]`. Chữ ký field khác không đổi (`spec_id: str`, `spec_version: str`, `definition_hash: str`).

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/governance/test_contracts.py`:

```python
import pytest
from pydantic import ValidationError


def test_pinned_spec_identity_accepts_prompt_kind():
    identity = PinnedSpecIdentity(spec_kind="prompt", spec_id="cofounder/system", spec_version="2026.08.3", definition_hash="a" * 64)
    assert identity.spec_kind == "prompt"


def test_pinned_spec_identity_accepts_model_policy_kind():
    identity = PinnedSpecIdentity(spec_kind="model_policy", spec_id="default-deepseek", spec_version="7", definition_hash="a" * 64)
    assert identity.spec_kind == "model_policy"


def test_pinned_spec_identity_accepts_tool_contract_kind():
    identity = PinnedSpecIdentity(spec_kind="tool_contract", spec_id="company.strategy.read", spec_version="3", definition_hash="a" * 64)
    assert identity.spec_kind == "tool_contract"


def test_pinned_spec_identity_accepts_skill_kind():
    identity = PinnedSpecIdentity(spec_kind="skill", spec_id="research", spec_version="12", definition_hash="a" * 64)
    assert identity.spec_kind == "skill"


def test_pinned_spec_identity_still_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        PinnedSpecIdentity(spec_kind="eval_suite", spec_id="x", spec_version="1", definition_hash="a" * 64)
```

- [ ] **Step 2: Chạy test, xác nhận 4 test kind mới FAIL, test "rejects unknown" PASS**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/governance/test_contracts.py -v -k "pinned_spec_identity_accepts or pinned_spec_identity_still_rejects"`
Expected: 4 FAIL (pydantic.ValidationError vì `spec_kind` chưa chấp nhận giá trị mới), 1 PASS (`test_pinned_spec_identity_still_rejects_unknown_kind` — `"eval_suite"` cố tình KHÔNG có trong Literal, đúng quyết định ADR §2.4).

- [ ] **Step 3: Sửa `PinnedSpecIdentity.spec_kind`**

Trong `packages/agent_core/governance/contracts.py`, sửa dòng 16:

```python
    spec_kind: Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract"]
```

Và cập nhật docstring của class (dòng 10-14) để phản ánh phạm vi mở rộng:

```python
class PinnedSpecIdentity(BaseModel):
    """Định danh bất biến của 1 artifact đã publish (AgentSpec/WorkflowSpec/
    SkillSpec/PromptSpec/ModelPolicySpec/ToolContractSpec) mà 1 Run đã resolve
    tới. `definition_hash` (không phải chỉ `spec_version`) là thứ chống silent
    drift — xem PHẦN I §1 của COSA_AGENT_CORE_GOVERNANCE_TEMPORAL_MODEL_2026-08-23.md
    và ADR-ARTIFACT-IDENTITY-001 (không tạo ArtifactIdentity/ArtifactRef riêng,
    tổng quát hóa type này thay vào đó)."""
```

- [ ] **Step 4: Chạy lại toàn bộ test file, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/governance/test_contracts.py -v`
Expected: tất cả PASS (bao gồm test cũ lẫn 5 test mới).

- [ ] **Step 5: Chạy test suite governance đầy đủ để xác nhận không phá vỡ consumer khác**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/governance/ tests/agent_core/contracts/ tests/agent_core/registry/ tests/agent_core/workflows/ tests/agent_core/coordination/ -v`
Expected: tất cả PASS — các nơi dùng `PinnedSpecIdentity` với `spec_kind="agent"`/`"workflow"` (contracts/spec.py, workflows/schema.py, coordination/delegation_envelope.py, governance/store.py, governance/providers/) không bị ảnh hưởng vì các giá trị cũ vẫn hợp lệ.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_contracts.py
git commit -m "feat(governance): widen PinnedSpecIdentity.spec_kind to skill/prompt/model_policy/tool_contract"
```

---

### Task 4: Migration mở rộng CHECK constraint

**Files:**
- Create: `packages/agent_core/migrations/012_widen_spec_resolution_manifest_kinds.sql`

**Interfaces:** Không có API Python — thay đổi DB constraint thuần.

- [ ] **Step 1: Viết migration**

```sql
-- Migration: 012_widen_spec_resolution_manifest_kinds.sql
-- Description: Mở rộng CHECK constraint trên spec_kind của
--   agent_core_governance.spec_resolution_manifest_entries để khớp với
--   PinnedSpecIdentity.spec_kind đã mở rộng (ADR-ARTIFACT-IDENTITY-001) —
--   thêm 'skill', 'prompt', 'model_policy', 'tool_contract'.
-- Storage ownership: schema agent_core_governance owned by packages/agent_core/governance/.
--
-- 002_governance_temporal_model.sql đã apply là bất biến — không sửa file đó,
-- ALTER constraint bằng migration mới này thay vào đó.

ALTER TABLE agent_core_governance.spec_resolution_manifest_entries
    DROP CONSTRAINT IF EXISTS spec_resolution_manifest_entries_spec_kind_check;

ALTER TABLE agent_core_governance.spec_resolution_manifest_entries
    ADD CONSTRAINT spec_resolution_manifest_entries_spec_kind_check
    CHECK (spec_kind IN ('agent', 'workflow', 'skill', 'prompt', 'model_policy', 'tool_contract'));
```

- [ ] **Step 2: Xác nhận tên constraint tự sinh của Postgres đúng như dự đoán trước khi chạy thật**

Postgres tự đặt tên `CHECK` constraint không có tên tường minh theo dạng `<table>_<column>_check`. Verify bằng cách connect vào DB dev thật (đã migrate tới `011`) và chạy:

Run: `psql "$AGENT_CORE_DATABASE_URL" -c "\d agent_core_governance.spec_resolution_manifest_entries"`
Expected: thấy dòng constraint tên `spec_resolution_manifest_entries_spec_kind_check`. Nếu tên khác, sửa lại `DROP CONSTRAINT IF EXISTS` trong migration cho khớp trước khi chạy Step 3 (an toàn vì có `IF EXISTS`, nhưng phải khớp đúng tên để DROP thật sự xảy ra).

- [ ] **Step 3: Chạy migration thật trên DB dev**

Run: `cd /Volumes/SSD/javis-saas && make migrate-agent-platform`
Expected: log hiển thị `012_widen_spec_resolution_manifest_kinds.sql` được áp dụng, không lỗi `MigrationChecksumMismatchError`.

- [ ] **Step 4: Verify constraint mới bằng insert thử qua psql**

Run:
```bash
psql "$AGENT_CORE_DATABASE_URL" -c "INSERT INTO agent_core_governance.spec_resolution_manifest_entries (run_id, spec_kind, spec_id, spec_version, definition_hash) VALUES ('smoke-test-run', 'prompt', 'cofounder/system', '1', repeat('a', 64));"
psql "$AGENT_CORE_DATABASE_URL" -c "DELETE FROM agent_core_governance.spec_resolution_manifest_entries WHERE run_id = 'smoke-test-run';"
```
Expected: INSERT thành công (trước migration này sẽ bị `CHECK` constraint chặn), DELETE dọn sạch dữ liệu smoke-test.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/migrations/012_widen_spec_resolution_manifest_kinds.sql
git commit -m "migrate(governance): widen spec_resolution_manifest_entries CHECK constraint to match PinnedSpecIdentity"
```

---

### Task 5: `SpecDependencyEdge` — lineage edge tối giản

**Files:**
- Modify: `packages/agent_core/governance/contracts.py` (thêm class mới cuối file)
- Test: Create `tests/agent_core/governance/test_spec_dependency_edge.py`

**Interfaces:**
- Consumes: `PinnedSpecIdentity` (Task 3).
- Produces: `SpecDependencyEdge(owner: PinnedSpecIdentity, dependency: PinnedSpecIdentity, relation: str)` — dùng ở Wave M2 để ghi lineage khi publish AgentSpec pin Prompt/ModelPolicy/ToolContract/Skill.

- [ ] **Step 1: Viết test thất bại**

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_core.governance.contracts import PinnedSpecIdentity, SpecDependencyEdge


def _identity(kind: str, spec_id: str, version: str = "1") -> PinnedSpecIdentity:
    return PinnedSpecIdentity(spec_kind=kind, spec_id=spec_id, spec_version=version, definition_hash="a" * 64)


def test_spec_dependency_edge_holds_owner_dependency_and_relation():
    owner = _identity("agent", "cofounder")
    dependency = _identity("prompt", "cofounder/system")

    edge = SpecDependencyEdge(owner=owner, dependency=dependency, relation="uses_prompt")

    assert edge.owner == owner
    assert edge.dependency == dependency
    assert edge.relation == "uses_prompt"


def test_spec_dependency_edge_is_frozen():
    owner = _identity("agent", "cofounder")
    dependency = _identity("skill", "research", version="12")
    edge = SpecDependencyEdge(owner=owner, dependency=dependency, relation="pins_skill")

    with pytest.raises(ValidationError):
        edge.relation = "changed"


def test_spec_dependency_edge_equality_is_value_based():
    owner = _identity("agent", "cofounder")
    dependency = _identity("prompt", "cofounder/system")

    a = SpecDependencyEdge(owner=owner, dependency=dependency, relation="uses_prompt")
    b = SpecDependencyEdge(owner=owner, dependency=dependency, relation="uses_prompt")

    assert a == b
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/governance/test_spec_dependency_edge.py -v`
Expected: FAIL — `ImportError: cannot import name 'SpecDependencyEdge'`.

- [ ] **Step 3: Thêm `SpecDependencyEdge` vào `packages/agent_core/governance/contracts.py`**

Thêm vào cuối file (sau `SpecResolutionManifest`, dòng 33 hiện tại):

```python
class SpecDependencyEdge(BaseModel):
    """Một cạnh lineage: `owner` phụ thuộc vào `dependency` với quan hệ
    `relation` (vd "uses_prompt", "pins_skill", "uses_model_policy",
    "uses_tool_contract") — theo ADR-ARTIFACT-IDENTITY-001 §2.5. Dùng ở Wave
    M2 khi publish AgentSpec để ghi lại dependency graph phục vụ audit/lineage
    query, KHÔNG dùng để lưu vào SpecResolutionManifest của một Run (hai khái
    niệm khác nhau: manifest là identity một Run đã resolve tới; edge này là
    quan hệ tĩnh giữa hai artifact đã publish)."""

    model_config = {"frozen": True}

    owner: PinnedSpecIdentity
    dependency: PinnedSpecIdentity
    relation: str
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/governance/test_spec_dependency_edge.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_spec_dependency_edge.py
git commit -m "feat(governance): add SpecDependencyEdge as minimal lineage edge over PinnedSpecIdentity"
```

---

### Task 6: `PinnedSkillRef.to_pinned_identity()` adapter

**Files:**
- Modify: `packages/agent_core/contracts/identity.py`
- Test: Modify `tests/agent_core/contracts/test_contracts_all.py` (đọc file trước khi sửa để giữ đúng convention hiện có trong file)

**Interfaces:**
- Consumes: `PinnedSkillRef` (đã tồn tại, không đổi field), `PinnedSpecIdentity` (Task 3, đã chấp nhận `spec_kind="skill"`).
- Produces: `PinnedSkillRef.to_pinned_identity() -> PinnedSpecIdentity` — cầu nối để dùng `PinnedSkillRef` (cơ chế ổn định của `AgentSpec.pinned_skills`) trong `SpecDependencyEdge` (Task 5) mà không cần đổi `PinnedSkillRef` hay chỗ nào đang consume nó.

- [ ] **Step 1: Đọc file test hiện có để nắm convention**

Run: `cat /Volumes/SSD/javis-saas/tests/agent_core/contracts/test_contracts_all.py`

(Không cần sửa gì ở bước này — chỉ đọc để bước sau viết test khớp style, ví dụ cách import, cách đặt tên hàm test trong file này.)

- [ ] **Step 2: Viết test thất bại**

Thêm vào cuối `tests/agent_core/contracts/test_contracts_all.py`:

```python
from agent_core.contracts.identity import PinnedSkillRef
from agent_core.governance.contracts import PinnedSpecIdentity


def test_pinned_skill_ref_converts_to_pinned_spec_identity():
    ref = PinnedSkillRef(skill_id="research", version="12", definition_hash="b" * 64)

    identity = ref.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="skill", spec_id="research", spec_version="12", definition_hash="b" * 64
    )
```

- [ ] **Step 3: Chạy test, xác nhận FAIL với `AttributeError`**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/contracts/test_contracts_all.py -v -k to_pinned_spec_identity`
Expected: FAIL — `AttributeError: 'PinnedSkillRef' object has no attribute 'to_pinned_identity'`.

- [ ] **Step 4: Thêm method vào `PinnedSkillRef`**

Trong `packages/agent_core/contracts/identity.py`, thêm method vào cuối class `PinnedSkillRef` (sau field `definition_hash`):

```python
    skill_id: str
    version: str
    definition_hash: str

    def to_pinned_identity(self) -> "PinnedSpecIdentity":
        """Adapter sang PinnedSpecIdentity(spec_kind="skill") — dùng khi cần
        đưa 1 pinned skill vào SpecDependencyEdge chung với các dependency
        kind khác (prompt/model_policy/tool_contract), theo
        ADR-ARTIFACT-IDENTITY-001 §3. Không đổi PinnedSkillRef hiện có —
        AgentSpec.pinned_skills vẫn dùng type gốc."""
        return PinnedSpecIdentity(
            spec_kind="skill",
            spec_id=self.skill_id,
            spec_version=self.version,
            definition_hash=self.definition_hash,
        )
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/contracts/test_contracts_all.py -v`
Expected: tất cả PASS.

- [ ] **Step 6: Chạy toàn bộ test suite agent_core liên quan để xác nhận không phá vỡ gì**

Run: `cd /Volumes/SSD/javis-saas && python -m pytest tests/agent_core/ -v`
Expected: tất cả PASS (test cần Postgres/Encore thật, nếu có, sẽ skip hoặc fail độc lập với thay đổi này — nếu fail, xác nhận lỗi đó tồn tại trước cả khi bắt đầu Task 1 bằng `git stash` rồi chạy lại, trước khi kết luận thay đổi ở đây gây ra lỗi).

- [ ] **Step 7: Commit**

```bash
git add packages/agent_core/contracts/identity.py tests/agent_core/contracts/test_contracts_all.py
git commit -m "feat(contracts): add PinnedSkillRef.to_pinned_identity() adapter to PinnedSpecIdentity"
```

---

## Sau khi hoàn thành plan này

Wave M0/M1 xong khi cả 6 task trên commit và `python -m pytest tests/agent_core/ -v` xanh toàn bộ. Bước tiếp theo là Wave M2 (registry integration & runtime wiring — `PromptSpec`/`ModelPolicySpec`/`ToolContractSpec`, mở rộng `AgentSpec`, wiring `apps/cosa/agents/specs.py` qua registry) — cần một plan riêng (`writing-plans` mới) vì đụng tới `apps/cosa` (registry + runtime wiring), không nằm trong scope thuần `agent_core` của plan này. Không tự ý mở rộng phạm vi task hiện tại sang M2 khi thực thi plan này.
