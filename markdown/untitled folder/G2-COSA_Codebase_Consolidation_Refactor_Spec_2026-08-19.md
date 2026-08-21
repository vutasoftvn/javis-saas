# COSA Codebase Consolidation & Refactor Specification
## Tài liệu điều chỉnh, bổ sung và hội tụ kiến trúc COSA sau audit codebase

**Trạng thái:** Proposed → Implementation Ready  
**Ngày:** 2026-08-19  
**Đối tượng triển khai:** Founder / Claude Code / Dev team / AI coding agents  
**Phạm vi:** Backend FastAPI + PostgreSQL/pgvector + MinIO + AI Workforce + Flutter + Local/Central Control Plane + LiveKit + OpenSandbox  
**Mục tiêu:** Biến COSA từ một codebase nhiều chức năng thành một **AI Co-Founder Operating System** có runtime xuyên suốt, dữ liệu thật, bảo mật license đúng chuẩn và UX đơn giản cho founder.

---

# 0. Executive Summary

COSA hiện đã có nền tảng tốt và **không cần viết lại**. Kiến trúc 5 domain đã hình thành rõ:

1. `founder_os`
2. `business`
3. `workforce`
4. `integrations`
5. `platform`

Hệ thống cũng đã có nhiều thành phần runtime thật:

- PostgreSQL + pgvector;
- MinIO;
- async/sync worker;
- chat jobs;
- task scheduler / dispatcher;
- agent registry;
- tool registry;
- approval;
- agent budget / cost ledger;
- memory;
- LiveKit Local cho Desktop;
- LiveKit Cloud cho Mobile/Web;
- OpenSandbox execution;
- central sync/outbox/inbox;
- entitlement snapshot;
- Flutter Hologram Hub;
- CI cho backend, frontend, realtime và architecture boundary.

Vấn đề chính hiện nay **không phải thiếu module**, mà là:

- nhiều thế hệ kiến trúc tồn tại song song;
- một số model/entity bị trùng vai trò;
- Co-Founder UI/API đã đi trước orchestration runtime;
- một số phản hồi đang dùng dữ liệu hard-code hoặc fallback giả thành công;
- workspace mới mặc định ở stage quá trưởng thành;
- license offline dùng symmetric HMAC chưa phù hợp với sản phẩm public/license;
- tenant/workspace isolation chưa được áp dụng thống nhất;
- global agent definitions có nguy cơ bị chỉnh từ workspace;
- Hologram Hub có một số thao tác UI chưa commit trạng thái thật xuống backend.

Mục tiêu của tài liệu này là **hội tụ**, không mở rộng vô hạn.

---

# 1. Product North Star

COSA phải được hiểu là:

> **AI Co-Founder Operating System dành cho founder vận hành doanh nghiệp bằng hội thoại, mục tiêu, dữ liệu, bằng chứng, quyết định, missions và AI workforce.**

Founder không cần chọn:

- model;
- agent;
- skill;
- MCP;
- tool;
- workflow;
- prompt;
- queue;
- sandbox.

Founder chỉ cần:

1. nói mục tiêu / vấn đề / câu hỏi;
2. xem COSA hiểu gì;
3. duyệt những quyết định quan trọng;
4. theo dõi Top 3;
5. nhận artifact, evidence, outcome;
6. điều chỉnh doanh nghiệp.

COSA chịu trách nhiệm điều phối phần còn lại.

---

# 2. Nguyên tắc kiến trúc bắt buộc

## 2.1. Không rewrite

Không thay FastAPI, PostgreSQL, Flutter, LiveKit, MinIO hay worker architecture chỉ để “làm sạch”.

Ưu tiên:

- reuse;
- migrate;
- deprecate;
- adapter;
- compatibility layer.

Chỉ delete khi đã có test chứng minh không còn reference.

---

## 2.2. Không thêm Agent chỉ vì có một kỹ năng mới

Kỹ năng mới mặc định phải đi vào:

```text
Skill / Capability
        ↓
Tool / Workflow
        ↓
Existing Domain Agent
```

Chỉ tạo Agent mới khi:

- có trách nhiệm dài hạn độc lập;
- có memory scope riêng;
- có budget riêng;
- có permission riêng;
- có KPI/outcome riêng;
- có lý do xuất hiện trong org chart.

---

## 2.3. COSA là cửa vào chính

Flow mặc định:

```text
Founder
  ↓
COSA Co-Founder
  ↓
Intent + Context
  ↓
Reason / Challenge / Decide / Mission
  ↓
Domain Agents
  ↓
Tools / Workflows / Sandbox
  ↓
Artifacts + Evidence + Outcome
  ↓
Hologram Hub
```

Founder chỉ đi trực tiếp vào domain nếu chủ động chọn.

---

## 2.4. “Truthful Runtime” – trạng thái UI phải là trạng thái thật

Cấm các hành vi:

- UI remove approval nhưng backend chưa approve;
- API lỗi nhưng UI báo “Agent đang triển khai”;
- Co-Founder nói “đã giao Marketing Agent” nhưng chưa tạo run/job;
- Company Pulse báo on-track bằng mặc định;
- Finance recommendation dùng số giả;
- “đã lưu vào memory” nếu database write chưa thành công.

Mỗi trạng thái phải có nguồn:

```text
DB row
Event
Job
Run
Artifact
Evidence
Outcome
```

---

## 2.5. Không tạo model mới nếu đã có entity gần tương đương

Trước mọi migration Claude Code phải:

1. search model hiện tại;
2. search Alembic history;
3. search router/service đang dùng;
4. xác định canonical entity;
5. chỉ add column/table khi không thể reuse.

Đặc biệt phải kiểm tra các entity hiện có liên quan:

- `AgentDefinition`
- `AgentRun`
- `AgentStep`
- `ExecutionJob`
- `FounderDecision`
- `ApprovalRequest`
- `Outcome`
- `OutcomeRun`
- `Artifact`
- `EvidenceItem`
- `NextActionCandidate`
- `NextActionRanking`
- `TwelveWeekCycle`
- `WeeklyPlan`
- `Project`
- `WorkspaceAgent`
- missions hiện có trong platform/workforce.

---

## 2.6. Stage-aware nhưng không stage-gated cứng

Stage dùng để:

- thay đổi UI;
- thay đổi prompt/context;
- thay đổi phương pháp;
- thay đổi metric;
- thay đổi Next Best Action;
- thay đổi capability recommendation.

Stage **không được tự động khóa founder** vì “chưa hoàn thành bài học”.

Founder có quyền override và ghi reason.

---

## 2.7. Evidence-first, không “AI hallucinated metrics”

Mọi recommendation có con số phải kèm:

- nguồn dữ liệu;
- thời điểm;
- confidence;
- calculation;
- hoặc ghi rõ là scenario/assumption.

Ví dụ đúng:

```text
Runway hiện tại: 7.2 tháng
Nguồn: FinanceSnapshot 2026-08-19
Cash balance: 420m VND
Average burn: 58.3m VND/month
```

Ví dụ sai:

```text
Nếu chi 50 triệu thì runway giảm từ 7.5 xuống 6.2 tháng
```

nếu không có calculation/data thật.

---

## 2.8. Global defaults immutable; workspace chỉ override

Không cho company thay trực tiếp:

- default agent manifest;
- platform default prompt;
- signing keys;
- tool registry global;
- core template global.

Company chỉ tạo override/version riêng.

---

## 2.9. Local-first business data

Dữ liệu vận hành chi tiết thuộc company ưu tiên local:

- CRM;
- accounting;
- legal documents;
- campaigns;
- prompts override;
- API keys;
- full chat;
- full evidence;
- files;
- agent memory;
- tasks.

Central chỉ lưu metadata cần cho:

- identity;
- license;
- entitlement;
- tier;
- company lifecycle;
- project lifecycle;
- stage analytics;
- success metrics;
- product telemetry tối thiểu;
- update/catalog distribution.

---

## 2.10. Backward compatibility có thời hạn

Mỗi compatibility entity phải có metadata:

```text
ACTIVE
COMPATIBILITY
DEPRECATED
REMOVABLE
```

Không để “legacy” sống vô thời hạn.

---

# 3. Target Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         HUMAN FOUNDER                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      COSA AI CO-FOUNDER                         │
│ Intent • Context • Challenge • Decision • Mission • Synthesis   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        FOUNDER OPERATING LOOP       WORKFORCE CONTROL
        Stage / 12WY / Top3          Mission / AgentPlan
        Decision / Review            Permission / Approval
        Evidence / Outcome           Budget / Runtime
                 │                         │
                 └────────────┬────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         5 CORE DOMAINS                          │
│ Finance • Marketing • Sales • Build/Tech • Legal               │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CAPABILITIES / SKILLS / TOOLS / WORKFLOWS / MCP / SANDBOX      │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ LOCAL COMPANY DATA PLANE                                       │
│ PostgreSQL • pgvector • MinIO • Secrets • Memory • Artifacts    │
└─────────────────────────────┬───────────────────────────────────┘
                              │ signed/sanitized events
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CENTRAL CONTROL PLANE                                          │
│ Identity • Tier • License • Lifecycle • Catalog • Updates       │
│ Project intelligence • Aggregate product analytics              │
└─────────────────────────────────────────────────────────────────┘
```

---

# 4. Canonical Workforce Model

## 4.1. Visible Workforce

Mặc định founder chỉ thấy:

```text
COSA Co-Founder
├── Finance Agent
├── Marketing Agent
├── Sales Agent
├── Build & Tech Agent
└── Legal Agent
```

Optional:

```text
People / HR
Product
Analytics
Customer Support
Research
Operations
...
```

không hiện nếu chưa kích hoạt.

---

## 4.2. Registry Compatibility

Các key cũ như:

- `founder`
- `founder_copilot`
- `general`
- `finance`
- `marketing`
- `sales`
- `developer`
- `legal`
- `researcher_agent`
- `google_search`

được giữ như:

```json
{
  "category": "LEGACY",
  "is_default_active": false,
  "visible_in_ui": false,
  "direct_dispatch": false,
  "canonical_parent_key": "..."
}
```

Nếu schema chưa có `visible_in_ui`, `direct_dispatch`, `canonical_parent_key`, ưu tiên lưu trong `config_jsonb` trước khi quyết định thêm column.

---

# 5. Canonical Execution Chain

Mọi work item do Co-Founder giao phải đi qua chain:

```text
Founder Message
    ↓
IntentDecision
    ↓
ContextBundle
    ↓
CofounderDecision
    ↓
Mission
    ↓
Agent Plan
    ↓
Plan Steps
    ↓
Execution Job / Tool Call / Workflow
    ↓
Approval (nếu cần)
    ↓
Artifact / Evidence
    ↓
Outcome
    ↓
Memory promotion (nếu đủ điều kiện)
    ↓
Hologram Update
```

## 5.1. Không tạo chain song song mới

Claude Code phải kiểm tra và reuse:

- `platform/core/missions_router.py`;
- `workforce/agents/control_plane/*`;
- `workforce/agents/execution/*`;
- `workforce/agents/governance/*`;
- `founder_os/outcomes/*`;
- `core/events.py`;
- task dispatcher;
- workflow engine.

Nếu đã có Mission model, **không tạo `missions_v2`**.

---

# 6. P0 — Security, License & Runtime Truth

---

## 6.1. P0.1 — Thay HMAC entitlement bằng Ed25519

### Hiện trạng cần loại bỏ

Local runtime hiện có khả năng dùng symmetric HMAC secret để sign/verify entitlement.

Đối với sản phẩm license:

```text
client có secret verify = client có khả năng sign
```

là không chấp nhận được.

### Target

```text
CENTRAL:
Ed25519 Private Key
        ↓ sign
SignedEntitlementSnapshot

LOCAL:
Ed25519 Public Key
        ↓ verify
Access decision
```

### File ảnh hưởng

```text
backend/app/platform/sync/entitlement_crypto.py
backend/app/platform/sync/entitlement_manager.py
backend/app/platform/sync/entitlement_guard.py
backend/app/platform/sync/router.py
backend/app/core/runtime_config.py
docker-compose.yml
```

### Environment mới

Central:

```bash
COSA_ENTITLEMENT_PRIVATE_KEY_B64=...
COSA_ENTITLEMENT_KEY_ID=2026-01
```

Local:

```bash
COSA_ENTITLEMENT_PUBLIC_KEY_B64=...
COSA_ENTITLEMENT_KEY_ID=2026-01
```

### Payload nên có

```json
{
  "company_id": "uuid",
  "plan": "pro",
  "limits": {},
  "features": {},
  "issued_at": "...",
  "valid_until": "...",
  "grace_period_days": 7,
  "key_id": "2026-01",
  "nonce": "...",
  "schema_version": 1
}
```

### Quy tắc

- private key không bao giờ build vào desktop/mobile;
- không commit fallback production secret;
- local chỉ verify;
- key rotation hỗ trợ bằng `key_id`;
- snapshot cũ vẫn verify bằng public key catalog trong thời hạn chuyển đổi.

### Migration compatibility

Trong 1 release chuyển tiếp:

```text
signature_alg = HMAC_SHA256 | ED25519
```

Local verify cả hai nhưng:

- Central chỉ phát Ed25519 mới;
- cảnh báo nếu gặp HMAC;
- release kế tiếp bỏ HMAC.

---

## 6.2. P0.2 — Tách entitlement signing endpoint khỏi Local API

Endpoint kiểu:

```text
POST /platform/sync/entitlement/sign
```

không được mount trên company runtime.

### Chọn một trong hai cách

**Ưu tiên A: Hai app entrypoint**

```text
backend/app/main.py                 → company/local plane
backend/app/control_plane_main.py   → central
```

hoặc:

**B: Conditional router registration**

```bash
COSA_RUNTIME_PLANE=company
COSA_RUNTIME_PLANE=control
```

Nếu `company`:

- không mount sign;
- không mount admin license issue;
- không mount central ingest admin endpoints.

Nếu `control`:

- mount signing;
- yêu cầu control-plane admin/service auth.

### Acceptance

```text
Local company API cannot issue a paid entitlement.
```

---

## 6.3. P0.3 — Persist Entitlement Snapshot local

Không dùng RAM cache làm source of truth.

### Model đề xuất

Chỉ tạo nếu chưa có table tương đương:

```python
LocalEntitlementSnapshot
- id
- company_id
- plan
- payload_jsonb
- signature
- signature_alg
- key_id
- issued_at
- valid_until
- grace_period_days
- received_at
- verified_at
- verification_status
- is_current
```

Unique current snapshot:

```text
company_id + is_current
```

### Flow

```text
Central refresh
  ↓
Verify signature
  ↓
DB transaction:
  old.is_current = false
  insert new
  ↓
In-memory cache optional
```

Startup:

```text
load current snapshot from DB
  ↓
verify
  ↓
cache
```

Restart không được fallback Free nếu local có snapshot Pro còn hiệu lực.

---

## 6.4. P0.4 — WorkspaceContext thống nhất

### Vấn đề

Không được tin trực tiếp:

- `workspace_id` query;
- `workspace_id` body;
- `X-Workspace-ID`;
- `X-Company-ID`.

### Tạo

```python
class WorkspaceContext:
    user_id: int
    workspace_id: int
    company_id: str
    role: str
    company_stage: str
    entitlement_plan: str
    entitlement_mode: str
```

Dependency:

```python
get_workspace_context(...)
```

### Quy trình

1. lấy JWT user;
2. lấy requested workspace;
3. query `WorkspaceMember`;
4. reject nếu không thuộc workspace;
5. lấy Workspace;
6. derive company/platform ID server-side;
7. load entitlement server-side;
8. trả context.

### Áp dụng trước cho

```text
workforce/api/cofounder_api.py
workforce/api/packs_api.py
platform/sync/*
founder_os/*
business/marketing/*
business/sales/*
business/finance/*
business/legal/*
workforce/admin APIs
```

### Quy tắc

Service layer nhận:

```python
ctx.workspace_id
```

không dùng raw client ID.

---

## 6.5. P0.5 — Fix Workspace Genesis Stage

### Hiện trạng

Workspace mới không được khởi tạo đúng stage startup.

### Target stages

```text
S0_GENESIS
S1_PROBLEM_DISCOVERY
S2_PROBLEM_VALIDATION
S3_SOLUTION_VALIDATION
S4_GO_TO_MARKET
S5_OPERATE_GROWTH
S6_SCALE
```

### Default bắt buộc

```python
company_stage = "S0_GENESIS"
```

### Register flow

Khi register:

```text
User
  ↓
Workspace S0_GENESIS
  ↓
Admin membership
  ↓
Default Brain
  ↓
Founder Profile empty
  ↓
Genesis Next Actions
```

### Existing workspaces

Migration không được tự động kéo mọi S5 về S0.

Script cần:

```text
if workspace.created_at before migration:
    preserve stage
```

Chỉ sửa default cho workspace mới.

Có thể cung cấp admin command:

```text
reassess-company-stage
```

để founder chọn reclassify.

---

## 6.6. P0.6 — Fix Greeting Intent

### Mục tiêu

`"chào"` phải là social greeting đúng nghĩa.

### Target

`deterministic_intent()` trả:

```python
Intent.GREETING
```

không trả `GENERAL_CHAT`.

Service:

```python
if intent == Intent.GREETING:
    return greeting_response
```

Không dựa vào:

```text
"greetings" in decision.reason
```

### Tests

```text
chào
chào!
xin chào
hello
hi cosa
cảm ơn
```

không được query Project / Pulse / DB business context.

---

## 6.7. P0.7 — Remove fake Approval success

### Frontend

File:

```text
frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart
```

Hiện `approveTask()` phải đổi thành:

```dart
final success = await _approvalsService.approve(approvalId);

if (success) {
  pendingApprovals.removeWhere(...);
  snackbar success;
} else {
  snackbar error;
}
```

### Rule

Không remove trước khi server success.

Tương tự:

- reject;
- revision;
- resolve decision;
- toggle pack;
- publish;
- payment;
- tool execution.

---

## 6.8. P0.8 — Remove fake Chat fallback

Nếu Co-Founder API fail:

Không được trả:

```text
“Tôi đã ghi nhận và đang điều phối...”
```

### Target UX

```text
“Không thể gửi yêu cầu tới COSA runtime.
Yêu cầu chưa được tạo thành Mission.”
```

Kèm:

- retry;
- error id;
- local connectivity status.

---

## 6.9. P0.9 — Remove hard-coded business conclusions

### File chính

```text
backend/app/workforce/orchestrator/cosa_cofounder_service.py
```

Các method:

```text
synthesize_cross_domain()
get_next_best_action()
get_company_pulse()
challenge_assumptions()
```

phải tách:

```text
Data Retrieval
Reasoning
Presentation
```

### Company Pulse

Phải query thật:

```text
active 12WY objectives
current weekly commitments
completion %
blocked tasks
pending decisions
pending approvals
running missions
failed missions
finance alerts
sales pipeline alerts
marketing experiment alerts
legal obligations due
```

Không có data thì:

```text
unknown / unavailable
```

không tự coi on-track.

### Next Best Action

Ưu tiên reuse:

```text
NextActionCandidate
NextActionRanking
```

nếu đúng chức năng.

Ranking factors:

```text
urgency
expected impact
stage relevance
deadline
dependency unblock value
evidence gap
cash risk
founder-only requirement
12WY alignment
```

### Challenge Mode

Không trigger chỉ bằng keyword “build ngay”.

Phải kết hợp:

```text
intent
stage
evidence sufficiency
cost/risk
current experiment
founder preference
```

Challenge là advisory.

Founder có thể:

```text
Proceed anyway
```

và COSA lưu reason.

---

## 6.10. P0.10 — Production CORS

`main.py`:

Không dùng wildcard production.

```bash
COSA_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
```

Development có thể allow localhost.

### Test

Production startup fail nếu:

```text
* + credentials
```

---

# 7. P1 — Co-Founder End-to-End Runtime

Đây là phase quan trọng nhất về product.

---

## 7.1. Intent → Action Contract

Mỗi intent phải trả một structured decision:

```json
{
  "intent": "FOUNDER_COMMAND",
  "confidence": 0.94,
  "target": "MISSION",
  "domain": "MARKETING",
  "requires_context": ["project", "stage", "12wy"],
  "requires_confirmation": true,
  "risk_level": 2
}
```

Không chỉ string.

---

## 7.2. ContextBundle

Tạo service, không nhất thiết tạo DB model:

```text
CofounderContextAssembler
```

Output:

```json
{
  "workspace": {},
  "project": {},
  "stage": {},
  "founder_profile": {},
  "active_12wy": {},
  "weekly_plan": {},
  "top_blockers": [],
  "pending_decisions": [],
  "pending_approvals": [],
  "business_signals": {
    "marketing": {},
    "sales": {},
    "finance": {},
    "legal": {}
  },
  "evidence": [],
  "recent_outcomes": []
}
```

### Minimum Viable Context

Không load toàn bộ database.

Intent Finance:

```text
Finance + current project + 12WY + decisions
```

Intent greeting:

```text
none
```

Intent general:

```text
minimal company profile
```

---

## 7.3. Mission Creation

Khi founder nói:

> “Trong 30 ngày tìm cho tôi 20 khách hàng tiềm năng phù hợp.”

COSA không được chỉ mô tả.

Phải tạo:

```text
Mission
title
goal
success_metric
target_value
deadline
project_id
created_by
created_from_message_id
status = DRAFT
risk_level
```

Nếu system đã có Mission model, reuse.

### Founder confirmation

Nếu mission có write/external action:

```text
DRAFT
  ↓ founder confirm
PLANNED
  ↓
ACTIVE
```

Read-only research có thể auto-start theo policy.

---

## 7.4. Mission Decomposition

Ví dụ:

```text
Mission: 20 qualified leads / 30 days
│
├── Marketing
│   ├─ Define ICP
│   ├─ Landing message
│   └─ Lead source strategy
│
├── Sales
│   ├─ Build prospect list
│   ├─ Qualify
│   └─ Outreach
│
└── Build
    └─ Landing page / lead capture if required
```

Không phải mission nào cũng gọi 3 agent.

Planner phải chọn tối thiểu số agent cần thiết.

---

## 7.5. Plan → Jobs

Mỗi AgentPlanStep phải map được sang:

```text
ToolCall
Workflow
ExecutionJob
HumanAction
Decision
```

Không có step kiểu:

```text
“Marketing Agent suy nghĩ”
```

mà không có executor.

---

## 7.6. Approval Policy

Risk model:

```text
R0 Read-only              → auto
R1 Internal write         → auto/log
R2 External draft         → auto draft, approve publish/send
R3 Money / deploy / legal → founder approval
R4 Irreversible/high risk → founder-only + explicit confirmation
```

Ví dụ:

```text
web search             R0
read CRM               R0
create internal task   R1
draft email            R2
send email             R2/R3
publish social         R3
deploy production      R3
payment                R4
legal signature        R4
delete data            R4
```

---

## 7.7. Artifact/Evidence/Outcome

Mỗi Mission khi complete phải có tối thiểu:

```text
result summary
artifacts[]
evidence[]
metrics
cost
duration
agent runs
failed steps
founder decisions
outcome status
```

### Không đánh completed nếu chỉ agent trả text

Complete chỉ khi success criteria có evaluation.

---

# 8. P1 — Company Pulse v2

## 8.1. Pulse Contract

```json
{
  "stage": "S2_PROBLEM_VALIDATION",
  "current_cycle": {},
  "progress": {},
  "missions": {},
  "founder_attention": {},
  "business_health": {},
  "top_risks": [],
  "evidence_gaps": [],
  "updated_at": "..."
}
```

## 8.2. Hologram Hub chỉ cần 5 nhóm

```text
1. COSA Co-Founder
2. Company Pulse
3. Top 3 Focus
4. Waiting for You
5. AI Workforce
```

Không thêm card top-level mới nếu có thể nằm trong 5 nhóm này.

---

# 9. P1 — Stage-Aware Operating Engine

---

## 9.1. Stage matrix

### S0 — Genesis

Focus:

- founder/company profile;
- problem hypothesis;
- target market;
- first project;
- first 12WY cycle.

Không ưu tiên:

- BSC;
- corporate KPI complexity;
- multi-level budgeting.

---

### S1 — Problem Discovery

Focus:

- customer;
- JTBD;
- problem;
- interview;
- qualitative evidence.

Capabilities:

```text
Customer Interview
JTBD
Problem Statement
ICP Draft
Evidence Capture
```

---

### S2 — Problem Validation

Focus:

- severity;
- frequency;
- willingness-to-pay;
- alternative solutions;
- evidence quality.

Capabilities:

```text
Assumption
Hypothesis
Experiment
Interview
Smoke Test
Evidence
```

Validation không phải gate bắt buộc.

---

### S3 — Solution Validation

Focus:

- MVP;
- usage;
- activation;
- retention;
- paid signal.

Capabilities:

```text
MVP
Product experiment
Activation metric
Retention
Pricing test
```

---

### S4 — Go-To-Market

Focus:

- positioning;
- marketing;
- sales;
- channel;
- funnel;
- CRM.

Capabilities:

```text
Marketing
Sales
CRM
Campaign
Attribution
Landing Page
Automation
```

---

### S5 — Operate/Growth

Focus:

- repeatable operations;
- budget;
- unit economics;
- department performance;
- compliance.

Capabilities có thể bật:

```text
BSC
advanced finance
team structure
automation
department metrics
```

---

### S6 — Scale

Focus:

- portfolio;
- multi-team;
- governance;
- advanced strategy;
- capital allocation;
- enterprise controls.

---

## 9.2. PESTEL / SWOT / TOWS / BSC

Không xóa.

Chuyển thành:

```text
Strategy Capability Library
```

Rule:

```text
COSA suggests when useful
Founder can request anytime
Not a mandatory top-level flow
```

PESTEL có thể phù hợp khi:

- regulatory environment;
- multi-market;
- funding/policy;
- macro impact.

SWOT/TOWS phù hợp khi có đủ evidence.

BSC ưu tiên S5/S6.

---

# 10. P1 — Agent Model Consolidation

## 10.1. Canonical Registry

Ưu tiên:

```text
workforce.models.AgentDefinition
ToolDefinition
AgentToolPermission
UnifiedPermission
ApprovalRequest
AgentBudget
CostLedger
PlatformPromptTemplate
```

## 10.2. Runtime canonical

Phải audit:

```text
workforce.models.AgentRun
workforce.agents.governance.AgentRun
founder_os.tasks.Agent
workforce.agents.control_plane.*
```

### Claude Code deliverable

Tạo bảng mapping:

| Existing Entity | Purpose | References | Keep? | Canonical replacement |
|---|---|---:|---|---|
| ... | ... | ... | ... | ... |

### Rule

Không rename/delete trong cùng PR với runtime feature lớn.

Thực hiện:

1. inventory;
2. adapters;
3. migrate writes;
4. migrate reads;
5. deprecation warning;
6. delete ở release sau.

---

# 11. P1 — Workforce Pack Isolation

## 11.1. Global Definition

Global manifest:

```text
immutable
versioned
platform-owned
```

## 11.2. Workspace Override

Ưu tiên reuse `WorkspaceAgent` nếu đủ chức năng.

Nếu chưa đủ, mở rộng hoặc tạo entity:

```text
WorkspaceAgentConfig
- workspace_id
- agent_definition_id
- enabled
- visible
- model_profile_override
- budget_override
- permission_override_jsonb
- prompt_override_id
- updated_by
- updated_at
```

### Core rule

COSA Co-Founder:

```text
cannot disable
```

5 core domains:

Có thể:

- active/paused tùy plan/config;

nhưng không sửa global definition.

Nếu product quyết định “5 core luôn tồn tại” thì `enabled=false` chỉ mang nghĩa temporarily paused, không delete.

---

# 12. P1 — Prompt Governance

## 12.1. Global defaults

Platform prompt:

```text
default_content
version
checksum
```

immutable với company user.

## 12.2. Company override

Admin founder có thể:

```text
edit current override
view diff
restore default
rollback version
```

## 12.3. Permission

Chỉ role:

```text
admin/founder
```

được:

- sửa system prompt;
- sửa Build Spec;
- sửa tool permission;
- reset defaults.

Staff sau này dùng RBAC.

---

# 13. P1 — Build Spec Governance

Build spec phải local-first và readable/editable từ dashboard.

Entity hoặc protected resource phải có:

```text
project_id
version
content
checksum
status
updated_by
source = DEFAULT | FOUNDER | AGENT
```

Admin có:

```text
Edit
Diff
Rollback
Reset to platform default
```

Agent không tự sửa spec nền mà không tạo revision.

---

# 14. P2 — Central Control Plane

Central không phải “database thay local”.

Nó là:

> **Identity + License + Product Intelligence + Distribution Control Plane**

---

## 14.1. Central Companies

```text
companies
- id
- external/local_company_id
- owner_platform_user_id
- plan
- status
- created_at
- activated_at
- last_seen_at
- current_stage
- seats
- project_count
```

---

## 14.2. Central Projects

Central nên lưu lifecycle metadata:

```text
projects
- platform_project_id
- company_id
- local_project_id
- name or privacy-safe label
- status
- stage
- created_at
- updated_at
- archived_at
- deleted_at
- first_revenue_at
- success_state
```

Không cần sync:

- full strategy document;
- interview transcript;
- CRM rows;
- accounting entries;
- API keys.

---

## 14.3. Project Lifecycle Events

Local outbox phát:

```text
COMPANY_CREATED
COMPANY_STAGE_CHANGED

PROJECT_CREATED
PROJECT_UPDATED
PROJECT_STAGE_CHANGED
PROJECT_ARCHIVED
PROJECT_RESTORED
PROJECT_DELETED

FIRST_CUSTOMER
FIRST_REVENUE
VALIDATED_REVENUE
PROJECT_SUCCESS_MARKED
```

Envelope:

```json
{
  "event_id": "uuid",
  "event_type": "PROJECT_STAGE_CHANGED",
  "schema_version": 1,
  "company_id": "...",
  "project_id": "...",
  "occurred_at": "...",
  "payload": {},
  "privacy_class": "METADATA"
}
```

---

## 14.4. Idempotency

Central inbox:

```text
unique(event_id)
```

Process:

```text
receive
→ verify company
→ reject invalid schema
→ deduplicate
→ transaction apply
→ ack
```

Local outbox:

```text
PENDING
SENDING
ACKNOWLEDGED
FAILED_RETRYABLE
DEAD_LETTER
```

---

# 15. P2 — Product Intelligence

COSA operator có thể biết:

```text
bao nhiêu companies
bao nhiêu free/pro
bao nhiêu projects
stage distribution
project completion/success
first revenue conversion
time S0 → S1 → S2...
retention
feature adoption
agent usage aggregated
```

Không đọc nội dung private của company nếu không có consent.

---

# 16. Data Classification

| Data | Local | Central | Ghi chú |
|---|---|---|---|
| User local account | Yes | Identity mapping | Central phục vụ license |
| Company profile | Yes | Minimal metadata | |
| Projects | Full | Lifecycle metadata | |
| Stage | Yes | Yes | analytics |
| Strategy docs | Yes | No mặc định | |
| PESTEL/SWOT/TOWS | Yes | No | |
| OKR/12WY | Yes | Aggregate optional | |
| Tasks | Yes | No | |
| CRM leads | Yes | No | |
| Marketing campaign details | Yes | Aggregate optional | |
| Finance transactions | Yes | No | |
| Legal documents | Yes | No | |
| API keys | Yes | Never | encrypted |
| Agent prompts override | Yes | No | |
| Platform default prompt | local cached | Source central | signed/versioned |
| License | cached | Source central | signed |
| Project lifecycle | Yes | Yes | event sync |
| First revenue milestone | Yes | Yes metadata | no amount unless consent |
| Product telemetry | minimal | Yes | privacy-safe |

---

# 17. P2 — Update Distribution

Central có thể phân phối:

```text
Prompt Pack
Business Pack
Legal Templates
Policy Data
Agent Manifest
Tool Definitions
Stage Methodology
UI Feature Flags
```

Package:

```json
{
  "pack_id": "...",
  "version": "2026.08.1",
  "checksum": "...",
  "signature": "...",
  "min_cosa_version": "...",
  "files": []
}
```

Local:

```text
download
verify signature
show diff
backup
apply
rollback
```

Company override không bị overwrite.

---

# 18. Frontend Refactor

## 18.1. Main route policy

Giữ top-level:

```text
Login
Hologram Hub
Mission Control
Settings/Admin
```

Dashboard cũ nếu trùng Hologram phải xem xét merge.

---

## 18.2. Hologram Hub

### Command Center

```text
COSA Co-Founder
Company Pulse
Top 3
Waiting for You
```

### Workforce tab

Chỉ show:

```text
COSA
5 Core Agents
Enabled Optional Packs
```

Không show legacy aliases.

---

## 18.3. Module inventory

Claude Code phải scan:

```text
frontend/lib/modules/*
```

Tạo file:

```text
docs/architecture/frontend_module_inventory.md
```

Mỗi module:

```text
ACTIVE
INTERNAL
OPTIONAL
LEGACY
DEPRECATED
```

Không delete trước inventory.

---

# 19. Realtime Voice

Kiến trúc hiện tại giữ nguyên:

```text
Desktop
→ LiveKit Local
→ realtime-agent local

Mobile/Web
→ LiveKit Cloud
→ realtime-agent-cloud
```

COSA voice phải gọi cùng Co-Founder runtime, không tạo logic riêng.

Voice chỉ là transport:

```text
voice input
→ transcript
→ Co-Founder API/runtime
→ response
→ TTS
```

Không duplicate intent routing.

---

# 20. OpenSandbox Security

OpenSandbox được xem như privileged plane.

Yêu cầu:

- không expose public;
- network policy;
- resource quotas;
- execution timeout;
- workspace temp directory;
- no host secret mount;
- Docker socket access phải được đánh giá riêng;
- prefer isolated Docker proxy/runtime nếu có thể;
- destructive command policy;
- audit all executions.

Execution record phải lưu:

```text
who
agent
mission
command/tool
sandbox
started_at
finished_at
exit_code
artifact
risk_level
approval_id
```

---

# 21. API Contract Cleanup

## 21.1. Không mount cùng router ở nhiều prefix nếu không cần

Audit các pattern:

```text
router.include_router(x, prefix="/api/v1/...")
router.include_router(x, prefix="/api/v1")
```

Nếu chỉ để compatibility:

```text
mark legacy route
emit deprecation header
remove after transition
```

## 21.2. API versioning

Canonical mới:

```text
/api/v1/cofounder/*
/api/v1/missions/*
/api/v1/workforce/*
/api/v1/founder-os/*
/api/v1/business/*
/api/v1/platform/*
```

Tránh tạo `/api/v2` chỉ để sửa nội bộ.

---

# 22. Naming Cleanup

Repo cũ tên `javis-saas`, nhưng product là COSA.

Không rename repo/path ngay nếu gây migration lớn.

Ưu tiên:

```text
user-facing: COSA
API title: COSA
container future: cosa_*
docs: COSA
```

`javis_*` container/database có thể đổi ở maintenance release.

---

# 23. Test Strategy

---

## 23.1. P0 Tests

### License

- valid Ed25519 snapshot;
- invalid signature;
- wrong key;
- expired;
- grace period;
- restart retains entitlement;
- local cannot sign.

### Workspace Security

- user A cannot query workspace B;
- forged `X-Workspace-ID` rejected;
- forged `X-Company-ID` ignored;
- admin/member permissions.

### Greeting

- greeting no project query;
- greeting no company pulse call.

### UI truth

- approval API failure leaves item;
- chat failure not show “mission started”.

---

## 23.2. P1 Runtime Tests

Scenario:

```text
Founder: “Tìm 20 qualified prospects trong 30 ngày”
```

Expected:

1. intent Founder Command;
2. ContextBundle;
3. Mission DRAFT;
4. founder confirmation;
5. AgentPlan;
6. Marketing/Sales steps;
7. execution jobs;
8. approvals if external sending;
9. artifacts;
10. outcome;
11. Hologram refresh.

Test database state at every step.

---

## 23.3. Stage Tests

New workspace:

```text
S0_GENESIS
```

S0 UI không suggest BSC.

S5 có thể suggest BSC.

Founder request SWOT at S1 vẫn được chạy nhưng COSA có thể cảnh báo evidence thấp.

---

# 24. CI Gate bổ sung

Giữ CI hiện tại và thêm:

```text
security-contract-tests
workspace-isolation-tests
license-crypto-tests
cofounder-e2e-tests
no-global-agent-mutation-test
no-hardcoded-business-metric-test
```

Có thể tạo static rule:

Search forbidden patterns trong Co-Founder service:

```text
"50 triệu"
"7.5 tháng"
"25-30%"
```

nếu đó là sample production logic.

---

# 25. Database Migration Principles

1. One concern per migration.
2. Backward compatible trước.
3. Data backfill riêng.
4. Index trước workload mới.
5. Không drop column cùng release chuyển read/write.
6. Mọi migration chạy qua:
   - `alembic upgrade head`;
   - `alembic check`;
   - integration tests.
7. Backup trước migration production.
8. Large table migration phải online-safe.

---

# 26. Implementation Phases

---

## Phase 0A — Security Freeze

**Không thêm feature mới.**

Deliverables:

- Ed25519 entitlement;
- local snapshot persistence;
- local/control plane separation;
- WorkspaceContext;
- CORS;
- no default prod signing secret.

Exit criteria:

```text
license cannot be forged by local runtime
cross-workspace access blocked
production startup safe
```

---

## Phase 0B — Runtime Truth

Deliverables:

- greeting fix;
- approval real API;
- chat failure truth;
- remove hard-coded business synthesis;
- Pulse backed by data;
- Genesis stage default.

Exit criteria:

```text
No UI success without backend success.
No business number without source.
```

---

## Phase 1A — Co-Founder Mission Runtime

Deliverables:

- ContextAssembler;
- Mission creation;
- Mission confirmation;
- AgentPlan;
- Execution mapping;
- outcome aggregation;
- Hologram update.

Exit criteria:

Một founder command chạy end-to-end.

---

## Phase 1B — Workforce Consolidation

Deliverables:

- canonical agent inventory;
- hide legacy aliases;
- workspace agent override;
- no global mutation;
- 1 + 5 visible workforce.

---

## Phase 1C — Stage Operating Engine

Deliverables:

- S0–S6;
- stage-aware Top3;
- stage-aware Hologram;
- capability recommendation;
- PESTEL/SWOT/TOWS/BSC as capability.

---

## Phase 2 — Central Intelligence

Deliverables:

- company/project lifecycle sync;
- project stage analytics;
- entitlement distribution;
- signed pack update;
- project success/revenue milestones;
- product analytics.

---

# 27. File-Level Implementation Checklist

## Backend core

```text
backend/app/main.py
- production CORS
- local/control route boundary
- startup validation
```

```text
backend/app/core/runtime_config.py
- Ed25519 key validation
- plane validation
- CORS validation
```

---

## Auth

```text
backend/app/platform/auth/models.py
- default stage S0_GENESIS
```

```text
backend/app/platform/auth/router.py
- create new workspace Genesis
```

```text
backend/app/core/auth.py
- WorkspaceContext dependency
```

---

## Entitlement

```text
backend/app/platform/sync/entitlement_crypto.py
- Ed25519 sign/verify
```

```text
backend/app/platform/sync/entitlement_manager.py
- DB-backed current snapshot
```

```text
backend/app/platform/sync/entitlement_guard.py
- derive company from WorkspaceContext
```

```text
backend/app/platform/sync/router.py
- remove local sign endpoint
- central auth
```

---

## Co-Founder

```text
backend/app/workforce/routing/deterministic.py
- GREETING
```

```text
backend/app/workforce/routing/router.py
- structured route contract
```

```text
backend/app/workforce/api/cofounder_api.py
- WorkspaceContext
```

```text
backend/app/workforce/orchestrator/cosa_cofounder_service.py
- no hard-code
- context assembler
- mission creation
- runtime integration
```

---

## Workforce

```text
backend/app/workforce/api/packs_api.py
- no global mutation
- workspace override
- hide legacy
```

```text
backend/app/workforce/registry/defaults.py
- immutable manifests
- metadata categories
```

```text
backend/app/workforce/models.py
- canonical model review
```

```text
backend/app/db/base.py
- remove duplicate imports only after migrations complete
```

---

## Worker

```text
backend/app/worker_main.py
- reuse execution runtime
- mission/run event hooks
```

---

## Strategy

```text
backend/app/founder_os/strategy/models.py
- preserve strategy capabilities
- stage policy
- avoid duplicate strategy entities
```

---

## Flutter

```text
frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart
- real approvals
- no fake chat success
```

```text
frontend/lib/data/services/cofounder_api_service.dart
- Workspace context support
- mission endpoints
```

```text
frontend/lib/data/services/approvals_service.dart
- canonical approval calls
```

```text
frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
- stage-aware cards
- 1 + 5 workforce
```

---

## Infrastructure

```text
docker-compose.yml
- plane env
- public entitlement key local
- private key central only
- CORS env
```

```text
.github/workflows/quality.yml
- add P0/P1 gates
```

---

# 28. Definition of Done

COSA được xem là hoàn thành giai đoạn consolidation khi:

### Product

- Founder chat là entry point thật.
- Greeting không trigger business flow.
- Hologram chỉ show thông tin cần hành động.
- Co-Founder không giả trạng thái.
- Top 3 dựa trên dữ liệu thật.

### Workforce

- 1 Co-Founder + 5 core domains.
- Optional agents hidden by default.
- Mission thực sự dispatch Agent.
- Approval thực sự unlock execution.

### Data

- business data local-first;
- central lifecycle metadata sync;
- company/project/stage history có thể phân tích.

### Security

- local không có private entitlement signing key;
- workspace isolation enforced;
- secrets không lộ cho LLM;
- production CORS restricted.

### Architecture

- canonical agent/run model documented;
- no new duplicate model;
- deprecated entities có migration plan.

---

# 29. Prompt triển khai cho Claude Code

## Prompt 1 — Audit trước refactor

```text
Bạn đang làm việc trên repository COSA hiện tại.

Mục tiêu:
Lập inventory chính xác trước khi chỉnh code. KHÔNG tạo model/table mới ở bước này.

Hãy:
1. Đọc backend/app/db/base.py.
2. Tìm tất cả models liên quan:
   Agent, AgentDefinition, AgentRun, AgentStep, Mission, AgentGoal, AgentPlan,
   ExecutionJob, ApprovalRequest, FounderDecision, Outcome, Artifact,
   EvidenceItem, NextActionCandidate, NextActionRanking, WorkspaceAgent.
3. Tìm router/service/test đang reference từng model.
4. Tìm Alembic migrations tạo/chỉnh từng table.
5. Tạo docs/architecture/canonical_model_inventory.md với bảng:
   - entity
   - table
   - responsibility
   - write paths
   - read paths
   - status: ACTIVE/COMPATIBILITY/DEPRECATED
   - proposed canonical replacement
6. KHÔNG xóa, rename hoặc migrate database.
7. Chạy test/boundary check hiện tại và ghi kết quả.

Đầu ra:
- inventory doc
- không thay đổi runtime behavior
- danh sách conflict/duplication có evidence bằng file path.
```

---

## Prompt 2 — P0 License Security

```text
Triển khai P0 License Security cho COSA.

Bắt buộc:
- thay HMAC entitlement bằng Ed25519;
- Central giữ private key;
- Local chỉ giữ public key;
- hỗ trợ key_id;
- persist entitlement snapshot trong PostgreSQL local;
- restart vẫn giữ license;
- không còn endpoint sign entitlement trên company runtime;
- backward compatibility HMAC chỉ dùng để migrate nếu cần;
- không có production fallback signing secret trong source.

Trước khi tạo table:
search toàn repo xem đã có entitlement persistence model chưa.

Thêm tests:
- valid signature;
- invalid signature;
- expired;
- grace;
- wrong key;
- restart;
- local cannot sign.

Không thay đổi business domain logic.
```

---

## Prompt 3 — Workspace Isolation

```text
Triển khai WorkspaceContext thống nhất.

Yêu cầu:
- derive workspace membership từ JWT + DB;
- không tin raw X-Company-ID;
- không tin workspace_id body/query nếu user không thuộc workspace;
- derive company_id server-side;
- attach company_stage và entitlement;
- áp dụng trước cho cofounder_api và workforce packs;
- giữ compatibility header nếu cần nhưng validate.

Viết integration tests user A không thể đọc/sửa workspace B.
```

---

## Prompt 4 — Runtime Truth

```text
Sửa toàn bộ các điểm UI/API báo thành công giả.

Ưu tiên:
1. Hologram approveTask phải gọi ApprovalsService.approve().
2. Không remove UI item nếu backend fail.
3. Co-Founder chat API fail phải báo request failed, không nói agent đang chạy.
4. deterministic greeting trả GREETING.
5. greeting không query project/company pulse.
6. tìm các snackbar/success fallback tương tự trong Hologram/Mission Control.

Tạo test cho từng hành vi.
```

---

## Prompt 5 — Co-Founder Data Truth

```text
Refactor cosa_cofounder_service.py.

Cấm hard-coded business metrics và recommendation giả.

Tách:
- ContextAssembler
- PulseCalculator
- NextActionEngine
- CrossDomainSynthesis
- ResponsePresenter

Ưu tiên reuse:
- EvidenceItem
- NextActionCandidate
- NextActionRanking
- TwelveWeekCycle
- WeeklyPlan
- FounderDecision
- ApprovalRequest
- AgentRun/ExecutionJob canonical sau inventory
- business domain snapshots hiện có.

Nếu thiếu dữ liệu:
trả unknown/not_enough_data thay vì tạo số giả.

Mọi con số phải có source metadata.
```

---

## Prompt 6 — Co-Founder Mission E2E

```text
Triển khai một happy path end-to-end:

Founder:
"Tìm 20 khách hàng tiềm năng phù hợp trong 30 ngày."

Expected:
1. FOUNDER_COMMAND.
2. ContextBundle.
3. Tạo Mission DRAFT.
4. Trả mission preview cho founder.
5. Founder confirm.
6. Tạo AgentPlan tối thiểu Marketing + Sales.
7. Map plan step sang executor thật.
8. Queue runtime hiện có.
9. Nếu cần gửi external outreach -> approval.
10. Sau approval worker tiếp tục.
11. Tạo artifacts/evidence/outcome.
12. Hologram cập nhật active mission và result.

KHÔNG tạo parallel worker architecture.
Reuse worker_main.py, existing execution/governance/outcome components.

Viết integration/e2e test DB state từng bước.
```

---

## Prompt 7 — Workforce Consolidation

```text
Mục tiêu UI/runtime:
COSA + 5 Core Domain Agents.

Không xóa legacy aliases ngay.

Hãy:
- đánh dấu legacy agents invisible;
- global AgentDefinition immutable;
- workspace toggle chỉ ghi override;
- Co-Founder không thể disable;
- optional packs inactive/hidden mặc định;
- sửa API list packs;
- sửa Flutter workforce tab.

Đảm bảo founder A toggle không ảnh hưởng founder B/global defaults.
Viết integration test.
```

---

## Prompt 8 — Stage Engine

```text
Triển khai stage-aware operating policy S0-S6.

Default workspace mới = S0_GENESIS.

Stage chỉ điều chỉnh recommendation/capability/UI, KHÔNG hard-block founder.

PESTEL/SWOT/TOWS/BSC:
- giữ model/data;
- chuyển thành capability;
- không top-level mặc định;
- BSC ưu tiên S5/S6;
- founder có thể gọi bất kỳ stage nào.

Top3 và Hologram phải dùng stage để chọn focus.
```

---

# 30. Anti-Patterns Claude Code phải tránh

Không:

```text
create new *_v2 model because easier
create another AgentRun
create another Mission table
fork another worker
hard-code sample metrics
edit global agent defaults from workspace
store API key central
sync full company data central
expose model/agent selection to founder by default
add 20 dashboard menu items
make validation a mandatory gate
```

---

# 31. Recommended Commit Sequence

```text
chore: add canonical architecture inventory

security: add ed25519 entitlement verification
security: split entitlement issuer from company runtime
feat: persist local entitlement snapshots
security: add workspace context isolation

fix: set new workspace to genesis stage
fix: normalize greeting intent
fix: make hologram approvals transactional
fix: remove fake cofounder success fallbacks

refactor: extract cofounder context assembler
refactor: make company pulse data-backed
refactor: make next actions evidence-backed

feat: connect cofounder command to mission runtime
feat: connect mission plan to existing agent execution
feat: expose mission outcome in hologram hub

refactor: isolate workspace agent overrides
refactor: hide legacy workforce aliases
feat: add stage-aware operating policies

feat: sync company/project lifecycle to control plane
feat: distribute signed platform packs
```

Mỗi commit phải nhỏ, rollback được.

---

# 32. Kết luận kiến trúc

COSA đã có đủ các mảnh chính.

Không nên tối ưu tiếp theo hướng:

> “thêm nhiều AI agent hơn”.

Nên tối ưu theo hướng:

> **“COSA hiểu đúng → dùng dữ liệu đúng → giao đúng runtime → theo dõi đúng trạng thái → trả đúng outcome.”**

North Star cuối cùng:

```text
Founder nói mục tiêu
      ↓
COSA hiểu bối cảnh
      ↓
COSA hỏi/challenge khi thật sự cần
      ↓
Mission được tạo
      ↓
Agent phù hợp được điều phối
      ↓
Tool/Workflow/Sandbox chạy
      ↓
Founder duyệt điểm rủi ro
      ↓
Artifacts + Evidence được thu
      ↓
Outcome được đo
      ↓
Hologram Hub cập nhật
      ↓
COSA đề xuất Next Best Action
```

Khi flow này ổn định, COSA mới nên tiếp tục mở rộng capability, integrations và business packs.

---

# 33. Checklist trước khi bắt đầu thêm bất kỳ tích hợp mới

Trước khi tích hợp repo/framework mới, trả lời 7 câu:

1. Nó giải quyết capability nào mà COSA chưa có?
2. Có cần Agent mới hay chỉ Skill/Tool?
3. Có entity nào hiện tại reuse được?
4. Nó gắn vào Mission runtime ở bước nào?
5. Dữ liệu local hay central?
6. Risk/approval level?
7. Hologram sẽ chỉ hiển thị outcome gì?

Nếu không trả lời được 7 câu này:

> **Chưa tích hợp.**

Đây là cơ chế chống phình kiến trúc cho COSA.
