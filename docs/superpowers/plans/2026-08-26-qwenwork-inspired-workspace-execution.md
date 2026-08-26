# QwenWork-Inspired Workspace Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bổ sung trải nghiệm Agent Session có timeline và deliverable, connector consent scope, lịch chạy durable và capability gate cho COSA test pilot mà không tạo session identity trùng lặp, không làm yếu tenant isolation, và không mở rộng sang computer control/marketplace.

**Architecture:** `ConversationRecord`/`conversation_id` là Agent Session v1; `RunRecord` và `agent_conversation.run_stream_events` là execution/timeline source of truth. `WorkspaceArtifact` được thêm vào `agent_core` vì nó là output runtime có lineage. `services/cosa` sở hữu connector control records và schedule definition/execution; nó chỉ enqueue low-level `scheduled_tasks` với target cố định, còn `apps/cosa` worker tạo Run. Flutter chỉ đọc canonical Agent API và bắt buộc feature manifest trước khi vào UI. Chi tiết quyết định, data contract và scope nằm ở [spec](/Volumes/SSD/javis-saas/docs/architecture/QWENWORK_INSPIRED_PRODUCT_ADJUSTMENT_2026-08-26.md).

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy async, PostgreSQL, TypeScript, Encore, Drizzle ORM, Flutter/GetX, pytest + pytest-asyncio, Vitest.

**Spec:** `docs/architecture/QWENWORK_INSPIRED_PRODUCT_ADJUSTMENT_2026-08-26.md`

## Global Constraints

- Thực hiện P0 trong `docs/architecture/TEST_READINESS_REAUDIT_2026-08-26.md` trước khi bật mutation mới trên môi trường test chung: strict config ngoài test, worker ingress bị bảo vệ, Postgres tích hợp trong CI.
- Không tạo `AgentSession` table hoặc `session_id` mới. Public Session API trả `id == conversation_id`; nếu ghi `RunRecord.session_ref` thì giá trị phải bằng `conversation_id`.
- `packages/agent_core` không import `services/company` hoặc `apps/cosa`.
- Database/API/log không chứa OAuth access token, refresh token hoặc credential. Database chỉ chứa `secret_ref` opaque; response chỉ trả status/scopes/ID được redaction.
- Mọi query resource mới lọc `company_id` **và** `workspace_id`; `conversation_id`, `run_id` hay artifact ID một mình không phải authorization boundary.
- Không expose public endpoint cho low-level schedule/claim/complete hay connector secret resolution. Dùng worker ingress đã harden ở Wave P0.
- v1 schedule chỉ nhận `one_time`, `daily`, `weekdays`; dùng IANA timezone hợp lệ và đóng băng prompt/connector grant snapshot theo execution.
- Event UI chỉ dùng `agent_conversation.run_stream_events`; `agent_core.run_events` tiếp tục là governance ledger riêng.
- Chỉ ship connector `sandbox-read` sau khi policy test pass. Không ship connector write/computer control trong plan này.
- Tên định danh mới dùng English; comment mới giải thích bằng tiếng Việt. Không đổi contract cũ không liên quan.

---

### Task 0: Khóa P0 và baseline trước khi thêm bề mặt sản phẩm

**Files:**
- Verify/modify: `services/cosa/handlers/control-plane.handler.ts`
- Verify/modify: `services/cosa/handlers/worker-ingress.handler.ts`
- Verify/modify: `apps/cosa/composition/agent_plane.py`
- Test: `services/cosa/tests/worker-ingress.test.ts`
- Test: `tests/apps/cosa/test_composition.py`

**Interface:** mọi caller production của `build_cosa_agent_plane()` phải có `AGENT_CORE_DATABASE_URL`; scheduler lifecycle chỉ chấp nhận worker credential đã xác thực.

- [ ] **Step 1: Chạy baseline và ghi kết quả vào PR/task log.**

```bash
cd /Volumes/SSD/javis-saas
./.venv/bin/python -m pytest tests/apps/cosa tests/agent_core -q
(cd services/cosa && pnpm test)
```

Expected: xử lý failure theo re-audit trước; không đổi integration test về repository in-memory để làm xanh giả.

- [ ] **Step 2: Viết/giữ test red cho ingress không có credential.**

Trong `services/cosa/tests/worker-ingress.test.ts`, gọi schedule/claim/heartbeat/complete không có worker credential và assert non-success. Một request ký đúng vẫn chạy lifecycle bình thường.

- [ ] **Step 3: Implement P0.**

Trong `control-plane.handler.ts`, không public các mutation worker-only; `worker-ingress.handler.ts` xác thực credential trước khi gọi scheduler. Giữ `build_cosa_agent_plane()` fail-closed khi thiếu URL DB và giữ explicit in-memory repositories chỉ cho test.

- [ ] **Step 4: Verify P0.**

```bash
cd /Volumes/SSD/javis-saas
(cd services/cosa && pnpm vitest run tests/worker-ingress.test.ts tests/control-plane-scheduler-crash-recovery.test.ts)
./.venv/bin/python -m pytest tests/apps/cosa/test_composition.py -v
```

Expected: ingress trái phép bị chặn, crash recovery pass và production composition không rơi về RAM.

---

### Task 1: Thêm SessionView read model trên Conversation substrate hiện có

**Files:**
- Modify: `apps/cosa/api/schemas.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/api/event_stream.py`
- Modify: `apps/cosa/conversations/repository.py`
- Modify: `packages/agent_core/conversations/repository.py`
- Test: `tests/apps/cosa/test_session_view.py` (new)
- Test: `tests/apps/cosa/test_event_stream.py`

**Interfaces:**

```python
class SessionStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"

class SessionViewResponse(BaseModel):
    id: str  # exact ConversationRecord.conversation_id
    company_id: str
    workspace_id: str
    title: str
    agent_profile: str | None
    status: SessionStatus
    latest_run: RunSummaryResponse | None
    messages: list[MessageResponse]
    timeline: list[EventEnvelopeDTO]
    artifacts: list[WorkspaceArtifactResponse]
    enabled_connector_keys: list[str]

GET /agent/sessions/{conversation_id} -> SessionViewResponse
GET /agent/sessions/{conversation_id}/timeline?after_sequence=0&limit=100 -> list[EventEnvelopeDTO]
```

- [ ] **Step 1: Viết test aggregate/tenancy thất bại.**

Tạo `tests/apps/cosa/test_session_view.py` với hai conversations ở hai `(company_id, workspace_id)` khác nhau, một run và ba stream events trong session của caller. Assert owner có `id == conversation_id`, event đúng sequence; tenant khác nhận `404`; `after_sequence` loại event cũ; `limit=101` nhận `422`; `run.failed`, approval pending và `run.completed` lần lượt cho `failed`, `waiting_approval`, `completed`.

- [ ] **Step 2: Thêm DTO không lặp message contract.**

Trong `apps/cosa/api/schemas.py`, export `RunSummaryResponse`, `SessionStatus`, `SessionTimelineResponse` và `SessionViewResponse`. Reuse `ConversationResponse`, `MessageResponse`, `EventEnvelopeDTO`; `timeline` mặc định `[]`; route giới hạn `1 <= limit <= 100`.

- [ ] **Step 3: Thêm scoped read và allowlisted event projection.**

Thêm `get_session_context(company_id: str, workspace_id: str, conversation_id: str)` vào conversation repository. Thêm stream read theo `after_sequence`/`limit`. Trong `CosaEventStreamManager`, frozen allowlist là:

```python
UX_EVENT_TYPES = frozenset({
    "run.started", "reasoning.status", "message.started", "message.delta",
    "approval.required", "approval.resolved", "run.completed", "run.failed",
})
```

Tạo `redact_ux_event_payload(event_type: str, payload: dict[str, Any]) -> dict[str, Any]`. Nó không forwards `secret_ref`, `authorization_id`, `access_token`, `refresh_token`, `delegation_token`, `input_payload` hay arbitrary `error_details`; event không nhận diện được bị bỏ qua và log nội bộ.

- [ ] **Step 4: Thêm hai GET route mà không đổi route conversation cũ.**

Trong `apps/cosa/api/routes.py`, resolve principal/company/workspace bằng helper đang dùng cho route conversation, gọi repository scoped, derive status từ run/event mới nhất, trả `404` cho record thiếu hoặc out-of-scope. Không dùng `X-Workspace-ID` một mình làm authorization.

- [ ] **Step 5: Chạy test.**

```bash
cd /Volumes/SSD/javis-saas
./.venv/bin/python -m pytest tests/apps/cosa/test_session_view.py tests/apps/cosa/test_event_stream.py tests/apps/cosa/test_conversation_routes.py -v
```

Expected: tenant denial, event redaction và route conversation hiện hữu đều pass.

---

### Task 2: Persist WorkspaceArtifact và tạo output artifact cho completed run

**Files:**
- Create: `packages/agent_core/artifacts/__init__.py`
- Create: `packages/agent_core/artifacts/models.py`
- Create: `packages/agent_core/artifacts/repository.py`
- Create: `packages/agent_core/artifacts/postgres.py`
- Create: `packages/agent_core/migrations/016_workspace_artifacts.sql`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/api/schemas.py`
- Modify: `apps/cosa/api/routes.py`
- Test: `tests/agent_core/artifacts/test_repository.py` (new)
- Test: `tests/apps/cosa/test_artifact_routes.py` (new)
- Test: `tests/apps/cosa/test_worker_handlers.py`

**Interfaces:**

```python
class WorkspaceArtifact(BaseModel):
    artifact_id: str
    company_id: str
    workspace_id: str
    conversation_id: str
    run_id: str | None = None
    source_message_id: str | None = None
    artifact_kind: Literal["assistant_output", "report", "table", "file_export"]
    display_name: str
    media_type: str
    object_ref: str
    checksum: str | None = None
    size_bytes: int = 0
    status: Literal["available", "failed", "archived"] = "available"
    input_artifact_ids: list[str] = []
```

`ArtifactRepository.create(artifact)`, `list_for_conversation(company_id, workspace_id, conversation_id)` và `archive(company_id, workspace_id, artifact_id)` là ba operation v1. `GET /agent/conversations/{conversation_id}/artifacts` trả artifacts scoped/available.

- [ ] **Step 1: Chọn migration number ngay trước khi code.**

Chạy `ls packages/agent_core/migrations | sort | tail -3`. Nếu số `016` đã được merge bởi work khác, dùng số kế tiếp thật cho tên file và cập nhật reference trong task này. SQL tạo schema `agent_artifact`, table `workspace_artifacts`, JSONB `input_artifact_ids NOT NULL DEFAULT '[]'::jsonb`, indexes `(company_id, workspace_id, conversation_id, created_at DESC)` và `(run_id)`.

- [ ] **Step 2: Viết repository test red.**

Trong `tests/agent_core/artifacts/test_repository.py`, create/round-trip artifact qua Postgres; list bằng workspace khác không có row; archive owner scope rồi default list không chứa nó; `object_ref="secret://..."` bị validation reject, valid ref bắt đầu `object://` hoặc `artifact://`.

- [ ] **Step 3: Implement contract/repositories.**

`WorkspaceArtifact` tạo ID `art_<12 hex>`, validate display name/media type không rỗng và opaque ref prefix. `PostgresArtifactRepository` có company/workspace predicates ở mọi select/update. Cung cấp `InMemoryArtifactRepository` trong cùng repository module, chỉ dùng khi test inject rõ ràng. Không thêm storage SDK/presigned URL.

- [ ] **Step 4: Wire composition và worker.**

Thêm required `artifact_repository: ArtifactRepository` vào `CosaAgentPlane`; production dùng Postgres từ `AGENT_CORE_DATABASE_URL`, test inject in-memory. Trong `apps/cosa/worker/handlers.py::execute_run_task`, sau successful assistant message write, create:

```python
WorkspaceArtifact(
    company_id=company_id,
    workspace_id=workspace_id,
    conversation_id=conversation_id,
    run_id=run_id,
    source_message_id=assistant_message.message_id,
    artifact_kind="assistant_output",
    display_name="Agent response",
    media_type="text/plain",
    object_ref=f"artifact://run/{run_id}/assistant-output",
)
```

Bind `assistant_message = await _append_message(...)`. Không tạo artifact nếu message persistence failed.

- [ ] **Step 5: Thêm scoped DTO/read route và verify.**

Thêm `WorkspaceArtifactResponse`, trước hết verify conversation ownership rồi list bằng exact company/workspace/conversation tuple. Chạy:

```bash
cd /Volumes/SSD/javis-saas
./scripts/run-agent-core-migrations.sh
./.venv/bin/python -m pytest tests/agent_core/artifacts tests/apps/cosa/test_artifact_routes.py tests/apps/cosa/test_worker_handlers.py -v
```

Expected: migration additive; artifact chỉ hiện trong tenant sở hữu và có lineage tới run/message.

---

### Task 3: Thêm connector installation, authorization reference và session grant

**Files:**
- Create: `services/cosa/migrations/11_workspace_connectors_and_schedules.up.sql`
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Create: `services/cosa/services/workspace-connector.service.ts`
- Create: `services/cosa/handlers/workspace-connector.handler.ts`
- Modify: `services/cosa/handlers/index.ts`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/api/schemas.py`
- Test: `services/cosa/tests/workspace-connector.test.ts` (new)
- Test: `tests/apps/cosa/test_connector_proxy_routes.py` (new)

**Interfaces:**

```ts
type ConnectorAuthorizationState = "active" | "expired" | "revoked";
type SessionConnectorGrantState = "enabled" | "revoked" | "expired";

installWorkspaceConnector(input: {
  companyId: string; workspaceId: string; connectorKey: "sandbox-read"; installedBy: string;
}): Promise<WorkspaceConnectorInstallation>;

registerConnectorAuthorization(input: {
  installationId: string; principalId: string; secretRef: string;
  grantedScopes: string[]; expiresAt: Date;
}): Promise<ConnectorAuthorization>;

grantConnectorToSession(input: {
  companyId: string; workspaceId: string; conversationId: string;
  authorizationId: string; grantedBy: string; allowedActions: string[];
  expiresAt: Date | null;
}): Promise<SessionConnectorGrant>;
```

- [ ] **Step 1: Tạo schema và Drizzle map.**

Migration 11 thêm `workspace_connector_installations` unique `(company_id, workspace_id, connector_key)`; `connector_authorizations` reference installation, principal, `secret_ref`, JSONB scopes/state/expiry/revoke metadata; `session_connector_grants` reference authorization và exact company/workspace/conversation tuple, JSONB allowed actions/state/expiry. Use `CHECK` cho state. Không có token column. Map sang camelCase TypeScript trong `control-plane-schema.ts`.

- [ ] **Step 2: Viết test red.**

`workspace-connector.test.ts` cover duplicate installation chỉ trả một record; list/session projection không lộ `secretRef`; authorization workspace khác không grant được; expired/revoked tạo typed `connector_reauth_required`; thiếu scope/action bị reject; active `sandbox-read` chỉ usable cho đúng principal/session.

- [ ] **Step 3: Implement service và handler.**

Reject key ngoài `COSA_CONNECTOR_ALLOWED_KEYS`. `secretRef` phải match `secret://cosa-connectors/<opaque-id>`. DTO public chỉ `has_secret`, state, expiry, scopes. Mọi state transition transactionally audit operation/state và IDs. TS handler lấy identity/company/workspace từ authenticated context, không tin các value client mutable. Agent API chỉ proxy user-level grant/revoke sau conversation ownership check.

- [ ] **Step 4: Insert authorization assertion trước capability invocation.**

Tạo adapter trong `apps/cosa/capabilities/` gọi internal control-plane assertion với IDs/scope/action trước connector capability handler. Secret provider chỉ được resolve sau assertion thành công. Register deterministic read-only fake cho `sandbox-read` ở test, không integration provider production.

- [ ] **Step 5: Verify privacy/tenancy.**

```bash
cd /Volumes/SSD/javis-saas
(cd services/cosa && pnpm vitest run tests/workspace-connector.test.ts tests/worker-ingress.test.ts)
./.venv/bin/python -m pytest tests/apps/cosa/test_connector_proxy_routes.py -v
```

Expected: secret never appears in public response snapshot; grant ownership and expiry are enforced.

---

### Task 4: Implement schedule definition/execution durable và worker handoff

**Files:**
- Modify: `services/cosa/migrations/11_workspace_connectors_and_schedules.up.sql`
- Modify: `services/cosa/storage/control-plane-schema.ts`
- Create: `services/cosa/services/workspace-schedule.service.ts`
- Create: `services/cosa/handlers/workspace-schedule.handler.ts`
- Modify: `services/cosa/control-plane.cron.ts`
- Modify: `services/cosa/handlers/index.ts`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/api/schemas.py`
- Test: `services/cosa/tests/workspace-schedule.test.ts` (new)
- Test: `tests/apps/cosa/test_scheduled_session_worker.py` (new)

**Interfaces:**

```ts
type ScheduleKind = "one_time" | "daily" | "weekdays";
type ScheduleState = "enabled" | "paused" | "archived";
type ScheduleExecutionState = "queued" | "running" | "succeeded" | "failed" | "blocked_reauth" | "cancelled";

createWorkspaceSchedule(input: {
  companyId: string; workspaceId: string; createdBy: string;
  scheduleKind: ScheduleKind; timezone: string; runAt?: Date;
  hour?: number; minute?: number; weekdays?: number[];
  promptTemplate: string; agentProfile: "operations" | "finance";
  connectorGrantIds: string[];
}): Promise<WorkspaceScheduleDefinition>;

dispatchDueWorkspaceSchedules(now: Date, limit: number): Promise<number>;
```

- [ ] **Step 1: Add data tables with immutable execution snapshot.**

Migration 11 thêm `workspace_schedule_definitions` (owner scope, state, kind, IANA timezone, time fields, prompt template, agent profile, connector grant IDs, next run) và `workspace_schedule_executions` (definition ID, owner scope, `scheduled_for`, immutable prompt/profile/grant snapshots, state, low-level task ID, run ID, error). Unique `(definition_id, scheduled_for)` ngăn duplicate; indexes definitions `(state, next_run_at)` và executions `(company_id, workspace_id, scheduled_for DESC)`.

- [ ] **Step 2: Write failing schedule service tests.**

Freeze time in `workspace-schedule.test.ts`. Assert one-time dispatch đúng một lần và không enabled sau completion; daily `Asia/Ho_Chi_Minh` tính đúng UTC; weekdays nhận only 1–7 and skips days; dispatch twice yields one execution/task; paused/archived không dispatch; active schedule thứ 11 bị reject; execution snapshot không đổi sau edit definition.

- [ ] **Step 3: Implement bounded calendar calculation.**

Validate IANA timezone by constructing formatter, hour `0..23`, minute `0..59`, nonempty/distinct weekdays for `weekdays`, and `runAt > now` for one-time. Use current Node capability or introduce one explicit timezone library only if existing target cannot convert IANA zones safely. No client cron parser.

- [ ] **Step 4: Dispatcher transaction dùng existing durable queue.**

`control-plane.cron.ts` invokes `dispatchDueWorkspaceSchedules(new Date(), configuredBatchSize)` each minute. Transaction locks due enabled definitions with `FOR UPDATE SKIP LOCKED`, creates execution and calls existing `scheduleTask` with exactly:

```ts
{
  targetSpecId: "cosa.schedule-execution",
  targetSpecKind: "agent",
  coalescingKey: `schedule-execution:${execution.id}`,
  inputPayload: { task_type: "scheduled_session", schedule_execution_id: execution.id },
}
```

Store task ID and advance `next_run_at`. Queue payload must not have prompt, tenant identity, grant IDs or secret ref.

- [ ] **Step 5: Worker handoff và reauth block.**

`apps/cosa/worker/main.py` sends `scheduled_session` to `execute_scheduled_session_task`. Handler loads authenticated internal execution projection, marks running atomically, validates all grants from Task 3. A failed grant marks `blocked_reauth` and returns before model/tool call. If valid, create a fresh `ConversationRecord` with metadata `{"origin": "schedule", "schedule_execution_id": execution_id}`, a fresh run ID, then call `execute_run_task` with server-supplied prompt/profile/identity. On terminal call `completeScheduleExecution`; never call public user route from worker.

- [ ] **Step 6: User routes and run-now.**

Add `POST/GET/PATCH /agent/schedules` and `POST /agent/schedules/{id}/run-now`. Run-now invokes the same service method creating execution at current UTC; it is not direct model invocation. Responses expose execution state/time and linked `conversation_id`/`run_id`, but no prompt/secret refs.

- [ ] **Step 7: Verify durable behavior.**

```bash
cd /Volumes/SSD/javis-saas
(cd services/cosa && pnpm vitest run tests/workspace-schedule.test.ts tests/control-plane-scheduler-crash-recovery.test.ts)
./.venv/bin/python -m pytest tests/apps/cosa/test_scheduled_session_worker.py tests/apps/cosa/test_worker_handlers.py -v
```

Expected: concurrent dispatch not duplicate, queue payload is server controlled, reauth blocks with no model call, success creates one linked conversation/run.

---

### Task 5: Wire canonical Flutter UI behind capability manifest

**Files:**
- Modify: `frontend/lib/core/manifest/test_capability_manifest.dart`
- Create: `frontend/lib/core/manifest/capability_gate.dart`
- Modify: `frontend/lib/core/routing/app_pages.dart`
- Modify: `frontend/lib/core/routing/app_routes.dart`
- Modify: `frontend/lib/modules/chat/services/agent_chat_service.dart`
- Modify: `frontend/lib/modules/chat/models/chat_models.dart`
- Modify: `frontend/lib/modules/chat/controllers/chat_controller.dart`
- Modify: `frontend/lib/modules/chat/views/chat_view.dart`
- Create: `frontend/lib/modules/schedules/services/schedule_service.dart`
- Create: `frontend/lib/modules/schedules/controllers/schedule_controller.dart`
- Create: `frontend/lib/modules/schedules/views/schedule_view.dart`
- Test: `frontend/test/core/manifest/capability_gate_test.dart` (new)
- Test: `frontend/test/modules/chat/session_timeline_test.dart` (new)
- Test: `frontend/test/modules/schedules/schedule_module_test.dart` (new)

**Interfaces:**

```dart
enum TestCapability { canonicalSessions, artifactLineage, connectorConsent, schedules }

abstract final class CapabilityGate {
  static bool allows(TestCapability capability);
  static RouteSettings blockedRoute(RouteSettings requested);
}

Future<SessionView> AgentChatService.fetchSession(String conversationId);
Future<List<WorkspaceArtifact>> AgentChatService.listArtifacts(String conversationId);
Future<WorkspaceScheduleExecution> ScheduleService.runNow(String scheduleId);
```

- [ ] **Step 1: Write widget/unit tests first.**

Gate test asserts disabled route redirects to neutral unavailable screen and does not construct binding. Session test maps redacted events/artifact in order and never renders secret-like field. Schedule test asserts disabled route unavailable and `runNow` calls canonical Agent API once.

- [ ] **Step 2: Implement fail-closed manifest/gate.**

Extend manifest with typed server-delivered list. Missing/malformed/unknown values produce false. Preserve existing legacy-extension flag behavior. Route guard in `app_pages.dart` executes before a binding. Do not add a default-enabled legacy route.

- [ ] **Step 3: Adapt chat and schedules UI.**

Keep current message send/SSE behavior. Fetch SessionView on page load/terminal event; render compact ordered timeline and Deliverables section. `connector_reauth_required` shows localized reconnect instruction, never provider error. Schedule screen is list/create/pause/resume/run-now/history only; explicit one-time/daily/weekdays selector, restricted IANA timezone picker, weekday selector, no cron text input. Completed execution links `conversation_id` to chat route.

- [ ] **Step 4: Verify Flutter and routes.**

```bash
cd /Volumes/SSD/javis-saas/frontend
flutter test test/core/manifest/capability_gate_test.dart test/modules/chat/session_timeline_test.dart test/modules/schedules/schedule_module_test.dart
flutter analyze
```

Expected: direct route cannot bypass gate; enabled canonical screens only call `/agent` API.

---

### Task 6: Add origin/quotas/telemetry and stage pilot evidence

**Files:**
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `services/cosa/services/workspace-schedule.service.ts`
- Modify: `frontend/lib/modules/chat/views/chat_view.dart`
- Test: `tests/apps/cosa/test_scheduled_session_worker.py`
- Test: `services/cosa/tests/workspace-schedule.test.ts`
- Create: `docs/architecture/reports/qwenwork-workspace-execution-pilot-evidence-2026-08-26.md`

**Interfaces:** interactive and schedule runs set `RunRequest.metadata["execution_origin"]` to `"interactive"` or `"schedule"`; scheduled runs also hold `schedule_execution_id`. Limits are `COSA_SCHEDULE_MAX_ACTIVE_PER_WORKSPACE=10`, `COSA_SCHEDULE_MAX_EXECUTIONS_24H=50` and `COSA_SCHEDULE_DISPATCH_BATCH_SIZE=25`.

- [ ] **Step 1: Write red quota/origin tests.**

Assert scheduled run metadata has origin/execution ID; interactive run stays interactive; 51st queued/running/succeeded occurrence during rolling 24h is rejected before low-level queue insert.

- [ ] **Step 2: Implement bounded usage and safe telemetry.**

Add origin/execution ID plus fresh policy snapshot to `RunRequest.metadata`, nothing credential-like. Count schedule executions in same transaction that creates execution. Record only non-sensitive `session.created`, `run.queue_delay_ms`, `run.time_to_first_event_ms`, `run.terminal`, `artifact.created`, `connector.reauth_blocked`, `schedule.dispatch_lag_ms`, `schedule.duplicate_prevented`, `tenant.scope_denied`. Exclude raw prompt, object ref and secret/provider IDs.

- [ ] **Step 3: Run acceptance plus negative paths.**

Create two test companies/workspaces. Enable all four capabilities only in workspace A. Run the spec Golden path. From workspace B attempt every session/artifact/grant/schedule ID of A: expect 404/policy denial. Revoke A authorization then run schedule: expect `blocked_reauth`, no model/tool call. Concurrent run-now: expect one occurrence. Direct disabled Flutter route: unavailable.

- [ ] **Step 4: Full verification and evidence.**

```bash
cd /Volumes/SSD/javis-saas
./.venv/bin/python -m pytest tests/agent_core tests/apps/cosa -q
(cd services/cosa && pnpm test)
(cd frontend && flutter analyze && flutter test)
git diff --check
```

Populate the evidence file with revision, migration versions, redacted workspace IDs, manifest values, command statuses and golden/negative results. Never add personal customer data or secrets. Do not call the pilot ready if any integration suite was skipped; fix infrastructure or record rollout blocked. Keep rollout to workspace allowlist for seven days; expand only if release criteria in the spec all hold.

## Final implementation checklist

- [ ] P0 control-plane and persistent test gates pass.
- [ ] `SessionView` reuses `conversation_id`, scopes reads and redacts events.
- [ ] Artifact migration/repository/API preserve run and message lineage.
- [ ] Connector state is install → authorization → session grant; no credential is persisted or rendered.
- [ ] Scheduler creates immutable execution snapshots, queue payload contains only execution ID, and reauth prevents model/tool execution.
- [ ] Flutter routes and bindings fail closed through test capability manifest.
- [ ] Cross-plane suites and evidence cover both positive and negative pilot paths.
