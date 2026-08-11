# Wave 1 DeepSeek Chat Design

## Goal

Replace the mock chat worker with a JavisOS-native DeepSeek chat runtime.
Flutter continues to communicate only with `brain-api`; it never receives a
provider credential or connects to legacy Javis.

## Scope

This wave delivers a DeepSeek-backed interactive chat path, streaming UI,
durable message/run state, and workspace-scoped usage read APIs.

It does not deliver retrieval/citations, MCP tool calling, background
workflows, provider fallback, or model selection per workflow.

## Provider policy

- Default provider: `deepseek`.
- Default model: `deepseek-chat`.
- Credential: `DEEPSEEK_API_KEY` in the backend runtime environment only.
- Flutter cannot supply a provider, model, base URL, API key, price, or token
  count.
- A missing DeepSeek key leaves the message in terminal `error` state with a
  safe user-facing error; it must not create a mock response.

## Components

### AI router

`backend/app/services/ai_router.py` owns a small provider-independent
interface:

    generate(messages: list[ChatTurn]) -> AsyncIterator[AIEvent]

`backend/app/integrations/deepseek_client.py` implements the interface using
the OpenAI-compatible DeepSeek Chat Completions API. It emits only normalised
events: `delta`, `completed`, or `failed`.

### Worker

`agent-worker` claims one pending user message at a time. It:

1. atomically marks that message `processing`;
2. writes an assistant message in `streaming` state;
3. appends DeepSeek deltas to that assistant message;
4. writes a durable AI run with provider, model, input/output tokens and cost;
5. marks the assistant `delivered` or `error`.

The worker retries no provider request in this wave. A failed attempt is
durable and visible; a later retry policy belongs to a dedicated reliability
wave.

### API and streaming

Existing session/message endpoints remain the source of truth. A new
tenant-scoped SSE endpoint streams persisted message state for one session.
It emits the current assistant content after each persisted delta and a final
`completed` or `failed` event. Reconnecting clients can recover by reading
the normal message history endpoint.

### Usage

AI runs are workspace-owned directly, not inferred through workflow runs.
Each record includes chat session/message references, provider/model, status,
input tokens, output tokens, estimated cost, error code, and timestamps.
The usage API returns only runs belonging to the authenticated workspace.

## Frontend behavior

The Chat controller sends a user message through the current API and subscribes
to the backend SSE session stream. It updates the streaming assistant bubble
from server events. Connection loss falls back to bounded polling of the same
message-history endpoint, then reconnects to SSE. It never calls legacy
WebSocket endpoints.

The initial model UI is read-only: it labels the active default as
`DeepSeek / deepseek-chat`. Model switching is intentionally deferred until
the model-policy wave.

## Security and tenancy

- Every chat, stream, and usage query verifies the authenticated workspace and
  that the requested brain/session/message belongs to it.
- No provider exception body, API key, or request header is written to the
  database, API response, or log.
- The API process owns client authentication. Only the worker reads the
  DeepSeek credential.

## Tests and acceptance

- A user message produces a persisted assistant reply using a fake DeepSeek
  transport in tests.
- Missing provider configuration records an error without a mock reply.
- Another workspace cannot read the stream, message, or usage run.
- Duplicate client message IDs do not trigger duplicate AI runs.
- Flutter renders streamed content and can reload message history after a
  stream reconnect.
- `frontend/lib` retains no legacy runtime reference.
