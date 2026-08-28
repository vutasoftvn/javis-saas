# COSA Local-First Event-Driven Agent Operating Model — P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây business-event substrate local-first cho COSA — business fact tin cậy (transactional outbox trong cùng DB transaction) giao qua local relay tới AgentOS inbox và kích hoạt agent run theo policy, với DLQ + trace end-to-end; không rời local node, không broker.

**Architecture:** Company Services ghi domain state + envelope vào `integration.event_outbox` trong **cùng một DB transaction** (đóng cửa sổ dual-write). Một local cron relay claim row đến hạn (fencing token + visibility timeout), POST có ký tới endpoint private `POST /agent/internal/events` của `apps/cosa`. Intake validate envelope theo JSON Schema dùng chung, ghi inbox idempotent theo `(workspace_id, event_id, consumer_name)`, resolve `EventTriggerRule` chính xác (exact event type + spec pin + rate limit + required capabilities), rồi schedule một run **reference-only** qua local execution plane. Không consumer nào tin nội dung event làm thẩm quyền — mọi read/write tiếp theo vẫn qua capability + policy + approval + audit.

**Tech Stack:** TypeScript strict, Encore, Drizzle ORM, PostgreSQL 16, Vitest (integration-style, real DB). Python 3.11, FastAPI, Pydantic, pytest. JSON Schema Draft 2020-12 (`jsonschema` lib phía Python; validator tự viết phía TS).

**Spec:** `docs/superpowers/specs/2026-08-28-event-driven-agent-operating-model-design.md` (đã duyệt, commit `cb080b77`). Plan này phủ **P0**: spec Task 0 + Task 2 → Task 5. P1 (spec Task 6–8) và P2 (spec Task 9) có plan riêng sau khi P0 landed.

## Global Constraints

- **TDD bắt buộc**: viết test đỏ → chạy xác nhận đỏ → implement tối thiểu → chạy xác nhận xanh → commit. Không tuyên bố xong khi chưa chạy test (CLAUDE.md #11).
- **An toàn working tree** (CLAUDE.md #10): chạy `git status` trước thao tác có thể mất dữ liệu; không `--force` / `--no-verify` trừ khi được yêu cầu rõ; không tự xoá/archive file không liên quan.
- **Migration number**: kiểm tra số migration khả dụng *tại từng service* ngay trước khi tạo file. `services/company/operations/migrations/` hiện cao nhất = **16** ⇒ file mới `17_...`. `packages/agent_core/migrations/` hiện cao nhất ≈ **016** ⇒ file mới `017_...` (xác nhận `ls` ngay trước khi tạo). Sau khi thêm migration company: `make services-migrate-company`. Migration agent_core: `python packages/agent_core/scripts/migrate.py`.
- **Encore** (CLAUDE.md): lỗi qua `APIError` (`invalidArgument`/`unauthenticated`/`permissionDenied`/`notFound`/`internal`) — không throw `Error` trần. Endpoint nội bộ giữa service: `expose: false`. Schema Drizzle tập trung ở `services/company/shared/db/schema/` — **không** rải trong `models/`.
- **`packages/agent_core` KHÔNG import từ `apps/` hay `services/`.** Contract dùng chung đặt ở company shared layer (TS) + file JSON Schema; adapter Python nằm ở `apps/cosa/` (composition boundary).
- **Data residency**: raw business `payload` không lên VPS. Relay chỉ POST tới địa chỉ AgentOS local. Scheduler task payload chỉ chứa *reference* (`workspace_id`, `event_id`, `correlation_id`, spec pin, aggregate ref) — không nhân bản raw payload.
- **Classification trước persist**: không log/stream secret/token/raw PII/raw tool IO mặc định. Payload event từ chối key khớp `/(access_token|secret|password|api[_-]?key|authorization|private[_-]?key)/i` và payload > 16 KB.
- **Event delivery = at-least-once.** Không hứa exactly-once. Mọi consumer có inbox + idempotency key; hiệu ứng đúng-một-lần nhờ dedup, không nhờ delivery.
- **Domain event = fact đã xảy ra, past tense.** Không phát event trong read/query path.
- **Comment tiếng Việt cho phần why**; identifier/log/error/tên hằng giữ tiếng Anh.

---

## File Structure

| File | Trách nhiệm |
| --- | --- |
| `docs/architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md` | Chốt quyết định: local node giữ Postgres/scheduler/outbox; VPS chỉ identity/policy/telemetry sanitized; no-broker default. |
| `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md` | Khung decision record cho broker evaluation (số đo điền ở P2). |
| `docs/architecture/event-envelope.schema.json` | **Nguồn sự thật** cấu trúc envelope, ngôn ngữ-trung tính. TS + Python đều validate theo file này. |
| `services/company/shared/events/envelope.ts` | Types + `makeBusinessEvent()` + `validateEnvelope()` + classification/size guard. |
| `services/company/shared/events/event-types.ts` | Hằng canonical event type (past tense, có `.vN`) + type union cho payload từng loại. |
| `services/company/shared/events.ts` | Re-export contract mới; xoá `DomainEvent`/`makeDomainEvent` legacy; xoá comment `backend/agentos/...` stale. |
| `services/company/shared/events/fixtures/*.json` | Mẫu envelope export từ builder TS — input cho cross-language contract test. |
| `services/company/shared/db/schema/integration.ts` | Drizzle schema `integration.event_outbox` (Postgres schema `integration`). |
| `services/company/operations/migrations/17_local_event_outbox.up.sql` | `CREATE SCHEMA integration` + bảng `event_outbox` + index. |
| `services/company/shared/events/outbox.repository.ts` | `appendOutboxEvent(tx, e)` / `claimDueOutboxEvents` / `completeOutboxEvent` / `failOutboxEvent` / `pruneDeliveredOutbox`. |
| `services/company/operations/services/task-events.service.ts` | Build canonical envelope cho `operations.task.created.v1` / `.completed.v1`. |
| `services/company/operations/services/okr-events.service.ts` | Xoá — OKR progress không còn là producer event (là consumer concern của `task.completed`). |
| `services/company/operations/services/task.service.ts` | `appendOutboxEvent(tx, ...)` trong cùng transaction với insert/update; bỏ `taskEvents.publish`. |
| `services/company/operations/services/okr.service.ts` | Bỏ `okrEvents.publish` khỏi `getObjectiveProgressService`. |
| `services/company/events/outbox-relay.service.ts` | Claim → POST có ký tới AgentOS local → complete/fail. Bounded. Chặn target = remote platform URL. |
| `services/company/events/outbox-relay.cron.ts` | Encore CronJob đánh thức relay. |
| `services/company/events/event-operations.handler.ts` | Operator API: list retryable/DLQ, retry, disable rule, correlation chain — workspace-scoped, không raw payload. |
| `apps/cosa/events/__init__.py`, `contracts.py`, `inbox.py`, `trigger_policy.py`, `router.py` | Validate envelope, inbox idempotent, resolve trigger rule, schedule reference-only. |
| `apps/cosa/api/event_intake_routes.py` | `POST /agent/internal/events` (private, local service auth). |
| `apps/cosa/api/event_operations_routes.py` | Operator API phía cosa (inbox listing, correlation chain). |
| `apps/cosa/api/app.py` | `app.include_router(...)` cho 2 router mới. |
| `apps/cosa/composition/agent_plane.py` | Dựng `EventIntakeService` + `LocalExecutionPlaneClient` (fail-fast: execution URL ≠ platform URL, loopback/local ở production). |
| `packages/agent_core/migrations/017_event_inbox.sql` | Bảng `event_inbox` với UNIQUE `(workspace_id, event_id, consumer_name)`. |
| `apps/cosa/api/event_stream.py` | Mở rộng redaction thành allowlist **storage-time** (trước `repository.append`). |
| `docs/operations/event-driven-agent-runtime-runbook.md` | Local topology, DLQ triage, incident, replay, disable rule, redacted export. |
| `tests/architecture/test_adr_local_first_references.py` | Guard ADR tồn tại + heading + no-broker-in-manifests. |
| `tests/contract/test_event_envelope_cross_language.py` | Fixture JSON validate theo `event-envelope.schema.json`; field set khớp. |
| `services/company/**/tests/*.test.ts` | Envelope, outbox atomicity/retry/DLQ, relay, operator API. |
| `tests/apps/cosa/test_local_event_intake.py`, `test_event_operations.py` | Intake outcomes, cross-process recovery, tenancy, correlation. |

---

### Task 1: ADR local-first + no-broker guard

**Files:**
- Create: `docs/architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md`
- Create: `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md`
- Test: `tests/architecture/test_adr_local_first_references.py`

**Interfaces:**
- Consumes: nothing.
- Produces: hai file ADR với heading ổn định (`## Context`, `## Decision`, `## Data residency`, `## Execution-plane rule`, `## Event backbone`, `## Status`, `## Relates`) mà mọi task sau tham chiếu bằng tên file.

- [ ] **Step 1: Viết test guard**

Create `tests/architecture/test_adr_local_first_references.py`:

```python
"""Guard: quyết định kiến trúc local-first phải tồn tại bằng văn bản và
không có broker nào lọt vào deployment manifest trước capacity review."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADR = REPO / "docs/architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md"
BACKBONE_ADR = REPO / "docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md"

REQUIRED_HEADINGS = [
    "## Context",
    "## Decision",
    "## Data residency",
    "## Execution-plane rule",
    "## Event backbone",
    "## Status",
    "## Relates",
]


def test_adr_local_first_file_exists() -> None:
    assert ADR.is_file(), f"missing {ADR.relative_to(REPO)}"


def test_adr_local_first_has_required_headings() -> None:
    text = ADR.read_text(encoding="utf-8")
    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    assert not missing, f"ADR missing headings: {missing}"


def test_backbone_adr_stub_exists() -> None:
    assert BACKBONE_ADR.is_file()
    assert "## Decision inputs" in BACKBONE_ADR.read_text(encoding="utf-8")


def test_no_broker_in_deployment_manifests() -> None:
    globs = ["deploy/**/*.y*ml", "docker-compose*.y*ml", "**/k8s/**/*.y*ml", "infra/**/*.y*ml"]
    hits: list[str] = []
    pattern = re.compile(r"\b(kafka|redpanda|nats)\b", re.IGNORECASE)
    for g in globs:
        for path in REPO.glob(g):
            if "node_modules" in path.parts:
                continue
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(path.relative_to(REPO)))
    assert not hits, f"broker reference in deployment manifest(s): {hits}"
```

- [ ] **Step 2: Chạy test — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/architecture/test_adr_local_first_references.py -q`
Expected: FAIL — `missing docs/architecture/adr/ADR-LOCAL-FIRST-001-...md`.

- [ ] **Step 3: Viết ADR-LOCAL-FIRST-001**

Create the file with exactly these sections (nội dung tiếng Việt cho phần why; giữ nguyên các cụm khoá tiếng Anh):

- `# ADR-LOCAL-FIRST-001: Workspace Runtime Node data residency & execution-plane boundary`
- `## Status` — `ACCEPTED 2026-08-28`. Ghi rõ: ACCEPTED ≠ IMPLEMENTED ≠ WIRED ≠ VERIFIED ≠ PRODUCTION.
- `## Context` — 4 vùng kiến trúc CLAUDE.md; code hiện chỉ có một `COSA_CONTROL_PLANE_URL` (`apps/cosa/composition/agent_plane.py:273-275`) dùng chung cho scheduler + lease + knowledge + connector; hai tài liệu nguồn CLAUDE.md nêu (`COSA_FINAL_INTEGRATION_...`, `BLUEPRINT_V2_RECONCILED_...`) không còn trong repo; `docs/architecture/adr/` rỗng trước ADR này.
- `## Decision` — Workspace Runtime Node local chứa: Company Services (business truth), AgentOS, Agent Core Postgres, local execution scheduler, transactional outbox/inbox, evidence/artifact/knowledge. VPS Platform Control Plane chỉ giữ: platform identity/license, policy/entitlement đã lọc, registry/promotion metadata, telemetry tổng hợp đã sanitize.
- `## Data residency` — bảng (Class | Local node | VPS allowed | Example): business fact payload = Yes / No by default; run/checkpoint/tool result = Yes / No by default; RAG source/chunk/embedding = Yes / No by default; incident evidence = Local / explicit redacted export only; skill/agent/policy identity = cached/pinned / Yes; event envelope metadata = Yes / only aggregate-sanitized.
- `## Execution-plane rule` — `apps/cosa` không bao giờ silently fallback từ local execution URL sang remote platform URL. Scheduler task payload lưu reference (`workspace_id`, event ID, artifact/ref IDs, exact spec pins), không nhân bản raw business payload. Biến tách bạch: `COSA_EXECUTION_PLANE_URL` (local scheduler/lease) vs `COSA_PLATFORM_CONTROL_PLANE_URL` (identity/license/connector). Rename toàn diện thuộc `SPEC-EXEC-PLANE-SPLIT`.
- `## Event backbone` — PostgreSQL transactional outbox relay là backbone P0/P1. Kafka/Redpanda/NATS không phải dependency mặc định; chỉ đánh giá lại qua `ADR-LOCAL-EVENT-BACKBONE-001` khi số đo vận hành chứng minh Postgres relay không đáp ứng.
- `## Relates` — bổ sung deployment profile local cho `ADR-CONTROLPLANE-001` (control-plane primitives tại `services/cosa` — vẫn đúng). Không supersede ADR nào.

- [ ] **Step 4: Viết ADR-LOCAL-EVENT-BACKBONE-001 (khung)**

Create with: `# ADR-LOCAL-EVENT-BACKBONE-001: Event backbone capacity gate`, `## Status` = `PROPOSED — awaiting P2 capacity data`, `## Decision inputs` (bullet list placeholder: p95 delivery latency, sustained outbox backlog, consumer fan-out, replay window, node resource use, operator recovery time, data-residency requirement, cost), `## Candidate outcomes` (keep Postgres outbox relay / add local optional broker profile per Workspace Runtime Node / reject broker), `## Migration invariants` (giữ outbox envelope + inbox idempotency qua mọi migration). Ghi: số đo thật điền ở P2 (spec Task 9).

- [ ] **Step 5: Chạy test — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/architecture/test_adr_local_first_references.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add docs/architecture/adr/ADR-LOCAL-FIRST-001-workspace-runtime-node-data-residency.md \
        docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md \
        tests/architecture/test_adr_local_first_references.py
git commit -m "docs(adr): local-first data residency & execution-plane boundary"
```

---

### Task 2: Canonical business-event envelope + producer semantics

**Files:**
- Create: `docs/architecture/event-envelope.schema.json`
- Create: `services/company/shared/events/event-types.ts`
- Create: `services/company/shared/events/envelope.ts`
- Create: `services/company/shared/events/fixtures/operations.task.created.v1.json`
- Create: `services/company/shared/events/fixtures/operations.task.completed.v1.json`
- Modify: `services/company/shared/events.ts`
- Modify: `services/company/operations/services/task-events.service.ts`
- Delete: `services/company/operations/services/okr-events.service.ts`
- Modify: `services/company/operations/services/okr.service.ts:192-207`
- Modify: `services/company/shared/tests/events.test.ts`
- Modify: `services/company/operations/tests/task.test.ts`
- Modify: `services/company/operations/tests/okr.test.ts` (nếu có test cho progress event; nếu không, thêm)
- Create: `tests/contract/test_event_envelope_cross_language.py`

**Interfaces:**
- Consumes: nothing from Task 1 (chỉ tham chiếu ADR trong doc).
- Produces:
  - `event-envelope.schema.json` — JSON Schema Draft 2020-12, `$id: https://cosa.local/schemas/business-event-envelope/v1`.
  - `CURRENT_SCHEMA_VERSION: number` (= 1), `MAX_PAYLOAD_BYTES: number` (= 16384).
  - `interface BusinessEventEnvelope<TPayload extends Record<string, unknown>>` — fields: `eventId` string, `eventType` string, `schemaVersion` number, `occurredAt` string, `workspaceId` string, `aggregateType` string, `aggregateId` string, `correlationId` string, `causationId?` string, `actor {kind:"user"|"agent"|"system"; id:string}`, `producer {service:string; version:string}`, `classification "internal"|"confidential"|"restricted"`, `payload TPayload`.
  - `interface BusinessEventInput<T>` — caller cung cấp `eventType, workspaceId, aggregateType, aggregateId, correlationId, causationId?, actor, classification, payload`.
  - `function makeBusinessEvent<T>(input: BusinessEventInput<T>): BusinessEventEnvelope<T>` — sinh `eventId` (uuid v4), `occurredAt` (now ISO UTC), `schemaVersion` (= CURRENT_SCHEMA_VERSION), `producer` (từ hằng module); gọi `validateEnvelope` trước khi trả.
  - `function validateEnvelope(e: unknown): asserts e is BusinessEventEnvelope<Record<string, unknown>>` — throw `APIError.invalidArgument` khi: thiếu field bắt buộc; `eventType` không khớp `^[a-z]+\.[a-z_]+\.[a-z_]+\.v[0-9]+$`; `JSON.stringify(payload)` byte length > `MAX_PAYLOAD_BYTES`; key bất kỳ trong payload (đệ quy) khớp `FORBIDDEN_PAYLOAD_KEYS`; `classification === "restricted"` mà payload có field không thuộc allowlist reference keys (`id`, `ref`, `hash`, `count`, `*_id`, `*_ref`).
  - `event-types.ts`: `OPERATIONS_TASK_CREATED_V1 = "operations.task.created.v1"`, `OPERATIONS_TASK_COMPLETED_V1 = "operations.task.completed.v1"`; `interface TaskCreatedPayloadV1 { taskId: string; workspaceId: string; title: string; status: string }`; `interface TaskCompletedPayloadV1 { taskId: string; workspaceId: string; completedAt: string }`.
- Later tasks rely on: `makeBusinessEvent`, `validateEnvelope`, `BusinessEventEnvelope`, the two `OPERATIONS_TASK_*` constants, and both payload interfaces.

- [ ] **Step 1: Viết `event-envelope.schema.json`**

Create `docs/architecture/event-envelope.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://cosa.local/schemas/business-event-envelope/v1",
  "title": "BusinessEventEnvelope",
  "type": "object",
  "required": ["eventId", "eventType", "schemaVersion", "occurredAt", "workspaceId",
               "aggregateType", "aggregateId", "correlationId", "actor", "producer",
               "classification", "payload"],
  "additionalProperties": false,
  "properties": {
    "eventId":       { "type": "string", "format": "uuid" },
    "eventType":     { "type": "string", "pattern": "^[a-z]+\\.[a-z_]+\\.[a-z_]+\\.v[0-9]+$" },
    "schemaVersion": { "type": "integer", "minimum": 1 },
    "occurredAt":    { "type": "string", "format": "date-time" },
    "workspaceId":   { "type": "string", "minLength": 1 },
    "aggregateType": { "type": "string", "minLength": 1 },
    "aggregateId":   { "type": "string", "minLength": 1 },
    "correlationId": { "type": "string", "minLength": 1 },
    "causationId":   { "type": "string", "minLength": 1 },
    "actor": {
      "type": "object", "required": ["kind", "id"], "additionalProperties": false,
      "properties": {
        "kind": { "enum": ["user", "agent", "system"] },
        "id":   { "type": "string", "minLength": 1 }
      }
    },
    "producer": {
      "type": "object", "required": ["service", "version"], "additionalProperties": false,
      "properties": {
        "service": { "type": "string", "minLength": 1 },
        "version": { "type": "string", "minLength": 1 }
      }
    },
    "classification": { "enum": ["internal", "confidential", "restricted"] },
    "payload": { "type": "object" }
  }
}
```

- [ ] **Step 2: Viết test đỏ cho envelope (TS)**

Replace `services/company/shared/tests/events.test.ts` với:

```ts
import { describe, expect, it } from "vitest";
import {
  makeBusinessEvent,
  validateEnvelope,
  CURRENT_SCHEMA_VERSION,
  MAX_PAYLOAD_BYTES,
} from "../events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../events/event-types";

const baseInput = {
  eventType: OPERATIONS_TASK_CREATED_V1,
  workspaceId: "ws_1",
  aggregateType: "task",
  aggregateId: "t_1",
  correlationId: "corr_1",
  actor: { kind: "user" as const, id: "u_1" },
  classification: "internal" as const,
  payload: { taskId: "t_1", workspaceId: "ws_1", title: "x", status: "todo" },
};

describe("makeBusinessEvent", () => {
  it("stamps a uuid eventId, ISO occurredAt, schemaVersion and producer", () => {
    const e = makeBusinessEvent(baseInput);
    expect(e.eventId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(() => new Date(e.occurredAt).toISOString()).not.toThrow();
    expect(e.schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
    expect(e.producer.service).toBe("company.operations");
    expect(e.producer.version).toBeTruthy();
  });

  it("preserves caller identity fields", () => {
    const e = makeBusinessEvent({ ...baseInput, causationId: "cause_1" });
    expect(e).toMatchObject({
      eventType: OPERATIONS_TASK_CREATED_V1,
      workspaceId: "ws_1",
      aggregateId: "t_1",
      correlationId: "corr_1",
      causationId: "cause_1",
      actor: { kind: "user", id: "u_1" },
    });
  });
});

describe("validateEnvelope", () => {
  it("rejects a non-past-tense / unversioned eventType", () => {
    expect(() => validateEnvelope({ ...makeBusinessEvent(baseInput), eventType: "task.list" }))
      .toThrow(/eventType/i);
  });

  it("rejects a payload containing a credential-shaped key", () => {
    expect(() =>
      makeBusinessEvent({ ...baseInput, payload: { taskId: "t_1", access_token: "abc" } as any })
    ).toThrow(/forbidden|credential|payload/i);
  });

  it("rejects an oversized payload", () => {
    const big = { taskId: "t_1", blob: "z".repeat(MAX_PAYLOAD_BYTES + 1) };
    expect(() => makeBusinessEvent({ ...baseInput, payload: big as any })).toThrow(/size|large|bytes/i);
  });

  it("rejects a restricted envelope whose payload is not reference-only", () => {
    expect(() =>
      makeBusinessEvent({
        ...baseInput,
        classification: "restricted",
        payload: { taskId: "t_1", customerName: "Jane Doe" } as any,
      })
    ).toThrow(/restricted|reference/i);
  });

  it("accepts a restricted envelope with reference-only payload", () => {
    const e = makeBusinessEvent({
      ...baseInput,
      classification: "restricted",
      payload: { taskId: "t_1", snapshot_ref: "snap_9" },
    });
    expect(e.classification).toBe("restricted");
  });
});
```

- [ ] **Step 3: Chạy test — xác nhận đỏ**

Run: `cd services/company && npx vitest run shared/tests/events.test.ts --reporter=dot`
Expected: FAIL — `Cannot find module '../events/envelope'`.

- [ ] **Step 4: Viết `event-types.ts`**

Create `services/company/shared/events/event-types.ts`:

```ts
// Canonical business-event types — past tense, "domain.entity.action.vN".
// Xem docs/architecture/adr/ADR-LOCAL-FIRST-001-...md + event-envelope.schema.json.
export const OPERATIONS_TASK_CREATED_V1 = "operations.task.created.v1";
export const OPERATIONS_TASK_COMPLETED_V1 = "operations.task.completed.v1";

export type CanonicalEventType =
  | typeof OPERATIONS_TASK_CREATED_V1
  | typeof OPERATIONS_TASK_COMPLETED_V1;

// Payload chỉ chứa IDs + changed state; consumer re-read chi tiết qua capability.
export interface TaskCreatedPayloadV1 {
  taskId: string;
  workspaceId: string;
  title: string;
  status: string;
}

export interface TaskCompletedPayloadV1 {
  taskId: string;
  workspaceId: string;
  completedAt: string;
}
```

- [ ] **Step 5: Viết `envelope.ts`**

Create `services/company/shared/events/envelope.ts`:

```ts
import { randomUUID } from "node:crypto";
import { APIError } from "encore.dev/api";

export const CURRENT_SCHEMA_VERSION = 1;
export const MAX_PAYLOAD_BYTES = 16 * 1024;

const PRODUCER_SERVICE = "company.operations";
const PRODUCER_VERSION = process.env.COMPANY_SERVICE_VERSION || "0.0.0-dev";

const EVENT_TYPE_RE = /^[a-z]+\.[a-z_]+\.[a-z_]+\.v[0-9]+$/;
const FORBIDDEN_PAYLOAD_KEYS = /(access_token|secret|password|api[_-]?key|authorization|private[_-]?key)/i;
const RESTRICTED_REFERENCE_KEY_RE = /^([a-z][a-z0-9]*_)?(id|ref|hash|count)$|_(id|ref)$/i;

export interface BusinessEventEnvelope<TPayload extends Record<string, unknown>> {
  eventId: string;
  eventType: string;
  schemaVersion: number;
  occurredAt: string;
  workspaceId: string;
  aggregateType: string;
  aggregateId: string;
  correlationId: string;
  causationId?: string;
  actor: { kind: "user" | "agent" | "system"; id: string };
  producer: { service: string; version: string };
  classification: "internal" | "confidential" | "restricted";
  payload: TPayload;
}

export interface BusinessEventInput<T extends Record<string, unknown>> {
  eventType: string;
  workspaceId: string;
  aggregateType: string;
  aggregateId: string;
  correlationId: string;
  causationId?: string;
  actor: BusinessEventEnvelope<T>["actor"];
  classification: BusinessEventEnvelope<T>["classification"];
  payload: T;
}

function assertNoForbiddenKeys(value: unknown, path = "payload"): void {
  if (value === null || typeof value !== "object") return;
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (FORBIDDEN_PAYLOAD_KEYS.test(k)) {
      throw APIError.invalidArgument(`forbidden credential-shaped key in ${path}.${k}`);
    }
    assertNoForbiddenKeys(v, `${path}.${k}`);
  }
}

export function validateEnvelope(
  e: unknown
): asserts e is BusinessEventEnvelope<Record<string, unknown>> {
  const env = e as Partial<BusinessEventEnvelope<Record<string, unknown>>>;
  const required = [
    "eventId", "eventType", "schemaVersion", "occurredAt", "workspaceId",
    "aggregateType", "aggregateId", "correlationId", "actor", "producer",
    "classification", "payload",
  ] as const;
  for (const field of required) {
    if (env[field] === undefined || env[field] === null) {
      throw APIError.invalidArgument(`business event missing field: ${field}`);
    }
  }
  if (!EVENT_TYPE_RE.test(env.eventType as string)) {
    throw APIError.invalidArgument(`eventType must match ${EVENT_TYPE_RE} (past tense, versioned)`);
  }
  if (typeof env.schemaVersion !== "number" || env.schemaVersion < 1) {
    throw APIError.invalidArgument("schemaVersion must be a positive integer");
  }
  if (Number.isNaN(new Date(env.occurredAt as string).getTime())) {
    throw APIError.invalidArgument("occurredAt must be an ISO-8601 timestamp");
  }
  const payload = env.payload as Record<string, unknown>;
  if (Buffer.byteLength(JSON.stringify(payload), "utf8") > MAX_PAYLOAD_BYTES) {
    throw APIError.invalidArgument(`payload exceeds ${MAX_PAYLOAD_BYTES} bytes`);
  }
  assertNoForbiddenKeys(payload);
  if (env.classification === "restricted") {
    const offending = Object.keys(payload).filter((k) => !RESTRICTED_REFERENCE_KEY_RE.test(k));
    if (offending.length > 0) {
      throw APIError.invalidArgument(
        `restricted classification requires reference-only payload; offending keys: ${offending.join(", ")}`
      );
    }
  }
}

export function makeBusinessEvent<T extends Record<string, unknown>>(
  input: BusinessEventInput<T>
): BusinessEventEnvelope<T> {
  const envelope: BusinessEventEnvelope<T> = {
    eventId: randomUUID(),
    eventType: input.eventType,
    schemaVersion: CURRENT_SCHEMA_VERSION,
    occurredAt: new Date().toISOString(),
    workspaceId: input.workspaceId,
    aggregateType: input.aggregateType,
    aggregateId: input.aggregateId,
    correlationId: input.correlationId,
    ...(input.causationId ? { causationId: input.causationId } : {}),
    actor: input.actor,
    producer: { service: PRODUCER_SERVICE, version: PRODUCER_VERSION },
    classification: input.classification,
    payload: input.payload,
  };
  validateEnvelope(envelope);
  return envelope;
}
```

- [ ] **Step 6: Chạy test envelope — xác nhận xanh**

Run: `cd services/company && npx vitest run shared/tests/events.test.ts --reporter=dot`
Expected: PASS.

- [ ] **Step 7: Commit envelope contract**

```bash
git add docs/architecture/event-envelope.schema.json \
        services/company/shared/events/event-types.ts \
        services/company/shared/events/envelope.ts \
        services/company/shared/tests/events.test.ts
git commit -m "feat(events): canonical business-event envelope + validation"
```

- [ ] **Step 8: Viết cross-language contract test đỏ + fixtures**

Create `services/company/shared/events/fixtures/operations.task.created.v1.json` bằng cách thêm một script test tạm — hoặc viết fixture thủ công khớp `makeBusinessEvent` output. Fixture ví dụ (`operations.task.created.v1.json`):

```json
{
  "eventId": "3f1c8a2e-9b4d-4e7a-8c21-0a5b6d7e8f90",
  "eventType": "operations.task.created.v1",
  "schemaVersion": 1,
  "occurredAt": "2026-08-28T10:00:00.000Z",
  "workspaceId": "ws_1",
  "aggregateType": "task",
  "aggregateId": "t_1",
  "correlationId": "corr_1",
  "actor": { "kind": "user", "id": "u_1" },
  "producer": { "service": "company.operations", "version": "0.0.0-dev" },
  "classification": "internal",
  "payload": { "taskId": "t_1", "workspaceId": "ws_1", "title": "Write plan", "status": "todo" }
}
```

Create `operations.task.completed.v1.json` tương tự (payload `{ "taskId": "t_1", "workspaceId": "ws_1", "completedAt": "2026-08-28T11:00:00.000Z" }`).

Create `tests/contract/test_event_envelope_cross_language.py`:

```python
"""Contract: mọi fixture envelope do phía TS sinh phải validate được theo
docs/architecture/event-envelope.schema.json — nguồn sự thật dùng chung."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((REPO / "docs/architecture/event-envelope.schema.json").read_text("utf-8"))
FIXTURES = sorted((REPO / "services/company/shared/events/fixtures").glob("*.json"))

REQUIRED = set(SCHEMA["required"])
ALLOWED = set(SCHEMA["properties"].keys())


def test_fixtures_present() -> None:
    assert FIXTURES, "no envelope fixtures found"


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_fixture_matches_shared_schema(path: Path) -> None:
    doc = json.loads(path.read_text("utf-8"))
    Draft202012Validator(SCHEMA).validate(doc)
    keys = set(doc.keys())
    assert REQUIRED <= keys, f"{path.name} missing {REQUIRED - keys}"
    assert keys <= ALLOWED, f"{path.name} has undeclared keys {keys - ALLOWED}"
    assert path.stem == doc["eventType"], "fixture filename must equal its eventType"
```

- [ ] **Step 9: Chạy — xác nhận xanh** (schema + fixtures đã có)

Run: `PYTHONPATH=. .venv/bin/pytest tests/contract/test_event_envelope_cross_language.py -q`
Expected: PASS. Nếu `jsonschema` chưa cài: `.venv/bin/pip install jsonschema` rồi thêm vào `requirements-dev`/`pyproject` dev deps trong cùng commit.

- [ ] **Step 10: Viết test đỏ cho producer + read-path**

Trong `services/company/operations/tests/task.test.ts`, thay 3 test event cũ (`publishes task.created ...`, `does not re-publish ...`, `transitions ... publishes on done`) bằng phiên bản kiểm envelope canonical. Ví dụ test `task.created`:

```ts
it("appends one canonical operations.task.created.v1 outbox event on genuine insert", async () => {
  const { workspaceId, authorization } = await makeAuthedWorkspace("Created Event Test Inc");
  const task = await createTask({ workspaceId, title: "Notify on create", authorization });

  const rows = await readOutbox(workspaceId, "task", task.id); // helper Task 3 cung cấp; ở Task 2 stub tạm
  expect(rows).toHaveLength(1);
  expect(rows[0].eventType).toBe("operations.task.created.v1");
  expect(rows[0].envelope).toMatchObject({
    schemaVersion: 1,
    workspaceId,
    aggregateId: task.id,
    payload: { taskId: task.id, workspaceId, title: "Notify on create", status: "todo" },
  });
  expect(rows[0].envelope.eventId).toMatch(/^[0-9a-f-]{36}$/);
  expect(rows[0].envelope.correlationId).toBeTruthy();
});
```

Trong `services/company/operations/tests/okr.test.ts` thêm:

```ts
it("getObjectiveProgress is a pure read — emits zero events", async () => {
  const { workspaceId, authorization } = await makeAuthedWorkspace("OKR Read Purity Inc");
  // ... tạo objective + key result qua handlers hiện có ...
  const before = await countOutbox(workspaceId);      // helper Task 3
  await getObjectiveProgress({ objectiveId, authorization });
  const after = await countOutbox(workspaceId);
  expect(after).toBe(before);
});
```

> **Lưu ý thứ tự:** Step 10–12 phụ thuộc outbox helper của Task 3. Nếu thực thi tuần tự, hoãn Step 10–12 và chạy chúng như bước đầu của Task 3. Nếu chạy song song, Task 2 chỉ commit tới Step 9; producer rewrite gộp vào Task 3.

- [ ] **Step 11: Chuyển producer sang builder canonical + xoá read-path publish**

- `task-events.service.ts`: thay `makeDomainEvent` bằng `makeBusinessEvent`. `buildTaskCreatedEvent(task, ctx)` trả `BusinessEventEnvelope<TaskCreatedPayloadV1>` với `eventType: OPERATIONS_TASK_CREATED_V1`, `aggregateType: "task"`, `aggregateId: task.id`, `correlationId` lấy từ request context (tham số mới; nếu chưa có, sinh `randomUUID()` và ghi log 1 dòng cảnh báo thiếu correlation), `actor` từ caller, `classification: "internal"`, payload `{ taskId, workspaceId, title, status }`.
- `okr.service.ts:205`: **xoá** dòng `await okrEvents.publish(buildOkrProgressUpdatedEvent(objectiveId, score));` và import liên quan.
- Xoá file `okr-events.service.ts`. `grep -rn "okrEvents\|okr-events\|buildOkrProgressUpdatedEvent" services/company` → dọn sạch tham chiếu (test, handler).
- `shared/events.ts`: xoá `DomainEvent`, `makeDomainEvent`, comment `backend/agentos/...`. Giữ lại hằng string strategy-domain (`EXPERIMENT_CREATED`, `EVIDENCE_RECORDED`, `GATE_EVALUATED`, `DECISION_RECORDED`) nhưng thêm `/** @deprecated chưa có producer/consumer canonical — không dùng cho BusinessEventEnvelope */`. Re-export `./events/envelope` và `./events/event-types`.
- `grep -rn "makeDomainEvent\|DomainEvent<" services/company --include='*.ts'` → 0 kết quả ngoài node_modules.

- [ ] **Step 12: Chạy vitest company + contract — xác nhận xanh**

Run: `cd services/company && npx vitest run shared/tests/events.test.ts operations/tests/task.test.ts operations/tests/okr.test.ts --reporter=dot`
Run: `PYTHONPATH=. .venv/bin/pytest tests/contract/test_event_envelope_cross_language.py -q`
Expected: PASS cả hai. (task/okr test cần outbox helper Task 3 — xem lưu ý Step 10.)

- [ ] **Step 13: Commit**

```bash
git add services/company/shared/events.ts services/company/shared/events/ \
        services/company/operations/services/task-events.service.ts \
        services/company/operations/services/okr.service.ts \
        services/company/operations/tests/ tests/contract/
git rm services/company/operations/services/okr-events.service.ts
git commit -m "feat(events): move producers to canonical envelope; drop read-path publish"
```

---

### Task 3: Transactional local outbox — đóng cửa sổ dual-write

**Files:**
- Create: `services/company/operations/migrations/17_local_event_outbox.up.sql` (xác nhận số 17 bằng `ls services/company/operations/migrations/` ngay trước)
- Create: `services/company/shared/db/schema/integration.ts`
- Modify: `services/company/shared/db/schema/index.ts` (export `integration`)
- Modify: `services/company/operations/db.ts` (thêm `integrationSchema` vào `schema` object)
- Create: `services/company/shared/events/outbox.repository.ts`
- Modify: `services/company/operations/services/task.service.ts`
- Modify: `services/company/operations/services/task-events.service.ts` (builder nhận `tx` không cần thiết — builder thuần; service gọi `appendOutboxEvent(tx, envelope)`)
- Create: `services/company/operations/tests/event-outbox.test.ts`
- Create: `services/company/operations/tests/helpers/outbox.ts` (test helper `readOutbox`, `countOutbox`)

**Interfaces:**
- Consumes: `makeBusinessEvent`, `BusinessEventEnvelope`, `OPERATIONS_TASK_CREATED_V1`, `OPERATIONS_TASK_COMPLETED_V1`, `TaskCreatedPayloadV1`, `TaskCompletedPayloadV1` (Task 2).
- Produces:
  - Postgres table `integration.event_outbox` (cột dưới Step 1).
  - `async function appendOutboxEvent(tx: NodePgTransaction, e: BusinessEventEnvelope<Record<string, unknown>>): Promise<void>` — `INSERT ... ON CONFLICT (event_id) DO NOTHING`.
  - `async function claimDueOutboxEvents(workerId: string, limit: number): Promise<OutboxRow[]>`.
  - `async function completeOutboxEvent(eventId: string, claimToken: string): Promise<boolean>`.
  - `async function failOutboxEvent(eventId: string, claimToken: string, error: string): Promise<void>`.
  - `async function pruneDeliveredOutbox(olderThanDays: number): Promise<number>`.
  - `interface OutboxRow { eventId: string; workspaceId: string; aggregateType: string; aggregateId: string; eventType: string; schemaVersion: number; occurredAt: string; envelope: BusinessEventEnvelope<Record<string, unknown>>; classification: string; status: "pending"|"claimed"|"delivered"|"dead"; attemptCount: number; maxAttempts: number; claimToken: string | null; visibilityTimeoutAt: string | null; lastError: string | null; deadLetterReason: string | null }`.
  - Test helpers: `readOutbox(workspaceId, aggregateType, aggregateId): Promise<OutboxRow[]>`, `countOutbox(workspaceId): Promise<number>`.
- Later tasks rely on: `claimDueOutboxEvents`, `completeOutboxEvent`, `failOutboxEvent`, `OutboxRow` (Task 4 relay); operator listing reads the same table (Task 5).

- [ ] **Step 1: Viết migration**

Confirm number: `ls services/company/operations/migrations/`. Create `17_local_event_outbox.up.sql`:

```sql
-- Transactional outbox local — business fact được ghi CÙNG transaction với domain
-- state (đóng cửa sổ dual-write). Relay local claim theo fencing token + visibility
-- timeout; không có row nào rời Workspace Runtime Node (ADR-LOCAL-FIRST-001).
CREATE SCHEMA IF NOT EXISTS integration;

CREATE TABLE integration.event_outbox (
  id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id              UUID        NOT NULL UNIQUE,
  workspace_id          TEXT        NOT NULL,
  aggregate_type        TEXT        NOT NULL,
  aggregate_id          TEXT        NOT NULL,
  event_type            TEXT        NOT NULL,
  schema_version        INTEGER     NOT NULL,
  occurred_at           TIMESTAMPTZ NOT NULL,
  envelope              JSONB       NOT NULL,
  payload_hash          TEXT        NOT NULL,
  classification        TEXT        NOT NULL,
  status                TEXT        NOT NULL DEFAULT 'pending'
                          CHECK (status IN ('pending','claimed','delivered','dead')),
  attempt_count         INTEGER     NOT NULL DEFAULT 0,
  max_attempts          INTEGER     NOT NULL DEFAULT 8,
  claim_token           TEXT,
  visibility_timeout_at TIMESTAMPTZ,
  last_error            TEXT,
  dead_letter_reason    TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  delivered_at          TIMESTAMPTZ
);

CREATE INDEX idx_event_outbox_due
  ON integration.event_outbox (visibility_timeout_at)
  WHERE status IN ('pending','claimed');
CREATE INDEX idx_event_outbox_ws_aggr
  ON integration.event_outbox (workspace_id, aggregate_type, aggregate_id);
CREATE INDEX idx_event_outbox_type
  ON integration.event_outbox (event_type);
```

- [ ] **Step 2: Viết Drizzle schema**

Create `services/company/shared/db/schema/integration.ts`:

```ts
import { pgSchema, bigint, text, integer, timestamp, jsonb, uniqueIndex, index } from "drizzle-orm/pg-core";

export const integrationSchema = pgSchema("integration");

export const eventOutbox = integrationSchema.table("event_outbox", {
  id: bigint("id", { mode: "bigint" }).primaryKey().generatedAlwaysAsIdentity(),
  eventId: text("event_id").notNull(),
  workspaceId: text("workspace_id").notNull(),
  aggregateType: text("aggregate_type").notNull(),
  aggregateId: text("aggregate_id").notNull(),
  eventType: text("event_type").notNull(),
  schemaVersion: integer("schema_version").notNull(),
  occurredAt: timestamp("occurred_at", { withTimezone: true }).notNull(),
  envelope: jsonb("envelope").notNull(),
  payloadHash: text("payload_hash").notNull(),
  classification: text("classification").notNull(),
  status: text("status").notNull().default("pending"),
  attemptCount: integer("attempt_count").notNull().default(0),
  maxAttempts: integer("max_attempts").notNull().default(8),
  claimToken: text("claim_token"),
  visibilityTimeoutAt: timestamp("visibility_timeout_at", { withTimezone: true }),
  lastError: text("last_error"),
  deadLetterReason: text("dead_letter_reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
  deliveredAt: timestamp("delivered_at", { withTimezone: true }),
}, (t) => ({
  eventIdUq: uniqueIndex("event_outbox_event_id_uq").on(t.eventId),
  wsAggrIdx: index("event_outbox_ws_aggr_idx").on(t.workspaceId, t.aggregateType, t.aggregateId),
}));
```

Add `export * from "./integration";` to `services/company/shared/db/schema/index.ts`. Add `import * as integrationSchema from "../shared/db/schema/integration";` and spread `...integrationSchema` into the `schema` object in `services/company/operations/db.ts`.

- [ ] **Step 3: Viết test đỏ — atomicity, retry, DLQ, fencing**

Create `services/company/operations/tests/event-outbox.test.ts`. Test cases (mỗi `it` một hành vi):

```ts
import { describe, expect, it } from "vitest";
import { db } from "../db";
import {
  appendOutboxEvent, claimDueOutboxEvents, completeOutboxEvent, failOutboxEvent,
} from "../../shared/events/outbox.repository";
import { makeBusinessEvent } from "../../shared/events/envelope";
import { OPERATIONS_TASK_CREATED_V1 } from "../../shared/events/event-types";
import { createTask } from "../handlers/task.handler";
import { makeAuthedWorkspace } from "../tests/helpers/workspace"; // trích từ task.test.ts nếu chưa dùng chung
import { readOutbox } from "./helpers/outbox";

function evt(workspaceId: string, aggregateId: string) {
  return makeBusinessEvent({
    eventType: OPERATIONS_TASK_CREATED_V1, workspaceId,
    aggregateType: "task", aggregateId, correlationId: "corr_x",
    actor: { kind: "system", id: "test" }, classification: "internal",
    payload: { taskId: aggregateId, workspaceId, title: "x", status: "todo" },
  });
}

describe("event outbox", () => {
  it("rolls back the event when the domain transaction fails", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox Rollback Inc");
    await expect(db.transaction(async (tx) => {
      await appendOutboxEvent(tx, evt(workspaceId, "t_rollback"));
      throw new Error("boom"); // buộc rollback
    })).rejects.toThrow("boom");
    expect(await readOutbox(workspaceId, "task", "t_rollback")).toHaveLength(0);
  });

  it("writes exactly one outbox row on a successful task insert", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Outbox One Row Inc");
    const task = await createTask({ workspaceId, title: "Ship", authorization });
    expect(await readOutbox(workspaceId, "task", task.id)).toHaveLength(1);
  });

  it("leaves a retryable pending row when relay fails", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox Retry Inc");
    await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, "t_retry")));
    const [claimed] = await claimDueOutboxEvents("worker-a", 10);
    await failOutboxEvent(claimed.eventId, claimed.claimToken!, "connection refused");
    const [row] = await readOutbox(workspaceId, "task", "t_retry");
    expect(row.status).toBe("pending");
    expect(row.attemptCount).toBe(1);
    expect(row.lastError).toMatch(/connection refused/);
  });

  it("dead-letters after max attempts", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox DLQ Inc");
    await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, "t_dlq")));
    for (let i = 0; i < 8; i++) {
      const [c] = await claimDueOutboxEvents("worker-a", 10);
      await failOutboxEvent(c.eventId, c.claimToken!, `fail ${i}`);
    }
    const [row] = await readOutbox(workspaceId, "task", "t_dlq");
    expect(row.status).toBe("dead");
    expect(row.deadLetterReason).toBeTruthy();
  });

  it("rejects completion with a stale claim token", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox Fencing Inc");
    await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, "t_fence")));
    const [first] = await claimDueOutboxEvents("worker-a", 10);
    // visibility hết hạn → worker khác claim lại
    await db.execute(
      `UPDATE integration.event_outbox SET visibility_timeout_at = now() - interval '1 minute'
       WHERE event_id = '${first.eventId}'`
    );
    const [second] = await claimDueOutboxEvents("worker-b", 10);
    expect(second.eventId).toBe(first.eventId);
    expect(await completeOutboxEvent(first.eventId, first.claimToken!)).toBe(false);
    expect(await completeOutboxEvent(second.eventId, second.claimToken!)).toBe(true);
  });

  it("gives two concurrent claimers disjoint rows (SKIP LOCKED)", async () => {
    const { workspaceId } = await makeAuthedWorkspace("Outbox SkipLocked Inc");
    for (let i = 0; i < 6; i++) {
      await db.transaction((tx) => appendOutboxEvent(tx, evt(workspaceId, `t_sl_${i}`)));
    }
    const [a, b] = await Promise.all([
      claimDueOutboxEvents("worker-a", 3),
      claimDueOutboxEvents("worker-b", 3),
    ]);
    const ids = new Set([...a, ...b].map((r) => r.eventId));
    expect(ids.size).toBe(a.length + b.length);
  });
});
```

Also create `services/company/operations/tests/helpers/outbox.ts`:

```ts
import { eq, and, sql } from "drizzle-orm";
import { db } from "../../db";
import { eventOutbox } from "../../../shared/db/schema/integration";
import type { OutboxRow } from "../../../shared/events/outbox.repository";

export async function readOutbox(
  workspaceId: string, aggregateType: string, aggregateId: string
): Promise<OutboxRow[]> {
  const rows = await db.select().from(eventOutbox).where(and(
    eq(eventOutbox.workspaceId, workspaceId),
    eq(eventOutbox.aggregateType, aggregateType),
    eq(eventOutbox.aggregateId, aggregateId),
  ));
  return rows.map(mapRow);
}

export async function countOutbox(workspaceId: string): Promise<number> {
  const [{ n }] = await db.select({ n: sql<number>`count(*)::int` })
    .from(eventOutbox).where(eq(eventOutbox.workspaceId, workspaceId));
  return n;
}

function mapRow(r: typeof eventOutbox.$inferSelect): OutboxRow {
  return {
    eventId: r.eventId, workspaceId: r.workspaceId, aggregateType: r.aggregateType,
    aggregateId: r.aggregateId, eventType: r.eventType, schemaVersion: r.schemaVersion,
    occurredAt: r.occurredAt.toISOString(), envelope: r.envelope as any,
    classification: r.classification, status: r.status as OutboxRow["status"],
    attemptCount: r.attemptCount, maxAttempts: r.maxAttempts, claimToken: r.claimToken,
    visibilityTimeoutAt: r.visibilityTimeoutAt ? r.visibilityTimeoutAt.toISOString() : null,
    lastError: r.lastError, deadLetterReason: r.deadLetterReason,
  };
}
```

- [ ] **Step 4: Chạy test — xác nhận đỏ**

Run: `cd services/company && npx vitest run operations/tests/event-outbox.test.ts --reporter=dot`
Expected: FAIL — `Cannot find module '../../shared/events/outbox.repository'`.

- [ ] **Step 5: Viết `outbox.repository.ts`**

Create `services/company/shared/events/outbox.repository.ts`. Core logic:

```ts
import { createHash, randomUUID } from "node:crypto";
import { and, eq, inArray, lt, or, sql } from "drizzle-orm";
import { db } from "../../operations/db";
import { eventOutbox } from "../db/schema/integration";
import type { BusinessEventEnvelope } from "./envelope";

const VISIBILITY_SECONDS = 120;
const BACKOFF_BASE_SECONDS = 5;
const BACKOFF_CAP_SECONDS = 300;

export interface OutboxRow { /* như Interfaces block */ }

type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

export async function appendOutboxEvent(
  tx: Tx, e: BusinessEventEnvelope<Record<string, unknown>>
): Promise<void> {
  const payloadHash = createHash("sha256")
    .update(JSON.stringify(e.payload)).digest("hex");
  await tx.insert(eventOutbox).values({
    eventId: e.eventId, workspaceId: e.workspaceId,
    aggregateType: e.aggregateType, aggregateId: e.aggregateId,
    eventType: e.eventType, schemaVersion: e.schemaVersion,
    occurredAt: new Date(e.occurredAt), envelope: e, payloadHash,
    classification: e.classification,
  }).onConflictDoNothing({ target: eventOutbox.eventId });
}

export async function claimDueOutboxEvents(workerId: string, limit: number): Promise<OutboxRow[]> {
  const token = `${workerId}:${randomUUID().slice(0, 12)}`;
  const rows = await db.execute(sql`
    UPDATE integration.event_outbox SET
      status = 'claimed',
      claim_token = ${token},
      attempt_count = attempt_count + 1,
      visibility_timeout_at = now() + (${VISIBILITY_SECONDS} || ' seconds')::interval
    WHERE id IN (
      SELECT id FROM integration.event_outbox
      WHERE status = 'pending'
         OR (status = 'claimed' AND visibility_timeout_at < now())
      ORDER BY occurred_at
      FOR UPDATE SKIP LOCKED
      LIMIT ${limit}
    )
    RETURNING *;
  `);
  return (rows.rows as any[]).map(mapDbRow);
}

export async function completeOutboxEvent(eventId: string, claimToken: string): Promise<boolean> {
  const res = await db.execute(sql`
    UPDATE integration.event_outbox
    SET status = 'delivered', delivered_at = now()
    WHERE event_id = ${eventId} AND claim_token = ${claimToken} AND status = 'claimed'
    RETURNING id;
  `);
  return (res.rows as any[]).length === 1;
}

export async function failOutboxEvent(eventId: string, claimToken: string, error: string): Promise<void> {
  await db.execute(sql`
    UPDATE integration.event_outbox
    SET status = CASE WHEN attempt_count >= max_attempts THEN 'dead' ELSE 'pending' END,
        dead_letter_reason = CASE WHEN attempt_count >= max_attempts THEN ${error} ELSE dead_letter_reason END,
        last_error = ${error},
        claim_token = NULL,
        visibility_timeout_at = now() + (LEAST(${BACKOFF_CAP_SECONDS},
          ${BACKOFF_BASE_SECONDS} * power(2, GREATEST(attempt_count - 1, 0))) || ' seconds')::interval
    WHERE event_id = ${eventId} AND claim_token = ${claimToken};
  `);
}

export async function pruneDeliveredOutbox(olderThanDays: number): Promise<number> {
  const res = await db.execute(sql`
    DELETE FROM integration.event_outbox
    WHERE status = 'delivered' AND delivered_at < now() - (${olderThanDays} || ' days')::interval
    RETURNING id;
  `);
  return (res.rows as any[]).length;
}

function mapDbRow(r: any): OutboxRow { /* snake_case → camelCase, envelope as-is */ }
```

- [ ] **Step 6: Chạy migration + test — xác nhận xanh**

Run: `make services-migrate-company`
Run: `cd services/company && npx vitest run operations/tests/event-outbox.test.ts --reporter=dot`
Expected: PASS (6 passed).

- [ ] **Step 7: Nối producer vào cùng transaction**

Rewrite `createTaskService` (`task.service.ts:109-131`) và `updateTaskStatusService` (`:164-189`) để bọc insert/update + `appendOutboxEvent` trong một `db.transaction`:

```ts
const task = await db.transaction(async (tx) => {
  const [row] = await tx.insert(tasks).values({ /* như cũ */ }).returning();
  if (!row) throw APIError.internal("failed to create task");
  const t = toTask(row);
  await appendOutboxEvent(tx, buildTaskCreatedEvent(t, { correlationId, actor }));
  return t;
});
return task;
```

`buildTaskCreatedEvent(task, ctx)` giờ trả `BusinessEventEnvelope<TaskCreatedPayloadV1>` (Task 2 Step 11). Xoá `await taskEvents.publish(...)` và `const { taskEvents } = ...` khỏi `task.service.ts`. Xoá `Topic` `taskEvents` trong `task-events.service.ts` (không còn dùng — relay đọc từ bảng).

`correlationId`/`actor`: lấy từ tham số service (thêm vào `CreateTaskParams`/`updateTaskStatusService` signature qua một `ctx` object). Handler truyền xuống từ request. Nếu handler chưa có correlation, sinh `randomUUID()` + `log.warn("missing correlation id on task create")`.

- [ ] **Step 8: Chạy vitest operations đầy đủ — xác nhận xanh**

Run: `cd services/company && npx vitest run operations/tests/ shared/tests/events.test.ts --reporter=dot`
Expected: PASS. Sửa mọi test còn spy `taskEvents.publish` → assert qua `readOutbox`.

- [ ] **Step 9: Commit**

```bash
git add services/company/operations/migrations/17_local_event_outbox.up.sql \
        services/company/shared/db/schema/ services/company/operations/db.ts \
        services/company/shared/events/outbox.repository.ts \
        services/company/operations/services/task.service.ts \
        services/company/operations/services/task-events.service.ts \
        services/company/operations/tests/
git commit -m "feat(events): transactional outbox; producers append in-tx"
```

---

### Task 4: Local relay + AgentOS inbox + policy-controlled trigger

**Files:**
- Create: `services/company/events/encore.service.ts` (khai báo Encore service `events`)
- Create: `services/company/events/outbox-relay.service.ts`
- Create: `services/company/events/outbox-relay.cron.ts`
- Create: `services/company/events/tests/outbox-relay.test.ts`
- Create: `packages/agent_core/migrations/017_event_inbox.sql` (xác nhận số bằng `ls packages/agent_core/migrations/`)
- Create: `apps/cosa/events/__init__.py`, `contracts.py`, `inbox.py`, `trigger_policy.py`, `router.py`
- Create: `apps/cosa/api/event_intake_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Create: `tests/apps/cosa/test_local_event_intake.py`

**Interfaces:**
- Consumes: `claimDueOutboxEvents`, `completeOutboxEvent`, `failOutboxEvent`, `OutboxRow` (Task 3); `event-envelope.schema.json` (Task 2).
- Produces:
  - Endpoint `POST /agent/internal/events` — body = `BusinessEventEnvelope`; header `X-COSA-Local-Signature`. Response 200 `{ outcome: "accepted", scheduledTaskId }` | `{ outcome: "duplicate" }` | `{ outcome: "ignored_rule_disabled" }` | `{ outcome: "policy_denied", reason }`. 400 invalidArgument (envelope invalid). 401 unauthenticated (bad signature). 403 permissionDenied (cross-workspace).
  - Postgres table `event_inbox` — UNIQUE `(workspace_id, event_id, consumer_name)`.
  - Python: `contracts.validate_envelope(dict) -> Envelope` (pydantic model mirroring schema); `inbox.record(conn, workspace_id, event_id, consumer_name, ...) -> Literal["recorded","duplicate"]`; `trigger_policy.resolve(workspace_id, event_type, aggregate) -> TriggerDecision`; `router.handle_event(envelope, signature) -> IntakeOutcome`.
  - `LocalExecutionPlaneClient.schedule_reference_task(rule, envelope) -> str` (returns scheduled task id) — base URL từ `COSA_EXECUTION_PLANE_URL`.
- Later tasks rely on: `event_inbox` table + `router.handle_event` outcomes (Task 5 operator + correlation).

- [ ] **Step 1: Viết migration inbox**

Confirm number: `ls packages/agent_core/migrations/`. Create `017_event_inbox.sql`:

```sql
-- AgentOS inbox: idempotency theo (workspace_id, event_id, consumer_name).
-- At-least-once delivery từ relay → duplicate POST không tạo run thứ hai.
CREATE TABLE IF NOT EXISTS event_inbox (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  workspace_id      TEXT        NOT NULL,
  event_id          UUID        NOT NULL,
  consumer_name     TEXT        NOT NULL,
  event_type        TEXT        NOT NULL,
  correlation_id    TEXT        NOT NULL,
  received_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  outcome           TEXT        NOT NULL,
  scheduled_task_id TEXT,
  UNIQUE (workspace_id, event_id, consumer_name)
);
CREATE INDEX IF NOT EXISTS idx_event_inbox_correlation ON event_inbox (workspace_id, correlation_id);
```

Apply: `python packages/agent_core/scripts/migrate.py` (hoặc lệnh tương đương trong Makefile — kiểm `grep -n migrate Makefile`).

- [ ] **Step 2: Viết test đỏ — intake outcomes (Python)**

Create `tests/apps/cosa/test_local_event_intake.py`. Dùng `create_cosa_app(plane=...)` với plane inject (theo `tests/apps/cosa/test_event_stream.py` + `conftest.py`). Test cases:

```python
import uuid
import pytest

CONSUMER = "agentos.event_intake"

def _env(workspace_id="ws_1", event_type="operations.task.created.v1", aggregate_id="t_1"):
    return {
        "eventId": str(uuid.uuid4()), "eventType": event_type, "schemaVersion": 1,
        "occurredAt": "2026-08-28T10:00:00.000Z", "workspaceId": workspace_id,
        "aggregateType": "task", "aggregateId": aggregate_id, "correlationId": "corr_1",
        "actor": {"kind": "system", "id": "relay"},
        "producer": {"service": "company.operations", "version": "1.0.0"},
        "classification": "internal",
        "payload": {"taskId": aggregate_id, "workspaceId": workspace_id, "title": "x", "status": "todo"},
    }

async def test_accepted_event_schedules_reference_task(intake_client, enabled_rule):
    r = await intake_client.post("/agent/internal/events", json=_env(), headers=_sig())
    assert r.status_code == 200 and r.json()["outcome"] == "accepted"
    assert r.json()["scheduledTaskId"]

async def test_duplicate_event_returns_duplicate_without_second_task(intake_client, enabled_rule):
    env = _env()
    first = await intake_client.post("/agent/internal/events", json=env, headers=_sig())
    second = await intake_client.post("/agent/internal/events", json=env, headers=_sig())
    assert first.json()["outcome"] == "accepted"
    assert second.json()["outcome"] == "duplicate"
    assert scheduled_task_count() == 1

async def test_invalid_local_signature_returns_401(intake_client):
    r = await intake_client.post("/agent/internal/events", json=_env(), headers={"X-COSA-Local-Signature": "bad"})
    assert r.status_code == 401

async def test_cross_workspace_envelope_returns_403(intake_client_ws1):
    r = await intake_client_ws1.post("/agent/internal/events", json=_env(workspace_id="ws_2"), headers=_sig())
    assert r.status_code == 403

async def test_disabled_rule_returns_ignored(intake_client, disabled_rule):
    r = await intake_client.post("/agent/internal/events", json=_env(), headers=_sig())
    assert r.json()["outcome"] == "ignored_rule_disabled"
    assert scheduled_task_count() == 0

async def test_no_rule_returns_ignored(intake_client):
    r = await intake_client.post("/agent/internal/events", json=_env(event_type="operations.task.overdue.v1"), headers=_sig())
    assert r.json()["outcome"] == "ignored_rule_disabled"

async def test_rate_limited_aggregate_returns_policy_denied(intake_client, enabled_rule_limit_1):
    await intake_client.post("/agent/internal/events", json=_env(aggregate_id="t_rl"), headers=_sig())
    r = await intake_client.post("/agent/internal/events", json=_env(aggregate_id="t_rl"), headers=_sig())
    assert r.json()["outcome"] == "policy_denied" and r.json()["reason"] == "rate_limited"

async def test_rule_missing_capability_returns_policy_denied(intake_client, rule_requiring_absent_cap):
    r = await intake_client.post("/agent/internal/events", json=_env(), headers=_sig())
    assert r.json()["outcome"] == "policy_denied"
    assert r.json()["reason"].startswith("missing_capability:")

async def test_invalid_envelope_returns_400(intake_client):
    bad = _env(); del bad["correlationId"]
    r = await intake_client.post("/agent/internal/events", json=bad, headers=_sig())
    assert r.status_code == 400

async def test_worker_crash_after_inbox_before_schedule_recovers_without_duplicate(intake_client, enabled_rule, crash_after_inbox):
    env = _env()
    with pytest.raises(SimulatedCrash):
        await intake_client.post("/agent/internal/events", json=env, headers=_sig())
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig())  # relay retries
    assert r.json()["outcome"] in ("accepted", "duplicate")
    assert scheduled_task_count() == 1

async def test_intake_target_must_be_local_not_remote_platform_url(monkeypatch):
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://platform.cosa.example.com")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.cosa.example.com")
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="execution plane URL"):
        build_cosa_agent_plane()
```

Fixtures (`intake_client`, `enabled_rule`, `_sig`, `scheduled_task_count`, `crash_after_inbox`) trong file test hoặc `conftest.py` — dùng plane inject + in-memory scheduler stub (đã có mẫu ở `tests/apps/cosa/`).

- [ ] **Step 3: Chạy — xác nhận đỏ**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_local_event_intake.py -q`
Expected: FAIL — route `/agent/internal/events` không tồn tại (404) / import error.

- [ ] **Step 4: Viết `contracts.py`**

Create `apps/cosa/events/contracts.py` — pydantic model khớp `event-envelope.schema.json`, cộng validate bổ sung (event type regex, payload size, forbidden keys). Load schema JSON để cross-check ở test (`tests/contract/`), runtime dùng pydantic:

```python
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, field_validator

_EVENT_TYPE_RE = re.compile(r"^[a-z]+\.[a-z_]+\.[a-z_]+\.v[0-9]+$")
_FORBIDDEN = re.compile(r"(access_token|secret|password|api[_-]?key|authorization|private[_-]?key)", re.I)
MAX_PAYLOAD_BYTES = 16 * 1024

class Actor(BaseModel):
    kind: Literal["user", "agent", "system"]
    id: str = Field(min_length=1)

class Producer(BaseModel):
    service: str = Field(min_length=1)
    version: str = Field(min_length=1)

class Envelope(BaseModel):
    model_config = {"extra": "forbid"}
    eventId: str
    eventType: str
    schemaVersion: int = Field(ge=1)
    occurredAt: str
    workspaceId: str = Field(min_length=1)
    aggregateType: str = Field(min_length=1)
    aggregateId: str = Field(min_length=1)
    correlationId: str = Field(min_length=1)
    causationId: str | None = None
    actor: Actor
    producer: Producer
    classification: Literal["internal", "confidential", "restricted"]
    payload: dict

    @field_validator("eventType")
    @classmethod
    def _type(cls, v: str) -> str:
        if not _EVENT_TYPE_RE.match(v):
            raise ValueError("eventType must be past-tense, versioned")
        return v

    @field_validator("payload")
    @classmethod
    def _payload(cls, v: dict) -> dict:
        if len(json.dumps(v).encode()) > MAX_PAYLOAD_BYTES:
            raise ValueError("payload too large")
        def scan(o):
            if isinstance(o, dict):
                for k, sub in o.items():
                    if _FORBIDDEN.search(k):
                        raise ValueError(f"forbidden key: {k}")
                    scan(sub)
        scan(v)
        return v

def validate_envelope(raw: dict) -> Envelope:
    return Envelope.model_validate(raw)
```

- [ ] **Step 5: Viết `inbox.py`, `trigger_policy.py`, `router.py`**

`inbox.py` — `async def record(conn, *, workspace_id, event_id, consumer_name, event_type, correlation_id, outcome, scheduled_task_id=None) -> Literal["recorded", "duplicate"]`: `INSERT ... ON CONFLICT (workspace_id, event_id, consumer_name) DO NOTHING RETURNING id`; nếu 0 rows → `"duplicate"`.

`trigger_policy.py`:

```python
@dataclass(frozen=True)
class EventTriggerRule:
    rule_id: str
    workspace_id: str
    event_type: str
    agent_spec: PinnedSpecIdentity   # id + version + definition_hash
    mode: Literal["artifact_only", "proposal", "write"]
    max_runs_per_aggregate_per_day: int
    required_capabilities: tuple[str, ...]
    aggregate_filter: dict | None
    owner: str
    enabled: bool = False

@dataclass(frozen=True)
class TriggerDecision:
    outcome: Literal["accepted", "ignored_rule_disabled", "policy_denied"]
    rule: EventTriggerRule | None = None
    reason: str | None = None

async def resolve(store, capabilities, run_counter, *, workspace_id, event_type, aggregate) -> TriggerDecision:
    rule = await store.find(workspace_id, event_type, aggregate)
    if rule is None or not rule.enabled:
        return TriggerDecision("ignored_rule_disabled")
    if await run_counter.today(workspace_id, rule.rule_id, aggregate["id"]) >= rule.max_runs_per_aggregate_per_day:
        return TriggerDecision("policy_denied", reason="rate_limited")
    missing = [c for c in rule.required_capabilities if not capabilities.has(workspace_id, c)]
    if missing:
        return TriggerDecision("policy_denied", reason=f"missing_capability:{missing[0]}")
    return TriggerDecision("accepted", rule=rule)
```

`router.py` — `handle_event`:

```python
async def handle_event(deps, raw_body: dict, signature: str) -> IntakeResult:
    if not deps.local_auth.verify(signature, raw_body):
        raise Unauthenticated()
    env = validate_envelope(raw_body)                 # → 400 nếu ValueError
    if env.workspaceId != deps.caller_workspace_id:
        raise PermissionDenied()
    async with deps.db.begin() as conn:
        state = await inbox.record(conn, workspace_id=env.workspaceId, event_id=env.eventId,
                                   consumer_name=CONSUMER, event_type=env.eventType,
                                   correlation_id=env.correlationId, outcome="pending")
        if state == "duplicate":
            return IntakeResult(outcome="duplicate")
        decision = await deps.trigger_policy.resolve(
            workspace_id=env.workspaceId, event_type=env.eventType,
            aggregate={"type": env.aggregateType, "id": env.aggregateId})
        if decision.outcome != "accepted":
            await inbox.set_outcome(conn, env.workspaceId, env.eventId, CONSUMER, decision.outcome)
            return IntakeResult(outcome=decision.outcome, reason=decision.reason)
        task_id = await deps.execution_plane.schedule_reference_task(decision.rule, env)
        await inbox.set_outcome(conn, env.workspaceId, env.eventId, CONSUMER, "accepted", task_id)
    return IntakeResult(outcome="accepted", scheduled_task_id=task_id)
```

`schedule_reference_task` payload = `{"workspace_id", "event_id", "correlation_id", "agent_spec": {...pin}, "aggregate_ref": {"type","id"}, "mode"}` — **không** raw `payload`.

- [ ] **Step 6: Viết `event_intake_routes.py` + wire vào app + composition**

`apps/cosa/api/event_intake_routes.py`:

```python
from fastapi import APIRouter, Header, Request
from apps.cosa.events.router import handle_event, Unauthenticated, PermissionDenied
from fastapi import HTTPException

def create_event_intake_router() -> APIRouter:
    router = APIRouter(prefix="/agent/internal", tags=["event-intake"])

    @router.post("/events")
    async def intake(request: Request, x_cosa_local_signature: str = Header(default="")):
        deps = request.app.state.plane.event_intake_deps
        body = await request.json()
        try:
            result = await handle_event(deps, body, x_cosa_local_signature)
        except Unauthenticated:
            raise HTTPException(status_code=401, detail="invalid local signature")
        except PermissionDenied:
            raise HTTPException(status_code=403, detail="cross-workspace envelope")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return result.model_dump(exclude_none=True)

    return router
```

`app.py`: `from apps.cosa.api.event_intake_routes import create_event_intake_router` → `app.include_router(create_event_intake_router())`.

`agent_plane.py` (sau block dựng scheduler, `:266-275`): dựng `event_intake_deps` (db pool, local_auth, trigger_policy store, execution_plane client). Add fail-fast:

```python
execution_url = os.environ.get("COSA_EXECUTION_PLANE_URL", "http://127.0.0.1:4001")
platform_url = os.environ.get("COSA_PLATFORM_CONTROL_PLANE_URL",
                              os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001"))
env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
if env_name in ("production", "staging", "prod"):
    if execution_url == platform_url:
        raise RuntimeError(
            "execution plane URL must not equal the platform control-plane URL "
            "(ADR-LOCAL-FIRST-001 §Execution-plane rule)")
    host = urlparse(execution_url).hostname or ""
    if host not in ("127.0.0.1", "localhost", "::1") and not host.endswith(".local"):
        raise RuntimeError(f"execution plane URL must be local for a Workspace Runtime Node, got {host}")
```

> Rename toàn diện `COSA_CONTROL_PLANE_URL` → 2 biến ở mọi call-site thuộc `SPEC-EXEC-PLANE-SPLIT`. Ở đây chỉ giới thiệu `COSA_EXECUTION_PLANE_URL` cho đường intake→scheduler, giữ P0 self-contained.

- [ ] **Step 7: Chạy test intake — xác nhận xanh**

Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_local_event_intake.py -q`
Expected: PASS.

- [ ] **Step 8: Viết test đỏ — relay (TS)**

Create `services/company/events/tests/outbox-relay.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { runRelayOnce } from "../outbox-relay.service";
import { db } from "../../operations/db";
import { appendOutboxEvent } from "../../shared/events/outbox.repository";
// ... helpers evt(), readOutbox() ...

describe("outbox relay", () => {
  it("delivers pending rows and marks them delivered", async () => {
    const post = vi.fn().mockResolvedValue({ status: 200, body: { outcome: "accepted" } });
    await db.transaction((tx) => appendOutboxEvent(tx, evt("ws_r", "t_r1")));
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });
    expect(post).toHaveBeenCalledTimes(1);
    const [row] = await readOutbox("ws_r", "task", "t_r1");
    expect(row.status).toBe("delivered");
  });

  it("retries on 5xx and respects the batch limit", async () => {
    const post = vi.fn().mockResolvedValue({ status: 503, body: {} });
    for (let i = 0; i < 20; i++) await db.transaction((tx) => appendOutboxEvent(tx, evt("ws_r", `t_r${i}`)));
    await runRelayOnce({ post, batchLimit: 5, agentOsUrl: "http://127.0.0.1:8081" });
    expect(post).toHaveBeenCalledTimes(5);
  });

  it("refuses to start when the target is a remote platform URL", () => {
    expect(() => assertLocalTarget("https://platform.cosa.example.com")).toThrow(/local/i);
    expect(() => assertLocalTarget("http://127.0.0.1:8081")).not.toThrow();
  });

  it("treats duplicate/ignored outcomes as success (no infinite retry)", async () => {
    const post = vi.fn().mockResolvedValue({ status: 200, body: { outcome: "duplicate" } });
    await db.transaction((tx) => appendOutboxEvent(tx, evt("ws_r", "t_dup")));
    await runRelayOnce({ post, batchLimit: 10, agentOsUrl: "http://127.0.0.1:8081" });
    const [row] = await readOutbox("ws_r", "task", "t_dup");
    expect(row.status).toBe("delivered");
  });
});
```

- [ ] **Step 9: Chạy — xác nhận đỏ**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts --reporter=dot`
Expected: FAIL — `Cannot find module '../outbox-relay.service'`.

- [ ] **Step 10: Viết relay service + cron + Encore service**

`services/company/events/encore.service.ts`: `import { Service } from "encore.dev/service"; export default new Service("events");`

`outbox-relay.service.ts`:

```ts
import { createHmac } from "node:crypto";
import { claimDueOutboxEvents, completeOutboxEvent, failOutboxEvent } from "../shared/events/outbox.repository";

const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "::1"]);

export function assertLocalTarget(url: string): void {
  const host = new URL(url).hostname;
  if (!LOCAL_HOSTS.has(host) && !host.endsWith(".local")) {
    throw new Error(`relay target must be local (Workspace Runtime Node), got ${host}`);
  }
}

interface RelayDeps {
  post: (url: string, body: unknown, headers: Record<string, string>) => Promise<{ status: number; body: any }>;
  batchLimit: number;
  agentOsUrl: string;
}

export async function runRelayOnce(deps: RelayDeps): Promise<void> {
  assertLocalTarget(deps.agentOsUrl);
  const rows = await claimDueOutboxEvents("company-relay", deps.batchLimit);
  const secret = process.env.COSA_LOCAL_SERVICE_SECRET || "dev-secret";
  for (const row of rows) {
    const payload = JSON.stringify(row.envelope);
    const sig = createHmac("sha256", secret).update(payload).digest("hex");
    try {
      const res = await deps.post(`${deps.agentOsUrl}/agent/internal/events`, row.envelope,
        { "X-COSA-Local-Signature": sig, "Content-Type": "application/json" });
      const outcome = res.body?.outcome;
      if (res.status === 200 && ["accepted", "duplicate", "ignored_rule_disabled"].includes(outcome)) {
        await completeOutboxEvent(row.eventId, row.claimToken!);
      } else if (res.status === 200 && outcome === "policy_denied") {
        await completeOutboxEvent(row.eventId, row.claimToken!); // terminal — không retry vô hạn
      } else {
        await failOutboxEvent(row.eventId, row.claimToken!, `status=${res.status} body=${JSON.stringify(res.body)}`);
      }
    } catch (e) {
      await failOutboxEvent(row.eventId, row.claimToken!, String(e));
    }
  }
}

export async function relayTick(): Promise<void> {
  await runRelayOnce({
    post: async (url, body, headers) => {
      const r = await fetch(url, { method: "POST", body: JSON.stringify(body), headers });
      return { status: r.status, body: await r.json().catch(() => ({})) };
    },
    batchLimit: Number(process.env.COSA_RELAY_BATCH_LIMIT || 50),
    agentOsUrl: process.env.COSA_AGENTOS_INTAKE_URL || "http://127.0.0.1:8081",
  });
}
```

`outbox-relay.cron.ts`:

```ts
import { CronJob } from "encore.dev/cron";
import { api } from "encore.dev/api";
import { relayTick } from "./outbox-relay.service";

export const relayTickEndpoint = api({ method: "POST", expose: false, path: "/events/relay/tick" },
  async (): Promise<void> => { await relayTick(); });

const _ = new CronJob("outbox-relay", {
  title: "Local outbox relay tick",
  every: "1m",
  endpoint: relayTickEndpoint,
});
```

- [ ] **Step 11: Chạy relay test — xác nhận xanh**

Run: `cd services/company && npx vitest run events/tests/outbox-relay.test.ts --reporter=dot`
Expected: PASS (4 passed).

- [ ] **Step 12: Chạy regression P0 hai phía**

Run: `cd services/company && npx vitest run --reporter=dot`
Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_local_event_intake.py tests/contract tests/architecture -q`
Expected: PASS.

- [ ] **Step 13: Commit**

```bash
git add services/company/events/ packages/agent_core/migrations/017_event_inbox.sql \
        apps/cosa/events/ apps/cosa/api/event_intake_routes.py apps/cosa/api/app.py \
        apps/cosa/composition/agent_plane.py tests/apps/cosa/test_local_event_intake.py
git commit -m "feat(events): local relay + AgentOS inbox + policy-gated trigger"
```

---

### Task 5: Operate outbox/inbox/DLQ + end-to-end correlation

**Files:**
- Create: `services/company/events/handlers/event-operations.handler.ts`
- Create: `services/company/events/event-operations.api.ts` (Encore endpoints, `expose: true`, operator-auth)
- Create: `services/company/events/tests/event-operations.test.ts`
- Create: `services/company/events/outbox-prune.cron.ts`
- Create: `apps/cosa/api/event_operations_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/api/event_stream.py`
- Create: `tests/apps/cosa/test_event_operations.py`
- Create: `docs/operations/event-driven-agent-runtime-runbook.md`

**Interfaces:**
- Consumes: `integration.event_outbox` + `pruneDeliveredOutbox` (Task 3); `event_inbox` (Task 4).
- Produces:
  - `GET /events/outbox?workspaceId=&status=retryable|dead` → `{ items: OutboxSummary[] }` where `OutboxSummary = { eventId, eventType, aggregateType, aggregateId, status, attemptCount, lastError, deadLetterReason, occurredAt }` — **no `envelope`/`payload`**.
  - `POST /events/outbox/:eventId/retry` `{ workspaceId }` → `{ status: "requeued" }`; typed audit record.
  - `POST /events/rules/:ruleId/disable` `{ workspaceId }` → `{ status: "disabled" }`; typed audit record.
  - `GET /agent/events/correlation/:correlationId?workspaceId=` (cosa side) → `{ chain: [{ kind: "event"|"inbox"|"scheduled_task"|"run"|"artifact", id, at, ...refs }] }` — no raw tool result / payload.
  - `event_stream.py`: `persist_ux_event(record)` replaces non-allowlisted `payload` with `{ event_ref, hash, classification }` **before** `repository.append`.
- Later tasks: none in P0 (P1/P2 build on runbook + metrics names).

- [ ] **Step 1: Viết test đỏ — authorization + no-leak (TS)**

Create `services/company/events/tests/event-operations.test.ts`:

```ts
describe("event operations API", () => {
  it("hides DLQ from a non-member of the workspace", async () => {
    const a = await makeAuthedWorkspace("Ops A"); const b = await makeAuthedWorkspace("Ops B");
    await seedDeadLetter(a.workspaceId, "t_x");
    await expect(listOutbox({ workspaceId: a.workspaceId, status: "dead", authorization: b.authorization }))
      .rejects.toThrow(/not found|forbidden/i);
  });

  it("does not let workspace B retry a workspace A event", async () => {
    const a = await makeAuthedWorkspace("Ops A2"); const b = await makeAuthedWorkspace("Ops B2");
    const { eventId } = await seedDeadLetter(a.workspaceId, "t_y");
    await expect(retryOutbox({ eventId, workspaceId: b.workspaceId, authorization: b.authorization }))
      .rejects.toThrow(/not found|forbidden/i);
  });

  it("summarises a dead-letter row without envelope or payload", async () => {
    const a = await makeAuthedWorkspace("Ops A3");
    const { eventId } = await seedDeadLetter(a.workspaceId, "t_z");
    const { items } = await listOutbox({ workspaceId: a.workspaceId, status: "dead", authorization: a.authorization });
    const row = items.find((i) => i.eventId === eventId)!;
    expect(row).not.toHaveProperty("envelope");
    expect(row).not.toHaveProperty("payload");
    expect(row.deadLetterReason).toBeTruthy();
  });

  it("requeues a dead-letter event and writes a typed audit record", async () => {
    const a = await makeAuthedWorkspace("Ops A4");
    const { eventId } = await seedDeadLetter(a.workspaceId, "t_w");
    await retryOutbox({ eventId, workspaceId: a.workspaceId, authorization: a.authorization });
    const [row] = await readOutboxByEventId(eventId);
    expect(row.status).toBe("pending");
    expect(await lastAudit(a.workspaceId, "event.outbox.retry")).toMatchObject({ eventId });
  });

  it("prune removes delivered rows older than 30d, never dead rows", async () => {
    const a = await makeAuthedWorkspace("Ops A5");
    await seedDelivered(a.workspaceId, "t_old", { ageDays: 40 });
    await seedDeadLetter(a.workspaceId, "t_keep");
    const removed = await pruneDeliveredOutbox(30);
    expect(removed).toBeGreaterThanOrEqual(1);
    expect((await readOutbox(a.workspaceId, "task", "t_keep"))[0].status).toBe("dead");
  });
});
```

- [ ] **Step 2: Viết test đỏ — correlation + SSE storage-time (Python)**

Create `tests/apps/cosa/test_event_operations.py`:

```python
async def test_correlation_chain_links_event_to_run_without_tool_result(ops_client, seeded_chain):
    r = await ops_client.get(f"/agent/events/correlation/{seeded_chain.correlation_id}",
                             params={"workspaceId": seeded_chain.workspace_id})
    kinds = [step["kind"] for step in r.json()["chain"]]
    assert kinds == ["event", "inbox", "scheduled_task", "run", "artifact"]
    dump = r.text.lower()
    assert "tool_result" not in dump and "access_token" not in dump

async def test_workspace_b_cannot_read_workspace_a_correlation(ops_client_b, seeded_chain_a):
    r = await ops_client_b.get(f"/agent/events/correlation/{seeded_chain_a.correlation_id}",
                               params={"workspaceId": seeded_chain_a.workspace_id})
    assert r.status_code in (403, 404)

def test_sse_persistence_redacts_non_allowlisted_payload_at_storage_time(stream_manager, fake_repo):
    stream_manager.emit(run_id="r1", event_type="tool.raw_output", payload={"secret": "x", "blob": "y"})
    stored = fake_repo.last_appended()
    assert "secret" not in json.dumps(stored.payload)
    assert set(stored.payload.keys()) <= {"event_ref", "hash", "classification"}
```

- [ ] **Step 3: Chạy — xác nhận đỏ**

Run: `cd services/company && npx vitest run events/tests/event-operations.test.ts --reporter=dot`
Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_event_operations.py -q`
Expected: FAIL cả hai (handler/endpoint/redaction chưa có).

- [ ] **Step 4: Implement operator API (TS)**

`event-operations.handler.ts` — parse input → gọi service → response (không query DB trực tiếp trong handler; business logic ở `event-operations.service.ts`). Mọi truy vấn filter `workspace_id` và kiểm `requireWorkspaceAccess(authorization, workspaceId)` trước. `status=retryable` → `WHERE status IN ('pending','claimed') AND attempt_count > 0`; `status=dead` → `WHERE status='dead'`. SELECT chỉ các cột summary — **không** `envelope`. Retry → `UPDATE ... SET status='pending', claim_token=NULL, visibility_timeout_at=now(), attempt_count=0 WHERE event_id=$1 AND workspace_id=$2 AND status='dead'` + ghi audit typed (`event.outbox.retry`, `{ eventId, actor }`). Disable rule → gọi qua endpoint cosa/company nơi rule store sống (rule là workspace-scoped ở phía cosa — nếu vậy đặt endpoint disable ở `event_operations_routes.py` thay vì company; điều chỉnh theo nơi `EventTriggerRule` được lưu ở Task 4). Audit dùng cơ chế audit hiện có (`grep -rn "audit" services/company/shared`).

`event-operations.api.ts` — Encore `api({ method, expose: true, ... })` cho 3 endpoint, auth operator role.

`outbox-prune.cron.ts` — `CronJob("outbox-prune", { every: "24h", ... })` gọi `pruneDeliveredOutbox(Number(process.env.COSA_OUTBOX_RETENTION_DAYS || 30))`.

- [ ] **Step 5: Implement correlation + SSE storage-time (Python)**

`event_operations_routes.py` — `GET /agent/events/correlation/{correlation_id}`: join `event_inbox` (by `workspace_id + correlation_id`) → scheduled task (by `scheduled_task_id`) → run (by task→run link) → artifact refs. Trả danh sách step `{kind, id, at, refs}` — không đọc `run_events`/tool result body. Workspace check từ caller context.

`event_stream.py` — thêm `_persist_safe(record)`: nếu `record.event_type` không thuộc `UX_EVENT_TYPES` allowlist → thay `record.payload` bằng `{"event_ref": record.id, "hash": sha256(json(payload)), "classification": classify(record)}` **trước** `repository.append(record)` (hiện redact chỉ ở response path `redact_ux_event_payload` — giữ nguyên nó, thêm lớp storage-time).

`app.py` — `app.include_router(create_event_operations_router())`.

- [ ] **Step 6: Chạy — xác nhận xanh**

Run: `cd services/company && npx vitest run events/tests/event-operations.test.ts --reporter=dot`
Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/test_event_operations.py -q`
Expected: PASS.

- [ ] **Step 7: Viết runbook**

Create `docs/operations/event-driven-agent-runtime-runbook.md` với sections: `## Local topology` (diagram từ spec §"Kiến trúc đích"), `## DLQ triage` (`GET /events/outbox?status=dead` → đọc `deadLetterReason` → sửa nguyên nhân → `POST /events/outbox/:id/retry`), `## Incident: relay stuck` (kiểm cron `outbox-relay`, `COSA_AGENTOS_INTAKE_URL` reachable, `claimed` rows quá hạn visibility), `## Replay window & idempotency` (inbox unique key nghĩa là replay an toàn), `## Disable a runaway trigger rule` (`POST /events/rules/:ruleId/disable`), `## Redacted workspace export` (chỉ correlation id + failure code, không payload), link `docs/architecture/adr/ADR-LOCAL-EVENT-BACKBONE-001.md`. Cập nhật `tests/architecture/test_adr_local_first_references.py::test_backbone_adr_stub_exists` nếu cần assert runbook link (đã có trong Task 1 nếu để nguyên).

- [ ] **Step 8: Chạy toàn bộ regression P0**

Run: `cd services/company && npx vitest run --reporter=dot`
Run: `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa tests/contract tests/architecture -q`
Run: `make services-migrate-company && python packages/agent_core/scripts/migrate.py`
Expected: PASS toàn bộ; migration apply sạch.

- [ ] **Step 9: Commit**

```bash
git add services/company/events/ apps/cosa/api/event_operations_routes.py \
        apps/cosa/api/app.py apps/cosa/api/event_stream.py \
        tests/apps/cosa/test_event_operations.py \
        docs/operations/event-driven-agent-runtime-runbook.md
git commit -m "feat(events): operator DLQ/retry API, correlation chain, storage-time redaction"
```

---

## Self-Review

**Spec coverage (P0 = spec Task 0, 2, 3, 4, 5):**

| Spec requirement | Plan task |
| --- | --- |
| Task 0 — `ADR-LOCAL-FIRST-001` + `ADR-LOCAL-EVENT-BACKBONE-001` khung + no-broker guard test | Task 1 |
| Task 2 — canonical envelope, JSON Schema SoT, `makeBusinessEvent`/`validateEnvelope`, cross-language contract test, drop read-path publish, delete `okr-events.service.ts`, cutover `DomainEvent`, strategy events `@deprecated` | Task 2 |
| Task 3 — `integration.event_outbox` DDL + Drizzle schema + `outbox.repository.ts` (append/claim/complete/fail/prune), producers append in-tx, atomicity/retry/DLQ/fencing/SKIP-LOCKED tests | Task 3 |
| Task 4 — relay (bounded, signed, local-only), `event_inbox` UNIQUE, `POST /agent/internal/events` with 4 outcomes + 400/401/403, `EventTriggerRule` + `trigger_policy.resolve`, reference-only schedule via `COSA_EXECUTION_PLANE_URL`, exec-URL fail-fast, cross-process recovery test | Task 4 |
| Task 5 — operator list/retry/disable (workspace-scoped, no raw payload), correlation chain, SSE storage-time allowlist, prune cron, runbook | Task 5 |
| PB-11 (no-rule → `ignored_rule_disabled`) | Task 4 Step 2 `test_no_rule_returns_ignored`, Step 5 `trigger_policy.resolve` |
| PB-12 (retention/prune) | Task 3 `pruneDeliveredOutbox`, Task 5 `outbox-prune.cron.ts` + test |
| DoD #1 (task completes while AgentOS down; delivered after recovery) | Task 3 (in-tx outbox) + Task 4 (relay retry) + e2e Verification below |
| DoD #2 (duplicate → no second run; stale claim can't complete) | Task 3 fencing test + Task 4 duplicate test |
| DoD #3 (workspace isolation on event/DLQ/replay) | Task 4 403 test + Task 5 authorization tests |
| DoD #4 (no raw payload in SSE persistence/logs/telemetry) | Task 5 SSE storage-time test + Task 4 reference-only schedule |
| DoD #8 (operator inspect/retry/disable + follow correlation) | Task 5 |

**Deferred to P1/P2 plans (not this plan):** spec Task 6 (memory/RAG wiring), Task 7 (durable supervisor — blocked on `SPEC-EXEC-PLANE-SPLIT`), Task 8 (eval/promotion gate on triggers — `EventTriggerRule.eval_evidence_ref` left nullable here), Task 9 (broker capacity review — `ADR-LOCAL-EVENT-BACKBONE-001` body). DoD #5/#6/#7/#9 belong to those plans.

**Placeholder scan:** No "TBD"/"handle edge cases"/"similar to Task N". Every code step has a real code block. Test steps have real assertions. Two ordering caveats are called out explicitly (Task 2 Step 10 depends on Task 3 outbox helper; Task 4 Step 6 exec-plane fail-fast is a narrow subset of `SPEC-EXEC-PLANE-SPLIT`).

**Type consistency:** `BusinessEventEnvelope` / `makeBusinessEvent` / `validateEnvelope` / `OPERATIONS_TASK_CREATED_V1` / `OPERATIONS_TASK_COMPLETED_V1` / `TaskCreatedPayloadV1` / `TaskCompletedPayloadV1` defined in Task 2, consumed verbatim in Tasks 3–4. `OutboxRow` / `appendOutboxEvent` / `claimDueOutboxEvents` / `completeOutboxEvent` / `failOutboxEvent` / `pruneDeliveredOutbox` defined in Task 3, consumed verbatim in Tasks 4–5. `EventTriggerRule` / `TriggerDecision` / `IntakeResult` / `handle_event` defined in Task 4, consumed in Task 5. Endpoint `POST /agent/internal/events` outcome strings (`accepted`/`duplicate`/`ignored_rule_disabled`/`policy_denied`) identical in Task 4 route, relay success set (Task 4 Step 10), and tests.

---

## Verification (end-to-end, after Task 5)

**Regression:**
```
cd services/company && npx vitest run --reporter=dot
PYTHONPATH=. .venv/bin/pytest tests/apps/cosa tests/contract tests/architecture -q
make services-migrate-company && python packages/agent_core/scripts/migrate.py
```

**Manual e2e scenario:**
1. Stop AgentOS (`apps/cosa`). Create a task via Company API → task row committed **and** exactly one `integration.event_outbox` row with `status='pending'` (`SELECT status, event_type FROM integration.event_outbox WHERE aggregate_id = ...`).
2. Start AgentOS + let the `outbox-relay` cron tick → `POST /agent/internal/events` returns `{"outcome":"accepted","scheduledTaskId":...}`; one `event_inbox` row; one scheduled task with reference-only payload (`SELECT payload FROM ... ` shows `workspace_id`/`event_id`/spec pin, no title/body).
3. Re-POST the same envelope (simulate relay redelivery) → `{"outcome":"duplicate"}`, no second scheduled task.
4. As Workspace B, call `POST /events/outbox/<A's eventId>/retry` → rejected (404/403).
5. `GET /agent/events/correlation/<correlationId>?workspaceId=<A>` → chain `event → inbox → scheduled_task → run → artifact`; response body contains no tool result / raw payload.
6. `grep -rniE 'kafka|redpanda|nats' deploy/ docker-compose*.yml` → 0 matches; `pytest tests/architecture -q` green.
7. `pytest tests/contract/test_event_envelope_cross_language.py -q` green → TS builder output ↔ Python `Envelope` model agree on `event-envelope.schema.json`.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-28-event-driven-agent-operating-model-p0.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

This plan does not authorize deployment to VPS, broker installation, external provider configuration, or deletion of existing data. P1 (spec Tasks 6–8) and P2 (spec Task 9) get their own plans after P0 lands.
