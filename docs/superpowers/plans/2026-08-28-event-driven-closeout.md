# Event-Driven Agent Operating Model — Closeout Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans hoặc superpowers:subagent-driven-development. Steps dùng `- [ ]`.

**Goal:** Đóng nốt 6 mảng còn hở sau P0 (Antigravity) + P2 + SPEC-EXEC-PLANE-SPLIT + P1 Tasks 1/3 + P1 Task 2 (Python layer) đã landed: (1) P1 Task 2 phần TS `services/cosa`; (2) wiring vào composition root; (3) semantic retrieval thật; (4) 2 việc nhỏ P2; (5) reconcile docs; (6) verify P0 + fix DB infra test.

**Architecture:** Không đổi kiến trúc. Chủ yếu là *nối dây* các guard/adapter đã có vào composition root, hoàn thiện durable child-task ở tầng scheduler TS, và dọn doc. Semantic retrieval là mảng duy nhất có decision point (chọn embedding model).

**Tech Stack:** TypeScript strict + Encore + Drizzle + PostgreSQL 16 + Vitest (`services/cosa`). Python 3.11 + FastAPI + SQLAlchemy + pytest (`apps/cosa`, `packages/agent_core`). Markdown (docs).

**Baseline (đã commit trên `remediation/dev-readiness-remaining`):**
- P0 Tasks 1–5 (Antigravity) tới `d44c52a9`.
- P2 `0f2c185c` `cae39239`; SPEC-EXEC-PLANE-SPLIT `6d8105dc` `ed05250c`.
- P1 Task 1 `4b4ea86e` `6ca3aafa` `935c3dc6`; P1 Task 3 `94814de6`; P1 Task 2 Python layer `78e2b142`.
- **Closeout Task 1 `dde64a9f` (docs) · Task 2 `d0d0e196` (memory/knowledge wiring on plane) — DONE.**

**Phát hiện khi khảo sát (2026-08-28) — điều chỉnh 4 task còn lại:**
- `services/company/events/` **không có metric emission nào** — P0 Task 5 "metrics" (`event_delivery_latency_seconds`, `event_dlq_total`, ...) **chưa được implement**. ⇒ Task 6a không phải "thêm 2 gauge" mà là "xây tầng metrics event từ đầu" (thực chất là gap P0, không phải polish P2).
- **Không có `PostgresTriggerRuleStore` / bảng `event_trigger_rules` / migration nào.** Chỉ có `TriggerRuleStoreProtocol` + `InMemoryTriggerRuleStore` (test fixture). ⇒ Task 4 = xây rule store + bảng + migration + admin endpoint + tích hợp `can_enable_trigger`, lớn hơn ước tính.
- ⇒ Mỗi task 3/4/5/6 giờ đủ lớn để xứng một spec/plan riêng, hoặc bị chặn bởi decision (sink route, embedding provider) hoặc infra (Postgres role `javis_app`).

**Specs liên quan:** `2026-08-28-event-driven-agent-operating-model-design.md`, `2026-08-28-exec-plane-split-design.md`, plans `...-p0.md` / `-p1.md` / `-p2.md`.

## Global Constraints

- **TDD**: test đỏ → xác nhận đỏ → implement → xác nhận xanh → commit.
- **An toàn working tree** (CLAUDE.md #10): `git status` trước; **partial commit** `git commit <path...>` để không gom việc song song đang staged; không `--force`/`--no-verify`.
- **Tree chung với Antigravity** — Task 5 (P1 Task 2 TS) đụng `services/cosa/services/control-plane-scheduler.service.ts`. Làm trong **git worktree riêng** (`superpowers:using-git-worktrees`) hoặc xác nhận Antigravity đã xong P0 hẳn trước khi bắt đầu Task 5.
- **Migration number**: `ls services/cosa/migrations/` (cao nhất `9_...` ⇒ `10_...`) và `ls packages/agent_core/migrations/` ngay trước khi tạo.
- **`packages/agent_core` KHÔNG import `apps/` hay `services/`.**
- **Không production in-memory fallback.** Guard đã có ở P1 Task 1 — task này chỉ *nối* bản production.
- Comment tiếng Việt cho why; identifier/error tiếng Anh.
- **Không** deploy VPS, cài broker, xoá dữ liệu, cấu hình provider ngoài.

---

## Task 1: Reconcile docs (làm trước — rẻ, làm rõ trạng thái)

**Files:**
- Modify: `docs/superpowers/specs/2026-08-28-exec-plane-split-design.md`
- Modify: `docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-p1.md`
- Modify: `docs/superpowers/plans/2026-08-28-exec-plane-split.md`

- [ ] **Step 1: exec-plane-split design — sửa phân loại `/schedules`**

Trong `2026-08-28-exec-plane-split-design.md` bảng Context + §Decision.2: đổi `routes.py:828,870,908` (`/schedules*`) và `worker/handlers.py:349,412` từ **execution** → **platform**. Xoá đoạn "Judgment call: `/schedules` endpoints" hoặc cập nhật thành: "schedule store sống ở `services/cosa` control plane ⇒ CRUD/snapshot fetch là platform; chỉ `run_scheduler`/`run_lease_client` (durable run dispatch/lease) là execution". Cập nhật DoD #2 cho khớp.

- [ ] **Step 2: exec-plane-split plan — sửa Task 2 bảng repoint**

Trong `2026-08-28-exec-plane-split.md` Task 2 Step 1: `/schedules*` → `resolve_platform_control_plane_url()` (khớp code đã landed `ed05250c`).

- [ ] **Step 3: P1 plan — gỡ trạng thái blocked của Task 2**

Trong `2026-08-28-event-driven-agent-operating-model-p1.md`:
- Header Task 2: bỏ "BỊ CHẶN tới khi `SPEC-EXEC-PLANE-SPLIT` merged" → "SPEC-EXEC-PLANE-SPLIT đã merged (`6d8105dc` `ed05250c`); Python layer đã landed (`78e2b142`); còn lại phần TS `services/cosa` — xem closeout plan Task 5".
- Bảng "Dependencies vào các plan khác": đánh dấu dòng `SPEC-EXEC-PLANE-SPLIT` là ✅ done.
- Thêm 1 dòng ghi chú: commit `e6351881` (P1 plan doc) vô tình gom kèm deletion `services/company/operations/services/okr-events.service.ts` do Antigravity đã staged — hợp lệ, không cần sửa.

- [ ] **Step 4: Commit**

```bash
git commit docs/superpowers/specs/2026-08-28-exec-plane-split-design.md \
  docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-p1.md \
  docs/superpowers/plans/2026-08-28-exec-plane-split.md \
  -m "docs: reconcile exec-plane-split classification + unblock P1 Task 2 status"
```

---

## Task 2: Wiring composition root — memory & knowledge production stores

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/api/routes.py` (review-status-sync path ~1155–1180)
- Modify: `apps/cosa/api/app.py` (nếu cần seed service vào state)
- Test: `tests/apps/cosa/composition/test_agent_plane_knowledge_memory_wiring.py` (mới)

**Interfaces:**
- Consumes: `MemoryService.for_production()` (`4b4ea86e`), `get_knowledge_store()` (`packages/agent_core/knowledge/store.py:76`, đã fail-fast), `assert_production_scanner_ready` (`6ca3aafa`).
- Produces:
  - `CosaAgentPlane.memory_service: MemoryService`
  - `CosaAgentPlane.knowledge_ingestion_service: KnowledgeIngestionService`
  - `build_cosa_agent_plane(..., memory_service=None, knowledge_ingestion_service=None)` — inject cho test; production dựng từ `AGENT_CORE_DATABASE_URL` (fail-fast nếu thiếu, theo pattern `agent_plane.py:177-251`).

- [ ] **Step 1: Test đỏ**

Create `tests/apps/cosa/composition/test_agent_plane_knowledge_memory_wiring.py`:

```python
import pytest
from apps.cosa.composition.agent_plane import build_cosa_agent_plane

pytestmark = pytest.mark.asyncio


def test_production_build_requires_db_for_memory_and_knowledge(monkeypatch):
    monkeypatch.delenv("AGENT_CORE_DATABASE_URL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")
    with pytest.raises(RuntimeError, match="AGENT_CORE_DATABASE_URL"):
        build_cosa_agent_plane()


def test_injected_services_are_exposed_on_plane():
    from agent_core.memory.service import MemoryService
    from agent_core.knowledge.service import KnowledgeIngestionService
    from agent_core.knowledge.store import InMemoryKnowledgeStore

    mem = MemoryService.in_memory()
    kis = KnowledgeIngestionService(InMemoryKnowledgeStore())
    plane = build_cosa_agent_plane(
        repository=_in_memory_run_repo(), conversation_repository=_in_memory_conv_repo(),
        spec_registry=_in_memory_registry(), governance_store=_in_memory_gov(),
        stream_event_repository=_in_memory_stream(),
        memory_service=mem, knowledge_ingestion_service=kis,
        runtime="manual_tool_loop",
    )
    assert plane.memory_service is mem
    assert plane.knowledge_ingestion_service is kis
```

(dùng helper in-memory sẵn có trong `tests/apps/cosa/` — xem `test_cosa_plane.py`.)

- [ ] **Step 2: Chạy — đỏ**

`PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/composition/test_agent_plane_knowledge_memory_wiring.py -q` → FAIL (`CosaAgentPlane` chưa có 2 attr).

- [ ] **Step 3: Implement**

- `agent_plane.py`:
  - Thêm param `memory_service`, `knowledge_ingestion_service` vào `build_cosa_agent_plane`.
  - Sau block dựng repo (`~:251`): nếu param None →
    ```python
    if memory_service is None:
        memory_service = MemoryService.for_production(resolved_url) if resolved_url else _fail("memory")
    if knowledge_ingestion_service is None:
        from agent_core.knowledge.service import KnowledgeIngestionService
        from agent_core.knowledge.store import get_knowledge_store
        knowledge_ingestion_service = KnowledgeIngestionService(get_knowledge_store(resolved_url)) if resolved_url else _fail("knowledge")
    ```
    (`_fail` = raise RuntimeError như các guard hiện có; `resolved_url` đã có ở `agent_plane.py`.)
  - `CosaAgentPlane.__init__` + `__init__` call site (`:110`, `:455` area): thêm 2 field.
  - `close_cosa_agent_plane`: đóng nếu store có `aclose`.
- `routes.py` review-status-sync (~1163): thay
  ```python
  knowledge_service = getattr(request.app.state, "knowledge_ingestion_service", None)
  if knowledge_service is None:
      from agent_core.knowledge.service import KnowledgeIngestionService
      knowledge_service = KnowledgeIngestionService()
  ```
  bằng
  ```python
  plane = request.app.state.plane
  knowledge_service = getattr(plane, "knowledge_ingestion_service", None) \
      or getattr(request.app.state, "knowledge_ingestion_service", None)
  if knowledge_service is None:
      _env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
      if _env == "production":
          raise HTTPException(status_code=503, detail="knowledge service not wired")
      from agent_core.knowledge.service import KnowledgeIngestionService
      knowledge_service = KnowledgeIngestionService()
  ```

- [ ] **Step 4: Chạy — xanh**

`PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/composition/ tests/apps/cosa/test_cosa_plane.py tests/apps/cosa/knowledge_ingestion/ -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git commit apps/cosa/composition/agent_plane.py apps/cosa/api/routes.py apps/cosa/api/app.py \
  tests/apps/cosa/composition/test_agent_plane_knowledge_memory_wiring.py \
  -m "feat(composition): wire production MemoryService + KnowledgeIngestionService onto plane"
```

---

## Task 3: Wiring — knowledge publish sink + trigger evidence store

**Decision point (Step 0):** `knowledge.source.published.v1` phải vào `integration.event_outbox` (schema ở `services/company` Postgres). `apps/cosa` dùng `AGENT_CORE_DATABASE_URL` khác `COMPANY_DATABASE_URL` ⇒ không ghi trực tiếp. **Chọn:** thêm endpoint nội bộ `services/company` `POST /events/internal/knowledge-published` (`expose:false`) nhận envelope đã validate → `appendOutboxEvent` (dùng lại repo P0 Task 3). `apps/cosa` `publish_knowledge_source(emit=...)` POST tới đó qua `resolve_platform_control_plane_url()`... **KHÔNG** — company không phải platform. Dùng biến mới `COMPANY_SERVICE_URL` (đã có trong `.env.example:39`). Sink mặc định = HTTP client tới `COMPANY_SERVICE_URL`.

**Files:**
- Create: `services/company/events/handlers/knowledge-published.handler.ts` + endpoint trong `services/company/events/` barrel
- Create: `services/company/events/tests/knowledge-published.test.ts`
- Create: `apps/cosa/knowledge_ingestion/event_sink.py` (`CompanyOutboxEventSink`)
- Modify: `apps/cosa/knowledge_ingestion/publish.py` (default sink = `CompanyOutboxEventSink`)
- Modify: `apps/cosa/api/routes.py` (gọi `publish_knowledge_source` khi review → PUBLISHED, sau khi `update_document_ingest_status` thành công)
- Modify: `apps/cosa/composition/agent_plane.py` (dựng `TriggerPolicyService` evidence deps — xem dưới)
- Create: `apps/cosa/events/evidence_store.py` (`PostgresPromotionEvidenceStore`, `SpecFingerprintProvider`)
- Test: `tests/apps/cosa/knowledge_ingestion/test_publish_wired.py`, `tests/apps/cosa/test_trigger_evidence_wiring.py`

**Interfaces:**
- Consumes: `appendOutboxEvent` (P0 Task 3, `services/company/shared/events/outbox.repository.ts`), `validateEnvelope` (P0 Task 2), `publish_knowledge_source` (`935c3dc6`), `can_enable_trigger` / `TriggerPolicyService` (`94814de6`), `PromotionEvidence` repo (`packages/agent_core/evals/promotion_repository.py`).
- Produces:
  - `POST /events/internal/knowledge-published` — body `BusinessEventEnvelope`, `expose:false`, service-token auth. 202 `{stored:true}` | 400 invalidArgument | 409 duplicate (eventId đã có → idempotent, vẫn 202).
  - `class CompanyOutboxEventSink` — `async __call__(envelope: dict) -> None` POST tới `{COMPANY_SERVICE_URL}/events/internal/knowledge-published`.
  - `class PostgresPromotionEvidenceStore` — `async load(evidence_ref: str) -> PromotionEvidence | None`.
  - `class SpecFingerprintProvider` — `async current(rule) -> dict[str, str]` (agent_spec + skill + policy definition_hash hiện tại từ registry).

- [ ] **Step 1: Test đỏ — company endpoint**

`services/company/events/tests/knowledge-published.test.ts`:
```ts
it("appends a knowledge.source.published.v1 outbox row from a valid envelope", async () => { ... expect readOutbox(...).toHaveLength(1) });
it("is idempotent on duplicate eventId", async () => { ... post twice ... expect(rows).toHaveLength(1) });
it("rejects an invalid envelope with invalidArgument", async () => { ... });
it("rejects a non-service caller", async () => { ... });
```

- [ ] **Step 2: Test đỏ — python sink + trigger evidence**

`tests/apps/cosa/knowledge_ingestion/test_publish_wired.py`:
```python
async def test_publish_posts_envelope_to_company_when_review_published(httpx_mock):
    httpx_mock.add_response(url__contains="/events/internal/knowledge-published", status_code=202, json={"stored": True})
    # gọi review-decision endpoint với decision=PUBLISHED → 1 POST tới company
```
`tests/apps/cosa/test_trigger_evidence_wiring.py`:
```python
async def test_resolve_denies_proposal_rule_when_evidence_stale(deps_with_evidence):
    # evidence_store trả evidence có fingerprint cũ → resolve() = policy_denied/stale_eval_evidence
async def test_resolve_accepts_proposal_rule_with_fresh_matching_evidence(deps_with_evidence):
    # → accepted
```

- [ ] **Step 3: Chạy — đỏ** (endpoint + sink chưa tồn tại)

- [ ] **Step 4: Implement company endpoint**

`knowledge-published.handler.ts`: parse → `validateEnvelope(body)` → `db.transaction(tx => appendOutboxEvent(tx, body))` (append-only, `ON CONFLICT DO NOTHING` đã idempotent) → 202. Service-token guard theo pattern các endpoint `expose:false` khác trong `services/company`.

- [ ] **Step 5: Implement python sink + wire publish**

`event_sink.py`:
```python
class CompanyOutboxEventSink:
    def __init__(self, base_url: str | None = None):
        self._url = (base_url or os.environ["COMPANY_SERVICE_URL"]).rstrip("/")
    async def __call__(self, envelope: dict) -> None:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.post(f"{self._url}/events/internal/knowledge-published", json=envelope,
                             headers={"Authorization": f"Bearer {os.environ.get('COSA_WORKER_SERVICE_TOKEN','')}"})
            r.raise_for_status()
```
`publish.py`: `_default_emit` → `CompanyOutboxEventSink()`. `routes.py` review path: sau `update_document_ingest_status(..., "published")` thành công và có `KnowledgeSnapshot`, gọi
```python
await publish_knowledge_source(snapshot=snap, approved=True, persisted=True,
    reviewed_by=identity.platform_user_id, reviewed_at=..., correlation_id=...)
```
(Nếu review path chưa tạo `KnowledgeSnapshot` — tạo tối thiểu từ source refs; hoặc bỏ qua publish nếu chưa có snapshot, log warning. Ghi rõ đây là chỗ RAG P1 gate.)

- [ ] **Step 6: Implement evidence store + wire trigger deps**

`evidence_store.py`: `PostgresPromotionEvidenceStore.load()` đọc từ `promotion_repository`/`promotion_evidence` table. `SpecFingerprintProvider.current(rule)` gọi `SpecRegistryRepository` lấy `definition_hash` hiện tại của `rule.agent_spec.id` + skill/policy deps.
`agent_plane.py`: khi dựng `event_intake_deps` (P0 Task 4 wiring), truyền `TriggerPolicyService(store, caps, run_counter, evidence_store=PostgresPromotionEvidenceStore(...), fingerprint_provider=SpecFingerprintProvider(spec_registry), policy_version=<cfg>)`.

- [ ] **Step 7: Chạy — xanh**

`cd services/company && npx vitest run events/tests/knowledge-published.test.ts --reporter=dot`
`PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/knowledge_ingestion/ tests/apps/cosa/test_trigger_evidence_wiring.py tests/apps/cosa/test_local_event_intake.py -q`

- [ ] **Step 8: Commit** (2 commit: company endpoint; cosa sink+evidence)

---

## Task 4: Enable-trigger-rule admin endpoint + seed updates

**Files:**
- Create: `apps/cosa/api/event_rule_routes.py` (`POST /agent/events/rules`, `POST /agent/events/rules/{id}/enable`)
- Modify: `apps/cosa/api/app.py` (mount)
- Modify: `apps/cosa/agents/seed.py`
- Create: `apps/cosa/events/rule_store.py` (`PostgresTriggerRuleStore` — nếu P0 chưa có store thật; kiểm `grep -rn "class.*TriggerRuleStore" apps/cosa`)
- Migration: `packages/agent_core/migrations/NNN_event_trigger_rules.sql` (nếu chưa có bảng)
- Test: `tests/apps/cosa/test_event_rule_admin.py`

**Interfaces:**
- `POST /agent/events/rules/{rule_id}/enable` `{workspaceId}` → gọi `can_enable_trigger(rule, evidence, fingerprints, policy_version=)`:
  - `allowed=False` → 422 `{reason}`
  - `allowed=True, requires_human_approval=True` và chưa có approval → 202 `{status:"pending_human_approval"}`
  - `allowed=True` (còn lại) → set `enabled=True`, 200
- `seed.py`: rule mẫu (nếu seed) — `enabled=False`, `eval_evidence_ref=None`, comment "cần eval + (write ⇒ human approval) trước khi bật".

- [ ] **Step 1: Test đỏ** — `test_event_rule_admin.py`:
```python
async def test_enable_denied_without_evidence(): ... 422 reason=no_eval_evidence
async def test_enable_write_rule_needs_human_approval(): ... 202 pending_human_approval
async def test_enable_artifact_only_with_valid_evidence_succeeds(): ... 200 enabled
async def test_enable_rejected_cross_workspace(): ... 403
```
- [ ] **Step 2: Chạy — đỏ**
- [ ] **Step 3: Implement route + rule store (nếu cần) + migration + seed**
- [ ] **Step 4: Chạy — xanh** (`pytest tests/apps/cosa/test_event_rule_admin.py tests/apps/cosa/agents/ -q`)
- [ ] **Step 5: Commit**

---

## Task 5: P1 Task 2 — durable child-task scheduler (TypeScript `services/cosa`)

> **Làm trong worktree riêng.** Đụng `control-plane-scheduler.service.ts`.

**Files:**
- Create: `services/cosa/migrations/10_scheduled_task_child_edges.up.sql` (xác nhận số)
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Modify: `services/cosa/services/control-plane-scheduler.service.ts`
- Modify: `services/cosa/api.ts` / handlers — endpoint `child`/`join`
- Modify: `packages/agent_core/coordination/control_plane_scheduler_client.py`
- Modify: `packages/agent_core/coordination/supervisor.py`
- Modify: `services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts`
- Create: `tests/agent_core/coordination/test_durable_supervisor_subprocess.py`

**Interfaces:**
- Consumes: `DurableSupervisor` + `ChildSchedulerProtocol` (`78e2b142`); scheduler `scheduleTask`/`pollDueTasks`/`heartbeatTask`/`completeTask`/`reclaimStuckTasks` (P0/pre-existing).
- Produces:
  - Cột mới trên `control_plane.scheduled_tasks`: `parent_task_id TEXT`, `child_id TEXT`, `depends_on JSONB NOT NULL DEFAULT '[]'`, `join_policy TEXT`, `join_quorum INTEGER`. Index `(parent_task_id)`, unique `(parent_task_id, child_id)`.
  - `scheduleChildTask(params & { parentTaskId, childId, dependsOn, joinPolicy, joinQuorum, blocked })` → `ScheduledTaskRow` (status `blocked` nếu `blocked`, ngược lại `pending`).
  - `resolveJoin(parentTaskId)` → `{ satisfied, completed[], pending[] }`; side effect: unblock child có `depends_on` đã completed.
  - Endpoints `expose:false`: `POST /control-plane/internal/scheduled-tasks/child`, `GET .../children?parentTaskId=`, `POST .../child/complete`.
  - `HttpControlPlaneSchedulerClient` += `schedule_child_task(...)`, `list_children(parent_task_id)`, `complete_child(...)` khớp `ChildSchedulerProtocol`.
  - `SupervisorCoordinator.execute_mission`: nếu bất kỳ `specialist_spec.capability_refs` là write (dùng `spec_has_write_capability`) → route qua `DurableSupervisor` thay `ParallelCoordinator`; ngược lại giữ `_parallel` cho read-only synthesis.

- [ ] **Step 1: Migration + schema cột** — viết `10_...up.sql` (ALTER TABLE + index), cập nhật `control-plane-schema.ts`, comment nhóm bảng "execution scheduler — LOCAL Workspace Runtime Node".
- [ ] **Step 2: Test đỏ (TS)** — `control-plane-scheduler-crash-recovery.test.ts` thêm:
```ts
it("child with unmet depends_on is created blocked, unblocked on parent completion", ...)
it("resolveJoin('all') satisfied only when every child completed", ...)
it("resolveJoin('quorum', 2) satisfied at 2 of 3", ...)
it("child dependency edges + join_policy survive reclaimStuckTasks", ...)
it("stale claim token cannot complete a re-claimed child", ...)
```
- [ ] **Step 3: Implement `scheduleChildTask` + `resolveJoin`** — tái dùng `scheduleTask` core; `resolveJoin` = query children by `parent_task_id`, tính `satisfied` theo `join_policy`/`join_quorum`, `UPDATE ... SET status='pending' WHERE status='blocked' AND depends_on <@ (completed set)`.
- [ ] **Step 4: Endpoints + Python client** — 3 endpoint `expose:false`; `HttpControlPlaneSchedulerClient` 3 method mới trả/nhận shape khớp `ChildSchedulerProtocol` (chú ý `list_children` trả list dict có `child_id`/`status`/`scheduled_task_id`/`join_policy`/`join_quorum`/`depends_on`/`result`/`idempotency_key`).
- [ ] **Step 5: `supervisor.py` routing** — thêm nhánh write → `DurableSupervisor(scheduler=<HttpControlPlaneSchedulerClient adapter>)`. Adapter: wrap client methods thành `ChildSchedulerProtocol`.
- [ ] **Step 6: Cross-process test (Python)** — `test_durable_supervisor_subprocess.py`: spawn worker process thật (theo mẫu `tests/apps/cosa/worker/test_crash_recovery_subprocess.py`), tạo 3 child, kill sau 2 child completed, process mới `resume()` → child thứ 3 vẫn `pending`, `is_join_satisfied` False; `record_child_result` lặp idempotency_key → không double side effect. **Cần Postgres chạy được** — xem Task 6 Step 3.
- [ ] **Step 7: Chạy**
```bash
cd services/cosa && npx vitest run tests/control-plane-scheduler-crash-recovery.test.ts --reporter=dot
PYTHONPATH=. .venv/bin/pytest tests/agent_core/coordination/ -q
# subprocess test: chỉ khi DB sẵn sàng
```
- [ ] **Step 8: Commit** (migration+schema; scheduler+endpoints; client+supervisor+tests)

---

## Task 6: P2 metrics nhỏ + semantic retrieval + verify

### 6a. P2 metrics còn thiếu

**Files:** `services/company/events/` (nơi P0 Task 5 phát metric), `docs/operations/event-backbone-capacity-review.md`
- [ ] Thêm gauge `event_outbox_backlog` — scrape `SELECT count(*) FILTER (WHERE status='pending'), extract(epoch from now()-min(created_at)) FROM integration.event_outbox`. Test: `event-operations.test.ts` thêm `it("exposes outbox backlog gauge")`.
- [ ] Thêm đo `event_replay_duration_seconds` quanh đường replay/DLQ retry batch.
- [ ] Xoá mục tương ứng khỏi `## Metric gaps` trong capacity-review doc.
- [ ] Commit.

### 6b. Semantic retrieval thật (có decision point)

**Decision (Step 0):** chọn embedding provider. Ứng viên: (a) DeepSeek/OpenAI embeddings qua LiteLLM (đã có LiteLLM trong stack); (b) local sentence-transformers (offline, hợp local-first). **Khuyến nghị (b)** cho local-first residency — embedding không rời node.

**Files:** `packages/agent_core/knowledge/embedding.py` (mới), `packages/agent_core/knowledge/providers/postgres.py`, `packages/agent_core/migrations/NNN_knowledge_chunk_embedding_index.sql`, `tests/agent_core/knowledge/test_semantic_retrieval.py`
- [ ] **Step 1** Test đỏ: `search_chunks_semantic` trên Postgres store trả kết quả sắp theo cosine; `retrieve(mode="semantic")` với embedder thật + eval score đạt ngưỡng → `mode_used="semantic"`.
- [ ] **Step 2** `EmbeddingProvider` protocol + impl chọn ở Step 0; `embed_query(text) -> list[float]`, `embed_chunks(texts) -> list[list[float]]`.
- [ ] **Step 3** `PostgresKnowledgeStore.search_chunks_semantic`: bỏ `NotImplementedError`, thực thi `ORDER BY embedding <=> :qvec` (pgvector); migration thêm index `USING hnsw (embedding vector_cosine_ops)`.
- [ ] **Step 4** Ingestion (`KnowledgeIngestionService.ingest_*`) gọi `embed_chunks` khi có provider; `KnowledgeSnapshot.embedding_model`/`embedding_version` set thật; `retrieval_eval_run_id` gắn khi eval pass.
- [ ] **Step 5** `retrieve()` nhận `embedder` (hoặc `query_embedding` do caller tính) — cập nhật call-sites.
- [ ] **Step 6** Benchmark eval suite (`tests/agent_core/knowledge/test_retrieval_evals.py` mở rộng): so semantic vs lexical trên fixture, ghi `min_eval_score` mặc định từ kết quả.
- [ ] **Step 7** Chạy + commit.

### 6c. Verify P0 + fix DB infra

- [ ] **Step 1** Audit P0 DoD (spec `§7`): chạy `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa tests/contract tests/architecture -q` + `cd services/company && npx vitest run --reporter=dot`. Đối chiếu từng DoD #1–#9 với test tồn tại; ghi gap (nếu có) vào issue.
- [ ] **Step 2** Kịch bản e2e thủ công P0 (spec `...-p0.md` §Verification) trên môi trường có Postgres.
- [ ] **Step 3** Fix 2 test DB-infra: `tests/apps/cosa/worker/test_crash_recovery_subprocess.py`, `tests/apps/cosa/test_sse_reconnect_e2e.py` — `asyncpg InvalidPasswordError for user "javis_app"`. Nguyên nhân: test cần Postgres với role `javis_app` mà env local chưa tạo. Sửa: (a) `docker-compose` / `make db-test-setup` tạo role + DB test đúng creds; hoặc (b) skipif rõ ràng khi `TEST_DATABASE_URL` không set (đừng để fail mập mờ). Commit.

---

## Self-Review

| Điều còn hở (từ báo cáo) | Task |
| --- | --- |
| 1. P1 Task 2 phần TS `services/cosa` | Task 5 |
| 2. Wiring composition root (memory/knowledge/publish/trigger evidence/seed/enable-endpoint) | Task 2, Task 3, Task 4 |
| 3. Semantic retrieval thật | Task 6b |
| 4. P2 việc nhỏ (backlog gauge, replay duration, review-log signoff) | Task 6a (signoff là thao tác vận hành, không phải code) |
| 5. Reconcile docs (exec-plane-split, P1 plan, e6351881 note) | Task 1 |
| 6. Verify P0 + fix DB infra test | Task 6c |

**Placeholder scan:** interface + test-name cụ thể cho mọi task; decision point (embedding provider, publish sink route) nêu rõ + khuyến nghị. Task 5 có full DDL cột; code block đầy đủ cho sink/helper. Chỗ chưa có code block chi tiết (resolveJoin SQL, evidence_store queries) mô tả thuật toán + bảng nguồn — chấp nhận được cho closeout plan đa lĩnh vực.
**Type consistency:** `ChildSchedulerProtocol` (list_children shape) khớp giữa Task 5 client và `durable_supervisor.py` đã landed. `can_enable_trigger` signature khớp Task 3/Task 4. `publish_knowledge_source(snapshot=, approved=, persisted=, reviewed_by=, reviewed_at=, correlation_id=, emit=)` khớp `935c3dc6`.

---

## Verification (toàn cục, sau Task 6)

```
PYTHONPATH=. .venv/bin/pytest tests/agent_core tests/apps/cosa tests/contract tests/architecture -q
cd services/company && npx vitest run --reporter=dot
cd services/cosa && npx vitest run --reporter=dot
make services-migrate-company && python packages/agent_core/scripts/migrate.py
grep -rn 'COSA_CONTROL_PLANE_URL' apps/cosa --include='*.py' | grep -v 'config/planes.py' | grep -v test   # → 0
grep -rniE 'kafka|redpanda|nats' deploy/ docker-compose*.yml infra/ 2>/dev/null   # → 0
```

**e2e thủ công (cần Postgres):**
1. Production build: unset `AGENT_CORE_DATABASE_URL` → `build_cosa_agent_plane()` raise; set → plane có `memory_service` + `knowledge_ingestion_service` là Postgres-backed.
2. Review một knowledge source → PUBLISHED → đúng 1 `knowledge.source.published.v1` trong `integration.event_outbox`, payload reference-only.
3. Tạo trigger rule `mode=write` không evidence → `POST .../enable` trả 422. Gắn evidence pass + fingerprint khớp → 202 `pending_human_approval`.
4. `DurableSupervisor` qua `HttpControlPlaneSchedulerClient` thật: 3 child, kill worker sau 2, process mới `resume` → child 3 `pending`, join chưa satisfied; replay `record_child_result` → side effect = 1.
5. Semantic retrieval: ingest doc có embedding → `retrieve(mode="semantic", eval_score đạt ngưỡng)` trả `mode_used="semantic"`, citations workspace-scoped; hạ eval_score → fallback `lexical`.

---

## Execution Handoff

Thứ tự khuyến nghị: **Task 1** (docs) → **Task 2** → **Task 3** → **Task 4** → **Task 6a/6c** → **Task 5** (worktree riêng) → **Task 6b** (sau khi chốt embedding provider).

Task 5 và các cross-process/DB test cần Postgres chạy được với role `javis_app` — Task 6c Step 3 dựng cái đó trước.

Không cho phép: deploy VPS, cài broker, cấu hình provider ngoài, xoá dữ liệu hiện có.
