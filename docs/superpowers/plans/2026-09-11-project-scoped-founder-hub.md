# Founder Hub theo Project Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Biến Founder Hub thành Project Execution Console không có Company-wide, trong đó mọi command, run và dấu vết vận hành được khóa theo Project và có thể truy hồi bền vững.

**Architecture:** Giữ Company là nguồn sự thật cho Project và business fact; Agent Platform giữ conversation, run và Project Activity Feed projection. Mọi request Hub mang Project tường minh, được Company xác minh trước side effect. Flutter chỉ khôi phục Project đã chọn từ local storage, dùng typed contract để chat và tải/stream timeline; nó không suy ra quyền hay dựng activity từ state tạm.

**Tech Stack:** PostgreSQL, Python/FastAPI/Pydantic, SQLAlchemy/asyncpg, Encore/TypeScript/Drizzle, Flutter/GetX, SSE, pytest, Vitest và Flutter test.

**Spec:** docs/superpowers/specs/2026-09-11-project-scoped-founder-hub-design.md

## Global Constraints

- Làm trực tiếp trên main; không tạo git worktree.
- Không ghi đè hoặc discard các thay đổi hiện có của người dùng trong frontend; rebase thiết kế task lên trạng thái file tại thời điểm thực thi.
- Company Services là business truth. Agent Platform không đọc/ghi trực tiếp Company DB; business fact đi qua typed Company API và Company outbox.
- Không có Company-wide, All Project, Project mặc định, projects.first, Project gần nhất hoặc suy diễn Project từ prompt/agent profile trong Founder Hub.
- Local key active_project_id:<workspace_id> chỉ phục hồi lựa chọn UX. Server xác minh workspace, Project và quyền ở mọi read/write.
- Mọi artifact Hub tạo/hiển thị có project_id: conversation, message, run, checkpoint, tool call, approval, activity event và stream payload.
- Conversation không đổi Project. Bản ghi cũ thiếu Project là LEGACY_UNSCOPED: giữ audit, không tự backfill và không tạo run mới.
- Timeline là durable projection có source reference, correlation và redaction; không chứa raw prompt, Vault content, token, secret hoặc payload nhạy cảm.
- Mọi live endpoint được khai báo trong shared/contracts/mvp-surface.json, sinh lại generated contract và có backend negative test, Flutter contract test cùng E2E phù hợp.
- Không thêm GitHub adapter, repository connector, pull request/issue flow hoặc bất kỳ collaboration surface kiểu Buzz/GitHub.
- Lifecycle Workspace/Project được giữ nguyên; Project context không phải authorization và không cho phép agent tự đổi lifecycle.

---

## Delivery order

    1 contract + persisted Project scope
              |
    2 conversation/run request enforcement
              |
    3 durable Activity Feed projection
              |
    4 Company outbox -> projection intake
              |
    5 activity read/detail/SSE API
              |
    6 Flutter Project scope + typed clients
              |
    7 Hub layout and truthful rendering
              |
    8 cross-plane evidence and release gate

## Source map locked before implementation

| Area | Existing responsibility | Planned change |
| --- | --- | --- |
| packages/agent/conversations | ConversationRecord and repository for durable conversations/messages | Persist immutable Project scope and list/read by workspace plus Project. |
| packages/agent/runs | Durable run, tool, approval, checkpoint and SSE ledgers | Carry Project scope to every new runtime record and stream envelope. |
| apps/cosa/api/conversation_routes.py | Conversation creation, message acceptance and scheduler dispatch | Require and verify Project before any message/run side effect; remove fallback resolution. |
| apps/cosa/api/event_stream.py | Durable run SSE fanout and payload redaction | Preserve Project in run events and feed the separate Project Activity projection. |
| apps/cosa/events and Company outbox | Signed Company business-event delivery to Agent Platform | Deliver typed, Project-bearing facts into the projection without Agent Platform touching Company DB. |
| frontend chat and Hologram Hub | Existing chat transport and visible Founder Hub | Carry Project on every request, restore local selected Project and render only durable Project activity. |
| shared/contracts/mvp-surface.json | Canonical client/route ownership contract | Register every Project-scoped conversation and activity endpoint. |

### Task 1: Freeze the Project-scoped contract and durable storage shape

**Files:**

- Create: packages/agent/migrations/004_project_scoped_founder_hub.sql
- Create: packages/agent/migrations/004_project_scoped_founder_hub.down.sql
- Modify: packages/agent/conversations/models.py
- Modify: packages/agent/conversations/repository.py
- Modify: packages/agent/runs/models.py
- Modify: packages/agent/runs/repository.py
- Modify: packages/agent/runs/stream_events.py
- Modify: apps/cosa/api/schemas.py
- Modify: shared/contracts/mvp-surface.json
- Modify: apps/cosa/api/mvp_contracts_generated.py
- Modify: services/company/shared/contracts/mvp-surface.generated.ts
- Create: tests/agent/conversations/test_project_scoped_repository.py
- Create: tests/agent/runs/test_project_scoped_records.py
- Create: tests/contracts/test_project_scoped_hub_surface.py

**Interfaces:**

- Produces ConversationRecord.project_id and scope_state, where scope_state is PROJECT_SCOPED or LEGACY_UNSCOPED.
- Produces MessageRecord.project_id, RunRecord.project_id, RunCheckpointRecord.project_id, RunToolCallRecord.project_id, RunApprovalRecord.project_id, RunEventRecord.project_id and RunStreamEventRecord.workspace_id/project_id.
- Produces ConversationRepository list_conversations(workspace_id, project_id, include_archived, limit, offset) and scoped lookup methods that require both workspace_id and project_id.
- Produces contract entries for agent.conversation.create/read/update/message and agent.project_activity.read/detail/stream, all with requires_workspace and requires_project true.

- [ ] **Step 1: Write failing model, repository and contract tests**

    Add model assertions that a new Hub artifact cannot be built without Project
    scope, while an explicitly constructed legacy fixture remains read-only:

        def test_new_conversation_requires_project_scope():
            with pytest.raises(ValidationError, match="project_id"):
                ConversationRecord(
                    workspace_id="ws_a",
                    created_by_principal="human_a",
                    title="Founder Hub",
                    scope_state="PROJECT_SCOPED",
                )

        def test_legacy_conversation_is_explicit_not_inferred():
            legacy = ConversationRecord(
                workspace_id="ws_a",
                created_by_principal="human_a",
                title="Old",
                project_id=None,
                scope_state="LEGACY_UNSCOPED",
            )
            assert legacy.project_id is None

    Add an in-memory repository test with Project A and B in one workspace:

        rows, total = await repo.list_conversations(
            workspace_id="ws_a", project_id="proj_a"
        )
        assert total == 1
        assert [row.conversation_id for row in rows] == ["conv_a"]

    Add contract assertions that each new Agent Hub capability has
    requires_project true and no capability path contains company-wide, all-projects
    or GitHub adapter ownership.

- [ ] **Step 2: Run the focused tests and confirm they fail**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/agent/conversations/test_project_scoped_repository.py tests/agent/runs/test_project_scoped_records.py tests/contracts/test_project_scoped_hub_surface.py -q

    Expected: FAIL because current models omit Project fields, repository list
    reads only workspace, and the canonical MVP surface does not define the
    required Project-scoped Hub endpoints.

- [ ] **Step 3: Add a forward-only, non-inferential migration**

    In migration 004, add nullable Project columns to existing durable records:

        agent_conversation.conversations.project_id
        agent_conversation.conversations.scope_state
        agent_conversation.messages.project_id
        agent.runs.project_id
        agent.run_checkpoints.project_id
        agent.run_tool_calls.project_id
        agent.approvals.project_id
        agent.run_events.project_id
        agent_conversation.run_stream_events.workspace_id
        agent_conversation.run_stream_events.project_id

    Use CHECK constraints so a row is either LEGACY_UNSCOPED with project_id
    null, or PROJECT_SCOPED with project_id non-null. Mark pre-existing rows
    LEGACY_UNSCOPED in the migration; do not derive a Project from title,
    timestamp, agent profile or workspace ordering. Add indexes on:

        conversations(workspace_id, project_id, archived_at)
        runs(workspace_id, project_id, status, created_at desc)
        run_stream_events(workspace_id, project_id, sequence)

    The down migration must refuse to drop a column if a PROJECT_SCOPED row
    exists. It may only remove the additive schema when no new scoped data has
    been written; this prevents rollback from silently deleting audit context.

- [ ] **Step 4: Propagate Project scope through models and repositories**

    Add Pydantic validation equivalent to:

        if self.scope_state == "PROJECT_SCOPED" and not self.project_id:
            raise ValueError("PROJECT_SCOPED records require project_id")
        if self.scope_state == "LEGACY_UNSCOPED" and self.project_id:
            raise ValueError("LEGACY_UNSCOPED records must not carry project_id")

    Update InMemory and Postgres repository inserts/selects so Project columns
    are written and read at every named durable artifact. Change scoped
    conversation queries to include both workspace_id and project_id. Keep
    unscoped legacy rows excluded from Project-scoped list/read queries.

- [ ] **Step 5: Register the canonical surface and generate code**

    Add the following source-owned entries to shared/contracts/mvp-surface.json:

        agent.conversation.create
        agent.conversation.read
        agent.conversation.update
        agent.conversation.message.create
        agent.project_activity.read
        agent.project_activity.detail
        agent.project_activity.stream

    Each entry must name its exact API path, schema, agent owner,
    agent_db source kind, backend test, Flutter service test and integration
    test. Set requires_workspace and requires_project to true. Generate, do
    not hand-edit, apps/cosa/api/mvp_contracts_generated.py and
    services/company/shared/contracts/mvp-surface.generated.ts:

        node scripts/gen-mvp-contracts.mjs

- [ ] **Step 6: Run focused proof**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/agent/conversations/test_project_scoped_repository.py tests/agent/runs/test_project_scoped_records.py tests/contracts/test_project_scoped_hub_surface.py -q

    Expected: PASS. A Project A query cannot return Project B or legacy rows;
    generated contracts agree with the JSON source.

- [ ] **Step 7: Commit the contract and storage boundary**

    git add packages/agent/migrations/004_project_scoped_founder_hub.sql packages/agent/migrations/004_project_scoped_founder_hub.down.sql packages/agent/conversations packages/agent/runs apps/cosa/api/schemas.py shared/contracts/mvp-surface.json apps/cosa/api/mvp_contracts_generated.py services/company/shared/contracts/mvp-surface.generated.ts tests/agent/conversations/test_project_scoped_repository.py tests/agent/runs/test_project_scoped_records.py tests/contracts/test_project_scoped_hub_surface.py
    git commit -m "feat: scope hub artifacts to projects"

### Task 2: Require and verify Project context before conversation or run side effects

**Files:**

- Create: apps/cosa/api/project_context.py
- Modify: apps/cosa/api/conversation_routes.py
- Modify: apps/cosa/api/routes.py
- Modify: apps/cosa/worker/handlers.py
- Modify: apps/cosa/api/schemas.py
- Modify: frontend/lib/modules/chat/services/agent_chat_service.dart
- Create: tests/apps/cosa/api/test_conversation_project_context.py
- Modify: tests/apps/cosa/test_routes.py
- Modify: tests/apps/cosa/worker/test_project_scoped_agent_run.py

**Interfaces:**

- Produces verify_project_context(plane, identity, project_id) -> VerifiedProjectContext.
- Produces ProjectContextHttpError with codes PROJECT_CONTEXT_REQUIRED, PROJECT_CONTEXT_MISMATCH and PROJECT_NOT_FOUND_OR_FORBIDDEN.
- Produces a Project-scoped conversation command contract: create, list, get, update, message and run event/cancel calls receive a project_id and enforce equality with the persisted conversation/run.

- [ ] **Step 1: Write server negative tests before route changes**

    Test all side effects are absent on a missing/mismatched Project:

        response = await client.post(
            "/agent/conversations",
            json={"title": "Founder Hub", "active_agent_profile": "operations"},
            headers=auth_headers("ws_a"),
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "PROJECT_CONTEXT_REQUIRED"
        assert await conversation_repo.list_conversations(
            workspace_id="ws_a", project_id="proj_a"
        ) == ([], 0)

        response = await client.post(
            "/agent/conversations/conv_a/messages",
            json={
                "content": "ship it",
                "project_id": "proj_b",
                "data_access": {"categories": ["internal"]},
            },
            headers=auth_headers("ws_a"),
        )
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "PROJECT_CONTEXT_MISMATCH"
        assert scheduler.scheduled == []

    Add a cross-tenant fixture where Company returns no authorized Project for
    ws_a/proj_b. Assert a 404 code PROJECT_NOT_FOUND_OR_FORBIDDEN and no
    existence details. Extend worker proof so an operations payload missing
    Project fails before a run/checkpoint/tool/approval record is created.

- [ ] **Step 2: Run the focused server tests and confirm they fail**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_conversation_project_context.py tests/apps/cosa/worker/test_project_scoped_agent_run.py -q

    Expected: FAIL because ConversationCreate has no project_id, MessageCreate
    accepts no Project, and conversation_routes resolves a workspace Project
    after persisting a message.

- [ ] **Step 3: Add one reusable Company-backed Project verifier**

    Implement apps/cosa/api/project_context.py. It validates non-empty
    project_id, calls the existing Company Project read boundary with the
    authenticated workspace and delegation, and returns only verified Project
    metadata. Map invalid/missing to a typed 422 response and unknown/foreign
    Project to one typed 404 response. Do not use Project title, client local
    storage, a generic workspace list or an exception string as authorization.

    Reuse this verifier from conversation routes, run cancel/events and the
    later Activity Feed routes. Keep it at the API composition layer; do not
    put Company authorization into packages/agent.

- [ ] **Step 4: Remove fallback and make all conversation paths Project-scoped**

    Remove _resolve_workspace_project_id and its use. Require project_id in
    ConversationCreate and MessageCreate. Persist a Project-scoped
    ConversationRecord first; for message creation verify:

        request project_id == conversation.project_id == verified Project

    before minting delegation, adding MessageRecord, starting SSE state or
    scheduling work. Create RunRecord and scheduler payload with the same
    project_id. Pass the Project into worker preparation and reject mismatches
    before kernel execution. List/get/update conversations and run event/cancel
    endpoints must resolve the stored Project and verify it, rather than relying
    only on workspace_id.

    Return stable machine-readable errors:

        422 {detail: {code: PROJECT_CONTEXT_REQUIRED}}
        422 {detail: {code: PROJECT_CONTEXT_MISMATCH}}
        404 {detail: {code: PROJECT_NOT_FOUND_OR_FORBIDDEN}}

- [ ] **Step 5: Make the generic chat transport explicit**

    Change AgentChatService signatures so callers cannot omit Project:

        Future<ChatConversation?> createConversation({
          required String projectId,
          required String title,
          required String activeAgentProfile,
        })

        Future<Map<String, dynamic>?> sendMessage(
          String conversationId, {
          required String projectId,
          required String content,
          required MessageDataAccess dataAccess,
        })

    Keep project_id in the request body even when a conversation path also
    identifies it. Update existing ChatController callers to supply the active
    Project or surface a local Project-required state without dispatching.

- [ ] **Step 6: Run focused proof**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_conversation_project_context.py tests/apps/cosa/test_routes.py tests/apps/cosa/worker/test_project_scoped_agent_run.py -q

    Run: cd frontend && flutter test test/modules/chat/chat_module_test.dart test/founder_command_center_chat_test.dart

    Expected: PASS. Omitted/mismatched/cross-tenant context causes no persisted
    message or scheduled run; every accepted generic chat request carries its
    Project on the wire.

- [ ] **Step 7: Commit the fail-closed execution boundary**

    git add apps/cosa/api/project_context.py apps/cosa/api/conversation_routes.py apps/cosa/api/routes.py apps/cosa/api/schemas.py apps/cosa/worker/handlers.py frontend/lib/modules/chat/services/agent_chat_service.dart tests/apps/cosa/api/test_conversation_project_context.py tests/apps/cosa/test_routes.py tests/apps/cosa/worker/test_project_scoped_agent_run.py frontend/test/modules/chat/chat_module_test.dart frontend/test/founder_command_center_chat_test.dart
    git commit -m "feat: require project context for hub runs"

### Task 3: Build the durable Project Activity projection for runtime activity

**Files:**

- Create: packages/agent/migrations/005_project_activity_feed.sql
- Create: packages/agent/migrations/005_project_activity_feed.down.sql
- Create: packages/agent/project_activity/__init__.py
- Create: packages/agent/project_activity/models.py
- Create: packages/agent/project_activity/repository.py
- Create: apps/cosa/project_activity/service.py
- Modify: apps/cosa/composition/agent_plane.py
- Modify: apps/cosa/composition/storage_factory.py
- Modify: apps/cosa/api/event_stream.py
- Modify: apps/cosa/api/conversation_routes.py
- Modify: apps/cosa/api/routes.py
- Create: tests/agent/project_activity/test_repository.py
- Create: tests/apps/cosa/project_activity/test_runtime_projection.py

**Interfaces:**

- Produces ProjectActivityEventRecord and ProjectActivityRepository.
- Produces append_if_absent(event) -> ProjectActivityEventRecord, where a duplicate source event returns the original row and does not consume a new project_sequence.
- Produces ProjectActivityService.record_runtime_event with a safe event vocabulary and redacted summary.

- [ ] **Step 1: Write failing durable projection tests**

    Use a real repository fixture plus the in-memory implementation:

        first = await repo.append_if_absent(event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_1:run.queued:1",
            source_type="run",
            source_id="run_1",
            source_version="1",
            kind="run.queued",
        ))
        duplicate = await repo.append_if_absent(same_event)
        second = await repo.append_if_absent(event(
            workspace_id="ws_a",
            project_id="proj_a",
            idempotency_key="run:run_2:run.started:1",
            source_type="run",
            source_id="run_2",
            source_version="1",
            kind="run.started",
        ))
        assert duplicate.project_sequence == first.project_sequence == 1
        assert second.project_sequence == 2

    Add redaction coverage: an event containing input_payload, raw_secret or
    access_token has none of those keys in its summary/detail projection.
    Add an isolation assertion that the same sequence checkpoint for proj_a
    cannot list proj_b.

- [ ] **Step 2: Run the focused tests and confirm they fail**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/agent/project_activity/test_repository.py tests/apps/cosa/project_activity/test_runtime_projection.py -q

    Expected: FAIL because no Project Activity schema, repository or runtime
    projection exists.

- [ ] **Step 3: Add projection persistence with idempotency before sequencing**

    Migration 005 creates:

        agent.project_activity_idempotency
        agent.project_activity_sequences
        agent.project_activity_events

    project_activity_events must contain event_id, workspace_id, project_id,
    project_sequence, kind, phase, status, actor_kind, actor_id,
    correlation_id, source_type, source_id, source_version, summary,
    classification, payload_hash, occurred_at and recorded_at. It must not
    contain raw prompt/content/Vault/tool payload columns.

    Implement append_if_absent in one transaction:

    1. claim idempotency_key in project_activity_idempotency;
    2. if already claimed, read and return the original event;
    3. increment exactly one workspace_id/project_id cursor;
    4. insert the event with that project_sequence;
    5. commit all four operations together.

    The down migration must refuse when any activity event exists.

- [ ] **Step 4: Map runtime sources into safe activity events**

    In ProjectActivityService, map only durable runtime facts:

        chat.accepted
        run.queued
        run.started
        run.checkpointed
        run.waiting_approval
        tool.requested
        tool.policy_allowed
        tool.policy_denied
        approval.requested
        approval.resolved
        run.completed
        run.failed
        run.cancelled

    Derive source ID/version from the persisted message/run/checkpoint/tool/
    approval record. Use the existing UX redaction policy plus a stricter
    allowlist for summary. Unknown runtime events produce a redacted
    system-delivery activity row with a hash/reference, never arbitrary raw
    payload.

    Wire the service through CosaAgentPlane and storage_factory. Record
    chat.accepted and run.queued only after their canonical records are
    persisted. Extend CosaEventStreamManager so a durable runtime event also
    creates an idempotent Project Activity event before live fanout.

- [ ] **Step 5: Run focused proof**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/agent/project_activity/test_repository.py tests/apps/cosa/project_activity/test_runtime_projection.py tests/apps/cosa/test_event_stream.py -q

    Expected: PASS. Duplicate delivery leaves sequence intact; a runtime event
    remains queryable after a fresh repository instance; sensitive fields are
    absent from projection.

- [ ] **Step 6: Commit the runtime projection**

    git add packages/agent/migrations/005_project_activity_feed.sql packages/agent/migrations/005_project_activity_feed.down.sql packages/agent/project_activity apps/cosa/project_activity apps/cosa/composition/agent_plane.py apps/cosa/composition/storage_factory.py apps/cosa/api/event_stream.py apps/cosa/api/conversation_routes.py apps/cosa/api/routes.py tests/agent/project_activity tests/apps/cosa/project_activity tests/apps/cosa/test_event_stream.py
    git commit -m "feat: persist project activity from runtime events"

### Task 4: Project Company facts into Activity Feed through the signed outbox

**Files:**

- Modify: services/company/shared/events/envelope.ts
- Modify: services/company/shared/events/event-types.ts
- Modify: services/company/operations/services/task-events.service.ts
- Modify: services/company/operations/services/work-package.service.ts
- Modify: services/company/operations/services/work-package-review.service.ts
- Modify: services/company/operations/services/execution-outcome.service.ts
- Modify: services/company/operations/strategy/services/project-action-context.service.ts
- Modify: services/company/shared/events/outbox.repository.ts
- Modify: apps/cosa/api/event_rule_routes.py
- Create: apps/cosa/project_activity/company_event_projector.py
- Create: services/company/shared/events/tests/project_activity_envelope.test.ts
- Modify: services/company/operations/tests/event-outbox.test.ts
- Create: tests/apps/cosa/project_activity/test_company_event_projector.py

**Interfaces:**

- Produces ProjectActivityBusinessEventEnvelope, a Company outbox event with projectId, source reference and restricted-safe payload.
- Produces project_activity_company_event_projector.consume(envelope) that writes only the Agent projection and returns accepted, duplicate or rejected.
- Produces Project-scoped Company facts for task, work package, decision, evidence and risk events sent to the existing signed internal event intake.

- [ ] **Step 1: Write failing Company and intake tests**

    Verify Company rejects a Hub-visible event with no projectId:

        expect(() => makeBusinessEvent({
          eventType: "operations.task.created.v1",
          workspaceId: "ws_a",
          aggregateType: "task",
          aggregateId: "task_a",
          correlationId: "corr_a",
          actor: { kind: "user", id: "human_a" },
          classification: "internal",
          payload: { taskId: "task_a" },
        })).toThrow(/projectId/)

    Verify a valid task event retains only Project-safe data after relay:

        const event = makeBusinessEvent({
          eventType: "operations.task.completed.v1",
          workspaceId: "ws_a",
          projectId: "proj_a",
          aggregateType: "task",
          aggregateId: "task_a",
          correlationId: "corr_a",
          actor: { kind: "user", id: "human_a" },
          classification: "restricted",
          payload: { task_id: "task_a", project_id: "proj_a", evidence_ref: "ev_1" },
        });

    In the Agent test, send this signed envelope twice and assert one activity
    event with kind task.completed, Project A and the same correlation ID.
    Send an envelope for Project B and assert a Project A feed query returns
    neither its source nor its summary.

- [ ] **Step 2: Run focused tests and confirm they fail**

    Run: cd services/company && encore test shared/events/tests/project_activity_envelope.test.ts operations/tests/event-outbox.test.ts

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/project_activity/test_company_event_projector.py -q

    Expected: FAIL because the business envelope has no Project contract and
    the signed intake does not project Company facts.

- [ ] **Step 3: Version and validate Project-bearing business events**

    Extend BusinessEventEnvelope and BusinessEventInput with optional projectId
    only for generic infrastructure compatibility, then enforce projectId for
    every event type that can appear in Founder Hub Activity Feed. Add
    project-scoped versions of task, work-package, decision, evidence and risk
    event types in event-types.ts. Validation must reject an event type in that
    set without projectId and reject a payload project_id that disagrees with
    envelope projectId.

    Update named service producers to obtain Project from the canonical business
    record inside their transaction, not from UI input. Append the event in the
    existing Company transaction/outbox path. Retain Company truth; do not add
    an Agent DB write to any Company service.

- [ ] **Step 4: Consume at the existing signed Agent intake**

    In event_rule_routes.py, after signature and envelope validation, route the
    Project-bearing Hub event types to company_event_projector. The projector
    validates source type/classification, creates a redacted summary and calls
    ProjectActivityRepository.append_if_absent using Company eventId as the
    idempotency key. Return duplicate for replayed delivery and rejected for a
    missing/mismatched Project payload. Do not inspect Company tables from
    apps/cosa.

- [ ] **Step 5: Run focused proof**

    Run: cd services/company && encore test shared/events/tests/project_activity_envelope.test.ts operations/tests/event-outbox.test.ts operations/tests/work-package-dispatch.test.ts

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/project_activity/test_company_event_projector.py tests/apps/cosa/events/test_event_worker_contract.py -q

    Expected: PASS. Transaction rollback emits no activity source; successful
    relay projects once; duplicate delivery does not increment sequence; foreign
    Project data remains isolated.

- [ ] **Step 6: Commit the Company-to-projection bridge**

    git add services/company/shared/events services/company/operations/services/task-events.service.ts services/company/operations/services/work-package.service.ts services/company/operations/services/work-package-review.service.ts services/company/operations/services/execution-outcome.service.ts services/company/operations/strategy/services/project-action-context.service.ts services/company/operations/tests/event-outbox.test.ts apps/cosa/api/event_rule_routes.py apps/cosa/project_activity/company_event_projector.py services/company/shared/events/tests/project_activity_envelope.test.ts tests/apps/cosa/project_activity/test_company_event_projector.py
    git commit -m "feat: project company events into founder activity"

### Task 5: Expose authorized Activity Feed read, detail and resume stream APIs

**Files:**

- Create: apps/cosa/api/project_activity_routes.py
- Modify: apps/cosa/api/app.py
- Modify: apps/cosa/api/schemas.py
- Modify: apps/cosa/api/event_stream.py
- Modify: apps/cosa/api/mvp_contracts_generated.py
- Create: tests/apps/cosa/api/test_project_activity_routes.py
- Modify: tests/apps/cosa/test_sse_reconnect_e2e.py
- Modify: tests/apps/cosa/test_router_registration.py
- Modify: tests/quality/test_generated_mvp_contracts.py

**Interfaces:**

- Produces GET /agent/projects/{project_id}/activity with after_project_sequence, limit and kinds filters.
- Produces GET /agent/projects/{project_id}/activity/{event_id}.
- Produces GET /agent/projects/{project_id}/activity/stream with Last-Event-ID or after_project_sequence resume.
- Produces ProjectActivityEventDTO and ProjectActivityDetailDTO, each carrying workspace_id, project_id, project_sequence, correlation_id and safe fields.

- [ ] **Step 1: Write failing route/security/reconnect tests**

    Add a route test where Project A has two events and Project B has one:

        response = await client.get(
            "/agent/projects/proj_a/activity?after_project_sequence=1",
            headers=auth_headers("ws_a"),
        )
        assert response.status_code == 200
        body = response.json()
        assert [item["project_sequence"] for item in body["items"]] == [2]
        assert all(item["project_id"] == "proj_a" for item in body["items"])

    Add detail tests that a user with Project access but without source
    visibility receives a redacted source reference, not the original payload.
    Add unknown/cross-tenant Project tests returning
    PROJECT_NOT_FOUND_OR_FORBIDDEN. Extend the process-restart SSE test to
    read one Project activity event, kill the process, reconnect with
    Last-Event-ID and assert only later Project A sequence values arrive.

- [ ] **Step 2: Run the focused tests and confirm they fail**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_project_activity_routes.py tests/apps/cosa/test_sse_reconnect_e2e.py tests/apps/cosa/test_router_registration.py -q

    Expected: FAIL because no Project Activity routes, DTOs or Project-level
    replay stream exist.

- [ ] **Step 3: Implement feed list and inspector detail**

    Register project_activity_routes in app.py. Every route first calls
    verify_project_context. List queries use workspace_id and project_id in the
    repository, sort only by project_sequence, and cap limit at 100.

    Detail fetches the activity row and rechecks visibility of its source:

        - conversation/message/run sources use scoped runtime repositories;
        - task/decision/evidence sources retain a typed reference and Company
          authorization result;
        - missing or unauthorized source returns safe redacted metadata.

    Never put a raw source object into the Activity DTO. Return integrity hash,
    source type/ID/version, status, actor and safe summary.

- [ ] **Step 4: Implement durable Project stream**

    Add a Project Activity stream manager distinct from the existing per-run
    SSE manager. Its source of truth is ProjectActivityRepository list_since;
    in-memory queues only wake live subscribers. Stream format uses
    project_sequence as SSE ID. On reconnect, replay rows with sequence greater
    than Last-Event-ID before live fanout. Include heartbeat comments and do
    not close on temporary idle.

    Reject Last-Event-ID values that are not positive integers. The stream
    payload must include project_id so the Flutter client can discard an event
    that arrives after a Project switch.

- [ ] **Step 5: Verify contract generation and focused behavior**

    Run: node scripts/gen-mvp-contracts.mjs

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/api/test_project_activity_routes.py tests/apps/cosa/test_sse_reconnect_e2e.py tests/apps/cosa/test_router_registration.py tests/quality/test_generated_mvp_contracts.py -q

    Expected: PASS. Restart/reconnect has no duplicate/gap; detail redacts
    restricted source; API does not leak foreign Project existence.

- [ ] **Step 6: Commit Activity Feed API**

    git add apps/cosa/api/project_activity_routes.py apps/cosa/api/app.py apps/cosa/api/schemas.py apps/cosa/api/event_stream.py apps/cosa/api/mvp_contracts_generated.py tests/apps/cosa/api/test_project_activity_routes.py tests/apps/cosa/test_sse_reconnect_e2e.py tests/apps/cosa/test_router_registration.py tests/quality/test_generated_mvp_contracts.py shared/contracts/mvp-surface.json services/company/shared/contracts/mvp-surface.generated.ts
    git commit -m "feat: expose project activity feed"

### Task 6: Make Flutter selection, chat and activity clients explicitly Project-scoped

**Files:**

- Create: frontend/lib/modules/hologram_hub/models/project_activity_models.dart
- Create: frontend/lib/modules/hologram_hub/services/active_project_store.dart
- Create: frontend/lib/modules/hologram_hub/services/project_activity_service.dart
- Modify: frontend/lib/modules/chat/models/chat_models.dart
- Modify: frontend/lib/modules/chat/services/agent_chat_service.dart
- Modify: frontend/lib/modules/chat/controllers/chat_controller.dart
- Modify: frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart
- Modify: frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart
- Modify: frontend/lib/core/network/realtime_service.dart
- Create: frontend/test/modules/hologram_hub/services/active_project_store_test.dart
- Create: frontend/test/modules/hologram_hub/services/project_activity_service_test.dart
- Modify: frontend/test/modules/hologram_hub/founder_command_center_controller_test.dart
- Modify: frontend/test/founder_command_center_chat_test.dart
- Modify: frontend/test/core/network/realtime_service_lifecycle_test.dart

**Interfaces:**

- Produces ActiveProjectStore.read(workspaceId), write(workspaceId, projectId) and clear(workspaceId). Its key is active_project_id:<workspaceId>.
- Produces ProjectActivityService.fetch(projectId, afterSequence, kinds) and stream(projectId, afterSequence).
- Produces FounderCommandCenterController.selectProject(projectId) and a Project generation token independent from workspace generation.

- [ ] **Step 1: Write failing Flutter tests**

    Cover restoration and no-first-Project behavior:

        SharedPreferences.setMockInitialValues({
          'workspace_id': 'ws_1',
          'active_project_id:ws_1': 'proj_b',
        });
        await controller.loadDashboardData();
        expect(controller.activeProjectId.value, 'proj_b');

        SharedPreferences.setMockInitialValues({'workspace_id': 'ws_1'});
        await controller.loadDashboardData();
        expect(controller.activeProjectId.value, isNull);
        expect(controller.requiresProjectSelection.value, isTrue);

    Add a chat transport test whose POST body contains project_id in both
    create conversation and send message. Add a Project-switch race test:
    start a Project A fetch/stream, select B, complete A late, then assert
    Project A message/activity/KPI is not inserted into B state.

- [ ] **Step 2: Run focused Flutter tests and confirm they fail**

    Run: cd frontend && flutter test test/modules/hologram_hub/services/active_project_store_test.dart test/modules/hologram_hub/services/project_activity_service_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart test/founder_command_center_chat_test.dart test/core/network/realtime_service_lifecycle_test.dart

    Expected: FAIL because no active Project store/activity client exists and
    the controller selects projects.first.

- [ ] **Step 3: Add local Project restoration without authority**

    Implement ActiveProjectStore using SecureStorageService read/write/delete
    for non-secret storage. It stores only the ID, namespaced by Workspace.
    In FounderCommandCenterController:

    1. load authorized Project list;
    2. read local selected ID;
    3. select it only if present in that response;
    4. otherwise clear the key and set requiresProjectSelection true;
    5. never select the first Project.

    selectProject must cancel Project-level subscriptions, increment a
    project generation counter, clear visible Project-derived state, persist the
    new ID, then load only that Project's snapshot/activity. Workspace switch
    and logout also clear Project state and cancel its subscriptions.

- [ ] **Step 4: Make every Hub client Project-aware**

    Add immutable projectId to ChatConversation, message/run responses and
    ProjectActivityEvent models. AgentChatService must send project_id
    explicitly. ProjectActivityService uses only the generated contract paths
    from Task 5 and sends Last-Event-ID/project sequence on reconnect.

    Change CoFounderApiService signatures so getCompanyPulse,
    listPendingDecisions and every Hub KPI/read call require projectId. Add the
    Project selector to task/decision query parameters only when their Company
    endpoint contract confirms Project filtering; otherwise replace the call
    with a Project Operating Loop or Activity Feed projection already scoped by
    Project. Do not retain a workspace-wide fallback that makes Project KPI
    visually incorrect.

    RealtimeService must keep a checkpoint per workspace and Project, and
    discard events whose workspace/project do not match its active subscription.

- [ ] **Step 5: Run focused Flutter proof**

    Run: cd frontend && flutter test test/modules/hologram_hub/services/active_project_store_test.dart test/modules/hologram_hub/services/project_activity_service_test.dart test/modules/hologram_hub/founder_command_center_controller_test.dart test/founder_command_center_chat_test.dart test/core/network/realtime_service_lifecycle_test.dart test/modules/chat/chat_module_test.dart

    Expected: PASS. A missing/stale local ID does not select another Project;
    messages and activity requests include Project; late Project A data cannot
    contaminate Project B.

- [ ] **Step 6: Commit the Flutter scope boundary**

    git add frontend/lib/modules/hologram_hub/models/project_activity_models.dart frontend/lib/modules/hologram_hub/services/active_project_store.dart frontend/lib/modules/hologram_hub/services/project_activity_service.dart frontend/lib/modules/chat/models/chat_models.dart frontend/lib/modules/chat/services/agent_chat_service.dart frontend/lib/modules/chat/controllers/chat_controller.dart frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart frontend/lib/core/network/realtime_service.dart frontend/test/modules/hologram_hub/services frontend/test/modules/hologram_hub/founder_command_center_controller_test.dart frontend/test/founder_command_center_chat_test.dart frontend/test/core/network/realtime_service_lifecycle_test.dart frontend/test/modules/chat/chat_module_test.dart
    git commit -m "feat: scope flutter hub to active project"

### Task 7: Recompose Hub as a truthful Project Execution Console

**Files:**

- Create: frontend/lib/modules/hologram_hub/widgets/project_context_bar.dart
- Create: frontend/lib/modules/hologram_hub/widgets/project_activity_timeline.dart
- Create: frontend/lib/modules/hologram_hub/widgets/project_activity_inspector.dart
- Modify: frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/chat_panel_content.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/hub_activity_timeline_card.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/command_center_workforce_sidebar.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/agent_direct_chat_sheet.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart
- Modify: frontend/lib/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart
- Modify: frontend/lib/core/routing/app_pages.dart
- Modify: frontend/lib/core/localization/locales/vi/vi_strategy.dart
- Modify: frontend/lib/core/localization/locales/en/en_strategy.dart
- Modify: frontend/lib/core/localization/app_translations.dart
- Delete: frontend/lib/modules/hologram_hub/widgets/draggable_chat_panel.dart
- Modify: frontend/test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart
- Modify: frontend/test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart
- Create: frontend/test/modules/hologram_hub/widgets/project_context_bar_test.dart
- Create: frontend/test/modules/hologram_hub/widgets/project_activity_timeline_test.dart
- Create: frontend/test/modules/hologram_hub/widgets/project_activity_inspector_test.dart

**Interfaces:**

- Produces ProjectContextBar(projects, selectedProjectId, onSelected).
- Produces ProjectActivityTimeline(events, onSelectEvent, filters, loading, unavailable) and ProjectActivityInspector(eventId, projectId).
- Produces a fixed central ChatPanelContent bound to the selected Project; it is no longer a floating/draggable primary control.

- [ ] **Step 1: Write failing widget tests from the approved interaction**

    Add a Project picker test:

        await tester.tap(find.byKey(const Key('project_context_selector')));
        await tester.tap(find.text('Project B'));
        await tester.pump();
        expect(find.textContaining('Project: Project B'), findsOneWidget);
        expect(find.text('Company-wide'), findsNothing);

    Add an empty-context test asserting chat composer, agent direct chat,
    approval actions, Top 3 and KPI action controls are disabled until a Project
    is selected. Add timeline test with one completed run and one pending
    approval; tapping approval opens an inspector containing source ID and
    correlation ID but not a raw token/prompt. Add fixed-chat test asserting
    ChatPanelContent is visible in the central Hub layout without opening a
    draggable panel.

- [ ] **Step 2: Run focused widget tests and confirm they fail**

    Run: cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart test/modules/hologram_hub/widgets/project_context_bar_test.dart test/modules/hologram_hub/widgets/project_activity_timeline_test.dart test/modules/hologram_hub/widgets/project_activity_inspector_test.dart

    Expected: FAIL because the Hub has Company-wide copy, a floating/draggable
    chat route and session-composed HubActivityTimelineCard.

- [ ] **Step 3: Replace Company-wide context with a Project selector**

    Render ProjectContextBar in the Hub header with Workspace name, exact
    selected Project and lifecycle stage. It has no All or Company-wide option.
    The no-selection state gives a clear Project picker/loading/error state and
    does not render operational content. Route /hub continues to require
    Project setup, but no route or route argument may manufacture a Project
    selection.

    Update Vietnamese and English catalogs for Project context, Project-required
    state, timeline filters, activity unavailable and inspector privacy copy.
    Remove any Company-wide label/copy from the Hub rather than renaming it.

- [ ] **Step 4: Make chat and workforce fixed and Project-bound**

    Put ChatPanelContent in the central content column with a header:

        Chat with Co-Founder and selected Project

    Disable composer and agent direct chat if selectedProjectId is null. Pass
    selectedProjectId into every message/run/agent direct chat action. Replace
    fallback agent cards with real assigned/available state or an explicit
    unavailable state; do not fill the left rail with synthetic online agents.

    Remove DraggableChatPanel and the floating voice/chat primary action from
    HologramHubView only after all imports, route tests and accessibility focus
    behavior are transferred to the fixed composer. Keep unrelated consumer
    surfaces unchanged if they use those widgets outside Hub.

- [ ] **Step 5: Replace session-composed timeline with Activity Feed**

    HubActivityTimelineCard must no longer derive rows from chatMessages,
    FounderInboxTask or ExecutionPlan. Either remove it after callers migrate
    or reduce it to an adapter around ProjectActivityTimeline with no local
    event synthesis.

    ProjectActivityTimeline groups/filter events by Chat, Run, Tool, Approval,
    Decision, Task and Risk; it renders time, actor, status and source-safe
    summary. It subscribes only to ProjectActivityService and opens
    ProjectActivityInspector for details. Empty state means the durable feed
    returned no rows; unavailable state is distinct from empty.

    Top 3, KPI and Project Operating Loop link must use selectedProjectId.
    The Project Operating Loop navigation path includes that exact ID. Any
    Company-wide decision/task request discovered during implementation must be
    removed from Hub or replaced with its Project-scoped counterpart; do not
    retain it as a hidden fallback.

- [ ] **Step 6: Run focused Flutter verification**

    Run: cd frontend && flutter test test/modules/hologram_hub/hologram_hub_view_chat_panel_test.dart test/modules/hologram_hub/hub_hides_widgets_without_projects_test.dart test/modules/hologram_hub/widgets/project_context_bar_test.dart test/modules/hologram_hub/widgets/project_activity_timeline_test.dart test/modules/hologram_hub/widgets/project_activity_inspector_test.dart test/modules/hologram_hub/widgets/top3_focus_widget_checklist_test.dart

    Run: cd frontend && flutter analyze

    Expected: PASS. Hub has no Company-wide mode, no primary floating chat,
    no fake activity, and Project A never renders Project B data.

- [ ] **Step 7: Commit the Hub composition**

    git add frontend/lib/modules/hologram_hub frontend/lib/core/routing/app_pages.dart frontend/lib/core/localization frontend/test/modules/hologram_hub
    git rm frontend/lib/modules/hologram_hub/widgets/draggable_chat_panel.dart
    git commit -m "feat: make hub a project execution console"

### Task 8: Prove cross-plane durability, isolation and release readiness

**Files:**

- Create: tests/e2e/test_project_scoped_founder_hub.py
- Modify: tests/e2e/test_cross_plane_smoke.py
- Modify: tests/quality/test_frontend_api_contracts.py
- Modify: tests/contracts/test_startup_core_mvp_surface.py
- Modify: docs/superpowers/specs/2026-09-11-project-scoped-founder-hub-design.md
- Modify: docs/superpowers/plans/2026-09-11-project-scoped-founder-hub.md

**Interfaces:**

- Produces a disposable-Postgres/process proof for Project select -> chat -> durable run -> Company/outbox activity -> reconnect -> inspector detail.
- Produces release evidence that no new Hub operational record is unscoped and no contract/UI path claims Company-wide behavior.

- [ ] **Step 1: Write the cross-plane acceptance scenario**

    Create two Projects in one workspace and a second workspace. The scenario
    must:

    1. select Project A and create a Project-scoped conversation/message;
    2. verify a durable run and runtime activity carry ws_a/proj_a;
    3. emit a Company task or decision event for proj_a through signed outbox;
    4. consume the activity stream, record its sequence, restart the API
       process and reconnect after that sequence;
    5. verify later Project A events resume exactly once;
    6. request Project B and foreign workspace data and verify isolation;
    7. attempt missing/mismatched Project chat and verify no side effect;
    8. verify activity detail hides a restricted source payload;
    9. load the Flutter contract fixture and assert the same Project is sent on
       every command.

    Use process boundaries and disposable Postgres; do not substitute an
    in-memory repository for restart/replay proof.

- [ ] **Step 2: Run the scenario and confirm it fails**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/e2e/test_project_scoped_founder_hub.py -q

    Expected: FAIL until all layers have Project propagation, projection,
    authorized SSE and Flutter contract enforcement.

- [ ] **Step 3: Add release-contract guards**

    Extend contract/quality tests to assert:

        - every Hub command capability has requires_project true;
        - generated Python/TypeScript contracts match JSON;
        - no Founder Hub endpoint or Flutter client uses a Company-wide mode;
        - no Founder Hub endpoint references a GitHub adapter;
        - UI test fixtures cannot post a chat message without project_id.

    Do not make a broad string-ban across the repository; Company administration,
    billing and unrelated documentation are outside Hub. Scope the guard to Hub
    routes, Hub widgets/controllers and Hub MVP capabilities.

- [ ] **Step 4: Update implementation status only with evidence**

    Change the Hub design status from DRAFT to IMPLEMENTED only after all
    acceptance tests in this task pass. Record exact commands, date, commit and
    known external limitations in the design/plan execution section. Do not
    claim WIRED, VERIFIED or PRODUCTION from static tests alone.

- [ ] **Step 5: Run targeted and aggregate gates**

    Run: PYTHONPATH=. .venv/bin/python -m pytest tests/contracts/test_startup_core_mvp_surface.py tests/quality/test_frontend_api_contracts.py tests/e2e/test_project_scoped_founder_hub.py tests/e2e/test_cross_plane_smoke.py -q

    Run: make apps-cosa-test

    Run: make services-test-company

    Run: make frontend-test

    Run: make frontend-analyze

    Run: make e2e-cross-plane-smoke

    Expected: all targeted gates pass. If an existing baseline failure prevents
    a broad gate, record the full command, failure ownership and unchanged
    targeted evidence; do not relabel the feature verified.

- [ ] **Step 6: Commit release evidence**

    git add tests/e2e/test_project_scoped_founder_hub.py tests/e2e/test_cross_plane_smoke.py tests/quality/test_frontend_api_contracts.py tests/contracts/test_startup_core_mvp_surface.py docs/superpowers/specs/2026-09-11-project-scoped-founder-hub-design.md docs/superpowers/plans/2026-09-11-project-scoped-founder-hub.md
    git commit -m "test: prove project scoped founder hub"

## Plan self-review

### Spec coverage

| Spec requirement | Plan task |
| --- | --- |
| Remove Company-wide and never auto-select Project | Tasks 1, 6, 7 and 8 |
| Local active Project is UX only | Task 6 |
| Project mandatory for Hub artifacts and no fallback | Tasks 1 and 2 |
| Conversation immutable by Project and legacy preservation | Tasks 1 and 2 |
| Durable, redacted, replayable timeline | Tasks 3 and 5 |
| Company truth reaches feed through outbox, not direct DB | Task 4 |
| Fixed chat, Project-bound workforce/KPI/loop UI | Tasks 6 and 7 |
| Tenancy, switching races, restart/reconnect and redaction proof | Tasks 2, 5, 6 and 8 |
| No GitHub/Buzz collaboration surface | Tasks 1, 7 and 8 |

### Placeholder scan

The plan has no deferred implementation markers. Every task defines exact files,
interfaces, test command, expected failure, implementation boundary, proof and
commit scope.

### Type consistency

Project identity is named project_id at API/persistence boundaries and projectId
in Dart/TypeScript client models. ProjectActivityEventDTO carries
project_sequence, while SSE uses that same value as Last-Event-ID. All Project
read/write paths use workspace_id plus project_id and never use workspace-only
selection as a substitute.
