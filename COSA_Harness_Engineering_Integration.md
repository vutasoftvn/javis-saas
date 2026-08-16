# COSA Harness Engineering Integration

**Tài liệu triển khai kiến trúc Harness Engineering cho COSA**  
**Mục tiêu:** chuyển COSA từ một hệ thống “AI agent + prompt + tools” sang **Founder OS có Harness Control Plane**, nơi model chỉ là một thành phần bên trong hệ thống điều phối có trạng thái, quyền hạn, kiểm chứng và khả năng phục hồi.

---

## 1. Mục tiêu tài liệu

Tài liệu này định nghĩa cách tích hợp các nguyên tắc từ **Harness Engineering** vào COSA mà không biến COSA thành một framework multi-agent quá phức tạp.

Mục tiêu chính:

1. Chặn việc agent gọi tool sai ngữ cảnh.
2. Tách logic điều phối khỏi prompt của model.
3. Quản lý prompt/spec/policy tập trung và chỉ admin được chỉnh sửa.
4. Chuẩn hóa vòng đời task: yêu cầu → kế hoạch → thực thi → kiểm chứng → hoàn thành.
5. Cho phép task tiếp tục sau khi app restart, đổi model hoặc đổi thiết bị.
6. Tách context theo task để giảm token và giảm nhiễu.
7. Chuẩn hóa skill/tool/MCP/CLI theo policy.
8. Bắt buộc sandbox cho tác vụ có khả năng thay đổi hệ thống.
9. Bổ sung verification trước khi một agent được phép báo “Done”.
10. Visualize trạng thái agent và task trên Hologram Hub.
11. Cho phép self-improvement theo mô hình **proposal → admin approval**, tuyệt đối không tự sửa core spec/prompt/policy.
12. Giữ kiến trúc đủ đơn giản cho giai đoạn Founder / One Person Company.

---

# 2. Nguyên tắc thiết kế

## 2.1. Model không phải là hệ thống điều phối

Không thiết kế:

```text
User
  ↓
Prompt
  ↓
LLM
  ↓
Tool
  ↓
Response
```

Thiết kế mới:

```text
User
  ↓
Intent Router
  ↓
Policy + State
  ↓
Context Builder
  ↓
Agent Runtime
  ↓
Tool Gateway
  ↓
Sandbox / External Tool
  ↓
Verifier
  ↓
Memory / State Update
  ↓
Response
```

LLM chịu trách nhiệm suy luận và tạo nội dung.

Harness chịu trách nhiệm:

- agent nào được gọi;
- model nào được dùng;
- context nào được nạp;
- skill nào được phép load;
- tool nào được phép gọi;
- có cần approval không;
- có cần sandbox không;
- kết quả có đạt verification không;
- state nào được ghi lại;
- memory nào được lưu;
- task có được chuyển trạng thái hay không.

---

## 2.2. Quyền phải nằm trong code, không nằm trong prompt

Không dùng prompt kiểu:

> “Không được xóa file quan trọng.”

Thay vào đó, tool request phải qua Policy Engine trước khi thực thi.

Policy trả về một trong bốn trạng thái:

```text
ALLOW
ALLOW_SANDBOX
REQUIRE_APPROVAL
DENY
```

Ví dụ:

| Action | Policy |
|---|---|
| Đọc project | ALLOW |
| Đọc OKRs | ALLOW |
| Phân tích tài chính | ALLOW |
| Chạy test code | ALLOW_SANDBOX |
| Sửa source code | ALLOW_SANDBOX |
| Deploy production | REQUIRE_APPROVAL |
| Gửi email bên ngoài | REQUIRE_APPROVAL |
| Xóa database | DENY |
| Sửa core system prompt | DENY |
| Sửa permission policy | DENY |
| Reset core spec | ADMIN_ONLY |

---

## 2.3. State dài hạn không nằm trong chat history

Chat history chỉ phục vụ hội thoại.

Task state phải tồn tại độc lập.

```text
Conversation
    │
    ├── Message history
    │
    └── Task reference
             │
             ▼
        Task State
             │
      ┌──────┼────────┐
      │      │        │
    Plan  Execution Evidence
```

Task phải tiếp tục được sau:

- restart desktop;
- restart backend;
- mất mạng;
- đổi model;
- đổi Claude Code → Codex;
- desktop → mobile;
- user đóng cửa sổ chat.

---

# 3. Vấn đề routing hiện tại cần sửa

Một lỗi cần xử lý ngay:

```text
User: "Chào"
```

COSA không được tự động:

```text
→ kiểm tra project
→ gọi hàm project lookup
→ trả thông tin project
```

Routing đúng:

```yaml
intent: casual_greeting
confidence: 0.99
tools_allowed: []
agents_allowed: [conversation]
project_lookup: false
memory_lookup: false
memory_write: false
```

Response:

```text
Chào anh 👋 Hôm nay COSA có thể giúp gì cho anh?
```

Project workflow chỉ được kích hoạt khi user có intent liên quan, ví dụ:

- “Kiểm tra project hiện tại.”
- “Phân tích project mID.”
- “Project nào đang trễ?”
- “Mở OKR của project A.”
- “Tạo project mới.”

---

# 4. Kiến trúc tổng thể đề xuất

```text
COSA
│
├── 1. Experience Layer
│   ├── Hologram Hub
│   ├── Chat
│   ├── Voice
│   ├── Desktop Flutter
│   └── Mobile Flutter
│
├── 2. Harness Control Plane
│   ├── Intent Router
│   ├── State Machine
│   ├── Context Resolver
│   ├── Skill Resolver
│   ├── Model Router
│   ├── Planner
│   ├── Policy Engine
│   ├── Approval Engine
│   ├── Verification Engine
│   ├── Memory Controller
│   └── Audit Controller
│
├── 3. Agent Runtime
│   ├── Founder Agent
│   ├── Finance Agent
│   ├── Legal Agent
│   ├── Marketing Agent
│   ├── Sales Agent
│   ├── Tech Agent
│   └── Learning Agent
│
├── 4. Execution Plane
│   ├── Skills
│   ├── MCP
│   ├── n8n
│   ├── Claude Code CLI
│   ├── Codex CLI
│   ├── Browser
│   ├── External APIs
│   └── OpenSandbox
│
├── 5. State Layer
│   ├── TaskSpec
│   ├── Plan
│   ├── Milestones
│   ├── Execution Events
│   ├── Verification
│   ├── Evidence
│   ├── Decisions
│   └── Memory
│
└── 6. Governance
    ├── Admin-only System Spec
    ├── Admin-only Prompt Registry
    ├── Admin-only Policy
    ├── Reset Default
    ├── Audit Trail
    └── Improvement Proposal
```

---

# 5. Harness Control Plane

## 5.1. Intent Router

### Nhiệm vụ

Xác định user đang:

- trò chuyện thông thường;
- hỏi thông tin;
- yêu cầu phân tích;
- yêu cầu thao tác;
- yêu cầu tạo task;
- yêu cầu kiểm tra project;
- yêu cầu coding;
- yêu cầu tài chính;
- yêu cầu marketing;
- yêu cầu sales;
- yêu cầu legal;
- yêu cầu learning/research.

### Output bắt buộc

```json
{
  "intent": "project_analysis",
  "confidence": 0.94,
  "domain": "founder",
  "requires_task": true,
  "requires_project_context": true,
  "requires_tools": true,
  "candidate_agents": ["founder"],
  "candidate_skills": ["project.analysis"]
}
```

### Intent tối thiểu

```text
casual_greeting
casual_chat
general_question
project_lookup
project_analysis
project_create
okr_review
twelve_week_review
finance_analysis
sales_operation
marketing_operation
legal_analysis
learning_research
code_analysis
code_change
external_action
system_admin
unknown
```

### Rule quan trọng

Nếu intent thuộc:

```text
casual_greeting
casual_chat
```

thì mặc định:

```text
tool_access = false
project_lookup = false
agent_orchestration = false
```

---

# 6. State Machine

COSA không nên để agent tự suy diễn trạng thái.

Task lifecycle:

```text
DRAFT
  ↓
READY
  ↓
PLANNING
  ↓
WAITING_APPROVAL     (nếu cần)
  ↓
EXECUTING
  ↓
VERIFYING
  ↓
COMPLETED
```

Nhánh lỗi:

```text
EXECUTING
  ↓
FAILED
  ↓
REPLAN
```

Nhánh dừng:

```text
PAUSED
CANCELLED
BLOCKED
```

Agent chỉ được dùng tool phù hợp state.

Ví dụ:

### PLANNING

Allowed:

```text
read
search
analyze
create_plan
```

Denied:

```text
deploy
delete
send_external_message
```

### EXECUTING

Allowed theo policy:

```text
write_workspace
run_cli
use_mcp
run_browser
```

### VERIFYING

Allowed:

```text
run_test
read_output
compare_expected
capture_evidence
```

Không được:

```text
silently_change_scope
deploy_unapproved_change
```

---

# 7. Canonical Agent Spec

Không tạo prompt riêng biệt cho từng provider theo kiểu:

```text
claude_prompt_v3
deepseek_prompt_final
codex_prompt_new
gemini_prompt_latest
```

COSA cần một Canonical Agent Spec.

Ví dụ:

```yaml
agent_id: marketing
name: Marketing Agent
purpose: >
  Hỗ trợ founder nghiên cứu thị trường, thiết kế campaign,
  landing page, content, funnel và đo lường.

domains:
  - marketing
  - growth

allowed_skills:
  - marketing.research
  - marketing.copywriting
  - marketing.landing_page
  - marketing.funnel

tool_policy:
  browser: allow
  write_workspace: sandbox
  deploy: approval
  send_email: approval

memory_scope:
  - company
  - project
  - marketing

verification:
  - factual_check
  - output_schema_check
  - task_specific_evaluation
```

Provider adapter chuyển Canonical Spec thành format phù hợp:

```text
Canonical Agent Spec
       │
       ├── Claude Adapter
       ├── Codex Adapter
       ├── DeepSeek Adapter
       ├── Gemini Adapter
       └── Local Model Adapter
```

---

# 8. Prompt & Spec Registry

## 8.1. Quyền

Core prompt/spec/policy:

```text
ADMIN: READ + WRITE + RESET
AGENT: READ
EMPLOYEE: READ hoặc NO ACCESS
```

Agent không được phép tự sửa:

- system prompt;
- policy;
- routing rules;
- tool permissions;
- core agent spec;
- admin config;
- security rules.

Agent chỉ được tạo:

```text
Improvement Proposal
```

---

## 8.2. Reset Default

Mỗi spec phải có:

```text
default_content
current_content
updated_at
updated_by
checksum
```

Admin có action:

```text
Reset to Default
```

Flow:

```text
Admin
  ↓
Review Diff
  ↓
Confirm Reset
  ↓
Restore Default
  ↓
Audit Log
```

---

# 9. Planning Artifact

Mọi task phức tạp phải tạo TaskSpec trước.

## 9.1. TaskSpec

```yaml
task_id:
title:
requested_by:
project_id:
intent:
objective:
scope:
out_of_scope:
constraints:
dependencies:
risk_level:
approval_required:
expected_outputs:
verification_required:
```

---

## 9.2. Plan

```yaml
goal:
context:
approach:
milestones:
  - id:
    title:
    status:
    verification:
risks:
open_questions:
expected_artifacts:
```

Rule:

> Milestone không được chuyển `DONE` nếu verification gate chưa pass.

---

# 10. Execution Log

Không dùng chat làm log triển khai.

Execution Event phải append-only.

Ví dụ:

```json
{
  "event_id": "evt_123",
  "task_id": "task_456",
  "type": "implementation_decision",
  "agent": "tech",
  "message": "Use Next.js App Router",
  "reason": "Existing project uses Next.js",
  "timestamp": "2026-08-16T08:00:00+07:00"
}
```

Event types:

```text
task_created
plan_created
plan_updated
approval_requested
approval_granted
tool_requested
tool_allowed
tool_denied
tool_executed
decision
deviation
verification_started
verification_passed
verification_failed
replan
task_completed
task_failed
memory_written
```

Không sửa event cũ.

Nếu có thay đổi:

```text
append new event
```

---

# 11. Skill Registry

Skills không được nạp toàn bộ vào prompt.

Thiết kế lazy-load.

```text
Skill Registry
│
├── founder.project_analysis
├── founder.okr
├── founder.12wy
├── finance.micro_business
├── finance.reporting
├── legal.contract_review
├── marketing.research
├── marketing.landing_page
├── marketing.content
├── sales.lead_generation
├── sales.crm
├── sales.pipeline
├── tech.nextjs
├── tech.fastapi
├── tech.postgresql
└── learning.research
```

Flow:

```text
Intent
  ↓
Skill Resolver
  ↓
Candidate Skills
  ↓
Permission Filter
  ↓
Load 1–3 skills cần thiết
```

Không inject toàn bộ skill index chi tiết vào model.

---

# 12. Context Resolver

Context phải được build theo yêu cầu hiện tại.

## 12.1. Context Pack

Ví dụ user hỏi:

> Doanh thu tháng này thế nào?

Context Pack chỉ gồm:

```text
user identity
company
current company finance context
finance policy
relevant transactions
finance skill
recent finance decisions
```

Không load:

```text
marketing
codebase
legal
landing page
sales playbook
all projects
all historical chat
```

---

## 12.2. Context Scope

Mỗi context item phải có:

```text
scope:
  user
  company
  project
  task
  agent
  session

priority:
  critical
  high
  normal
  optional

freshness:
  current
  stale
  expired
```

---

# 13. Memory Architecture

Memory đề xuất:

```text
Memory
├── User Preferences
├── Company Facts
├── Project Facts
├── Decisions
├── Lessons
├── Agent Episodes
└── Working Memory
```

Schema:

```yaml
memory_id:
type:
scope:
subject:
content:
source:
confidence:
created_at:
updated_at:
valid_until:
verification_state:
```

`verification_state`:

```text
unverified
verified
stale
invalid
```

### Rule quan trọng

Memory retrieved không mặc định là sự thật.

Nếu memory:

- cũ;
- conflict với database;
- không rõ source;
- ảnh hưởng quyết định quan trọng;

thì phải revalidate trước khi dùng.

---

# 14. Policy Engine

Policy Engine chạy **trước** Tool Gateway.

Input:

```json
{
  "user_role": "founder_admin",
  "agent": "tech",
  "task_state": "EXECUTING",
  "tool": "deploy",
  "action": "deploy_production",
  "target": "landing-page",
  "risk": "high"
}
```

Output:

```json
{
  "decision": "REQUIRE_APPROVAL",
  "reason": "Production deployment requires founder approval."
}
```

---

# 15. Approval Engine

Các action mặc định cần approval:

- deploy production;
- push public website;
- gửi email;
- gửi tin nhắn;
- tạo campaign có chi phí;
- đăng social;
- thay đổi data tài chính;
- xóa dữ liệu;
- thay đổi user role;
- thay đổi permission;
- thay đổi integration;
- thực thi giao dịch tài chính;
- publish hợp đồng;
- thay đổi core config.

UI:

```text
┌──────────────────────────────┐
│ Approval Required            │
│                              │
│ Agent: Tech                  │
│ Action: Deploy production    │
│ Project: Landing Page A      │
│ Risk: High                   │
│                              │
│ Summary                      │
│ ...                          │
│                              │
│ [Approve] [Reject]           │
└──────────────────────────────┘
```

---

# 16. Tool Gateway

Tất cả tool phải đi qua một gateway thống nhất.

```text
Agent
  ↓
Tool Request
  ↓
Policy Engine
  ↓
Tool Gateway
  ├── Skill
  ├── MCP
  ├── CLI
  ├── API
  ├── Browser
  └── n8n
```

Tool descriptor:

```yaml
tool_id:
category:
risk_level:
requires_sandbox:
requires_approval:
input_schema:
output_schema:
timeout:
allowed_agents:
```

---

# 17. Sandbox

Các tác vụ có write/execute phải mặc định chạy sandbox.

## 17.1. Sandbox-required

- chạy shell;
- Claude Code;
- Codex;
- sửa code;
- cài dependency;
- build;
- test;
- chạy script;
- tải file không tin cậy;
- browser automation;
- xử lý code generated.

---

## 17.2. Kiến trúc

```text
COSA Harness
    │
    ▼
Sandbox Manager
    │
    ├── Workspace Mount
    ├── Env
    ├── Resource Limits
    ├── Network Policy
    ├── File Policy
    └── Process Policy
             │
             ▼
Claude Code / Codex / Script
```

OpenSandbox có thể được dùng làm execution boundary.

---

# 18. Desktop và Mobile

Giữ hướng hiện tại:

## Desktop

```text
Flutter Desktop
    ↓
COSA Local Runtime
    ↓
Harness Engine
    ↓
Local Tools / Sandbox
    ↓
LiveKit Local
```

Desktop có quyền chạy executor local theo policy.

---

## Mobile

```text
Flutter Mobile
    ↓
COSA API
    ↓
Cloud Harness Runtime
    ↓
Cloud tools
    ↓
LiveKit Cloud
```

Mobile ưu tiên:

- chat;
- voice;
- approve;
- review;
- monitor;
- dashboard.

Không nên cho mobile mặc định có quyền thực thi shell local.

---

# 19. Model Router

Model Router không chọn model theo kiểu cố định toàn hệ thống.

Input:

```text
intent
task complexity
domain
cost target
latency target
privacy requirement
tool capability
context size
```

Ví dụ:

| Workload | Model Role |
|---|---|
| Chat nhanh | DeepSeek |
| Phân tích Founder | ChatGPT |
| Coding | Claude Code / Codex |
| Local/private | Local model |
| Vision | Vision-capable model |
| Verification | Có thể dùng model khác executor |

Rule:

> Planner và Verifier không bắt buộc phải cùng model với Executor.

---

# 20. Verification Engine

Agent không được tự tuyên bố task hoàn thành.

Flow:

```text
Execution Complete
      ↓
Verification Engine
      ↓
Evidence
      ↓
PASS?
 ┌────┴────┐
 │         │
YES       NO
 │         │
DONE     REPLAN / FAIL
```

---

## 20.1. Verification Types

### Code

```text
lint
typecheck
unit test
integration test
build
HTTP check
visual check
```

### Landing Page

```text
HTTP 200
responsive
form submit
database write
analytics event
broken links
visual screenshot
```

### Research

```text
source count
source reliability
date freshness
citation completeness
contradiction check
```

### Finance

```text
input completeness
calculation check
period reconciliation
policy compliance
evidence reference
```

### Sales

```text
lead deduplication
contact validity
pipeline status
next action
source
```

---

# 21. Evidence

Verification phải tạo evidence.

Evidence types:

```text
test_result
log
screenshot
file
URL
database_record
API_response
calculation
citation
```

Schema:

```yaml
evidence_id:
task_id:
verification_id:
type:
location:
summary:
created_at:
```

---

# 22. Hologram Hub

Hologram Hub nên trở thành **Agent Control Center**.

## 22.1. Agent Card

```text
┌──────────────────────────────┐
│ Marketing Agent              │
│ ● Executing                  │
│                              │
│ Project     Landing Page A   │
│ Plan        4 / 6            │
│ Tools       17               │
│ Verification 3 / 5           │
│                              │
│ Current                      │
│ Validate lead form           │
│                              │
│ [Open] [Pause]               │
└──────────────────────────────┘
```

---

## 22.2. Task Card

```text
Task
Status
Agent
Project
Progress
Current Step
Risk
Approval
Verification
```

---

## 22.3. Visual Task Flow

```text
Request
  ↓
Plan
  ↓
Execute
  ↓
Verify
  ↓
Complete
```

Màu trạng thái:

```text
Planning
Waiting Approval
Executing
Verifying
Completed
Failed
Blocked
```

Không cần visual quá kỹ thuật ở giai đoạn đầu.

---

# 23. Multi-Agent Strategy

Không dùng multi-agent mặc định.

Chỉ tạo sub-agent khi có ít nhất một lý do:

1. cần chạy song song;
2. cần context isolation;
3. cần permission khác;
4. cần domain expertise riêng;
5. cần independent verification.

Ví dụ hợp lý:

```text
Founder Agent
   │
   ├── Research Agent
   └── Finance Agent
```

Không nên:

```text
CEO Agent
 ↓
Planner Agent
 ↓
Manager Agent
 ↓
Worker Agent
 ↓
Critic Agent
 ↓
Reviewer Agent
```

cho những task đơn giản.

---

# 24. Self-Improvement

COSA có thể quan sát:

```text
routing errors
tool errors
failed tasks
verification failures
token usage
latency
user corrections
repeated replan
```

Sau đó Improvement Agent tạo:

```yaml
proposal:
problem:
evidence:
suggested_change:
affected_component:
risk:
expected_benefit:
test_plan:
```

Flow:

```text
Trace
  ↓
Evaluator
  ↓
Improvement Proposal
  ↓
Founder/Admin Review
  ↓
Approve / Reject
```

Không cho phép:

```text
Agent → modify core prompt automatically
Agent → modify policy automatically
Agent → change permission automatically
```

---

# 25. Audit Trail

Phải audit:

- admin chỉnh prompt;
- admin chỉnh spec;
- reset default;
- permission changes;
- approvals;
- denied tool calls;
- production deploy;
- external communication;
- data deletion;
- integration changes.

Schema:

```yaml
audit_id:
actor:
action:
resource:
before:
after:
reason:
timestamp:
```

---

# 26. Database đề xuất

PostgreSQL vẫn là system-of-record phù hợp.

Các bảng chính:

```text
users
roles
companies
projects

agents
agent_specs
agent_spec_defaults

skills
agent_skills

prompts
prompt_defaults

policies
policy_rules

tasks
task_plans
task_milestones
task_events

tool_definitions
tool_calls

approvals

verifications
verification_results
evidences

memories

improvement_proposals

audit_logs
```

---

# 27. Local Config

Có thể lưu spec local để app đọc nhanh, nhưng PostgreSQL nên giữ canonical state nếu deployment có server.

Local:

```text
~/.cosa/
├── config/
├── specs/
├── cache/
├── tasks/
├── logs/
└── workspace/
```

### Rule

Spec local:

- cache;
- export;
- offline fallback.

Không để file local trở thành nguồn sự thật duy nhất nếu COSA đang chạy multi-device.

Admin edit:

```text
UI Admin
  ↓
Canonical Store
  ↓
Validate
  ↓
Persist
  ↓
Sync Local Cache
```

---

# 28. Source Structure đề xuất

Backend FastAPI:

```text
backend/
├── app/
│   ├── harness/
│   │   ├── router/
│   │   ├── state/
│   │   ├── context/
│   │   ├── skills/
│   │   ├── models/
│   │   ├── planner/
│   │   ├── policy/
│   │   ├── approval/
│   │   ├── verification/
│   │   ├── memory/
│   │   └── audit/
│   │
│   ├── agents/
│   ├── tools/
│   ├── sandbox/
│   ├── integrations/
│   ├── projects/
│   ├── okrs/
│   ├── twelve_week/
│   ├── finance/
│   ├── sales/
│   ├── marketing/
│   ├── legal/
│   └── learning/
```

---

# 29. API đề xuất

```text
POST /harness/route
POST /tasks
GET  /tasks/{id}
POST /tasks/{id}/plan
POST /tasks/{id}/execute
POST /tasks/{id}/pause
POST /tasks/{id}/resume

GET  /tasks/{id}/events
GET  /tasks/{id}/evidence

POST /approvals/{id}/approve
POST /approvals/{id}/reject

GET  /agents
GET  /agents/{id}

GET  /admin/specs
PUT  /admin/specs/{id}
POST /admin/specs/{id}/reset

GET  /admin/prompts
PUT  /admin/prompts/{id}
POST /admin/prompts/{id}/reset

GET  /admin/policies
PUT  /admin/policies/{id}

GET  /improvements
POST /improvements/{id}/approve
POST /improvements/{id}/reject
```

---

# 30. Permission Matrix

## Founder/Admin

```text
manage spec
manage prompts
manage policy
manage agents
approve high-risk actions
reset defaults
view audit logs
```

## Employee

Trong tương lai:

```text
use assigned agents
view assigned projects
execute allowed workflows
request approvals
```

Không mặc định:

```text
modify system
modify policy
modify agent core prompt
```

---

# 31. Compatibility với các module COSA hiện tại

Harness Engine phải bọc các module hiện có, không thay thế chúng.

```text
Projects
OKRs
12 Week Year
Finance
Legal
Marketing
Sales
Learning
CRM
LiveKit
OpenSandbox
Claude Code
Codex
n8n
Hostinger
```

Tất cả được gọi qua:

```text
Harness → Policy → Tool/Agent
```

---

# 32. Mối quan hệ với Claude Code / Codex

Claude Code và Codex là **executor**, không phải orchestration core.

Flow đúng:

```text
User
 ↓
COSA Harness
 ↓
TaskSpec
 ↓
Plan
 ↓
Policy
 ↓
Sandbox
 ↓
Claude Code / Codex
 ↓
Verification
 ↓
Evidence
 ↓
COSA
```

Không:

```text
User
 ↓
Claude Code
 ↓
full repository
 ↓
tự quyết định mọi thứ
```

---

# 33. Mối quan hệ với n8n

n8n là workflow executor/integration layer.

Ví dụ:

```text
COSA
  ↓
approval
  ↓
n8n
  ↓
Email / CRM / API
```

Không dùng n8n làm core reasoning engine.

---

# 34. Mối quan hệ với OpenSandbox

OpenSandbox đảm nhiệm:

```text
untrusted execution
workspace isolation
process isolation
resource limitation
```

Harness quyết định:

```text
khi nào cần sandbox
agent nào được quyền
workspace nào được mount
network nào được phép
```

---

# 35. Mối quan hệ với LiveKit

LiveKit không nằm trong Harness core.

Nó thuộc Experience Layer.

```text
Voice
 ↓
LiveKit
 ↓
Conversation Gateway
 ↓
Intent Router
 ↓
Harness
```

Desktop:

```text
LiveKit Local
```

Mobile:

```text
LiveKit Cloud
```

---

# 36. Hướng triển khai theo ưu tiên

## P0 — Core Reliability

Triển khai trước:

1. Intent Router.
2. Casual-chat no-tool rule.
3. State Machine.
4. Canonical Agent Spec.
5. Prompt/Spec Registry.
6. Admin-only edit.
7. Reset Default.
8. Policy Engine.
9. TaskSpec.
10. Plan.
11. Execution Event Log.
12. Verification Gate.
13. Evidence.
14. Hologram Hub task status.

### Kết quả P0

COSA phải:

- không gọi project tool khi user chỉ chào;
- không để model tự thay đổi permission;
- không báo Done nếu chưa verify;
- task không mất state khi restart;
- Hologram Hub hiển thị được task đang làm gì.

---

## P1 — Execution Safety

1. Tool Registry.
2. Tool Gateway.
3. Sandbox Manager.
4. OpenSandbox integration.
5. Skill lazy loading.
6. Context Resolver.
7. Context compression.
8. Model Router.
9. Approval Engine.
10. Memory validation.

---

## P2 — Advanced Harness

1. Sub-agent orchestration.
2. Parallel tasks.
3. Planner / Executor separation.
4. Independent verifier.
5. Automated evals.
6. Trace analysis.
7. Improvement Proposal Agent.
8. Performance optimization.
9. Cache-aware prompt design.

---

# 37. Acceptance Criteria

## Routing

- [ ] “Chào” không gọi project lookup.
- [ ] Casual conversation không gọi tool.
- [ ] Project intent mới load project context.
- [ ] Unknown intent không tự thực thi high-risk action.

## Spec Governance

- [ ] Core spec chỉ admin sửa được.
- [ ] Core prompt chỉ admin sửa được.
- [ ] Có Reset to Default.
- [ ] Mọi thay đổi có audit.

## Task

- [ ] Task có persistent state.
- [ ] Có TaskSpec.
- [ ] Có Plan.
- [ ] Có append-only event log.
- [ ] Có pause/resume.
- [ ] Restart app không mất task.

## Tools

- [ ] Tool phải đi qua Policy Engine.
- [ ] High-risk tool cần approval.
- [ ] Code execution chạy sandbox.
- [ ] Tool output có schema.

## Verification

- [ ] Task không được Completed trước verification.
- [ ] Verification có evidence.
- [ ] Failure chuyển sang replan hoặc failed.

## Memory

- [ ] Memory có source.
- [ ] Memory có confidence.
- [ ] Memory có verification_state.
- [ ] Stale memory không được tự động tin dùng.

## Hologram Hub

- [ ] Hiện agent.
- [ ] Hiện task.
- [ ] Hiện state.
- [ ] Hiện progress.
- [ ] Hiện approval.
- [ ] Hiện verification.
- [ ] Hiện current action.

---

# 38. Definition of Done cho Harness Core

Harness Core được coi là đạt khi demo được flow:

```text
User:
"Chào"

→ casual_greeting
→ no tools
→ response
```

và:

```text
User:
"Phân tích project COSA và đề xuất landing page"

→ project_analysis
→ project context
→ TaskSpec
→ Plan
→ Marketing Agent
→ relevant skills
→ execution
→ verification
→ evidence
→ Completed
```

và:

```text
User:
"Deploy landing page"

→ external/high-risk action
→ REQUIRE_APPROVAL
→ Founder approves
→ sandbox / executor
→ deployment
→ HTTP verification
→ evidence
→ Completed
```

---

# 39. Nguyên tắc không được phá vỡ

1. LLM không có quyền bypass Policy Engine.
2. Agent không được tự sửa core prompt/spec.
3. Không dùng chat history làm persistent task state.
4. Không báo Completed trước verification.
5. Không đưa toàn bộ skills/context vào mọi request.
6. Không tự động multi-agent cho task đơn giản.
7. Không cho code executor truy cập toàn máy mặc định.
8. Không auto-apply self-improvement.
9. High-risk action phải có deterministic rule.
10. Hologram Hub đọc state thật từ Harness, không render “AI đang làm...” giả lập.

---

# 40. Kết luận

Harness Engineering nên trở thành một lớp lõi mới của COSA:

```text
Founder OS
   +
Harness Control Plane
   +
Agent Runtime
   +
Execution Plane
```

Thay vì tiếp tục tăng số lượng agent hoặc thêm prompt ngày càng lớn, COSA nên ưu tiên xây dựng lớp điều phối deterministic xung quanh model.

Kiến trúc này giúp COSA:

- ổn định hơn;
- dễ debug hơn;
- an toàn hơn;
- ít phụ thuộc model hơn;
- giảm token;
- dễ thay provider;
- dễ chạy local/cloud hybrid;
- hỗ trợ desktop/mobile;
- hỗ trợ future employees;
- phù hợp với mô hình Founder / One Person Company;
- tạo nền tảng cho self-improving agent có governance.

**Định hướng kiến trúc cuối cùng:**

```text
COSA không phải chỉ là một tập hợp AI Agents.

COSA là Founder Operating System,
trong đó Harness Engine quản lý cách AI suy nghĩ,
được phép hành động, kiểm chứng kết quả
và ghi nhớ để tiếp tục công việc.
```
