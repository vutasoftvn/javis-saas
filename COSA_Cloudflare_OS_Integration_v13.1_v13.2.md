# COSA — Cloudflare OS Architecture Integration Guide
## Tích hợp các pattern Workspace, Gatekeeper, Sandbox, Action Center, Provenance, Mini App và Blueprint vào COSA v13.1 / v13.2

**Trạng thái:** Implementation specification  
**Đối tượng sử dụng:** Claude Code / đội phát triển COSA  
**Ngày:** 2026-08-15  
**Mục tiêu:** Áp dụng các ý tưởng kiến trúc phù hợp từ Cloudflare OS vào COSA mà **không fork Cloudflare OS**, **không thay FastAPI/PostgreSQL**, và **không phụ thuộc Cloudflare Workers/Durable Objects**.

---

# 1. Executive Summary

Cloudflare OS là một "AI productivity operating system" mã nguồn mở, tập trung vào ba khả năng cốt lõi:

1. Agent Workspace được nạp context và skills của tổ chức.
2. Ứng dụng nhỏ do AI tạo, chạy trong sandbox và có thể được tái sử dụng dưới dạng Blueprint.
3. Gatekeeper kiểm soát truy cập tài nguyên theo capability, ghi log hành động và đưa các thao tác có side effect vào Human-in-the-Loop.

COSA không nên fork hoặc chuyển runtime sang Cloudflare OS. Kiến trúc hiện tại của COSA phù hợp hơn với mục tiêu Founder / One Person Company:

- Flutter/GetX frontend.
- Python FastAPI backend.
- PostgreSQL làm system of record.
- DeepSeek Harness cho agent execution.
- DSPy cho evaluation/optimization ở các workflow AI phù hợp.
- OpenSandbox cho code/tool execution cô lập.
- n8n cho deterministic automation và integration.
- LiveKit cho realtime voice.
- Multi-model routing qua COSA AI Gateway.

Tài liệu này chuyển các pattern tốt nhất của Cloudflare OS thành các module native của COSA:

- Founder Workspace
- COSA Context Library
- Capability Gateway
- AI Action Center
- Observation / Provenance Graph
- Sandbox Runtime
- COSA Mini Apps
- COSA Blueprints
- COSA AI Gateway
- Policy & Approval Engine
- Audit & Observability

> **Nguyên tắc kiến trúc:** Cloudflare OS là nguồn tham khảo về mô hình; COSA tự triển khai các primitive tương đương trên stack hiện tại.

---

# 2. Phạm vi và Non-goals

## 2.1. Phạm vi triển khai

Tài liệu này tập trung vào **AI runtime + governance + execution layer**.

Các domain agent có thể sử dụng nền tảng này:

- Founder / CEO
- Project
- OKR
- 12 Week Year
- Weekly Tactics
- Tasks
- Daily Top 3
- Weekly Review
- Week 13
- Finance
- Sales
- Marketing
- Legal
- Learning

## 2.2. Không triển khai trong tài liệu này

Không dùng tài liệu này để:

- fork nguyên repository `cloudflare/cloudflare-os`;
- chuyển FastAPI sang Cloudflare Workers;
- thay PostgreSQL bằng Durable Objects/KV/R2;
- đưa Cloudflare Access thành dependency bắt buộc;
- bắt buộc sử dụng Cap'n Web RPC;
- bắt buộc sử dụng Cloudflare AI Gateway;
- tái kích hoạt các module Strategy đã được tạm ẩn/disable như PESTEL, SWOT, TOWS;
- tạo một "version mới" độc lập ngoài baseline v13.1/v13.2.

Nếu sau này Strategy được bật lại, nó chỉ là một domain sử dụng Agent Runtime mới, không được gắn cứng vào core runtime.

---

# 3. Những pattern từ Cloudflare OS cần học

## 3.1. Workspace là execution context, không chỉ là chat

Một Workspace phải chứa:

```text
Workspace
├── goal
├── agent sessions
├── context
├── memory
├── files
├── outputs
├── resources
├── capabilities
├── sandbox
├── actions
└── observations
```

Do đó COSA Chat không được tiếp tục là một cửa sổ hội thoại tách biệt.

Chat/Voice chỉ là **interface** của Workspace.

## 3.2. Capability-based security

Mặc định:

```text
Agent = NO ACCESS
Mini App = NO ACCESS
Workflow = NO ACCESS
```

Quyền chỉ được cấp khi có:

```text
subject
+ resource
+ capability
+ scope
+ policy
+ expiry
```

Ví dụ:

```text
SalesAgent
  can:
    crm.lead.read
    crm.lead.create
    crm.lead.update

  cannot:
    email.send
    invoice.issue
    payment.transfer
```

Không được cấp quyền kiểu:

```text
SalesAgent -> access_to_everything = true
```

## 3.3. Human-in-the-loop không được chặn reasoning

Thay vì:

```text
Agent
  -> cần gửi email
  -> STOP
  -> đợi founder approve
```

COSA dùng:

```text
Agent
  -> propose email.send
  -> simulate outcome
  -> continue reasoning
  -> propose next actions
  -> Action Center
  -> founder approve/reject batch
  -> execute actual side effects
```

## 3.4. AI nên là toolmaker, không phải lúc nào cũng là executor

Nếu một flow có thể deterministic:

```text
trigger
-> SQL/query
-> rule
-> transform
-> API
```

thì không chạy LLM ở mọi bước.

LLM chỉ dùng ở:

- classification khó;
- extraction semantic;
- reasoning;
- drafting;
- exception handling;
- recommendation;
- synthesis.

Sau khi flow ổn định:

```text
AI designs
n8n executes
AI handles exceptions
```

## 3.5. App có thể trở thành artifact của AI

Một cuộc hội thoại có thể chuyển thành:

```text
Conversation
  -> Specification
  -> Mini App
  -> Blueprint
  -> reusable business capability
```

Đây là hướng COSA nên phát triển sau khi Agent Runtime và Gatekeeper ổn định.

---

# 4. Target Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       COSA Founder OS                       │
├─────────────────────────────────────────────────────────────┤
│ Interfaces                                                  │
│ Flutter Desktop / Mobile / Web / Chat / LiveKit Voice       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Founder Workspace                       │
│ goal · sessions · files · context · memory · resources      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                       │
│ intent · planning · agent routing · task graph              │
└───────────┬─────────────────┬─────────────────┬─────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
      Context Engine      Skill Registry    Memory Engine
            │                 │                 │
            └─────────────────┼─────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Agent Runtime                           │
│ DeepSeek Harness · DSPy evaluation · Tool Runtime           │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
       OpenSandbox          Mini App Runtime
              │                 │
              └────────┬────────┘
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Capability Gateway                         │
│ authz · scope · policy · simulation · approval · audit      │
└─────────────┬────────────────────┬──────────────────────────┘
              │                    │
         safe reads          side effects
              │                    │
              ▼                    ▼
       execute directly      AI Action Center
                                   │
                             approve/reject
                                   │
                                   ▼
                               executor
                                   │
         ┌─────────────────────────┼─────────────────────┐
         ▼                         ▼                     ▼
      PostgreSQL                 n8n               External APIs
         │                                             │
         ├─ Finance                                   Gmail
         ├─ Sales                                     Zalo
         ├─ Marketing                                 Telegram
         ├─ Legal                                     CRM
         └─ Work                                      Banking*
```

`*` Financial transfer/signature must remain strongly restricted.

---

# 5. Core Modules mới

Đề xuất tạo các module backend:

```text
app/
├── workspace/
├── context/
├── skills/
├── agents/
├── capabilities/
├── actions/
├── observations/
├── sandbox/
├── miniapps/
├── blueprints/
├── ai_gateway/
├── policies/
├── audit/
└── integrations/
```

Không cần refactor toàn bộ codebase ngay lập tức. Tạo adapter quanh domain hiện hữu.

---

# 6. Founder Workspace

## 6.1. Mục tiêu

Workspace là boundary chính giữa:

- user;
- agent;
- resources;
- context;
- session;
- sandbox;
- actions.

Một founder có thể có nhiều workspace:

```text
Founder
├── Company Workspace
├── Product Launch Workspace
├── Sales Q3 Workspace
├── Finance Workspace
└── Learning Workspace
```

## 6.2. Data model

### `workspaces`

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL,
    company_id UUID,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    workspace_type VARCHAR(64),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `workspace_members`

```sql
CREATE TABLE workspace_members (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, user_id)
);
```

Đối với One Person Company, schema vẫn hỗ trợ nhiều thành viên để không khóa khả năng mở rộng.

## 6.3. Workspace state

Không nhồi toàn bộ state vào một JSON lớn.

Tách thành:

- workspace metadata;
- sessions;
- context links;
- resource introductions;
- capability grants;
- actions;
- observations;
- artifacts.

---

# 7. Context Library

## 7.1. Context hierarchy

```text
Global COSA Context
        ↓
Company Context
        ↓
Domain Context
        ↓
Project Context
        ↓
Workspace Context
        ↓
Session Context
```

## 7.2. Context types

```text
policy
procedure
terminology
company_fact
project_fact
financial_rule
sales_playbook
marketing_playbook
legal_guideline
learning_note
skill_instruction
```

## 7.3. Context entity

```sql
CREATE TABLE context_documents (
    id UUID PRIMARY KEY,
    company_id UUID,
    owner_id UUID,
    title VARCHAR(255) NOT NULL,
    context_type VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    source_type VARCHAR(64),
    source_uri TEXT,
    visibility VARCHAR(32) NOT NULL DEFAULT 'private',
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 7.4. Context không đồng nghĩa vector search

Retrieval nên kết hợp:

```text
explicitly attached context
+ structured company/project data
+ permissions
+ lexical retrieval
+ semantic retrieval
+ recency
+ source reliability
```

Không đưa toàn bộ knowledge base vào context window.

---

# 8. Skill Registry

## 8.1. Skill là reusable business procedure

Ví dụ:

```text
skills/
├── work/
│   ├── create_okr
│   ├── weekly_review
│   └── week13_review
├── finance/
│   ├── cashflow_review
│   ├── expense_classification
│   └── monthly_close
├── sales/
│   ├── lead_qualification
│   ├── follow_up
│   └── forecast
├── marketing/
│   ├── market_research
│   ├── campaign_plan
│   └── content_repurpose
└── legal/
    └── contract_review
```

## 8.2. Skill manifest

```yaml
id: sales.follow_up
name: Sales Follow Up
version: 1
agent_types:
  - sales
inputs:
  - lead_id
required_capabilities:
  - crm.lead.read
  - crm.activity.read
optional_capabilities:
  - email.draft
side_effect_capabilities:
  - email.send
execution:
  mode: hybrid
  deterministic_first: true
evaluation:
  enabled: true
  evaluator: dspy
```

## 8.3. DSPy role

DSPy không thay thế skill.

DSPy dùng cho:

- prompt/program optimization;
- structured output reliability;
- evaluator;
- regression test;
- scoring;
- selecting candidate reasoning program.

Không dùng DSPy để quản lý quyền hoặc execution.

---

# 9. Capability Gateway

Đây là module quan trọng nhất của thay đổi kiến trúc.

## 9.1. Mục tiêu

Mọi access từ:

- agent;
- skill;
- workflow;
- Mini App;
- sandbox code

đến:

- PostgreSQL domain service;
- Gmail;
- CRM;
- Zalo;
- Telegram;
- n8n;
- filesystem;
- external API

đều phải qua Gateway khi resource có security boundary.

## 9.2. Capability structure

```json
{
  "subject_type": "agent",
  "subject_id": "sales-agent",
  "resource_type": "crm.lead",
  "resource_id": "lead-123",
  "actions": ["read", "update"],
  "scope": {
    "company_id": "company-1"
  },
  "expires_at": null
}
```

## 9.3. Naming convention

```text
domain.resource.action
```

Ví dụ:

```text
crm.lead.read
crm.lead.create
crm.lead.update

email.message.read
email.message.draft
email.message.send

finance.invoice.read
finance.invoice.draft
finance.invoice.issue

finance.payment.read
finance.payment.request
finance.payment.transfer

marketing.post.draft
marketing.post.publish

legal.contract.read
legal.contract.draft
legal.contract.sign
```

## 9.4. Capability grant table

```sql
CREATE TABLE capability_grants (
    id UUID PRIMARY KEY,
    workspace_id UUID,
    subject_type VARCHAR(32) NOT NULL,
    subject_id UUID NOT NULL,
    capability VARCHAR(128) NOT NULL,
    resource_type VARCHAR(128),
    resource_id VARCHAR(255),
    scope JSONB NOT NULL DEFAULT '{}',
    granted_by UUID NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 9.5. Default deny

Pseudo-code:

```python
decision = policy_engine.evaluate(request)

if decision == "deny":
    raise CapabilityDenied()

if decision == "read":
    return executor.execute()

if decision == "write_auto":
    return executor.execute_with_audit()

if decision == "approval":
    return action_center.simulate_and_queue()

if decision == "manual_only":
    return ManualActionRequired()
```

---

# 10. Policy & Risk Levels

Áp dụng 6 level:

| Level | Loại | Ví dụ | Default |
|---|---|---|---|
| L0 | Read | đọc lead | auto |
| L1 | Analyze | phân tích cashflow | auto |
| L2 | Draft | draft email | auto |
| L3 | Internal write | update lead status | policy |
| L4 | External side effect | send email, publish post | approval |
| L5 | Legal/Financial critical | transfer, sign contract | strong approval/manual |

## 10.1. Strong approval

L5 phải hỗ trợ:

- explicit user confirmation;
- re-authentication tùy deployment;
- transaction summary;
- immutable audit event;
- amount/recipient validation;
- optional second factor.

Không cho LLM tự bypass.

## 10.2. Policy examples

```yaml
capability: email.message.send
risk_level: L4
approval: required

capability: crm.lead.update
risk_level: L3
approval:
  when:
    - field in ["owner_id", "deal_value"]
    - bulk_count > 20

capability: finance.payment.transfer
risk_level: L5
approval: manual_only
```

---

# 11. AI Action Center

## 11.1. Mục tiêu

Đây phải là màn hình trung tâm của COSA, nơi Founder quản lý các side effects được AI đề xuất.

```text
AI ACTION CENTER

Pending 7 | Approved 2 | Rejected 1 | Executed 34

[Finance]
Draft invoice #INV-102           READY
Issue invoice #INV-102           APPROVAL

[Sales]
Update lead stage                AUTO
Send follow-up to ACME           APPROVAL

[Marketing]
Publish LinkedIn post            APPROVAL
```

## 11.2. Action states

```text
proposed
simulated
pending_approval
approved
rejected
executing
executed
failed
expired
cancelled
```

## 11.3. Database

```sql
CREATE TABLE agent_actions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    agent_id UUID,
    session_id UUID,
    capability VARCHAR(128) NOT NULL,
    resource_type VARCHAR(128),
    resource_id VARCHAR(255),
    risk_level VARCHAR(8) NOT NULL,
    action_payload JSONB NOT NULL,
    simulation_result JSONB,
    status VARCHAR(32) NOT NULL,
    requested_by UUID,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    result JSONB,
    error JSONB,
    idempotency_key VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 11.4. Simulation contract

Connector hỗ trợ side effect phải có tối thiểu:

```python
class CapabilityConnector:
    async def observe(...)
    async def simulate(...)
    async def execute(...)
```

Ví dụ `email.send`:

### simulate

Trả:

```json
{
  "to": "customer@example.com",
  "subject": "...",
  "body_preview": "...",
  "attachments": [],
  "expected_result": "email_sent"
}
```

Không gửi email thật.

### execute

Chỉ chạy sau approval.

## 11.5. Batch approval

Action Center phải hỗ trợ:

```text
Approve selected
Reject selected
Edit before approve
```

Nhưng phải validate lại capability + policy tại thời điểm execute.

Approval cũ không được xem như quyền vĩnh viễn.

---

# 12. Observation / Provenance Graph

## 12.1. Vấn đề cần giải

Nếu AI nói:

> Doanh thu tháng này giảm do tỷ lệ chuyển đổi lead giảm.

COSA phải có khả năng trả lời:

- agent nào tạo kết luận;
- session nào;
- đã đọc dữ liệu nào;
- source nào;
- lúc nào;
- phiên bản nào;
- action nào phát sinh từ kết luận đó.

## 12.2. Observation table

```sql
CREATE TABLE agent_observations (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    session_id UUID,
    agent_id UUID,
    subject_type VARCHAR(32),
    subject_id UUID,
    resource_type VARCHAR(128) NOT NULL,
    resource_id VARCHAR(255),
    capability VARCHAR(128),
    operation VARCHAR(64),
    source_version VARCHAR(128),
    content_hash VARCHAR(128),
    metadata JSONB NOT NULL DEFAULT '{}',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 12.3. Artifact lineage

```sql
CREATE TABLE artifact_observations (
    artifact_id UUID NOT NULL,
    observation_id UUID NOT NULL,
    PRIMARY KEY (artifact_id, observation_id)
);
```

Graph:

```text
Lead #12 ─┐
Lead #18 ─┼─> observations
CRM KPI ──┘       │
                  ▼
           Sales Analysis
                  │
                  ▼
             Forecast
                  │
                  ▼
         Follow-up Actions
```

## 12.4. Provenance requirements

Mọi tool read quan trọng phải tạo observation.

Không cần log toàn bộ token hoặc mọi biến nội bộ.

Ưu tiên:

- source identity;
- query;
- version/hash;
- actor;
- resource;
- timestamp;
- resulting artifact/action.

---

# 13. Audit Event Store

Audit và Observation là hai khái niệm khác nhau.

### Observation

"Agent đã nhìn thấy gì?"

### Audit

"Hệ thống/agent/user đã làm gì?"

Schema:

```sql
CREATE TABLE audit_events (
    id UUID PRIMARY KEY,
    company_id UUID,
    workspace_id UUID,
    actor_type VARCHAR(32) NOT NULL,
    actor_id VARCHAR(255),
    event_type VARCHAR(128) NOT NULL,
    resource_type VARCHAR(128),
    resource_id VARCHAR(255),
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Event examples:

```text
capability.granted
capability.revoked
resource.observed
action.proposed
action.approved
action.rejected
action.executed
action.failed
sandbox.started
sandbox.terminated
miniapp.created
blueprint.instantiated
model.invoked
```

---

# 14. OpenSandbox Integration

## 14.1. Vai trò

OpenSandbox là execution boundary cho:

- code do agent tạo;
- data transformation;
- scripts;
- temporary files;
- testing Mini App;
- tool experiments.

## 14.2. Không cho sandbox network unrestricted

Default:

```text
internet = deny
filesystem = temporary
secrets = none
database = none
```

External access:

```text
sandbox
  -> Capability Gateway
  -> scoped connector
  -> external resource
```

Không inject:

- database password;
- Gmail token;
- CRM secret;
- n8n secret

trực tiếp vào sandbox.

## 14.3. Sandbox session

```sql
CREATE TABLE sandbox_sessions (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    agent_id UUID,
    status VARCHAR(32) NOT NULL,
    runtime VARCHAR(64),
    limits JSONB NOT NULL,
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);
```

## 14.4. Resource limits

Mỗi sandbox cần:

```text
cpu_limit
memory_limit
execution_timeout
disk_limit
network_policy
allowed_capabilities
```

---

# 15. COSA Mini App

Triển khai sau Capability Gateway + Action Center.

## 15.1. Định nghĩa

Mini App là một artifact chạy được, do AI hoặc developer tạo, phục vụ một workflow nhỏ.

Ví dụ:

```text
Sales Pipeline Dashboard
Cashflow Simulator
Weekly Review Board
Campaign Tracker
Customer Follow-up Console
```

## 15.2. Mini App manifest

```yaml
id: sales-pipeline-dashboard
name: Sales Pipeline Dashboard
version: 1
runtime: cosa-miniapp-v1

permissions:
  required:
    - crm.lead.read
  optional:
    - crm.lead.update

storage:
  mode: isolated

agent_api:
  enabled: true
```

## 15.3. Isolation

Mỗi instance:

```text
code
+ app state
+ capability bindings
+ owner
```

Không dùng shared credential.

## 15.4. Agent-friendly API

Không bắt buộc Cap'n Web.

COSA có thể chuẩn hóa:

```text
Mini App RPC
```

qua:

- HTTP/JSON;
- generated OpenAPI;
- internal Python interface;
- WebSocket khi realtime.

Yêu cầu quan trọng:

> API mà frontend gọi được thì Agent Runtime cũng có thể discover/call thông qua schema.

---

# 16. COSA Blueprint

## 16.1. Mục tiêu

Blueprint là template của Mini App hoặc workspace bundle.

Ví dụ:

```text
Founder Weekly Review Blueprint
Sales Pipeline Blueprint
Hotel Sales Blueprint
Agency CRM Blueprint
Startup Finance Blueprint
```

## 16.2. Security rule

Khi export Blueprint:

**ĐƯỢC PHÉP:**

- code;
- UI schema;
- workflow definition;
- skill references;
- capability requirements;
- sample/demo data.

**KHÔNG ĐƯỢC PHÉP:**

- production data;
- access token;
- OAuth credential;
- API key;
- chat history;
- private context;
- real customer data;
- personal memory.

## 16.3. Blueprint schema

```sql
CREATE TABLE blueprints (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    blueprint_type VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    manifest JSONB NOT NULL,
    code_location TEXT,
    visibility VARCHAR(32) NOT NULL DEFAULT 'private',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## 16.4. Instantiation

```text
Blueprint
  ↓
validate
  ↓
create new instance
  ↓
new isolated state
  ↓
request resource introductions
  ↓
grant capabilities
  ↓
ready
```

---

# 17. Resource Introduction

Không để agent tự tìm tất cả account/resources của Founder.

Founder "introduces" resource vào Workspace.

Ví dụ:

```text
Add Resource
├── Gmail account
├── CRM workspace
├── PostgreSQL dataset
├── Project
├── Finance ledger
└── GitHub repository
```

`workspace_resources`:

```sql
CREATE TABLE workspace_resources (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    resource_type VARCHAR(128) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    introduced_by UUID NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Resource introduction không tự cấp mọi action.

Ví dụ:

```text
resource: Gmail account
introduced: yes

capabilities:
  read: yes
  draft: yes
  send: no
```

---

# 18. COSA AI Gateway

## 18.1. Không bắt buộc Cloudflare AI Gateway

Xây adapter độc lập:

```text
Agent
  ↓
COSA AI Gateway
  ├── OpenAI
  ├── DeepSeek
  ├── Anthropic
  ├── Gemini
  ├── local model
  └── future provider
```

## 18.2. Routing policy

```yaml
routes:
  chat_default:
    provider: deepseek

  analysis:
    provider: openai

  coding:
    provider: anthropic

  low_cost_classification:
    provider: local_or_low_cost

  voice:
    provider: realtime_selected
```

Không hardcode tên model vào business logic.

## 18.3. Gateway telemetry

Lưu:

```text
provider
model
workspace
agent
skill
latency
input_tokens
output_tokens
estimated_cost
success/failure
```

## 18.4. Budget policy

```text
daily_budget
monthly_budget
workspace_budget
agent_budget
model_allowlist
fallback_chain
```

---

# 19. DeepSeek Harness Integration

DeepSeek Harness là **agent execution harness**, không phải security layer.

Flow:

```text
Workspace
  ↓
Orchestrator
  ↓
DeepSeek Harness
  ↓
Skill
  ↓
Tool request
  ↓
Capability Gateway
```

Harness không được bypass Gateway.

Tool registry trả cho harness chỉ nên chứa:

- schema;
- capability requirement;
- proxy endpoint.

Không trả credential.

---

# 20. n8n Integration

## 20.1. n8n là deterministic workflow executor

```text
AI
  -> design/configure workflow
n8n
  -> executes repeated workflow
AI
  -> only invoked where semantic reasoning is needed
```

## 20.2. n8n action cũng phải qua Gateway đối với side effect

Hai mô hình:

### Option A — preferred

```text
n8n
  -> COSA Capability API
  -> external connector
```

### Option B

n8n cầm credential riêng.

Chỉ dùng Option B khi customer tự quản lý n8n/VPS và boundary đã rõ.

Trong COSA-managed workflow, ưu tiên Option A.

## 20.3. Workflow examples

### Lead follow-up

```text
Cron
 -> get stale leads
 -> deterministic filter
 -> LLM drafts follow-up
 -> Action Center
 -> approve
 -> email.send
 -> update CRM
```

### Finance alert

```text
Cron
 -> query receivables
 -> calculate overdue
 -> threshold
 -> notify founder

LLM not required
```

---

# 21. LiveKit / Voice Integration

Voice phải dùng cùng Workspace + Permission system.

Không tạo một agent voice riêng có quyền khác không kiểm soát.

```text
LiveKit
  ↓
Speech/Realtime Model
  ↓
Workspace Session
  ↓
Agent Orchestrator
  ↓
Capability Gateway
```

Ví dụ Founder nói:

> Gửi email nhắc khách A thanh toán.

Voice agent:

1. nhận intent;
2. đọc invoice theo capability;
3. draft email;
4. tạo `email.message.send` action;
5. đọc lại summary cho user;
6. founder phê duyệt trong UI/voice;
7. execute.

L5 action không nên xác nhận chỉ bằng câu "ok" mơ hồ.

---

# 22. API Design

Base:

```text
/api/v1/workspaces
/api/v1/context
/api/v1/skills
/api/v1/agents
/api/v1/resources
/api/v1/capabilities
/api/v1/actions
/api/v1/observations
/api/v1/sandboxes
/api/v1/miniapps
/api/v1/blueprints
/api/v1/ai
/api/v1/audit
```

## 22.1. Capability check

```http
POST /api/v1/capabilities/check
```

Request:

```json
{
  "workspace_id": "...",
  "subject": {
    "type": "agent",
    "id": "..."
  },
  "capability": "email.message.send",
  "resource": {
    "type": "gmail.account",
    "id": "..."
  }
}
```

Response:

```json
{
  "allowed": true,
  "mode": "approval",
  "risk_level": "L4"
}
```

## 22.2. Propose action

```http
POST /api/v1/actions
```

## 22.3. Approve

```http
POST /api/v1/actions/{id}/approve
```

## 22.4. Execute

Internal service:

```http
POST /internal/actions/{id}/execute
```

Frontend không gọi execute trực tiếp nếu action cần approval.

---

# 23. Connector Interface

Tất cả integration nên dần chuyển về common interface.

```python
class ResourceConnector(Protocol):
    connector_id: str

    async def list_resources(self, user_context): ...
    async def observe(self, operation, resource, params): ...
    async def simulate(self, operation, resource, params): ...
    async def execute(self, operation, resource, params): ...
    def capabilities(self) -> list[str]: ...
```

Ví dụ connectors:

```text
connectors/
├── gmail/
├── telegram/
├── zalo/
├── crm/
├── finance/
├── postgres/
├── n8n/
└── filesystem/
```

---

# 24. Idempotency và Side-effect Safety

Mọi action thực thi bên ngoài phải có:

```text
idempotency_key
```

Ví dụ:

```text
email:{workspace}:{action_id}
invoice:{company}:{invoice_id}:{operation}
```

Trước execute:

```text
if already_executed(idempotency_key):
    return previous_result
```

Điều này ngăn agent retry và gửi 2 email / tạo 2 invoice.

---

# 25. Secrets Management

Không lưu API secret dạng plaintext trong:

- prompts;
- chat history;
- workspace metadata;
- action payload;
- Mini App code;
- sandbox env không kiểm soát.

Tạo abstraction:

```text
SecretRef
```

Ví dụ:

```json
{
  "provider": "vault",
  "secret_ref": "gmail/account-123"
}
```

Connector resolve secret tại execution time.

---

# 26. Frontend UX

## 26.1. Navigation đề xuất

```text
Home
Workspaces
AI
Action Center
Projects
OKRs
12 Week Year
Tasks
Finance
Sales
Marketing
Learning
Mini Apps
Settings
```

Không cần bật tất cả module cùng lúc.

## 26.2. Workspace screen

```text
┌───────────────────────────────┐
│ Workspace: Sales Q3           │
├───────────────────────────────┤
│ Chat / Voice                  │
│                               │
│                               │
├───────────────────────────────┤
│ Context    Resources    Files │
│ Actions    Outputs      Apps  │
└───────────────────────────────┘
```

## 26.3. Resource badge

Trong chat:

```text
Resources available:
[CRM Leads: read]
[Gmail: read + draft]
[Send Email: approval]
```

User phải thấy agent đang có quyền gì.

## 26.4. Action card

```text
SEND EMAIL

To: customer@acme.com
Subject: Payment reminder
Reason:
Invoice INV-102 overdue 7 days

AI simulation:
Expected result: follow-up email sent

[Edit] [Reject] [Approve]
```

---

# 27. Agent Contract

Mỗi Agent definition:

```yaml
id: sales-agent
name: Sales Agent

purpose:
  - manage leads
  - improve conversion
  - support founder sales

allowed_domains:
  - sales

default_capabilities:
  - crm.lead.read
  - crm.activity.read

requestable_capabilities:
  - crm.lead.update
  - email.message.draft
  - email.message.send

forbidden_capabilities:
  - finance.payment.transfer
  - legal.contract.sign

skills:
  - sales.lead_qualification
  - sales.follow_up
  - sales.forecast
```

Agent không tự cấp thêm capability.

---

# 28. Permission Escalation Flow

```text
Agent needs capability
        │
        ▼
Request Capability
        │
        ▼
Policy Engine
  ┌─────┼──────┐
  │     │      │
 deny  auto   ask user
              │
              ▼
        User grants scope
              │
              ▼
       capability_grant
              │
              ▼
         Agent retries
```

Grant có thể là:

```text
once
this workspace
this resource
until date
always for this policy
```

Không nên mặc định "always".

---

# 29. Local-first / VPS Deployment

Các pattern này phải chạy được trong ba mode:

## Desktop local

```text
Flutter Desktop
FastAPI local
PostgreSQL/local DB
OpenSandbox local
optional n8n local
```

## Customer VPS

```text
Flutter/Web Client
Customer FastAPI
Customer PostgreSQL
Customer n8n
OpenSandbox service
```

## Hybrid

```text
Desktop execution
+ cloud/mobile sync
+ remote inference
+ cloud LiveKit
```

Capability model phải giống nhau giữa các mode.

---

# 30. Migration Strategy

Không big-bang refactor.

## Phase 0 — Stabilize interfaces

- xác định Agent Runtime hiện tại;
- xác định Tool Registry;
- xác định integration đang bypass backend;
- thêm `workspace_id` vào session/action cần thiết.

## Phase 1 — Workspace + Resource Introduction

Implement:

- workspaces;
- sessions mapped to workspace;
- workspace_resources;
- context links;
- UI Workspace.

**Acceptance:**

- chat luôn thuộc workspace;
- agent chỉ thấy resource đã introduce.

## Phase 2 — Capability Gateway

Implement:

- capability registry;
- grant/revoke;
- policy engine;
- default deny;
- connector proxy.

**Acceptance:**

- không integration quan trọng nào được agent gọi trực tiếp;
- denied capability không thực thi.

## Phase 3 — Action Center

Implement:

- propose;
- simulate;
- approve/reject;
- execute;
- idempotency;
- audit.

**Acceptance:**

- email.send không chạy trước approval;
- simulation không tạo side effect;
- batch approval hoạt động.

## Phase 4 — Observation & Provenance

Implement:

- observations;
- artifact lineage;
- source view;
- audit timeline.

**Acceptance:**

- report quan trọng có "Sources used";
- có thể truy ngược output -> observations.

## Phase 5 — OpenSandbox Hardening

Implement:

- isolated execution;
- no ambient credentials;
- network deny by default;
- capability proxy;
- limits.

## Phase 6 — AI Gateway

Implement:

- provider adapters;
- routing;
- telemetry;
- cost/budget;
- fallback.

## Phase 7 — n8n deterministic automation

- convert stable repeated workflows;
- minimize repeated LLM calls;
- side effects routed through Gateway.

## Phase 8 — Mini Apps

Chỉ bắt đầu khi Phase 1–7 ổn định.

## Phase 9 — Blueprints

- export manifest/code;
- sanitize private state;
- instantiate isolated copy.

---

# 31. Priority

## P0 — bắt buộc

1. Workspace
2. Capability Gateway
3. Policy Engine
4. Action Center
5. Audit
6. OpenSandbox security boundary

## P1 — giá trị cao

7. Observation / Provenance
8. AI Gateway
9. n8n deterministic execution
10. Context Library
11. Skill Registry normalization

## P2 — sau khi core ổn

12. Mini Apps
13. Blueprints
14. Marketplace/library
15. collaborative Mini Apps

Không làm Mini App trước Gatekeeper.

---

# 32. Security Invariants

Claude Code **không được phá các invariant sau**.

## INV-01 Default deny

Agent không có ambient access đến external resource.

## INV-02 No credential in prompt

Credential không được đưa vào LLM context.

## INV-03 Side effects require policy evaluation

Không external write nào bypass Policy Engine.

## INV-04 Approval != execution

Approve và Execute là hai bước riêng.

## INV-05 Revalidate before execute

Capability được kiểm tra lại khi execute.

## INV-06 Idempotent side effects

Retry không được tạo tác động trùng lặp.

## INV-07 Sandbox is untrusted

Code trong sandbox luôn coi là untrusted.

## INV-08 Blueprint contains no private state

Export Blueprint phải sanitize.

## INV-09 Observation is append-only logically

Không cho agent tự sửa provenance sau khi đã tạo.

## INV-10 Critical financial/legal action cannot be silently automated

L5 không được auto-approve.

---

# 33. Testing Strategy

## 33.1. Unit tests

- policy decision;
- scope matching;
- expiry;
- grant/revoke;
- risk classification;
- idempotency;
- blueprint sanitization.

## 33.2. Integration tests

### Test: Email approval

1. agent proposes send;
2. connector simulate;
3. email chưa gửi;
4. user approves;
5. execute;
6. email gửi đúng 1 lần;
7. audit created.

### Test: capability denied

1. agent requests finance transfer;
2. policy denies;
3. connector never called.

### Test: sandbox secret isolation

1. sandbox script attempts env dump;
2. secret absent.

### Test: blueprint export

1. Mini App has production data;
2. export Blueprint;
3. instantiate;
4. new instance contains code;
5. no production data;
6. no credentials.

## 33.3. Agent regression

Dùng DSPy/evaluation dataset cho:

- tool selection;
- structured output;
- permission request correctness;
- no unsafe bypass;
- reasoning quality.

---

# 34. Observability Metrics

Theo dõi:

```text
agent_runs_total
agent_run_success_rate
tool_calls_total
capability_denials
approval_requests
approval_accept_rate
action_failure_rate
sandbox_execution_failures
model_latency
model_cost
tokens_per_workflow
llm_calls_per_workflow
deterministic_execution_ratio
```

Mục tiêu dài hạn:

```text
repeatable workflows:
LLM calls ↓
deterministic execution ↑
cost ↓
reliability ↑
```

---

# 35. Cost Optimization

Áp dụng nguyên tắc:

```text
simple rule -> code
query/filter -> SQL
repeat workflow -> n8n
semantic task -> small/cheap model
complex reasoning -> strong model
coding -> coding model
voice -> realtime path
```

Không dùng frontier model cho mọi request.

Cache ở các layer phù hợp:

- context retrieval;
- embeddings;
- static policy;
- tool schema;
- deterministic results.

Không cache side effect result theo cách gây nhầm trạng thái.

---

# 36. Failure Handling

Mỗi action failure phải có:

```text
error_category
retryable
retry_count
last_error
recovery_instruction
```

Agent không được retry vô hạn.

Ví dụ:

```yaml
email.send:
  max_retries: 2

finance.payment.transfer:
  max_retries: 0
```

---

# 37. Recommended Implementation Order for Claude Code

Claude Code triển khai theo thứ tự sau, mỗi bước phải có migration + test.

```text
01 workspace
02 workspace resources
03 capability registry
04 policy engine
05 connector abstraction
06 action model
07 simulation
08 approval API
09 executor
10 audit
11 observation
12 sandbox proxy
13 AI gateway
14 n8n adapter
15 frontend Action Center
16 Mini App runtime
17 Blueprint
```

Không tạo nhiều service quá sớm nếu chưa cần.

Có thể bắt đầu modular monolith trong FastAPI.

---

# 38. Suggested FastAPI Structure

```text
backend/
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   ├── security.py
    │   └── events.py
    │
    ├── workspace/
    │   ├── models.py
    │   ├── schemas.py
    │   ├── service.py
    │   └── router.py
    │
    ├── capabilities/
    │   ├── registry.py
    │   ├── policy.py
    │   ├── service.py
    │   └── router.py
    │
    ├── actions/
    │   ├── models.py
    │   ├── simulation.py
    │   ├── executor.py
    │   ├── service.py
    │   └── router.py
    │
    ├── observations/
    ├── audit/
    ├── connectors/
    ├── agents/
    ├── skills/
    ├── sandbox/
    ├── ai_gateway/
    ├── miniapps/
    └── blueprints/
```

---

# 39. Event Model

Dùng event nội bộ để giảm coupling.

```text
WorkspaceCreated
ResourceIntroduced
CapabilityGranted
CapabilityRevoked
ObservationRecorded
ActionProposed
ActionApproved
ActionRejected
ActionExecuted
ActionFailed
MiniAppCreated
BlueprintCreated
```

Ban đầu có thể dùng in-process event bus.

Không cần Kafka ở giai đoạn này.

---

# 40. Example End-to-End Flow — Sales

Founder:

> Kiểm tra những lead đang nguội và chuẩn bị follow-up.

Flow:

```text
Voice/Chat
   ↓
Sales Workspace
   ↓
Sales Agent
   ↓
skill: sales.follow_up
   ↓
Capability Gateway
   ↓
crm.lead.read
   ↓
Observation records
   ↓
deterministic stale-lead filter
   ↓
LLM drafts only relevant messages
   ↓
email.message.send
   ↓
Policy L4
   ↓
simulate
   ↓
Action Center
   ↓
Founder approve
   ↓
execute email
   ↓
crm.activity.update
   ↓
Audit
```

Nếu flow chạy mỗi ngày:

```text
n8n cron
 -> stale lead query
 -> rule
 -> AI draft
 -> Action Center
```

Không cần agent reasoning toàn bộ từ đầu.

---

# 41. Example End-to-End Flow — Finance

Founder:

> Cho tôi biết khoản nào cần thu trong tuần này.

Flow:

```text
Finance Agent
   ↓
finance.receivable.read
   ↓
PostgreSQL
   ↓
SQL deterministic calculation
   ↓
summary
```

Không cần approval vì read/analyze.

Founder:

> Gửi nhắc thanh toán cho các khoản quá hạn.

Flow:

```text
find overdue
 -> draft reminders
 -> simulate send
 -> batch Action Center
 -> Founder approves
 -> execute
```

Founder:

> Chuyển khoản thanh toán nhà cung cấp.

Flow:

```text
finance.payment.transfer
 -> L5
 -> manual/strong approval
 -> no silent agent execution
```

---

# 42. Example End-to-End Flow — Marketing

```text
Campaign Workspace
  ↓
Marketing Agent
  ↓
research/context
  ↓
draft posts
  ↓
marketing.post.publish
  ↓
L4 approval
  ↓
Action Center
  ↓
publish
```

Stable publishing schedule:

```text
n8n
  ↓
content queue
  ↓
approval status check
  ↓
publish
```

---

# 43. Mini App Use Case — Weekly Scoreboard

Founder:

> Tạo dashboard theo dõi tiến độ 12 Week Year của tôi.

AI:

1. đọc schema được phép;
2. tạo Mini App spec;
3. generate frontend/backend;
4. test trong OpenSandbox;
5. request capabilities;
6. deploy instance;
7. register agent API.

Manifest:

```yaml
name: Weekly Scoreboard
permissions:
  - okr.read
  - twelve_week_year.read
  - task.read

write_permissions:
  - weekly_review.update
```

Nếu `weekly_review.update` là L3, Policy Engine quyết định auto/approval theo field.

---

# 44. Blueprint Use Case

Sau khi Founder thích Weekly Scoreboard:

```text
Create Blueprint
```

System:

1. copy code;
2. remove personal state;
3. remove chat history;
4. remove resource IDs;
5. remove secrets;
6. preserve capability requirements;
7. assign Blueprint version.

Customer khác:

```text
Install Weekly Scoreboard Blueprint
  ↓
new app state
  ↓
select Project
  ↓
grant read capabilities
  ↓
ready
```

---

# 45. Claude Code Implementation Rules

Khi triển khai, Claude Code phải:

1. đọc codebase hiện tại trước khi tạo module;
2. tái sử dụng existing auth/user/company model;
3. không duplicate entity nếu đã tồn tại;
4. dùng migration có rollback hợp lý;
5. không hardcode model/provider;
6. không hardcode secret;
7. không bypass policy;
8. viết tests cho mỗi security invariant;
9. giữ backward compatibility cho flow hiện tại;
10. feature flag module chưa sẵn sàng.

---

# 46. Feature Flags

Đề xuất:

```text
FEATURE_WORKSPACES_V2
FEATURE_CAPABILITY_GATEWAY
FEATURE_ACTION_CENTER
FEATURE_PROVENANCE
FEATURE_SANDBOX_V2
FEATURE_AI_GATEWAY
FEATURE_MINI_APPS
FEATURE_BLUEPRINTS
```

Rollout:

```text
dev
 -> internal
 -> selected customer
 -> default
```

---

# 47. Definition of Done — Core Runtime

Core integration được coi là hoàn tất khi:

- [ ] Mọi AI session thuộc Workspace.
- [ ] Workspace có resource introduction.
- [ ] Agent mặc định không có external capability.
- [ ] Capability có scope.
- [ ] Policy Engine phân biệt read/write/side-effect/critical.
- [ ] L4 được queue vào Action Center.
- [ ] Simulation không gây side effect.
- [ ] Approval và execution tách biệt.
- [ ] Execution idempotent.
- [ ] Audit event được lưu.
- [ ] Important reads tạo Observation.
- [ ] OpenSandbox không có ambient secret.
- [ ] Model calls đi qua COSA AI Gateway abstraction.
- [ ] n8n workflow có thể gọi Gateway.
- [ ] Existing COSA workflows vẫn chạy.
- [ ] Strategy modules đã disable không bị tự bật lại.

---

# 48. Definition of Done — Mini App / Blueprint

- [ ] Mini App có manifest.
- [ ] Mini App instance có isolated state.
- [ ] Mini App không giữ raw credential.
- [ ] Agent có thể call app API qua schema.
- [ ] Mini App external action đi qua Capability Gateway.
- [ ] Blueprint export loại bỏ data/credential/history.
- [ ] Blueprint instantiate tạo state mới.
- [ ] Capability phải được grant lại trên instance mới.
- [ ] Blueprint versioning hoạt động.

---

# 49. Kiến trúc cuối cùng đề xuất

```text
                        COSA Founder OS
                              │
                ┌─────────────┴─────────────┐
                │                           │
              Chat                        Voice
                │                           │
                └─────────────┬─────────────┘
                              ▼
                       Founder Workspace
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
      Context               Memory               Files
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                       Agent Orchestrator
                              │
                    DeepSeek Harness
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
        Skills              DSPy             Tool Runtime
          │                                       │
          │                                 OpenSandbox
          │                                       │
          └───────────────────┬───────────────────┘
                              ▼
                     Capability Gateway
                              │
             ┌────────────────┼────────────────┐
             │                │                │
           READ             WRITE          CRITICAL
             │                │                │
          execute           policy        strong policy
                              │
                        Action Center
                              │
                         Founder Approval
                              │
                  ┌───────────┼────────────┐
                  │           │            │
             PostgreSQL      n8n       External APIs
                  │
        ┌─────────┼───────────────┐
        │         │               │
     Finance    Sales         Marketing/Legal
                  │
            Observation Graph
                  │
                Audit
```

---

# 50. Architectural Decision Records

## ADR-001 — Do not fork Cloudflare OS

**Decision:** Không fork.

**Reason:**

- COSA đã có domain/product architecture khác;
- Cloudflare OS phụ thuộc mạnh Workers runtime;
- COSA cần local/VPS deployment;
- reimplement pattern giảm lock-in.

## ADR-002 — PostgreSQL remains System of Record

**Decision:** Giữ PostgreSQL.

Không thay bằng Durable Objects/SQLite của Cloudflare OS.

Mini App có thể có isolated local state nhưng domain business data vẫn ở PostgreSQL.

## ADR-003 — Capability Gateway is mandatory trust boundary

Mọi Agent/Skill/Mini App/Sandbox external action phải qua Gateway.

## ADR-004 — Human approval is asynchronous where possible

Agent được phép simulate và tiếp tục reasoning; user xử lý queue sau.

## ADR-005 — AI is toolmaker for stable workflows

Workflow lặp lại chuyển dần sang deterministic execution/n8n.

## ADR-006 — Mini Apps are P2

Không ưu tiên Mini App trước security/runtime foundation.

---

# 51. Kết luận

Cloudflare OS không nên được xem như một dependency cần nhúng vào COSA.

Điều COSA nên tiếp thu là tư duy:

```text
AI application
≠
chatbot + tools
```

mà là:

```text
AI Operating System
=
Workspace
+ Context
+ Skills
+ Agent Runtime
+ Sandbox
+ Capability Security
+ Human Approval
+ Provenance
+ Deterministic Automation
+ Modifiable Apps
```

Với COSA, kiến trúc này được chuyên biệt hóa cho Founder / One Person Company:

```text
COSA
=
Founder Workspace
+ Department Agents
+ Business Context
+ Action Center
+ Finance/Sales/Marketing/Legal capabilities
+ OpenSandbox
+ n8n
+ Voice
+ AI Gateway
+ Mini Apps
```

Thành phần cần ưu tiên cao nhất không phải Mini App mà là:

```text
Workspace
     +
Capability Gateway
     +
Action Center
     +
Observation/Audit
```

Khi 4 foundation này ổn định, COSA mới nên mở khả năng cho AI tự tạo Mini App và Blueprint.

Đây là bước chuyển từ:

> **"Ứng dụng có nhiều AI Agent"**

sang:

> **"Founder AI Operating System có runtime, quyền, execution và governance riêng."**

---

# 52. Nguồn tham khảo chính

Các nguồn dưới đây được dùng để rút ra pattern kiến trúc, không phải dependency bắt buộc của COSA.

1. Cloudflare OS — official repository  
   https://github.com/cloudflare/cloudflare-os

2. Cloudflare OS Starter — official deployment/customization repository  
   https://github.com/cloudflare/cloudflare-os-starter

3. Cloudflare Blog — "Cloudflare OS: an open platform for agents, apps, and work" — 2026-08-05  
   https://blog.cloudflare.com/cloudflare-os/

4. Cloudflare Blog — "How we're rethinking work at Cloudflare with Cloudflare OS" — 2026-08-05  
   https://blog.cloudflare.com/how-we-use-ai-with-cloudflare-os/

5. Cloudflare OS deployment flow  
   https://os.cloudflare.app/

---

# 53. Prompt ngắn cho Claude Code

Sử dụng tài liệu này làm architectural specification.

```text
Read this document completely before making code changes.

Implement the Cloudflare-OS-inspired architecture natively in the existing COSA v13.1/v13.2 codebase.

DO NOT fork Cloudflare OS.
DO NOT replace FastAPI or PostgreSQL.
DO NOT re-enable disabled Strategy/PESTEL/SWOT/TOWS modules.
DO NOT introduce Cloudflare Workers/Durable Objects as mandatory dependencies.

Start with P0 only:
1. Workspace
2. Workspace Resources
3. Capability Registry
4. Policy Engine
5. Connector abstraction
6. AI Action Center
7. Audit
8. OpenSandbox trust boundary

Before modifying the code:
- inspect current models, services, routers, agent runtime, integrations, auth, database schema, and existing tests;
- map existing code to this architecture;
- reuse existing entities where possible;
- create an implementation plan;
- implement incrementally;
- add migrations and tests;
- preserve backward compatibility.

All external side effects initiated by agents must pass through Capability Gateway.
No credentials may be exposed to LLM prompts or sandbox code.
L4 actions require approval.
L5 financial/legal actions require strong approval/manual execution.
All side-effect execution must be idempotent.

After P0 is stable, continue with:
- Observation/Provenance
- AI Gateway
- n8n deterministic workflow integration
- Mini Apps
- Blueprints

Treat the Security Invariants and Definition of Done sections as mandatory acceptance criteria.
```

---

**END OF DOCUMENT**
