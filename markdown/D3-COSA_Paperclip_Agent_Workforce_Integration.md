# COSA — Tài liệu tích hợp Agent Workforce Control Plane
## Tham chiếu kiến trúc Paperclip, tối ưu cho COSA local-first, license theo từng công ty

**Trạng thái:** Đề xuất triển khai  
**Mục tiêu:** Chuẩn hóa lớp quản trị AI Agent của COSA theo mô hình “AI Workforce”, không biến COSA thành bản sao Paperclip và không đưa Startup Validation vào core flow.

---

# 1. Mục tiêu kiến trúc

COSA không nên vận hành như một tập hợp chatbot độc lập. COSA cần trở thành **Founder/Company Operating System** có khả năng quản trị một đội AI Agent có:

- danh tính và vai trò rõ ràng;
- cấp trên/cấp dưới;
- nhiệm vụ và quyền hạn;
- runtime có thể thay thế;
- skill có version;
- ngân sách và giới hạn chi phí;
- approval gate;
- audit log;
- workspace thực thi riêng;
- trust boundary;
- cơ chế event-driven;
- khả năng backup/export/reset;
- khả năng cài riêng cho từng công ty.

Paperclip được sử dụng như **reference architecture** cho lớp Agent Workforce Control Plane, không phải dependency bắt buộc.

---

# 2. Nguyên tắc bắt buộc

## 2.1 Không đưa Validation vào core flow

COSA **không chịu trách nhiệm thực hiện Startup Validation như một flow bắt buộc**.

Founder có thể:

- nghiên cứu thị trường bên ngoài;
- phỏng vấn khách hàng bên ngoài;
- dùng ChatGPT/Claude/Gemini độc lập;
- thuê chuyên gia;
- dùng tài liệu hoặc công cụ riêng;
- sau đó nhập kết luận vào Project/Objective nếu cần.

Không tạo các node bắt buộc như:

```text
Project
  ↓
Validation
  ↓
Approved
```

Flow chính của COSA là:

```text
Vision
  ↓
Mission
  ↓
Core Values
  ↓
Project
  ↓
Objective
  ↓
OKRs
  ↓
12 Week Year
  ↓
Weekly Tactics
  ↓
Tasks
  ↓
Agent/Human Execution
  ↓
Work Product
  ↓
Review
  ↓
Scoreboard
```

Founder vẫn có thể đính kèm:

- market research;
- customer interview;
- competitor report;
- feasibility report;
- tài liệu bên ngoài;

nhưng đây là **evidence/reference**, không phải gate của hệ thống.

---

# 3. Vai trò của Agent Workforce trong COSA

Agent Workforce là lớp nằm giữa Founder OS và các runtime AI.

```text
                    FOUNDER
                       │
                COSA FOUNDER OS
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
 Strategy          Execution          Review
     │                 │                 │
     └─────────────────┼─────────────────┘
                       │
            AGENT WORKFORCE CONTROL PLANE
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
 Agent Registry     Governance        Budget
 Skills             Permissions       Audit
 Runtime Adapter    Heartbeat         Workspace
 Routine            Approval          Trust
                       │
             RUNTIME ADAPTER LAYER
                       │
    ┌──────────┬───────┼─────────┬──────────┐
 Claude Code  Codex  Gemini   DeepSeek   OpenClaw
                       │
                      MCP
                       │
       GitHub / n8n / CRM / Email / Web / DB
```

---

# 4. Core flow mới của COSA

## 4.1 Strategic Flow

```text
Company
  ↓
Vision
  ↓
Mission
  ↓
3 Core Values
  ↓
Projects
  ↓
Objectives
  ↓
OKRs
```

## 4.2 Execution Flow

```text
OKR
  ↓
12 Week Year
  ↓
Week
  ↓
Weekly Tactics
  ↓
Tasks
  ↓
Assignee
     ├── Human
     └── Agent
  ↓
Execution
  ↓
Artifact / Result
  ↓
Review
```

## 4.3 Week 13

```text
Week 12 Complete
      ↓
Week 13
      ├── Celebrate
      ├── Retrospective
      ├── Score
      ├── Lessons
      ├── Carry Forward
      └── New Cycle Proposal
```

Agent Workforce chỉ tham gia khi cần phân tích, thực thi, tổng hợp, kiểm tra hoặc đề xuất.

---

# 5. Không để Chat tự động kích hoạt workflow

Một nguyên tắc quan trọng:

```text
User says "Chào"
```

KHÔNG được:

```text
→ tìm project
→ load company context
→ chạy project agent
→ phân tích OKR
```

Thay vào đó:

```text
Chat Router
   ↓
Intent Classification
   ↓
No operational intent?
   ↓
Normal conversational response
```

Chỉ gọi workflow khi intent rõ ràng:

```text
"Kiểm tra project COSA"
"Phân tích OKR hiện tại"
"Giao việc cho Marketing Agent"
"Chạy weekly review"
"Tạo task triển khai landing page"
```

## Quy tắc Router

```yaml
routing_policy:
  greetings:
    use_workflow: false

  casual_chat:
    use_workflow: false

  operational_request:
    use_workflow: true

  explicit_project_reference:
    use_project_context: true

  ambiguous:
    use_minimal_context: true
    run_side_effect: false
```

---

# 6. Các module mới cần có

## 6.1 Agent Registry

Quản lý tất cả AI Agent trong company.

Mỗi agent gồm:

- ID;
- tên;
- vai trò;
- department;
- purpose;
- manager;
- runtime adapter;
- model/runtime config;
- skills;
- permissions;
- budget;
- risk level;
- execution policy;
- status;
- health;
- audit history.

Ví dụ:

```yaml
agent:
  id: sales_manager
  name: AI Sales Manager
  department: sales
  reports_to: founder

  purpose:
    - manage_pipeline
    - analyze_sales
    - recommend_followups

  runtime:
    adapter: deepseek
    profile: chat_reasoning

  skills:
    - crm-analysis
    - lead-qualification
    - sales-follow-up

  permissions:
    - crm.read
    - crm.write
    - sales.read
    - sales.recommend

  restricted:
    - email.send
    - zalo.send
    - finance.write
    - system.prompt.write

  risk_level: medium

  budget:
    monthly_limit_usd: 10

  execution:
    trigger_mode: event_driven
    max_concurrent_runs: 1
```

---

# 7. Agent Runtime Adapter Layer

Không gắn Agent trực tiếp với model/provider.

Thiết kế interface:

```python
from abc import ABC, abstractmethod

class AgentRuntimeAdapter(ABC):

    @abstractmethod
    async def check_capability(self) -> dict:
        pass

    @abstractmethod
    async def execute(self, run_context) -> dict:
        pass

    @abstractmethod
    async def cancel(self, run_id: str) -> bool:
        pass

    @abstractmethod
    async def health(self) -> dict:
        pass
```

Các adapter ban đầu:

```text
ClaudeCodeAdapter
CodexAdapter
GeminiCLIAdapter
DeepSeekAdapter
OpenClawAdapter
HTTPAgentAdapter
LocalProcessAdapter
```

Không cần triển khai tất cả ngay.

## Phase đầu

Ưu tiên:

```text
1. ClaudeCodeAdapter
2. DeepSeekAdapter
3. HTTPAgentAdapter
```

Sau đó mở rộng.

---

# 8. Runtime Capability Detection

Đặc biệt với CLI local, không được giả định runtime luôn hoạt động.

Ví dụ:

```python
{
  "runtime": "claude_code",
  "installed": True,
  "authenticated": True,
  "headless_supported": True,
  "mcp_available": True,
  "workspace_access": True
}
```

Nếu runtime không khả dụng:

```text
PRIMARY
  ↓ fail
FALLBACK
  ↓
secondary runtime
```

Ví dụ:

```yaml
runtime_policy:
  primary: claude_code
  fallback:
    - codex
    - http_api
```

---

# 9. Skill Registry

Chuyển từ prompt lớn sang skill nhỏ, có routing.

Cấu trúc:

```text
/cosa
  /skills
    /sales
      /lead-qualification
        SKILL.md
      /sales-follow-up
        SKILL.md

    /marketing
      /campaign-planning
        SKILL.md

    /finance
      /circular-58
        SKILL.md

    /legal
      /legal-check
        SKILL.md

    /engineering
      /code-review
        SKILL.md
```

Ví dụ:

```yaml
---
id: lead-qualification
name: Lead Qualification
department: sales
version: 1.0.0
risk: low
description: >
  Dùng khi cần đánh giá lead, nhu cầu, khả năng mua,
  urgency và bước follow-up tiếp theo.
---
```

## Skill phải có

```text
Metadata
Purpose
When to use
When NOT to use
Inputs
Outputs
Process
Constraints
Examples
Failure modes
Escalation rules
```

---

# 10. Prompt / Skill / Policy / Spec phải tách riêng

Không gom toàn bộ vào system prompt.

```text
/prompts
  router.md
  founder_assistant.md

/skills
  ...

/policies
  approval.yaml
  permission.yaml
  trust.yaml
  budget.yaml

/specs
  company_spec.md
  founder_os.md
  finance_spec.md
  sales_spec.md
```

Ý nghĩa:

- **Prompt**: cách agent giao tiếp/suy luận.
- **Skill**: cách thực hiện một nghiệp vụ.
- **Policy**: điều gì agent được/không được làm.
- **Spec**: hệ thống phải hoạt động như thế nào.

---

# 11. Quyền chỉnh sửa

COSA cài riêng cho từng company.

Ban đầu:

```text
Founder = Admin
```

Các nội dung quan trọng:

```text
System Prompt
Agent Prompt
Skill Core
Policy
Build Spec
Company Spec
Runtime Policy
Security Policy
```

chỉ Admin được sửa.

Agent không được tự sửa.

## Permission

```text
prompt.read
prompt.write

skill.read
skill.write
skill.reset

spec.read
spec.write
spec.reset

policy.read
policy.write

runtime.read
runtime.write
```

Mặc định:

```text
Founder/Admin → full access
Employee → limited
Agent → read what required
```

---

# 12. Reset Default

Mọi Prompt/Skill/Policy/Spec hệ thống phải có:

```text
Default
Customized
Reset to Default
Diff
Version
Last Modified
Modified By
```

Database cần lưu:

```text
source = default | custom
default_version
current_version
content_hash
```

Admin có thể:

```text
View Diff
Reset File
Reset Module
Reset All Defaults
```

Không reset:

```text
company data
project data
finance data
CRM
user data
API keys
```

---

# 13. Human Authority Gate

COSA phải có risk-based approval.

## Risk Level

### LOW

Agent tự thực hiện.

Ví dụ:

```text
research
summarize
read CRM
draft content
analyze data
```

### MEDIUM

Agent thực hiện nhưng phải log/notify.

```text
create internal task
update non-critical CRM fields
generate campaign proposal
```

### HIGH

Phải Founder/Admin approve.

```text
send email
send Zalo
publish social
deploy production
create invoice
modify accounting data
spend ad budget
```

### CRITICAL

Founder only.

```text
API key
payment
banking
delete financial records
modify policy
modify system prompt
modify build spec
change license
change permissions
```

---

# 14. Approval Engine

Data model:

```text
ApprovalRequest

id
company_id
requested_by
action_type
resource_type
resource_id
risk_level
reason
payload
status

pending
approved
rejected
revision_requested
expired

approved_by
approved_at
```

Flow:

```text
Agent proposes action
       ↓
Policy Engine
       ↓
Risk Evaluation
       ↓
Low?
 ├── yes → execute
 └── no
       ↓
Create Approval
       ↓
Founder
   ├── Approve
   ├── Reject
   └── Request Revision
```

---

# 15. Budget Engine

Budget cần quản lý:

```text
Company
Department
Agent
Project
Runtime
Tool
Campaign
```

Ví dụ:

```yaml
budget:
  company_monthly_ai_usd: 100

  departments:
    sales: 20
    marketing: 20
    engineering: 30
    finance: 10

  thresholds:
    warning: 0.80
    hard_stop: 1.00
```

## Chính sách

```text
80% → warning
90% → urgent warning
100% → stop execution
```

Trừ khi:

```text
Founder Override
```

---

# 16. Cost Ledger

Mỗi Agent Run phải ghi:

```text
runtime
model
input_tokens
output_tokens
estimated_cost
actual_cost
tool_cost
duration
company_id
project_id
agent_id
task_id
```

Phục vụ:

```text
AI Cost Dashboard
Agent ROI
Cost per Project
Cost per Task
Cost per Department
```

---

# 17. Heartbeat Engine

Không polling mặc định.

Ưu tiên:

```text
EVENT-DRIVEN FIRST
SCHEDULE SECOND
POLLING LAST
```

Trigger:

```text
task.assigned
task.updated
comment.created
approval.approved
routine.fired
webhook.received
manual.run
```

## Agent Run

```text
Event
  ↓
Wake Request
  ↓
Queue
  ↓
Policy Check
  ↓
Budget Check
  ↓
Permission Check
  ↓
Run Agent
  ↓
Persist Result
```

---

# 18. Routine Engine

Routine khác Heartbeat.

```text
Routine = công việc định kỳ
Heartbeat = cách đánh thức agent
```

Ví dụ:

```yaml
routine:
  id: weekly_sales_review
  schedule: "0 17 * * 5"
  timezone: Asia/Ho_Chi_Minh

  action:
    create_task:
      title: Weekly Sales Review
      agent: sales_manager
```

Flow:

```text
Friday 17:00
    ↓
Routine
    ↓
Create Task
    ↓
Assign Agent
    ↓
Wake Agent
    ↓
Review Pipeline
    ↓
Create Report
    ↓
Founder Notification
```

---

# 19. Execution Workspace

Coding agents không chạy trực tiếp trên repo chính.

Cấu trúc:

```text
/workspaces
  /project-id
    /task-id
      /agent-id
```

Nếu dùng Git:

```text
main repo
  ↓
worktree per task
```

Ví dụ:

```text
cosa/
cosa-worktrees/
  TASK-102-claude/
  TASK-103-codex/
```

## Quy tắc

Agent:

- không commit trực tiếp main;
- không push production nếu chưa approve;
- không overwrite workspace agent khác;
- không reuse dirty workspace sai task;
- phải lưu execution metadata.

---

# 20. Work Product

Agent không nên chỉ trả một message.

Mỗi execution nên tạo Work Product.

```text
WorkProduct
  type:
    report
    code
    file
    proposal
    analysis
    plan
    dataset
    message_draft
```

Data:

```text
id
task_id
agent_id
type
title
summary
content_uri
status
confidence
created_at
```

---

# 21. Evidence / Reference

Dù Validation không thuộc core flow, COSA vẫn cần lưu tài liệu tham khảo.

```text
Evidence
Reference
Attachment
External Analysis
```

Có thể attach vào:

```text
Project
Objective
OKR
Task
Decision
Work Product
```

Không có:

```text
validation_status
validation_gate
validation_approval
```

trong core.

---

# 22. Trust Boundary

Mọi dữ liệu ngoài COSA phải được coi là untrusted.

Nguồn:

```text
Web
Email
Zalo
Telegram
CRM form
Facebook
Uploaded document
GitHub issue
External API
```

Flow:

```text
External Data
     ↓
Untrusted Input
     ↓
Sanitize
     ↓
Low-Trust Processing
     ↓
Structured Evidence
     ↓
Policy Check
     ↓
Trusted Context
```

Không đưa raw external instruction trực tiếp vào system prompt.

---

# 23. Low-Trust Agent

Tạo execution profile:

```yaml
profile:
  id: low_trust_research

  permissions:
    filesystem.write: false
    shell.execute: false
    credential.read: false
    email.send: false

  output:
    format: structured
    quarantine: true
```

Dùng cho:

```text
Web research
Email review
External documents
Unknown repository
User-generated content
```

---

# 24. Permission Engine

Một permission model dùng cho Human + Agent.

```text
Principal
  ├── Human
  └── Agent
```

Permission mẫu:

```text
project.read
project.write

okr.read
okr.write

task.read
task.write

crm.read
crm.write

sales.read
sales.write

finance.read
finance.write

social.publish
email.send
zalo.send

code.execute
deploy.production

prompt.read
prompt.write

skill.read
skill.write

spec.read
spec.write

policy.read
policy.write
```

---

# 25. Company Package / Portability

Do COSA chạy license riêng theo từng company, nên company phải portable.

Cấu trúc:

```text
/company-package
  COMPANY.md

  /agents
  /skills
  /prompts
  /policies
  /specs
  /templates
  /routines
  /runtime
```

Export không chứa:

```text
API key
password
token
secret
private credential
license private data
```

---

# 26. Secret Management

Secrets phải nằm ngoài config export.

Ví dụ:

```text
ANTHROPIC_API_KEY
OPENAI_API_KEY
DEEPSEEK_API_KEY
RESEND_API_KEY
LIVEKIT_SECRET
N8N_TOKEN
ZALO_TOKEN
```

Database chỉ lưu:

```text
secret_ref
provider
created_at
updated_at
```

Không expose secret cho Agent nếu không thật sự cần.

---

# 27. Company Isolation

Mỗi customer/company quản lý riêng:

```text
PostgreSQL
API keys
Agent configs
Skills
Prompts
Documents
CRM
Finance
Automation
n8n
```

COSA license server chỉ quản lý tối thiểu:

```text
license_id
device_id
activation
expiry
entitlement
product_version
```

Không quản lý business data của khách trừ khi khách bật cloud service riêng.

---

# 28. Suggested Database Schema

## companies

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## agents

```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    department TEXT,
    reports_to UUID,
    purpose JSONB,
    runtime_adapter TEXT,
    runtime_config JSONB,
    risk_level TEXT DEFAULT 'low',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## agent_skills

```sql
CREATE TABLE agent_skills (
    id UUID PRIMARY KEY,
    agent_id UUID NOT NULL,
    skill_id UUID NOT NULL,
    enabled BOOLEAN DEFAULT TRUE
);
```

## skills

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY,
    company_id UUID,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

## tasks

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    project_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    assigned_human_id UUID,
    assigned_agent_id UUID,
    risk_level TEXT DEFAULT 'low',
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## agent_runs

```sql
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    task_id UUID,
    runtime TEXT,
    model TEXT,
    status TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    estimated_cost NUMERIC DEFAULT 0,
    actual_cost NUMERIC DEFAULT 0,
    metadata JSONB
);
```

## approvals

```sql
CREATE TABLE approvals (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    requester_type TEXT NOT NULL,
    requester_id UUID,
    action_type TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    payload JSONB,
    status TEXT DEFAULT 'pending',
    approved_by UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    decided_at TIMESTAMPTZ
);
```

## routines

```sql
CREATE TABLE routines (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    code TEXT NOT NULL,
    cron TEXT,
    timezone TEXT DEFAULT 'Asia/Ho_Chi_Minh',
    enabled BOOLEAN DEFAULT TRUE,
    action JSONB NOT NULL
);
```

## audit_logs

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id UUID,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

# 29. FastAPI module structure

```text
backend/
  app/
    agents/
      router.py
      service.py
      models.py
      schemas.py

    runtimes/
      base.py
      claude_code.py
      deepseek.py
      http_agent.py

    skills/
    policies/
    permissions/
    approvals/
    budgets/
    routines/
    heartbeat/
    workspaces/
    work_products/
    audit/
    secrets/
```

---

# 30. API đề xuất

## Agent

```text
GET    /api/agents
POST   /api/agents
GET    /api/agents/{id}
PATCH  /api/agents/{id}
POST   /api/agents/{id}/run
POST   /api/agents/{id}/pause
POST   /api/agents/{id}/resume
```

## Skills

```text
GET    /api/skills
POST   /api/skills
PATCH  /api/skills/{id}
POST   /api/skills/{id}/reset
```

## Approval

```text
GET    /api/approvals
POST   /api/approvals/{id}/approve
POST   /api/approvals/{id}/reject
POST   /api/approvals/{id}/request-revision
```

## Runtime

```text
GET    /api/runtimes
GET    /api/runtimes/{adapter}/capabilities
POST   /api/runtimes/{adapter}/test
```

## Routine

```text
GET    /api/routines
POST   /api/routines
PATCH  /api/routines/{id}
POST   /api/routines/{id}/run
```

---

# 31. Event Bus

Không gọi agent trực tiếp từ UI.

Dùng event:

```text
task.created
task.assigned
task.updated

approval.approved

routine.triggered

agent.run.requested

agent.run.started
agent.run.completed
agent.run.failed

work_product.created
```

Ví dụ:

```python
await event_bus.publish(
    "task.assigned",
    {
        "company_id": company_id,
        "task_id": task.id,
        "agent_id": agent.id,
    }
)
```

Heartbeat listener xử lý event.

---

# 32. Agent Execution Pipeline

```text
RUN REQUEST
    ↓
Load Agent
    ↓
Load Task
    ↓
Load Required Company Context
    ↓
Load Relevant Skills
    ↓
Permission Check
    ↓
Risk Policy
    ↓
Budget Check
    ↓
Trust Check
    ↓
Runtime Capability Check
    ↓
Create Workspace
    ↓
Execute
    ↓
Collect Result
    ↓
Create Work Product
    ↓
Update Task
    ↓
Audit
    ↓
Notify Founder
```

---

# 33. Context Loader

Không đưa toàn bộ Company DB vào prompt.

Context theo principle:

```text
Minimum Required Context
```

Ví dụ Sales Agent:

```text
Company Summary
Relevant Project
Relevant OKR
Assigned Task
CRM record
Sales skills
Applicable policy
```

Không load:

```text
Finance detail
Legal private data
System spec
Other projects
Other agent memories
```

nếu không liên quan.

---

# 34. Org Chart

COSA nên có Org Chart nhưng không cần tạo hàng chục agent mặc định.

Core:

```text
Founder
  │
  ├── AI Executive Assistant
  ├── Finance Agent
  ├── Sales Agent
  └── Marketing Agent
```

Optional packs:

```text
Engineering
Legal
Product
Research
Customer Success
Operations
```

---

# 35. Department Packs

Cấu trúc:

```text
/packs
  /sales
    agents/
    skills/
    routines/
    templates/

  /marketing
  /finance-vn
  /engineering
  /legal-vn
```

Admin:

```text
Install Pack
Enable Pack
Disable Pack
Reset Pack
Upgrade Pack
```

Không uninstall làm mất dữ liệu business.

---

# 36. Hologram Hub

Hologram Hub nên trở thành nơi hiển thị Workforce.

Card:

```text
AI Sales Manager
Status: Working
Task: Review pipeline
Budget: $4.20 / $10
Health: Good
Last run: 5 min ago
```

Có thể visualize:

```text
Founder
 │
 ├── Sales
 ├── Marketing
 ├── Finance
 └── Engineering
```

Click agent:

```text
Role
Skills
Current Task
Recent Runs
Budget
Permissions
Logs
Work Products
```

---

# 37. Founder Dashboard

Dashboard ưu tiên “Company Pulse”, không phải chat.

```text
Company Pulse

OKR Progress
12WY Score
Revenue
Pipeline
Cash
Open Risks

AI Workforce

Needs Attention
  3 Approvals
  2 Blocked Tasks
  1 Budget Warning

Today's Top 3
```

Chat/Voice là command interface bên cạnh.

---

# 38. Chat / Voice

Chat và LiveKit Voice không thay Agent Workforce.

Flow:

```text
Chat/Voice
    ↓
Intent Router
    ↓
Command Parser
    ↓
Read-only request?
    ├── answer
    └── operational command
           ↓
        Policy
           ↓
        Task/Event
           ↓
        Agent Workforce
```

Ví dụ:

```text
Founder:
"Kiểm tra pipeline tuần này"

Router:
sales.analytics

→ create read-only analysis run
→ Sales Agent
→ response
```

---

# 39. Audit Log

Mọi action quan trọng phải audit.

```text
WHO
DID WHAT
TO WHAT
WHEN
WHY
WITH WHICH RUNTIME
AT WHAT COST
RESULT
```

Actor:

```text
human
agent
system
routine
webhook
```

---

# 40. Failure Handling

Agent run phải có:

```text
queued
running
completed
failed
cancelled
blocked
waiting_approval
budget_blocked
permission_denied
```

Retry policy:

```yaml
retry:
  max_attempts: 2
  retry_on:
    - timeout
    - provider_unavailable

  never_retry:
    - permission_denied
    - approval_required
    - budget_exceeded
```

---

# 41. Agent Loop Protection

Ngăn agent tự tạo loop:

```text
max depth
max child tasks
max runtime
max token/cost
max tool calls
```

Ví dụ:

```yaml
limits:
  max_run_minutes: 30
  max_tool_calls: 50
  max_child_tasks: 5
  max_delegate_depth: 2
```

---

# 42. Delegation

Không cho agent tự thuê/tạo agent mới.

Agent có thể:

```text
Recommend Delegation
```

Nếu agent cần agent khác:

```text
Agent A
  ↓
Delegation Request
  ↓
Policy
  ↓
Existing Agent?
   ├── Yes → assign if allowed
   └── No → Founder approval
```

---

# 43. Decision Record

Các quyết định quan trọng cần lưu riêng.

```text
Decision

Context
Options
Recommendation
Founder Decision
Reason
Date
Related Project
Related OKR
Related Work Products
```

Agent chỉ recommend.

Founder là người quyết định nếu risk cao.

---

# 44. Không tự động mở rộng scope

Agent phải ưu tiên task được giao.

Không:

```text
"Trong khi làm task A, tôi thấy nên build luôn B, C, D..."
```

Nếu phát hiện việc mới:

```text
Create Recommendation
```

Founder chọn:

```text
Accept → Task
Reject
Backlog
```

---

# 45. MVP nên triển khai

Không build toàn bộ ngay.

## Phase A — Core Control Plane

```text
Agent Registry
Runtime Adapter Base
Task Assignment
Agent Run
Audit Log
```

## Phase B — Governance

```text
Permission
Risk Policy
Approval
Budget
```

## Phase C — Skills

```text
Skill Registry
Skill Loader
Version
Reset Default
```

## Phase D — Automation

```text
Event Bus
Heartbeat
Routine
```

## Phase E — Secure Execution

```text
Workspace
Low Trust
Sandbox
Secrets
```

## Phase F — UX

```text
Hologram Workforce
Agent Cards
Approval Inbox
Cost Dashboard
Run History
```

---

# 46. Thứ tự ưu tiên triển khai

```text
P0
Agent Registry
Runtime Adapter
Task → Agent
Agent Run
Audit

P1
Permissions
Approval
Budget
Skills

P2
Event Bus
Heartbeat
Routine
Workspace

P3
Low Trust
Portable Company
Department Packs
Performance analytics
```

---

# 47. Không làm ở Phase đầu

Không cần ngay:

```text
multi-company SaaS orchestration
agent marketplace
public agent sharing
hundreds of predefined agents
complex autonomous hierarchy
agent self-hiring
cross-company agent network
```

COSA là license per company.

Tối ưu cho:

```text
1 Founder
1 Company
3–6 Core Agents
local/private deployment
```

---

# 48. Prompt cho Claude Code — Phase A

```text
Bạn đang triển khai COSA Agent Workforce Control Plane.

Stack hiện tại:
- Backend: Python FastAPI
- Database: PostgreSQL
- Frontend: Flutter + GetX
- Deployment: local-first / private company installation
- License per company

Mục tiêu Phase A:
1. Agent Registry
2. Runtime Adapter interface
3. Task assignment cho Human hoặc Agent
4. Agent Run lifecycle
5. Audit log

Yêu cầu kiến trúc:

Agent KHÔNG gắn trực tiếp với provider/model.
Phải tạo AgentRuntimeAdapter abstract interface.

Tạo trước:
- ClaudeCodeAdapter stub
- DeepSeekAdapter stub
- HTTPAgentAdapter stub

Mỗi adapter phải có:
- check_capability()
- execute()
- cancel()
- health()

Tạo database:
- agents
- tasks
- agent_runs
- audit_logs

Không triển khai:
- startup validation
- agent self-hiring
- autonomous recursive delegation
- marketplace

Cần bảo đảm mọi query đều scoped theo company_id.

Agent run status:
queued
running
completed
failed
cancelled
blocked

Tạo API:
GET /api/agents
POST /api/agents
GET /api/agents/{id}
PATCH /api/agents/{id}
POST /api/agents/{id}/run
GET /api/agent-runs
GET /api/agent-runs/{id}

Viết test cho:
- company isolation
- invalid runtime
- task assignment
- run status
- audit creation

Không thay đổi các module ngoài scope nếu không cần.
```

---

# 49. Prompt cho Claude Code — Phase B

```text
Tiếp tục COSA Agent Workforce.

Triển khai Governance Layer:

1. Permission Engine
2. Risk Policy
3. Approval Engine
4. Budget Engine
5. Cost Ledger

Risk:
LOW → auto
MEDIUM → execute + notify
HIGH → approval
CRITICAL → founder only

CRITICAL bao gồm:
- system prompt write
- spec write
- policy write
- API key
- payment
- license
- permission changes

Agent không được tự sửa prompt/spec/policy.

Budget:
- company
- department
- agent
- project

Threshold:
80% warning
90% urgent
100% block

Mọi approval/budget event phải audit.

Viết migration + tests.
```

---

# 50. Prompt cho Claude Code — Phase C

```text
Triển khai Skill Registry cho COSA.

Skill lưu dưới dạng SKILL.md.

Metadata:
id
name
department
version
description
risk

DB phải hỗ trợ:
default content
custom content
source
version
content_hash

Admin có thể:
edit
diff
reset to default

Agent chỉ read.

Skill loader chỉ nạp skill liên quan task.
Không inject toàn bộ skill library vào context.

Tạo API + test.
```

---

# 51. Prompt cho Claude Code — Phase D

```text
Triển khai Event-Driven Agent Execution.

Nguyên tắc:
EVENT FIRST
SCHEDULE SECOND
POLLING LAST

Events:
task.assigned
approval.approved
routine.triggered
agent.run.requested

Tạo:
EventBus abstraction
Heartbeat service
Routine service

Routine tạo task rồi assign agent.

Không cho timer đánh thức tất cả agent theo chu kỳ.

Support cron theo timezone Asia/Ho_Chi_Minh.
```

---

# 52. Prompt cho Claude Code — Phase E

```text
Triển khai Secure Agent Execution.

Bao gồm:
- per-task workspace
- Git worktree support cho coding agent
- low-trust execution profile
- secret reference
- runtime capability detection
- loop protection

External data được đánh dấu untrusted.

Low trust agent:
- no shell
- no credential
- no write filesystem
- structured output
- quarantine result

Coding agent:
- không commit main
- không deploy production nếu chưa approval
```

---

# 53. Acceptance Criteria

Chỉ xem module hoàn thành khi:

### Agent

- tạo/sửa/pause agent được;
- agent có runtime độc lập;
- runtime capability được kiểm tra.

### Execution

- task assign agent;
- run lifecycle đúng;
- failure được persist;
- không block UI.

### Security

- company isolation;
- permission enforced server-side;
- secret không xuất hiện trong logs;
- approval không bypass.

### Cost

- ghi cost;
- warning;
- hard stop.

### Skills

- load đúng skill;
- version;
- reset default;
- agent không edit.

### Automation

- event wake agent;
- routine create task;
- không polling vô ích.

### Audit

- mọi action quan trọng có trace.

---

# 54. Definition of Done

COSA được xem là có Agent Workforce Control Plane nền tảng khi founder có thể:

1. mở Hologram Hub;
2. thấy các AI Agent đang tồn tại;
3. xem agent nào đang làm gì;
4. giao một task;
5. hệ thống chọn runtime;
6. kiểm tra quyền;
7. kiểm tra budget;
8. chạy agent;
9. nhận Work Product;
10. xem chi phí;
11. approve action rủi ro;
12. xem lịch sử/audit;
13. reset skill/prompt/spec về default;
14. export cấu hình company mà không lộ secret.

---

# 55. Kiến trúc COSA sau tích hợp

```text
COSA
│
├── Founder OS
│   ├── Strategic Identity (Tầng Định hướng Cốt lõi)
│   │   ├── Vision
│   │   ├── Mission
│   │   └── Core Values
│   └── Project-Driven Execution (Tầng Thực thi Dự án Linh hoạt)
│       ├── Projects (Thời gian N tuần linh hoạt: 2W, 4W, 6W, 12W...)
│       ├── Objectives & OKRs (Gắn liền theo Project)
│       ├── Weekly Tactics (Phân bổ chiến thuật theo Tuần 1 -> Tuần N)
│       ├── Tasks (Giao việc cho Human hoặc AI Agent)
│       ├── Scoreboard (Chấm điểm kỷ luật thực thi hàng tuần)
│       └── Retrospective (Mốc tổng kết & bài học kinh nghiệm cuối Project)
│
├── Business
│   ├── Sales & CRM
│   ├── Marketing
│   ├── Finance (Kế toán & Thuế chuẩn VN)
│   ├── Legal (Hợp đồng & Pháp chế VN)
│   └── Learning (Knowledge Base, SOPs)
│
├── Agent Workforce (Control Plane)
│   ├── Prompts (Persona & Style giao tiếp tinh gọn)
│   ├── Skills Registry (File SKILL.md vật lý, nạp On-Demand theo Task)
│   ├── Policies (4 cấp Risk: Low/Med/High/Critical, Budget & Trust YAML)
│   ├── Specs (Company Spec, Work Product Schemas)
│   ├── Agent Registry & Org Chart
│   ├── Runtime Adapters (Claude, Gemini, DeepSeek, Ollama, HTTP)
│   ├── Governance & Approval Gate
│   ├── Budget & Cost Ledger (USD, VND, Token)
│   ├── Event-Driven Automation (Heartbeat, EventBus, Routines)
│   ├── Workspace & Trust Boundary (Dynamic Sandbox & Git Worktrees)
│   └── Work Products & ADRs (Bàn giao có cấu trúc: Docs, Diffs, Decisions)
│
├── Integration
│   ├── MCP
│   ├── n8n
│   ├── GitHub
│   ├── Channels (Email, Zalo, Telegram)
│   └── LiveKit (Voice/Video Realtime)
│
└── Platform
    ├── FastAPI
    ├── PostgreSQL
    ├── Flutter/GetX
    ├── Local-first
    ├── License Manager (License per company)
    └── Company Package & Vault (Secret Broker)
```

---

# 56. Kết luận

Paperclip không nên được nhúng nguyên vào COSA.

COSA nên học Paperclip ở các lớp:

```text
Agent Identity
Org Structure
Runtime Adapter
Skills
Heartbeat
Routine
Approval
Budget
Workspace
Trust
Audit
Portability
```

Nhưng COSA tiếp tục giữ lợi thế riêng:

```text
Founder OS
OKRs
12 Week Year
Week 13
Sales
CRM
Marketing
Finance Việt Nam
Legal Việt Nam
Learning
LiveKit
local-first
license per company
```

Và đặc biệt:

```text
KHÔNG có Startup Validation trong core flow.
```

Founder tự phân tích validation bên ngoài. COSA chỉ nhận các tài liệu/kết quả đó như Evidence hoặc Reference nếu founder muốn liên kết vào Project, Objective, OKR hoặc Decision.

Kiến trúc cuối cùng cần hướng tới:

> **COSA = Founder Operating System + AI Workforce Control Plane.**

Founder vẫn là người ra quyết định cuối cùng. Agent là lực lượng phân tích và thực thi có quyền, ngân sách, kỹ năng và phạm vi được kiểm soát.
