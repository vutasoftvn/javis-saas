# Wave 1 DeepSeek Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mock worker with a tenant-safe DeepSeek chat runtime that streams persisted output to Flutter and records workspace-scoped usage.

**Architecture:** `backend/app` owns a provider-neutral AI router and a DeepSeek adapter. The worker claims durable chat work and saves every state transition to Postgres; a tenant-scoped SSE endpoint exposes that persisted state to Flutter. Flutter remains an API-only client and uses HTTP history to recover a disconnected stream.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, httpx, sse-starlette, PostgreSQL, Flutter/Dart, flutter_test.

## Global Constraints

- Default provider is `deepseek`; default model is `deepseek-chat`.
- Only backend runtime receives `DEEPSEEK_API_KEY`; Flutter never sends provider, model, base URL, usage or credentials.
- `javis/` and `backend/server/` are reference only and cannot become runtime dependencies.
- Every query carrying a brain, chat session, message or run ID validates workspace ownership server-side.
- New runtime state is Postgres/MinIO only; do not add SQLite files.
- Do not log provider request headers, API keys, or raw provider error bodies.

---

### Task 1: Add durable chat-run schema and provider settings

**Files:**
- Create: `backend/alembic/versions/c4a1b9e8d2f0_add_chat_ai_run_fields.py`
- Modify: `backend/app/db/models.py:566-577`
- Modify: `.env.example`
- Test: `backend/app/tests/test_ai_run_model.py`

**Interfaces:**
- Produces: `AIRun.workspace_id: UUID`, `chat_session_id: UUID | None`, `chat_message_id: UUID | None`, `status: str`, `input_tokens: int | None`, `output_tokens: int | None`, `error_code: str | None`, `started_at: datetime`, and `finished_at: datetime | None`.
- Produces: backend-only environment variables `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL=https://api.deepseek.com`, and `DEEPSEEK_DEFAULT_MODEL=deepseek-chat`.

- [ ] **Step 1: Write failing model tests**

Create a model test which constructs an `AIRun` with a workspace, chat session,
message, token counts and `completed` status, then asserts these fields retain
their hand-written values.

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_ai_run_model.py -q`
Expected: FAIL because the chat-run fields do not exist.

- [ ] **Step 3: Add the migration and SQLAlchemy fields**

Add nullable foreign keys for chat session/message, a non-null workspace foreign
key, status and usage/error/timestamp fields. Backfill existing `ai_runs`
workspace-less records as unavailable only if migration safety requires it; do
not infer an owner from a workflow. Add explicit indexes for workspace and
chat message lookup.

- [ ] **Step 4: Add safe environment documentation**

Add only empty/example DeepSeek variables to `.env.example`; never add a real
credential or a fallback API key.

- [ ] **Step 5: Verify the model test**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_ai_run_model.py -q`
Expected: PASS.

### Task 2: Implement the DeepSeek adapter and AI router

**Files:**
- Create: `backend/app/integrations/deepseek_client.py`
- Create: `backend/app/services/ai_router.py`
- Test: `backend/app/tests/test_deepseek_client.py`

**Interfaces:**
- Produces: `ChatTurn(role: str, content: str)` and `AIEvent(kind: Literal["delta", "completed", "failed"], content: str = "", input_tokens: int | None = None, output_tokens: int | None = None, error_code: str | None = None)`.
- Produces: `AIRouter.stream_chat(turns: list[ChatTurn]) -> AsyncIterator[AIEvent]`.

- [ ] **Step 1: Write failing adapter tests**

Use `httpx.MockTransport` to feed OpenAI-compatible SSE chunks. Assert the
router emits two literal delta events, then one completed event with the usage
counts from the provider payload. Add a separate test that no API key produces
one `failed` event with `error_code == "provider_not_configured"`.

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_deepseek_client.py -q`
Expected: FAIL because the router and adapter do not exist.

- [ ] **Step 3: Implement the adapter**

Use `httpx.AsyncClient` with the DeepSeek base URL from environment. Send
`deepseek-chat` unless the backend environment changes the default. Convert
the OpenAI-compatible stream into the defined events; map transport failures
to safe error codes without retaining response body text.

- [ ] **Step 4: Verify the adapter tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_deepseek_client.py -q`
Expected: PASS.

### Task 3: Replace the mock worker with durable DeepSeek execution

**Files:**
- Modify: `backend/app/worker_main.py`
- Create: `backend/app/services/chat_execution_service.py`
- Test: `backend/app/tests/test_chat_execution_service.py`

**Interfaces:**
- Consumes: `AIRouter.stream_chat`, `ChatMessage`, `ChatSession`, and `AIRun`.
- Produces: `process_pending_chat_messages(db: Session, router: AIRouter) -> int`.

- [ ] **Step 1: Write failing execution tests**

With an in-memory fake router, create one `sent` user message and assert
`process_pending_chat_messages` transitions it to `processed`, creates one
assistant record with concatenated literal content, and creates one completed
`AIRun`. Add a provider failure case that creates an assistant `error`
message and failed run without a mock reply.

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_chat_execution_service.py -q`
Expected: FAIL because execution service does not exist.

- [ ] **Step 3: Implement message claiming and persistence**

Claim only `role == "user"` messages with `status == "sent"`; mark them
`processing` before provider work. Save a `streaming` assistant message,
append each delta durably, then mark it delivered/failed and persist the AI run
with the message's workspace resolved through its session brain. Do not process
the same client message twice.

- [ ] **Step 4: Point worker entrypoint at the service**

Replace `process_mock_ai` with the service call while retaining a clean
session lifecycle and sleep interval. Remove all mock response strings.

- [ ] **Step 5: Verify the execution tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_chat_execution_service.py -q`
Expected: PASS.

### Task 4: Expose tenant-scoped stream, model and usage APIs

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/api/ai.py`
- Modify: `backend/app/core/tenancy.py`
- Test: `backend/app/tests/test_chat_stream.py`
- Test: `backend/app/tests/test_ai_api.py`

**Interfaces:**
- Produces: `GET /api/v1/chat/{brain_id}/sessions/{session_id}/stream?workspace_id=` as `text/event-stream`.
- Produces: `GET /api/v1/ai/default-model?workspace_id=` returning `{"provider":"deepseek","model":"deepseek-chat"}`.
- Produces: `GET /api/v1/ai/runs?workspace_id=` returning only direct workspace-owned runs.

- [ ] **Step 1: Write failing API tests**

Assert a valid member receives streaming message snapshots and that a user from
another workspace receives 404 for the same session. Assert usage list returns
only the requesting workspace's run and default-model response ignores any
client model query parameter.

- [ ] **Step 2: Run the targeted tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_chat_stream.py app/tests/test_ai_api.py -q`
Expected: FAIL because stream/model endpoints and direct run scoping do not exist.

- [ ] **Step 3: Implement scoped helpers and SSE**

Add reusable scoped lookup helpers for ChatSession/ChatMessage. The SSE route
polls persisted assistant status/content at a short bounded interval, emits
`message` snapshots plus terminal `completed`/`failed` events, and ends
after a terminal state. It must never invoke the provider itself.

- [ ] **Step 4: Replace AI usage inference**

Query `AIRun.workspace_id == workspace_id` directly and serialize status,
token counts, cost, provider/model and timestamps. Return no cross-workspace
records even if a caller guesses an ID.

- [ ] **Step 5: Verify API tests**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_chat_stream.py app/tests/test_ai_api.py -q`
Expected: PASS.

### Task 5: Stream the backend response in Flutter

**Files:**
- Modify: `frontend/lib/data/services/chat_service.dart`
- Modify: `frontend/lib/modules/chat/controllers/chat_controller.dart`
- Modify: `frontend/lib/modules/chat/views/chat_view.dart`
- Create: `frontend/test/chat_stream_controller_test.dart`

**Interfaces:**
- Consumes: server-sent `message`, `completed`, and `failed` events from
  the chat stream endpoint.
- Produces: a visible streaming assistant bubble and a read-only active-model
  label.

- [ ] **Step 1: Write failing Flutter tests**

Inject a fake `ChatGateway` stream with two content snapshots followed by
`completed`; assert the controller displays the final literal assistant text
and clears `isSending`. Add a disconnect case whose gateway returns persisted
history, then assert the controller uses that history instead of legacy
WebSocket transport.

- [ ] **Step 2: Run the targeted Flutter test**

Run: `cd frontend && flutter test test/chat_stream_controller_test.dart`
Expected: FAIL because ChatGateway has no stream interface.

- [ ] **Step 3: Add API-only stream support**

Extend `ChatGateway` with a session stream implementation using HTTP SSE and
authorization headers. Update the controller to replace polling with stream
events, retain bounded history polling only after a stream disconnect, and
cancel subscriptions when changing session or closing the controller.

- [ ] **Step 4: Add the model label**

Load `/ai/default-model` through the existing API client and render the
server-supplied label as read-only in the Chat header. Do not add a model
selector in this wave.

- [ ] **Step 5: Verify Flutter tests and boundary**

Run: `cd frontend && flutter test && flutter analyze`

Run: `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib`

Expected: tests pass, analyze has no new issues from Wave 1, and the boundary
scan prints no matches.

### Task 6: Full verification and operational handoff

**Files:**
- Modify: `DEPLOYMENT.md`
- Modify: `docker-compose.yml`
- Test: `backend/app/tests/test_deepseek_client.py`
- Test: `frontend/test/chat_stream_controller_test.dart`

**Interfaces:**
- Produces: a documented DeepSeek backend-only runtime setup.

- [ ] **Step 1: Document configuration**

Document `DEEPSEEK_API_KEY` as required only by `agent-worker`; do not
place it in Flutter configuration or expose it through `brain-api`.

- [ ] **Step 2: Verify backend suite**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests -q`
Expected: PASS.

- [ ] **Step 3: Verify frontend suite and analysis**

Run: `cd frontend && flutter test && flutter analyze`
Expected: all tests pass; any pre-existing analyzer information must be listed
separately from Wave 1 changes.

- [ ] **Step 4: Verify deployment configuration**

Run: `docker compose config`
Expected: valid compose configuration with DeepSeek credential mounted only in
`agent-worker`.
