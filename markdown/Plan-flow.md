# COSA Plan Engine — Tài liệu kiến trúc và triển khai

**Trạng thái:** Đề xuất triển khai vào kiến trúc COSA hiện tại
**Mục tiêu:** Chuẩn hóa toàn bộ quá trình từ yêu cầu của Founder → lập kế hoạch → thực thi → quan sát → điều chỉnh → kiểm chứng → bàn giao kết quả.
**Nguyên tắc trung tâm:**

> **Understand → Plan → Execute → Observe → Re-plan → Verify → Deliver**

Đối với công việc phức tạp:

> **NO PLAN → NO EXECUTION**

---

# 1. Mục tiêu

COSA không nên hoạt động theo mô hình:

```text
Founder
  ↓
Prompt
  ↓
LLM
  ↓
Answer / Tool Call
```

Mà chuyển thành:

```text
Founder Goal
     ↓
Understand
     ↓
PLAN ENGINE
     ↓
Execution Runtime
     ↓
Act
     ↓
Observe
     ↓
Update Plan / Re-plan
     ↓
Verify
     ↓
Deliver
```

Plan không phải nội dung suy nghĩ tạm thời của LLM.

Plan phải trở thành **đối tượng dữ liệu chính thức** trong COSA, có thể:

* lưu vào PostgreSQL;
* hiển thị trên Hologram Hub;
* liên kết Project;
* liên kết Agent;
* liên kết Tasks;
* theo dõi tiến độ;
* lưu dependency;
* lưu blocker;
* lưu evidence;
* thay đổi trong quá trình thực thi;
* kiểm tra acceptance criteria;
* phục hồi sau restart;
* audit toàn bộ quá trình Agent đã làm.

---

# 2. Vị trí của Plan Engine trong COSA

Không tạo thêm một `Planning Agent` độc lập nếu không thật sự cần thiết.

`Plan Engine` nên là **core service dùng chung cho tất cả Agent**.

```text
                    ┌─────────────────┐
                    │     Founder     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ COSA Co-founder │
                    └────────┬────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Request Understanding │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │      PLAN ENGINE      │
                 │                       │
                 │ Goal                  │
                 │ Deliverables          │
                 │ Milestones            │
                 │ Tasks                 │
                 │ Dependencies          │
                 │ Agents                │
                 │ Tools                 │
                 │ Risks                 │
                 │ Success Criteria      │
                 │ Verification          │
                 └───────────┬───────────┘
                             │
                             ▼
               ┌───────────────────────────┐
               │ Agent Execution Runtime   │
               └─────────────┬─────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
      AI Agents          MCP / API          Local Tools
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
                         OBSERVE
                             │
                    ┌────────┴────────┐
                    │                 │
                 success           problem
                    │                 │
                    ▼                 ▼
              next task           RE-PLAN
                    │                 │
                    └────────┬────────┘
                             ▼
                           VERIFY
                             │
                             ▼
                          RESULT
```

---

# 3. Plan Engine không thay thế Agent

Cần tách rõ:

## Plan Engine

Trả lời:

* cần làm gì;
* theo thứ tự nào;
* ai thực hiện;
* dùng công cụ nào;
* đầu vào là gì;
* đầu ra là gì;
* điều kiện hoàn thành là gì.

## Agent

Thực hiện một hoặc nhiều nhiệm vụ trong Plan.

Ví dụ:

```text
PLAN
│
├── Market research
│      └── Marketing Agent
│
├── Build landing page
│      └── Coding Agent
│
├── Setup lead pipeline
│      └── Sales Agent
│
└── Review compliance
       └── Legal Agent
```

Agent không tự tạo một hệ quản trị công việc riêng.

Tất cả dùng chung:

```text
COSA Plan Engine
```

---

# 4. Phân loại yêu cầu trước khi lập Plan

Không phải yêu cầu nào cũng cần một Plan lớn.

COSA nên có `Task Complexity Classifier`.

## Level 0 — Conversation

Ví dụ:

```text
"Chào COSA"
"PMF là gì?"
"Giải thích CAC"
```

Xử lý trực tiếp.

Không tạo Plan.

---

## Level 1 — Direct Action

Ví dụ:

```text
"Đổi tên project thành COSA"
"Đánh dấu task này completed"
"Mở project ABC"
```

Có thể thực thi trực tiếp.

Flow:

```text
Understand
→ Permission check
→ Execute
→ Verify
→ Respond
```

Không cần Plan chi tiết.

---

# 5. Level 2 — Planned Task

Ví dụ:

```text
"Phân tích 5 đối thủ cạnh tranh."
"Viết landing page cho sản phẩm."
"Lập kế hoạch marketing tháng sau."
```

COSA tạo `Compact Plan`.

Ví dụ:

```yaml
goal: Phân tích 5 đối thủ

steps:
  - xác định đối thủ
  - thu thập dữ liệu
  - phân tích positioning
  - so sánh pricing
  - tìm opportunity
  - tổng hợp báo cáo

deliverables:
  - competitor_matrix
  - findings
  - recommendations

success_criteria:
  - đủ 5 đối thủ
  - có nguồn dữ liệu
  - có phân tích
  - có khuyến nghị
```

Sau đó có thể tự thực thi.

---

# 6. Level 3 — Project Execution

Ví dụ:

```text
"Xây CRM cho COSA."

"Thiết kế và triển khai website sản phẩm."

"Tích hợp hệ thống Marketing Automation."

"Xây module kế toán."
```

Bắt buộc:

```text
Understand
   ↓
Inspect Current State
   ↓
Create Execution Plan
   ↓
Define Acceptance Criteria
   ↓
Plan Validation
   ↓
Execute Incrementally
```

Quy tắc:

```text
NO PLAN
=
NO EXECUTION
```

Đặc biệt áp dụng cho:

* Claude Code;
* Coding Agent;
* migration database;
* deployment;
* automation;
* thay đổi kiến trúc;
* tác vụ ảnh hưởng nhiều module.

---

# 7. Cấu trúc chuẩn của COSA Plan

Mỗi Plan tối thiểu nên chứa:

```yaml
plan:
  id:
  company_id:
  project_id:

  title:
  description:

  user_goal:
  interpreted_goal:

  plan_level:

  context:

  deliverables: []

  milestones: []

  tasks: []

  dependencies: []

  assumptions: []

  constraints: []

  risks: []

  agents: []

  tools: []

  success_criteria: []

  verification: []

  current_state:

  progress:

  created_at:
  updated_at:
```

---

# 8. Goal

Phân biệt:

```text
user_goal
```

và:

```text
interpreted_goal
```

Ví dụ Founder nói:

> Làm landing page để bán khóa học.

Không nên lưu interpreted goal đơn giản:

```text
Tạo landing page.
```

Mà nên chuyển thành:

```text
Tạo và triển khai landing page responsive
cho khóa học, cho phép khách hàng hiểu offer,
đăng ký thông tin và tạo lead trong CRM.
```

---

# 9. Deliverables

Mỗi Plan phải định nghĩa rõ sản phẩm cuối cùng.

Ví dụ:

```yaml
deliverables:
  - type: website
    name: Landing Page
    required: true

  - type: database
    name: Lead Capture
    required: true

  - type: integration
    name: CRM Integration
    required: true

  - type: document
    name: Deployment Notes
    required: true
```

Điều này ngăn Agent kết luận:

> Đã hoàn thành.

trong khi mới chỉ viết source code mà chưa deploy.

---

# 10. Milestone

Plan lớn cần chia thành milestone.

Ví dụ:

```text
M1 — Analyze
M2 — Architecture
M3 — Backend
M4 — Frontend
M5 — Integration
M6 — Testing
M7 — Deployment
```

Mỗi milestone phải có:

```yaml
id:
title:
description:
status:
dependencies:
success_criteria:
```

---

# 11. Task

Milestone tiếp tục chia thành task đủ nhỏ để Agent thực thi.

Ví dụ:

```yaml
task:
  id: TASK-031

  milestone: M3

  title: Create lead API

  description:
    Tạo REST endpoint nhận thông tin lead.

  assigned_agent:
    coding_agent

  tools:
    - filesystem
    - terminal
    - postgres

  dependencies:
    - TASK-028
    - TASK-029

  expected_output:
    - POST /api/leads

  success_criteria:
    - returns 201
    - persists database
    - validation implemented
    - unit test passed

  status:
    pending
```

---

# 12. State Machine

Không lưu task bằng boolean đơn giản:

```text
done = true / false
```

Nên dùng state machine.

```text
DRAFT
  ↓
READY
  ↓
RUNNING
  ↓
WAITING
  ↓
BLOCKED
  ↓
RUNNING
  ↓
VERIFYING
  ↓
COMPLETED
```

Ngoài ra:

```text
FAILED
CANCELLED
SKIPPED
NEEDS_REPLAN
```

---

# 13. Plan State

Plan tổng có thể có:

```text
draft

planning

ready

executing

paused

blocked

replanning

verifying

completed

failed

cancelled
```

---

# 14. Observe Engine

Sau mỗi action:

```text
ACTION
   ↓
TOOL
   ↓
TOOL RESULT
   ↓
OBSERVE
```

Observe phải tạo structured data.

Ví dụ:

```json
{
  "task_id": "TASK-031",
  "status": "failed",
  "observation_type": "tool_error",
  "summary": "Database migration failed",
  "error_code": "DB_SCHEMA_CONFLICT",
  "retryable": false,
  "requires_replan": true
}
```

Không chỉ gửi error text lại cho LLM.

---

# 15. Re-plan

Đây là thành phần bắt buộc.

Plan COSA phải là:

> **Living Plan**

Không phải checklist được tạo một lần rồi cố chạy đến cuối.

Ví dụ:

```text
Original

M3
├── Create schema
├── Create API
└── Connect UI
```

Agent phát hiện schema cũ xung đột.

COSA chuyển:

```text
TASK → NEEDS_REPLAN
```

Sau đó:

```text
M3
├── Backup schema
├── Analyze migration
├── Generate migration
├── Validate data
├── Create API
└── Connect UI
```

Nhưng phải giữ lịch sử:

```text
Plan Version 1
Plan Version 2
```

Không overwrite hoàn toàn Plan cũ.

---

# 16. Plan Versioning

Tạo:

```text
plan_versions
```

Ví dụ:

```yaml
version: 3

reason:
  PostgreSQL schema conflict discovered

changed:
  - added backup step
  - added data migration
  - modified API dependency
```

Cho phép Founder hỏi:

> Vì sao COSA thay đổi kế hoạch?

COSA có thể trả lời dựa trên event thực tế.

---

# 17. Evidence

Mỗi task quan trọng phải tạo evidence.

Ví dụ coding:

```text
commit
test result
build result
changed files
```

Marketing:

```text
sources
campaign data
screenshots
analytics
```

Sales:

```text
lead record
email sent
CRM stage change
```

Finance:

```text
document
calculation
source transaction
```

Schema:

```yaml
evidence:
  id:
  plan_id:
  task_id:

  evidence_type:

  source:

  content:

  file_path:

  created_at:
```

---

# 18. Success Criteria

Đây là thành phần bắt buộc của Plan.

Không dùng:

```text
"Hoàn thành website"
```

Nên dùng:

```yaml
success_criteria:

  - landing page deployed

  - HTTPS works

  - mobile responsive

  - lead form works

  - data appears in CRM

  - no critical console errors

  - build passes

  - analytics event recorded
```

Agent chỉ được chuyển:

```text
VERIFYING
→
COMPLETED
```

sau khi kiểm tra các criteria.

---

# 19. Verification Engine

Verification có thể bao gồm:

```text
Automated Verification
+
Agent Review
+
Founder Approval
```

Không phải task nào cũng cần Founder approve.

---

# 20. Approval Policy

Ví dụ:

## Auto execute

```text
search
analysis
read data
draft content
generate report
```

## Execute + log

```text
create local file
create task
update internal status
```

## Require confirmation

```text
send public post
send customer email
deploy production
delete data
financial transaction
sign document
change security config
```

Plan Engine phải lưu:

```yaml
approval_required: true
approval_status: pending
```

---

# 21. Database đề xuất

COSA hiện tại có thể bổ sung các bảng:

```text
plans

plan_versions

plan_milestones

plan_tasks

plan_dependencies

plan_assignments

plan_tool_requirements

plan_success_criteria

plan_verifications

plan_events

plan_evidence

plan_approvals
```

---

# 22. Bảng `plans`

```sql
CREATE TABLE plans (
    id UUID PRIMARY KEY,

    company_id UUID NOT NULL,

    project_id UUID,

    title TEXT NOT NULL,

    user_goal TEXT NOT NULL,

    interpreted_goal TEXT,

    description TEXT,

    plan_level INTEGER NOT NULL,

    status VARCHAR(30) NOT NULL,

    progress NUMERIC DEFAULT 0,

    current_milestone_id UUID,

    current_task_id UUID,

    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),

    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

# 23. `plan_milestones`

```sql
CREATE TABLE plan_milestones (
    id UUID PRIMARY KEY,

    plan_id UUID NOT NULL
        REFERENCES plans(id)
        ON DELETE CASCADE,

    title TEXT NOT NULL,

    description TEXT,

    sequence INTEGER NOT NULL,

    status VARCHAR(30) NOT NULL,

    progress NUMERIC DEFAULT 0,

    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),

    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

# 24. `plan_tasks`

```sql
CREATE TABLE plan_tasks (
    id UUID PRIMARY KEY,

    plan_id UUID NOT NULL
        REFERENCES plans(id)
        ON DELETE CASCADE,

    milestone_id UUID
        REFERENCES plan_milestones(id),

    title TEXT NOT NULL,

    description TEXT,

    sequence INTEGER,

    status VARCHAR(30) NOT NULL,

    assigned_agent TEXT,

    expected_output JSONB,

    input_data JSONB,

    output_data JSONB,

    retry_count INTEGER DEFAULT 0,

    max_retries INTEGER DEFAULT 3,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

# 25. Dependencies

Không nên chỉ dựa vào `sequence`.

Ví dụ:

```text
TASK C
```

có thể cần:

```text
TASK A + TASK B
```

Tạo:

```sql
CREATE TABLE plan_dependencies (
    id UUID PRIMARY KEY,

    plan_id UUID NOT NULL,

    task_id UUID NOT NULL,

    depends_on_task_id UUID NOT NULL,

    dependency_type VARCHAR(30)
);
```

---

# 26. Event Log

Đây là phần rất quan trọng.

Mọi thay đổi nên tạo event:

```text
PLAN_CREATED

TASK_STARTED

TOOL_CALLED

TOOL_SUCCEEDED

TOOL_FAILED

TASK_BLOCKED

REPLAN_REQUESTED

PLAN_UPDATED

TASK_COMPLETED

VERIFICATION_FAILED

PLAN_COMPLETED
```

Ví dụ:

```json
{
  "event": "TASK_BLOCKED",

  "plan_id": "...",

  "task_id": "...",

  "reason": "Missing VPS credentials",

  "timestamp": "..."
}
```

Đây sẽ là nguồn quan trọng cho:

* audit;
* Hologram;
* debugging;
* Agent memory;
* analytics.

---

# 27. API FastAPI đề xuất

Tạo module:

```text
backend/
└── app/
    └── plan_engine/
        ├── models.py
        ├── schemas.py
        ├── repository.py
        ├── service.py
        ├── planner.py
        ├── executor.py
        ├── observer.py
        ├── replanner.py
        ├── verifier.py
        └── routes.py
```

---

# 28. API cơ bản

```text
POST
/api/plans
```

Tạo Plan.

```text
GET
/api/plans/{id}
```

Xem Plan.

```text
POST
/api/plans/{id}/start
```

Thực thi.

```text
POST
/api/plans/{id}/pause
```

Pause.

```text
POST
/api/plans/{id}/resume
```

Resume.

```text
POST
/api/plans/{id}/replan
```

Re-plan.

```text
GET
/api/plans/{id}/events
```

Timeline.

```text
GET
/api/plans/{id}/evidence
```

Evidence.

```text
POST
/api/plans/{id}/approve
```

Founder approval.

---

# 29. Planning Pipeline

Khi nhận yêu cầu:

```python
async def process_user_request(request):

    understanding = await understand(request)

    complexity = await classify_complexity(
        understanding
    )

    if complexity == "conversation":
        return await direct_response()

    if complexity == "direct_action":
        return await execute_direct_action()

    context = await context_engine.retrieve(
        understanding
    )

    plan = await plan_engine.create(
        understanding=understanding,
        context=context
    )

    await plan_repository.save(plan)

    return plan
```

---

# 30. Execution Loop

Logic cốt lõi:

```python
while not plan.is_finished():

    task = plan.get_next_ready_task()

    if not task:
        break

    if task.requires_approval:
        await wait_for_approval(task)
        continue

    result = await executor.execute(task)

    observation = await observer.inspect(result)

    await save_observation(observation)

    if observation.requires_replan:

        await replanner.update(
            plan=plan,
            observation=observation
        )

        continue

    verification = await verifier.verify(
        task,
        result
    )

    if verification.passed:
        await complete(task)

    else:
        await handle_failure(task)
```

Đây chính là:

```text
PLAN
  ↕
REASON
  ↕
ACT
  ↕
OBSERVE
```

---

# 31. Agent Assignment

Plan Engine quyết định agent theo capability.

Ví dụ registry:

```yaml
agents:

  marketing_agent:
    capabilities:
      - market_research
      - positioning
      - campaign
      - content

  sales_agent:
    capabilities:
      - leads
      - crm
      - pipeline
      - outreach

  finance_agent:
    capabilities:
      - accounting
      - cashflow
      - financial_analysis

  legal_agent:
    capabilities:
      - legal_research
      - document_review

  coding_agent:
    capabilities:
      - architecture
      - coding
      - testing
      - deployment
```

Plan task không nhất thiết hard-code agent.

Có thể khai báo:

```yaml
required_capabilities:
  - frontend_development
```

Runtime chọn agent phù hợp.

---

# 32. Tool Registry

Tương tự Agent Registry:

```yaml
tools:

  web_search:
    risk: low

  filesystem:
    risk: medium

  postgres:
    risk: medium

  github:
    risk: medium

  terminal:
    risk: high

  deployment:
    risk: high

  email_send:
    risk: high
```

Plan có thể xác định trước tool cần dùng.

Executor vẫn phải kiểm tra permission trước mỗi action.

---

# 33. Context Engine

Plan không được sinh chỉ từ prompt.

Trước khi planning cần retrieve:

```text
Company
Project
Stage
Previous decisions
Current architecture
Relevant documents
Current tasks
Available agents
Available tools
Permissions
Existing code state
```

Ví dụ Founder yêu cầu:

> Xây CRM.

Plan phải biết COSA đã có:

```text
Lead
Marketing
Sales
Automation
n8n
```

để không thiết kế một hệ thống CRM tách biệt khỏi kiến trúc hiện tại.

---

# 34. Stage-Aware Planning

Plan Engine nên biết startup/project đang ở giai đoạn nào.

Ví dụ:

```text
Discovery
Validation
MVP
Traction
Growth
Operations
```

Hai Founder cùng yêu cầu:

> Xây marketing plan.

Nhưng:

```text
Startup A → Validation
```

Plan ưu tiên:

```text
interviews
problem validation
experiments
landing page
lead signal
```

Trong khi:

```text
Company B → Growth
```

Plan ưu tiên:

```text
CAC
conversion
campaign
retention
automation
channel optimization
```

Đây là lý do `Project Stage` phải trở thành một phần Context của Plan Engine.

---

# 35. Tích hợp Project Management

Plan Engine không thay thế hệ Project Management.

Quan hệ đề xuất:

```text
Project
   ↓
Plan
   ↓
Milestone
   ↓
Task
```

Task có thể tiếp tục mapping sang:

```text
12 Week Year
Weekly Tactics
Daily Top 3
```

Ví dụ:

```text
Founder Goal
   ↓
COSA Plan
   ↓
Milestones
   ↓
Tasks
   ↓
Weekly execution
   ↓
Daily Top 3
```

Như vậy AI planning và quản trị thực thi dùng chung một nguồn dữ liệu.

---

# 36. Hologram Hub

Plan nên trở thành một loại Card chính.

Ví dụ:

```text
┌─────────────────────────────────────┐
│ CRM Implementation                  │
│                                     │
│ EXECUTING                           │
│ ██████████████░░░░ 67%              │
│                                     │
│ Current                             │
│ Connect Lead API → Pipeline         │
│                                     │
│ Next                                │
│ CRM UI                              │
│                                     │
│ Agents                              │
│ Coding · Sales                      │
│                                     │
│ Blockers                            │
│ None                                │
│                                     │
│ 12 / 18 tasks completed             │
└─────────────────────────────────────┘
```

---

# 37. Plan Detail Screen

Khi mở Plan:

```text
Overview

Goal

Deliverables

Progress

Milestones

Tasks

Agents

Dependencies

Blockers

Evidence

Verification

Timeline
```

Không hiển thị raw chain-of-thought của LLM.

Chỉ hiển thị thông tin hữu ích:

```text
Decision

Why

Evidence

Next Action
```

---

# 38. Timeline UI

Ví dụ:

```text
09:20 Plan created

09:22 Architecture analysis started

09:28 14 files inspected

09:31 Database schema conflict detected

09:32 Plan updated → version 2

09:36 Migration generated

09:41 Migration tests passed

09:43 API implementation started
```

Đây là cách Founder biết AI thực sự đang làm gì.

---

# 39. Founder Controls

Các nút cần có:

```text
Start

Pause

Resume

Stop

Approve

Reject

Re-plan

Edit Plan

Skip Task

Retry

Assign Agent
```

Founder vẫn là authority cuối cùng.

---

# 40. AI đề xuất Plan trước khi thực thi

Với Level 3, UI có thể:

```text
COSA has prepared an execution plan.

7 milestones
24 tasks
3 agents
Estimated complexity: High

[Review Plan]

[Start]
```

Không nhất thiết bắt Founder approve mọi Plan.

Policy có thể cấu hình:

```text
Auto Start
```

hoặc:

```text
Require Founder Approval
```

---

# 41. Prompt chuẩn cho Planner

```text
SYSTEM ROLE

You are the COSA Planning Engine.

Your responsibility is NOT to execute the task.

Your responsibility is to transform a user's goal
into a structured, executable and verifiable plan.


OBJECTIVES

Create a plan that is:

- complete
- executable
- context-aware
- dependency-aware
- tool-aware
- agent-aware
- measurable
- verifiable
- adaptable


BEFORE PLANNING

Inspect available:

- company context
- project context
- project stage
- existing architecture
- existing data
- previous decisions
- available agents
- available tools
- permissions
- constraints


PLAN MUST DEFINE

1. interpreted goal

2. expected deliverables

3. milestones

4. tasks

5. dependencies

6. required capabilities

7. required tools

8. assumptions

9. constraints

10. risks

11. success criteria

12. verification methods


IMPORTANT

Never mark vague actions such as:

"implement feature"

Instead decompose them into executable tasks.

Do not execute tools.

Do not invent unavailable capabilities.

Do not expose hidden chain-of-thought.

Return structured planning decisions only.
```

---

# 42. Re-planner Prompt

```text
You are the COSA Re-planning Engine.

An execution plan is currently running.

A new observation has changed the execution context.

Your task is to update ONLY the parts of the plan
that are affected.

Preserve:

- completed work
- valid tasks
- evidence
- previous plan version
- project constraints

Analyze:

- what changed
- which tasks are invalid
- which dependencies changed
- whether new tasks are required
- whether success criteria changed

Return:

- reason_for_replan
- affected_tasks
- added_tasks
- removed_tasks
- modified_dependencies
- new_plan_version

Never discard completed evidence.
```

---

# 43. Verifier Prompt

```text
You are the COSA Verification Engine.

Your job is NOT to improve the output.

Your job is to determine whether the execution
actually satisfies the agreed success criteria.

For each criterion return:

- criterion
- status
- evidence
- explanation

Valid statuses:

PASS
FAIL
NOT_VERIFIED

A task cannot be completed when mandatory
criteria remain FAIL or NOT_VERIFIED.
```

---

# 44. Claude Code Integration

Đây là nơi Plan Engine đặc biệt quan trọng.

Claude Code không nên nhận:

```text
"Build CRM"
```

và lập tức sửa code.

Flow phải là:

```text
Founder
   ↓
COSA
   ↓
Plan Engine
   ↓
Coding Execution Plan
   ↓
Claude Code
```

---

# 45. Quy tắc cho coding task

Mọi coding project Level 3 phải:

```text
1. Inspect repository

2. Identify current architecture

3. Identify affected modules

4. Identify constraints

5. Create implementation plan

6. Define acceptance criteria

7. Execute one milestone at a time

8. Test

9. Observe

10. Re-plan if required

11. Verify

12. Report evidence
```

---

# 46. CLAUDE.md — bổ sung quy tắc ngắn

Bổ sung vào `CLAUDE.md` hiện tại:

```markdown
## Planning Before Execution

For non-trivial changes:

1. Inspect the existing codebase first.
2. Understand current architecture and conventions.
3. Create an implementation plan before editing files.
4. Identify affected files, dependencies and risks.
5. Define acceptance criteria.
6. Execute incrementally by task or milestone.
7. Test after meaningful changes.
8. Observe errors and update the plan when assumptions fail.
9. Do not continue blindly after a failed dependency.
10. Verify acceptance criteria before declaring completion.

Rule:

NO PLAN → NO EXECUTION

Do not rewrite working architecture unless the plan explicitly requires it.
Do not create duplicate modules when equivalent functionality already exists.
Prefer extending COSA's existing architecture over introducing parallel systems.
```

Không nên biến `CLAUDE.md` thành tài liệu hàng nghìn dòng.

Nó chỉ chứa các nguyên tắc lâu dài.

Chi tiết Plan nằm trong Plan Engine.

---

# 47. Plan Artifact cho Claude Code

COSA có thể sinh file tạm:

```text
.cosa/
plans/
crm-implementation.json
```

Ví dụ:

```json
{
  "goal": "Implement CRM module",

  "current_task": "CRM-07",

  "task": {
    "title": "Create pipeline API",

    "affected_files": [
      "backend/app/crm/routes.py",
      "backend/app/crm/service.py"
    ],

    "acceptance_criteria": [
      "API returns valid pipeline",
      "tests pass",
      "existing lead APIs unaffected"
    ]
  }
}
```

Claude Code chỉ cần tập trung task hiện tại.

Không cần nhồi toàn bộ project context vào mỗi prompt.

---

# 48. Tránh Plan quá chi tiết

Plan Engine cũng không được biến thành bureaucracy.

Không nên tạo:

```text
Task:
Open file.

Task:
Read line 1.

Task:
Read line 2.
```

Mức task phù hợp:

> Một đơn vị công việc có output và success criteria riêng.

---

# 49. Progressive Planning

Đối với project lớn, không nhất thiết lập chi tiết 200 task ngay từ đầu.

Dùng:

```text
High-level Plan
      ↓
Detailed Current Milestone
      ↓
Execute
      ↓
Expand Next Milestone
```

Ví dụ:

```text
M1 Architecture
    → detailed

M2 Backend
    → summary

M3 Frontend
    → summary

M4 Deployment
    → summary
```

Khi M1 gần xong:

```text
expand M2
```

Điều này giảm:

* token;
* kế hoạch lỗi thời;
* assumptions;
* re-planning không cần thiết.

---

# 50. Plan Budget

Mỗi Plan có thể có:

```yaml
budget:

  max_steps:

  max_tool_calls:

  max_retries:

  max_tokens:

  max_duration:

  cost_limit:
```

Đặc biệt quan trọng khi Agent chạy tự động.

---

# 51. Failure Policy

Ví dụ:

```yaml
failure_policy:

  retry:
    max: 3

  after_retry:
    replan: true

  critical_failure:
    pause: true

  destructive_action:
    require_founder: true
```

---

# 52. Blocker

Nếu không thể tiếp tục:

```text
BLOCKED
```

thay vì Agent ngồi retry vô hạn.

Ví dụ:

```yaml
blocker:

  type:
    missing_credential

  description:
    Hostinger VPS SSH key unavailable

  resolution:
    Founder must configure VPS credentials
```

Hologram hiển thị:

```text
⚠ Waiting for Founder
```

---

# 53. Memory Integration

Không lưu toàn bộ execution vào conversational memory.

Phân tầng:

```text
PLAN DATABASE
→ execution truth

EVENT LOG
→ operational history

EVIDENCE
→ proof

MEMORY
→ useful long-term knowledge
```

Ví dụ sau project:

```text
"Company prefers Next.js landing pages."
```

có thể trở thành memory.

Nhưng:

```text
"tool call #147 returned timeout"
```

chỉ nên nằm Event Log.

---

# 54. Local-first

Plan Engine phải hoạt động hoàn toàn với dữ liệu Company local.

Các dữ liệu:

```text
plans
tasks
events
evidence
agent execution
project context
```

thuộc database của Company.

Không yêu cầu COSA server trung tâm phải đọc nội dung Plan của doanh nghiệp.

Server trung tâm nếu có chỉ nên quản lý những metadata phù hợp với mô hình license.

---

# 55. Security

Mỗi task trước khi thực thi:

```text
Task
 ↓
Agent Permission
 ↓
Tool Permission
 ↓
Company Policy
 ↓
Risk Classification
 ↓
Execute
```

Không dựa riêng vào prompt.

---

# 56. Agent không tự cấp quyền

Nếu Plan cần:

```text
deployment
```

nhưng Agent không có permission:

```text
BLOCKED
```

hoặc:

```text
REQUEST_APPROVAL
```

Không tự tăng quyền.

---

# 57. Plan Analytics

Sau này COSA có thể phân tích:

```text
Plans created

Plans completed

Completion rate

Average duration

Tasks requiring re-plan

Most common blockers

Agent success rate

Tool failure rate

Founder intervention rate
```

Đây là dữ liệu rất giá trị để cải thiện Agent Runtime.

---

# 58. Tích hợp các phòng ban

Không tạo Plan Engine riêng cho từng phòng ban.

Dùng:

```text
CORE PLAN ENGINE
```

và domain-specific templates.

Ví dụ:

```text
Marketing Plan Template

Sales Plan Template

Finance Plan Template

Legal Plan Template

Product Plan Template

Coding Plan Template
```

---

# 59. Marketing Example

Founder:

> Chuẩn bị chiến dịch ra mắt sản phẩm A.

Plan:

```text
Goal

Launch Product A


M1 Context

- understand product
- customer segment
- positioning


M2 Research

- customer evidence
- competitors
- market signals


M3 Offer

- value proposition
- offer
- pricing


M4 Assets

- landing page
- content
- creatives


M5 Distribution

- channels
- campaign
- automation


M6 Measurement

- leads
- conversion
- CAC
- feedback


M7 Review

- results
- learnings
- next experiments
```

---

# 60. Coding Example

Founder:

> Tích hợp Plan Engine vào COSA.

Plan Engine có thể tự tạo:

```text
M1 — Inspect existing architecture

M2 — Database schema

M3 — Backend Plan Service

M4 — Planning prompts

M5 — Agent Runtime integration

M6 — Observe / Re-plan

M7 — Verification

M8 — Hologram UI

M9 — Tests

M10 — Migration & rollout
```

Đây chính là Plan mà tài liệu này đề xuất triển khai.

---

# 61. MVP triển khai

Không nên xây toàn bộ hệ thống ngay lập tức.

## Phase 1 — Plan Core

Triển khai:

```text
plans

milestones

tasks

success criteria

plan status

task status
```

Có:

```text
Create Plan

Start Plan

Task progression

Complete Plan
```

---

# 62. Phase 2 — Hologram

Thêm:

```text
Plan Card

Plan Detail

Progress

Current Task

Blockers

Timeline
```

---

# 63. Phase 3 — Execution Runtime

Thêm:

```text
Agent assignment

Tool execution

Observe

Retry

Failure

Evidence
```

---

# 64. Phase 4 — Re-plan

Thêm:

```text
Plan Version

Re-plan

Dependency adjustment

Dynamic task creation
```

---

# 65. Phase 5 — Verification

Thêm:

```text
Success Criteria

Verification

Automated checks

Founder approval
```

---

# 66. Phase 6 — Project Management Integration

Mapping:

```text
Plan
→ Project

Milestone
→ 12 Week Year / milestone

Task
→ Weekly Tactic / Task

Priority task
→ Daily Top 3
```

Không bắt buộc mọi Plan phải đưa vào 12 Week Year.

Chỉ những công việc chiến lược/phù hợp mới mapping.

---

# 67. Phase 7 — Advanced Planning

Sau khi core ổn định mới thêm:

```text
Plan templates

Plan analytics

Historical planning patterns

Agent performance

Cost optimization

Plan recommendation

Cross-agent planning
```

---

# 68. Không nên triển khai ngay

Không cần MVP đầu tiên có:

```text
multi-agent debate

complex DAG visual editor

AI-generated Gantt

automatic resource forecasting

hundreds of planning fields

full BPMN engine
```

COSA cần:

> **Plan → Execute → Observe → Re-plan → Verify**

hoạt động chắc chắn trước.

---

# 69. Acceptance Criteria tổng thể

Plan Engine chỉ xem là hoàn thành khi:

* [ ] Request được phân loại theo complexity.
* [ ] Level 2/3 có thể tạo Plan structured.
* [ ] Level 3 không tự execution trước Plan.
* [ ] Plan được lưu PostgreSQL.
* [ ] Plan có milestone.
* [ ] Milestone có task.
* [ ] Task có status.
* [ ] Task hỗ trợ dependency.
* [ ] Task có success criteria.
* [ ] Agent Runtime đọc task từ Plan.
* [ ] Tool result tạo Observation.
* [ ] Error có thể làm task `BLOCKED`.
* [ ] Hỗ trợ retry.
* [ ] Hỗ trợ `NEEDS_REPLAN`.
* [ ] Plan có version history.
* [ ] Completed task không bị mất khi re-plan.
* [ ] Có Evidence.
* [ ] Có Verification.
* [ ] Có Event Log.
* [ ] Hologram hiển thị progress.
* [ ] Founder thấy current task.
* [ ] Founder thấy blocker.
* [ ] Founder có thể Pause/Resume.
* [ ] Các action nhạy cảm hỗ trợ approval.
* [ ] Claude Code tuân thủ Plan trước khi sửa project lớn.

---

# 70. Kiến trúc COSA sau khi tích hợp

```text
                         FOUNDER
                            │
                            ▼
                   ┌─────────────────┐
                   │ COSA Co-founder │
                   └────────┬────────┘
                            │
                            ▼
                   UNDERSTAND ENGINE
                            │
                   ┌────────┴─────────┐
                   │                  │
              Simple Request     Complex Goal
                   │                  │
                   ▼                  ▼
             Direct Action       PLAN ENGINE
                                      │
            ┌─────────────────────────┼─────────────────────┐
            │                         │                     │
            ▼                         ▼                     ▼
         Context                  Milestones             Criteria
            │                         │                     │
            └─────────────────────────┼─────────────────────┘
                                      ▼
                              EXECUTION RUNTIME
                                      │
                       ┌──────────────┼──────────────┐
                       ▼              ▼              ▼
                    Agent           Tool            MCP
                       │              │              │
                       └──────────────┼──────────────┘
                                      ▼
                                   OBSERVE
                                      │
                           ┌──────────┴──────────┐
                           │                     │
                          OK                  PROBLEM
                           │                     │
                           ▼                     ▼
                      NEXT TASK              RE-PLAN
                           │                     │
                           └──────────┬──────────┘
                                      ▼
                                    VERIFY
                                      │
                                      ▼
                                   EVIDENCE
                                      │
                                      ▼
                                    RESULT
                                      │
                  ┌───────────────────┼──────────────────┐
                  ▼                   ▼                  ▼
                Chat               Artifact           Workflow
                  │
                  ▼
                            HOLOGRAM / PROJECT
```

---

# 71. Nguyên tắc kiến trúc cần chốt

## Principle 1

**Plan là first-class object.**

Không chỉ tồn tại trong context của LLM.

---

## Principle 2

**Complex task must be planned before execution.**

```text
NO PLAN → NO EXECUTION
```

---

## Principle 3

**Plan is living state.**

Có thể thay đổi dựa trên Observation.

---

## Principle 4

**Plan phải measurable.**

Không có Success Criteria thì chưa phải Plan hoàn chỉnh.

---

## Principle 5

**Agent execution phải tạo evidence.**

Không chấp nhận:

> Tôi đã làm xong.

mà không có bằng chứng tương ứng.

---

## Principle 6

**Verify before Complete.**

```text
Executed
≠
Completed
```

---

## Principle 7

**Human authority remains above Agent.**

COSA được quyền chủ động nhưng không vượt policy của Founder/Company.

---

## Principle 8

**One Plan Engine — Many Agents.**

Không xây một planning framework riêng cho Marketing, Sales, Finance, Coding...

---

## Principle 9

**Plan connects AI with execution management.**

```text
Founder Goal
→ Plan
→ Project
→ Milestone
→ Task
→ Agent
→ Evidence
→ Result
```

---

# 72. Kết luận

Plan Engine nên trở thành một trong những thành phần lõi nhất của COSA.

COSA không nên chỉ là:

> Founder hỏi → AI trả lời.

Mà phải tiến đến:

> Founder đưa ra mục tiêu → COSA hiểu mục tiêu → xây kế hoạch → chia nhỏ công việc → chọn Agent và công cụ → thực thi → quan sát → điều chỉnh kế hoạch → kiểm chứng bằng evidence → trả kết quả.

Khi đó COSA thực sự hoạt động như một **AI Co-founder có khả năng tổ chức và điều hành công việc**, thay vì chỉ là tập hợp nhiều AI Agent.

Kiến trúc mục tiêu:

```text
GOAL
 ↓
UNDERSTAND
 ↓
PLAN
 ↓
EXECUTE
 ↓
OBSERVE
 ↙       ↘
OK      RE-PLAN
 ↓         │
 └────┬────┘
      ↓
    VERIFY
      ↓
   EVIDENCE
      ↓
    RESULT
```

Và nguyên tắc nên được đưa vào core architecture của COSA:

> **Plan first. Execute second. Observe continuously. Re-plan when reality changes. Verify before claiming success.**
