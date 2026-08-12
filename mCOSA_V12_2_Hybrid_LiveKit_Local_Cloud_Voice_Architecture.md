# mCOSA V12.2 — Hybrid LiveKit Local + Cloud Realtime Architecture
## Implementation Specification — V12.1 Baseline + V12.2 Desktop Local / Mobile Cloud Update

**Product:** mCOSA — *my Company One System AI*  
**Baseline:** V10 Hybrid Workforce implemented; V12 Project & Portfolio OS planned/implementing  
**Upgrade type:** Additive architecture update  
**Primary goal:** Add production-grade realtime voice/multimodal interaction without coupling mCOSA directly to one realtime model provider  
**Realtime transport:** LiveKit  
**Default realtime voice model:** Gemini Live through LiveKit Agents  
**Routine text chat:** DeepSeek  
**Strategic reasoning:** ChatGPT Terra profile  
**Coding:** Claude Code CLI  
**Frontend:** Flutter + GetX  
**Backend:** Python FastAPI + PostgreSQL  
**Execution:** Existing mCOSA Local AI Worker Runtime  
**Core architectural rule:** Realtime interaction is a separate plane from business truth and execution

---

# 1. Executive Decision

mCOSA should adopt **LiveKit as the Realtime Interaction Plane**.

LiveKit is not the AI brain and must not replace:

- mCOSA Core.
- Strategy OS.
- Portfolio OS.
- Knowledge Engine.
- Hybrid Workforce.
- Policy Engine.
- Local AI Worker Runtime.
- DeepSeek.
- ChatGPT Terra.
- Claude Code.

Its role is:

```text
Realtime Transport
Voice / Video / Screen / Data
Turn-taking
Interruption / Barge-in
Session lifecycle
Realtime agent participant
```

Recommended north-star:

```text
Flutter Mobile/Desktop/Web
          │
          ▼
        LiveKit
     WebRTC / Data
          │
          ▼
 mCOSA Voice Agent Runtime
          │
   ┌──────┼───────────┐
   ▼      ▼           ▼
Gemini   mCOSA       Context
 Live    Tools       Builder
          │
          ▼
       mCOSA Core
          │
  ┌───────┼─────────────────┐
  ▼       ▼                 ▼
DeepSeek Terra          Hybrid Workforce
                         │
                  ┌──────┼─────────┐
                  ▼      ▼         ▼
              Claude   Agents   Automation
               Code
```

The central principle is:

> **LiveKit carries realtime interaction. mCOSA remains the source of truth.**

---

# 2. Why LiveKit

LiveKit should be used to avoid building and maintaining a custom realtime media stack.

Verified LiveKit capabilities relevant to mCOSA include:

- WebRTC-based realtime communication between frontend and agents.
- Voice, video and realtime data transport.
- Agent participants.
- Turn detection and interruption handling.
- Support for both realtime speech-to-speech models and STT → LLM → TTS pipelines.
- Flutter SDK and Flutter voice-agent starter application.
- LiveKit Cloud or self-hosted deployment.
- Gemini Live realtime plugin.
- Agent observability and cloud session metering.

This makes LiveKit a stronger abstraction boundary than wiring Flutter directly to Gemini Live.

---

# 3. Architectural Boundary

Do not design:

```text
Flutter
  ↓
Gemini Live
  ↓
mCOSA
```

Use:

```text
Flutter
  ↓
LiveKit
  ↓
mCOSA Realtime Agent
  ↓
Realtime Model Adapter
  ├── Gemini Live
  ├── OpenAI Realtime
  └── STT + LLM + TTS Pipeline
```

This allows model switching without rewriting Flutter voice architecture.

---

# 4. Realtime Interaction Plane vs Execution Plane

These are separate systems.

## Realtime Interaction Plane

Use for:

```text
Voice conversation
Video
Screen sharing
Realtime captions
Turn-taking
Interruption
Human–AI session
Phone/SIP later
```

## Execution Plane

Use for:

```text
Research worker
Marketing worker
Finance worker
Claude Code
Browser automation
Scheduled workflows
Document generation
Background jobs
```

Therefore:

```text
LiveKit Agents
≠
mCOSA Agent Runtime
```

LiveKit Agents are realtime participants. mCOSA Workers are business/execution workers. Do not merge the two frameworks.

---

# 5. Voice Is a Modality, Not the Brain

Voice should not own strategic or operational business logic.

Example:

Founder says:

> “Hôm nay tôi cần làm gì?”

Incorrect:

```text
Voice model invents answer
```

Correct:

```text
Voice
 ↓
LiveKit Agent
 ↓
mCOSA Tool:
get_next_best_actions()
 ↓
Portfolio / Project OS
 ↓
Structured result
 ↓
Voice model explains result
```

Business truth stays inside mCOSA.

---

# 6. Recommended Model Roles

```yaml
ai:
  voice_realtime:
    transport: livekit
    default_model: gemini_live

  chat:
    provider: deepseek

  strategy:
    provider: chatgpt
    profile: terra

  coding:
    provider: claude_code_cli
```

| Capability | Default |
| --- | --- |
| Realtime voice | LiveKit + Gemini Live |
| Routine chat | DeepSeek |
| Intent / lightweight commands | LiveKit agent + mCOSA router |
| Strategic PESTEL/SWOT/TOWS/Portfolio | Terra |
| Coding | Claude Code CLI |
| Business data | mCOSA services/PostgreSQL |
| Knowledge retrieval | mCOSA Knowledge Engine |

---

# 7. LiveKit Voice Agent Runtime

Create a dedicated Python service/process:

```text
mCOSA Voice Agent Runtime
```

Suggested modules:

```text
voice_runtime/
  session_manager/
  livekit_transport/
  realtime_model/
  tool_bridge/
  context_builder/
  turn_manager/
  policy_bridge/
  event_bridge/
  cost_tracker/
  observability/
```

FastAPI remains the Control Plane API. The Voice Runtime is a long-lived realtime worker.

---

# 8. FastAPI Responsibilities

FastAPI should handle:

- User authentication.
- Workspace authorization.
- Voice session creation.
- LiveKit access token issuance.
- Session metadata.
- Device/workspace context.
- Tool authorization.
- Policy checks.
- Usage/budget configuration.
- Audit.
- Session history metadata.
- Links to Project / Portfolio / Current Cycle.

FastAPI should **not** directly process the realtime audio loop.

---

# 9. Flutter Responsibilities

Flutter should handle:

- Microphone permission.
- Audio capture/playback.
- LiveKit room connection.
- Audio track subscription/publication.
- Optional video/camera.
- Optional screen share.
- Realtime transcript display.
- Realtime state animation.
- Mute/unmute.
- Push-to-talk.
- Conversation Mode.
- Session start/end.
- Device audio routing.
- Reconnect UX.
- User-visible error states.

Do not embed provider API keys in Flutter.

---

# 10. Flutter SDK Strategy

Use LiveKit Flutter client as the realtime client abstraction.

Recommended service boundary:

```dart
abstract class RealtimeSessionGateway {
  Future<void> connect(...);
  Future<void> disconnect();
  Future<void> setMicrophoneEnabled(bool enabled);
  Stream<RealtimeSessionEvent> get events;
}
```

Implementation:

```text
LiveKitRealtimeSessionGateway
```

Presentation:

```text
VoiceSessionController
HologramStateController
RealtimeTranscriptController
```

Keep GetX in Presentation / Navigation / DI, consistent with existing mCOSA architecture.

---

# 11. Voice Session Lifecycle

Suggested lifecycle:

```text
CREATING
CONNECTING
READY
LISTENING
THINKING
RETRIEVING
ACTING
WAITING_APPROVAL
SPEAKING
INTERRUPTED
RECONNECTING
ERROR
ENDED
```

The Hologram Hub should map animation/state to these actual events.

---

# 12. Hologram Hub State Mapping

```text
LiveKit connected
   ↓
IDLE / READY

User speech detected
   ↓
LISTENING

Turn ends
   ↓
THINKING

Tool call started
   ↓
RETRIEVING / ACTING

Approval required
   ↓
WAITING APPROVAL

Agent audio publishing
   ↓
SPEAKING

User interrupts
   ↓
INTERRUPTED → LISTENING
```

Do not expose private chain-of-thought.

---

# 13. Barge-in Is an MVP Requirement

Realtime voice must support user interruption.

Scenario:

```text
mCOSA:
"mVault currently has three—"

Founder:
"Dừng. Mở dashboard."
```

Expected behavior:

```text
Agent speaking
   ↓
User activity detected
   ↓
Interruption
   ↓
Stop agent audio
   ↓
Capture new turn
   ↓
Process new intent
```

Do not ship a voice MVP that forces the user to wait for full TTS completion.

---

# 14. Turn Detection

Turn detection determines when the user has finished speaking.

V1 should use LiveKit-supported turn/activity detection and allow tuning:

```yaml
voice:
  turn_detection:
    mode:
    min_endpointing_delay:
    max_endpointing_delay:
    interruption_enabled: true
    interruption_threshold:
```

Avoid hard-coding one timing profile for every device/language. Vietnamese should be benchmarked independently.

---

# 15. Voice Modes

## 15.1 Push-to-Talk

Recommended initial mobile mode.

```text
Hold button
→ speak
→ release
→ process
```

Benefits:

- Easy to understand.
- Fewer false turns.
- Lower idle cost.
- Strong privacy boundary.

## 15.2 Conversation Mode

```text
Start Conversation
→ continuous realtime session
```

Useful for:

- Weekly review.
- Strategy discussion.
- Project walkthrough.
- Hands-free interaction.

## 15.3 Ambient Desktop Mode

```text
Local Wake Word
→ open LiveKit session
```

Do not stream microphone audio continuously to cloud while idle.

---

# 16. Wake Word

Wake word should be local where feasible.

```text
Microphone
  ↓
Local Wake Word Detector
  ↓
"mCOSA"
  ↓
Start / wake realtime session
```

Do not implement:

```text
Mic 24/7
→ Cloud realtime model
```

Benefits:

- Privacy.
- Lower bandwidth.
- Lower usage cost.
- Lower unnecessary cloud processing.

Wake-word implementation remains provider-neutral.

---

# 17. Realtime Model Adapter

Create a provider-neutral contract:

```python
class RealtimeVoiceModel:
    async def attach(self, session_context): ...
    async def update_context(self, context): ...
    async def send_tool_result(self, result): ...
    async def close(self): ...
```

Initial implementation:

```text
GeminiLiveRealtimeModel
```

Future options:

```text
OpenAIRealtimeModel
PipelineRealtimeModel
```

Do not expose Gemini-specific protocol to Flutter.

---

# 18. Gemini Live Default

Gemini Live is the recommended initial realtime speech model behind LiveKit because LiveKit provides a Google realtime plugin with a `RealtimeModel` abstraction for low-latency two-way voice interaction.

Use it for:

- Natural voice conversation.
- Low-latency spoken responses.
- Audio input/output.
- Optional multimodal scenarios when enabled.

Do not use it as the sole source for strategic truth.

---

# 19. STT → LLM → TTS Alternative

LiveKit Agents also supports:

```text
Speech
 ↓
STT
 ↓
LLM
 ↓
TTS
```

This can be used when:

- Cost is more important than native speech-to-speech behavior.
- A text model must remain the conversation brain.
- Better transcript control is required.
- A specific TTS voice is required.
- Native realtime audio provider is unavailable.

Potential V2 profile:

```yaml
voice:
  profile: pipeline
  stt: configurable
  llm: deepseek
  tts: configurable
```

Do not hard-code this into V1.

---

# 20. Voice Session Router

```text
User Speech
   ↓
Realtime Session Router
   ├── Conversational
   ├── Operational Command
   ├── Strategic Analysis
   ├── Knowledge Query
   ├── Approval
   └── Coding Request
```

Routing:

```text
Conversational
→ realtime model

Operational command
→ mCOSA tool

Strategic
→ Terra strategic job

Knowledge
→ Knowledge Engine

Approval
→ V10 Policy / Approval service

Coding
→ Technology WorkItem → Claude Code
```

---

# 21. Tool Bridge

The Voice Agent must call mCOSA application services through a controlled Tool Bridge.

Example tools:

```text
CEO:
- get_ceo_brief
- get_next_best_actions
- get_needs_you

Project:
- get_project_status
- get_weekly_mission
- get_milestone
- open_project_dashboard

Portfolio:
- get_portfolio_status
- get_project_priorities
- get_founder_capacity

Work:
- create_work_item
- get_run_status
- get_artifact

Approval:
- get_pending_approvals
- approve_action
- reject_action

Knowledge:
- knowledge_search
- knowledge_read

Navigation:
- open_dashboard
- open_project
- open_portfolio
```

Do not expose raw database or shell access to the realtime agent.

---

# 22. Policy Bridge

No voice command may bypass the V10 Policy Engine.

Founder says:

> “Đăng luôn bài Facebook.”

Correct path:

```text
Voice Command
  ↓
mCOSA Action
  ↓
Policy Engine
  ↓
Risk / Authority / Budget
  ↓
Approval if needed
  ↓
Execute
```

Incorrect:

```text
Voice model → Facebook API directly
```

---

# 23. Approval by Voice

Voice can be an approval surface, but approval semantics remain in mCOSA.

```text
mCOSA:
"Chiến dịch này sẽ sử dụng 3 triệu đồng ngân sách quảng cáo. Anh có muốn duyệt không?"

Founder:
"Duyệt."
```

Record:

```text
approval_request_id
approved_by
voice_session_id
timestamp
action_ref
policy_result
```

For high-risk actions, stronger confirmation/authentication may still be required.

---

# 24. Voice Context Builder

A realtime session should receive only compact context.

Default context:

```text
User
Role
Organization
Current Portfolio
Current Project
Current Cycle
Current Week
Current UI screen
Top active goals
Top 3 Next Best Actions
Pending approvals count
Short conversation summary
Available tool definitions
```

Do not inject:

```text
Entire Knowledge vault
All chat history
All project artifacts
All run logs
```

Retrieve on demand.

---

# 25. Knowledge Retrieval During Voice

Founder:

> “Tại sao mVault tuần này bị cảnh báo?”

Voice agent calls:

```text
portfolio.get_project_health()
knowledge.search()
project.get_risks()
```

mCOSA returns structured evidence; voice model explains.

---

# 26. Voice + Terra Strategic Analysis

Strategic request:

> “Phân tích lại 3 project và đề xuất tôi nên tập trung vào cái nào.”

Flow:

```text
Speech
 ↓
LiveKit
 ↓
Intent: STRATEGIC_PORTFOLIO_ANALYSIS
 ↓
Create Strategic Analysis Job
 ↓
Terra Strategic Analyzer
 ↓
Portfolio Analysis Artifact
 ↓
mCOSA Review State
 ↓
Voice summary
```

Do not ask the realtime voice model to replace Terra for deep strategy work.

---

# 27. Voice + Claude Code

Founder:

> “Triển khai Portfolio Impact Matrix.”

Flow:

```text
LiveKit
 ↓
mCOSA Tool Bridge
 ↓
Technology WorkItem
 ↓
V10 Execution Runtime
 ↓
Desktop Device Agent
 ↓
Claude Code CLI
 ↓
Git Worktree
 ↓
Tests / Build
 ↓
Artifact
 ↓
Voice notification
```

The realtime session must not execute shell commands itself.

---

# 28. Realtime Events from Desktop Execution

Expose selected events to Voice Runtime:

```text
JOB_STARTED
PLAN_READY
TESTS_RUNNING
TESTS_PASSED
TESTS_FAILED
WAITING_APPROVAL
ARTIFACT_READY
JOB_FAILED
```

Then voice can answer:

> “Claude Code đang làm tới đâu?”

without reading raw logs.

---

# 29. Human + AI Realtime Sessions

LiveKit room architecture can later support:

```text
Founder
Human Manager
mCOSA Voice Agent
```

Possible uses:

- Weekly company review.
- Project review.
- Planning session.
- Team meeting.
- Customer call with AI assistant.

Avoid creating rooms where many AI agents freely talk to each other. Internal AI collaboration should remain structured through Task, Artifact, Evidence and Decision.

---

# 30. Human Meeting Copilot

Future feature:

```text
Human meeting
  ↓
LiveKit room
  ↓
mCOSA listens with permission
  ↓
Transcript
  ↓
Decisions
Actions
Evidence
Follow-ups
  ↓
Knowledge candidates
```

Explicit participant consent/privacy rules must apply. Do not silently record meetings.

---

# 31. Video and Screen Sharing

Possible use cases:

```text
Screen share dashboard
→ "Giải thích tại sao project này màu đỏ."

Screen share Claude Code
→ "Tình trạng build thế nào?"
```

V1 does not need to make video mandatory. Architecture should simply avoid preventing it later.

---

# 32. Screen Context Rule

Differentiate:

```text
SCREEN_VIEW
SCREEN_CONTROL
LOCAL_TOOL_EXECUTION
```

V1 may support `SCREEN_VIEW` while actual control remains through authorized mCOSA tools.

---

# 33. Telephony Future Path

Possible future uses:

```text
Customer support calls
Sales qualification
Appointment calls
Inbound company assistant
External expert call assistant
```

This is V2/V3, not MVP.

Telephony requires additional privacy, consent, call recording, escalation and legal review.

---

# 34. RealtimeTransport Interface

```python
class RealtimeTransport:
    async def create_session(self, ...): ...
    async def close_session(self, ...): ...
    async def send_data(self, ...): ...
    async def publish_event(self, ...): ...
```

Implementation:

```text
LiveKitRealtimeTransport
```

This prevents LiveKit identifiers from spreading throughout domain code.

---

# 35. VoiceGateway Interface

```python
class VoiceGateway:
    async def start_session(self, request): ...
    async def end_session(self, session_id): ...
    async def push_context(self, session_id, context): ...
    async def notify(self, session_id, event): ...
```

Implementation:

```text
LiveKitVoiceGateway
```

---

# 36. Session Domain

```yaml
realtime_session:
  id:
  organization_id:
  user_id:
  device_id:
  project_id: optional
  portfolio_id: optional
  mode: push_to_talk|conversation|ambient
  transport: livekit
  model_profile:
  started_at:
  ended_at:
  status:
  room_ref:
  agent_ref:
  cost_summary:
```

Do not store raw provider credentials.

---

# 37. Realtime Event Domain

```yaml
realtime_event:
  id:
  session_id:
  sequence:
  type:
  timestamp:
  payload_ref:
  project_id:
  run_id:
  work_item_id:
  approval_id:
```

Events:

```text
SESSION_CONNECTED
USER_SPEECH_STARTED
USER_SPEECH_ENDED
USER_TRANSCRIPT
AGENT_THINKING
TOOL_CALL_STARTED
TOOL_CALL_FINISHED
APPROVAL_REQUIRED
AGENT_SPEECH_STARTED
AGENT_SPEECH_STOPPED
USER_INTERRUPTED
SESSION_RECONNECTED
SESSION_ERROR
SESSION_ENDED
```

Persist only what is useful for audit/UX.

---

# 38. Transcript Policy

Configurable:

```text
OFF
EPHEMERAL
SESSION_ONLY
SAVE_SUMMARY
SAVE_FULL_TRANSCRIPT
```

Recommended OPC default:

```text
SAVE_SUMMARY
```

unless user requests full transcript.

---

# 39. Audio Recording Policy

Do not record audio by default.

```text
record_audio: false
```

When enabled:

- User knows recording is active.
- Retention policy is explicit.
- Access control is applied.
- Recording classification is set.
- Deletion is supported.

---

# 40. Privacy Architecture

Rules:

- No API secrets in audio context.
- No passwords in logs.
- Sensitive content can disable transcript persistence.
- Knowledge permissions still apply.
- Cross-project access still applies.
- Screen share is user-controlled.
- Microphone is visibly active.
- Session termination must actually stop media publication.
- Local wake word should not upload idle microphone audio.

---

# 41. Authentication

```text
Flutter
  ↓
mCOSA Auth
  ↓
POST /realtime/sessions
  ↓
FastAPI validates user/workspace/device
  ↓
Issue short-lived LiveKit connection credentials
  ↓
Flutter joins room
```

Do not ship long-lived LiveKit admin credentials in the app.

---

# 42. Authorization

Session token scope should reflect:

```text
organization
user
device
room
participant identity
media permissions
```

mCOSA Tool Bridge separately verifies:

```text
RBAC
ABAC
Project access
Portfolio access
Knowledge scope
Action authority
```

Realtime room participation never implies business permission.

---

# 43. Cloud vs Self-Hosted

Keep deployment provider-neutral:

```text
RealtimeTransport
   ↓
LiveKit
   ├── LiveKit Cloud
   └── Self-Hosted
```

## Recommended MVP

Use LiveKit Cloud.

Reasons:

- Faster deployment.
- Avoid operating WebRTC infrastructure.
- Easier NAT/network handling.
- Easier production testing.

## Re-evaluate self-hosting when

- Enterprise/on-prem demand.
- Data residency constraints.
- Privacy requirements.
- Cost at meaningful scale.
- Private-network use cases.

For a one-person company MVP, operating WebRTC infrastructure is usually a poor use of Founder Attention.

---

# 44. Local-First Boundary

LiveKit improves online realtime interaction but does not make voice fully offline.

mCOSA remains local-first because:

- Knowledge can remain local.
- Claude Code runs local.
- Desktop files remain local.
- Worker runtime remains local.
- Cloud sync remains controlled.

When internet is unavailable:

```text
Cloud realtime voice
→ OFFLINE / DEGRADED

Local text/desktop functions
→ continue
```

---

# 45. Offline Fallback

V1:

```text
No network
→ Voice unavailable
→ Text/local command fallback
```

V2 possible:

```text
Local wake word
Local STT
Local small router/model
Local TTS
```

Use the same abstraction boundaries where practical.

---

# 46. Cost Model

Realtime cost may include:

```text
LiveKit session
+
Realtime model
+
Optional STT
+
Optional TTS
+
Optional LLM
```

Implement:

```yaml
voice_budget:
  monthly_budget:
  per_session_limit:
  warning_threshold:
  max_conversation_minutes:
  idle_timeout:
```

Do not assume voice is free because one layer has a free allowance.

---

# 47. Idle Timeout

Conversation Mode should end or suspend after inactivity.

```yaml
voice:
  idle_timeout_seconds:
  max_session_minutes:
```

Do not leave realtime sessions connected indefinitely.

---

# 48. Cost-Aware Voice Modes

```text
Push-to-Talk
→ default mobile, low cost

Conversation
→ user explicitly starts session

Ambient
→ local wake word, cloud session only after wake
```

---

# 49. Observability

Track:

```text
Session duration
Connection failures
Reconnect count
User speech latency
End-of-turn latency
Time-to-first-agent-audio
Tool-call latency
Interruption rate
False interruption rate
Model errors
Tool errors
Cost
```

End-to-end conversational latency matters more than raw model latency alone.

---

# 50. Voice Quality KPIs

Recommended:

```text
P50 / P95 response latency
P50 / P95 tool response latency
Successful interruption rate
False interruption rate
Session completion rate
Reconnect recovery rate
User correction rate
Voice command success rate
Cost per successful session
```

---

# 51. Hologram Voice UX

Hologram Hub should render:

```text
IDLE
LISTENING
THINKING
RETRIEVING
ACTING
WAITING APPROVAL
SPEAKING
WARNING
ERROR
OFFLINE
```

Visuals can respond to audio amplitude and actual operational states.

---

# 52. Voice UX — CEO Brief

Founder:

> “mCOSA, tình hình hôm nay?”

Tool:

```text
get_ceo_brief()
```

Response data:

```text
Company health
Current 12WY week
Top portfolio risks
Top 3 next actions
Approvals
Founder capacity
```

Voice model summarizes only the important parts.

---

# 53. Voice UX — Weekly Mission

Founder:

> “Tuần này mục tiêu gì?”

Tool:

```text
get_weekly_company_mission()
```

Voice:

```text
"Tuần này mục tiêu chính là hoàn tất MVP mCOSA
và xác thực rủi ro pháp lý của mVault.
Anh có ba việc cần trực tiếp xử lý..."
```

---

# 54. Voice UX — Portfolio

Founder:

> “So sánh 3 project.”

Light comparison:

```text
DeepSeek / deterministic portfolio data
```

Deep strategic reconsideration:

```text
Create Terra analysis job
```

Voice should say when a deeper job is being created instead of pretending it completed instantly.

---

# 55. Voice UX — Approval

Founder:

> “Có gì chờ tôi duyệt?”

Tool:

```text
get_pending_approvals()
```

Return highest-risk first; do not read long lists.

Example:

```text
"Anh có 4 yêu cầu. Một yêu cầu mức rủi ro cao liên quan triển khai production.
Anh muốn xem nó trước không?"
```

---

# 56. Voice UX — Coding

Founder:

> “Claude Code đã xong chưa?”

Tool:

```text
get_developer_run_status()
```

Response:

```text
"Đã hoàn thành code và build.
38 test pass, còn 2 warning.
Đang chờ anh duyệt merge."
```

---

# 57. Voice UX — Navigation

Examples:

```text
"Mở Portfolio."
"Mở mVault."
"Cho tôi xem Week 4."
"Mở approval."
```

Use a structured navigation event to Flutter. Do not let the voice model fabricate routes.

---

# 58. Flutter Navigation Event

```yaml
ui_command:
  type: OPEN_ROUTE
  route: /portfolio/{id}
  params:
```

Flutter validates route and user state.

---

# 59. Realtime Data Channel

Use realtime data for:

```text
UI commands
Structured tool progress
State events
Captions
Approval cards
Artifact notifications
```

Do not send large artifacts through realtime messages; send artifact references.

---

# 60. Artifacts

If voice triggers long work:

```text
Research report
Code diff
Portfolio analysis
Spreadsheet
```

return:

```text
artifact_id
title
status
summary
```

Voice can say:

> “Báo cáo đã hoàn thành. Tôi đã mở artifact trên màn hình.”

---

# 61. Long-Running Jobs

Voice must never hold the realtime model “thinking” for minutes.

```text
User command
 ↓
Create WorkItem / Job
 ↓
Voice acknowledges
 ↓
Background execution
 ↓
Realtime event when ready
 ↓
Voice/notification surfaces result
```

---

# 62. Notifications After Session Ends

If a job completes after voice session ends:

```text
Cloud event
 ↓
Mobile/Desktop notification
 ↓
User reopens
 ↓
mCOSA can speak result
```

Do not require the LiveKit room to stay connected for background work.

---

# 63. Room Design

Recommended default:

```text
1 user session
1 mCOSA realtime agent
```

Future:

```text
multiple humans
1 mCOSA agent
```

Avoid:

```text
1 user
12 speaking agents
```

Internal agent orchestration remains behind mCOSA.

---

# 64. Participant Identity

Examples:

```text
human:{user_id}
mcosa:voice:{session_id}
```

Do not expose internal workers as room participants unless a real use case requires it.

---

# 65. Python Agent Service

Recommended package:

```text
services/realtime_agent/
```

Responsibilities:

```text
LiveKit agent lifecycle
Gemini Live adapter
Tool bridge
Session context
Turn/interruption events
Operational telemetry
```

Keep separate from:

```text
services/local_worker/
services/control_plane/
```

---

# 66. Deployment Topology

MVP:

```text
Flutter Client
    │
    ▼
LiveKit Cloud
    │
    ▼
mCOSA Realtime Agent Service
    │
    ├── Gemini Live
    └── FastAPI / mCOSA Core
              │
              ▼
          PostgreSQL
              │
              ▼
      Desktop Execution Node
```

---

# 67. Desktop Local Voice Option

Desktop can use LiveKit for online conversation.

If future privacy/local requirements justify it, add:

```text
Flutter Desktop
 ↓
Local Voice Gateway
```

Do not entangle it with V1 LiveKit implementation.

---

# 68. Failure Handling

Handle:

```text
LiveKit disconnect
Model disconnect
Tool timeout
Tool error
Permission denied
Microphone error
Audio device change
Network degradation
Provider quota
Invalid session
Desktop worker offline
```

User-facing messages must distinguish voice failure from mCOSA Core or Desktop Worker failure.

---

# 69. Reconnect

On transient network loss:

```text
RECONNECTING
```

Flutter should:

- Preserve UI.
- Stop claiming the agent is listening.
- Attempt reconnect.
- Rehydrate compact context if necessary.
- Avoid duplicate action execution.

Use idempotency keys for voice-triggered commands.

---

# 70. Voice Command Idempotency

Every consequential command should receive:

```text
voice_command_id
```

If reconnect/retry occurs, mCOSA must not create duplicate:

```text
payments
posts
jobs
approvals
work items
```

---

# 71. Audit

Audit:

```text
who asked
what action was interpreted
which tool was called
policy result
approval result
which worker executed
artifact/result
```

Do not audit hidden model reasoning.

---

# 72. Transcript vs Action Audit

These are separate.

A transcript can be deleted while consequential action audit remains.

Example:

```text
Transcript retention: 0 days
Action audit: retained according to company policy
```

---

# 73. Voice and Knowledge Memory

Do not promote all voice conversations into permanent knowledge.

```text
Voice Session
 ↓
Session Summary
 ↓
Candidate Memories
 ↓
Evaluation
 ↓
Approved Knowledge
```

Important decisions can be proposed as Knowledge candidates.

---

# 74. Decision Capture

Founder says:

> “Chu kỳ này tạm dừng VT Signal và tập trung mCOSA.”

Create a structured decision proposal:

```text
VT Signal → HOLD
mCOSA → ACCELERATE
```

If confirmed/authorized:

```text
Decision
→ Portfolio state update
→ Knowledge
→ Audit
```

---

# 75. Voice Security Levels

Map voice actions onto the existing V10 risk policy.

Example:

```text
"Open dashboard"
→ informational

"Create draft"
→ local/reversible

"Publish campaign"
→ external consequential

"Transfer money"
→ critical + strong confirmation
```

---

# 76. Voice Authentication Is Not Enough for Critical Actions

Voice recognition alone should not be assumed to be strong identity proof.

For critical actions:

```text
Voice command
 ↓
Policy
 ↓
App confirmation / biometric / strong auth
 ↓
Execute
```

Do not implement voiceprint-only payment authorization in V1.

---

# 77. LiveKit Cloud First

Recommended:

```text
V1 → LiveKit Cloud
```

Reasons:

- Faster implementation.
- Lower operational complexity.
- Easier WebRTC deployment.
- Good Flutter support.
- Easier production testing.

Keep deployment interfaces so self-hosting remains possible.

---

# 78. Self-Hosted Later

Evaluate self-hosting only when evidence supports it.

Decision inputs:

```text
Monthly realtime minutes
Concurrent sessions
Region/data residency
Enterprise contract
Network topology
Operational staffing
Privacy requirements
```

For an OPC MVP, operating WebRTC infrastructure is usually a poor use of Founder Attention.

---

# 79. Provider Lock-In Control

Avoid three forms of lock-in.

## Transport lock-in

Use:

```text
RealtimeTransport
```

## Realtime model lock-in

Use:

```text
RealtimeVoiceModel
```

## Tool lock-in

Voice tools call mCOSA application services, not provider-specific function schemas directly.

---

# 80. LiveKit Inference vs Direct Provider Plugin

Architecture should allow both:

```text
LiveKit Inference
```

and:

```text
Direct Gemini plugin / provider billing
```

Decision factors:

```text
latency
billing
rate limits
deployment
data handling
cost
```

Do not make this a domain decision.

---

# 81. Feature Flags

```text
livekit_transport_v12_1
voice_agent_runtime_v12_1
gemini_live_voice_v12_1
voice_tools_v12_1
voice_barge_in_v12_1
voice_transcript_v12_1
voice_navigation_v12_1
voice_approval_v12_1
voice_screen_share_v12_1
voice_multi_human_v12_1
telephony_v12_1
```

---

# 82. Database Additions

Suggested:

```text
realtime_sessions
realtime_session_participants
realtime_events
voice_commands
voice_command_tool_calls
voice_session_summaries
voice_usage_records
voice_recording_policies
voice_preferences
```

Reuse:

```text
users
organizations
projects
portfolios
work_items
runs
approvals
artifacts
audit
knowledge
```

---

# 83. API Sketch

```text
POST /realtime/sessions
GET  /realtime/sessions/{id}
POST /realtime/sessions/{id}/end

POST /realtime/token
GET  /realtime/config

POST /voice/commands/{id}/confirm
POST /voice/commands/{id}/cancel

GET  /voice/preferences
PUT  /voice/preferences

GET  /voice/usage

POST /voice/session/{id}/summary
```

Most realtime events flow through LiveKit rather than normal REST endpoints.

---

# 84. Internal Tool API

Use application service contracts such as:

```text
CEOService
ProjectService
PortfolioService
NextBestActionService
ApprovalService
KnowledgeService
NavigationService
WorkService
ArtifactService
DeviceService
```

Voice Runtime must not directly query database tables for business decisions.

---

# 85. MVP Scope

V12.1 MVP should implement:

```text
LiveKit Cloud
Flutter audio session
1 user + 1 mCOSA voice agent
Gemini Live default
Push-to-Talk
Conversation Mode
Barge-in
Realtime transcript
Hologram state mapping
CEO Brief tool
Next Best Actions tool
Project status tool
Portfolio status tool
Approval listing
Navigation commands
Claude Code run status
Session usage tracking
```

Do not include telephony or multi-human meetings in MVP.

---

# 86. First Vertical Slice

Founder opens Hologram Hub and asks:

> “Hôm nay tôi cần làm gì?”

Expected:

```text
1. Flutter joins LiveKit room.
2. Microphone is published.
3. Voice Agent detects the turn.
4. Agent calls mCOSA get_next_best_actions().
5. mCOSA returns structured portfolio-aware priorities.
6. Gemini Live verbalizes the answer.
7. Hologram transitions through real states.
8. Founder interrupts mid-sentence.
9. Agent immediately stops and listens.
10. Founder says “Mở project mVault.”
11. Voice Agent sends a structured UI navigation event.
12. Flutter opens mVault Project dashboard.
13. Session remains active.
```

This validates transport, tool bridge, interruption and UI integration.

---

# 87. Second Vertical Slice

Founder asks:

> “Claude Code đang làm tới đâu?”

Expected:

```text
Voice
→ mCOSA Device/Run service
→ Existing V10 run events
→ Structured status
→ Spoken response
```

No Claude Code shell execution from the voice process.

---

# 88. Third Vertical Slice

Founder asks:

> “Phân tích lại 3 project và đề xuất project ưu tiên.”

Expected:

```text
Voice
→ classify as strategic
→ create Portfolio Strategic Analysis Job
→ Terra workflow
→ acknowledge job
→ background result
→ artifact ready event
→ voice/mobile notification
```

Do not block the realtime session for long strategic reasoning.

---

# 89. Implementation Phases

## Phase LK-0 — Contracts

Implement:

```text
RealtimeTransport
VoiceGateway
RealtimeVoiceModel
RealtimeSession domain
VoiceCommand domain
```

## Phase LK-1 — Flutter Connection

Implement:

```text
LiveKit token endpoint
Flutter join/leave
Mic/audio
Session states
```

## Phase LK-2 — Voice Agent

Implement:

```text
Python LiveKit Agents runtime
Gemini Live
Basic transcript
```

## Phase LK-3 — Tool Bridge

Implement:

```text
CEO Brief
Next Best Action
Project/Portfolio status
```

## Phase LK-4 — Hologram Integration

Map realtime operational events to UI animation.

## Phase LK-5 — Interruption

Tune VAD/turn detection/barge-in for Vietnamese.

## Phase LK-6 — Work / Approval / Navigation

Connect V10 work, approval and Flutter routing.

## Phase LK-7 — Observability / Cost

Add metrics, usage policy and idle timeout.

## Phase LK-8 — Optional Multimodal

Screen share/video.

## Phase LK-9 — Future Telephony

Only after clear business need.

---

# 90. Claude Code Implementation Rules

1. Read existing V10/V12 realtime-related code first.
2. Do not replace V10 Worker Runtime.
3. Do not put long-lived audio processing inside FastAPI request handlers.
4. Use LiveKit Flutter SDK for media transport.
5. Do not put Gemini API credentials in Flutter.
6. Implement `RealtimeTransport` before provider-specific integrations.
7. Implement `RealtimeVoiceModel` before Gemini-specific logic.
8. Implement `VoiceGateway` before exposing voice to domain services.
9. Business tools must call application services, not repositories directly.
10. All consequential actions pass V10 Policy Engine.
11. Add idempotency for voice-triggered actions.
12. Do not persist raw audio by default.
13. Do not persist full transcript by default.
14. Do not store private chain-of-thought.
15. Do not implement voiceprint-based critical authorization.
16. Keep LiveKit Cloud/self-host choice in infrastructure configuration.
17. Add tests for reconnect and duplicate command prevention.
18. Add tests for project/portfolio authorization.
19. Add instrumentation for latency and interruptions.
20. Keep telephony out of MVP.

---

# 91. Suggested Backend Package

```text
backend/app/realtime/
  domain/
    session.py
    events.py
    commands.py

  application/
    session_service.py
    voice_gateway.py
    tool_bridge.py
    context_builder.py

  infrastructure/
    livekit/
      transport.py
      token_service.py
      agent_dispatch.py

    models/
      realtime_model.py
      gemini_live.py

  api/
    routes.py
```

Realtime agent service:

```text
services/realtime_agent/
  main.py
  agent.py
  tools.py
  session_context.py
  event_bridge.py
```

---

# 92. Suggested Flutter Package

```text
lib/features/realtime_voice/
  data/
    livekit_gateway.dart

  domain/
    realtime_session.dart
    realtime_event.dart

  presentation/
    controllers/
      voice_session_controller.dart
      transcript_controller.dart

    widgets/
      push_to_talk_button.dart
      conversation_controls.dart
      transcript_view.dart
```

Integrate with existing:

```text
hologram_hub/
navigation/
approvals/
projects/
portfolios/
```

---

# 93. Config Example

```yaml
realtime:
  transport:
    provider: livekit
    deployment: cloud

  voice:
    default_mode: push_to_talk
    conversation_mode_enabled: true
    ambient_mode_enabled: false

  model:
    provider: gemini_live

  transcript:
    retention: summary_only

  recording:
    enabled: false

  interruption:
    enabled: true

  security:
    critical_actions_require_strong_confirmation: true

  cost:
    idle_timeout_seconds: 120
    session_warning_minutes: 30
```

---

# 94. Environment Variables

```text
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET

GOOGLE_API_KEY

VOICE_SESSION_MAX_MINUTES
VOICE_IDLE_TIMEOUT_SECONDS
```

Secrets stay server-side.

---

# 95. Acceptance Criteria

V12.1 is accepted when:

1. Flutter Mobile/Desktop can open a LiveKit voice session.
2. No provider secret is embedded in Flutter.
3. User speech reaches the realtime agent.
4. Agent audio reaches Flutter.
5. User can interrupt agent speech.
6. Hologram state reflects actual realtime state.
7. Voice can retrieve CEO Brief.
8. Voice can retrieve Next Best Actions.
9. Voice can query Project/Portfolio status.
10. Voice can report Claude Code job state.
11. Voice can send UI navigation commands.
12. Consequential actions still pass V10 Policy Engine.
13. Reconnect does not duplicate actions.
14. Transcript retention follows policy.
15. Raw audio is not recorded by default.
16. Long jobs are executed asynchronously outside voice session.
17. Strategic requests can route to Terra jobs.
18. Routine chat remains available through DeepSeek where appropriate.
19. LiveKit is isolated behind a `RealtimeTransport` abstraction.
20. Gemini Live is isolated behind a `RealtimeVoiceModel` abstraction.
21. Existing V10 Hybrid Workforce remains unchanged.
22. Existing V12 Project/Portfolio logic remains the source of truth.

---

# 96. Non-Goals

Do not build in V12.1 MVP:

```text
Fully offline realtime speech
Custom WebRTC server
Voiceprint payment authorization
12-agent realtime AI conference
Always-on cloud microphone
Full telephony contact center
Automatic call recording
Realtime agent-to-agent brainstorming rooms
Direct voice shell access
Direct voice database access
Direct Gemini integration inside Flutter
```

---

# 97. ADRs to Create

```text
ADR-LK-001 LiveKit as Realtime Interaction Plane
ADR-LK-002 Realtime Interaction vs Execution Plane
ADR-LK-003 LiveKit Cloud First
ADR-LK-004 Gemini Live Behind RealtimeVoiceModel
ADR-LK-005 Voice Tool Bridge Uses mCOSA Application Services
ADR-LK-006 Barge-in as MVP Requirement
ADR-LK-007 Transcript and Recording Retention
ADR-LK-008 Voice Critical Action Authentication
ADR-LK-009 Voice Session Idempotency
ADR-LK-010 Realtime Context Minimization
```

---

# 98. Final Architecture

```text
                         FOUNDER / CEO
                               │
                               ▼
                        FLUTTER CLIENT
                  Mobile / Desktop / Web
                               │
                               ▼
                            LIVEKIT
                  WebRTC / Audio / Video / Data
                               │
                               ▼
                    mCOSA REALTIME AGENT
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
              ▼                ▼                 ▼
        GEMINI LIVE       TOOL BRIDGE       CONTEXT BUILDER
                               │
                               ▼
                           mCOSA CORE
                               │
          ┌────────────────────┼─────────────────────┐
          ▼                    ▼                     ▼
       DEEPSEEK              TERRA               KNOWLEDGE
      routine chat       strategy jobs            ENGINE
                               │
                               ▼
                    PROJECT / PORTFOLIO OS
                               │
                               ▼
                     HYBRID WORKFORCE V10
             ┌─────────────────┼──────────────────┐
             ▼                 ▼                  ▼
           HUMAN            AI AGENTS         AUTOMATION
                                                  │
                         ┌────────────────────────┼───────────┐
                         ▼                        ▼           ▼
                    CLAUDE CODE                 MCP         BROWSER
                         │
                         ▼
                  ARTIFACT / RESULT
                         │
                         ▼
                     POLICY / AUDIT
                         │
                         ▼
                   LIVEKIT RESPONSE
```

---

# 99. Architectural Summary

The correct abstraction is:

> **LiveKit = Realtime Interaction Plane**

> **Gemini Live = Default realtime voice model**

> **DeepSeek = Routine conversational model**

> **ChatGPT Terra = Strategic analysis model/profile**

> **Claude Code CLI = Developer execution worker**

> **mCOSA Core = Company truth, strategy, portfolio, projects, policy, tools, knowledge, work and audit**

LiveKit must make mCOSA more realtime and multimodal without making the system dependent on a single voice model or moving business logic into the voice layer.

---

# 100. Implementation Recommendation

Implement V12.1 in this order:

```text
LiveKit Transport
   ↓
Flutter Audio Session
   ↓
Python Realtime Agent
   ↓
Gemini Live
   ↓
Tool Bridge
   ↓
CEO Brief / Next Best Actions
   ↓
Hologram State
   ↓
Barge-in
   ↓
Project / Portfolio Tools
   ↓
Approval / Work Status
   ↓
Observability / Cost
```

The first production objective is not “voice everywhere.”

It is:

> **A founder can open mCOSA, speak naturally, interrupt naturally, ask what matters now, and securely control the existing Project/Portfolio/Hybrid Workforce system without touching a complex dashboard.**

---

# Appendix A — Verified LiveKit Capabilities Used in This Specification

This specification relies on LiveKit capabilities documented by LiveKit:

- LiveKit Agents uses WebRTC between frontend and agent and is designed for realtime voice/video agents.
- LiveKit Agents supports both STT–LLM–TTS pipelines and realtime models.
- Turn-taking includes user activity detection and interruption handling.
- LiveKit provides a Flutter SDK and Flutter voice-agent starter.
- LiveKit's Google plugin provides a realtime model wrapper for Gemini Live.
- LiveKit can connect clients to LiveKit Cloud or a self-hosted LiveKit server.
- LiveKit Cloud publishes separate agent-session quotas, metering and pricing.

Provider models, prices, quotas and allowances may change, so model IDs and cost values must remain configuration rather than domain constants.

---

# Appendix B — Primary References

- LiveKit Agents: https://docs.livekit.io/agents/
- Agent speech/audio: https://docs.livekit.io/agents/multimodality/audio/
- Turn detection: https://docs.livekit.io/agents/logic/turns/
- Turn-taking tuning / interruption handling: https://docs.livekit.io/agents/logic/turns/tuning/
- Gemini Live plugin: https://docs.livekit.io/agents/models/realtime/plugins/gemini/
- Flutter quickstart: https://docs.livekit.io/transport/sdk-platforms/flutter/
- Flutter starter app: https://docs.livekit.io/frontends/start/starter-apps/flutter/
- Flutter SDK reference: https://docs.livekit.io/reference/client-sdk-flutter/
- LiveKit Cloud billing: https://docs.livekit.io/deploy/admin/billing/
- LiveKit quotas/limits: https://docs.livekit.io/deploy/admin/quotas-and-limits/
- LiveKit pricing: https://livekit.io/pricing
- LiveKit open-source server: https://github.com/livekit/livekit

# V12.2 Update — Hybrid LiveKit Local + Cloud Voice Architecture

## 101. Decision Summary

V12.2 refines the V12.1 realtime design into a hybrid deployment model:

```text
Desktop
→ LiveKit Local
→ Local Realtime Agent
→ Local-first mCOSA Runtime

Mobile
→ LiveKit Cloud
→ Cloud Realtime Agent
→ mCOSA Cloud Control Plane
→ Desktop Execution Node when required
```

The default model responsibilities remain:

```text
Desktop routine conversation
→ Local / DeepSeek-backed conversational path

Mobile realtime voice
→ Gemini Live through LiveKit Cloud

Strategic reasoning
→ ChatGPT Terra assisted workflow or configured reasoning API

Coding
→ Claude Code CLI on Desktop
```

Key product rule:

> **Realtime transport selection and AI-model selection are independent decisions.**

For example:

```text
LiveKit Local + cloud LLM
```

is valid.

So is:

```text
LiveKit Local + local STT/TTS + DeepSeek
```

---

# 102. Desktop Realtime Architecture

Desktop is already an mCOSA Execution Node, therefore it should preferentially run the realtime media plane locally.

Recommended topology:

```text
Flutter Desktop
      │
      ▼
LiveKit Local Server
      │
      ▼
mCOSA Local Voice Agent
      │
 ┌────┼─────────────────────┐
 ▼    ▼                     ▼
STT  Conversation        mCOSA Tools
     Model                  │
                            ▼
                   Local AI Worker Runtime
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        Knowledge       Claude Code      Browser/MCP
```

Benefits:

- Lower local audio transport latency.
- No LiveKit Cloud minutes for local desktop conversations.
- Better privacy boundary.
- Direct access to local mCOSA services through controlled interfaces.
- Better integration with local Knowledge Engine.
- Better integration with Claude Code CLI.
- Reduced dependence on cloud availability for the realtime transport layer.

---

# 103. Desktop Does Not Mean Fully Offline

Important distinction:

```text
LOCAL TRANSPORT
≠
LOCAL AI
```

LiveKit can be local while the selected model remains cloud-based.

Examples:

```text
LiveKit Local
→ Gemini Live

LiveKit Local
→ DeepSeek API

LiveKit Local
→ OpenAI API

LiveKit Local
→ Local STT + Local LLM + Local TTS
```

The architecture must therefore separate:

```text
RealtimeTransport
RealtimeVoiceModel
ConversationModel
STT
TTS
```

---

# 104. Recommended Desktop Voice Profiles

## Profile A — Local Efficient

Recommended default for long desktop usage.

```text
LiveKit Local
→ Local STT
→ DeepSeek / low-cost conversation model
→ Local TTS
```

Use for:

- General conversation.
- Task lookup.
- CEO brief.
- Project status.
- Next Best Action.
- Navigation.
- Knowledge queries.
- Operational commands.

Advantages:

- Low transport cost.
- Reduced cloud-audio exposure.
- Predictable cost.
- Suitable for frequent daily use.

---

## Profile B — Natural Realtime

Use when natural low-latency speech-to-speech is more important.

```text
LiveKit Local
→ Gemini Live
```

The audio transport between Flutter Desktop and the local Voice Agent stays local, while model inference can still use the cloud.

Use for:

- Longer conversational sessions.
- Hands-free reviews.
- Natural interruption-heavy interaction.
- Multimodal sessions.

---

## Profile C — Local Private

Future option:

```text
LiveKit Local
→ Local STT
→ Local LLM
→ Local TTS
```

Use for:

- Sensitive local-only Projects.
- Offline/degraded connectivity.
- Privacy-sensitive sessions.

This is not required for V12.2 MVP.

---

# 105. Mobile Realtime Architecture

Mobile should default to LiveKit Cloud.

```text
Flutter Mobile
      │
      ▼
LiveKit Cloud
      │
      ▼
mCOSA Cloud Voice Agent
      │
      ├── Gemini Live
      ├── mCOSA Tool Bridge
      └── Cloud Context Builder
               │
               ▼
        FastAPI Control Plane
               │
          ┌────┴─────┐
          ▼          ▼
     PostgreSQL   Desktop Node
                     │
                     ▼
                Claude Code
                Local Files
                Local Knowledge
```

Mobile is a remote surface, not the primary execution node.

---

# 106. Why Mobile Uses LiveKit Cloud

Mobile connectivity must handle:

- Wi-Fi ↔ 4G/5G switching.
- NAT.
- Network degradation.
- Foreground/background changes.
- Remote access to Desktop.
- Reconnection.
- Geographic distance.

Operating a publicly exposed self-hosted LiveKit stack solely for an OPC mobile client is not recommended in the initial architecture.

LiveKit Cloud should therefore be the default Mobile transport.

---

# 107. AUTO Realtime Transport Mode

Add:

```text
Voice Transport

○ Local
○ Cloud
● Auto
```

Recommended routing:

```text
IF device == Desktop
AND local LiveKit available
AND local Voice Runtime healthy
THEN
    transport = LOCAL
ELSE
    transport = CLOUD
```

Mobile:

```text
transport = CLOUD
```

Future trusted-LAN mobile mode may optionally connect locally, but should not complicate MVP.

---

# 108. Realtime Transport Resolver

Introduce:

```python
class RealtimeTransportResolver:
    async def resolve(self, context) -> TransportDecision:
        ...
```

Inputs:

```text
Device type
Network state
Local LiveKit health
Cloud availability
Project privacy policy
Voice mode
User preference
Cost policy
```

Output:

```yaml
transport_decision:
  transport: livekit_local|livekit_cloud
  reason:
  fallback:
```

---

# 109. Voice Intelligence AUTO Mode

Add:

```text
Voice Intelligence

○ Local Efficient
○ Natural Realtime
○ Private Local
● Auto
```

Suggested AUTO routing:

```text
Routine information / command
→ efficient conversation path

Natural conversational session
→ Gemini Live

Strategic request
→ Terra strategic job

Coding request
→ Claude Code WorkItem
```

The founder should not need to think in provider names during normal use.

---

# 110. ChatGPT Plus / Terra Boundary

Critical architecture rule:

> **ChatGPT Plus is not an OpenAI API entitlement.**

Therefore:

```text
LiveKit Local
→ ChatGPT Plus API
```

must **not** be implemented.

Terra remains a strategic reasoning profile through one of these supported modes:

```text
ASSISTED_CHATGPT_TERRA
OPENAI_API_REASONING
OTHER_REASONING_API
LOCAL_REASONING
```

Recommended current configuration:

```text
ASSISTED_CHATGPT_TERRA
```

---

# 111. Assisted Terra Strategic Workflow

Desktop or Mobile strategic request:

```text
"Phân tích lại PESTEL của 3 project."
```

Flow:

```text
Voice / Chat
    ↓
Strategic Intent
    ↓
mCOSA builds Analysis Package
    ↓
Terra Assisted Workflow
    ↓
Founder uses ChatGPT Plus / Terra
    ↓
Import result into mCOSA
    ↓
Schema + Evidence validation
    ↓
CEO Review
```

mCOSA must not:

- scrape ChatGPT sessions;
- automate consumer login;
- store browser cookies to emulate an API;
- treat Plus subscription as backend API credits.

---

# 112. Optional OpenAI API Realtime

If the founder later wants OpenAI realtime API:

```text
LiveKit Local
→ OpenAI Realtime API
```

or:

```text
LiveKit Cloud
→ OpenAI Realtime API
```

is architecturally valid.

However:

```text
OpenAI API billing
```

is separate from:

```text
ChatGPT Plus subscription
```

The adapter boundary should make this an infrastructure/configuration change, not a domain change.

---

# 113. Claude Code Subscription Boundary

Claude Code remains a local developer worker.

Recommended:

```text
Desktop Node
→ installed Claude Code CLI
→ user-authenticated Claude Code environment
```

mCOSA should:

- detect availability;
- launch allowed jobs;
- supply worktree/context;
- collect results/events;

but should not:

- store the user's Claude password;
- proxy consumer subscription credentials for other users;
- expose Claude credentials to Cloud Control Plane.

---

# 114. DeepSeek Role

DeepSeek remains the default routine conversational model.

Use for:

```text
Text chat
Intent classification
Project classification
Simple extraction
Command interpretation
Dashboard explanation
Weekly summaries
Status narration
Low-risk Knowledge Q&A
```

For Desktop efficient voice, DeepSeek can sit behind:

```text
Local STT
→ DeepSeek
→ Local TTS
```

Provider identifiers and credentials remain infrastructure configuration.

---

# 115. Unified RealtimeSession

Do not create separate business-session models for Desktop and Mobile.

Use:

```yaml
realtime_session:
  id:
  user_id:
  organization_id:
  device_id:
  device_type:
  transport:
  voice_profile:
  model_profile:
  project_id:
  portfolio_id:
  cycle_id:
  started_at:
  ended_at:
```

Examples:

```text
Desktop:
transport = LIVEKIT_LOCAL

Mobile:
transport = LIVEKIT_CLOUD
```

Both use the same mCOSA Project/Portfolio/Work/Approval state.

---

# 116. Session Continuity Across Devices

mCOSA business context should be transferable across devices.

Example:

```text
Desktop:
Founder reviews mVault.

Leaves office.

Mobile:
"Tiếp tục phần mVault vừa rồi."
```

Mobile can load:

```text
Current Project
Current Cycle
Recent decision context
Pending approval
Last session summary
```

Do not attempt to migrate a raw LiveKit room between deployments.

Transfer **mCOSA session context**, not media-session identity.

---

# 117. Desktop Local Discovery

Flutter Desktop should detect:

```text
Local LiveKit Server
Local Voice Agent
Local Worker Runtime
```

Health model:

```yaml
local_realtime_health:
  livekit:
  voice_agent:
  worker_runtime:
  last_checked_at:
```

If unhealthy:

```text
AUTO
→ fallback to LiveKit Cloud
```

with user-visible notification.

---

# 118. Local LiveKit Binding

For Desktop single-machine mode:

```text
127.0.0.1 / localhost
```

should be preferred unless LAN access is intentionally enabled.

Do not expose the local LiveKit server publicly by default.

---

# 119. Desktop LAN Mode — Future

Optional future:

```text
Trusted local network
Mobile
→ local LiveKit Desktop server
```

Only add after:

- device pairing;
- TLS;
- access tokens;
- network trust model;
- discovery security;
- firewall guidance.

Not part of MVP.

---

# 120. Mobile Remote Desktop Execution

Mobile request:

> “Triển khai feature này.”

Flow:

```text
Mobile
 ↓
LiveKit Cloud
 ↓
Cloud Voice Agent
 ↓
mCOSA Control Plane
 ↓
Create Technology WorkItem
 ↓
Desktop Device Agent
 ↓
Claude Code CLI
 ↓
Artifact / Events
 ↓
Cloud
 ↓
Mobile
```

Mobile voice never executes local shell directly.

---

# 121. Desktop Voice Execution

Desktop request:

> “Chạy test module Portfolio.”

Flow:

```text
Desktop Voice
 ↓
LiveKit Local
 ↓
Local Voice Agent
 ↓
mCOSA Tool Bridge
 ↓
Policy
 ↓
Local WorkItem
 ↓
Claude Code / Local Worker
```

The architecture may avoid a cloud roundtrip for safe local operations, while audit/sync can occur asynchronously.

---

# 122. Cloud Control Plane Boundary

Cloud remains authoritative for:

```text
Identity
Workspace
Device registry
Remote jobs
Sync metadata
Cross-device approvals
Notifications
Audit aggregation
```

Desktop local runtime remains authoritative for local execution state until synchronized.

Voice transport does not change this boundary.

---

# 123. Local-First Voice Privacy

Recommended Desktop default:

```text
Audio transport:
LOCAL

Transcript:
SUMMARY_ONLY or SESSION_ONLY

Raw audio recording:
OFF
```

If cloud AI is called, send only what the selected model requires.

Future optimization:

```text
Local STT
→ send text only to cloud
```

to avoid uploading raw audio for routine requests.

---

# 124. Cloud Mobile Privacy

Mobile LiveKit Cloud must still respect:

```text
Knowledge scopes
Project restrictions
Data classifications
Transcript policy
Recording policy
Tool permissions
```

A Cloud voice session must not gain access to Desktop-local secrets merely because the Desktop is online.

---

# 125. Local vs Cloud Tool Availability

Desktop Local session may expose:

```text
Local Knowledge
Local Files
Claude Code
Git
Browser
Local MCP
```

Mobile Cloud session may expose:

```text
Cloud-safe Project data
Portfolio data
Remote WorkItem creation
Remote status
Approval
Artifacts
```

Access to local-only tools happens through the Desktop Device Agent and policy.

---

# 126. Tool Capability Discovery

Voice Runtime should retrieve:

```text
available_capabilities
```

from mCOSA rather than assuming tools exist.

Example:

```yaml
capabilities:
  claude_code:
    online: true
    device_id:
  local_knowledge:
    online: true
  browser:
    online: false
```

Voice response can then be accurate.

---

# 127. Hybrid Failure Modes

Handle:

```text
Desktop local LiveKit down
→ Cloud fallback

Cloud unavailable
→ Desktop local continues

Desktop offline while Mobile requests Claude Code
→ WAITING_FOR_DEVICE

Gemini quota unavailable
→ fallback voice profile

DeepSeek unavailable
→ configured fallback

Terra assisted analysis pending
→ show WAITING_FOR_FOUNDER
```

Do not surface all failures as “AI unavailable.”

---

# 128. Voice Profile Configuration

Suggested config:

```yaml
realtime:

  transport:
    desktop: auto
    mobile: livekit_cloud

  desktop_profiles:

    efficient:
      transport: livekit_local
      stt: local
      conversation: deepseek
      tts: local

    natural:
      transport: livekit_local
      realtime_model: gemini_live

    private:
      transport: livekit_local
      stt: local
      conversation: local_model
      tts: local

  mobile_profile:
    transport: livekit_cloud
    realtime_model: gemini_live

  strategy:
    profile: terra
    mode: assisted_chatgpt

  coding:
    provider: claude_code_cli
    execution: desktop_local
```

---

# 129. User Settings

Expose simple settings, not infrastructure complexity.

```text
Voice Mode
● Auto
○ Local
○ Cloud

Desktop Voice Quality
● Efficient
○ Natural
○ Private

Mobile Voice
● Realtime
○ Push-to-Talk only

Strategic Analysis
ChatGPT Terra — Assisted

Coding
Claude Code — Connected
```

Advanced provider configuration lives in Developer/System Settings.

---

# 130. Cost Strategy for OPC

V12.2 is designed around a fixed/low-variable-cost philosophy where practical.

Recommended:

```text
Desktop:
LiveKit Local
+ local audio processing where possible
+ DeepSeek for routine conversation
+ Terra assisted for strategic analysis
+ Claude Code subscription for coding

Mobile:
LiveKit Cloud
+ Gemini Live only when realtime voice is actually used
```

This pushes high-frequency interaction toward lower-cost/local paths and reserves usage-based cloud realtime for mobile or high-value sessions.

---

# 131. Founder Attention vs Compute Cost

Do not optimize only for monetary cost.

Example:

A local voice stack that saves $5/month but causes:

```text
poor recognition
repeated commands
high latency
founder frustration
```

is a bad OPC optimization.

Optimization order:

```text
1. Accepted outcome
2. Founder attention
3. Reliability
4. Privacy/risk
5. Latency
6. Cost
```

within practical budget constraints.

---

# 132. Recommended V12.2 Vertical Slice

Implement:

> Founder uses Desktop local voice during work, then leaves and continues from Mobile cloud voice.

## Desktop

```text
1. Flutter Desktop detects local LiveKit.
2. AUTO selects LOCAL.
3. Founder asks: "Hôm nay tôi cần làm gì?"
4. Local Voice Agent calls NextBestActionService.
5. Response is spoken.
6. Founder says: "Triển khai Portfolio Impact Matrix."
7. Technology WorkItem created.
8. Claude Code begins locally.
```

## Mobile

```text
9. Founder leaves Desktop running.
10. Flutter Mobile uses LiveKit Cloud.
11. Founder asks: "Claude Code đang tới đâu?"
12. Cloud Voice Agent queries Desktop run through Control Plane.
13. Mobile receives spoken status.
14. Job completes.
15. Mobile receives notification/result.
16. Founder approves next action.
```

This validates the entire distributed realtime model.

---

# 133. Second V12.2 Vertical Slice — Strategic Request

Desktop or Mobile:

> “Phân tích PESTEL của mCOSA, mVault và VT Signal.”

Expected:

```text
Voice recognizes strategic intent
 ↓
mCOSA builds Portfolio Analysis request
 ↓
Terra Assisted Analysis package created
 ↓
Founder is told:
"Đây là phân tích chiến lược sâu. Tôi đã chuẩn bị gói phân tích Terra."
 ↓
Founder completes Terra workflow
 ↓
Result imported
 ↓
mCOSA validates evidence
 ↓
Portfolio analysis updated
```

Realtime voice remains responsive instead of pretending to perform deep strategic reasoning immediately.

---

# 134. Migration from V12.1

No destructive migration.

Add:

```text
transport_mode
voice_profile
local_realtime_health
device_realtime_capabilities
session_origin
```

Update `RealtimeTransportResolver`.

Keep:

```text
LiveKitRealtimeTransport
LiveKitVoiceGateway
RealtimeVoiceModel
GeminiLiveRealtimeModel
```

Add:

```text
LiveKitLocalTransport
LiveKitCloudTransport
DesktopVoiceProfileResolver
```

---

# 135. New ADRs

Add:

```text
ADR-LK-011 Hybrid Local/Cloud LiveKit Deployment
ADR-LK-012 Desktop LiveKit Local First
ADR-LK-013 Mobile LiveKit Cloud First
ADR-LK-014 Realtime Transport Resolver AUTO Mode
ADR-LK-015 Local Transport Does Not Imply Local AI
ADR-LK-016 ChatGPT Plus Is Not an API Credential
ADR-LK-017 Terra Assisted Strategic Workflow
ADR-LK-018 Cross-Device Session Context Continuity
ADR-LK-019 OPC Voice Cost Strategy
```

---

# 136. V12.2 Feature Flags

```text
desktop_livekit_local_v12_2
mobile_livekit_cloud_v12_2
realtime_transport_auto_v12_2
desktop_voice_efficient_v12_2
desktop_voice_natural_v12_2
desktop_voice_private_v12_2
cross_device_session_context_v12_2
remote_claude_status_voice_v12_2
```

---

# 137. V12.2 Acceptance Criteria

V12.2 is accepted when:

1. Desktop can run voice through a local LiveKit server.
2. Desktop AUTO mode selects local transport when healthy.
3. Desktop can fall back to cloud transport.
4. Mobile defaults to LiveKit Cloud.
5. Desktop and Mobile map to the same mCOSA business context.
6. Raw LiveKit room identity is not used as the business-session identity.
7. Desktop can use an efficient non-realtime-model voice profile.
8. Desktop can optionally use Gemini Live for natural realtime speech.
9. ChatGPT Plus/Terra is never treated as an API credential.
10. Strategic Terra workflow remains assisted/configurable.
11. Claude Code remains a local Desktop worker.
12. Mobile can query Claude Code status remotely.
13. Mobile can create a remote coding WorkItem.
14. Desktop safe-local operations can execute without unnecessary cloud roundtrips when policy allows.
15. Audit/sync remains consistent after local execution.
16. Tool availability is capability-driven.
17. Desktop local failure is clearly distinguishable from cloud failure.
18. Cloud outage does not unnecessarily break local Desktop voice.
19. No long-lived provider secrets are embedded in Flutter.
20. V10 Hybrid Workforce and V12 Project/Portfolio execution remain unchanged.

---

# 138. Final V12.2 Architecture

```text
                           FOUNDER / CEO
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
          FLUTTER DESKTOP                FLUTTER MOBILE
                 │                             │
                 ▼                             ▼
          LIVEKIT LOCAL                  LIVEKIT CLOUD
                 │                             │
                 ▼                             ▼
        LOCAL VOICE AGENT               CLOUD VOICE AGENT
                 │                             │
       ┌─────────┼─────────┐                   ▼
       ▼         ▼         ▼               GEMINI LIVE
 Local STT    DeepSeek   Gemini                 │
 Local TTS      Chat      Live                  │
       │                   │                    │
       └─────────┬─────────┘                    │
                 ▼                              │
             mCOSA TOOLS ◄──────────────────────┘
                 │
                 ▼
               mCOSA CORE
                 │
       ┌─────────┼─────────────────────────────┐
       ▼         ▼                             ▼
   PROJECT OS  PORTFOLIO OS                 KNOWLEDGE
       │         │                             │
       └─────────┼─────────────────────────────┘
                 ▼
          HYBRID WORKFORCE V10
       ┌─────────┼──────────────┐
       ▼         ▼              ▼
     HUMAN    AI AGENTS      AUTOMATION
                                 │
                     ┌───────────┼───────────┐
                     ▼           ▼           ▼
                CLAUDE CODE    MCP        BROWSER
                     │
                     ▼
                  ARTIFACT
                     │
                     ▼
              POLICY / APPROVAL
                     │
                     ▼
              AUDIT / KNOWLEDGE

Strategic deep reasoning:
mCOSA → Terra Assisted Workflow → CEO Review
```

---

# 139. V12.2 Implementation Recommendation

For the current OPC architecture, use:

## Desktop

```text
LiveKit Local
+
Local STT/TTS where practical
+
DeepSeek for frequent conversational work
+
Gemini Live as optional Natural Voice profile
+
ChatGPT Terra assisted for strategic analysis
+
Claude Code CLI for coding
```

## Mobile

```text
LiveKit Cloud
+
Gemini Live
+
mCOSA Cloud Control Plane
+
Remote Desktop Execution Node
```

## Principle

> **Use local infrastructure for frequent work, cloud realtime where mobility requires it, subscription-assisted reasoning for high-value strategic analysis, and local Claude Code for software execution.**

This model best matches mCOSA's local-first, distributed, one-person-company operating philosophy.
