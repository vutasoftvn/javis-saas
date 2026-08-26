# COSA Marin Patterns — M2 Registry Dependency Pinning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép `AgentSpec` pin đầy đủ dependency (Prompt, ModelPolicy, tool contracts) bằng exact version + fingerprint thay vì instructions/model_policy dạng string/dict rời rạc — hoàn thành phần agent_core-only của Wave M2 (`docs/implementation/marin-patterns-adjusted-plan.md`).

**Architecture:** Thêm `PromptSpec`/`ModelPolicySpec` theo đúng pattern `AgentSpec`/`SkillSpec` đã có (`compute_hash()`, `with_hash()`, `to_pinned_identity()` trả về `PinnedSpecIdentity` — không tạo `ArtifactRef` mới, theo ADR-ARTIFACT-IDENTITY-001 đã chốt ở Wave M1). `AgentSpec` thêm `prompt_ref`/`model_policy_ref` kiểu `PinnedSpecIdentity` và `tool_contract_refs` kiểu `CapabilityImplementationIdentity` (đã tồn tại ở `contracts/capability.py` — capability/tool-contract KHÔNG đi qua `SpecRegistryRepository` vì `CapabilitySpec` chưa có publish/version lifecycle, đây là quyết định người dùng, không mở rộng registry cho capability trong plan này). `registry/publisher.py::publish_agent_spec()` validate dependency đã publish + hash khớp trước khi ghi. `registry/resolver.py` (file mới) cung cấp exact-resolution (không floating) và tính `SpecDependencyEdge` list cho lineage — chỉ trả về in-memory, KHÔNG persist vào bảng mới (chưa có yêu cầu audit UI thật, tránh tạo persistence layer khi chưa cần — YAGNI).

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio — không đụng DB/migration nào trong plan này (không bảng mới).

## Global Constraints

- Không tạo `ArtifactIdentity`/`ArtifactRef` dataclass mới — dùng `PinnedSpecIdentity` (`packages/agent_core/governance/contracts.py`, đã hỗ trợ `spec_kind` gồm "prompt"/"model_policy"/"tool_contract" từ Wave M1).
- `tool_contract_refs` trên `AgentSpec` dùng `CapabilityImplementationIdentity` (`packages/agent_core/contracts/capability.py`, đã có `compute_identity_hash()`) — KHÔNG publish capability qua `SpecRegistryRepository`, KHÔNG tạo `ToolContractSpec` mới (quyết định người dùng: capability chưa có publish/version lifecycle, việc đó là quyết định kiến trúc riêng ngoài phạm vi plan này).
- Không chạm `apps/cosa/*` hay `services/*` trong plan này — runtime wiring (Run resolve exact spec từ registry) là plan M2b riêng, sau khi plan này xong.
- Không tạo bảng DB mới hay migration mới — lineage edge (`SpecDependencyEdge`, đã có từ Wave M1) chỉ tính in-memory, không persist.
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do (why); tên định danh và message lỗi hệ thống giữ tiếng Anh.
- Mỗi spec mới (`PromptSpec`, `ModelPolicySpec`) theo đúng pattern đã có ở `AgentSpec`/`SkillSpec`: field `definition_hash: Optional[str] = None`, method `compute_hash()` dùng `agent_core.governance.hashing.definition_hash`, `with_hash()`, `to_pinned_identity() -> PinnedSpecIdentity`.

---

### Task 1: `PromptSpec` contract

**Files:**
- Create: `packages/agent_core/contracts/prompt.py`
- Modify: `packages/agent_core/contracts/__init__.py` (thêm export)
- Test: `tests/agent_core/contracts/test_prompt_spec.py`

**Interfaces:**
- Produces: `PromptSpec(id: str, version: str = "1.0.0", text: str = "", variables: list[str] = [], metadata: dict = {}, definition_hash: Optional[str] = None)` với `compute_hash() -> str`, `with_hash() -> PromptSpec`, `to_pinned_identity() -> PinnedSpecIdentity` (spec_kind="prompt").

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/contracts/test_prompt_spec.py`:

```python
from __future__ import annotations

from agent_core.contracts.prompt import PromptSpec
from agent_core.governance.contracts import PinnedSpecIdentity


def test_prompt_spec_has_sensible_defaults():
    spec = PromptSpec(id="cofounder/system")

    assert spec.version == "1.0.0"
    assert spec.text == ""
    assert spec.variables == []
    assert spec.definition_hash is None


def test_prompt_spec_compute_hash_is_deterministic():
    a = PromptSpec(id="cofounder/system", text="Bạn là trợ lý.")
    b = PromptSpec(id="cofounder/system", text="Bạn là trợ lý.")

    assert a.compute_hash() == b.compute_hash()


def test_prompt_spec_compute_hash_changes_with_text():
    a = PromptSpec(id="cofounder/system", text="Bản A")
    b = PromptSpec(id="cofounder/system", text="Bản B")

    assert a.compute_hash() != b.compute_hash()


def test_prompt_spec_with_hash_returns_a_copy_with_definition_hash_set():
    spec = PromptSpec(id="cofounder/system", text="Nội dung")

    pinned = spec.with_hash()

    assert spec.definition_hash is None
    assert pinned.definition_hash == spec.compute_hash()


def test_prompt_spec_to_pinned_identity_uses_prompt_kind():
    spec = PromptSpec(id="cofounder/system", version="2026.08.3", text="Nội dung").with_hash()

    identity = spec.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="prompt",
        spec_id="cofounder/system",
        spec_version="2026.08.3",
        definition_hash=spec.definition_hash,
    )
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/test_prompt_spec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.contracts.prompt'`.

- [ ] **Step 3: Viết `PromptSpec`**

Tạo `packages/agent_core/contracts/prompt.py`:

```python
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["PromptSpec"]


class PromptSpec(BaseModel):
    """Đặc tả prompt có thể publish/pin độc lập khỏi AgentSpec — theo
    ADR-ARTIFACT-IDENTITY-001 (dùng PinnedSpecIdentity, spec_kind="prompt",
    không tạo ArtifactRef riêng). `text` là nội dung instruction thật;
    `AgentSpec.instructions` (string thô) vẫn là fallback cho spec chưa pin
    prompt qua `AgentSpec.prompt_ref` — resolve ưu tiên prompt_ref khi có
    (việc resolve thật thuộc Wave M2b, runtime wiring, ngoài phạm vi module
    contracts/ thuần này)."""

    id: str
    version: str = "1.0.0"
    text: str = ""
    variables: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của spec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> "PromptSpec":
        """Trả về bản sao của PromptSpec đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào AgentSpec.prompt_ref
        hoặc ghi vào SpecResolutionManifest."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="prompt",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
```

Sau đó mở `packages/agent_core/contracts/__init__.py`, thêm import và export:

```python
from agent_core.contracts.prompt import PromptSpec
```

(đặt sau dòng `from agent_core.contracts.kernel import ExecutionKernel`, trước `from agent_core.contracts.run import ...` — giữ thứ tự alphabet theo module path đã có trong file), và thêm `"PromptSpec",` vào `__all__` (giữ thứ tự alphabet như các entry khác).

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/test_prompt_spec.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Chạy `tests/agent_core/contracts/` để xác nhận `__init__.py` không vỡ import nào khác**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/ -v`
Expected: tất cả PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/contracts/prompt.py packages/agent_core/contracts/__init__.py tests/agent_core/contracts/test_prompt_spec.py
git commit -m "feat(contracts): add PromptSpec as a pinnable, publishable artifact"
```

---

### Task 2: `ModelPolicySpec` contract

**Files:**
- Create: `packages/agent_core/contracts/model_policy.py`
- Modify: `packages/agent_core/contracts/__init__.py` (thêm export)
- Test: `tests/agent_core/contracts/test_model_policy_spec.py`

**Interfaces:**
- Produces: `ModelPolicySpec(id: str, version: str = "1.0.0", model: str = "deepseek-chat", temperature: float = 0.0, metadata: dict = {}, definition_hash: Optional[str] = None)` với `compute_hash()`, `with_hash()`, `to_pinned_identity() -> PinnedSpecIdentity` (spec_kind="model_policy").

Lưu ý phạm vi field: `model`/`temperature` là 2 field DUY NHẤT hiện có consumer thật trong codebase (`packages/agent_core/kernel/openai_agents_kernel.py:482,484` đọc `spec.model_policy.get("model", ...)` / `.get("temperature", ...)`). Không thêm field suy đoán (provider/fallback/...) chưa có consumer — YAGNI.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/contracts/test_model_policy_spec.py`:

```python
from __future__ import annotations

from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.governance.contracts import PinnedSpecIdentity


def test_model_policy_spec_has_sensible_defaults():
    spec = ModelPolicySpec(id="default-deepseek-policy")

    assert spec.version == "1.0.0"
    assert spec.model == "deepseek-chat"
    assert spec.temperature == 0.0
    assert spec.definition_hash is None


def test_model_policy_spec_compute_hash_changes_with_model():
    a = ModelPolicySpec(id="default-deepseek-policy", model="deepseek-chat")
    b = ModelPolicySpec(id="default-deepseek-policy", model="deepseek-reasoner")

    assert a.compute_hash() != b.compute_hash()


def test_model_policy_spec_compute_hash_changes_with_temperature():
    a = ModelPolicySpec(id="default-deepseek-policy", temperature=0.0)
    b = ModelPolicySpec(id="default-deepseek-policy", temperature=0.7)

    assert a.compute_hash() != b.compute_hash()


def test_model_policy_spec_with_hash_returns_a_copy_with_definition_hash_set():
    spec = ModelPolicySpec(id="default-deepseek-policy")

    pinned = spec.with_hash()

    assert spec.definition_hash is None
    assert pinned.definition_hash == spec.compute_hash()


def test_model_policy_spec_to_pinned_identity_uses_model_policy_kind():
    spec = ModelPolicySpec(id="default-deepseek-policy", version="7").with_hash()

    identity = spec.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="model_policy",
        spec_id="default-deepseek-policy",
        spec_version="7",
        definition_hash=spec.definition_hash,
    )
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/test_model_policy_spec.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.contracts.model_policy'`.

- [ ] **Step 3: Viết `ModelPolicySpec`**

Tạo `packages/agent_core/contracts/model_policy.py`:

```python
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["ModelPolicySpec"]


class ModelPolicySpec(BaseModel):
    """Đặc tả model/provider policy có thể publish/pin độc lập khỏi AgentSpec
    — theo ADR-ARTIFACT-IDENTITY-001 (spec_kind="model_policy"). Chỉ gồm
    `model`/`temperature` — 2 field duy nhất hiện có consumer thật
    (packages/agent_core/kernel/openai_agents_kernel.py). AgentSpec.model_policy
    (dict thô) vẫn là fallback cho spec chưa pin qua AgentSpec.model_policy_ref."""

    id: str
    version: str = "1.0.0"
    model: str = "deepseek-chat"
    temperature: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá cho toàn bộ nội dung của spec."""
        data = self.model_dump(exclude={"definition_hash"})
        return definition_hash(data)

    def with_hash(self) -> "ModelPolicySpec":
        """Trả về bản sao của ModelPolicySpec đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào AgentSpec.model_policy_ref
        hoặc ghi vào SpecResolutionManifest."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="model_policy",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
```

Sau đó mở `packages/agent_core/contracts/__init__.py`, thêm:

```python
from agent_core.contracts.model_policy import ModelPolicySpec
```

(đặt trước dòng `from agent_core.contracts.prompt import PromptSpec` — giữ thứ tự alphabet theo module path), và thêm `"ModelPolicySpec",` vào `__all__` (giữ thứ tự alphabet).

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/test_model_policy_spec.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Chạy `tests/agent_core/contracts/` để xác nhận không vỡ import nào khác**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/ -v`
Expected: tất cả PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/contracts/model_policy.py packages/agent_core/contracts/__init__.py tests/agent_core/contracts/test_model_policy_spec.py
git commit -m "feat(contracts): add ModelPolicySpec as a pinnable, publishable artifact"
```

---

### Task 3: `AgentSpec` pin đầy đủ dependency

**Files:**
- Modify: `packages/agent_core/contracts/spec.py`
- Test: `tests/agent_core/contracts/test_contracts_all.py` (thêm test — file đã tồn tại từ Wave M0/M1, đọc trước khi sửa để giữ convention) hoặc tạo `tests/agent_core/contracts/test_agent_spec.py` nếu chưa có file test riêng cho `AgentSpec` — **kiểm tra trước bằng `ls tests/agent_core/contracts/`** rồi quyết định thêm vào file có sẵn đúng chủ đề nhất, không tạo file trùng chủ đề.

**Interfaces:**
- Consumes: `PromptSpec.to_pinned_identity()` (Task 1), `ModelPolicySpec.to_pinned_identity()` (Task 2), `CapabilityImplementationIdentity` (`packages/agent_core/contracts/capability.py`, đã tồn tại).
- Produces: `AgentSpec` có thêm 3 field mới: `prompt_ref: Optional[PinnedSpecIdentity] = None`, `model_policy_ref: Optional[PinnedSpecIdentity] = None`, `tool_contract_refs: list[CapabilityImplementationIdentity] = []`. `compute_hash()` không đổi chữ ký, tự động bao gồm 3 field mới vì dùng `self.model_dump(exclude={"definition_hash"})`.

- [ ] **Step 1: Kiểm tra layout test hiện có**

Run: `ls /Volumes/SSD/javis-saas/tests/agent_core/contracts/`

Nếu có file dành riêng cho `AgentSpec` (ví dụ `test_agent_spec.py`), thêm test vào đó. Nếu không, thêm vào cuối `tests/agent_core/contracts/test_contracts_all.py` (đã có sẵn từ Task 6 của Wave M0/M1, đã import `PinnedSpecIdentity`).

- [ ] **Step 2: Viết test thất bại**

Thêm vào file đã chọn ở Step 1:

```python
from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec


def test_agent_spec_defaults_have_no_pinned_dependency_refs():
    spec = AgentSpec(id="test.agent.m2_1")

    assert spec.prompt_ref is None
    assert spec.model_policy_ref is None
    assert spec.tool_contract_refs == []


def test_agent_spec_fingerprint_changes_when_prompt_ref_is_set():
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    base = AgentSpec(id="test.agent.m2_2")
    with_prompt = base.model_copy(update={"prompt_ref": prompt.to_pinned_identity()})

    assert base.compute_hash() != with_prompt.compute_hash()


def test_agent_spec_fingerprint_changes_when_model_policy_ref_drifts():
    policy_v1 = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-chat").with_hash()
    policy_v2 = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-reasoner").with_hash()

    spec_v1 = AgentSpec(id="test.agent.m2_3", model_policy_ref=policy_v1.to_pinned_identity())
    spec_v2 = AgentSpec(id="test.agent.m2_3", model_policy_ref=policy_v2.to_pinned_identity())

    assert spec_v1.compute_hash() != spec_v2.compute_hash()


def test_agent_spec_fingerprint_changes_when_tool_contract_refs_change():
    from agent_core.contracts.capability import CapabilityImplementationIdentity

    base = AgentSpec(id="test.agent.m2_4")
    with_contract = base.model_copy(
        update={
            "tool_contract_refs": [
                CapabilityImplementationIdentity(capability_id="company.strategy.read", handler_version="2.0.0")
            ]
        }
    )

    assert base.compute_hash() != with_contract.compute_hash()
```

- [ ] **Step 3: Chạy test, xác nhận FAIL**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest <file_đã_chọn> -v -k "prompt_ref or model_policy_ref or tool_contract_refs"`
Expected: FAIL — `pydantic.ValidationError: prompt_ref` (extra field không cho phép, hoặc `AttributeError` nếu Pydantic bỏ qua field lạ — trong mọi trường hợp `assert spec.prompt_ref is None` sẽ FAIL vì field chưa tồn tại).

- [ ] **Step 4: Sửa `AgentSpec`**

Trong `packages/agent_core/contracts/spec.py`, sửa import (dòng 6):

```python
from agent_core.contracts.capability import CapabilityImplementationIdentity
from agent_core.contracts.identity import PinnedSkillRef
```

Và thêm 3 field mới vào class `AgentSpec`, ngay sau `pinned_skills: list[PinnedSkillRef] = Field(default_factory=list)` (dòng 26):

```python
    pinned_skills: list[PinnedSkillRef] = Field(default_factory=list)
    prompt_ref: Optional[PinnedSpecIdentity] = None
    model_policy_ref: Optional[PinnedSpecIdentity] = None
    tool_contract_refs: list[CapabilityImplementationIdentity] = Field(default_factory=list)
```

Cập nhật docstring của class (dòng 14-18) để ghi chú ý nghĩa 3 field mới:

```python
class AgentSpec(BaseModel):
    """Đặc tả Agent có thể thực thi theo Master Guide §6.1.

    Yêu cầu tính bất biến và định danh nội dung: `definition_hash` là bắt buộc
    để chống silent drift khi spec được publish hoặc nạp vào Run.

    `prompt_ref`/`model_policy_ref` pin Prompt/ModelPolicy đã publish (nếu có)
    — khi None, `instructions`/`model_policy` (dạng string/dict thô) vẫn là
    fallback (Wave M2, ADR-ARTIFACT-IDENTITY-001 §3). `tool_contract_refs`
    dùng CapabilityImplementationIdentity (không phải PinnedSpecIdentity) vì
    CapabilitySpec chưa có publish/version lifecycle qua SpecRegistryRepository
    — đây là quyết định phạm vi có chủ đích, không phải thiếu sót.
    """
```

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest <file_đã_chọn> -v`
Expected: tất cả PASS.

- [ ] **Step 6: Chạy toàn bộ `tests/agent_core/contracts/ tests/agent_core/registry/ tests/agent_core/governance/`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/ tests/agent_core/registry/ tests/agent_core/governance/ -v`
Expected: tất cả PASS — xác nhận thêm field optional không phá vỡ AgentSpec ở nơi khác (registry publisher test dùng `AgentSpec(id=..., version=..., instructions=...)` không truyền 3 field mới, phải vẫn hoạt động vì default `None`/`[]`).

- [ ] **Step 7: Commit**

```bash
git add packages/agent_core/contracts/spec.py <file_test_đã_sửa>
git commit -m "feat(contracts): pin AgentSpec dependencies via prompt_ref/model_policy_ref/tool_contract_refs"
```

---

### Task 4: Publisher cho `PromptSpec`/`ModelPolicySpec`

**Files:**
- Modify: `packages/agent_core/registry/publisher.py`
- Test: `tests/agent_core/registry/test_publisher.py`

**Interfaces:**
- Consumes: `PromptSpec` (Task 1), `ModelPolicySpec` (Task 2), `SpecRegistryRepository` (đã tồn tại), `PublishedSpecRecord` (đã tồn tại).
- Produces: `publish_prompt_spec(spec: PromptSpec, *, repository: SpecRegistryRepository, publisher: Optional[str] = None) -> PublishedSpecRecord`, `publish_model_policy_spec(spec: ModelPolicySpec, *, repository: SpecRegistryRepository, publisher: Optional[str] = None) -> PublishedSpecRecord`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/registry/test_publisher.py`:

```python
from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.registry.publisher import publish_model_policy_spec, publish_prompt_spec


@pytest.mark.asyncio
async def test_publish_prompt_spec_is_immutable_and_idempotent():
    repo = InMemorySpecRegistryRepository()
    spec = PromptSpec(id="test.prompt.registry_1", version="1.0.0", text="Bản đầu")

    record1 = await publish_prompt_spec(spec, repository=repo, publisher="tester")
    assert record1.spec_kind == "prompt"
    assert record1.definition_hash == spec.with_hash().definition_hash

    record2 = await publish_prompt_spec(spec, repository=repo, publisher="tester")
    assert record2.definition_hash == record1.definition_hash

    changed = PromptSpec(id="test.prompt.registry_1", version="1.0.0", text="Đã đổi")
    with pytest.raises(SpecVersionHashConflictError):
        await publish_prompt_spec(changed, repository=repo, publisher="tester")


@pytest.mark.asyncio
async def test_publish_model_policy_spec_is_immutable_and_idempotent():
    repo = InMemorySpecRegistryRepository()
    spec = ModelPolicySpec(id="test.model_policy.registry_1", version="1.0.0", model="deepseek-chat")

    record1 = await publish_model_policy_spec(spec, repository=repo, publisher="tester")
    assert record1.spec_kind == "model_policy"
    assert record1.definition_hash == spec.with_hash().definition_hash

    record2 = await publish_model_policy_spec(spec, repository=repo, publisher="tester")
    assert record2.definition_hash == record1.definition_hash
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/test_publisher.py -v -k "prompt_spec or model_policy_spec"`
Expected: FAIL — `ImportError: cannot import name 'publish_prompt_spec'`.

- [ ] **Step 3: Thêm 2 hàm publish**

Trong `packages/agent_core/registry/publisher.py`, sửa import + `__all__` ở đầu file:

```python
from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec
from agent_core.registry.models import PublishedSpecRecord
from agent_core.registry.repository import SpecRegistryRepository
from agent_core.skills.contracts import SkillSpec

__all__ = ["publish_agent_spec", "publish_skill_spec", "publish_prompt_spec", "publish_model_policy_spec"]
```

Thêm 2 hàm vào cuối file (sau `publish_skill_spec`):

```python
async def publish_prompt_spec(
    spec: PromptSpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 PromptSpec vào cùng registry dùng cho AgentSpec (`spec_kind="prompt"`)
    — theo ADR-ARTIFACT-IDENTITY-001, không tạo registry riêng cho prompt.
    Idempotent nếu cùng hash; raise SpecVersionHashConflictError nếu version đã
    publish với nội dung khác."""
    pinned_hash = spec.definition_hash or spec.compute_hash()
    record = PublishedSpecRecord(
        spec_kind="prompt",
        spec_id=spec.id,
        version=spec.version,
        definition_hash=pinned_hash,
        content=spec.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)


async def publish_model_policy_spec(
    spec: ModelPolicySpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 ModelPolicySpec vào cùng registry dùng cho AgentSpec
    (`spec_kind="model_policy"`) — theo ADR-ARTIFACT-IDENTITY-001, không tạo
    registry riêng. Idempotent nếu cùng hash; raise SpecVersionHashConflictError
    nếu version đã publish với nội dung khác."""
    pinned_hash = spec.definition_hash or spec.compute_hash()
    record = PublishedSpecRecord(
        spec_kind="model_policy",
        spec_id=spec.id,
        version=spec.version,
        definition_hash=pinned_hash,
        content=spec.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/test_publisher.py -v`
Expected: tất cả PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/registry/publisher.py tests/agent_core/registry/test_publisher.py
git commit -m "feat(registry): add publish_prompt_spec and publish_model_policy_spec"
```

---

### Task 5: `publish_agent_spec()` validate dependency đã publish

**Files:**
- Modify: `packages/agent_core/registry/repository.py` (thêm error class)
- Modify: `packages/agent_core/registry/publisher.py` (`publish_agent_spec`)
- Test: `tests/agent_core/registry/test_publisher.py`

**Interfaces:**
- Produces: `SpecDependencyMissingError(Exception)` trong `registry/repository.py` — fields `dependency_kind: str`, `dependency_id: str`, `dependency_version: str`, `reason: Literal["not_found", "hash_mismatch"]`.
- `publish_agent_spec()` giữ nguyên chữ ký, nhưng khi `spec.prompt_ref`/`spec.model_policy_ref` không None: gọi `repository.get(kind, id, version)`, raise `SpecDependencyMissingError` nếu không tìm thấy hoặc `definition_hash` khác `expected`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/registry/test_publisher.py`:

```python
from agent_core.registry.repository import SpecDependencyMissingError


@pytest.mark.asyncio
async def test_publish_agent_spec_rejects_prompt_ref_not_in_registry():
    repo = InMemorySpecRegistryRepository()
    from agent_core.governance.contracts import PinnedSpecIdentity

    spec = AgentSpec(
        id="test.agent.m2_dep_1",
        version="1.0.0",
        prompt_ref=PinnedSpecIdentity(
            spec_kind="prompt", spec_id="cofounder/system", spec_version="1", definition_hash="a" * 64
        ),
    )

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert exc_info.value.reason == "not_found"
    assert exc_info.value.dependency_kind == "prompt"


@pytest.mark.asyncio
async def test_publish_agent_spec_rejects_prompt_ref_with_hash_mismatch():
    repo = InMemorySpecRegistryRepository()
    published_prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung thật").with_hash()
    await publish_prompt_spec(published_prompt, repository=repo, publisher="tester")

    from agent_core.governance.contracts import PinnedSpecIdentity

    spec = AgentSpec(
        id="test.agent.m2_dep_2",
        version="1.0.0",
        prompt_ref=PinnedSpecIdentity(
            spec_kind="prompt", spec_id="cofounder/system", spec_version="1", definition_hash="f" * 64
        ),
    )

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert exc_info.value.reason == "hash_mismatch"


@pytest.mark.asyncio
async def test_publish_agent_spec_succeeds_when_prompt_ref_matches_published_hash():
    repo = InMemorySpecRegistryRepository()
    published_prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung thật").with_hash()
    await publish_prompt_spec(published_prompt, repository=repo, publisher="tester")

    spec = AgentSpec(
        id="test.agent.m2_dep_3",
        version="1.0.0",
        prompt_ref=published_prompt.to_pinned_identity(),
    )

    record = await publish_agent_spec(spec, repository=repo, publisher="tester")
    assert record.spec_kind == "agent"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ImportError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/test_publisher.py -v -k dependency`
Expected: FAIL — `ImportError: cannot import name 'SpecDependencyMissingError'`.

- [ ] **Step 3: Thêm `SpecDependencyMissingError`**

Trong `packages/agent_core/registry/repository.py`, thêm vào `__all__` (dòng 11-16): `"SpecDependencyMissingError",`. Thêm class mới sau `SpecVersionHashConflictError` (sau dòng 35):

```python
class SpecDependencyMissingError(Exception):
    """Raised khi AgentSpec pin 1 dependency (prompt_ref/model_policy_ref)
    chưa publish trong registry, hoặc đã publish nhưng với definition_hash
    khác — publish_agent_spec() không được ghi 1 spec có floating/broken
    dependency ref (Wave M2, tương đương INV-A3 của
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md)."""

    def __init__(self, dependency_kind: str, dependency_id: str, dependency_version: str, reason: str) -> None:
        super().__init__(
            f"AgentSpec pins {dependency_kind} '{dependency_id}@{dependency_version}' "
            f"({reason}) — publish {dependency_kind} trước khi publish AgentSpec."
        )
        self.dependency_kind = dependency_kind
        self.dependency_id = dependency_id
        self.dependency_version = dependency_version
        self.reason = reason
```

- [ ] **Step 4: Sửa `publish_agent_spec()`**

Trong `packages/agent_core/registry/publisher.py`, sửa import đầu file — thêm:

```python
from agent_core.registry.repository import SpecDependencyMissingError, SpecRegistryRepository
```

(thay cho `from agent_core.registry.repository import SpecRegistryRepository` hiện có).

Sửa hàm `publish_agent_spec()` thành:

```python
async def publish_agent_spec(
    spec: AgentSpec,
    *,
    repository: SpecRegistryRepository,
    publisher: Optional[str] = None,
) -> PublishedSpecRecord:
    """Publish 1 AgentSpec vào registry — idempotent nếu nội dung không đổi
    (cùng definition_hash), raise SpecVersionHashConflictError nếu version đã
    publish với nội dung KHÁC (Blueprint V2 §25: "Published version immutable;
    thay đổi phải tạo version mới"). Nếu spec pin prompt_ref/model_policy_ref,
    validate dependency đã publish với đúng hash trước khi ghi (Wave M2,
    tránh floating/broken reference — INV-A3)."""
    for ref, kind in ((spec.prompt_ref, "prompt"), (spec.model_policy_ref, "model_policy")):
        if ref is None:
            continue
        existing = await repository.get(ref.spec_kind, ref.spec_id, ref.spec_version)
        if existing is None:
            raise SpecDependencyMissingError(kind, ref.spec_id, ref.spec_version, "not_found")
        if existing.definition_hash != ref.definition_hash:
            raise SpecDependencyMissingError(kind, ref.spec_id, ref.spec_version, "hash_mismatch")

    pinned = spec.with_hash() if spec.definition_hash is None else spec
    record = PublishedSpecRecord(
        spec_kind="agent",
        spec_id=pinned.id,
        version=pinned.version,
        definition_hash=pinned.definition_hash,
        content=pinned.model_dump(mode="json"),
        publisher=publisher,
    )
    return await repository.publish(record)
```

- [ ] **Step 5: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/test_publisher.py -v`
Expected: tất cả PASS.

- [ ] **Step 6: Chạy toàn bộ `tests/agent_core/registry/` và `tests/agent_core/kernel/` (kernel test dùng `publish_agent_spec` — Wave M0/M1 report có nhắc `test_kernel_run_publishes_spec_to_registry`)**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/ tests/agent_core/kernel/ -v`
Expected: tất cả PASS — `AgentSpec` mặc định không có `prompt_ref`/`model_policy_ref` (None) nên validation mới không kích hoạt cho spec cũ, không phá vỡ test kernel hiện có.

- [ ] **Step 7: Commit**

```bash
git add packages/agent_core/registry/repository.py packages/agent_core/registry/publisher.py tests/agent_core/registry/test_publisher.py
git commit -m "feat(registry): reject publish_agent_spec when prompt_ref/model_policy_ref dependency is missing or hash-mismatched"
```

---

### Task 6: `SpecResolver` — exact resolution + lineage edges

**Files:**
- Create: `packages/agent_core/registry/resolver.py`
- Test: `tests/agent_core/registry/test_resolver.py`

**Interfaces:**
- Consumes: `SpecRegistryRepository` (đã tồn tại), `PinnedSpecIdentity`/`SpecDependencyEdge` (Wave M1, `governance/contracts.py`), `AgentSpec` (Task 3), `SpecDependencyMissingError` (Task 5).
- Produces:
  - `SpecResolver(repository: SpecRegistryRepository)`
  - `async def resolve_exact(self, kind: str, spec_id: str, version: str, expected_definition_hash: str) -> dict[str, Any]` — trả về `record.content`, raise `SpecDependencyMissingError` nếu not_found/hash_mismatch.
  - `async def resolve_agent_spec_dependencies(self, agent_spec: AgentSpec) -> AgentSpecResolution` — trả về dataclass `AgentSpecResolution(agent_content: dict, prompt_content: Optional[dict], model_policy_content: Optional[dict], edges: list[SpecDependencyEdge])`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/registry/test_resolver.py`:

```python
from __future__ import annotations

import pytest

from agent_core.contracts.model_policy import ModelPolicySpec
from agent_core.contracts.prompt import PromptSpec
from agent_core.contracts.spec import AgentSpec
from agent_core.registry.publisher import publish_agent_spec, publish_model_policy_spec, publish_prompt_spec
from agent_core.registry.repository import InMemorySpecRegistryRepository, SpecDependencyMissingError
from agent_core.registry.resolver import SpecResolver


async def _publish_full_agent_spec(repo) -> AgentSpec:
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung prompt").with_hash()
    await publish_prompt_spec(prompt, repository=repo, publisher="tester")
    policy = ModelPolicySpec(id="default-deepseek-policy", version="1", model="deepseek-chat").with_hash()
    await publish_model_policy_spec(policy, repository=repo, publisher="tester")

    spec = AgentSpec(
        id="test.agent.resolver_1",
        version="1.0.0",
        prompt_ref=prompt.to_pinned_identity(),
        model_policy_ref=policy.to_pinned_identity(),
    )
    await publish_agent_spec(spec, repository=repo, publisher="tester")
    return spec.with_hash()


@pytest.mark.asyncio
async def test_resolve_exact_returns_content_when_hash_matches():
    repo = InMemorySpecRegistryRepository()
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    await publish_prompt_spec(prompt, repository=repo, publisher="tester")
    resolver = SpecResolver(repository=repo)

    content = await resolver.resolve_exact("prompt", "cofounder/system", "1", prompt.definition_hash)

    assert content["text"] == "Nội dung"


@pytest.mark.asyncio
async def test_resolve_exact_raises_when_not_found():
    repo = InMemorySpecRegistryRepository()
    resolver = SpecResolver(repository=repo)

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await resolver.resolve_exact("prompt", "does.not.exist", "1", "a" * 64)
    assert exc_info.value.reason == "not_found"


@pytest.mark.asyncio
async def test_resolve_exact_raises_when_hash_mismatch():
    repo = InMemorySpecRegistryRepository()
    prompt = PromptSpec(id="cofounder/system", version="1", text="Nội dung").with_hash()
    await publish_prompt_spec(prompt, repository=repo, publisher="tester")
    resolver = SpecResolver(repository=repo)

    with pytest.raises(SpecDependencyMissingError) as exc_info:
        await resolver.resolve_exact("prompt", "cofounder/system", "1", "f" * 64)
    assert exc_info.value.reason == "hash_mismatch"


@pytest.mark.asyncio
async def test_resolve_agent_spec_dependencies_returns_resolved_content_and_edges():
    repo = InMemorySpecRegistryRepository()
    spec = await _publish_full_agent_spec(repo)
    resolver = SpecResolver(repository=repo)

    resolution = await resolver.resolve_agent_spec_dependencies(spec)

    assert resolution.agent_content["id"] == "test.agent.resolver_1"
    assert resolution.prompt_content["text"] == "Nội dung prompt"
    assert resolution.model_policy_content["model"] == "deepseek-chat"
    relations = {edge.relation for edge in resolution.edges}
    assert relations == {"uses_prompt", "uses_model_policy"}
    owners = {edge.owner.spec_id for edge in resolution.edges}
    assert owners == {"test.agent.resolver_1"}


@pytest.mark.asyncio
async def test_resolve_agent_spec_dependencies_returns_no_edges_when_no_refs_pinned():
    repo = InMemorySpecRegistryRepository()
    spec = AgentSpec(id="test.agent.resolver_2", version="1.0.0")
    await publish_agent_spec(spec, repository=repo, publisher="tester")
    resolver = SpecResolver(repository=repo)

    resolution = await resolver.resolve_agent_spec_dependencies(spec.with_hash())

    assert resolution.prompt_content is None
    assert resolution.model_policy_content is None
    assert resolution.edges == []
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/test_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.registry.resolver'`.

- [ ] **Step 3: Viết `SpecResolver`**

Tạo `packages/agent_core/registry/resolver.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from agent_core.contracts.spec import AgentSpec
from agent_core.governance.contracts import PinnedSpecIdentity, SpecDependencyEdge
from agent_core.registry.repository import SpecDependencyMissingError, SpecRegistryRepository

__all__ = ["SpecResolver", "AgentSpecResolution"]


@dataclass(frozen=True)
class AgentSpecResolution:
    """Kết quả resolve đầy đủ 1 AgentSpec: content của chính spec + content
    của từng dependency đã pin + lineage edges tương ứng. `edges` chỉ tính
    in-memory (không persist) — theo Global Constraints của plan này, chưa
    có bảng lineage nào được quyết định tạo."""

    agent_content: dict[str, Any]
    prompt_content: Optional[dict[str, Any]]
    model_policy_content: Optional[dict[str, Any]]
    edges: tuple[SpecDependencyEdge, ...]


class SpecResolver:
    """Exact-resolution cho registry (§7.3 của
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md):
    luôn yêu cầu definition_hash khớp tuyệt đối, không có floating "latest"
    resolution — production kernel chỉ dùng resolver này, không dùng registry
    repository trực tiếp."""

    def __init__(self, repository: SpecRegistryRepository) -> None:
        self._repository = repository

    async def resolve_exact(
        self,
        kind: str,
        spec_id: str,
        version: str,
        expected_definition_hash: str,
    ) -> dict[str, Any]:
        """Resolve đúng (kind, spec_id, version) và verify definition_hash khớp
        tuyệt đối. Raise SpecDependencyMissingError nếu không tìm thấy hoặc
        hash khác."""
        record = await self._repository.get(kind, spec_id, version)
        if record is None:
            raise SpecDependencyMissingError(kind, spec_id, version, "not_found")
        if record.definition_hash != expected_definition_hash:
            raise SpecDependencyMissingError(kind, spec_id, version, "hash_mismatch")
        return record.content

    async def resolve_agent_spec_dependencies(self, agent_spec: AgentSpec) -> AgentSpecResolution:
        """Resolve toàn bộ dependency đã pin (prompt_ref, model_policy_ref)
        của 1 AgentSpec bằng exact resolution, đồng thời tính lineage edges.
        Không resolve pinned_skills/tool_contract_refs ở đây — pinned_skills
        đã có SkillResolver riêng (packages/agent_core/skills/resolver.py),
        tool_contract_refs không đi qua registry (xem AgentSpec docstring)."""
        agent_hash = agent_spec.definition_hash or agent_spec.compute_hash()
        agent_record = await self.resolve_exact("agent", agent_spec.id, agent_spec.version, agent_hash)
        owner_identity = PinnedSpecIdentity(
            spec_kind="agent", spec_id=agent_spec.id, spec_version=agent_spec.version, definition_hash=agent_hash
        )

        prompt_content: Optional[dict[str, Any]] = None
        model_policy_content: Optional[dict[str, Any]] = None
        edges: list[SpecDependencyEdge] = []

        if agent_spec.prompt_ref is not None:
            ref = agent_spec.prompt_ref
            prompt_content = await self.resolve_exact(ref.spec_kind, ref.spec_id, ref.spec_version, ref.definition_hash)
            edges.append(SpecDependencyEdge(owner=owner_identity, dependency=ref, relation="uses_prompt"))

        if agent_spec.model_policy_ref is not None:
            ref = agent_spec.model_policy_ref
            model_policy_content = await self.resolve_exact(
                ref.spec_kind, ref.spec_id, ref.spec_version, ref.definition_hash
            )
            edges.append(SpecDependencyEdge(owner=owner_identity, dependency=ref, relation="uses_model_policy"))

        return AgentSpecResolution(
            agent_content=agent_record,
            prompt_content=prompt_content,
            model_policy_content=model_policy_content,
            edges=tuple(edges),
        )
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/registry/test_resolver.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Chạy toàn bộ `tests/agent_core/` để xác nhận cả Wave M2 (agent_core-only) không phá vỡ gì**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/ -v`
Expected: tất cả PASS (baseline trước Task 1 là 244 passed, 17 skipped — số PASSED sẽ tăng thêm đúng bằng số test mới đã viết ở Task 1-6, số SKIPPED giữ nguyên hoặc tương đương).

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/registry/resolver.py tests/agent_core/registry/test_resolver.py
git commit -m "feat(registry): add SpecResolver for exact dependency resolution and lineage edges"
```

---

## Sau khi hoàn thành plan này

Wave M2 (phần agent_core) xong khi cả 6 task trên commit và `./.venv/bin/python -m pytest tests/agent_core/ -v` xanh toàn bộ. Bước tiếp theo — **M2b (runtime wiring)** — cần một plan riêng, đụng tới `apps/cosa/`:

- Sửa `apps/cosa/agents/specs.py` để publish `COSA_FINANCE_AGENT_SPEC`/`COSA_OPERATIONS_AGENT_SPEC` vào registry (qua `publish_agent_spec()` từ plan này) thay vì chỉ định nghĩa làm Python constant.
- Sửa nơi dispatch Run (`apps/cosa/api/routes.py`, `apps/cosa/worker/handlers.py`) để dùng `SpecResolver.resolve_agent_spec_dependencies()` (từ Task 6 plan này) trước khi tạo `RunRecord`, thay vì import spec trực tiếp.
- Cần một `SpecRegistryRepository` instance thật (Postgres) được wire vào composition root (`apps/cosa/composition/agent_plane.py`) — hiện composition root đã có DB session factory cho các module khác, cần audit xem đã có sẵn hay cần thêm.

Không tự ý mở rộng phạm vi task hiện tại sang M2b khi thực thi plan này.
