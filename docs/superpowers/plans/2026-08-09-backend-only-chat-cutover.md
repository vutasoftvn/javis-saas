# Backend-only Chat Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Flutter Chat use only the JavisOS `backend/app` API and remove every runtime dependency on the legacy Javis server.

**Architecture:** The backend remains the only service boundary for the client. Flutter persists and reads chat sessions/messages through `/api/v1/chat`, while the existing `agent-worker` creates assistant messages asynchronously. The client polls the same backend session for the worker result; no code in `frontend/` may refer to `javis/`, `backend/server`, or port 8888.

**Tech Stack:** Flutter/Dart, FastAPI, SQLAlchemy/PostgreSQL, pytest.

## Global Constraints

- `javis/` is reference and migration input only; it is not a runtime dependency.
- Flutter communicates only with `backend/app` through the versioned `/api/v1` HTTP API.
- Do not import, start, proxy, or call `backend/server` from Flutter.
- Persist all new chat state in the existing Postgres models; no SQLite legacy state.
- Keep workspace/brain tenancy validation on every chat request.

---

### Task 1: Define backend chat payload behavior

**Files:**
- Modify: `backend/app/api/chat.py`
- Create: `backend/app/tests/test_chat.py`

**Interfaces:**
- Produces: `POST /api/v1/chat/{brain_id}/sessions/{session_id}/messages` accepting a user message and returning its persisted record.
- Produces: `GET /api/v1/chat/{brain_id}/sessions/{session_id}/messages` returning ordered persisted user/assistant records.

- [ ] **Step 1: Write failing tests**

Add tests for tenant-scoped message creation, duplicate `client_message_id` returning the original message, and ordered message history.

- [ ] **Step 2: Run the targeted test**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_chat.py -q`
Expected: failing test collection or missing required behavior.

- [ ] **Step 3: Implement the minimal API changes**

Keep request validation in Pydantic, preserve `_get_brain_or_404`, and return a consistent message JSON object with `id`, `role`, `content`, `status`, `client_message_id`, and `created_at`.

- [ ] **Step 4: Re-run the targeted test**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests/test_chat.py -q`
Expected: PASS.

### Task 2: Replace Flutter legacy chat services

**Files:**
- Modify: `frontend/lib/data/services/chat_service.dart`
- Delete: `frontend/lib/data/services/chat_socket_service.dart`
- Modify: `frontend/lib/modules/chat/controllers/chat_controller.dart`

**Interfaces:**
- Consumes: `ApiClient`, cached `workspace_id`, and cached `brain_id`.
- Produces: `ChatService.getSessions()`, `getMessages(sessionId)`, `createSession(title)`, and `sendUserMessage(sessionId, content, clientMessageId)`.

- [ ] **Step 1: Write a failing source-boundary test**

Add a lightweight Dart test or backend-independent static test that asserts the Chat client uses `ApiClient` and does not contain `:8888`, `backend/server`, `javis/`, or a websocket channel import.

- [ ] **Step 2: Run the targeted test**

Run: `cd frontend && flutter test`
Expected: FAIL before the migration.

- [ ] **Step 3: Implement the backend-only client**

Read workspace and brain IDs from `SharedPreferences`; send all requests to `/chat/{brainId}/...` with `workspace_id` query parameter. Create a session before sending the first message. Replace socket frames with periodic API polling while a response is pending. Surface API failures in the controller and always clear `isSending`.

- [ ] **Step 4: Remove the legacy socket service**

Delete `chat_socket_service.dart` and remove its imports, fields, lifecycle calls, and handling from `ChatController`.

- [ ] **Step 5: Re-run Flutter checks**

Run: `cd frontend && flutter test && flutter analyze`
Expected: PASS with no legacy runtime strings in `lib/`.

### Task 3: Enforce and document the boundary

**Files:**
- Modify: `DEPLOYMENT.md`
- Modify: `.gitignore` if required for generated test artifacts

**Interfaces:**
- Produces: deployment instructions that start only Postgres, MinIO, brain-api, agent-worker and Flutter.

- [ ] **Step 1: Write the failing boundary scan**

Run: `rg -n --glob '!build/**' '(:8888|backend/server|javis/)' frontend/lib`
Expected: matching legacy chat references before migration.

- [ ] **Step 2: Update deployment documentation**

Remove legacy-server startup instructions and specify that Flutter’s sole backend is `brain-api`.

- [ ] **Step 3: Verify the boundary**

Run the boundary scan again.
Expected: no matches in `frontend/lib`.

- [ ] **Step 4: Run regression verification**

Run: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest app/tests -q`
Expected: PASS.
