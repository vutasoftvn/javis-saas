# COSA Marin Patterns — M6 Knowledge Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép 1 knowledge index dùng production được pin bằng exact version + fingerprint (`KnowledgeSnapshot`) thay vì AgentSpec chỉ trỏ tới workspace knowledge base "hiện tại" (luôn thay đổi, không reproducible).

**Architecture:** `packages/agent_core/knowledge/` hiện đã có `KnowledgeDocument`/`KnowledgeChunk` (per-workspace, mutable, migration 003) và `knowledge.source_versions` (per-source content-hash versioning, migration 010) — nhưng KHÔNG có khái niệm gộp nhiều source lại thành 1 artifact bất biến, publish/pin được như `PromptSpec`/`ModelPolicySpec`/`EvalSuite` đã có (Wave M2/M3). `KnowledgeSnapshot` (file mới, theo đúng pattern `compute_hash()`/`with_hash()`/`to_pinned_identity()`) lấp khoảng trống đó: pin `source_refs` (danh sách `{source_id, version, content_hash}` từ `knowledge.source_versions` đã có) + `chunking_recipe_version` + `embedding_model`/`embedding_version` + `index_recipe_version` + `retrieval_eval_run_id` (Optional, tham chiếu `EvalRun` Wave M3 nếu đã chạy retrieval quality eval). `AgentSpec` thêm `knowledge_snapshot_ref: Optional[PinnedSpecIdentity]` — pin theo đúng pattern `prompt_ref`/`model_policy_ref` (Wave M2), không tự "latest" resolve. Persistence là bảng MỚI `knowledge.snapshots` (không đụng bảng cũ — additive, giống cách migration 010 đã làm).

**Tech Stack:** Python 3.11, Pydantic v2, pytest + pytest-asyncio, PostgreSQL (docker-compose `cosa_postgres`, cùng pattern Task migration các Wave trước).

## Global Constraints

- **Số thứ tự migration `015_knowledge_snapshots.sql` giả định Wave M4 (`docs/superpowers/plans/2026-08-26-marin-patterns-m4-promotion-evidence.md`, migration `014_promotion_evidence.sql`) đã merge trước.** Nếu M4 CHƯA merge khi thực thi plan này, đổi số file migration ở Task 3 Step 1 thành `014_knowledge_snapshots.sql` thay vì `015_...` (kiểm tra `ls packages/agent_core/migrations/ | tail -3` trước khi đặt tên file, luôn dùng số kế tiếp thật, không giả định).
- Không tạo `ArtifactIdentity`/`ArtifactRef` dataclass mới — dùng `PinnedSpecIdentity` (`packages/agent_core/governance/contracts.py`).
- Không sửa `KnowledgeDocument`/`KnowledgeChunk`/`knowledge/store.py`/`knowledge/service.py` (mutable per-workspace ingestion, ranh giới riêng — Memory Item = durable runtime state, Knowledge Snapshot = reproducible artifact, theo §11.2 tài liệu gốc) — `KnowledgeSnapshot` chỉ THAM CHIẾU `source_id`/`version` đã có trong `knowledge.source_versions` (migration 010), không publish lại nội dung document/chunk.
- Không tạo bảng mới cho `chunking_recipe`/`embedding_policy` riêng — pin bằng string version đơn giản (`chunking_recipe_version: str`, `embedding_model: str`, `embedding_version: str`) trong `KnowledgeSnapshot`, KHÔNG cần registry-publish riêng cho từng thứ (khác `PromptSpec`/`ModelPolicySpec` vì các recipe này chưa có lifecycle publish độc lập nào — decision tương tự `tool_contract_refs` ở Wave M2, dùng string đơn giản thay vì registry-backed ref khi chưa có nhu cầu thật).
- `retrieval_eval_run_id` chỉ là `Optional[str]` tham chiếu `EvalRun.run_id` (Wave M3, `packages/agent_core/evals/artifacts.py`) — KHÔNG bắt buộc phải có (chưa chạy retrieval eval vẫn publish được snapshot, nhưng nên có trước khi coi là "production-ready" — đó là quyết định sử dụng, không phải validation cứng ở Wave M6 này).
- Comment mới viết tiếng Việt cho phần giải thích ý nghĩa/lý do; tên định danh giữ tiếng Anh.
- Không chạm `apps/cosa/*`/`services/*` trong plan này.

---

### Task 1: Mở rộng `PinnedSpecIdentity.spec_kind` thêm `"knowledge_snapshot"`

**Files:**
- Modify: `packages/agent_core/governance/contracts.py`
- Test: `tests/agent_core/governance/test_contracts.py`

**Interfaces:**
- Produces: `PinnedSpecIdentity.spec_kind` chấp nhận thêm `"knowledge_snapshot"` — Literal đầy đủ: `["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract", "eval_suite", "knowledge_snapshot"]`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/governance/test_contracts.py`:

```python
def test_pinned_spec_identity_accepts_knowledge_snapshot_kind():
    identity = PinnedSpecIdentity(
        spec_kind="knowledge_snapshot", spec_id="workspace-abc-kb", spec_version="3", definition_hash="a" * 64
    )
    assert identity.spec_kind == "knowledge_snapshot"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/governance/test_contracts.py -v -k knowledge_snapshot_kind`
Expected: FAIL — `pydantic.ValidationError`.

**Lưu ý:** nếu Wave M3 (`docs/superpowers/plans/2026-08-26-marin-patterns-m3-eval-artifacts.md`) đã merge trước, `spec_kind` Literal hiện tại đã có `"eval_suite"` — kiểm tra dòng thật trong file trước khi sửa (đừng giả định vị trí dòng cố định), chỉ THÊM `"knowledge_snapshot"` vào cuối tuple hiện có, không xoá giá trị nào.

- [ ] **Step 3: Sửa `PinnedSpecIdentity.spec_kind`**

Trong `packages/agent_core/governance/contracts.py`, thêm `"knowledge_snapshot"` vào cuối `Literal[...]` của field `spec_kind` (đọc dòng hiện tại trước — nếu Wave M3 đã merge sẽ là `Literal["agent", "workflow", "skill", "prompt", "model_policy", "tool_contract", "eval_suite"]`, nếu chưa sẽ thiếu `"eval_suite"` — trong trường hợp đó THÊM CẢ HAI `"eval_suite"` và `"knowledge_snapshot"` cùng lúc, không tự ý bỏ qua `"eval_suite"` dù không thuộc phạm vi Wave M6 này).

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/governance/test_contracts.py -v`
Expected: tất cả PASS.

- [ ] **Step 5: Chạy toàn bộ `tests/agent_core/governance/ tests/agent_core/contracts/ tests/agent_core/registry/` để xác nhận không phá vỡ consumer khác**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/governance/ tests/agent_core/contracts/ tests/agent_core/registry/ -v`
Expected: tất cả PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/governance/contracts.py tests/agent_core/governance/test_contracts.py
git commit -m "feat(governance): widen PinnedSpecIdentity.spec_kind to knowledge_snapshot"
```

---

### Task 2: `KnowledgeSnapshot` contract

**Files:**
- Create: `packages/agent_core/knowledge/snapshot.py`
- Modify: `packages/agent_core/knowledge/__init__.py` (thêm export)
- Test: `tests/agent_core/knowledge/test_knowledge_snapshot.py` (mới — `tests/agent_core/knowledge/__init__.py` đã tồn tại, không cần tạo)

**Interfaces:**
- Consumes: `PinnedSpecIdentity` (Task 1, đã mở rộng `knowledge_snapshot`).
- Produces: `KnowledgeSnapshot(id: str, version: str = "1.0.0", workspace_id: str, source_refs: list[dict[str, Any]] = [], chunking_recipe_version: str = "1.0", embedding_model: str, embedding_version: str, index_recipe_version: str = "1.0", retrieval_eval_run_id: Optional[str] = None, metadata: dict = {}, definition_hash: Optional[str] = None)` với `compute_hash()`, `with_hash()`, `to_pinned_identity() -> PinnedSpecIdentity`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/agent_core/knowledge/test_knowledge_snapshot.py`:

```python
from __future__ import annotations

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.knowledge.snapshot import KnowledgeSnapshot


def _base_kwargs() -> dict:
    return dict(
        id="workspace-abc.default_kb",
        workspace_id="workspace-abc",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "src_1", "version": 2, "content_hash": "a" * 64}],
    )


def test_knowledge_snapshot_has_sensible_defaults():
    snapshot = KnowledgeSnapshot(**_base_kwargs())

    assert snapshot.version == "1.0.0"
    assert snapshot.chunking_recipe_version == "1.0"
    assert snapshot.index_recipe_version == "1.0"
    assert snapshot.retrieval_eval_run_id is None
    assert snapshot.definition_hash is None


def test_knowledge_snapshot_compute_hash_is_deterministic():
    a = KnowledgeSnapshot(**_base_kwargs())
    b = KnowledgeSnapshot(**_base_kwargs())

    assert a.compute_hash() == b.compute_hash()


def test_knowledge_snapshot_compute_hash_ignores_source_refs_order():
    kwargs = _base_kwargs()
    kwargs["source_refs"] = [
        {"source_id": "src_1", "version": 1, "content_hash": "a" * 64},
        {"source_id": "src_2", "version": 1, "content_hash": "b" * 64},
    ]
    a = KnowledgeSnapshot(**kwargs)

    kwargs_reordered = dict(kwargs)
    kwargs_reordered["source_refs"] = list(reversed(kwargs["source_refs"]))
    b = KnowledgeSnapshot(**kwargs_reordered)

    assert a.compute_hash() == b.compute_hash()


def test_knowledge_snapshot_compute_hash_changes_when_source_content_hash_changes():
    kwargs_a = _base_kwargs()
    kwargs_b = _base_kwargs()
    kwargs_b["source_refs"] = [{"source_id": "src_1", "version": 2, "content_hash": "f" * 64}]

    a = KnowledgeSnapshot(**kwargs_a)
    b = KnowledgeSnapshot(**kwargs_b)

    assert a.compute_hash() != b.compute_hash()


def test_knowledge_snapshot_compute_hash_changes_when_embedding_version_changes():
    kwargs_a = _base_kwargs()
    kwargs_b = _base_kwargs()
    kwargs_b["embedding_version"] = "2"

    a = KnowledgeSnapshot(**kwargs_a)
    b = KnowledgeSnapshot(**kwargs_b)

    assert a.compute_hash() != b.compute_hash()


def test_knowledge_snapshot_with_hash_returns_a_copy_with_definition_hash_set():
    snapshot = KnowledgeSnapshot(**_base_kwargs())

    pinned = snapshot.with_hash()

    assert snapshot.definition_hash is None
    assert pinned.definition_hash == snapshot.compute_hash()


def test_knowledge_snapshot_to_pinned_identity_uses_knowledge_snapshot_kind():
    snapshot = KnowledgeSnapshot(version="3", **_base_kwargs()).with_hash()

    identity = snapshot.to_pinned_identity()

    assert identity == PinnedSpecIdentity(
        spec_kind="knowledge_snapshot",
        spec_id="workspace-abc.default_kb",
        spec_version="3",
        definition_hash=snapshot.definition_hash,
    )
```

- [ ] **Step 2: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/knowledge/test_knowledge_snapshot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.knowledge.snapshot'`.

- [ ] **Step 3: Viết `KnowledgeSnapshot`**

Tạo `packages/agent_core/knowledge/snapshot.py`:

```python
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity
from agent_core.governance.hashing import definition_hash

__all__ = ["KnowledgeSnapshot"]


class KnowledgeSnapshot(BaseModel):
    """Đặc tả knowledge snapshot có thể publish/pin độc lập — theo
    ADR-ARTIFACT-IDENTITY-001 (spec_kind="knowledge_snapshot", Wave M6).
    `source_refs` chỉ THAM CHIẾU (source_id, version, content_hash) đã có
    trong `knowledge.source_versions` (migration 010), KHÔNG publish lại nội
    dung document/chunk — Memory Item (mutable, `knowledge/store.py`) và
    Knowledge Snapshot (bất biến, ở đây) là 2 khái niệm tách biệt (§11.2
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md).
    `chunking_recipe_version`/`embedding_model`/`embedding_version`/
    `index_recipe_version` là string đơn giản — các recipe này chưa có
    publish/version lifecycle riêng qua registry (giống quyết định
    `tool_contract_refs` ở Wave M2), không cần registry-backed ref khi
    chưa có nhu cầu thật."""

    id: str
    version: str = "1.0.0"
    workspace_id: str
    source_refs: list[dict[str, Any]] = Field(default_factory=list)
    chunking_recipe_version: str = "1.0"
    embedding_model: str
    embedding_version: str
    index_recipe_version: str = "1.0"
    retrieval_eval_run_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    definition_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Tính SHA-256 hash chuẩn hoá — source_refs được sort theo
        (source_id, version) để đảm bảo thứ tự không ảnh hưởng fingerprint."""
        data = self.model_dump(exclude={"definition_hash"})
        data["source_refs"] = sorted(
            data["source_refs"], key=lambda r: (r.get("source_id", ""), r.get("version", 0))
        )
        return definition_hash(data)

    def with_hash(self) -> "KnowledgeSnapshot":
        """Trả về bản sao của KnowledgeSnapshot đã được gắn definition_hash xác thực."""
        return self.model_copy(update={"definition_hash": self.compute_hash()})

    def to_pinned_identity(self) -> PinnedSpecIdentity:
        """Chuyển đổi sang PinnedSpecIdentity để pin vào AgentSpec.knowledge_snapshot_ref."""
        h = self.definition_hash or self.compute_hash()
        return PinnedSpecIdentity(
            spec_kind="knowledge_snapshot",
            spec_id=self.id,
            spec_version=self.version,
            definition_hash=h,
        )
```

Sau đó mở `packages/agent_core/knowledge/__init__.py`, thêm:

```python
from agent_core.knowledge.snapshot import KnowledgeSnapshot
```

(đặt trước dòng `from agent_core.knowledge.store import ...`, giữ thứ tự alphabet theo module path: `chunking` < `models` < `service` < `snapshot` < `store`), và thêm `"KnowledgeSnapshot",` vào `__all__` (giữ thứ tự alphabet: sau `"KnowledgeDocument"`, trước `"KnowledgeIngestionService"`).

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/knowledge/test_knowledge_snapshot.py -v`
Expected: 7 PASSED.

- [ ] **Step 5: Chạy `tests/agent_core/knowledge/` đầy đủ để xác nhận `__init__.py` không vỡ import cũ**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/knowledge/ -v`
Expected: tất cả PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/knowledge/snapshot.py packages/agent_core/knowledge/__init__.py tests/agent_core/knowledge/test_knowledge_snapshot.py
git commit -m "feat(knowledge): add KnowledgeSnapshot as a pinnable, publishable artifact"
```

---

### Task 3: Migration + `KnowledgeSnapshotRepository`

**Files:**
- Create: `packages/agent_core/migrations/015_knowledge_snapshots.sql`
- Create: `packages/agent_core/knowledge/snapshot_repository.py`
- Test: `tests/agent_core/knowledge/test_snapshot_repository.py` (mới)

**Interfaces:**
- Consumes: `KnowledgeSnapshot` (Task 2), `SpecVersionHashConflictError` (`agent_core.registry.repository`, đã có, tái dùng — không tạo error type mới).
- Produces: `KnowledgeSnapshotRepository` Protocol + `InMemoryKnowledgeSnapshotRepository` + `PostgresKnowledgeSnapshotRepository`, mỗi cái có: `publish(snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot`, `get(snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]`.

- [ ] **Step 1: Viết migration**

Tạo `packages/agent_core/migrations/015_knowledge_snapshots.sql`:

```sql
-- Migration: 015_knowledge_snapshots.sql
-- Description: Bảng knowledge.snapshots — KnowledgeSnapshot artifact bất
--   biến (Wave M6). Additive — không đụng knowledge_sources/knowledge_chunks/
--   source_versions (migration 003 + 010). Snapshot chỉ THAM CHIẾU
--   source_id/version đã có qua content JSONB, không FK cứng tới
--   source_versions (1 snapshot có thể tham chiếu NHIỀU source_version cùng
--   lúc — quan hệ nhiều-nhiều không hợp với FK đơn giản trên 1 cột).
--
-- PRIMARY KEY (snapshot_id, version) — composite ngay từ đầu (khác
-- agent_evals.suites ở migration 008 vốn PK đơn cột do lịch sử, xem Wave M3
-- Task 5 comment về giới hạn đó) vì đây là bảng MỚI, không có ràng buộc kế
-- thừa nào.

CREATE TABLE IF NOT EXISTS knowledge.snapshots (
    snapshot_id VARCHAR(64) NOT NULL,
    version VARCHAR(32) NOT NULL,
    workspace_id VARCHAR(64) NOT NULL,
    definition_hash VARCHAR(64) NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (snapshot_id, version),
    CONSTRAINT uq_knowledge_snapshots_hash UNIQUE (snapshot_id, version, definition_hash)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_snapshots_workspace
    ON knowledge.snapshots(workspace_id);
```

- [ ] **Step 2: Đảm bảo Postgres đang chạy**

Run: `docker ps --filter "name=cosa_postgres" --format "{{.Status}}"`
Expected: dòng `Up ... (healthy)`. Nếu không có output, chạy `docker compose up -d postgres` từ `/Volumes/SSD/javis-saas`.

- [ ] **Step 3: Chạy migration thật**

Run: `cd /Volumes/SSD/javis-saas && export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://javis_app:<mật khẩu thật trong .env DATABASE_URL>@localhost:5432/javis" && ./.venv/bin/python -m packages.agent_core.scripts.migrate`
Expected: log hiển thị `015_knowledge_snapshots.sql` được áp dụng.

- [ ] **Step 4: Verify bằng psql**

Run: `docker exec cosa_postgres psql -U javis_app -d javis -c "\d knowledge.snapshots"`
Expected: đủ cột `snapshot_id, version, workspace_id, definition_hash, content, created_at`, PRIMARY KEY `(snapshot_id, version)`.

- [ ] **Step 5: Viết test thất bại cho repository (InMemory trước)**

Tạo `tests/agent_core/knowledge/test_snapshot_repository.py`:

```python
from __future__ import annotations

import pytest

from agent_core.knowledge.snapshot import KnowledgeSnapshot
from agent_core.knowledge.snapshot_repository import InMemoryKnowledgeSnapshotRepository
from agent_core.registry.repository import SpecVersionHashConflictError


def _snapshot(**overrides) -> KnowledgeSnapshot:
    base = dict(
        id="workspace-abc.default_kb",
        version="1",
        workspace_id="workspace-abc",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
        source_refs=[{"source_id": "src_1", "version": 1, "content_hash": "a" * 64}],
    )
    base.update(overrides)
    return KnowledgeSnapshot(**base)


@pytest.mark.asyncio
async def test_publish_snapshot_is_immutable_and_idempotent():
    repo = InMemoryKnowledgeSnapshotRepository()
    snapshot = _snapshot()

    published1 = await repo.publish(snapshot)
    assert published1.definition_hash == snapshot.with_hash().definition_hash

    published2 = await repo.publish(snapshot)
    assert published2.definition_hash == published1.definition_hash

    changed = _snapshot(embedding_version="2")
    with pytest.raises(SpecVersionHashConflictError):
        await repo.publish(changed)


@pytest.mark.asyncio
async def test_get_returns_none_when_not_published():
    repo = InMemoryKnowledgeSnapshotRepository()

    result = await repo.get("does.not.exist", "1")

    assert result is None


@pytest.mark.asyncio
async def test_get_returns_full_content_after_publish():
    repo = InMemoryKnowledgeSnapshotRepository()
    snapshot = _snapshot()
    await repo.publish(snapshot)

    fetched = await repo.get("workspace-abc.default_kb", "1")

    assert fetched is not None
    assert fetched.source_refs == [{"source_id": "src_1", "version": 1, "content_hash": "a" * 64}]
    assert fetched.embedding_model == "text-embedding-3-small"
```

- [ ] **Step 6: Chạy test, xác nhận FAIL với `ModuleNotFoundError`**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/knowledge/test_snapshot_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_core.knowledge.snapshot_repository'`.

- [ ] **Step 7: Viết `KnowledgeSnapshotRepository` (Protocol + InMemory + Postgres)**

Tạo `packages/agent_core/knowledge/snapshot_repository.py`:

```python
from __future__ import annotations

import json
from typing import Any, Optional, Protocol, runtime_checkable

from sqlalchemy import text

from agent_core.knowledge.snapshot import KnowledgeSnapshot
from agent_core.registry.repository import SpecVersionHashConflictError

__all__ = [
    "KnowledgeSnapshotRepository",
    "InMemoryKnowledgeSnapshotRepository",
    "PostgresKnowledgeSnapshotRepository",
]


@runtime_checkable
class KnowledgeSnapshotRepository(Protocol):
    """Protocol cho persistence KnowledgeSnapshot (knowledge.snapshots,
    migration 015, Wave M6)."""

    async def publish(self, snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot: ...
    async def get(self, snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]: ...


class InMemoryKnowledgeSnapshotRepository:
    """In-memory implementation — chỉ dùng test/local dev, không dùng
    production (không durable qua restart)."""

    def __init__(self) -> None:
        self._snapshots: dict[tuple[str, str], KnowledgeSnapshot] = {}

    async def publish(self, snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot:
        pinned = snapshot.with_hash() if snapshot.definition_hash is None else snapshot
        key = (pinned.id, pinned.version)
        existing = self._snapshots.get(key)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "knowledge_snapshot", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing.model_copy(deep=True)
        stored = pinned.model_copy(deep=True)
        self._snapshots[key] = stored
        return stored.model_copy(deep=True)

    async def get(self, snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]:
        r = self._snapshots.get((snapshot_id, version))
        return r.model_copy(deep=True) if r else None


class PostgresKnowledgeSnapshotRepository:
    """PostgreSQL implementation — persist vào knowledge.snapshots
    (migration 015). PRIMARY KEY (snapshot_id, version) composite ngay từ
    đầu — publish() có thể idempotent-check qua get() trước INSERT, tương
    tự PostgresSpecRegistryRepository (Wave M0/M1)."""

    def __init__(self, db_session_factory: Any) -> None:
        if db_session_factory is None:
            raise ValueError("PostgresKnowledgeSnapshotRepository requires a valid db_session_factory.")
        self._session_factory = db_session_factory

    async def publish(self, snapshot: KnowledgeSnapshot) -> KnowledgeSnapshot:
        pinned = snapshot.with_hash() if snapshot.definition_hash is None else snapshot
        existing = await self.get(pinned.id, pinned.version)
        if existing is not None:
            if existing.definition_hash != pinned.definition_hash:
                raise SpecVersionHashConflictError(
                    "knowledge_snapshot", pinned.id, pinned.version, existing.definition_hash, pinned.definition_hash
                )
            return existing

        async with self._session_factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO knowledge.snapshots (snapshot_id, version, workspace_id, definition_hash, content)
                    VALUES (:snapshot_id, :version, :workspace_id, :definition_hash, :content)
                    ON CONFLICT (snapshot_id, version) DO NOTHING
                    """
                ),
                {
                    "snapshot_id": pinned.id,
                    "version": pinned.version,
                    "workspace_id": pinned.workspace_id,
                    "definition_hash": pinned.definition_hash,
                    "content": json.dumps(pinned.model_dump(mode="json")),
                },
            )
            await session.commit()

        stored = await self.get(pinned.id, pinned.version)
        if stored is None:
            return pinned
        if stored.definition_hash != pinned.definition_hash:
            raise SpecVersionHashConflictError(
                "knowledge_snapshot", pinned.id, pinned.version, stored.definition_hash, pinned.definition_hash
            )
        return stored

    async def get(self, snapshot_id: str, version: str) -> Optional[KnowledgeSnapshot]:
        async with self._session_factory() as session:
            res = await session.execute(
                text(
                    """
                    SELECT content
                    FROM knowledge.snapshots
                    WHERE snapshot_id = :snapshot_id AND version = :version
                    """
                ),
                {"snapshot_id": snapshot_id, "version": version},
            )
            row = res.mappings().first()
            if row is None:
                return None
            content = row["content"]
            if isinstance(content, str):
                content = json.loads(content)
            return KnowledgeSnapshot(**content)
```

- [ ] **Step 8: Chạy lại test InMemory, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/knowledge/test_snapshot_repository.py -v`
Expected: 3 PASSED.

- [ ] **Step 9: Viết + chạy test Postgres thật**

Thêm vào cuối `tests/agent_core/knowledge/test_snapshot_repository.py`:

```python
import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent_core.knowledge.snapshot_repository import PostgresKnowledgeSnapshotRepository


def _pg_session_factory():
    url = os.environ.get(
        "AGENT_CORE_DATABASE_URL",
        "postgresql+asyncpg://javis_app:CHANGE_ME@localhost:5432/javis",
    )
    engine = create_async_engine(url)
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_postgres_knowledge_snapshot_repository_publish_and_get_roundtrip():
    repo = PostgresKnowledgeSnapshotRepository(_pg_session_factory())
    snapshot = _snapshot(id="test.knowledge_snapshot.pg_1", version="1")

    published = await repo.publish(snapshot)
    fetched = await repo.get("test.knowledge_snapshot.pg_1", "1")

    assert fetched is not None
    assert fetched.definition_hash == published.definition_hash
    assert fetched.source_refs == [{"source_id": "src_1", "version": 1, "content_hash": "a" * 64}]


@pytest.mark.asyncio
async def test_postgres_knowledge_snapshot_repository_rejects_hash_conflict():
    repo = PostgresKnowledgeSnapshotRepository(_pg_session_factory())
    snapshot = _snapshot(id="test.knowledge_snapshot.pg_2", version="1")
    await repo.publish(snapshot)

    changed = _snapshot(id="test.knowledge_snapshot.pg_2", version="1", embedding_version="99")
    with pytest.raises(SpecVersionHashConflictError):
        await repo.publish(changed)
```

Run: `cd /Volumes/SSD/javis-saas && export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://javis_app:<mật khẩu thật>@localhost:5432/javis" && ./.venv/bin/python -m pytest tests/agent_core/knowledge/test_snapshot_repository.py -v`
Expected: 5 PASSED (3 InMemory + 2 Postgres).

- [ ] **Step 10: Commit**

```bash
git add packages/agent_core/migrations/015_knowledge_snapshots.sql packages/agent_core/knowledge/snapshot_repository.py tests/agent_core/knowledge/test_snapshot_repository.py
git commit -m "feat(knowledge): add knowledge.snapshots migration and KnowledgeSnapshotRepository"
```

---

### Task 4: Pin `AgentSpec.knowledge_snapshot_ref`

**Files:**
- Modify: `packages/agent_core/contracts/spec.py`
- Test: `tests/agent_core/contracts/test_contracts_all.py`

**Interfaces:**
- Consumes: `KnowledgeSnapshot.to_pinned_identity()` (Task 2).
- Produces: `AgentSpec` có thêm field `knowledge_snapshot_ref: Optional[PinnedSpecIdentity] = None`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/agent_core/contracts/test_contracts_all.py` (file này đã import `PinnedSpecIdentity`/`AgentSpec` từ Wave M2 Task 3 — không cần thêm import đó lại; chỉ thêm import `KnowledgeSnapshot` nếu chưa có):

```python
from agent_core.knowledge.snapshot import KnowledgeSnapshot


def test_agent_spec_defaults_to_no_knowledge_snapshot_ref():
    spec = AgentSpec(id="test.agent.m6_1")

    assert spec.knowledge_snapshot_ref is None


def test_agent_spec_fingerprint_changes_when_knowledge_snapshot_ref_is_set():
    snapshot = KnowledgeSnapshot(
        id="workspace-abc.default_kb",
        version="1",
        workspace_id="workspace-abc",
        embedding_model="text-embedding-3-small",
        embedding_version="1",
    ).with_hash()
    base = AgentSpec(id="test.agent.m6_2")
    with_ref = base.model_copy(update={"knowledge_snapshot_ref": snapshot.to_pinned_identity()})

    assert base.compute_hash() != with_ref.compute_hash()
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/test_contracts_all.py -v -k knowledge_snapshot_ref`
Expected: FAIL — `pydantic.ValidationError` (field `knowledge_snapshot_ref` chưa tồn tại trên `AgentSpec`) hoặc test đầu tiên FAIL vì `spec.knowledge_snapshot_ref` raise `AttributeError`.

- [ ] **Step 3: Sửa `AgentSpec`**

Trong `packages/agent_core/contracts/spec.py`, thêm field vào ngay sau `tool_contract_refs: list[CapabilityImplementationIdentity] = Field(default_factory=list)`:

```python
    tool_contract_refs: list[CapabilityImplementationIdentity] = Field(default_factory=list)
    knowledge_snapshot_ref: Optional[PinnedSpecIdentity] = None
    memory_policy: dict[str, Any] = Field(default_factory=dict)
```

Cập nhật docstring của class — thêm 1 câu vào đoạn giải thích các `*_ref` đã có:

```text
`knowledge_snapshot_ref` pin 1 KnowledgeSnapshot đã publish (Wave M6) — khi
None, `knowledge_policy` (dict thô) vẫn là fallback. Không tự "latest"
resolve trong Run nếu reproducibility là yêu cầu (§11.3 tài liệu gốc).
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/contracts/test_contracts_all.py -v`
Expected: tất cả PASS.

- [ ] **Step 5: Chạy toàn bộ `tests/agent_core/` để xác nhận cả Wave M6 không phá vỡ gì**

Run: `cd /Volumes/SSD/javis-saas && ./.venv/bin/python -m pytest tests/agent_core/ -q`
Expected: tất cả PASS — field optional mới không phá vỡ consumer khác của `AgentSpec` (registry publisher, kernel, apps/cosa nếu đã merge M2b).

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/contracts/spec.py tests/agent_core/contracts/test_contracts_all.py
git commit -m "feat(contracts): pin AgentSpec.knowledge_snapshot_ref"
```

---

## Sau khi hoàn thành plan này

Wave M6 (agent_core-only, tối giản theo tinh thần P2/optional) xong khi cả 4 task trên commit và `AGENT_CORE_DATABASE_URL=... ./.venv/bin/python -m pytest tests/agent_core/ -v` xanh toàn bộ. Việc còn lại ngoài phạm vi:

- **Pipeline build snapshot thật** (`SourceSnapshot → Normalize → Chunk → Embed → Index → RetrievalQualityEval → KnowledgeSnapshot@version`) — Wave M6 chỉ xây artifact CÓ THỂ pin, chưa xây pipeline TẠO ra nó tự động. Có thể tái dùng `WorkflowEngine` + `CachingStep` (Wave M5) làm nền, nhưng đó là quyết định wiring riêng, cần plan mới khi có yêu cầu cụ thể.
- **`apps/cosa` đọc `knowledge_snapshot_ref`** — runtime thật sự dùng snapshot đã pin thay vì query `knowledge/store.py` "hiện tại" — thuộc phạm vi M2b-style runtime wiring, chưa có yêu cầu cụ thể.
- **Retrieval quality eval thật** ghi `EvalRun` với `target_kind="knowledge_snapshot"` rồi gán vào `retrieval_eval_run_id` — cần 1 quy trình chạy retrieval eval thật (query mẫu → so khớp expected chunk → tính pass_rate), chưa có trong phạm vi Wave M3 hay M6.

Không tự ý mở rộng phạm vi task hiện tại sang các mục trên khi thực thi plan này.
