# COSA Canonical Architecture, Functional & Implementation Guide

> **Revision:** 2026-08-22 — bổ sung Text Chat như first-class primary interaction channel, conversation persistence, streaming event contract, attachments/citations, approval resume và Text ↔ Voice continuity.

> **Loại tài liệu:** Canonical Architecture + Functional Blueprint + Implementation Handbook  
> **Ngày:** 2026-08-22  
> **Code baseline đã đối chiếu:** `vutasoftvn/javis-saas@57c6c2c3d8581dcb4c879b18e26e24137eb5926d`  
> **Phạm vi:** `frontend/`, `services/`, `agentos/`, `services/realtime_agent/`, `skillpacks/`, `infra/`, `deploy/`, `legacy/`  
> **Mục tiêu:** trở thành tài liệu gốc để con người, Claude Code, Codex và các coding agent triển khai COSA thống nhất, không tạo thêm runtime/framework/bounded-context song song.

---

## 0. Authority, mục tiêu và cách dùng tài liệu

Tài liệu này hợp nhất ba loại nội dung trước đây đang nằm rải rác trong repo:

1. **Architecture** — công nghệ nào dùng ở đâu, subsystem nào sở hữu capability nào.
2. **Functional blueprint** — COSA cung cấp chức năng gì và các chức năng kết nối với nhau thế nào.
3. **Implementation handbook** — khi thêm Business Feature, Tool, Skill, Agent, Workflow, Memory Provider, Knowledge Source, Connector, Voice capability hoặc một service mới thì phải làm theo flow nào.

### 0.1. Quy tắc ưu tiên tài liệu

Khi có mâu thuẫn, áp dụng thứ tự sau:

```text
Approved ADR mới hơn
    > COSA Canonical Architecture, Functional & Implementation Guide
    > COSA Canonical Ownership Map
    > Active implementation plan / migration plan
    > README / feature notes / historical architecture docs
    > legacy code comments
```

`README.md` chỉ nên hướng dẫn khởi động và onboarding. README **không được** là nơi định nghĩa canonical architecture.

### 0.2. Ba trạng thái bắt buộc

Mỗi capability phải được hiểu theo ba nhãn:

- **CURRENT** — code/thành phần đang tồn tại tại baseline.
- **TRANSITION** — đang tồn tại nhưng sẽ được thay, port, hợp nhất hoặc retire.
- **TARGET** — vị trí/kiến trúc duy nhất được phép nhận feature mới.

Không được gọi một capability là “canonical production” chỉ vì code đã từng tồn tại hoặc đã có test. **Architecture ownership** và **operational traffic status** là hai khái niệm khác nhau.

### 0.3. Tài liệu bị supersede về định hướng

Các tài liệu cũ vẫn có giá trị lịch sử/audit nhưng không được dùng làm target architecture nếu mâu thuẫn với guide này:

- `docs/architecture/2026-08-22-cosa-core-extraction-plan.md`
- các row cũ trong `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` còn trỏ vào top-level `backend/...`
- các kế hoạch phục hồi Python monolith cũ
- các proposal tạo thêm một `backend/cosa_core/` chứa runtime + auth + identity + control-plane

Lý do không chỉ vì top-level `backend/` không còn tồn tại. Lý do kiến trúc quan trọng hơn là **COSA đã tách thành Business/Control Plane và Agent Plane**; tạo `cosa_core` kiểu cũ sẽ duplicate cả runtime lẫn identity/control-plane.

---

# 1. Executive Architecture Decision

COSA được chuẩn hóa thành bốn vùng trách nhiệm chính:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                             EXPERIENCE PLANE                             │
│ Flutter Desktop/Mobile/Web • Voice • Future Web • External API Clients  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ HTTP / Realtime / Events
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       BUSINESS / CONTROL PLANE                           │
│                         TypeScript + Encore                              │
│                                                                          │
│ control-plane • identity • operations • commercial • finance-legal      │
│ shared contracts/events/schema                                           │
│                                                                          │
│ OWNS: business truth, tenant, RBAC, domain invariants, transactions      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ governed APIs / tools / events
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            AGENT PLANE                                   │
│                              Python                                      │
│                                                                          │
│ context • skills • tools • governance • approvals • memory • knowledge  │
│ workflows • evals • observability • orchestration/runtime adapters      │
│                                                                          │
│ OWNS: agent behavior, reasoning context, autonomy, evaluation            │
└───────────────────────┬──────────────────────┬───────────────────────────┘
                        │                      │
                 orchestration             execution
                        │                      │
                        ▼                      ▼
               ┌────────────────┐    ┌────────────────────┐
               │   Google ADK   │    │  DeepSeek Harness  │
               │ multi-agent    │    │ specialist runtime │
               └────────────────┘    └────────────────────┘

                   Every side effect
                         │
                         ▼
                  COSA Tool Gateway
                         │
                    Governance
                         │
                       Audit
```

## 1.1. Bốn luật nền tảng

1. **`services/` owns business truth.**
2. **`agentos/` owns agent behavior.**
3. **Google ADK và DeepSeek Harness là implementation bên trong Agent Plane, không phải architecture root mới.**
4. **`legacy/` là migration source; không nhận feature production mới.**

## 1.2. Không chuyển toàn bộ COSA sang TypeScript

COSA không cần một ngôn ngữ duy nhất. Boundary đúng quan trọng hơn language uniformity:

- TypeScript/Encore phù hợp cho API, transactions, domain services, auth, tenant, RBAC, event contracts.
- Python phù hợp cho agent runtime, LLM adapters, ADK, DeepSeek Harness SDK, embeddings, evaluation, AI workflows.
- Flutter tiếp tục là experience client.
- Python realtime worker dùng LiveKit có thể tồn tại như channel adapter nhưng không được sở hữu business logic.

---

# 2. Baseline thực tế của repo

## 2.1. Experience Plane — Flutter

`frontend/` hiện dùng Flutter/Dart với các dependency đáng chú ý:

- Dart SDK `^3.12.2`
- GetX `^4.7.3`
- HTTP `^1.6.0`
- LiveKit Client `^2.11.0`
- Speech-to-Text, audio recording/playback
- Shared Preferences
- Markdown rendering

**TARGET:** giữ Flutter làm client chính. Frontend chỉ gọi public Business/Agent API, không biết database nội bộ và không import logic business.

Text Chat phải là **primary interaction channel** của COSA, ngang hàng về capability với Voice nhưng ưu tiên hơn về độ đầy đủ chức năng. Flutter target cần có:

- conversation list / create / rename / archive;
- message timeline;
- streaming Markdown response;
- tool execution status;
- approval cards ngay trong hội thoại;
- citations/evidence links;
- attachment upload;
- retry/regenerate/cancel run;
- specialist/agent selector khi cần;
- chuyển tiếp cùng conversation context giữa Text ↔ Voice.

Text Chat không được gọi thẳng model provider hoặc business database từ Flutter.

## 2.2. Business/Control Plane — TypeScript/Encore

`services/package.json` tại baseline sử dụng:

- `encore.dev ^1.58.2`
- `drizzle-orm ^0.45.2`
- PostgreSQL `pg ^8.23.0`
- TypeScript `^5.7.3`
- Vitest `^3.0.0`
- JWT + bcrypt

Các cluster hiện có:

```text
services/
├── control-plane/
├── identity/
├── operations/
├── commercial/
├── finance-legal/
├── shared/
└── realtime_agent/       # Python deploy unit, không phải Encore service
```

Layering chuẩn đã được repo chốt:

```text
service/
├── encore.service.ts
├── api.ts
├── db.ts
├── handlers/
├── services/
├── models/
├── migrations/
└── tests/
```

**TARGET:** mọi business capability mới ưu tiên mở rộng các bounded context hiện có thay vì tạo microservice mới.

## 2.3. Agent Plane — Python AgentOS

`agentos/` hiện có:

```text
agentos/
├── agents/
├── core/
├── evals/
├── knowledge/
├── memory/
├── observability/
├── skills/
├── tools/
└── workflows/
```

Dependencies trực tiếp trong `agentos/requirements.txt` hiện còn tối giản (`httpx`, `pydantic`, `PyYAML`, pytest). Google ADK và DeepSeek Harness chưa được khai báo ở composition package mới mặc dù legacy từng pin và verify chúng.

**TRANSITION:** AgentOS đang có custom runtime/executor, model gateway, tool registry, policy/approval, memory, knowledge, workflows và evals nhưng composition root chưa wire đầy đủ tất cả capability.

**TARGET:** AgentOS trở thành nền tảng thống nhất, trong đó ADK và DSH được tích hợp qua adapter/port rõ ràng.

## 2.4. Google ADK

Một implementation ADK thật đã tồn tại trong frozen legacy code, dùng `google.adk.workflow.Workflow`, node graph, specialist delegation, governance/approval/quality gates. Legacy requirements từng pin `google-adk==2.7.0`.

**Quan trọng:** đây là **migration reference có code thật**, không được mô tả là current production runtime chỉ vì đã từng verify/test.

**TARGET:** rehost/port hành vi và invariants cần thiết vào `agentos/orchestration/adk`, không `mv` nguyên dependency graph legacy.

## 2.5. DeepSeek Harness

Legacy từng pin `deepseek-harness-sdk==0.1.0rc6`. `agentos/core/adapters/deepseek_harness_provider.py` hiện chỉ bọc phần model-call surface: tạo Harness, chạy một task, lấy `final_response`, rồi AgentOS tự xử lý tool loop.

DeepSeek Harness hiện là sản phẩm **developer preview** và upstream cảnh báo có compatibility-breaking changes.

**TARGET:**

- giữ adapter boundary bắt buộc;
- version pin + compatibility tests;
- dùng DSH như specialist execution runtime khi ADR runtime được chốt;
- không để DSH gọi thẳng business DB/API mà bỏ qua COSA Tool Gateway.

## 2.6. Realtime Voice

`services/realtime_agent` dùng Python 3.11 + LiveKit. Compose truyền `SERVICES_API_URL=http://encore-services:4000`, nhưng code legacy voice tools vẫn có các import/path hack sang backend cũ.

**TARGET:** realtime-agent chỉ làm:

```text
Voice input/output
Session/channel state
Authentication/tenant envelope
Call Agent API
Render partial/final response
```

Không được trực tiếp làm:

```text
SQLAlchemy SessionLocal
CRM/Finance/Strategy query
Founder OS calls
Policy bypass
Direct secret access
```

---

# 3. Canonical Target Repository Structure

```text
COSA/
├── frontend/                         # Flutter experience client
│
├── services/                         # TypeScript/Encore Business + Control Plane
│   ├── control-plane/
│   ├── identity/
│   ├── operations/
│   │   ├── strategy/                 # target logical bounded context
│   │   ├── execution/
│   │   └── planning/
│   ├── commercial/
│   ├── finance-legal/
│   └── shared/
│
├── agentos/                          # Python Agent Plane
│   ├── api/                          # public Agent API: text chat, run events, approvals
│   │   ├── chat/
│   │   ├── runs/
│   │   └── conversations/
│   ├── runtime/
│   │   ├── ports/
│   │   ├── native/
│   │   └── adapters/
│   │       └── deepseek_harness/
│   ├── orchestration/
│   │   └── adk/
│   ├── context/
│   ├── governance/
│   ├── approvals/
│   ├── tools/
│   ├── skills/
│   ├── memory/
│   ├── knowledge/
│   ├── workflows/
│   ├── evals/
│   └── observability/
│
├── skillpacks/                       # Declarative/instruction skills
├── plugins/                          # Extension/plugin metadata where applicable
├── registry/                         # Catalogs/metadata if still needed after audit
├── infra/
├── deploy/
├── tests/
├── docs/
│   └── architecture/
└── legacy/                           # migration source only
```

### 3.1. Forbidden dependency directions

```text
services/  ─X→ agentos internals
agentos/   ─X→ services database
voice      ─X→ legacy business modules
ADK        ─X→ direct business side effects
DSH        ─X→ direct business side effects
skillpack  ─X→ direct database access
frontend   ─X→ internal service DB
```

Allowed:

```text
frontend → public APIs
agentos → services APIs via governed Tool adapters
services → events / public agent API when needed
ADK/DSH → COSA AgentOS contracts
voice → Agent API / services public APIs
```

---

# 4. Functional Architecture — COSA làm gì

COSA là Company/Startup Operating System có AI workforce, không chỉ là chatbot. Chức năng được chia thành các domain sau.

## 4.1. Platform & Company Control

**Owner:** `services/control-plane`

Chức năng:

- đăng ký/đăng nhập;
- platform user;
- company/tenant;
- company membership;
- role;
- plan/license/entitlement;
- authentication token;
- platform-level authorization;
- future billing/entitlement enforcement.

## 4.2. Identity & Hybrid Workforce

**Owner:** `services/identity`

Chức năng:

- workspace projection;
- local identity mapping từ platform user/company;
- workspace member;
- organization;
- human + AI workforce member;
- future org chart/reporting line;
- mapping `Company ↔ Workspace` trong transition.

### Target TenantContext

Mọi request xuyên hệ thống nên resolve về một context thống nhất:

```text
TenantContext
├── company_id
├── workspace_id
├── user_id
├── workforce_member_id?        # human hoặc AI instance
├── membership_role
├── permissions
└── correlation_id
```

Không service nào tự “đoán” company/workspace từ các nguồn khác nhau.

## 4.3. Strategy & Startup Co-Founder Methodology

**Owner:** logical bounded context `services/operations/strategy`

Đây là lớp cần bổ sung quan trọng nhất từ Founder OS cũ.

Canonical flow:

```text
Project / Venture
      ↓
Stage
      ↓
Assumption / Risk
      ↓
Experiment
      ↓
Evidence
      ↓
Gate Evaluation
      ↓
Decision
      ↓
Next Best Action
      ↓
Initiative / Task / OKR / 12WY
```

Các entity target:

- `projects`
- `stage_policies`
- `stage_transitions`
- `assumptions`
- `experiments`
- `evidence`
- `interviews`
- `discovery_signals`
- `gate_evaluations`
- `decision_records`
- `next_action_candidates`
- `next_action_rankings`

Không port nguyên `founder_os/`. Chỉ port domain concept, invariants, scoring/evidence rules và test cases có giá trị.

## 4.4. Execution & Planning

**Owner:** `services/operations`

Current schemas đã có:

- initiatives;
- tasks;
- task dependencies;
- task schedules;
- OKR cycles/objectives/key results;
- 12-week cycles;
- weekly plans;
- weekly commitments;
- portfolios;
- projects;
- portfolio-project relations.

Target business flow:

```text
Strategy Decision
      ↓
Initiative
      ↓
OKR / 12WY plan
      ↓
Task graph
      ↓
Human / AI assignment
      ↓
Execution
      ↓
Evidence / progress
      ↓
Score / review
      ↓
Strategy feedback
```

## 4.5. Commercial

**Owner:** `services/commercial`

Chức năng:

- accounts;
- contacts;
- leads;
- opportunities;
- customers;
- campaigns;
- marketing assets/forms/intake;
- invoices/subscriptions where this domain currently owns them.

Startup Strategy không duplicate CRM. Ví dụ:

```text
Experiment → sourceExperimentId → Lead
Interview → Contact reference
Evidence → Opportunity / Payment / Conversion reference
```

## 4.6. Finance & Legal

**Owner:** `services/finance-legal`

Chức năng:

- transactions/accounting records;
- accounting periods;
- legal obligations;
- checklists/compliance-related work;
- future runway/cash/risk projection.

Mọi action tài chính/pháp lý từ agent bắt buộc qua Tool Gateway + policy/approval.

## 4.7. Agent Assistant / AI Workforce

**Owner:** `agentos/`

Chức năng:

- chat/reasoning;
- company-context synthesis;
- skill routing;
- specialist delegation;
- multi-agent orchestration;
- tool calling;
- permission/approval;
- memory;
- knowledge retrieval;
- workflow execution;
- evaluation;
- cost/usage/trace;
- explain Next Best Action;
- produce draft/plan/recommendation;
- execute approved operations.

## 4.8. Text Chat — primary interaction channel

**Owner:** Agent Plane (`agentos/`) cho runtime/API; Flutter cho experience UI.

Text Chat là giao diện chính để Founder/Operator làm việc với COSA. Đây không phải một LLM chat box độc lập mà là **conversation surface của toàn bộ Company OS**.

Chức năng tối thiểu:

- tạo/tiếp tục conversation;
- chat với Co-Founder agent hoặc specialist;
- hỏi dữ liệu doanh nghiệp theo quyền;
- hỏi Knowledge/RAG và nhận citation;
- sử dụng Memory để duy trì context dài hạn;
- lập kế hoạch, phân tích, tạo draft;
- yêu cầu agent thực hiện action;
- xem tool đang chạy/kết quả tool;
- nhận approval request và approve/reject ngay trong conversation;
- cancel/retry một run;
- attach file/tài liệu;
- tạo Task/OKR/Experiment/Lead/... qua governed tools;
- tiếp tục cùng conversation từ Voice.

Canonical distinction:

```text
Conversation transcript
    ≠ Agent Memory
    ≠ Knowledge
    ≠ Business record
```

Conversation/message là lịch sử tương tác. Memory là thông tin được chọn/consolidate để tái sử dụng. Knowledge là tài liệu/chunks có provenance. Business record là dữ liệu domain do `services/` sở hữu.

## 4.9. Voice

Voice không phải domain riêng. Nó là channel cho cùng Agent/Business capability.

```text
Voice → Session → Agent Request → same Context/Skill/Tool/Governance → Response → Voice
```

Text Chat và Voice **bắt buộc dùng cùng Agent API, Tool Registry, Skills, Memory, Knowledge và Governance**; không được có hai bộ business/tool logic khác nhau.

---

# 5. Canonical End-to-End Product Flows

## 5.1. User onboarding

```text
Flutter
  ↓ register/login
Control Plane
  ↓ create/join Company
Identity
  ↓ sync Company → Workspace
  ↓ create WorkspaceMember
Frontend receives TenantContext
  ↓
COSA workspace ready
```

Acceptance:

- một user có thể thuộc nhiều company;
- mỗi request có company/workspace scope rõ;
- role không bị tự map mơ hồ giữa platform và local identity;
- agent request mang cùng tenant context.

## 5.2. Startup strategy flow

```text
Founder describes venture/problem
  ↓
Agent retrieves Company + Project + Memory + Knowledge
  ↓
Stage assessment
  ↓
Load stage-specific Skill
  ↓
Identify assumptions / unknowns
  ↓
Propose experiments
  ↓ approval if execution writes/external actions
Create experiment in services/operations/strategy
  ↓
Commercial/Research activity generates evidence
  ↓
Evidence normalized and linked
  ↓
Gate evaluation
  ↓
Decision record
  ↓
Deterministic NBA candidate scoring
  ↓
LLM explains / critiques / reranks within constraints
  ↓
Initiative / Task / OKR / 12WY creation
```

### Next Best Action rule

LLM không tự invent priority từ prompt trống. Candidate score phải dựa trên deterministic signals như:

- startup stage;
- unresolved assumptions;
- evidence strength;
- blocked tasks;
- OKR gap;
- commercial signals;
- cash/runway;
- legal risk;
- founder attention budget.

LLM dùng để **explain/critique/rerank** trong boundary, không thay business rules.

## 5.3. Text Chat flow — canonical

```text
Flutter Text Composer
      ↓
Create/Resume Conversation
      ↓
POST Agent Request
      ↓
Authenticate + resolve TenantContext
      ↓
Persist user message
      ↓
Create AgentRun
      ↓
ContextBuilder
  ├─ recent conversation turns
  ├─ selected Memory
  ├─ retrieved Knowledge
  ├─ Skill instructions
  └─ business snapshot via read tools/APIs
      ↓
Orchestrate
  ├─ simple request → native/runtime path
  ├─ multi-agent mission → Google ADK
  └─ specialist execution → DeepSeek Harness
      ↓
Stream Agent Events
  ├─ run.started
  ├─ message.delta
  ├─ tool.started / tool.completed
  ├─ approval.required
  ├─ citation
  ├─ error
  └─ run.completed
      ↓
Governed Tool Gateway when side effect is needed
      ↓
services/ business APIs
      ↓
Persist final assistant message + run summary
      ↓
Memory consolidation / Eval / Telemetry asynchronously
```

Nếu gặp action cần approval:

```text
AgentRun
  ↓
approval.required
  ↓ stream event
Flutter renders approval card
  ↓ Founder approves/rejects
Approval API
  ↓
resume SAME run
  ↓
execute / deny
  ↓
continue streaming
```

Không tạo một run mới làm mất causal chain chỉ vì có approval.

## 5.4. Agent tool execution flow

```text
User/Workflow/ADK/DSH
        ↓
Agent Request
        ↓
TenantContext
        ↓
ContextBuilder
   ├─ memory
   ├─ knowledge
   ├─ skills
   └─ business snapshot
        ↓
Plan / Orchestrate
        ↓
Tool intent
        ↓
Tool Registry
        ↓
Governance Decision
   ├─ RBAC entitlement
   ├─ Agent PermissionLevel
   ├─ Tool Risk
   ├─ Tenant Policy
   └─ Execution Mode
        ↓
ALLOW / APPROVAL / DENY
        ↓
Tool adapter
        ↓ HTTP/RPC
services/
        ↓ transaction
Domain Event
        ↓
Audit + Trace + Memory/Eval feedback
```

## 5.5. Voice flow target

```text
Flutter LiveKit client
     ↓ audio
LiveKit
     ↓
Realtime Agent
     ↓ signed TenantContext + optional conversation_id
Agent API
     ↓
AgentOS
     ↓
ADK/DSH/native runtime as appropriate
     ↓
Governed Tool Gateway
     ↓
Services
     ↓
Streaming answer/events
     ↓
Realtime Agent
     ↓ voice
Flutter
```

---

# 6. Technology Stack — Canonical Decision Matrix

| Layer | Technology | Status | Decision |
|---|---|---|---|
| Client | Flutter/Dart | CURRENT/TARGET | Keep |
| Client state | GetX | CURRENT | Keep until explicit frontend ADR |
| Text chat UI | Flutter | TARGET FIRST-CLASS | Primary interaction channel |
| Text streaming | SSE/event stream (WebSocket only when bidirectional semantics are required) | TARGET | Canonical text-run event transport |
| Agent API | Python AgentOS API boundary | TARGET | Own conversations/runs/chat events, never business truth |
| Business APIs | TypeScript + Encore | CURRENT/TARGET | Canonical |
| ORM | Drizzle | CURRENT/TARGET | Canonical for services |
| Business DB | PostgreSQL 16 | CURRENT/TARGET | Source of truth |
| Vector extension | pgvector | CURRENT/TARGET | Knowledge vectors; memory optional provider |
| Agent platform | Python AgentOS | CURRENT/TRANSITION/TARGET | Canonical Agent Plane |
| Multi-agent orchestration | Google ADK | LEGACY REFERENCE → TARGET ADAPTER | Port behavior, not legacy dependency graph |
| Specialist runtime | DeepSeek Harness | CURRENT thin provider → TARGET runtime adapter | Keep boundary, pin version |
| Native agent loop | AgentOS Executor | CURRENT | Fallback/test/simple runtime unless ADR promotes it |
| Voice | LiveKit + Python worker | CURRENT/TARGET channel | Remove business/legacy coupling |
| Local trace/checkpoint | SQLite | CURRENT/TARGET limited scope | Not business truth |
| Knowledge | AgentOS + pgvector | CURRENT/TARGET | Separate from memory |
| Agent memory | Provider interface | TRANSITION/TARGET | SQLite / pgvector / Agent Memory adapters |
| Object/blob | MinIO/object storage | CURRENT direction | Artifacts/blobs |
| Telemetry | OpenTelemetry | TRANSITION/TARGET | Unified distributed trace |
| Tests TS | Vitest/Encore test | CURRENT | Required |
| Tests Python | pytest | CURRENT | Required |
| Containers | Docker Compose | CURRENT | Local/dev; production topology separate |

---

# 7. Data Architecture

## 7.1. Data ownership

```text
Business truth          → PostgreSQL via services/
Conversation/messages   → Agent Plane conversation store
Agent runtime state     → runtime/session store
Local checkpoint/trace  → SQLite (bounded, redacted)
Agent memory            → Memory provider
Knowledge/RAG           → pgvector knowledge store
Files/artifacts          → MinIO/object storage
Telemetry               → OpenTelemetry collector/backend
Audit/compliance        → durable audit projection
```

## 7.2. Memory ≠ Knowledge ≠ Business Data

### Business data

Examples:

- company;
- customer;
- invoice;
- transaction;
- task;
- OKR;
- experiment;
- legal obligation.

Agent chỉ truy cập thông qua service API/tool.

### Conversation & Message History

Conversation history là dữ liệu của Agent Plane, dùng để:

- hiển thị lại hội thoại;
- resume context;
- reconstruct causal chain của một AgentRun;
- gắn tool events/approval/citations với đúng message;
- đồng bộ Text ↔ Voice;
- phục vụ audit/debug ở mức interaction.

Target persistence model tối thiểu:

```text
Conversation
- id
- company_id
- workspace_id
- created_by_principal
- title
- active_agent/profile
- created_at / updated_at / archived_at

Message
- id
- conversation_id
- role
- content
- run_id
- parent_message_id
- status
- created_at

MessageAttachment
- id
- message_id
- object_ref
- media_type
- file_name
- size
- checksum
- knowledge_ingest_status

RunEvent
- run_id
- sequence
- event_type
- payload_redacted
- created_at
```

**TARGET:** server/multi-device mode dùng durable Postgres-backed conversation store thuộc Agent Plane; SQLite chỉ được dùng cho local/offline cache/checkpoint khi có retention và sync semantics rõ.

Conversation transcript **không tự động trở thành Memory**. Memory consolidation là bước riêng, có policy chọn lọc và retention riêng.

Attachment binary không lưu trực tiếp trong message row; lưu object storage. Khi attachment được dùng làm RAG source, hệ thống tạo Knowledge source/chunks với provenance trỏ ngược về attachment/message.

### Memory

Memory là điều agent “nhớ” để hành xử tốt hơn:

- WORKING;
- EPISODIC;
- SEMANTIC;
- PROCEDURAL;
- ORGANIZATIONAL.

Memory cần isolation tối thiểu:

```text
company/workspace
principal/agent
namespace/kind
retention policy
```

### Knowledge

Knowledge là corpus có thể ingest/chunk/embed/retrieve:

- company docs;
- manuals;
- contracts;
- market research;
- strategy files;
- product docs.

Không lưu business state mutable dưới dạng knowledge vector và coi nó là source of truth.

## 7.3. SQLite rule

Được phép:

- local trace;
- runtime checkpoint;
- local cache;
- local-first memory provider;
- test fixtures.

Không được phép:

- authoritative CRM;
- accounting ledger;
- company membership;
- legal obligations;
- canonical task state.

## 7.4. Trace redaction

Current `SqliteTraceSink` từng ghi raw payload JSON. Đây là P0 security issue.

Trước production cutover phải có:

- secret redaction;
- PII filtering rules;
- configurable payload capture;
- retention;
- maximum payload size;
- correlation id;
- tenant scoping.

---

# 8. Identity, RBAC và Agent Permission

Không gộp RBAC và agent autonomy thành một enum.

## 8.1. RBAC

**Owner:** Business/Control Plane.

Trả lời:

> Principal này trong company được phép làm gì?

Ví dụ:

- Founder/Admin;
- Finance;
- Sales;
- Member;
- Auditor.

## 8.2. Agent PermissionLevel

**Owner:** AgentOS Governance.

Trả lời:

> Agent được tự chủ đến mức nào?

Canonical vocabulary hiện có hướng L0-L3:

```text
L0_READ
L1_SUGGEST
L2_DRAFT
L3A_EXECUTE_WITH_APPROVAL
L3_EXECUTE
```

## 8.3. Tool Risk

Tool phải có risk level riêng:

```text
LOW      read/query/retrieve
MEDIUM   internal mutable data with bounded impact
HIGH     external write, finance, deploy, delete, secrets
CRITICAL irreversible/high-value action if introduced later
```

## 8.4. ExecutionMode

Ví dụ:

- INTERACTIVE
- APPROVED_WORKFLOW
- AUTONOMOUS_SAFE

## 8.5. Canonical decision function

```text
Decision =
    RBAC/Entitlement
  ∩ TenantPolicy
  ∩ AgentPermissionLevel
  ∩ ToolRisk
  ∩ ExecutionMode
  ∩ DataScope
```

Output:

```text
ALLOW
REQUIRE_APPROVAL
DENY
```

`PermissionClass` hiện tại được giữ như metadata/migration vocabulary trong giai đoạn chuyển đổi; không nên là decision mechanism cuối cùng duy nhất.

---

# 9. AgentOS Runtime Architecture

## 9.1. Vai trò của AgentOS

AgentOS là integration platform, không phải một LLM wrapper duy nhất.

```text
AgentOS
├── Context
├── Skills
├── Tools
├── Governance
├── Approval
├── Memory
├── Knowledge
├── Workflows
├── Evaluation
├── Observability
├── Orchestration ports/adapters
└── Runtime ports/adapters
```

## 9.2. Composition root

Current `build_default_runtime()` có thể tạo `ToolRegistry()` rỗng và `AgentRuntime` hiện tạo `ContextBuilder(tool_registry)` mà không inject memory/skills/knowledge mặc định.

**TARGET composition:**

```text
build_production_agent_platform()
├── TenantContextResolver
├── ModelGateway
├── ADK Orchestrator
├── DeepSeekHarness RuntimeAdapter
├── Native RuntimeAdapter
├── ToolRegistry (cluster tools registered)
├── GovernanceEngine
├── ApprovalService
├── SkillRegistry + Router + InstructionLoader
├── MemoryService
├── KnowledgeRetriever
├── WorkflowEngine
├── AuditSink
├── Trace/OTEL
└── Eval hooks
```

Production entrypoint không được tự tạo một phần các dependency và silently bỏ qua phần còn lại.

## 9.3. Runtime lựa chọn

### Google ADK

Dùng cho:

- multi-agent orchestration;
- specialist routing;
- graph/nodes;
- parallel delegation;
- mission lifecycle;
- A2A sau này nếu cần.

Không dùng cho:

- business DB transaction;
- RBAC authority;
- accounting rules;
- stage/evidence business truth.

### DeepSeek Harness

Dùng cho:

- specialist execution;
- agent loop khi cần Harness capability;
- plugin/runtime ecosystem của DSH;
- long reasoning/tool execution trong governed sandbox.

Không được bypass:

- Tool Gateway;
- approval;
- tenant scope;
- audit.

### AgentOS Native Runtime

Dùng cho:

- tests;
- simple agents;
- fallback;
- deterministic/simple tool loop;
- compatibility while ADK/DSH integration matures.

Không phát triển Native Runtime thành framework thứ ba cạnh tranh nếu capability đó đã thuộc ADK/DSH.

---

# 10. Tool System — chuẩn bổ sung Tool

## 10.1. Tool là gì

Tool là **governed capability adapter** cho phép agent đọc hoặc thay đổi một hệ thống khác.

Tool không phải business implementation.

Sai:

```text
Tool handler → SQL INSERT vào CRM
```

Đúng:

```text
Tool handler → Services API → Commercial service → DB transaction
```

## 10.2. Current ToolSpec

Current code có:

```python
ToolSpec(
    name,
    description,
    handler,
    permission_class,
)
```

Nó quá mỏng cho production governance.

## 10.3. Target ToolSpecV2 — PROPOSED

> Đây là target schema, **chưa phải current code**.

```python
ToolSpecV2(
    name="operations.task_create",
    version="1.0.0",
    description="Create a task in a workspace",
    input_schema=...,            # JSON Schema / Pydantic
    output_schema=...,
    handler=...,
    permission_class="MODIFY_BUSINESS_DATA",
    risk_level="medium",
    write_scope="workspace",
    idempotent=True,
    reversible=False,
    approval_policy="conditional",
    audit_policy="full",
    timeout_seconds=15,
    tags=["operations", "task"],
)
```

Target metadata tối thiểu:

- stable name;
- semantic version;
- description;
- input schema;
- output schema;
- permission class;
- risk level;
- data/write scope;
- idempotency;
- reversibility;
- approval policy;
- audit policy;
- timeout;
- tags/domain.

## 10.4. Flow thêm Tool mới

### Bước 1 — xác định business owner

Ví dụ yêu cầu “tạo experiment”:

```text
Business owner = services/operations/strategy
```

Không bắt đầu từ AgentOS.

### Bước 2 — implement business API trước

Trong Encore service:

```text
handler → service → DB transaction → domain event
```

Có:

- validation;
- tenant scope;
- RBAC;
- idempotency cho write retry được;
- migration nếu cần;
- service unit/integration test.

### Bước 3 — tạo AgentOS adapter

Ví dụ target:

```text
agentos/tools/clusters/strategy_tools.py
```

Handler chỉ:

1. validate tool input;
2. inject trusted tenant context;
3. gọi Encore client;
4. normalize output/error.

### Bước 4 — khai governance metadata

Xác định:

- read/write;
- risk;
- approval;
- idempotency;
- principal scope.

### Bước 5 — register

Tool phải được đăng ký từ **một composition path canonical**. Không để production caller tự tạo `ToolRegistry()` rỗng.

### Bước 6 — contract tests

Bắt buộc:

- schema test;
- risk/permission test;
- tool registry test;
- mocked transport test;
- live HTTP pilot test với Encore nếu tool production-critical;
- retry/idempotency test cho write;
- unauthorized tenant test.

### Bước 7 — cập nhật Skill/Eval

Nếu tool phục vụ skill, cập nhật:

- `manifest.yaml` permissions;
- `SKILL.md` flow;
- eval cases.

## 10.5. Tool naming

Khuyến nghị canonical:

```text
<domain>.<resource>.<action>
```

Ví dụ:

```text
operations.task.create
strategy.experiment.create
commercial.lead.list
finance.transaction.create
identity.workspace.get
```

Trong transition có thể giữ tên underscore cũ để compatibility nhưng catalog mới nên có namespace rõ.

---

# 11. Skill System — chuẩn bổ sung Skill

## 11.1. Skill là gì

Skill là **knowledge/instruction/capability package giúp agent biết cách thực hiện một loại công việc**.

Skill không phải:

- service;
- database;
- agent runtime;
- tool implementation;
- một chatbot độc lập.

Current repo có pattern:

```text
skillpacks/<skill>/
├── manifest.yaml
└── SKILL.md
```

Ví dụ `skillpacks/okr/manifest.yaml` hiện có:

- `apiVersion`;
- `kind`;
- metadata id/name/version/description;
- publisher;
- source;
- capability domain/category/intents;
- runtime;
- required permissions;
- risk level;
- trust tier.

## 11.2. Flow thêm Skill mới

### Bước 1 — define capability

Ví dụ:

```text
ID: strategy.customer-discovery
Domain: strategy
Category: validation
Intents:
- plan customer interview
- synthesize interview evidence
- assess problem validation
```

### Bước 2 — xác định Tool dependencies

Skill phải chỉ rõ nó cần tool nào.

Ví dụ:

```text
strategy.interview.create
strategy.evidence.create
commercial.contact.get
knowledge.search
```

Nếu tool chưa tồn tại, tạo tool theo flow §10 **trước** khi tuyên bố skill executable.

### Bước 3 — tạo manifest

Template:

```yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: strategy.customer-discovery
  name: Customer Discovery
  version: 1.0.0
  description: Conduct and synthesize structured customer discovery.

publisher:
  name: javis
  type: official

source:
  type: local
  path: skillpacks/customer-discovery

capability:
  domain: strategy
  category: validation
  intents:
    - plan customer interview
    - synthesize interview evidence
    - assess problem validation

runtime:
  environment: python
  entrypoint: instructions

permissions:
  required:
    - READ_LOCAL
    - MODIFY_BUSINESS_DATA

risk:
  level: medium

trust:
  tier: T0
```

### Bước 4 — viết `SKILL.md`

`SKILL.md` phải chứa:

1. mục tiêu;
2. khi nào dùng / không dùng;
3. prerequisites/context;
4. deterministic steps;
5. tool calls được phép;
6. approval points;
7. output format;
8. failure/edge cases;
9. examples;
10. evidence requirements.

Không viết kiểu prompt chung chung “hãy làm tốt nhất”.

### Bước 5 — supply-chain/trust

Internal official skill hiện thường dùng `T0`. Skill bên ngoài phải đi qua supply-chain validation theo trust tier và policy hiện hành.

### Bước 6 — routing tests

Test:

- đúng intent → skill được chọn;
- intent gần nhưng không phù hợp → không chọn;
- tool permission không đủ → skill không được execute;
- missing prerequisite → agent hỏi/đề xuất thay vì hallucinate.

### Bước 7 — Skill Eval

Định nghĩa eval cases:

```text
input
expected selected skill
expected/forbidden tool calls
success criteria
business outcome metric
```

Quality score phải lấy từ outcome thật, không tự gán điểm đẹp trong manifest.

## 11.3. Khi nào không tạo Skill

Không tạo Skill mới nếu yêu cầu chỉ là:

- một API CRUD mới → Tool;
- business rule mới → services domain logic;
- một sequence retry/approval → Workflow;
- một persona/specialist → Agent Profile;
- corpus docs → Knowledge Source.

---

# 12. Agent Profile & AI Workforce

## 12.1. Hai identity khác nhau

### Workforce identity

Business identity của một nhân sự cụ thể trong company:

```text
WorkforceMember
Human hoặc AI instance
```

Owner target: `services/identity`.

### Agent Profile

Runtime definition:

```text
role/persona
skills
allowed tools
permission level
preferred runtime/model
quality policy
```

Owner: AgentOS.

Không dùng Agent Profile làm tenant membership record.

## 12.2. Target Agent Profile

```yaml
id: sales.researcher
name: Sales Researcher
version: 1.0.0
mission: Research and qualify commercial opportunities.

skills:
  - commercial.lead-research
  - strategy.customer-discovery

tools:
  allow:
    - commercial.contact.get
    - commercial.lead.create
    - knowledge.search

permission_level: L2_DRAFT
preferred_runtime: deepseek_harness
fallback_runtime: native

limits:
  max_tool_calls: 20
  max_cost_usd: 1.0
  max_runtime_seconds: 300
```

## 12.3. Flow thêm specialist agent

1. xác định trách nhiệm không overlap specialist có sẵn;
2. define Agent Profile;
3. gán Skill trước, Tool sau;
4. set PermissionLevel;
5. set budget/time/tool constraints;
6. chọn runtime preference;
7. register trong specialist registry/ADK adapter;
8. eval routing;
9. eval output quality;
10. eval forbidden actions;
11. map sang WorkforceMember nếu agent được “hire” vào một company.

---

# 13. Workflow — chọn đúng engine

COSA có ba loại workflow khác nhau. Không được dùng một engine cho mọi việc.

## 13.1. Business state machine

Ví dụ:

- Lead stage transition;
- Invoice lifecycle;
- Experiment state;
- Legal obligation status;
- Project gate.

**Owner:** `services/` domain tương ứng.

Lý do: đây là business truth và transaction invariant.

## 13.2. Deterministic Agent Workflow

Ví dụ:

- Retry tool;
- approval pause/resume;
- compensation;
- sequential/parallel execution;
- checkpoint;
- versioned agent procedure.

**Owner:** `agentos/workflows`.

Mọi write vẫn qua governed tools.

## 13.3. Multi-agent cognitive orchestration

Ví dụ:

- Co-Founder mission;
- parallel specialist analysis;
- synthesize outputs;
- quality gate;
- ask founder confirmation;
- delegate/rejoin.

**Owner:** `agentos/orchestration/adk`.

## 13.4. Quy tắc chọn

```text
Có thay đổi authoritative business state?
  └─ YES → services state machine

Là procedure deterministic của agent?
  └─ YES → agentos/workflows

Cần specialist/multi-agent reasoning graph?
  └─ YES → ADK orchestration
```

---

# 14. Memory Provider — chuẩn mở rộng

## 14.1. Target interface

Một abstraction thống nhất:

```text
MemoryService
├── put
├── search
├── delete/forget
├── consolidate
├── retention
└── namespace/isolation
```

Target adapters:

```text
agentos/memory/providers/
├── local_sqlite.py
├── pgvector.py
└── tencent_agent_memory.py
```

> Đây là target organization; current repo chưa có đầy đủ `providers/` như trên.

## 14.2. Khi thêm Memory Provider

Bắt buộc test:

- workspace isolation;
- agent/principal isolation;
- namespace isolation;
- retention/forget;
- relevance ranking;
- offline behavior;
- failure behavior không silent no-op;
- migration/backup story.

## 14.3. Không silent no-op

Production store không được kiểu:

```text
no session factory → put returns silently
```

Phải fail fast hoặc explicit `UnavailableMemoryBackend` tùy mode.

---

# 15. Knowledge Source — chuẩn ingest RAG

## 15.1. Pipeline

```text
Source
  ↓
Parse
  ↓
Normalize
  ↓
Chunk
  ↓
Embed
  ↓
Index pgvector
  ↓
Retrieve
  ↓
Citations/metadata
```

Current AgentOS knowledge layer đã có chunking, embedding provider abstraction và pgvector cosine retrieval; parse file formats và production DB ownership/migrations cần chốt rõ trước production.

## 15.2. Flow thêm source

1. define source type;
2. define parser;
3. preserve source metadata;
4. chunk strategy;
5. embedding model/version;
6. tenant scope;
7. upsert/idempotency;
8. delete/reindex flow;
9. retrieval eval;
10. citations/provenance.

Không cho LLM ingest file rồi bỏ mất source/metadata.

---

# 16. Connector, MCP, Plugin & External Integration

## 16.1. Nguyên tắc

External integration có hai tầng:

```text
Connector transport/auth
       ↓
COSA Tool adapter
       ↓
Governance
```

Không expose raw MCP/external client trực tiếp cho model mà thiếu policy metadata.

## 16.2. Flow thêm connector

Ví dụ Google Ads, Slack, Notion, n8n:

1. define external auth ownership;
2. secret lưu vault/secret store, không memory;
3. implement transport client/MCP adapter;
4. map operation thành ToolSpec;
5. classify read/write/external risk;
6. tenant-scoped credentials;
7. approval cho external write;
8. audit request/response metadata có redaction;
9. rate limit/retry/circuit breaker;
10. connector integration tests.

## 16.3. OAuth

OAuth/external account linking là identity/integration capability, không nên sống trong skillpack. Legacy implementation có thể là migration reference; target ownership phải được ADR chốt giữa `services/identity` và integration adapter layer.

---

# 17. Conversation Channels — Text Chat & Realtime Voice

Text và Voice là **channel adapters**, không phải hai agent system riêng.

## 17.1. Text Chat capability

Text Chat là channel chuẩn để triển khai capability mới trước tiên vì dễ quan sát, test, approval và debug hơn voice.

### 17.1.1. Agent Chat API target

Agent Plane cần public contract ổn định, ví dụ:

```text
POST   /agent/conversations
GET    /agent/conversations
GET    /agent/conversations/{conversation_id}
PATCH  /agent/conversations/{conversation_id}
POST   /agent/conversations/{conversation_id}/messages
POST   /agent/runs/{run_id}/cancel
POST   /agent/approvals/{approval_id}/decision
GET    /agent/runs/{run_id}/events     # SSE/event stream
```

Tên route cụ thể có thể thay đổi theo HTTP ADR; semantics không được thay đổi tùy framework.

Request phải chứa/resolve:

```text
authenticated principal
company_id
workspace_id
conversation_id
message
optional agent/profile
optional attachment refs
optional client metadata
```

Client không gửi trusted `PermissionLevel`, role hay tenant policy; server resolve từ canonical identity/governance data.

### 17.1.2. Streaming event contract

Text response không chỉ stream token. Event stream phải biểu diễn state machine của run:

```text
run.started
message.started
message.delta
reasoning.status          # chỉ status/metadata, không expose private chain-of-thought
tool.requested
tool.started
tool.completed
tool.failed
approval.required
approval.resolved
citation
attachment.processed
run.completed
run.cancelled
run.failed
```

Mỗi event cần:

```text
run_id
conversation_id
sequence
event_type
timestamp
payload
correlation_id
```

Sequence phải monotonic trong một run để client reconnect có thể resume/dedupe.

### 17.1.3. Chat UI target

Flutter Chat surface tối thiểu có:

- sidebar conversation;
- new chat;
- title/rename/archive;
- message composer;
- streaming Markdown;
- code/table rendering;
- attachment chips;
- citation/evidence cards;
- tool activity cards;
- approval card;
- cancel/retry;
- error/reconnect state;
- agent/specialist identity;
- run status;
- chuyển sang voice với cùng `conversation_id`.

Không render raw internal trace, secret hoặc private reasoning chain.

### 17.1.4. Attachment flow

```text
User selects file
  ↓
Upload to object storage
  ↓
Create attachment metadata
  ↓
Send message with attachment_ref
  ↓
Content-type policy
  ├─ small text/image input → runtime context when allowed
  └─ document corpus → Knowledge ingest pipeline
                       ↓
                   chunks + provenance
                       ↓
                   retrieval + citations
```

Malware/file-type/size policy phải chạy trước ingest. Attachment không được biến thành business record nếu chưa có explicit business import flow.

### 17.1.5. Add a new Chat capability correctly

```text
Need “chat can do X”
      ↓
X only changes presentation?
  YES → Flutter/Agent API event contract
  NO
      ↓
X changes business state?
  YES → services domain/API first
      ↓
Tool adapter + governance
      ↓
Skill/workflow/orchestration
      ↓
Text Chat exposes existing Agent capability
```

Không tạo `chat_tools.py` chứa business implementation riêng chỉ để chat dùng được.

## 17.2. Realtime/Voice Capability

Khi muốn voice agent có thêm chức năng, **không thêm business logic trực tiếp vào `voice_tools.py`**.

Flow:

```text
Need new voice capability
  ↓
Capability already exists through Agent API?
  ├─ YES → voice invokes same capability
  └─ NO  → implement Business API → Tool → Skill/Agent behavior first
              ↓
          expose through Agent API
              ↓
          Voice consumes it
```

Voice-specific code chỉ xử lý:

- turn detection;
- interruption;
- audio stream;
- transcript;
- speaking state;
- latency;
- session metadata.

Voice session nên nhận `conversation_id` khi user tiếp tục hội thoại hiện có. Transcript user/assistant cuối cùng được persist theo cùng conversation model; audio binary có retention policy riêng.

## 17.3. Text ↔ Voice continuity

```text
Text Chat conversation
       ↓ start voice
same conversation_id
       ↓
Realtime Agent
       ↓
same TenantContext + Memory + Knowledge + Skills
       ↓
voice turns persisted as messages/transcripts
       ↓ stop voice
Flutter returns to Text Chat
       ↓
conversation continues without context reset
```

Channel-specific state không được trở thành canonical business/agent state.

---

# 18. Thêm Business Feature / Domain Capability

## 18.1. Decision tree

Ví dụ user muốn “quản lý customer interview evidence”.

```text
Business record cần tồn tại lâu dài?
  YES
    ↓
Chọn owner service
    ↓
services/operations/strategy
    ↓
Schema + migration
    ↓
Service logic
    ↓
Handler/API
    ↓
Event
    ↓
Tool adapter
    ↓
Skill
    ↓
Agent/Workflow integration
    ↓
Frontend
```

Không bắt đầu từ prompt/agent rồi mới nghĩ database sau.

## 18.2. New microservice gate

Chỉ tạo `services/<new-service>` khi cả ba đúng:

1. có bounded context độc lập rõ ràng;
2. lifecycle/data ownership khác các service hiện có;
3. mở rộng service hiện tại làm coupling xấu đáng kể.

Nếu không, mở rộng cluster hiện tại.

---

# 19. Startup Co-Founder Functional Model

Đây là một capability lõi của COSA nên được chuẩn hóa thành business model, không chỉ prompt.

## 19.1. Stage model

Có thể giữ stage vocabulary S0-S6 nếu được product team duyệt, nhưng stage phải là domain policy/versioned configuration, không hardcode rải rác trong agent prompt.

## 19.2. Assumption

Mỗi assumption cần:

```text
id
project_id
stage
category
statement
importance
uncertainty
risk_score
status
owner
created_at
```

## 19.3. Experiment

```text
hypothesis
assumption_ids
method
success criteria
start/end
cost/budget
status
owner
linked commercial campaign/form
```

## 19.4. Evidence

```text
source_type
source_ref
claim
strength
confidence
captured_at
supports/refutes
```

Evidence có thể reference:

- interview;
- lead;
- opportunity;
- conversion;
- payment;
- analytics;
- document;
- external research.

## 19.5. Gate

Gate là deterministic evaluation + explainability:

```text
requirements
minimum evidence
blocking risks
score
result
rationale
human override record
```

## 19.6. Decision Record

Mọi stage transition quan trọng nên có:

- decision;
- evidence snapshot/ref;
- actor;
- agent recommendation;
- human approval/override;
- timestamp.

## 19.7. Next Best Action

NBA là projection/ranking, không phải source of truth.

```text
Candidate generation (deterministic)
      ↓
Score
      ↓
Policy filters
      ↓
LLM explanation/critique
      ↓
Human/Agent selection
      ↓
Create Initiative/Task/Experiment
```

---

# 20. Observability, Audit và Evaluation

## 20.1. Correlation model

Mọi agent/business flow nên có:

```text
correlation_id
run_id
company_id
workspace_id
user/principal id
agent id/profile
workflow id/version
parent span
```

## 20.2. Telemetry

OpenTelemetry là canonical distributed tracing layer.

Không dùng SQLite trace làm distributed telemetry authority.

## 20.3. Audit

Audit phải khác telemetry.

Telemetry hỏi:

> request chậm ở đâu?

Audit hỏi:

> ai/agent nào đã cố làm gì, policy quyết định gì, có approval không, kết quả business là gì?

Financial/delete/external write cần durable audit.

## 20.4. Evaluation taxonomy

COSA nên có ít nhất:

- Agent Eval;
- Tool Eval;
- Skill Eval;
- Model Eval;
- Business Outcome Eval;
- Safety/Governance Eval;
- Retrieval Eval.

## 20.5. Eval before autonomy

Không nâng agent từ L2 → L3A/L3 chỉ vì demo tốt. Phải có:

- success rate;
- tool correctness;
- forbidden action rate;
- business outcome;
- cost/latency;
- regression set.

---

# 21. Development Flow — từ yêu cầu tới merge

Mọi feature non-trivial dùng flow sau.

```text
1. Problem / User outcome
        ↓
2. Architecture owner classification
        ↓
3. Inspect current code + Ownership Map + ADR
        ↓
4. Implementation Plan
        ↓
5. Domain/API contracts
        ↓
6. Incremental implementation
        ↓
7. Unit/contract tests
        ↓
8. Integration/live pilot where needed
        ↓
9. Evals/security review
        ↓
10. Docs/ADR update
        ↓
11. Acceptance criteria verification
        ↓
12. Merge/deploy
```

## 21.1. Implementation Plan template

```markdown
# <Feature> Implementation Plan

## Problem
## User outcome
## Current code inspected
## Canonical owner
## Non-goals
## Data model changes
## API/event contracts
## Agent/Tool/Skill impact
## Security/tenant impact
## Migration/backward compatibility
## Files expected to change
## Test plan
## Rollback plan
## Acceptance criteria
```

## 21.2. Không code trước khi xác định owner

Ví dụ:

```text
“Agent tự gửi invoice”
```

Phải tách:

- invoice business logic → Commercial/Finance service;
- send capability → Tool/Connector;
- agent decision → Skill/Workflow/ADK;
- permission → Governance;
- approval → Approval Service.

---

# 22. Documentation Flow — tài liệu triển khai chuẩn

Mỗi feature lớn nên có bộ tài liệu tối thiểu:

```text
Product/Feature Spec
      ↓
Architecture Impact Note
      ↓
ADR (chỉ khi có decision khó đảo ngược)
      ↓
Implementation Plan
      ↓
Migration Plan (nếu thay owner/data/runtime)
      ↓
Runbook / Deployment Notes
      ↓
Verification / Readiness Report
```

## 22.1. Khi nào cần ADR

Cần ADR nếu thay:

- canonical owner;
- language/framework;
- database ownership;
- identity model;
- permission model;
- runtime/orchestrator;
- external protocol;
- durable workflow engine;
- migration strategy khó rollback.

Không cần ADR cho CRUD endpoint nhỏ trong boundary đã chốt.

## 22.2. Canonical docs set target

```text
docs/architecture/
├── COSA_CANONICAL_ARCHITECTURE_FUNCTIONAL_IMPLEMENTATION_GUIDE.md
├── COSA_CANONICAL_OWNERSHIP_MAP.md
├── MIGRATION_STATUS.md
├── adr/
├── runbooks/
└── _archive/
```

## 22.3. Architecture consistency checks

CI nên fail nếu:

- active canonical path không tồn tại;
- active doc còn chỉ định `backend/cosa_core` là target;
- Rules for new code trỏ vào `legacy/`;
- một capability có hai canonical target owner;
- ADR superseded không trỏ tới replacement;
- doc ghi production-ready nhưng không có matching readiness evidence.

---

# 23. Testing Strategy

## 23.1. Services

Bắt buộc:

- service logic tests;
- handler validation/auth tests;
- DB migration test;
- transaction/idempotency test;
- event emission test;
- tenant isolation.

## 23.2. AgentOS

Bắt buộc:

- registry tests;
- policy/approval tests;
- context tests;
- runtime adapter contract;
- memory/knowledge isolation;
- workflow pause/resume/rollback;
- skill routing;
- eval regression.

## 23.3. Live HTTP pilot

Mock không bắt được stale routes. Tool bindings production-critical nên có test chạy qua Encore instance thật, tương tự pilot hiện tại đã từng phát hiện nhiều route 404.

## 23.4. Text Chat

Test:

- create/resume/archive conversation;
- tenant isolation giữa conversations;
- message ordering;
- SSE/event sequence monotonic;
- reconnect/resume/dedupe;
- streaming partial/final consistency;
- tool event rendering contract;
- approval required → decision → resume same run;
- cancel run;
- retry semantics;
- attachment upload/ingest policy;
- citation provenance;
- conversation transcript không tự động mutate business data;
- memory consolidation không duplicate toàn bộ transcript;
- Text ↔ Voice continuity bằng cùng `conversation_id`;
- secret/PII redaction trong persisted RunEvent.

## 23.5. Voice

Test:

- session tenant scope;
- interruption;
- disconnect/reconnect;
- agent timeout;
- tool approval pause;
- no direct legacy DB dependency;
- partial response consistency.

---

# 24. Deployment Architecture

## 24.1. Local development — current useful topology

`services/docker-compose.yml` hiện có:

```text
Encore Gateway        :4000
Encore Dashboard      :9400
LiveKit               :7885 host mapping
PostgreSQL/pgvector   :5433
Realtime Agent        internal worker
```

Frontend có thể chạy riêng bằng Flutter.

## 24.2. Target local-first topology

```text
Flutter/Desktop
     │
     ├───────────── local HTTP ─────────────┐
     │                                      │
     ▼                                      ▼
Encore Services                        Agent API
     │                                      │
Postgres/pgvector                        AgentOS
     │                                      │
Object Storage                         ADK / DSH
                                            │
                                         Tools
                                            │
                                         Services

LiveKit ↔ Realtime Agent ↔ Agent API
```

## 24.3. Agent API deploy unit

AgentOS hiện cần một production composition/entrypoint rõ trước khi trở thành traffic-serving plane.

Target deploy unit nên:

- expose conversation/message/run/chat streaming endpoints;
- persist conversation/message metadata durably;
- accept authenticated principal and resolve trusted TenantContext server-side;
- own AgentOS composition root;
- stream events;
- support approval resume;
- expose health/readiness;
- export OTEL;
- not expose direct DB internals.

Framework HTTP cụ thể cần ADR nhỏ nếu chưa chốt; không để việc chọn FastAPI/khác làm thay đổi AgentOS domain contracts.

## 24.4. Production topology principles

- secrets qua managed secret store/environment injection;
- PostgreSQL backup/PITR;
- schema migrations trước traffic cutover;
- AgentOS horizontally scalable khi session store không process-local;
- approval/checkpoint durable;
- LiveKit production credentials riêng;
- no default dev JWT secret;
- OTEL collector/backend thật;
- object storage durability;
- health/readiness probes không `|| exit 0` khi production.

## 24.5. Supabase Central

Repo README mô tả hướng Hybrid `PostgreSQL Local Data Plane + Supabase Central Control Plane`, nhưng mức độ wiring hiện tại không đồng nhất giữa các subsystem. Không được coi mô tả README là fully implemented architecture nếu chưa có integration verification.

Nếu tiếp tục mô hình này, phải có ADR riêng xác định:

- dữ liệu nào local authority;
- dữ liệu nào central authority;
- sync direction;
- conflict resolution;
- offline semantics;
- encryption;
- company identity mapping.

---

# 25. CI/CD & Release Gates

Một release candidate chỉ được coi ready khi:

```text
TypeScript compile clean
Services tests green
Python tests green
Schema migrations verified
Tool contract tests green
Governance tests green
Chat streaming/reconnect/approval contract tests green
No stale canonical path check
Security secret scan
Live pilot for changed critical bindings
Evals above threshold
Deployment smoke test
Rollback documented
```

## 25.1. Versioning

Version độc lập cho:

- Business API contract;
- ToolSpec;
- Skill;
- Agent Profile;
- Workflow definition;
- prompt/instruction artifact nếu behavior-critical;
- embedding model/index generation.

---

# 26. Migration Roadmap

## Phase 0 — Architecture Authority

**P0**

- publish guide này vào `docs/architecture/`;
- supersede `cosa_core` extraction plan;
- rewrite Ownership Map thành `Target Owner + Operational Status`;
- sửa README để không tự mâu thuẫn về legacy traffic;
- archive/deprecate stale path rules;
- architecture consistency checks.

**DoD:** không còn active doc nào nói `backend/...` cũ là nơi nhận production code mới.

## Phase 1 — AgentOS Production Composition

- canonical production composition root;
- register all supported cluster tools;
- wire skills;
- wire memory;
- wire knowledge;
- unified TenantContext;
- secret-redacted trace;
- health/readiness;
- Agent API entrypoint;
- durable Conversation/Message store;
- text streaming event contract;
- Flutter Text Chat surface;
- attachment metadata/object-storage flow;
- approval resume through the same AgentRun.

## Phase 2 — Governance V2

- ToolSpecV2;
- tool risk classification;
- Executor cutover sang PermissionLevel/risk/execution mode;
- RBAC/tenant policy input;
- durable approvals;
- security/audit tests.

## Phase 3 — Google ADK Rehost

Port từ legacy theo behavior/invariants:

- mission lifecycle;
- nodes;
- specialist delegation;
- quality gate;
- approval semantics;
- pause/resume;
- anti-governance-bypass tests.

Không port legacy SQLAlchemy/app imports nếu chúng không thuộc AgentOS.

## Phase 4 — DeepSeek Harness Runtime

- RuntimePort;
- DSH adapter lifecycle;
- session/run mapping;
- governed tool bridge;
- budget/timeout/cancellation;
- compatibility pin/test;
- Native fallback.

## Phase 5 — Voice Convergence

- realtime-agent calls Agent API;
- remove sys.path/backend hacks;
- remove direct SessionLocal/business imports;
- same tools/skills/governance for chat + voice.

## Phase 6 — Startup Strategy Domain

- Assumption/Experiment/Evidence/Gate/Decision/NBA models;
- migrate useful founder_os behavior;
- link commercial signals;
- link OKR/tasks/12WY;
- frontend surfaces;
- strategy skills/evals.

## Phase 7 — Memory/Knowledge Productionization

- memory provider contract;
- provider selection;
- knowledge DB migration ownership;
- parse pipeline;
- retention;
- isolation;
- backup/reindex.

## Phase 8 — Legacy Retirement

Xóa từng capability chỉ khi:

```text
Target implemented
Parity evidence
Consumer scan = zero or migrated
Data migration complete
Regression tests green
Rollback window passed
```

Không xóa theo tên folder hoặc cảm giác “legacy”.

---

# 27. P0/P1 Backlog đề xuất

## P0 — security/authority

- redact SQLite trace secrets;
- supersede conflicting extraction plan;
- fix Ownership Map stale paths;
- resolve README contradiction;
- prohibit new imports from `legacy/` in active code;
- define AgentOS production entrypoint contract.

## P1 — convergence

- production AgentOS composition root;
- ToolSpecV2;
- governance cutover;
- TenantContext;
- Text Chat Agent API + durable conversation/event stream;
- Flutter Chat UI;
- realtime-agent convergence;
- ADK rehost plan + tests;
- DSH runtime ADR;
- Strategy bounded-context schema proposal.

## P2 — scale/quality

- memory provider abstraction;
- knowledge migrations/parsers;
- unified OTEL collector;
- stronger eval gates;
- A2A only if real distributed-agent requirement xuất hiện;
- centralized connector catalog/secret management.

---

# 28. Anti-patterns cấm

## 28.1. Runtime/framework

Không:

```text
create backend/cosa_core
create another ReAct engine
create another orchestration loop
fork DSH internals into Business Core
```

## 28.2. Business data

Không:

```text
Agent → direct Postgres
Voice → SessionLocal
Skill → ORM
ADK node → UPDATE business table
DSH plugin → company DB credential
```

## 28.3. Identity

Không:

```text
create new company table in AgentOS
create new role vocabulary per service
infer workspace/company independently
use AgentProfile as tenant membership
```

## 28.4. Chat/Channels

Không:

```text
Flutter → model provider directly
Chat → direct services DB
Voice → separate tool registry
Conversation transcript == Memory
Attachment blob stored inside message JSON
Approval creates unrelated new run
chat_tools.py reimplements business logic
```

## 28.5. Docs

Không:

```text
mark plan Approved but never supersede after architecture changes
keep dead paths in Canonical Ownership Map
copy same canonical doc into markdown/ and docs/architecture/
claim production from unit test only
```

---

# 29. Pull Request / Review Checklist

Mọi PR ảnh hưởng architecture hoặc agent capability trả lời được:

```text
[ ] Canonical owner là gì?
[ ] Có tạo implementation trùng không?
[ ] Business writes có đi qua service/API không?
[ ] Tenant scope ở đâu?
[ ] RBAC ở đâu?
[ ] Agent PermissionLevel/risk ở đâu?
[ ] Tool có input/output contract không?
[ ] Write có idempotency không?
[ ] External/high-risk action có approval không?
[ ] Audit/trace có redact không?
[ ] Skill/tool/workflow version có thay không?
[ ] Tests nào chứng minh?
[ ] Evals nào chứng minh behavior?
[ ] Migration/rollback thế nào?
[ ] Docs/ADR nào cần update?
```

---

# 30. Quick Decision Cheatsheet

| Tôi cần thêm... | Đặt ở đâu? |
|---|---|
| Business entity | `services/<domain>/models + migrations` |
| Business rule | `services/<domain>/services` |
| Public/internal API | `services/<domain>/handlers` |
| Business event | `services/shared/events` + publisher/consumer owner |
| Agent calls business API | `agentos/tools` |
| Agent instructions/process knowledge | `skillpacks/` + `agentos/skills` |
| New specialist persona | Agent Profile + ADK registry |
| Multi-agent graph | `agentos/orchestration/adk` |
| Runtime provider | `agentos/runtime/adapters` |
| Retry/approval/compensation procedure | `agentos/workflows` |
| Business lifecycle/state machine | `services/<domain>` |
| Episodic/procedural memory | `agentos/memory` |
| Documents/RAG | `agentos/knowledge` |
| External SaaS capability | Connector → Tool → Governance |
| Text Chat UI behavior | `frontend/` + Agent API event contract |
| Conversation/run API | `agentos/api` |
| Conversation/message persistence | Agent Plane durable conversation store |
| Chat attachment | object storage metadata → optional Knowledge ingest |
| Voice feature | build capability normally, voice calls same Agent API |
| Startup validation logic | `services/operations/strategy` |
| Audit | AgentOS audit + business durable projection as required |
| Distributed trace | OpenTelemetry |

---

# 31. Definition of Done cho COSA architecture convergence

COSA chỉ được coi là đã converged khi:

1. `services/` là business source-of-truth duy nhất cho các domain đã migrate.
2. `agentos/` có production entrypoint và composition root đầy đủ.
3. Text Chat là first-class primary channel với durable conversation, streaming events, approval resume, attachment/citation support.
4. Chat và Voice dùng cùng AgentOS Tool/Governance/Memory/Knowledge path và có thể tiếp tục cùng conversation.
5. ADK nằm sau AgentOS orchestration contract.
6. DeepSeek Harness nằm sau AgentOS runtime contract.
7. Native Executor không phát triển thành framework cạnh tranh không cần thiết.
8. ToolSpec có schema/risk/idempotency/audit metadata.
9. RBAC và Agent PermissionLevel được tách đúng.
10. Memory, Knowledge và Business DB không overlap ownership.
11. Startup methodology có business models thật, không chỉ prompt.
12. Legacy không còn production consumer trước khi bị xóa.
13. Ownership Map không chứa dead canonical paths.
14. CI có architecture consistency checks.
15. Critical agent actions có audit + approval + eval evidence.

---

# Appendix A — Current vs Target Status Matrix

| Capability | CURRENT baseline | TARGET |
|---|---|---|
| Business API | Encore services | Encore services |
| Agent runtime | custom AgentRuntime + adapters | AgentOS runtime ports; DSH specialist, Native fallback |
| Orchestration | legacy ADK reference + custom supervisor | AgentOS ADK adapter |
| Tools | ToolSpec thin + cluster tools | ToolSpecV2 governed catalog |
| Skills | Registry/router + `skillpacks` | Same, production-wired + eval gates |
| Memory | in-memory/pgvector-style stores + consolidation | provider architecture + isolation/retention |
| Knowledge | pgvector retrieval implementation | migrated DB + parser/provenance pipeline |
| Governance | PermissionClass + new PermissionLevel primitives | RBAC × PermissionLevel × Risk × Mode × TenantPolicy |
| Trace | SQLite + partial telemetry | redacted SQLite checkpoint + unified OTEL |
| Text Chat | not modeled as first-class in prior guide | Flutter + Agent API + durable conversations + streaming events |
| Voice | LiveKit worker with legacy coupling | channel adapter to same Agent API/conversation |
| Startup methodology | partial generic strategy fields + legacy concepts | first-class Strategy bounded context |
| Legacy | frozen/broken fragments but still referenced | migration source → retired |

---

# Appendix B — Evidence Snapshot dùng để viết guide

Các file/code đã được đối chiếu trực tiếp cho baseline này:

```text
README.md
CLAUDE.md
frontend/pubspec.yaml
services/package.json
services/docker-compose.yml
services/shared/db/schema/operations.ts
services/control-plane/...
services/identity/...
services/commercial/...
services/finance-legal/...
services/realtime_agent/...
agentos/requirements.txt
agentos/core/runtime.py
agentos/core/executor.py
agentos/core/factory.py
agentos/core/policy.py
agentos/core/trace_sink.py
agentos/core/adapters/deepseek_harness_provider.py
agentos/tools/registry.py
agentos/tools/clusters/...
agentos/skills/...
agentos/memory/...
agentos/knowledge/...
agentos/workflows/...
agentos/evals/...
skillpacks/okr/manifest.yaml
skillpacks/okr/SKILL.md
legacy/backend/requirements.txt
legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
docs/architecture/2026-08-22-cosa-core-extraction-plan.md
docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md
```

External technology status was also checked against official Google agent/ADK documentation and the official `deepseek-ai/deepseek-harness` repository. DeepSeek Harness remains developer preview at the time of this document, so version pinning and compatibility tests are architectural requirements rather than optional hygiene.

---

# Appendix C — Glossary

**Conversation** — container durable cho chuỗi message/run của một tương tác Text/Voice.  
**Message** — một turn user/assistant/system artifact được persist trong conversation.  
**RunEvent** — event có thứ tự mô tả lifecycle của AgentRun để stream/reconnect/audit.  
**Business Plane** — hệ thống sở hữu domain data, transactions, business rules.  
**Control Plane** — platform account/company/tenant/license/access management.  
**Agent Plane** — AI behavior, orchestration, runtime, tools, skills, memory, eval.  
**Tool** — governed adapter cho agent gọi một capability.  
**Skill** — instruction/capability package mô tả cách agent thực hiện công việc.  
**Agent Profile** — runtime role/config/skills/tools/autonomy của specialist.  
**Workflow** — deterministic procedure có steps/retry/approval/compensation.  
**Orchestration** — điều phối specialist/multi-agent reasoning graph.  
**Memory** — thông tin agent nhớ qua thời gian.  
**Knowledge** — corpus có provenance được chunk/embed/retrieve.  
**RBAC** — business authorization của principal trong company.  
**PermissionLevel** — mức tự chủ/trust của agent.  
**Tool Risk** — mức rủi ro của capability.  
**TenantContext** — scope company/workspace/principal xuyên request.  
**Governance** — policy evaluation trước side effect.  
**Approval** — human/authorized gate cho action rủi ro.  
**Audit** — durable record của action/decision/approval.  
**Telemetry** — operational observability/tracing/metrics.  
**Legacy migration source** — code được phép đọc/port behavior nhưng không nhận feature mới.

---

# Final Canonical Statement

COSA không cần thêm một “core framework” mới. COSA cần **hợp nhất ownership**:

```text
One Business/Control Plane  → services/
One Agent Plane             → agentos/
One governed Tool boundary  → agentos/tools + governance
One business source of truth→ PostgreSQL through services
One orchestration adapter   → Google ADK
One specialist runtime path → DeepSeek Harness (with Native fallback)
One skill ecosystem         → agentos/skills + skillpacks
One memory contract         → agentos/memory
One knowledge pipeline      → agentos/knowledge
One text conversation path  → Flutter → Agent API → AgentOS
One voice/channel path      → realtime-agent → same Agent API/conversation
One migration source        → legacy/
```

Mọi feature mới phải làm COSA **ít hệ thống song song hơn**, không nhiều hơn.
