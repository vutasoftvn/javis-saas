# mCOSA Realtime Voice Agent

LiveKit Agents worker that carries the actual realtime voice loop for mCOSA's
Hologram Hub (mCOSA V12.1/V12.2 §7 Voice Agent Runtime). This is a
**standalone process**, not part of `backend/app`/`brain-api` — long-lived
audio handling must never run inside a FastAPI request handler (spec §90.3).

```
Flutter (livekit_client)
      │
      ▼
LiveKit (Cloud today; Local later, see DEPLOYMENT.md)
      │
      ▼
services/realtime_agent  ◄── this process
      │
      ├── Gemini Live (livekit-plugins-google)
      └── Tool Bridge ──► backend/app (direct SessionLocal(), no HTTP hop)
```

`backend/app/modules/realtime` (`/api/v1/realtime`) only handles the Control
Plane side: creating a `RealtimeSession` row, minting a LiveKit join token,
and recording session status/events. It never touches the audio stream
itself.

## Why a separate venv

This directory has its own `.venv`/`requirements.txt`, deliberately isolated
from `backend/.venv`:

- `livekit-agents` and `livekit-plugins-google` (which pulls in
  `google-genai`) are only needed here, not in the FastAPI app —
  `backend/requirements.txt` only carries the lightweight `livekit-api` SDK
  (token minting only).
- `google-genai` requires `httpx>=0.28.1`; `backend/requirements.txt` pins
  `httpx==0.27.2` for its own unrelated reasons. **Do not**
  `pip install -r ../../backend/requirements.txt` into this venv — it will
  downgrade httpx and break Gemini Live.

## Running locally

Secrets are read from `backend/.env` (see `main.py` — this process has no
`.env` of its own, `backend/.env` is the single source of truth for
`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `GOOGLE_API_KEY`).

```bash
cd services/realtime_agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py dev
```

`main.py dev` runs the LiveKit Agents CLI in development mode (connects to
the LiveKit project configured by `LIVEKIT_URL`/`LIVEKIT_API_KEY` and waits
for job dispatch). The worker registers with no explicit `agent_name`, so it
picks up jobs via LiveKit's automatic dispatch to any new room whose name
matches the `cosa-{workspace_id}-{user_id}-{snowflake}` format minted by
`backend/app/modules/realtime/router.py::create_realtime_session`.

## Configuration (env vars, all optional with safe defaults)

Read by `agent.py::_build_turn_handling` and `session_guards.py` — see those
docstrings for exact defaults. Do not hardcode tuned values into code;
change these instead:

| Var | Default | Purpose |
|---|---|---|
| `VOICE_MIN_ENDPOINTING_DELAY` | `0.5` (s) | Turn-taking: min silence before the user's turn is considered done. |
| `VOICE_MAX_ENDPOINTING_DELAY` | `3.0` (s) | Turn-taking: max wait before forcing turn end. |
| `VOICE_INTERRUPTION_ENABLED` | `true` | Barge-in on/off. |
| `VOICE_INTERRUPTION_MIN_DURATION` | `0.5` (s) | Minimum speech length to count as a real interruption. |
| `VOICE_IDLE_TIMEOUT_SECONDS` | `120` | Close the session after this many seconds of *continuous* "away" user state — distinct from `AgentSession`'s own built-in 15s `user_away_timeout`, which only flips state and never closes anything on its own. |
| `VOICE_SESSION_MAX_MINUTES` | `30` | Hard cap on session duration regardless of activity. |

Vietnamese barge-in latency has not been benchmarked automatically — tune
the `VOICE_*ENDPOINTING*`/`VOICE_INTERRUPTION*` vars against a manual test
before changing production defaults:

1. Start a conversation session.
2. While the agent is mid-sentence, speak over it in Vietnamese.
3. Confirm the agent stops audio and the Hologram UI flips to `LISTENING`
   quickly enough to feel natural (subjective — there is no automated
   latency assertion for this yet).
4. Repeat with a short interjection (a few words) vs. a longer interruption
   to sanity-check `VOICE_INTERRUPTION_MIN_DURATION`.

## Module layout

- `main.py` — process entrypoint, loads `backend/.env`, starts the LiveKit
  Agents CLI worker.
- `agent.py` — `entrypoint()`/`prewarm()`: builds the `AgentSession` (Gemini
  Live), wires hologram-state/idle/max-duration event handlers.
- `tools.py` — the tool bridge: wraps `backend/app/modules/realtime/tools.py`
  functions as `@function_tool`s (CEO brief, next actions, project/portfolio
  status, developer job status/dispatch, approvals, navigation).
- `event_bridge.py` — single place that knows the `HOLOGRAM_STATE`/
  `UI_COMMAND` data-channel envelopes and the `RealtimeSession`
  status/`RealtimeEvent` writes.
- `session_guards.py` — `IdleGuard` and env-var readers for idle/max-duration
  enforcement (unit-testable without a real event loop).
- `session_context.py` — system prompt builder.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

Run under this directory's own venv — not `backend/.venv`.
