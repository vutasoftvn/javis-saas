# Spec chi tiết: COSA Local-First Event-Driven Agent Operating Model

- Nguồn phân tích: `docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-local-first.md`
- Đích lưu trong repo (hành động đầu tiên sau khi duyệt): `docs/superpowers/specs/2026-08-28-event-driven-agent-operating-model-design.md` + `git commit`
- Verify tiền đề: 3 lượt explore codebase 2026-08-28 (chi tiết trong "Context"). PDF Confluent đã trích mục lục và đối chiếu bảng §1.

---

## Context — vì sao làm việc này

COSA có durable run/checkpoint/scheduler nhưng **chưa có business-event substrate**. Xác minh trực tiếp trên code:

| Sự thật code (file:line) | Hệ quả |
| --- | --- |
| `services/company/shared/events.ts:14-18` — `DomainEvent = { name, emittedAt, payload }` | Không eventId/schemaVersion/correlation/causation/actor/producer/classification |
| `services/company/operations/services/task.service.ts:109-130` — insert DB rồi `taskEvents.publish()` ở bước kế tiếp | Cửa sổ dual-write: commit xong mà publish fail ⇒ fact mất im lặng |
| `okr.service.ts:192-207` — `getObjectiveProgressService` (hàm đọc) gọi `okrEvents.publish()` | Read-side effect; phát "fact" giả từ query |
| `task-events.service.ts:19` + `okr-events.service.ts:11` — 2 Encore `Topic`, `new Subscription()` = 0 toàn repo | Event tạo ra rồi mồ côi ở boundary |
| `shared/events.ts:9-12` — khai báo `experiment.created` / `evidence.recorded` / `gate.evaluated` / `decision.recorded` | 4 event strategy-domain không nằm trong allowlist §3.2 plan gốc |
| `shared/events.ts:1-3` — comment trỏ `backend/agentos/core/events.py` | Thư mục đã xoá (CLAUDE.md); comment rot |
| `apps/cosa/composition/agent_plane.py:273-275` — scheduler client + lease client cùng `COSA_CONTROL_PLANE_URL` (fallback `http://127.0.0.1:4001`) | Không có ranh giới execution-local vs platform-central. Cùng biến còn dùng ở `knowledge_ingestion/control_plane_client.py:38`, `capabilities/connector_grant_client.py`, `worker/handlers.py`, `api/routes.py` |
| `agent_plane.py:177-251` — fail-fast khi thiếu `AGENT_CORE_DATABASE_URL` cho Run/Conversation/SpecRegistry/Governance/StreamEvent repo | Pattern fail-fast production đã có sẵn để bắt chước |
| `services/cosa/services/control-plane-scheduler.service.ts` — `pollDueTasks` dùng `.for("update",{skipLocked:true})`, `claim_token` (fencing), `visibility_timeout_at` (120s), retry backoff `5*2^(n-1)` cap 300s, dead-letter khi `attempt>=maxAttempts`, `reclaimStuckTasks` sweeper | Cơ chế durable queue tốt — tái dùng, không viết lại |
| `services/cosa/storage/control-plane-schema.ts` — schema Postgres tên `control_plane`; bảng `scheduledTasks`, `runtimeLeases`, `workers` (execution) vs `connectorAuthorizations`, `sessionConnectorGrants` (platform) | Cần label rõ nhóm execution = local |
| `apps/cosa/api/event_stream.py:84-159` — `emit()` persist (`repository.append`) TRƯỚC fanout; `stream_events()` replay từ DB; `redact_ux_event_payload()` strip `secret_ref`/`access_token`/... theo allowlist `UX_EVENT_TYPES` | SSE là UX ledger đúng mục đích — cần mở rộng redaction thành allowlist ghi (storage-time), không chỉ response-time |
| `apps/cosa/api/routes.py:445,639` — chỉ có `GET /agent/runs/{id}/events` (SSE) và `GET /agent/sessions/{id}/timeline`; **không** `/agent/internal/events` | Chưa có event intake |
| Không có `apps/cosa/events/` module | Phải tạo mới |
| `packages/agent_core/memory/service.py:15` — `self._store = store or InMemoryMemoryStore()`; `store.py:48-64` `get_memory_store()` tạo `PostgresMemoryStore` | Default production = in-memory; Postgres tồn tại nhưng không phải default path |
| `packages/agent_core/knowledge/providers/postgres.py:249-252` — search ILIKE keyword-only; `chunk_embeddings` table + `KnowledgeChunk.embedding` có nhưng không dùng; `knowledge/snapshot.py:12-60` `KnowledgeSnapshot` có `source_refs`/`embedding_model`/`index_recipe_version` | Retrieval chưa semantic; snapshot identity concept đã có |
| `apps/cosa/knowledge_ingestion/handler.py:137-139` — default `FakeDocumentMalwareScanner(verdict="clean")`; `scanner.py:82-114` `assert_production_scanner_ready()` tồn tại nhưng chưa gọi ở activation path | Fake scanner là default; guard chưa wired |
| `packages/agent_core/coordination/parallel.py:55` — `asyncio.gather(*(run_one(t) ...))`; `supervisor.py:77-79` dùng `ParallelCoordinator`; `delegate.py:17-30` gọi `kernel.run()` trực tiếp; `wait_resolver.py:34-134` có `resolve_wait_by_event()` (đã event-driven) | Multi-agent fan-out chưa durable child-task |
| `packages/agent_core/workflows/engine.py:172-311` — DAG execute, checkpoint in-memory, compensation; không persistence layer ngoài checkpoint | Chưa durable child-task adapter |
| `packages/agent_core/evals/promotion_gate.py:21-50` — `PromotionGate.check()` validate evidence (policy version, eval runs present, checks passed, freshness) nhưng **không side effect**, không activate | Chưa nối làm release gate |
| grep `^from apps|^from services` trong `packages/agent_core/` = 0 | Bất biến isolation phải giữ |

**Kết quả mong muốn:** COSA thành hệ vận hành agent event-driven local-first — business fact tin cậy (transactional outbox) kích hoạt tác vụ agent bền; dữ liệu Workspace không rời local node mặc định; VPS chỉ giữ identity/license/policy đã lọc + telemetry tổng hợp; RAG/multi-agent/eval-gate có lộ trình production; **không** Kafka/broker ở P0/P1.

### Đối chiếu tài liệu nguồn

- CLAUDE.md trỏ `COSA_FINAL_INTEGRATION_...2026-08-25.md` + `BLUEPRINT_V2_RECONCILED_...` là nguồn cao nhất. **Cả hai không còn trong repo** (chỉ còn `docs/archive/2026-08/COSA_FINAL_INTEGRATION_EXECUTION_STATUS_2026-08-25.md` + blueprint V2 chưa-reconciled). `docs/architecture/adr/` **rỗng**.
- Code đã đổi nhiều lần, doc nguồn mất ⇒ **neo vào code hiện tại**, không vào plan cũ. ADR dir rỗng ⇒ không có ADR mâu thuẫn.
- PDF "Event-Driven Design for Agents" (Confluent / Sean Falconer 2025): trích được mục lục + khung chương. Đối chiếu bảng §1 plan gốc: Anatomy of an Agent ✅; Kafka-as-nervous-system → cố ý lệch sang Postgres outbox, có biện minh ✅; Multi-Agent Patterns (Orchestrator-Worker / Hierarchical / Blackboard / Market-Based) → chỉ làm hierarchical durable, cố ý bỏ 2 pattern kia ✅; Stream-Connect-Process-Govern + DLQ + Data Freshness ✅. Mapping trung thực, bảo thủ. PDF không chứa chỉ thị thực thi.

---

## Điểm phản biện với plan gốc (đã thống nhất hướng xử lý)

| # | Vấn đề | Xử lý |
|---|---|---|
| PB-1 | Task 1 (tách `COSA_EXECUTION_PLANE_URL` / `COSA_PLATFORM_CONTROL_PLANE_URL`) đụng `worker/handlers.py`, `api/routes.py`, `knowledge_ingestion`, `connector_grant_client` — blast radius rộng; trộn concern deployment-topology vào spec event | **Tách `SPEC-EXEC-PLANE-SPLIT` riêng.** Spec này *phụ thuộc*, không chi tiết hoá. Task 4 & Task 7 khai báo dependency cứng |
| PB-2 | Không ADR chống lưng hướng local-first; file plan gốc untracked/chưa review; repo có tiền sử tự tuyên bố "Wave/Phase xong" rồi bị audit lật | **Task 0 — `ADR-LOCAL-FIRST-001`** viết từ đầu, neo vào 4 vùng KT + 11 quy tắc CLAUDE.md + trạng thái code. P0, đi trước mọi task đổi hành vi. Task 2–3 (chỉ *thêm*) chạy song song lúc ADR review |
| PB-3 | Envelope định nghĩa 2 lần: TS (`envelope.ts`) + Python (`contracts.py`) ⇒ drift ngầm | Thêm `docs/architecture/event-envelope.schema.json` (JSON Schema) làm SoT ngôn ngữ-trung tính. Cả 2 phía validate theo file. Contract test CI (TS + Python) fail nếu lệch |
| PB-4 | Allowlist §3.2 bỏ sót 4 event strategy-domain đã khai báo (`shared/events.ts:9-12`) | Task 2 xử lý dứt: nâng canonical envelope hoặc `@deprecated` rõ nếu chưa có use case |
| PB-5 | `shared/events.ts:1-3` comment trỏ `backend/agentos/...` đã xoá | Task 2 cập nhật/xoá comment stale khi sửa file |
| PB-6 | Outbox table đặt `operations/migrations/` + `operations.ts` nhưng là concern cross-domain (finance cũng produce — §3.2); vi phạm nhẹ "schema tập trung `<app>/shared/db/schema/`" | Schema ở `services/company/shared/db/schema/integration.ts` (Postgres schema `integration`). Migration file vẫn ở service sở hữu (Encore migration per-service), import type từ shared |
| PB-7 | "Xoá shape cũ sau khi mọi producer migrate" — nhưng chỉ 2 producer + 0 consumer | **Cutover thẳng trong Task 2.** Xoá `DomainEvent`/`makeDomainEvent`. Không compat shim kéo dài |
| PB-8 | `schemaVersion: 1` literal type cản rule "consumer bỏ qua major version tương lai" | `schemaVersion: number` + hằng `CURRENT_SCHEMA_VERSION = 1`. Validator so range |
| PB-9 | DoD #1 "delivered exactly once in effect" dễ đọc nhầm exactly-once delivery | Viết lại: "at-least-once delivery + consumer idempotency ⇒ hiệu ứng đúng-một-lần" |
| PB-10 | Task 7 (durable supervisor) ngầm phụ thuộc scheduler-tại-local ⇒ phụ thuộc `SPEC-EXEC-PLANE-SPLIT` | P1 note: Task 7 **BỊ CHẶN** tới khi `SPEC-EXEC-PLANE-SPLIT` landed. Task 2–6, 8 không bị chặn |
| PB-11 | Plan gốc không nêu behaviour khi trigger rule vắng mặt cho một event type đã relay | Chuẩn hoá: intake trả `ignored_rule_disabled` (không lỗi); metric `trigger_no_rule_total` tăng; event vẫn ghi inbox (audit) nhưng không schedule |
| PB-12 | Không nêu retention/cleanup cho outbox `delivered` rows và inbox rows | Task 5: cron `pruneDeliveredOutbox(olderThan)` giữ `delivered` N ngày (mặc định 30) rồi xoá; inbox giữ theo cùng policy; DLQ rows **không** auto-prune |

---

## Phạm vi & quan hệ giữa các spec

- **Spec này (`SPEC-EVENT-OPERATING-MODEL`)**: Task 0 (ADR) + Task 2 → Task 9 của plan gốc, chi tiết theo TDD.
- **Phụ thuộc ngoài — `SPEC-EXEC-PLANE-SPLIT`** (viết riêng): thay `COSA_CONTROL_PLANE_URL` → `COSA_EXECUTION_PLANE_URL` + `COSA_PLATFORM_CONTROL_PLANE_URL`; fail-fast khi Workspace Runtime Node định queue business work lên platform từ xa; cập nhật mọi call-site. **P0 prerequisite** cho Task 4 và Task 7.
- **Ngoài phạm vi cả hai:** deploy VPS, cài broker, cấu hình provider ngoài, xoá dữ liệu hiện có.

---

## Kiến trúc đích (text)

```
Workspace Runtime Node (local)
  Company Services (business truth, Encore/TS)
    └─(cùng DB transaction)→ integration.event_outbox        [Task 3]
                                   │
                    outbox-relay.service.ts (cron, bounded)  [Task 4]
                                   │ signed POST, local-only
                                   ▼
  apps/cosa  POST /agent/internal/events  (private)           [Task 4]
    ├─ contracts.py   validate envelope theo schema JSON
    ├─ inbox.py       ghi (workspace_id, event_id, consumer_name) atomic
    ├─ trigger_policy.py  resolve EventTriggerRule (exact match, rate limit, caps)
    └─ router.py      schedule reference-only task qua LOCAL execution plane
                                   ▼
  services/cosa control-plane-scheduler (local profile)       [reuse]
                                   ▼
  Agent Core run (capability + policy + approval + audit vẫn giữ thẩm quyền)

VPS Platform Control Plane  ── chỉ nhận: identity/license, policy/entitlement đã lọc,
                                registry/promotion metadata, telemetry tổng hợp sanitized
```

Luồng dữ liệu duy nhất tới VPS: authenticated policy/config pull + aggregate telemetry push. **Raw business `payload` không lên VPS.**

---

## Nguyên tắc thực thi chung (mọi task)

- **TDD bắt buộc** (`superpowers:test-driven-development`): viết test đỏ → xác nhận đỏ → implement tối thiểu → xanh. Không tuyên bố xong khi chưa chạy test (CLAUDE.md #11).
- **An toàn working tree** (CLAUDE.md #10): `git status` trước thao tác mất mát; không `--force`/`--no-verify`; không tự xoá/archive file khác.
- **Migration**: kiểm tra số khả dụng *tại từng service* ngay trước khi tạo. Company hiện cao nhất = **16** ⇒ file mới `17_...` (xác nhận lại lúc chạy). Sau khi thêm: `make services-migrate-company`. `services/cosa` migration: kiểm số trong `services/cosa/migrations/` trước khi thêm.
- **Comment tiếng Việt cho why**; identifier/log/error tiếng Anh.
- **`packages/agent_core` không import `apps/` hay `services/`.** Contract chung ở agent_core hoặc company shared layer; adapter ở composition boundary.
- **Classification trước persist**; không log/stream secret/token/raw PII/raw tool IO mặc định.
- **Encore** (CLAUDE.md): lỗi qua `APIError` (không throw `Error` trần); endpoint nội bộ `expose: false`; schema Drizzle ở `<app>/shared/db/schema/`.

---

## Task 0 — ADR local-first data residency + execution-plane boundary  *(P0, đi trước code đổi hành vi)*

**Mục tiêu:** chốt bằng văn bản quyết định kiến trúc mà toàn bộ spec dựa vào.

**Files:**
- Tạo: `docs/architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md`
- Tạo: `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` (khung — Task 9 điền số đo)
- Tạo: `tests/architecture/test_adr_local_first_references.py`

**Nội dung `ADR-LOCAL-FIRST-001` — heading bắt buộc:**
1. `## Context` — 4 vùng KT CLAUDE.md; code hiện chỉ 1 `COSA_CONTROL_PLANE_URL`; doc nguồn cũ mất; ADR dir rỗng.
2. `## Decision` — Workspace Runtime Node local giữ Company Services + AgentOS + Agent Core Postgres + local execution scheduler + transactional outbox/inbox + evidence/artifact/knowledge. VPS chỉ: platform identity/license, policy/entitlement đã lọc, registry/promotion metadata, telemetry tổng hợp sanitized.
3. `## Data residency` — bảng (copy §2.1 plan gốc): business fact payload / run-checkpoint-tool result / RAG source-chunk-embedding / incident evidence = **local, không lên VPS mặc định**; chỉ skill/agent/policy identity + aggregate/sanitized metadata lên VPS.
4. `## Execution-plane rule` — `apps/cosa` không silently fallback từ local execution URL sang remote platform URL. Scheduler task payload lưu *reference* (`workspace_id`, event ID, artifact/ref IDs, exact spec pins), không nhân bản raw business payload.
5. `## Event backbone` — PostgreSQL transactional outbox relay là backbone P0/P1. Kafka/Redpanda/NATS **không** default; chỉ đánh giá lại qua `ADR-LOCAL-EVENT-BACKBONE-001` khi số đo chứng minh Postgres relay không đáp ứng.
6. `## Status` — ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION (5 trục tách biệt). ADR chỉ chốt trục quyết định.
7. `## Relates` — quan hệ với `ADR-CONTROLPLANE-001` (control plane primitives tại `services/cosa` — vẫn đúng, nay thêm deployment profile local).

**Test cases (`test_adr_local_first_references.py`):**
- `test_adr_file_exists`
- `test_adr_has_required_headings` — regex 6 heading trên
- `test_backbone_adr_referenced_by_runbook` — sau Task 5, runbook chứa link `ADR-LOCAL-EVENT-BACKBONE-001`
- `test_no_broker_in_deploy_manifests` — grep `deploy/`, `docker-compose*.yml`, manifest → 0 match `kafka|redpanda|nats`

**Steps:**
- [ ] **Step 1**: Viết test → chạy `PYTHONPATH=. .venv/bin/pytest tests/architecture/test_adr_local_first_references.py -q` → **FAIL**.
- [ ] **Step 2**: Viết 2 ADR (LOCAL-FIRST-001 đầy đủ; LOCAL-EVENT-BACKBONE-001 khung + placeholder "số đo: Task 9").
- [ ] **Step 3**: Chạy lại → **PASS**. Commit ADR trước khi mở task đổi hành vi.

---

## Task 2 — Canonical business-event envelope + producer semantics  *(P0)*

**Mục tiêu:** mọi business event mang đủ danh tính giao vận + governance; không read path nào phát fact.

**Files:**
- Tạo: `docs/architecture/event-envelope.schema.json` — JSON Schema Draft 2020-12, SoT (PB-3).
- Tạo: `services/company/shared/events/envelope.ts` — types, `makeBusinessEvent<T>()`, `validateEnvelope()`, classification guard, payload size guard.
- Sửa: `services/company/shared/events.ts` — re-export contract mới; **xoá** `DomainEvent`/`makeDomainEvent` sau khi producer chuyển (PB-7); xử lý 4 event strategy-domain (PB-4); xoá comment `backend/agentos/...` (PB-5).
- Sửa: `services/company/operations/services/task-events.service.ts`, `okr-events.service.ts` — build canonical envelope.
- Sửa: `services/company/operations/services/okr.service.ts` — **xoá** `okrEvents.publish` khỏi `getObjectiveProgressService`.
- Sửa test: `services/company/shared/tests/events.test.ts`, `operations/tests/task.test.ts`, `operations/tests/okr.test.ts`.
- Tạo: `services/company/shared/events/fixtures/` — mẫu envelope JSON export cho cross-language test.
- Tạo: `tests/contract/test_event_envelope_cross_language.py`.

**`event-envelope.schema.json` (rút gọn):**
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://cosa.local/schemas/business-event-envelope/v1",
  "type": "object",
  "required": ["eventId","eventType","schemaVersion","occurredAt","workspaceId",
               "aggregateType","aggregateId","correlationId","actor","producer",
               "classification","payload"],
  "properties": {
    "eventId":       {"type":"string","format":"uuid"},
    "eventType":     {"type":"string","pattern":"^[a-z]+\\.[a-z_]+\\.[a-z_]+\\.v[0-9]+$"},
    "schemaVersion": {"type":"integer","minimum":1},
    "occurredAt":    {"type":"string","format":"date-time"},
    "workspaceId":   {"type":"string","minLength":1},
    "aggregateType": {"type":"string"},
    "aggregateId":   {"type":"string"},
    "correlationId": {"type":"string"},
    "causationId":   {"type":"string"},
    "actor":    {"type":"object","required":["kind","id"],
                 "properties":{"kind":{"enum":["user","agent","system"]},"id":{"type":"string"}}},
    "producer": {"type":"object","required":["service","version"],
                 "properties":{"service":{"type":"string"},"version":{"type":"string"}}},
    "classification": {"enum":["internal","confidential","restricted"]},
    "payload":  {"type":"object"}
  },
  "additionalProperties": false
}
```

**`envelope.ts` (interface + guard):**
```ts
export const CURRENT_SCHEMA_VERSION = 1;                 // PB-8: number
export const MAX_PAYLOAD_BYTES = 16 * 1024;
const FORBIDDEN_PAYLOAD_KEYS = /(access_token|secret|password|api[_-]?key|authorization|private[_-]?key)/i;

export interface BusinessEventEnvelope<TPayload extends Record<string, unknown>> {
  eventId: string;              // UUID v4 — idempotency identity cho delivery (≠ aggregateId)
  eventType: string;            // "domain.entity.action.vN" — past tense
  schemaVersion: number;
  occurredAt: string;           // ISO-8601 UTC, fact time
  workspaceId: string;
  aggregateType: string;
  aggregateId: string;
  correlationId: string;        // chảy từ request → event → trigger → run → audit
  causationId?: string;         // event/command trước đó (nếu biết)
  actor: { kind: "user" | "agent" | "system"; id: string };
  producer: { service: string; version: string };
  classification: "internal" | "confidential" | "restricted";
  payload: TPayload;            // bounded; chỉ IDs + changed state; KHÔNG credentials
}

export interface BusinessEventInput<T> {
  eventType: string; workspaceId: string; aggregateType: string; aggregateId: string;
  correlationId: string; causationId?: string;
  actor: BusinessEventEnvelope<T>["actor"];
  classification: BusinessEventEnvelope<T>["classification"];
  payload: T;
}

export function makeBusinessEvent<T extends Record<string, unknown>>(
  input: BusinessEventInput<T>
): BusinessEventEnvelope<T>;   // gen eventId (uuid), occurredAt (now), producer (từ service const); validate

export function validateEnvelope(e: unknown): asserts e is BusinessEventEnvelope<Record<string, unknown>>;
// throws APIError.invalidArgument nếu: thiếu field, eventType sai pattern, payload > MAX_PAYLOAD_BYTES,
// key payload match FORBIDDEN_PAYLOAD_KEYS, classification="restricted" mà payload không phải reference shape
```

**Bất biến envelope (copy §3.1 plan gốc):** `eventId` = idempotency identity; ordering chỉ per-aggregate theo `occurredAt + eventId`; producer validate payload schema trước ghi outbox; consumer bỏ qua major schema tương lai + ghi delivery failure nhìn thấy; `restricted` ⇒ payload reference/minimization; `correlationId` chảy end-to-end.

**Xử lý 4 event strategy-domain (PB-4):** Task 2 kiểm `experiment.service.ts` / strategy handlers có publish thật không. Nếu có consumer/use case → nâng canonical (`strategy.experiment.created.v1`, ...). Nếu không → giữ hằng string nhưng đánh dấu `/** @deprecated chưa có producer/consumer — không dùng cho canonical envelope */` và loại khỏi `makeBusinessEvent` type union.

**Test cases:**
- `events.test.ts`: `makeBusinessEvent generates uuid eventId`; `occurredAt is ISO UTC`; `producer populated from service constant`; `validateEnvelope rejects missing correlationId`; `rejects non-past-tense eventType`; `rejects payload with access_token key`; `rejects payload > 16KB`; `restricted classification requires reference payload`.
- `task.test.ts`: `publishes canonical task.created.v1 with full identity on genuine insert`; `does not re-publish on idempotencyKey retry`; `task.completed.v1 emitted only on status→done transition`.
- `okr.test.ts`: `getObjectiveProgressService emits zero events` (spy `okrEvents.publish`, `toHaveBeenCalledTimes(0)`); `replaying the read has no side effect`.
- `test_event_envelope_cross_language.py`: load `event-envelope.schema.json` + mỗi fixture trong `shared/events/fixtures/` → `jsonschema.validate()` pass; assert field set fixture == `required` ∪ optional (không dư/thiếu).

**Steps:**
- [ ] **Step 1**: Viết test đỏ (danh sách trên).
- [ ] **Step 2**: `cd services/company && npx vitest run shared/tests/events.test.ts operations/tests/task.test.ts operations/tests/okr.test.ts --reporter=dot` → **FAIL**.
- [ ] **Step 3**: Implement `envelope.ts` + schema JSON + sửa 2 producer + xoá publish khỏi read path + cutover `events.ts`.
- [ ] **Step 4**: Chạy lại vitest + `PYTHONPATH=. .venv/bin/pytest tests/contract/test_event_envelope_cross_language.py -q` → **PASS**.

---

## Task 3 — Transactional local outbox, đóng cửa sổ dual-write  *(P0)*

**Files:**
- Tạo: `services/company/operations/migrations/17_local_event_outbox_inbox.up.sql` (xác nhận số 17 lúc chạy).
- Tạo: `services/company/shared/db/schema/integration.ts` (PB-6) — Drizzle schema.
- Tạo: `services/company/shared/events/outbox.repository.ts`.
- Sửa: `services/company/operations/services/task.service.ts`, `financial-transaction.service.ts` — thay `taskEvents.publish` bằng `appendOutboxEvent(tx, ...)` **trong cùng transaction**.
- Tạo test: `services/company/operations/tests/event-outbox.test.ts`.

**DDL `17_local_event_outbox_inbox.up.sql`:**
```sql
CREATE SCHEMA IF NOT EXISTS integration;

CREATE TABLE integration.event_outbox (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id              UUID NOT NULL UNIQUE,               -- idempotency identity
  workspace_id          TEXT NOT NULL,
  aggregate_type        TEXT NOT NULL,
  aggregate_id          TEXT NOT NULL,
  event_type            TEXT NOT NULL,
  schema_version        INTEGER NOT NULL,
  occurred_at           TIMESTAMPTZ NOT NULL,
  envelope              JSONB NOT NULL,                     -- immutable canonical envelope
  payload_hash          TEXT NOT NULL,                      -- sha256(canonical(payload))
  classification        TEXT NOT NULL,
  status                TEXT NOT NULL DEFAULT 'pending',    -- pending|claimed|delivered|dead
  attempt_count         INTEGER NOT NULL DEFAULT 0,
  max_attempts          INTEGER NOT NULL DEFAULT 8,
  claim_token           TEXT,
  visibility_timeout_at TIMESTAMPTZ,
  last_error            TEXT,
  dead_letter_reason    TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at          TIMESTAMPTZ
);
CREATE INDEX idx_event_outbox_due     ON integration.event_outbox (status, visibility_timeout_at)
  WHERE status IN ('pending','claimed');
CREATE INDEX idx_event_outbox_ws_aggr ON integration.event_outbox (workspace_id, aggregate_type, aggregate_id);
CREATE INDEX idx_event_outbox_type    ON integration.event_outbox (event_type);
```
(Bảng inbox nằm phía `apps/cosa` — Task 4, không trong migration company.)

**`outbox.repository.ts`:**
```ts
export interface OutboxRow { /* mirror DDL */ }

export async function appendOutboxEvent(
  tx: Transaction, e: BusinessEventEnvelope<Record<string, unknown>>
): Promise<void>;
// INSERT ... ON CONFLICT (event_id) DO NOTHING  → idempotent trong cùng tx với domain state

export async function claimDueOutboxEvents(workerId: string, limit: number): Promise<OutboxRow[]>;
// UPDATE ... SET status='claimed', claim_token=$tok, visibility_timeout_at=now()+interval '120s',
//   attempt_count=attempt_count+1
// WHERE id IN (SELECT id FROM integration.event_outbox
//              WHERE status='pending' OR (status='claimed' AND visibility_timeout_at < now())
//              ORDER BY occurred_at FOR UPDATE SKIP LOCKED LIMIT $limit)
// RETURNING *

export async function completeOutboxEvent(eventId: string, claimToken: string): Promise<boolean>;
// UPDATE ... SET status='delivered', delivered_at=now()
// WHERE event_id=$id AND claim_token=$tok AND status='claimed'  → false nếu stale token

export async function failOutboxEvent(
  eventId: string, claimToken: string, err: string
): Promise<void>;
// nếu attempt_count >= max_attempts → status='dead', dead_letter_reason=err
// ngược lại → status='pending', last_error=err, visibility_timeout_at = now() + backoff(attempt_count)
```

**Test cases (`event-outbox.test.ts`):**
- `transaction rollback writes neither task nor outbox row`
- `successful task write creates exactly one outbox row`
- `relay failure leaves a retryable pending row with incremented attempt_count`
- `duplicate client idempotencyKey does not create two domain facts or two events`
- `stale claim token cannot complete a re-claimed event`
- `attempt_count >= max_attempts moves row to status=dead with reason`
- `claimDueOutboxEvents respects SKIP LOCKED (two concurrent claimers get disjoint rows)`

**Steps:**
- [ ] **Step 1**: Viết test đỏ.
- [ ] **Step 2**: `cd services/company && npx vitest run operations/tests/event-outbox.test.ts operations/tests/task.test.ts --reporter=dot` → **FAIL**.
- [ ] **Step 3**: Implement schema + repository; thay direct topic publish ở task/finance write bằng `appendOutboxEvent(tx, ...)` cùng tx.
- [ ] **Step 4**: `make services-migrate-company && cd services/company && npx vitest run operations/tests/event-outbox.test.ts operations/tests/task.test.ts --reporter=dot` → **PASS**.

---

## Task 4 — Local relay + AgentOS inbox + trigger path có policy  *(P0; phụ thuộc `SPEC-EXEC-PLANE-SPLIT`)*

**Files:**
- Tạo: `services/company/events/outbox-relay.service.ts`, `outbox-relay.cron.ts`.
- Tạo: `apps/cosa/events/__init__.py`, `contracts.py`, `inbox.py`, `trigger_policy.py`, `router.py`.
- Tạo: `apps/cosa/api/event_intake_routes.py`.
- Sửa: `apps/cosa/api/app.py` (mount router), `apps/cosa/composition/agent_plane.py` (đăng ký intake/trigger; dùng explicit local execution-plane client từ `SPEC-EXEC-PLANE-SPLIT`; no remote fallback).
- Tạo migration `apps/cosa`: bảng `event_inbox` (kiểm số migration trước).
- Tạo test: `tests/apps/cosa/test_local_event_intake.py`, `services/company/events/tests/outbox-relay.test.ts`.

**DDL `event_inbox` (apps/cosa Agent Core Postgres):**
```sql
CREATE TABLE event_inbox (
  id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workspace_id   TEXT NOT NULL,
  event_id       UUID NOT NULL,
  consumer_name  TEXT NOT NULL,
  event_type     TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  received_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome        TEXT NOT NULL,           -- accepted|duplicate|ignored_rule_disabled|policy_denied
  scheduled_task_id TEXT,                 -- reference tới local execution plane task
  UNIQUE (workspace_id, event_id, consumer_name)
);
```

**Endpoint contract — `POST /agent/internal/events`** (`expose:false` tương đương; local service auth):
```
Request headers:  X-COSA-Local-Signature: <hmac hoặc mTLS identity>
Request body:     BusinessEventEnvelope  (validate theo event-envelope.schema.json)
Response 200:     { "outcome": "accepted",  "scheduledTaskId": "<id>" }
                  { "outcome": "duplicate" }
                  { "outcome": "ignored_rule_disabled" }
                  { "outcome": "policy_denied", "reason": "missing_capability:operations.task.read" }
Response 400:     APIError invalidArgument  — envelope invalid
Response 401:     APIError unauthenticated  — signature invalid
Response 403:     APIError permissionDenied — cross-workspace envelope
```

**`EventTriggerRule` (workspace-scoped, `trigger_policy.py`):**
```python
@dataclass(frozen=True)
class EventTriggerRule:
    rule_id: str
    workspace_id: str
    event_type: str                       # exact match, incl. .vN
    agent_spec: PinnedSpecIdentity        # id + version + definition_hash
    mode: Literal["artifact_only", "proposal", "write"]   # autonomy ceiling
    max_runs_per_aggregate_per_day: int
    required_capabilities: tuple[str, ...]
    aggregate_filter: dict | None
    owner: str
    enabled: bool = False
    eval_evidence_ref: str | None = None  # Task 8 gắn vào
```
Không free-form prompt template. Trigger chỉ *schedule* run theo reference (event ID + spec pin); mọi read/write sau đó vẫn qua capability + policy + connector grant + approval + audit + workspace authorization.

**`router.py` behaviour:**
1. `contracts.validate(envelope)` → 400 nếu fail.
2. Verify `workspace_id` khớp caller context → 403 nếu chéo.
3. `inbox.record(workspace_id, event_id, consumer_name, ...)` atomic. Nếu UNIQUE conflict → trả `duplicate`, **không** schedule.
4. `trigger_policy.resolve(event_type, workspace_id, aggregate)`:
   - không rule → `ignored_rule_disabled` (PB-11), metric `trigger_no_rule_total++`.
   - rule `enabled=False` → `ignored_rule_disabled`.
   - rate limit vượt → `policy_denied` reason `rate_limited`.
   - thiếu capability → `policy_denied` reason `missing_capability:<cap>`.
   - Task 8: `eval_evidence_ref` stale/thiếu với `mode!=artifact_only` → `policy_denied` reason `stale_eval_evidence`.
5. `router.schedule_reference_task(rule, envelope)` → gọi **local execution plane** client (`COSA_EXECUTION_PLANE_URL`), payload = `{workspace_id, event_id, correlation_id, agent_spec pin, aggregate_ref}`. Ghi `scheduled_task_id` vào inbox row. Trả `accepted`.

**`outbox-relay.service.ts`:** `claimDueOutboxEvents` → với mỗi row: POST tới `COSA_AGENTOS_INTAKE_URL` (local, validate loopback/local-node ở production) với chữ ký local service credential → `completeOutboxEvent` nếu 2xx + outcome ∈ {accepted, duplicate, ignored_rule_disabled}; `failOutboxEvent` nếu lỗi mạng / 5xx / `policy_denied` transient. **Chặn** nếu target URL là remote platform URL (throw at startup).

**Test cases (`test_local_event_intake.py`):**
- `accepted_event_schedules_reference_task`
- `duplicate_event_returns_duplicate_without_second_task`
- `invalid_local_signature_returns_401`
- `cross_workspace_envelope_returns_403`
- `disabled_rule_returns_ignored_rule_disabled`
- `rate_limited_aggregate_returns_policy_denied`
- `rule_missing_capability_returns_policy_denied`
- `worker_crash_after_inbox_claim_before_schedule_recovers_without_duplicate` (cross-process)
- `intake_target_must_be_local_not_remote_platform_url`

**Test cases (`outbox-relay.test.ts`):**
- `relay delivers pending rows and marks delivered`
- `relay retries on 5xx and respects backoff`
- `relay never targets a remote platform URL` (config assertion)
- `relay is bounded (does not claim more than limit per tick)`

**Steps:**
- [ ] **Step 1**: Viết test đỏ (2 danh sách trên).
- [ ] **Step 2**: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_local_event_intake.py -q && cd services/company && npx vitest run events/tests/outbox-relay.test.ts --reporter=dot` → **FAIL**.
- [ ] **Step 3**: Implement relay + intake + inbox + trigger_policy + router. Migration inbox.
- [ ] **Step 4**: Chạy lại → **PASS**. Restart relay/intake ⇒ mỗi event vẫn giao an toàn; test reject remote platform URL.

---

## Task 5 — Vận hành outbox/inbox/DLQ + correlate trace end-to-end  *(P0)*

**Files:**
- Tạo: `services/company/events/handlers/event-operations.handler.ts`, `apps/cosa/api/event_operations_routes.py`.
- Sửa: `apps/cosa/api/event_stream.py` — mở rộng `redact_ux_event_payload` thành **allowlist persistence boundary** (storage-time): trước `repository.append`, payload không thuộc `UX_EVENT_TYPES` allowlist → thay bằng `{event_ref, hash, classification}`.
- Sửa: `apps/cosa/api/routes.py` (mount).
- Tạo: `docs/operations/event-driven-agent-runtime-runbook.md`.
- Tạo test: `tests/apps/cosa/test_event_operations.py`, `services/company/events/tests/event-operations.test.ts`.
- Thêm cron: `pruneDeliveredOutbox` (PB-12).

**Operator API (workspace-scoped, `expose:true` cho operator console, auth = operator role):**
```
GET  /agent/events/outbox?workspace_id=&status=retryable|dead        → [{event_id, event_type, attempt_count, last_error, ...}]  (KHÔNG raw payload)
GET  /agent/events/inbox?workspace_id=&outcome=                       → [{event_id, outcome, scheduled_task_id, ...}]
POST /agent/events/outbox/{event_id}/retry   {workspace_id}          → reset status='pending', visibility_timeout_at=now(); audit typed
POST /agent/events/rules/{rule_id}/disable    {workspace_id}         → enabled=false; audit typed
GET  /agent/events/correlation/{correlation_id}?workspace_id=        → chain: event → inbox → scheduled_task → run → artifact refs  (KHÔNG raw tool result)
```

**Metrics (Prometheus-style names, không label chứa raw payload):**
`event_delivery_latency_seconds` (histogram, label: event_type), `event_retry_total`, `event_dlq_total`, `event_dedupe_total`, `trigger_denied_total` (label: reason), `trigger_no_rule_total`, `event_run_outcome_total` (label: event_type, outcome).

**Test cases (`test_event_operations.py`):**
- `non_member_cannot_list_dlq`
- `workspace_a_cannot_retry_workspace_b_event`
- `dlq_listing_shows_event_id_hash_failure_code_only` (không raw payload)
- `correlation_query_links_event_to_run_without_tool_result`
- `sse_persistence_replaces_non_allowlisted_payload_at_storage_time`
- `retry_and_disable_emit_typed_audit_records`

**Test cases (`event-operations.test.ts`):** `pruneDeliveredOutbox removes delivered older than 30d`; `pruneDeliveredOutbox never removes dead rows`.

**Runbook sections:** local topology diagram; "DLQ triage" (list → inspect → fix cause → retry); "Incident: relay stuck"; "Replay window & idempotency"; "Disable a runaway trigger rule"; "Workspace data export (redacted)"; link `ADR-LOCAL-EVENT-BACKBONE-001`.

**Steps:**
- [ ] **Step 1**: Viết test đỏ.
- [ ] **Step 2**: Implement operator API + storage-time allowlist + metrics + prune cron + runbook.
- [ ] **Step 3**: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_event_operations.py -q && cd services/company && npx vitest run events/tests/event-operations.test.ts --reporter=dot` → **PASS**.

---

## Task 6 — Memory & RAG là tiền đề an toàn cho event-driven knowledge refresh  *(P1)*

**Files:**
- Sửa: `packages/agent_core/memory/service.py`, `store.py` — production construction đòi `PostgresMemoryStore` + explicit lifecycle/retention policy; thiếu ⇒ fail activation. Giữ injection in-memory cho test (không production fallback).
- Sửa: `apps/cosa/knowledge_ingestion/handler.py` — gọi `assert_production_scanner_ready()` ở activation path; đòi real scanner + persistent knowledge store + object store; chỉ emit `knowledge.source.published.v1` **sau** human review/publish + persistent status update + snapshot identity confirmed.
- Sửa: `apps/cosa/api/routes.py`.
- Sửa: `packages/agent_core/knowledge/providers/postgres.py` — semantic retrieval **chỉ sau** benchmark/eval threshold; giữ lexical fallback + citations; pin source/chunk/embedding/index recipe trong `KnowledgeSnapshot`.
- Tạo test: `tests/apps/cosa/test_knowledge_production_wiring.py`, `tests/agent_core/knowledge/test_retrieval_evals.py`.

**Interfaces:**
- `MemoryService(store: MemoryStore, *, retention: RetentionPolicy)` — `store` bắt buộc ở production composition root; `RetentionPolicy` explicit (TTL, max entries/scope).
- `knowledge.source.published.v1` payload = `{sourceId, snapshotId, embeddingModel, indexRecipeVersion, reviewedBy, reviewedAt}` — reference-only, classification `internal`.
- Semantic retrieval bật qua `KnowledgeRetrievalConfig(mode="semantic", min_eval_score=...)`; nếu eval score < ngưỡng → tự fallback `lexical`, log `retrieval_fallback_total`.

**Test cases:**
- `no_feature_path_creates_default_in_memory_store_in_production`
- `fake_scanner_rejected_in_production_activation`
- `review_cannot_mark_retrieval_enabled_before_snapshot_index_eval`
- `citations_always_point_to_workspace_scoped_published_source`
- `semantic_retrieval_below_threshold_falls_back_to_lexical_with_citations`
- `knowledge_source_published_event_only_after_durable_status_and_snapshot`

**Steps:**
- [ ] **Step 1**: Viết test đỏ.
- [ ] **Step 2**: Wire production store/scanner từ composition root; semantic chỉ sau ngưỡng benchmark/eval.
- [ ] **Step 3**: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_knowledge_production_wiring.py tests/agent_core/knowledge/test_retrieval_evals.py -q` → **PASS**.

---

## Task 7 — Thay direct multi-agent fan-out bằng durable task/workflow  *(P1; BỊ CHẶN tới khi `SPEC-EXEC-PLANE-SPLIT` landed)*

**Files:**
- Sửa: `packages/agent_core/coordination/{delegate,parallel,supervisor,wait_resolver}.py`.
- Tạo: `packages/agent_core/workflows/durable_child_task.py`; sửa `workflows/engine.py`.
- Sửa: `services/cosa/storage/control-plane-schema.ts` (comment/label nhóm bảng execution scheduler = local-node), `services/cosa/services/control-plane-scheduler.service.ts` (nếu cần thêm field child-dependency).
- Tạo test: `tests/agent_core/coordination/test_durable_supervisor_workflow.py`; sửa `services/cosa/tests/control-plane-scheduler-crash-recovery.test.ts`.

**Interfaces:**
```python
@dataclass(frozen=True)
class ChildTaskSpec:
    child_id: str
    parent_run_id: str
    agent_spec: PinnedSpecIdentity
    depends_on: tuple[str, ...]           # child_id khác
    budget: Budget                        # token / time / autonomy ceiling
    join: Literal["all", "any", "quorum"]

class DurableSupervisor:
    async def spawn(self, children: list[ChildTaskSpec]) -> SupervisionHandle: ...
    async def resume(self, handle_id: str) -> SupervisionHandle: ...   # sau crash
    # child completion ghi idempotent (idempotency claim theo child_id + attempt);
    # resume/retry KHÔNG nhân đôi external side effect (Capability Gateway giữ thẩm quyền mỗi child action)
```
`asyncio.gather` coordinator hiện tại **chỉ** local pure computation; **cấm** production side-effecting delegation (raise nếu child spec có write capability). Chỉ enable **hierarchical supervisor-worker**; blackboard/market-based cố ý vắng mặt.

**Test cases:**
- `supervisor_crash_after_two_of_three_children_resumes_and_completes_remaining`
- `child_retry_with_existing_idempotency_claim_does_not_duplicate_side_effect`
- `child_awaiting_approval_blocks_join_without_busy_loop`
- `timeout_cancel_propagates_to_pending_children`
- `join_all_completes_only_after_worker_restart_reconciliation`
- (TS) `control-plane-scheduler-crash-recovery` mở rộng: `child dependency edges survive reclaim`

**Steps:**
- [ ] **Step 1**: Viết test cross-process đỏ.
- [ ] **Step 2**: Implement durable adapter (dùng lại scheduler lease/DLQ + workflow definitions), **không** engine orchestration thứ hai. Persist child identity/dependency/join state; schedule by reference.
- [ ] **Step 3**: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/coordination/test_durable_supervisor_workflow.py -q && cd services/cosa && npx vitest run tests/control-plane-scheduler-crash-recovery.test.ts --reporter=dot` → **PASS**.

---

## Task 8 — Gate event trigger/agent/policy bằng eval/promotion evidence  *(P1)*

**Files:**
- Sửa: `packages/agent_core/evals/{models,runner,promotion,promotion_gate}.py`.
- Sửa: `apps/cosa/agents/seed.py`.
- Tạo: `apps/cosa/events/trigger_promotion.py`.
- Tạo test: `tests/apps/cosa/test_event_trigger_promotion.py`, `tests/agent_core/evals/test_event_trigger_evals.py`.

**Interfaces:**
```python
class EventTriggerEvalSuite:
    event_schema_version: int
    input_fixtures: list[EventFixture]
    policy_version: str
    expected_action_boundary: Literal["artifact_only", "proposal", "write"]
    failure_injection: list[InjectionScenario]

def can_enable_trigger(rule: EventTriggerRule, evidence: PromotionEvidence) -> GateResult:
    # denied nếu: no eval / injection fail / SkillSpec hash đổi / policy hash đổi / event schema đổi / evidence stale
    # artifact_only evidence → cho enable artifact_only rule, KHÔNG write rule
    # write rule → thêm require human approval decision (services/cosa)
```
`PromotionGate` (hiện read-only) được `trigger_promotion.py` gọi làm **release gate** của `enable`; quyết định cuối vẫn ở `services/cosa` (không tự activate). Immutable evidence reference lưu `eval_evidence_ref` trên `EventTriggerRule`.

**Test cases:**
- `enable_denied_without_eval`
- `enable_denied_on_failed_injection_scenario`
- `enable_denied_on_changed_skillspec_hash`
- `enable_denied_on_changed_policy_hash`
- `enable_denied_on_changed_event_schema_version`
- `artifact_only_evidence_enables_artifact_only_rule_not_write_rule`
- `write_rule_requires_human_approval_decision`
- `stale_evidence_disables_previously_enabled_rule`

**Steps:**
- [ ] **Step 1**: Viết test đỏ.
- [ ] **Step 2**: Reuse eval/promotion primitives; nối gate vào trigger enable; lưu immutable evidence ref.
- [ ] **Step 3**: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_event_trigger_promotion.py tests/agent_core/evals/test_event_trigger_evals.py -q` → **PASS**.

---

## Task 9 — Broker evaluation gate (không phải broker-first)  *(P2)*

**Files:**
- Điền: `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` (khung tạo ở Task 0).
- Tạo: `docs/operations/event-backbone-capacity-review.md`.
- Sửa: `docs/operations/event-driven-agent-runtime-runbook.md`.
- Tạo test: `tests/architecture/test_event_backbone_adr_references.py`.

**Interfaces / nội dung:**
- Decision record 3 outcome: giữ Postgres outbox relay / thêm local optional broker profile / từ chối broker.
- Measurable inputs: p95 delivery latency, sustained outbox backlog, consumer fan-out, replay window, node resource use, operator recovery time, data-residency requirement, cost. Quarterly capacity review dùng dữ liệu production/pilot thật.
- Adoption criteria: ≥1 Postgres outbox SLO không đạt (có ghi nhận) + workload cần fan-out/replay scale độc lập + operator-approved local deploy/backup model — trước bất kỳ PoC broker. Broker candidate (nếu duyệt) deploy **per Workspace Runtime Node**, cùng envelope/inbox contract; **không bao giờ** default VPS destination.
- Migration invariant: giữ outbox envelope + inbox idempotency trong mọi migration.

**Test cases:** `capacity_review_doc_lists_all_required_metrics`; `adr_records_three_possible_outcomes`; `runbook_links_backbone_adr`; `no_broker_in_any_deployment_manifest`.

**Steps:**
- [ ] **Step 1**: Ghi measurable decision inputs + quarterly review cadence.
- [ ] **Step 2**: Document adoption criteria + migration invariants.
- [ ] **Step 3**: `PYTHONPATH=. .venv/bin/pytest tests/architecture/test_event_backbone_adr_references.py -q` → **PASS**.

---

## Trình tự release (đã resequence)

| Ưu tiên | Deliverable | Exit criteria |
|---|---|---|
| **P0 prereq** | `SPEC-EXEC-PLANE-SPLIT` (spec riêng) | `COSA_EXECUTION_PLANE_URL` + `COSA_PLATFORM_CONTROL_PLANE_URL` tách bạch; fail-fast; mọi call-site cập nhật |
| **P0** | Task 0 → Task 5 | ADR chốt; envelope + outbox + inbox qua restart; delivery local-only; operator DLQ/replay + trace chain hoạt động |
| **P1** | Task 6 → Task 8 (Task 7 sau `SPEC-EXEC-PLANE-SPLIT`) | RAG production wiring bền; supervisor-worker sống sót crash; event trigger đòi immutable eval/promotion evidence |
| **P2** | Task 9 | Quyết định broker dựa số đo capacity/SLO; không broker cài mặc định |

Task 2 & Task 3 (chỉ *thêm* contract/bảng, không đổi hành vi) được phép chạy song song lúc Task 0 (ADR) review; Task 4 trở đi cần Task 0 ACCEPTED.

---

## Definition of Done (production activation)

1. Workspace hoàn thành một task khi AgentOS *unavailable*; một durable local outbox event được giao sau khi relay recover — **at-least-once delivery + consumer idempotency ⇒ hiệu ứng đúng-một-lần** (PB-9).
2. Duplicate delivery không tạo run/side effect thứ 2. Stale worker không complete được event/task sau khi claim bị reclaim.
3. Event / artifact / knowledge source / event replay / DLQ entry của Workspace A **không** đọc/retry được bởi Workspace B.
4. Raw business payload **vắng mặt** khỏi platform telemetry, SSE persistence ngoài allowlist, logs, provider request — mặc định.
5. AgentSpec/SkillSpec/policy/event-schema drift ⇒ trigger bị disable/reject tới khi có eval/promotion evidence mới được duyệt.
6. RAG publication event chỉ fire sau durable storage + real security scan + review + snapshot identity; không expose nội dung chưa review như answer authority.
7. Supervisor crash/restart giữ nguyên child-task status + approval gate + idempotency, không replay side effect.
8. Operator inspect/retry/DLQ/disable rule local được và follow event → schedule → run → artifact theo correlation ID.
9. Capacity review phải diễn ra trước khi Kafka/Redpanda/NATS vào bất kỳ deployment manifest.

---

## Risk register

| Rủi ro | Giảm thiểu |
|---|---|
| `SPEC-EXEC-PLANE-SPLIT` chậm ⇒ chặn Task 4/7 | Task 2–3 (additive) làm trước, không phụ thuộc; Task 4 dùng feature flag `EVENT_INTAKE_ENABLED=false` mặc định tới khi split xong |
| Cutover `DomainEvent` (PB-7) sót call-site | `grep -rn "makeDomainEvent\|DomainEvent<" services/` trước xoá; TS compiler bắt phần còn lại |
| Cross-language envelope drift dù có schema | Contract test chạy ở CI cả 2 phía; fixture JSON là artifact bắt buộc trong Task 2 |
| Migration number đụng nếu nhánh khác thêm 17 song song | Executor kiểm số ngay trước khi tạo (CLAUDE.md #24 constraint); rebase nếu cần |
| `integration` schema mới cần grant/role | Migration tạo `CREATE SCHEMA IF NOT EXISTS`; kiểm Encore DB user có quyền |
| SSE storage-time allowlist làm mất event UX cần thiết | Allowlist khởi đầu = `UX_EVENT_TYPES` hiện có; chỉ *thêm* redaction cho type ngoài allowlist, không bỏ type nào |

---

## Verification (end-to-end)

**Per-task**: chạy lệnh test ghi trong mỗi task (đỏ trước implement, xanh sau).

**Regression toàn cục sau P0:**
```
cd services/company && npx vitest run --reporter=dot
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa tests/contract tests/architecture -q
make services-migrate-company
```

**Kịch bản e2e thủ công (P0 done):**
1. Dừng AgentOS. Tạo task qua Company API ⇒ task commit + đúng 1 outbox row `pending`.
2. Khởi động lại AgentOS + relay ⇒ event giao tới `/agent/internal/events`; inbox ghi 1 lần; trigger rule (nếu enabled) schedule 1 run reference-only.
3. Gửi lại cùng event (duplicate) ⇒ trả `duplicate`, không run thứ 2.
4. Từ Workspace B gọi operator retry event của Workspace A ⇒ bị từ chối (403).
5. Query `/agent/events/correlation/{cid}` ⇒ thấy event → schedule → run → artifact, không raw tool result/payload.
6. `grep -rniE 'kafka|redpanda|nats' deploy/ manifests/ docker-compose*.yml` ⇒ 0 kết quả.
7. `tests/contract/test_event_envelope_cross_language.py` xanh ⇒ TS builder ↔ Python validator đồng bộ theo `event-envelope.schema.json`.

---

## Execution handoff

Hành động đầu tiên sau khi duyệt:
1. Copy spec này → `docs/superpowers/specs/2026-08-28-event-driven-agent-operating-model-design.md`; `git add` + commit (`docs: spec local-first event-driven agent operating model`).
2. Gọi `superpowers:writing-plans` sinh implementation plan task-by-task (hoặc `superpowers:subagent-driven-development` nếu chạy luôn trong session).

Spec này **không** cho phép: deploy VPS, cài broker, cấu hình provider ngoài, xoá dữ liệu hiện có.
