# COSA Local-First Event-Driven Agent Operating Model — P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Biến ba tiền đề an toàn cho automated event triggers thành production-grade — memory/RAG chỉ chạy trên store bền + scanner thật + retrieval đã eval; multi-agent fan-out có child task bền sống sót crash; và một trigger rule chỉ được `enabled` khi có immutable eval/promotion evidence khớp fingerprint hiện tại.

**Architecture:** Không thêm engine điều phối thứ hai. Task 1 siết composition root: `MemoryService` / `KnowledgeIngestionService` production đòi dependency tường minh, fail activation nếu thiếu; semantic retrieval chỉ bật sau ngưỡng benchmark, luôn giữ lexical fallback + citations, và mọi enable ghi `retrieval_eval_run_id` vào `KnowledgeSnapshot`. Task 2 thêm `DurableSupervisor` adapter dùng lại durable scheduler của `services/cosa` (atomic claim + fencing + visibility + DLQ) để persist child identity/dependency/join state; `asyncio.gather` coordinator chỉ còn hợp lệ cho local pure computation. Task 3 nối `PromotionGate` (hiện read-only) làm release gate cho `EventTriggerRule.enabled` — artifact-only evidence chỉ mở artifact-only rule; write rule đòi human approval decision.

**Tech Stack:** Python 3.11, Pydantic, SQLAlchemy/asyncpg, pytest, pytest-asyncio. TypeScript strict, Encore, Drizzle ORM, PostgreSQL 16, Vitest.

**Spec:** `docs/superpowers/specs/2026-08-28-event-driven-agent-operating-model-design.md` (commit `cb080b77`). Plan này phủ **P1** = spec Task 6, 7, 8. Đi sau **P0** (`2026-08-28-event-driven-agent-operating-model-p0.md`) — cần `EventTriggerRule` từ P0 Task 4.

## Global Constraints

- **TDD bắt buộc**: test đỏ → xác nhận đỏ → implement tối thiểu → xác nhận xanh → commit. Không tuyên bố xong khi chưa chạy test (CLAUDE.md #11).
- **An toàn working tree** (CLAUDE.md #10): `git status` trước thao tác mất dữ liệu; không `--force`/`--no-verify`; không tự xoá/archive file không liên quan.
- **`packages/agent_core` KHÔNG import từ `apps/` hay `services/`.** Adapter Python cho durable scheduler nằm ở `apps/cosa/` hoặc gọi qua HTTP client abstraction đã có; contract kiểu ở `agent_core`.
- **Không production in-memory fallback.** Giữ được injection in-memory cho test (`MemoryService.in_memory()`, `scanner=FakeDocumentMalwareScanner(...)` chỉ khi caller truyền tường minh).
- **Capability Gateway giữ thẩm quyền ở MỌI child action.** Durable supervisor chỉ schedule by reference; resume/retry sau crash không được replay external side effect.
- **`agent_core` chỉ TẠO promotion evidence, KHÔNG tự activate.** Quyết định enable cuối cùng ở caller (`apps/cosa` / `services/cosa`). Gate chỉ trả `approved`/`blocking_issues`.
- **Migration number**: kiểm `ls packages/agent_core/migrations/` và `ls services/cosa/migrations/` ngay trước khi tạo. P0 đã dùng `packages/agent_core/migrations/017_event_inbox.sql` ⇒ file mới `018_...`.
- **DoD P1** (spec §7): #5 (drift ⇒ trigger disable/reject tới khi có evidence mới duyệt); #6 (RAG publication event chỉ sau durable storage + real scan + review + snapshot identity); #7 (supervisor crash/restart giữ child-task status + approval gate + idempotency, không replay side effect).
- **Comment tiếng Việt cho why**; identifier/log/error tiếng Anh.

---

## Dependencies vào các plan khác

| Cần | Nguồn | Vì sao |
| --- | --- | --- |
| `EventTriggerRule` dataclass (`apps/cosa/events/trigger_policy.py`) | P0 Task 4 | Task 3 thêm field `eval_evidence_ref` + gate vào `resolve()` / enable path. |
| `integration.event_outbox` + relay | P0 Task 3–4 | Task 1: `knowledge.source.published.v1` được append qua cùng `appendOutboxEvent` pattern. |
| Local execution plane (`COSA_EXECUTION_PLANE_URL`, scheduler tại local node) | **`SPEC-EXEC-PLANE-SPLIT`** | **Task 2 BỊ CHẶN** tới khi spec này merged — durable child task schedule qua local scheduler, không được rơi về platform VPS. |

Task 1 và Task 3 **không** bị chặn bởi `SPEC-EXEC-PLANE-SPLIT`. Thứ tự thực thi khuyến nghị: Task 1 → Task 3 → (chờ split) → Task 2.

---

## File Structure

| File | Trách nhiệm sau khi implement |
| --- | --- |
| `packages/agent_core/memory/service.py` | `__init__` đòi `store` tường minh; `MemoryService.in_memory()` classmethod cho test; `MemoryService.for_production(database_url)` dùng `get_memory_store()` (đã fail-fast sẵn). |
| `packages/agent_core/memory/retention.py` | `RetentionPolicy` (TTL theo kind, max item/scope) — tham số bắt buộc của production service. |
| `apps/cosa/knowledge_ingestion/handler.py` | Bỏ default `FakeDocumentMalwareScanner`; production đòi `scanner`/`object_store`/`knowledge_service` inject; gọi `assert_production_scanner_ready(scanner)` khi env prod. |
| `apps/cosa/api/routes.py:1168` | Bỏ `KnowledgeIngestionService()` default — lấy từ `request.app.state.plane`. |
| `apps/cosa/knowledge_ingestion/publish.py` | Sau human review/publish + persistent status update + `KnowledgeSnapshot.with_hash()`, append `knowledge.source.published.v1` (reference-only) qua outbox. |
| `packages/agent_core/knowledge/retrieval.py` | `KnowledgeRetrievalConfig(mode, min_eval_score)`; `retrieve()` chọn semantic nếu eval đạt ngưỡng, ngược lại lexical fallback; luôn trả citations. |
| `packages/agent_core/knowledge/providers/postgres.py` | Thêm `search_chunks_semantic()` dùng `chunk_embeddings`; giữ `search_chunks()` lexical. |
| `packages/agent_core/coordination/durable_supervisor.py` | `ChildTaskSpec`, `DurableSupervisor.spawn()/resume()`; persist qua scheduler; idempotency theo `child_id`. |
| `packages/agent_core/coordination/parallel.py` | `execute_parallel()` raise nếu bất kỳ `ParallelTask.spec` có write capability (chỉ còn cho pure computation). |
| `packages/agent_core/coordination/supervisor.py` | `SupervisorCoordinator` production path uỷ quyền cho `DurableSupervisor`; giữ `_parallel` chỉ cho read-only synthesis. |
| `services/cosa/storage/control-plane-schema.ts` | Thêm cột `parent_task_id`, `depends_on` (jsonb), `join_policy` vào `scheduledTasks`; comment nhóm bảng = local execution profile. |
| `services/cosa/services/control-plane-scheduler.service.ts` | `scheduleChildTask()`, `resolveJoin()` — tái dùng claim/fence/DLQ hiện có. |
| `services/cosa/migrations/NNN_scheduled_task_child_edges.up.sql` | Migration cột child/dependency/join. |
| `apps/cosa/events/trigger_policy.py` | `EventTriggerRule` thêm `eval_evidence_ref: str | None`; `resolve()` trả `policy_denied/stale_eval_evidence` khi rule mode ≠ `artifact_only` mà evidence thiếu/stale. |
| `apps/cosa/events/trigger_promotion.py` | `can_enable_trigger(rule, evidence, current_fingerprints) -> GateResult`; nối `PromotionGate`. |
| `apps/cosa/agents/seed.py` | Khi seed, gắn evidence ref cho rule mẫu (nếu có); rule write-capable ⇒ `enabled=False` tới khi có approval. |
| `packages/agent_core/evals/models.py` | Thêm `EventTriggerEvalSuite` (event schema version, fixtures, policy version, action boundary, failure injection). |
| `tests/**`, `services/**/tests/**` | Production-wiring, retrieval-eval, durable-workflow crash-recovery, stale-evidence gate. |

---

### Task 1: Memory & RAG là tiền đề an toàn cho event-driven knowledge refresh  *(spec Task 6)*

**Files:**
- Modify: `packages/agent_core/memory/service.py`
- Create: `packages/agent_core/memory/retention.py`
- Create: `packages/agent_core/knowledge/retrieval.py`
- Modify: `packages/agent_core/knowledge/providers/postgres.py`
- Modify: `apps/cosa/knowledge_ingestion/handler.py:133-149`
- Modify: `apps/cosa/api/routes.py:1168`
- Create: `apps/cosa/knowledge_ingestion/publish.py`
- Test: `tests/apps/cosa/test_knowledge_production_wiring.py`
- Test: `tests/agent_core/knowledge/test_retrieval_evals.py`
- Test: `tests/agent_core/memory/test_memory_service_production_guard.py`

**Interfaces:**
- Consumes: `get_memory_store()` (`packages/agent_core/memory/store.py:48` — đã fail-fast khi thiếu `AGENT_CORE_DATABASE_URL`); `assert_production_scanner_ready()` (`apps/cosa/knowledge_ingestion/scanner.py:82`); `KnowledgeSnapshot` (`packages/agent_core/knowledge/snapshot.py`, đã có `retrieval_eval_run_id`, `with_hash()`, `to_pinned_identity()`); `appendOutboxEvent` + envelope builder (P0 Task 2–3).
- Produces:
  - `MemoryService.__init__(self, store: MemoryStore, *, retention: RetentionPolicy)` — `store` bắt buộc.
  - `MemoryService.in_memory() -> MemoryService` — classmethod cho test (InMemoryMemoryStore + `RetentionPolicy.permissive()`).
  - `MemoryService.for_production(database_url: str | None = None) -> MemoryService`.
  - `class RetentionPolicy` — `ttl_by_kind: dict[MemoryKind, timedelta]`, `max_items_per_scope: int`; `RetentionPolicy.permissive()` classmethod.
  - `class KnowledgeRetrievalConfig` — `mode: Literal["lexical", "semantic"]`, `min_eval_score: float = 0.7`.
  - `async def retrieve(store, config, *, workspace_id, query, limit, eval_score: float | None) -> RetrievalResult` — `RetrievalResult{ chunks: list[KnowledgeChunk], citations: list[Citation], mode_used: str, fell_back: bool }`.
  - `PostgresKnowledgeStore.search_chunks_semantic(workspace_id, query_embedding, limit) -> list[KnowledgeChunk]`.
  - `publish_knowledge_source(review_result, snapshot: KnowledgeSnapshot) -> None` — chỉ append `knowledge.source.published.v1` khi `review_result.approved and review_result.persistent_status == "published" and snapshot.definition_hash`.
- Later tasks: none (Task 3 độc lập).

- [ ] **Step 1: Test đỏ — memory production guard**

Create `tests/agent_core/memory/test_memory_service_production_guard.py`:

```python
import pytest
from agent_core.memory.service import MemoryService
from agent_core.memory.store import InMemoryMemoryStore
from agent_core.memory.retention import RetentionPolicy


def test_init_requires_explicit_store() -> None:
    with pytest.raises(TypeError):
        MemoryService()  # type: ignore[call-arg]


def test_in_memory_helper_is_explicit_and_test_only() -> None:
    svc = MemoryService.in_memory()
    assert isinstance(svc._store, InMemoryMemoryStore)


def test_for_production_fails_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("AGENT_CORE_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="AGENT_CORE_DATABASE_URL"):
        MemoryService.for_production()


def test_production_service_carries_explicit_retention() -> None:
    svc = MemoryService(InMemoryMemoryStore(), retention=RetentionPolicy.permissive())
    assert svc._retention is not None
```

- [ ] **Step 2: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/memory/test_memory_service_production_guard.py -q`
Expected: FAIL — `MemoryService()` hiện hợp lệ (default `InMemoryMemoryStore`); `retention.py` chưa tồn tại.

- [ ] **Step 3: Viết `retention.py` + siết `MemoryService`**

Create `packages/agent_core/memory/retention.py`:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import timedelta
from agent_core.memory.models import MemoryKind

@dataclass(frozen=True)
class RetentionPolicy:
    """Chính sách lifecycle bộ nhớ — production service PHẢI khai báo tường
    minh, không để mặc định ngầm (spec §Task 6)."""
    ttl_by_kind: dict[MemoryKind, timedelta] = field(default_factory=dict)
    max_items_per_scope: int = 10_000

    @classmethod
    def permissive(cls) -> "RetentionPolicy":
        return cls(ttl_by_kind={}, max_items_per_scope=1_000_000)
```

Rewrite `packages/agent_core/memory/service.py` `__init__`:

```python
def __init__(self, store: MemoryStore, *, retention: "RetentionPolicy") -> None:
    self._store = store
    self._retention = retention

@classmethod
def in_memory(cls) -> "MemoryService":
    from agent_core.memory.store import InMemoryMemoryStore
    from agent_core.memory.retention import RetentionPolicy
    return cls(InMemoryMemoryStore(), retention=RetentionPolicy.permissive())

@classmethod
def for_production(cls, database_url: str | None = None) -> "MemoryService":
    from agent_core.memory.store import get_memory_store   # raises nếu thiếu AGENT_CORE_DATABASE_URL
    from agent_core.memory.retention import RetentionPolicy
    return cls(get_memory_store(database_url), retention=RetentionPolicy())
```

`grep -rn "MemoryService(" packages apps --include='*.py'` — hiện 0 production call-site; cập nhật mọi test dùng `MemoryService()` → `MemoryService.in_memory()`.

- [ ] **Step 4: Chạy — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/memory/ -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/memory/ tests/agent_core/memory/
git commit -m "feat(memory): production service requires explicit store + retention"
```

- [ ] **Step 6: Test đỏ — knowledge ingestion production wiring**

Create `tests/apps/cosa/test_knowledge_production_wiring.py`:

```python
import io
import pytest
from apps.cosa.knowledge_ingestion.handler import execute_knowledge_ingestion_task
from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner


async def test_production_rejects_fake_scanner(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")
    with pytest.raises(RuntimeError, match="production scanner"):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion", "ingestion_id": "ing_1"},
            claim_token="tok",
            scanner=FakeDocumentMalwareScanner(verdict="clean"),
        )


async def test_production_requires_injected_dependencies(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("KNOWLEDGE_INGESTION_ENABLED", "true")
    with pytest.raises(RuntimeError, match="must be injected"):
        await execute_knowledge_ingestion_task(
            {"task_type": "knowledge_ingestion", "ingestion_id": "ing_1"},
            claim_token="tok",
        )  # scanner/object_store/knowledge_service đều None
```

- [ ] **Step 7: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_knowledge_production_wiring.py -q`
Expected: FAIL — handler hiện im lặng dựng `FakeDocumentMalwareScanner(verdict="clean")` + `S3DocumentObjectStore()` + `KnowledgeIngestionService()`.

- [ ] **Step 8: Siết handler injection**

Rewrite `apps/cosa/knowledge_ingestion/handler.py:132-149`:

```python
import os
from apps.cosa.knowledge_ingestion.scanner import assert_production_scanner_ready

_is_prod = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower() in ("production", "staging", "prod")

if _is_prod:
    missing = [n for n, v in [("scanner", scanner), ("object_store", object_store),
                              ("knowledge_service", knowledge_service)] if v is None]
    if missing:
        raise RuntimeError(f"knowledge ingestion dependencies must be injected in production: {missing}")
    assert_production_scanner_ready(scanner)   # raise nếu FakeDocumentMalwareScanner

# Dev/test defaults (chỉ khi KHÔNG phải production)
if object_store is None:
    from apps.cosa.knowledge_ingestion.object_store import S3DocumentObjectStore
    object_store = S3DocumentObjectStore()
if scanner is None:
    from apps.cosa.knowledge_ingestion.scanner import FakeDocumentMalwareScanner
    scanner = FakeDocumentMalwareScanner(verdict="clean")
if sandbox is None:
    sandbox = DocumentConversionSandbox()
if knowledge_service is None:
    knowledge_service = KnowledgeIngestionService()
if control_plane_client is None:
    control_plane_client = DocumentIngestionControlPlaneClient()
```

`apps/cosa/api/routes.py:1168`: thay `knowledge_service = KnowledgeIngestionService()` bằng `knowledge_service = request.app.state.plane.knowledge_ingestion_service` (thêm attribute vào `CosaAgentPlane` trong `agent_plane.py`, dựng từ Postgres provider — fail-fast nếu thiếu `AGENT_CORE_DATABASE_URL`, theo pattern `agent_plane.py:177-251`).

- [ ] **Step 9: Chạy — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_knowledge_production_wiring.py tests/apps/cosa/knowledge_ingestion -q`
Expected: PASS.

- [ ] **Step 10: Test đỏ — retrieval eval gate + fallback**

Create `tests/agent_core/knowledge/test_retrieval_evals.py`:

```python
import pytest
from agent_core.knowledge.retrieval import KnowledgeRetrievalConfig, retrieve
from agent_core.knowledge.store import InMemoryKnowledgeStore
# ... helper seed_chunks(store, workspace_id, docs) ...


async def test_semantic_below_threshold_falls_back_to_lexical_with_citations() -> None:
    store = InMemoryKnowledgeStore()
    await seed_chunks(store, "ws_1", [("doc_a", "quarterly revenue grew 12%")])
    cfg = KnowledgeRetrievalConfig(mode="semantic", min_eval_score=0.8)
    res = await retrieve(store, cfg, workspace_id="ws_1", query="revenue", limit=5, eval_score=0.5)
    assert res.mode_used == "lexical" and res.fell_back is True
    assert res.citations and all(c.source_id for c in res.citations)


async def test_semantic_used_when_eval_meets_threshold() -> None:
    store = InMemoryKnowledgeStore()
    await seed_chunks(store, "ws_1", [("doc_a", "quarterly revenue grew 12%")])
    cfg = KnowledgeRetrievalConfig(mode="semantic", min_eval_score=0.8)
    res = await retrieve(store, cfg, workspace_id="ws_1", query="revenue", limit=5, eval_score=0.9)
    assert res.mode_used == "semantic" and res.fell_back is False


async def test_citations_always_point_to_workspace_scoped_published_source() -> None:
    store = InMemoryKnowledgeStore()
    await seed_chunks(store, "ws_1", [("doc_a", "alpha")])
    await seed_chunks(store, "ws_2", [("doc_b", "alpha")])
    res = await retrieve(store, KnowledgeRetrievalConfig(mode="lexical"),
                         workspace_id="ws_1", query="alpha", limit=5, eval_score=None)
    assert {c.workspace_id for c in res.citations} == {"ws_1"}
```

Create `tests/apps/cosa/test_knowledge_production_wiring.py::test_publish_event_only_after_durable_review` (thêm vào file Step 6):

```python
async def test_publish_event_only_after_durable_review(outbox_probe) -> None:
    from apps.cosa.knowledge_ingestion.publish import publish_knowledge_source
    review = ReviewResult(approved=True, persistent_status="published")
    snapshot = make_snapshot(workspace_id="ws_1").with_hash()
    await publish_knowledge_source(review, snapshot)
    assert outbox_probe.last().eventType == "knowledge.source.published.v1"
    assert set(outbox_probe.last().envelope["payload"].keys()) == {
        "sourceId", "snapshotId", "embeddingModel", "indexRecipeVersion", "reviewedBy", "reviewedAt"}

async def test_publish_event_suppressed_when_review_not_persisted(outbox_probe) -> None:
    from apps.cosa.knowledge_ingestion.publish import publish_knowledge_source
    review = ReviewResult(approved=True, persistent_status="pending")  # chưa persist
    await publish_knowledge_source(review, make_snapshot("ws_1").with_hash())
    assert outbox_probe.empty()
```

- [ ] **Step 11: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/knowledge/test_retrieval_evals.py tests/apps/cosa/test_knowledge_production_wiring.py -q`
Expected: FAIL — `agent_core.knowledge.retrieval` + `apps.cosa.knowledge_ingestion.publish` chưa tồn tại.

- [ ] **Step 12: Viết `retrieval.py` + `search_chunks_semantic` + `publish.py`**

`packages/agent_core/knowledge/retrieval.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class KnowledgeRetrievalConfig:
    mode: Literal["lexical", "semantic"] = "lexical"
    min_eval_score: float = 0.7

@dataclass(frozen=True)
class Citation:
    source_id: str
    workspace_id: str
    chunk_id: str

@dataclass
class RetrievalResult:
    chunks: list
    citations: list[Citation]
    mode_used: str
    fell_back: bool

async def retrieve(store, config: KnowledgeRetrievalConfig, *, workspace_id: str,
                   query: str, limit: int, eval_score: float | None) -> RetrievalResult:
    want_semantic = config.mode == "semantic" and eval_score is not None and eval_score >= config.min_eval_score
    if want_semantic and hasattr(store, "search_chunks_semantic"):
        chunks = await store.search_chunks_semantic(workspace_id=workspace_id, query=query, limit=limit)
        mode_used, fell_back = "semantic", False
    else:
        chunks = await store.search_chunks(workspace_id=workspace_id, query=query, limit=limit)
        mode_used = "lexical"
        fell_back = config.mode == "semantic"
    citations = [Citation(source_id=c.source_id, workspace_id=c.workspace_id, chunk_id=c.id)
                 for c in chunks if c.workspace_id == workspace_id]
    return RetrievalResult(chunks=chunks, citations=citations, mode_used=mode_used, fell_back=fell_back)
```

`packages/agent_core/knowledge/providers/postgres.py` — thêm `search_chunks_semantic(self, *, workspace_id, query, limit)`: embed `query`, `ORDER BY chunk_embeddings.embedding <-> :qvec LIMIT :limit` (pgvector) với `WHERE workspace_id = :ws`. Giữ nguyên `search_chunks()` lexical làm fallback. Docstring: chỉ dùng sau khi `retrieval_eval_run_id` được set trên snapshot đang phục vụ.

`apps/cosa/knowledge_ingestion/publish.py`:

```python
from __future__ import annotations
from agent_core.knowledge.snapshot import KnowledgeSnapshot

async def publish_knowledge_source(review_result, snapshot: KnowledgeSnapshot) -> None:
    """Append knowledge.source.published.v1 CHỈ khi review đã approve, trạng
    thái đã persist 'published', và snapshot có definition_hash (identity xác
    thực). Payload reference-only — không nội dung document/chunk (spec DoD #6)."""
    if not (getattr(review_result, "approved", False)
            and getattr(review_result, "persistent_status", None) == "published"
            and snapshot.definition_hash):
        return
    envelope = make_business_event(
        event_type="knowledge.source.published.v1",
        workspace_id=snapshot.workspace_id,
        aggregate_type="knowledge_source",
        aggregate_id=snapshot.id,
        correlation_id=review_result.correlation_id,
        actor={"kind": "user", "id": review_result.reviewed_by},
        classification="internal",
        payload={
            "sourceId": snapshot.id,
            "snapshotId": snapshot.to_pinned_identity().definition_hash,
            "embeddingModel": snapshot.embedding_model,
            "indexRecipeVersion": snapshot.index_recipe_version,
            "reviewedBy": review_result.reviewed_by,
            "reviewedAt": review_result.reviewed_at,
        },
    )
    await append_outbox_event(envelope)   # cùng repository pattern P0 Task 3 (phía Python: HTTP tới company, hoặc shared outbox nếu review chạy trong company tx)
```

> Nếu review/publish chạy trong `services/cosa` (TS), triển khai `publish_knowledge_source` tương ứng phía TS dùng `appendOutboxEvent(tx, ...)` trong cùng transaction cập nhật status. Chọn phía theo nơi review persist thực tế — kiểm `grep -rn "REVIEW_PENDING\|review.*publish" services/cosa apps/cosa`.

- [ ] **Step 13: Chạy — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/knowledge/ tests/apps/cosa/test_knowledge_production_wiring.py -q`
Expected: PASS.

- [ ] **Step 14: Commit**

```bash
git add packages/agent_core/knowledge/ apps/cosa/knowledge_ingestion/ apps/cosa/api/routes.py \
        apps/cosa/composition/agent_plane.py tests/agent_core/knowledge/ tests/apps/cosa/test_knowledge_production_wiring.py
git commit -m "feat(knowledge): production wiring guards, evaluated retrieval w/ lexical fallback, reviewed publish event"
```

---

### Task 2: Durable multi-agent supervisor  *(spec Task 7 — BỊ CHẶN tới khi `SPEC-EXEC-PLANE-SPLIT` merged)*

> **Không bắt đầu task này** cho tới khi `SPEC-EXEC-PLANE-SPLIT` đã merge và local execution scheduler chạy dưới `COSA_EXECUTION_PLANE_URL`. Child task phải schedule qua local scheduler; không được rơi về platform VPS (ADR-LOCAL-FIRST-001 §Execution-plane rule).

**Files:**
- Create: `packages/agent_core/coordination/durable_supervisor.py`
- Modify: `packages/agent_core/coordination/parallel.py`
- Modify: `packages/agent_core/coordination/supervisor.py`
- Modify: `packages/agent_core/workflows/engine.py` (expose child-task hook, không thêm engine mới)
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Modify: `services/cosa/services/control-plane-scheduler.service.ts`
- Create: `services/cosa/migrations/NNN_scheduled_task_child_edges.up.sql` (xác nhận NNN)
- Test: `tests/agent_core/coordination/test_durable_supervisor_workflow.py`
- Modify: `services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts`

**Interfaces:**
- Consumes: `services/cosa/services/control-plane-scheduler.service.ts` — `scheduleTask` / `pollDueTasks` / `heartbeatTask` / `completeTask` / `reclaimStuckTasks` (atomic claim `FOR UPDATE SKIP LOCKED`, `claim_token` fencing, `visibility_timeout_at`, retry backoff, dead-letter — đã có). `PinnedSpecIdentity` (`agent_core.governance.contracts`).
- Produces:
  - `@dataclass(frozen=True) class ChildTaskSpec` — `child_id: str`, `parent_run_id: str`, `agent_spec: PinnedSpecIdentity`, `depends_on: tuple[str, ...]`, `budget: Budget`, `mode: Literal["artifact_only","proposal","write"]`.
  - `@dataclass class SupervisionHandle` — `handle_id: str`, `children: dict[str, ChildState]`, `join: Literal["all","any","quorum"]`, `quorum: int | None`.
  - `class DurableSupervisor` — `async spawn(self, children: list[ChildTaskSpec], *, join, quorum=None) -> SupervisionHandle`; `async resume(self, handle_id: str) -> SupervisionHandle`; `async record_child_result(self, handle_id, child_id, result, idempotency_key) -> None` (idempotent theo `(child_id, idempotency_key)`); `def is_join_satisfied(self, handle: SupervisionHandle) -> bool`.
  - `scheduleChildTask(params: { parentTaskId, childId, dependsOn, joinPolicy, ...ScheduleParams }): Promise<ScheduledTaskRow>` (TS).
  - `resolveJoin(parentTaskId): Promise<{ satisfied: boolean; completed: string[]; pending: string[] }>` (TS).
- Later tasks: none.

- [ ] **Step 1: Test đỏ — cross-process durable workflow (Python)**

Create `tests/agent_core/coordination/test_durable_supervisor_workflow.py`:

```python
import pytest
from agent_core.coordination.durable_supervisor import DurableSupervisor, ChildTaskSpec
# fixture durable_scheduler = client tới scheduler thật (local test DB), KHÔNG in-process fake


async def test_supervisor_crash_after_two_of_three_children_resumes(durable_scheduler, pinned):
    sup = DurableSupervisor(scheduler=durable_scheduler)
    handle = await sup.spawn([ChildTaskSpec(f"c{i}", "run_1", pinned, (), budget(), "artifact_only")
                              for i in range(3)], join="all")
    await sup.record_child_result(handle.handle_id, "c0", {"ok": 1}, idempotency_key="k0")
    await sup.record_child_result(handle.handle_id, "c1", {"ok": 1}, idempotency_key="k1")
    # simulate process restart
    resumed = await DurableSupervisor(scheduler=durable_scheduler).resume(handle.handle_id)
    assert resumed.children["c0"].status == "completed"
    assert resumed.children["c2"].status in ("pending", "claimed")
    assert not DurableSupervisor(scheduler=durable_scheduler).is_join_satisfied(resumed)


async def test_child_retry_with_existing_idempotency_claim_no_duplicate_side_effect(durable_scheduler, pinned, side_effect_probe):
    sup = DurableSupervisor(scheduler=durable_scheduler)
    handle = await sup.spawn([ChildTaskSpec("c0", "run_2", pinned, (), budget(), "write")], join="all")
    await sup.record_child_result(handle.handle_id, "c0", {"ok": 1}, idempotency_key="k0")
    await sup.record_child_result(handle.handle_id, "c0", {"ok": 1}, idempotency_key="k0")  # replay
    assert side_effect_probe.count == 1


async def test_dependency_edge_blocks_child_until_parent_completes(durable_scheduler, pinned):
    sup = DurableSupervisor(scheduler=durable_scheduler)
    handle = await sup.spawn([
        ChildTaskSpec("a", "run_3", pinned, (), budget(), "artifact_only"),
        ChildTaskSpec("b", "run_3", pinned, ("a",), budget(), "artifact_only"),
    ], join="all")
    assert handle.children["b"].status == "blocked"
    await sup.record_child_result(handle.handle_id, "a", {"ok": 1}, idempotency_key="ka")
    refreshed = await sup.resume(handle.handle_id)
    assert refreshed.children["b"].status in ("pending", "claimed")


async def test_join_quorum_satisfied_after_worker_restart(durable_scheduler, pinned):
    sup = DurableSupervisor(scheduler=durable_scheduler)
    handle = await sup.spawn([ChildTaskSpec(f"c{i}", "run_4", pinned, (), budget(), "artifact_only")
                              for i in range(3)], join="quorum", quorum=2)
    await sup.record_child_result(handle.handle_id, "c0", {}, idempotency_key="k0")
    await sup.record_child_result(handle.handle_id, "c1", {}, idempotency_key="k1")
    resumed = await DurableSupervisor(scheduler=durable_scheduler).resume(handle.handle_id)
    assert DurableSupervisor(scheduler=durable_scheduler).is_join_satisfied(resumed)


async def test_child_awaiting_approval_does_not_busy_loop(durable_scheduler, pinned):
    sup = DurableSupervisor(scheduler=durable_scheduler)
    handle = await sup.spawn([ChildTaskSpec("c0", "run_5", pinned, (), budget(), "write")], join="all")
    # child schedules một approval wait — handle vẫn ở trạng thái pending, không tăng attempt_count vô hạn
    row = await durable_scheduler.get(handle.children["c0"].scheduled_task_id)
    assert row.attempt_count <= 1
```

- [ ] **Step 2: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/coordination/test_durable_supervisor_workflow.py -q`
Expected: FAIL — `durable_supervisor` module chưa tồn tại.

- [ ] **Step 3: Migration cột child/dependency/join (TS)**

Confirm number: `ls services/cosa/migrations/`. Create `NNN_scheduled_task_child_edges.up.sql`:

```sql
ALTER TABLE control_plane.scheduled_tasks
  ADD COLUMN parent_task_id TEXT,
  ADD COLUMN child_id       TEXT,
  ADD COLUMN depends_on     JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN join_policy    TEXT,
  ADD COLUMN join_quorum    INTEGER;

CREATE INDEX idx_scheduled_tasks_parent ON control_plane.scheduled_tasks (parent_task_id)
  WHERE parent_task_id IS NOT NULL;
CREATE UNIQUE INDEX uq_scheduled_tasks_parent_child
  ON control_plane.scheduled_tasks (parent_task_id, child_id)
  WHERE parent_task_id IS NOT NULL;
```

Update `services/cosa/storage/control-plane-schema.ts` `scheduledTasks` table: thêm `parentTaskId`, `childId`, `dependsOn` (jsonb), `joinPolicy`, `joinQuorum`. Thêm comment khối: `// Bảng execution scheduler — CHẠY TẠI LOCAL WORKSPACE RUNTIME NODE (ADR-LOCAL-FIRST-001), không phải platform VPS.`

- [ ] **Step 4: `scheduleChildTask` + `resolveJoin` (TS)**

Trong `control-plane-scheduler.service.ts`, thêm — tái dùng `scheduleTask` core, chỉ set thêm cột:

```ts
export async function scheduleChildTask(params: ScheduleParams & {
  parentTaskId: string; childId: string; dependsOn: string[];
  joinPolicy: "all" | "any" | "quorum"; joinQuorum?: number;
}): Promise<ScheduledTaskRow> {
  // child có dependsOn chưa hoàn thành → tạo với status 'blocked' thay vì 'pending'
  const deps = params.dependsOn ?? [];
  const blocked = deps.length > 0 && !(await allChildrenComplete(params.parentTaskId, deps));
  return scheduleTaskRow({ ...params, status: blocked ? "blocked" : "pending" });
}

export async function resolveJoin(parentTaskId: string): Promise<{
  satisfied: boolean; completed: string[]; pending: string[];
}> {
  const rows = await db.select().from(scheduledTasks)
    .where(eq(scheduledTasks.parentTaskId, parentTaskId));
  const completed = rows.filter(r => r.status === "completed").map(r => r.childId!);
  const pending = rows.filter(r => r.status !== "completed").map(r => r.childId!);
  const policy = rows[0]?.joinPolicy;
  const quorum = rows[0]?.joinQuorum ?? rows.length;
  const satisfied = policy === "any" ? completed.length >= 1
    : policy === "quorum" ? completed.length >= quorum
    : pending.length === 0;
  // khi một child completed: unblock các child depends_on nó đã thoả
  await unblockSatisfiedChildren(parentTaskId);
  return { satisfied, completed, pending };
}
```

- [ ] **Step 5: `durable_supervisor.py` (Python adapter)**

`packages/agent_core/coordination/durable_supervisor.py` — gọi scheduler qua client abstraction đã có (cùng client `apps/cosa` dùng cho run dispatch; `agent_core` giữ interface, `apps/cosa` inject impl). Core:

```python
class DurableSupervisor:
    def __init__(self, *, scheduler: "SchedulerClient") -> None:
        self._sched = scheduler

    async def spawn(self, children, *, join, quorum=None) -> SupervisionHandle:
        handle_id = f"sup_{uuid4().hex[:12]}"
        for c in children:
            await self._sched.schedule_child_task(
                parent_task_id=handle_id, child_id=c.child_id,
                depends_on=list(c.depends_on), join_policy=join, join_quorum=quorum,
                payload={"parent_run_id": c.parent_run_id, "agent_spec": c.agent_spec.model_dump(),
                         "mode": c.mode, "budget": c.budget.model_dump()},
                idempotency_key=f"{handle_id}:{c.child_id}",   # scheduler dedup
            )
        return await self.resume(handle_id)

    async def resume(self, handle_id: str) -> SupervisionHandle:
        rows = await self._sched.list_children(handle_id)
        children = {r.child_id: ChildState(status=r.status, scheduled_task_id=r.id) for r in rows}
        first = rows[0] if rows else None
        return SupervisionHandle(handle_id=handle_id, children=children,
                                 join=first.join_policy if first else "all",
                                 quorum=first.join_quorum if first else None)

    async def record_child_result(self, handle_id, child_id, result, idempotency_key) -> None:
        # completeTask phía scheduler đã fenced + idempotent theo claim_token;
        # thêm guard app-level theo (child_id, idempotency_key) trước khi apply side effect
        await self._sched.complete_child(handle_id, child_id, result, idempotency_key)
        await self._sched.resolve_join(handle_id)

    def is_join_satisfied(self, handle: SupervisionHandle) -> bool:
        done = sum(1 for c in handle.children.values() if c.status == "completed")
        if handle.join == "any":
            return done >= 1
        if handle.join == "quorum":
            return done >= (handle.quorum or len(handle.children))
        return all(c.status == "completed" for c in handle.children.values())
```

- [ ] **Step 6: Cấm side-effecting fan-out qua `asyncio.gather`**

`packages/agent_core/coordination/parallel.py` — đầu `execute_parallel`:

```python
for t in tasks:
    if _spec_has_write_capability(t.spec):
        raise RuntimeError(
            f"ParallelCoordinator is for local pure computation only; task '{t.task_id}' "
            f"has a write-capable spec — use DurableSupervisor (spec Task 7)")
```

`_spec_has_write_capability(spec)` = có tool contract ref nào thuộc allowlist write caps (`*.write`, `*.send`, `*.delete`, `*.deploy`). `packages/agent_core/coordination/supervisor.py` — `SupervisorCoordinator.execute_mission` production: nếu bất kỳ specialist spec write-capable → uỷ quyền `DurableSupervisor`; `_parallel` chỉ còn dùng cho read-only synthesis (quality gate + artifact synthesis không side-effect).

- [ ] **Step 7: Chạy — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/coordination/ -q`
Run: `cd services/cosa && npx vitest run tests/control-plane-scheduler-crash-recovery.test.ts --reporter=dot`
Expected: PASS. Bổ sung test TS: `child dependency edges survive reclaimStuckTasks`, `resolveJoin unblocks dependents on completion`.

- [ ] **Step 8: Commit**

```bash
git add packages/agent_core/coordination/ services/cosa/storage/control-plane-schema.ts \
        services/cosa/services/control-plane-scheduler.service.ts services/cosa/migrations/ \
        tests/agent_core/coordination/ services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts
git commit -m "feat(coordination): durable supervisor over local scheduler; forbid side-effecting gather fan-out"
```

---

### Task 3: Gate event triggers by eval/promotion evidence  *(spec Task 8)*

**Files:**
- Modify: `apps/cosa/events/trigger_policy.py` (từ P0 Task 4)
- Create: `apps/cosa/events/trigger_promotion.py`
- Modify: `packages/agent_core/evals/models.py`
- Modify: `apps/cosa/agents/seed.py`
- Test: `tests/apps/cosa/test_event_trigger_promotion.py`
- Test: `tests/agent_core/evals/test_event_trigger_evals.py`

**Interfaces:**
- Consumes: `EventTriggerRule` (P0 Task 4); `PromotionEvidence` + `build_promotion_evidence()` (`packages/agent_core/evals/promotion.py`); `PromotionGate` + `PromotionGateResult` (`packages/agent_core/evals/promotion_gate.py`); `CanonicalEvalRunner` (`packages/agent_core/evals/runner.py`); `EvalCategory` (`packages/agent_core/evals/models.py`).
- Produces:
  - `EventTriggerRule` thêm field `eval_evidence_ref: str | None = None`.
  - `@dataclass(frozen=True) class EventTriggerEvalSuite` — `event_schema_version: int`, `input_fixtures: tuple[EventFixture, ...]`, `policy_version: str`, `expected_action_boundary: Literal["artifact_only","proposal","write"]`, `failure_injection: tuple[InjectionScenario, ...]`.
  - `def can_enable_trigger(rule: EventTriggerRule, evidence: PromotionEvidence | None, current_fingerprints: dict[str, str], *, policy_version: str) -> GateResult` — `GateResult{ allowed: bool, reason: str | None, requires_human_approval: bool }`.
  - Rule mở rộng: `trigger_policy.resolve()` trả `TriggerDecision("policy_denied", reason="stale_eval_evidence")` khi `rule.mode != "artifact_only"` và `can_enable_trigger(...)` không `allowed`.
- Later tasks: none (P1 kết thúc ở đây).

- [ ] **Step 1: Test đỏ — stale/absent evidence gate**

Create `tests/apps/cosa/test_event_trigger_promotion.py`:

```python
import pytest
from apps.cosa.events.trigger_promotion import can_enable_trigger
from apps.cosa.events.trigger_policy import EventTriggerRule
# helpers: make_rule(mode, eval_evidence_ref=None), make_evidence(passed, fps), FP_NOW


def test_enable_denied_without_eval():
    r = make_rule(mode="artifact_only", eval_evidence_ref=None)
    g = can_enable_trigger(r, None, FP_NOW, policy_version="p1")
    assert not g.allowed and g.reason == "no_eval_evidence"


def test_enable_denied_on_failed_checks():
    r = make_rule("artifact_only", "promoevid_x")
    ev = make_evidence(passed=False, fps=FP_NOW)
    assert not can_enable_trigger(r, ev, FP_NOW, policy_version="p1").allowed


def test_enable_denied_on_changed_skillspec_or_policy_hash():
    r = make_rule("artifact_only", "promoevid_x")
    ev = make_evidence(passed=True, fps={"skill_a": "hash_OLD"})
    g = can_enable_trigger(r, ev, {"skill_a": "hash_NEW"}, policy_version="p1")
    assert not g.allowed and g.reason == "stale_evidence"


def test_enable_denied_on_changed_event_schema_version():
    r = make_rule("artifact_only", "promoevid_x", event_schema_version=1)
    ev = make_evidence(passed=True, fps=FP_NOW, event_schema_version=2)
    assert not can_enable_trigger(r, ev, FP_NOW, policy_version="p1").allowed


def test_artifact_only_evidence_enables_artifact_only_not_write():
    ev = make_evidence(passed=True, fps=FP_NOW, action_boundary="artifact_only")
    assert can_enable_trigger(make_rule("artifact_only", "e"), ev, FP_NOW, policy_version="p1").allowed
    g_write = can_enable_trigger(make_rule("write", "e"), ev, FP_NOW, policy_version="p1")
    assert not g_write.allowed and g_write.reason == "action_boundary_exceeded"


def test_write_rule_requires_human_approval_even_with_matching_evidence():
    ev = make_evidence(passed=True, fps=FP_NOW, action_boundary="write")
    g = can_enable_trigger(make_rule("write", "e"), ev, FP_NOW, policy_version="p1")
    assert g.allowed and g.requires_human_approval is True


def test_stale_evidence_disables_previously_enabled_rule(resolve_ctx):
    rule = make_rule("proposal", "promoevid_x", enabled=True)
    resolve_ctx.set_fingerprints({"skill_a": "hash_NEW"})   # drift
    decision = resolve_ctx.resolve(rule)
    assert decision.outcome == "policy_denied" and decision.reason == "stale_eval_evidence"
```

Create `tests/agent_core/evals/test_event_trigger_evals.py`:

```python
from agent_core.evals.models import EventTriggerEvalSuite, EvalCategory

def test_suite_records_schema_version_fixtures_policy_and_injection():
    s = EventTriggerEvalSuite(event_schema_version=1, input_fixtures=(fx(),),
                              policy_version="p1", expected_action_boundary="artifact_only",
                              failure_injection=(inj("duplicate_delivery"), inj("policy_denied")))
    assert s.event_schema_version == 1
    assert {i.name for i in s.failure_injection} == {"duplicate_delivery", "policy_denied"}

def test_suite_maps_to_security_governance_category():
    assert EventTriggerEvalSuite.eval_category() == EvalCategory.SECURITY_GOVERNANCE
```

- [ ] **Step 2: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_event_trigger_promotion.py tests/agent_core/evals/test_event_trigger_evals.py -q`
Expected: FAIL — `trigger_promotion` module + `EventTriggerEvalSuite` chưa tồn tại; `EventTriggerRule` chưa có `eval_evidence_ref`.

- [ ] **Step 3: `EventTriggerEvalSuite` trong evals/models.py**

Add to `packages/agent_core/evals/models.py`:

```python
class InjectionScenario(BaseModel):
    name: str
    description: str = ""

class EventFixture(BaseModel):
    fixture_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)

class EventTriggerEvalSuite(BaseModel):
    event_schema_version: int
    input_fixtures: tuple[EventFixture, ...]
    policy_version: str
    expected_action_boundary: str  # "artifact_only" | "proposal" | "write"
    failure_injection: tuple[InjectionScenario, ...]

    @staticmethod
    def eval_category() -> EvalCategory:
        return EvalCategory.SECURITY_GOVERNANCE
```

Add `"EventTriggerEvalSuite"`, `"EventFixture"`, `"InjectionScenario"` to `__all__`.

- [ ] **Step 4: `trigger_promotion.py` + wire vào `trigger_policy`**

`apps/cosa/events/trigger_promotion.py`:

```python
from __future__ import annotations
from dataclasses import dataclass
from agent_core.evals.promotion import PromotionEvidence
from agent_core.evals.promotion_gate import PromotionGate

_BOUNDARY_RANK = {"artifact_only": 0, "proposal": 1, "write": 2}

@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: str | None = None
    requires_human_approval: bool = False

def can_enable_trigger(rule, evidence: PromotionEvidence | None,
                       current_fingerprints: dict[str, str], *, policy_version: str) -> GateResult:
    if evidence is None or not rule.eval_evidence_ref:
        return GateResult(False, "no_eval_evidence")
    gate = PromotionGate(policy_version=policy_version).check(evidence, current_fingerprints)
    if not gate.approved:
        reason = "stale_evidence" if any("stale" in i.lower() for i in gate.blocking_issues) else "checks_failed"
        return GateResult(False, reason)
    ev_boundary = evidence.check_details.get("action_boundary", "artifact_only")
    ev_schema = evidence.check_details.get("event_schema_version")
    rule_schema = getattr(rule, "event_schema_version", ev_schema)
    if ev_schema is not None and rule_schema != ev_schema:
        return GateResult(False, "event_schema_changed")
    if _BOUNDARY_RANK[rule.mode] > _BOUNDARY_RANK[ev_boundary]:
        return GateResult(False, "action_boundary_exceeded")
    return GateResult(True, None, requires_human_approval=(rule.mode == "write"))
```

`apps/cosa/events/trigger_policy.py`:
- `EventTriggerRule`: thêm `eval_evidence_ref: str | None = None`, `event_schema_version: int = 1`.
- `resolve()`: sau khi rule tìm được và `enabled`, trước khi trả `accepted` — nếu `rule.mode != "artifact_only"`:
  ```python
  ev = await store.load_evidence(rule.eval_evidence_ref) if rule.eval_evidence_ref else None
  gate = can_enable_trigger(rule, ev, await fingerprints.current(rule), policy_version=policy.version)
  if not gate.allowed:
      return TriggerDecision("policy_denied", reason="stale_eval_evidence")
  ```
- Với `rule.mode == "artifact_only"`: vẫn cần evidence `allowed` để `enable`, nhưng runtime `resolve` chỉ cảnh báo (không chặn) — vì artifact-only không có side effect. Ghi metric `trigger_artifact_only_no_evidence_total`.

`apps/cosa/agents/seed.py`: rule mẫu write-capable (nếu seed rule nào) đặt `enabled=False`, `eval_evidence_ref=None` + comment "cần eval + human approval trước khi bật".

- [ ] **Step 5: Chạy — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_event_trigger_promotion.py tests/agent_core/evals/ tests/apps/cosa/test_local_event_intake.py -q`
Expected: PASS. (chạy lại intake test P0 để đảm bảo gate mới không phá luồng `artifact_only` đang xanh.)

- [ ] **Step 6: Commit**

```bash
git add apps/cosa/events/ packages/agent_core/evals/models.py apps/cosa/agents/seed.py \
        tests/apps/cosa/test_event_trigger_promotion.py tests/agent_core/evals/test_event_trigger_evals.py
git commit -m "feat(events): gate trigger enable/resolve on immutable eval/promotion evidence"
```

---

## Self-Review

**Spec coverage (P1 = spec Task 6, 7, 8):**

| Spec requirement | Plan task |
| --- | --- |
| Task 6 — production construction đòi `PostgresMemoryStore` + explicit retention; missing dep fails activation | Task 1 Steps 1–5 |
| Task 6 — fake scanner rejected in production; injected `object_store`/`knowledge_service` bắt buộc | Task 1 Steps 6–9 |
| Task 6 — semantic retrieval chỉ sau benchmark threshold; lexical fallback + citations luôn có; snapshot pin source/chunk/embedding/index recipe | Task 1 Steps 10–13 (`retrieval.py`, `search_chunks_semantic`, `KnowledgeSnapshot.retrieval_eval_run_id` đã có) |
| Task 6 — `knowledge.source.published.v1` chỉ sau human review/publish + persistent status + snapshot identity; payload reference-only | Task 1 Steps 10–13 (`publish.py`) |
| Task 7 — supervisor tạo persistent child task IDs + spec pins + dependency edges + budget/autonomy ceiling + join policy; child completion idempotent; resume/retry không nhân đôi side effect | Task 2 Steps 1–5 |
| Task 7 — `asyncio.gather` coordinator chỉ local pure computation; cấm production side-effecting delegation | Task 2 Step 6 |
| Task 7 — dùng scheduler lease/DLQ hiện có, không engine thứ hai; Capability Gateway giữ thẩm quyền mỗi child action | Task 2 Steps 4–5 (tái dùng `control-plane-scheduler.service.ts`) |
| Task 7 — blackboard/market-based cố ý vắng mặt | Không có file/interface nào cho 2 pattern đó; test chỉ hierarchical |
| Task 8 — trigger `enabled` chỉ khi exact AgentSpec/SkillSpec/policy fingerprint đã hoàn thành eval suite và evidence không stale | Task 3 Steps 1–4 (`can_enable_trigger` + `PromotionGate`) |
| Task 8 — eval suite ghi event schema version, fixtures, policy version, action boundary, failure injection | Task 3 Step 3 (`EventTriggerEvalSuite`) |
| Task 8 — artifact-only evidence enable artifact-only rule, không write rule; write rule đòi human approval | Task 3 Step 4 (`_BOUNDARY_RANK`, `requires_human_approval`) |
| Task 8 — immutable evidence reference trên rule; drift ⇒ disable/reject | Task 3 Step 4 (`eval_evidence_ref`, `resolve()` trả `stale_eval_evidence`) |
| DoD #5 (drift ⇒ trigger disable/reject) | Task 3 `test_stale_evidence_disables_previously_enabled_rule` |
| DoD #6 (RAG publication chỉ sau durable storage + real scan + review + snapshot) | Task 1 `publish.py` + `test_publish_event_only_after_durable_review` |
| DoD #7 (supervisor crash/restart giữ child status + approval + idempotency) | Task 2 crash-recovery tests |

**Placeholder scan:** Không "TBD"/"handle edge cases"/"similar to Task N". Mỗi code step có code block thật; test step có assertion thật. Điểm phụ thuộc ngoài được nêu rõ (Task 2 blocked; `publish.py` phía TS-hay-Python quyết theo `grep` nơi review persist).

**Type consistency:** `MemoryService(store, *, retention)` / `RetentionPolicy` / `KnowledgeRetrievalConfig` / `RetrievalResult` / `Citation` định nghĩa Task 1, không dùng lại ở task khác. `ChildTaskSpec` / `SupervisionHandle` / `DurableSupervisor` / `scheduleChildTask` / `resolveJoin` định nghĩa Task 2. `EventTriggerRule.eval_evidence_ref` / `EventTriggerRule.event_schema_version` / `EventTriggerEvalSuite` / `GateResult` / `can_enable_trigger` định nghĩa Task 3; `EventTriggerRule` gốc từ P0 Task 4 — Task 3 chỉ *thêm* field, không đổi field cũ. `PromotionGate(policy_version).check(evidence, current_fingerprints) -> PromotionGateResult{approved, blocking_issues}` dùng đúng chữ ký hiện có (`packages/agent_core/evals/promotion_gate.py:30`).

---

## Verification (end-to-end, sau Task 3)

**Regression:**
```
PYTHONPATH=. .venv/bin/pytest tests/agent_core tests/apps/cosa tests/contract tests/architecture -q
cd services/cosa && npx vitest run --reporter=dot
cd services/company && npx vitest run --reporter=dot
python packages/agent_core/scripts/migrate.py
```

**Manual e2e:**
1. Set `ENVIRONMENT=production`, unset `AGENT_CORE_DATABASE_URL` → `MemoryService.for_production()` raises; `build_cosa_agent_plane()` raises. Set URL → thành công.
2. Chạy knowledge ingestion task với `scanner=None` ở production → `RuntimeError("dependencies must be injected")`. Inject fake scanner → `RuntimeError("production scanner")`. Inject real → pipeline chạy tới `REVIEW_PENDING`.
3. Approve + persist review → đúng một `knowledge.source.published.v1` outbox row, payload chỉ có `sourceId/snapshotId/embeddingModel/indexRecipeVersion/reviewedBy/reviewedAt`. Approve nhưng `persistent_status="pending"` → không có event.
4. (Sau `SPEC-EXEC-PLANE-SPLIT`) `DurableSupervisor.spawn(3 children, join="all")`, kill process sau 2 child, `resume(handle_id)` từ process mới → child c2 vẫn `pending`, `is_join_satisfied` False. `record_child_result` lặp cùng `idempotency_key` → side-effect probe = 1.
5. Tạo `EventTriggerRule(mode="write")` không `eval_evidence_ref` → `resolve()` trả `policy_denied / stale_eval_evidence`. Gắn evidence pass + fingerprint khớp → `can_enable_trigger` `allowed=True, requires_human_approval=True`. Đổi một dependency fingerprint → `resolve()` lại trả `stale_eval_evidence`.
6. `pytest tests/agent_core/coordination -q` xanh và `grep -rn "blackboard\|market_based\|market-based" packages/agent_core` → 0 (2 pattern cố ý vắng).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-p1.md`. Thực thi **sau P0**; **Task 2 chờ `SPEC-EXEC-PLANE-SPLIT`**. Hai lựa chọn:

1. **Subagent-Driven (recommended)** — subagent riêng mỗi task, review giữa các task.
2. **Inline Execution** — executing-plans, checkpoint theo batch.

Which approach?

Plan này không cho phép: deploy VPS, cài broker, cấu hình provider ngoài, xoá dữ liệu hiện có. P2 (spec Task 9 — broker capacity ADR) có plan riêng.
