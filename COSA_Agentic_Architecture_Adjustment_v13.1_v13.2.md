# COSA Agentic Architecture Adjustment
## Điều chỉnh COSA theo Agentic AI System Reference Architecture

**Tài liệu dành cho:** Claude Code / đội phát triển COSA  
**Mục tiêu:** Điều chỉnh kiến trúc COSA hiện tại theo mô hình Agentic AI có Orchestrator, Agent Runtime, Tools, Memory, Reliability, Governance và Observability nhưng **không viết lại hệ thống đang có**.  
**Baseline:** COSA v13.1 + v13.2  
**Ngày:** 2026-08-15  
**Trạng thái:** Implementation Specification

---

# 1. Mục tiêu điều chỉnh

COSA đã phát triển theo hướng Founder OS / One Person Company với các năng lực AI, workflow, tài chính, sales, knowledge và automation. Kiến trúc mới không thay đổi định hướng sản phẩm mà chuẩn hóa hệ thống theo một Agentic AI Reference Architecture để COSA có thể:

1. Nhận **Goal** thay vì chỉ nhận prompt.
2. Phân rã Goal thành kế hoạch có kiểm soát.
3. Chọn đúng domain/capability để xử lý.
4. Gọi tool, workflow và external systems theo policy.
5. Duy trì state, context và business memory.
6. Ghi lại toàn bộ execution trace.
7. Retry/fallback khi lỗi.
8. Yêu cầu founder phê duyệt các hành động quan trọng.
9. Đo lường hiệu quả, chi phí, latency và kết quả.
10. Học từ lịch sử hoạt động mà không để AI tự ý thay đổi business truth.

Kiến trúc này phải giữ nguyên nguyên tắc:

> **AI được quyền nghiên cứu, suy luận, đề xuất và chuẩn bị hành động; quyền thực thi phụ thuộc policy và approval.**

---

# 2. Nguyên tắc không được phá vỡ

## 2.1 Không rewrite COSA v13

COSA v13 đã triển khai.

V13.1 là **incremental/additive Company Runtime Adjustment**.  
V13.2 tiếp tục bổ sung Revenue & Sales.

Do đó tài liệu này là:

> **Agentic Architecture Adjustment cho v13.1/v13.2**

Không tạo COSA v14 chỉ để đổi kiến trúc.

Không viết lại backend, frontend hoặc database nếu không cần thiết.

---

## 2.2 Không bật lại các module đang disable

Nếu Strategy hoặc module cũ đang được disable trong runtime hiện tại thì:

- không tự động re-enable;
- không thay đổi routing hiện tại chỉ vì kiến trúc mới có khái niệm Planning;
- Strategic concepts chỉ được dùng làm context/data model khi cần;
- việc bật lại module phải là quyết định sản phẩm riêng.

---

## 2.3 Giữ stack hiện tại

Kiến trúc mục tiêu:

```text
Flutter + GetX
      │
      ▼
FastAPI / brain-api
      │
      ├── PostgreSQL + pgvector
      ├── Agent Gateway
      ├── Agent Worker
      ├── n8n Gateway
      ├── LiveKit Gateway
      └── OpenSandbox Adapter
```

Không chuyển backend sang TypeScript.

Không thay PostgreSQL bằng một database agent riêng.

Không đưa business state vào DeepSeek Harness.

---

## 2.4 Local-first nhưng không local-only

COSA cần hỗ trợ:

- Desktop chạy local.
- Docker Compose cho backend local.
- PostgreSQL local hoặc customer-managed.
- MinIO/S3 private storage.
- n8n của khách hàng.
- provider AI configurable.
- mobile kết nối COSA runtime qua API.

Local-first có nghĩa:

> Hệ thống có thể chạy độc lập trên hạ tầng của khách hàng, không có nghĩa mọi model hoặc integration phải chạy local.

---

# 3. Kiến trúc COSA mới: 7 Layer

Reference Architecture gốc có 9 nhóm. Với COSA, rút gọn thành 7 layer để tránh over-engineering.

```text
┌──────────────────────────────────────────────────────┐
│ 1. EXPERIENCE LAYER                                  │
│ Flutter Desktop / Mobile / Chat / Voice / API       │
├──────────────────────────────────────────────────────┤
│ 2. COSA CONTROL PLANE                                │
│ Goal → Plan → Route → Policy → Execute → Evaluate   │
├──────────────────────────────────────────────────────┤
│ 3. DOMAIN AGENT LAYER                                │
│ Founder / Finance / Sales / Marketing / Legal ...   │
├──────────────────────────────────────────────────────┤
│ 4. TOOL & WORKFLOW LAYER                             │
│ Native Tools / n8n / OpenSandbox / Search / APIs    │
├──────────────────────────────────────────────────────┤
│ 5. MEMORY & KNOWLEDGE LAYER                          │
│ Context / Business Memory / Knowledge / Events      │
├──────────────────────────────────────────────────────┤
│ 6. TRUST & OPERATIONS LAYER                          │
│ Policy / Approval / Audit / Retry / Observability   │
├──────────────────────────────────────────────────────┤
│ 7. AI & DATA INFRASTRUCTURE                          │
│ PostgreSQL / pgvector / LLM Gateway / Redis opt.    │
└──────────────────────────────────────────────────────┘
```

---

# 4. Experience Layer

Experience Layer giữ Flutter + GetX.

## 4.1 Các channel

```text
Flutter Desktop
Flutter Mobile
Chat
Voice
Notification Center
Agent Activity
Approval Inbox
API
```

Voice sử dụng LiveKit theo kiến trúc hiện tại.

LiveKit chỉ xử lý realtime communication/session.

Không dùng LiveKit làm Agent Runtime.

---

## 4.2 UI mới cần bổ sung

### A. Command Center

Màn hình chính cho founder.

Hiển thị:

- Goals đang hoạt động.
- Plans đang chạy.
- Agent jobs.
- Approval chờ xử lý.
- Important events.
- Sales alerts.
- Finance alerts.
- Failed jobs.
- System health.

---

### B. Agent Activity

Hiển thị timeline:

```text
08:30 Goal received
08:30 COSA Planner created 4 steps
08:31 Sales capability querying CRM
08:31 Research capability searching market
08:33 Reasoning completed
08:34 Outreach drafts generated
08:34 Waiting for approval
```

Mỗi event phải có:

- timestamp;
- run_id;
- agent/domain;
- capability;
- tool;
- model;
- status;
- duration;
- token/cost nếu có;
- approval state.

---

### C. Approval Inbox

Founder xử lý:

```text
Approve
Edit
Reject
Approve once
Approve for this workflow
```

Không tạo approval popup rải rác.

Tập trung về một Approval Inbox.

---

# 5. COSA Control Plane

Control Plane là thay đổi quan trọng nhất.

Không để Flutter gọi trực tiếp domain agent.

Mọi yêu cầu agentic đi qua:

```text
Agent Gateway
    ↓
Goal Interpreter
    ↓
Context Resolver
    ↓
Task Decomposer
    ↓
Planner
    ↓
Policy Evaluator
    ↓
Agent/Capability Router
    ↓
Execution Manager
    ↓
Evaluator
```

---

# 6. Goal Object

Không coi mọi message là goal.

Phân biệt:

```text
CHAT
QUERY
COMMAND
GOAL
EVENT
```

Ví dụ:

**CHAT**

> Chào COSA.

Không tạo workflow.

**QUERY**

> Doanh thu tuần này bao nhiêu?

Chỉ query data.

**COMMAND**

> Tạo báo cáo sales tuần này.

Tạo một execution ngắn.

**GOAL**

> Trong 6 tuần tăng pipeline sales lên 500 triệu.

Cần planner, task decomposition, tracking.

---

## 6.1 Goal schema đề xuất

```json
{
  "id": "goal_xxx",
  "company_id": "company_xxx",
  "project_id": null,
  "type": "business_goal",
  "title": "Increase sales pipeline",
  "description": "...",
  "target": {
    "metric": "pipeline_value",
    "value": 500000000,
    "currency": "VND"
  },
  "deadline": "2026-09-30",
  "status": "active",
  "created_by": "user_xxx",
  "created_at": "..."
}
```

Goal không thay thế OKR hoặc 12WY.

Goal là entry point của Agentic Runtime.

Nếu module OKR/12WY đang được sử dụng thì goal có thể link đến chúng.

---

# 7. Context Resolver

Đây là thành phần bắt buộc.

Một câu hỏi như:

> “Tuần này sao rồi?”

không được gửi trực tiếp cho model.

Context Resolver phải xác định:

```text
User
Company
Current Project
Current Cycle
Current Week
Active Sales pipeline
Relevant Finance period
Recent agent runs
Pending approvals
```

---

## 7.1 Context Envelope

Mọi agent run nhận một Context Envelope thống nhất:

```json
{
  "user": {},
  "company": {},
  "project": {},
  "goal": {},
  "cycle": {},
  "time_context": {},
  "permissions": [],
  "recent_events": [],
  "memory_refs": [],
  "knowledge_refs": []
}
```

Không gửi toàn bộ database vào prompt.

Context Resolver chỉ lấy dữ liệu cần thiết.

---

# 8. Task Decomposition

Planner phải phân rã goal thành step.

Ví dụ:

> Tăng pipeline lên 500 triệu.

Có thể sinh:

```text
1. Audit current sales pipeline
2. Define ICP
3. Find prospects
4. Score prospects
5. Prepare outreach
6. Request approval
7. Execute outreach
8. Track reply
9. Update CRM
10. Evaluate conversion
```

Mỗi step có:

```text
input
expected_output
domain
capability
tool
policy_level
dependency
status
```

---

# 9. Agent Architecture: Domain Agent + Capability

Không xây hàng chục agent nhỏ.

COSA sử dụng mô hình hybrid.

## 9.1 Domain Agent

Domain Agent đại diện chuyên môn.

Ví dụ:

```text
Founder / Chief of Staff
Finance
Sales
Marketing
Legal
Learning
Operations
```

Chỉ enable agent/domain thực sự cần ở runtime hiện tại.

---

## 9.2 Shared Capability

Các capability dùng chung:

```text
Research
Reasoning
Data
Action
Communication
Evaluation
```

Ví dụ Sales Agent:

```text
Sales Domain
 ├── Research
 ├── Reasoning
 ├── Data
 ├── Communication
 ├── Action
 └── Evaluation
```

Finance cũng dùng cùng capability runtime nhưng với:

- prompt/policy riêng;
- tools riêng;
- data permissions riêng;
- knowledge riêng.

---

# 10. Không tạo Agent Explosion

Không tạo:

```text
SearchAgent
WebAgent
EmailAgent
CRMReadAgent
CRMWriteAgent
LeadAgent
LeadScoreAgent
ReportAgent
PDFAgent
...
```

Những phần trên phải là:

- capability;
- tool;
- skill;
- workflow;
- adapter.

Agent chỉ tồn tại khi có:

1. domain responsibility rõ;
2. business policy khác;
3. memory/context khác;
4. tool permission khác;
5. evaluation criteria khác.

---

# 11. Chief of Staff / Founder Agent

Đây là domain điều phối cấp business.

Không thay thế Control Plane.

Phân biệt:

```text
Control Plane = deterministic system orchestration
Chief of Staff = AI business reasoning role
```

Chief of Staff có thể:

- tổng hợp Finance + Sales + Marketing;
- đưa ra recommendation;
- tạo plan draft;
- đánh giá progress;
- chuẩn bị Weekly Review;
- đề xuất next action.

Không được:

- tự approve;
- tự thay đổi financial record;
- tự kích hoạt external high-impact action.

---

# 12. DeepSeek Harness Integration

DeepSeek Harness được sử dụng như **Agent Runtime**, không phải business backend.

Kiến trúc:

```text
Flutter
  ↓
FastAPI
  ↓
Agent Gateway
  ↓
COSA Runtime Adapter
  ↓
DeepSeek Harness
```

---

## 12.1 Harness chịu trách nhiệm

- session execution;
- runtime plugin;
- tool invocation lifecycle;
- execution history;
- resume;
- replay;
- fork/debug nếu cần;
- skill/runtime composition.

---

## 12.2 Harness không chịu trách nhiệm

Không lưu truth của:

```text
Company
User
Finance
Sales
Customer
Lead
Deal
Task
Approval
Policy
Business Memory
Knowledge ownership
```

Nguồn chuẩn vẫn là PostgreSQL COSA.

---

## 12.3 Session ≠ Business Memory

Đây là rule bắt buộc:

```text
Harness Session
    !=
COSA Memory
```

Harness session là execution memory.

COSA Memory là business memory.

Không query business knowledge từ Harness session history.

---

# 13. Tool & Workflow Layer

Tools chia hai nhóm.

## 13.1 Native Tools

Các tool quan trọng, cần kiểm soát chặt:

```text
PostgreSQL query
Knowledge retrieval
File read/write
OpenSandbox execution
Internal finance operations
Internal sales operations
Internal approval
Internal audit
```

---

## 13.2 External Workflow Tools

Đưa qua n8n:

```text
Gmail
Telegram
Zalo
CRM ngoài
Google services
Facebook
X
Threads
Webhook
Other SaaS
```

COSA không xây lại n8n.

---

# 14. n8n Gateway

Kiến trúc:

```text
Agent
  ↓
Action Capability
  ↓
Tool Registry
  ↓
Policy Check
  ↓
Approval if required
  ↓
n8n Gateway
  ↓
Customer n8n
  ↓
External system
```

COSA quản lý:

- workflow registry;
- allowed workflow;
- parameters;
- permission;
- execution status;
- audit event.

n8n quản lý:

- connector;
- credential;
- external API logic;
- retries ở workflow level.

---

# 15. OpenSandbox

OpenSandbox chỉ dành cho code/file/process cần sandbox.

Ví dụ:

```text
Python analysis
CSV processing
document conversion
temporary scripts
generated reports
safe code execution
```

Không cho agent chạy arbitrary command trực tiếp trên host.

Flow:

```text
Agent
 ↓
Code Execution Capability
 ↓
Policy
 ↓
OpenSandbox
 ↓
Artifact/result
 ↓
COSA storage
```

---

# 16. Tool Registry

Tạo registry thống nhất.

Ví dụ:

```yaml
tool:
  id: sales.crm.read
  domain: sales
  action: read
  risk: low
  approval: false

tool:
  id: communication.email.send
  domain: communication
  action: external_write
  risk: medium
  approval: conditional

tool:
  id: finance.payment.execute
  domain: finance
  action: financial_write
  risk: critical
  approval: always
```

Agent không tự quyết định tool permission.

---

# 17. Memory & Knowledge Architecture

COSA chia memory thành 5 loại.

```text
1. Working Memory
2. Business Memory
3. Knowledge Base
4. Episodic/Event Memory
5. Profile Memory
```

---

## 17.1 Working Memory

Ngắn hạn.

Bao gồm:

- current conversation;
- current plan;
- current run;
- tool result.

Có TTL.

Không coi là business truth.

---

## 17.2 Business Memory

Thông tin cần nhớ lâu:

```text
company facts
founder preferences
product facts
customers
sales context
operating constraints
approved decisions
```

Business Memory phải có provenance.

---

## 17.3 Knowledge Base

Tài liệu:

```text
PDF
DOC
MD
SOP
laws
manuals
product docs
internal docs
```

Lưu metadata PostgreSQL.

Vector search dùng pgvector.

Không cần vector database riêng ở giai đoạn này.

---

## 17.4 Episodic Memory

Event log:

```text
agent_run_started
agent_run_completed
tool_called
approval_requested
approval_granted
email_sent
lead_created
deal_updated
report_generated
error_occurred
```

Đây là cơ sở cho:

- timeline;
- analytics;
- replay;
- learning.

---

## 17.5 Profile Memory

Bao gồm:

```text
User Profile
Company Profile
Organization Settings
AI Preferences
Language
Timezone
Approval Defaults
Provider Preferences
```

---

# 18. Event Model

Tạo `agent_events`.

Tối thiểu:

```text
id
company_id
run_id
plan_id
step_id
event_type
actor_type
actor_id
tool_id
payload
status
created_at
```

Payload dùng JSONB.

Không lưu secret.

---

# 19. Execution Model

Mọi workflow agentic phải có ID chain:

```text
goal_id
plan_id
run_id
step_id
tool_call_id
approval_id
event_id
```

Nhờ vậy có thể trace toàn bộ.

---

# 20. Agent Run State Machine

```text
CREATED
  ↓
PLANNING
  ↓
READY
  ↓
RUNNING
  ↓
WAITING_TOOL
  ↓
WAITING_APPROVAL
  ↓
RUNNING
  ↓
EVALUATING
  ↓
COMPLETED
```

Error path:

```text
RUNNING
  ↓
FAILED
  ↓
RETRYING
  ↓
RUNNING
```

Hoặc:

```text
FAILED
  ↓
FALLBACK
  ↓
RUNNING
```

Cuối cùng:

```text
FAILED_FINAL
```

---

# 21. Governance Model

Chuẩn hóa permission thành 4 level.

```text
L0 READ
L1 SUGGEST
L2 DRAFT
L3 EXECUTE
```

Có thêm:

```text
L3A EXECUTE_WITH_APPROVAL
```

Để implementation dễ hiểu:

| Level | Quyền |
|---|---|
| L0 | đọc/query |
| L1 | phân tích/đề xuất |
| L2 | tạo draft |
| L3A | thực thi sau approval |
| L3 | thực thi tự động trong policy |

---

# 22. Default policy

## Read

```text
database read
knowledge search
analytics
```

=> Auto.

## Suggest

```text
recommendation
plan
forecast
lead score
```

=> Auto.

## Draft

```text
email draft
social content
proposal
report
```

=> Auto.

## External write

```text
send email
post social
update third-party CRM
```

=> Approval hoặc policy whitelist.

## Financial / Legal critical

```text
payment
signing
official filing
deleting accounting data
```

=> Human approval bắt buộc.

---

# 23. Approval Object

```json
{
  "id": "approval_xxx",
  "company_id": "company_xxx",
  "run_id": "run_xxx",
  "action": "communication.email.send",
  "risk_level": "medium",
  "request_payload": {},
  "status": "pending",
  "requested_at": "...",
  "resolved_by": null,
  "resolved_at": null
}
```

Approval luôn ghi audit event.

---

# 24. Reliability Layer

COSA phải coi LLM/tool là unreliable dependency.

## 24.1 Retry

Retry cho:

```text
timeout
429
temporary 5xx
network error
temporary n8n failure
```

Không retry blind đối với:

```text
invalid request
permission denied
policy denied
approval rejected
business validation error
```

---

## 24.2 Backoff

Ví dụ:

```text
2s
5s
15s
30s
```

Có max retry.

---

## 24.3 Fallback

Fallback phải explicit.

Ví dụ:

```text
Primary model
 ↓ failed
Fallback provider
```

Không tự dùng account subscription hoặc OAuth của Claude/ChatGPT như một token pool cho background job.

Provider/model phải configurable và log được.

---

## 24.4 Circuit Breaker

Nếu một connector fail liên tục:

```text
CLOSED
 ↓
OPEN
 ↓
HALF_OPEN
 ↓
CLOSED
```

Khi OPEN:

- ngừng gọi connector;
- tạo system alert;
- không spam retry;
- có thể route alternate connector nếu policy cho phép.

---

# 25. Human-in-the-loop

HITL không phải trường hợp ngoại lệ.

Nó là thành phần chính của COSA.

COSA cần hỗ trợ:

```text
AI → Draft → Human → Execute
AI → Plan → Human → Activate
AI → Detect risk → Human
AI → Exception → Human
```

---

# 26. Observability

Tạo Agent Observability.

## Metrics tối thiểu

```text
runs_total
runs_success
runs_failed
average_latency
tool_calls
tool_errors
tokens_in
tokens_out
estimated_cost
approval_wait_time
retry_count
fallback_count
```

---

## 26.1 Trace

Một trace hiển thị:

```text
User request
 ↓
Intent classifier
 ↓
Context Resolver
 ↓
Planner
 ↓
Sales Domain
 ↓
CRM Tool
 ↓
Reasoning
 ↓
Draft
 ↓
Approval
 ↓
n8n
```

---

# 27. Audit

Audit khác log.

Audit phải immutable theo logic ứng dụng.

Audit lưu:

```text
who
what
when
before
after
reason
approval
source
```

Đặc biệt cho:

```text
finance
sales customer data
permission
external communication
configuration
agent policy
```

---

# 28. Model Gateway

Không để từng agent gọi provider trực tiếp.

Tất cả qua:

```text
Model Gateway
```

Gateway chịu trách nhiệm:

```text
model routing
provider config
timeout
retry
fallback
cost tracking
rate limit
logging
redaction
```

---

# 29. Model Profiles

Không hard-code model theo agent.

Ví dụ:

```yaml
profiles:
  chat_fast:
    provider: deepseek

  reasoning:
    provider: configurable

  extraction:
    provider: configurable

  local_embedding:
    provider: local
```

Agent tham chiếu `model_profile`.

Không tham chiếu trực tiếp model string trong business logic.

---

# 30. Data Architecture

PostgreSQL vẫn là source of truth.

Các table mới nên additive.

Đề xuất:

```text
agent_goals
agent_plans
agent_plan_steps
agent_runs
agent_events
agent_tool_calls
agent_approvals
agent_policies
agent_memories
agent_memory_links
agent_metrics
tool_registry
workflow_registry
```

Không cần tạo database mới chỉ vì agentic architecture.

---

# 31. Queue / Worker

Nếu agent job dài, không giữ HTTP request.

Flow:

```text
Flutter
 ↓
POST /agent/runs
 ↓
FastAPI
 ↓
enqueue
 ↓
agent-worker
 ↓
runtime
```

Flutter nhận:

```text
run_id
status
```

Sau đó:

- polling;
- SSE;
- WebSocket;

tùy hạ tầng hiện tại.

Không bắt buộc Kafka.

---

# 32. Không over-engineer event bus

Giai đoạn hiện tại:

```text
PostgreSQL + worker queue
```

là đủ nếu tải chưa lớn.

Chỉ thêm Redis/RabbitMQ/Kafka khi có requirement thực tế.

Không triển khai Kafka chỉ để giống enterprise reference architecture.

---

# 33. Sales Agent 적용

Sales là domain phù hợp nhất để thử Agentic Runtime.

Flow mẫu:

```text
Goal:
"Tạo thêm 50 qualified leads trong tháng này"
        ↓
Planner
        ↓
Sales Domain
        ↓
Research capability
        ↓
Data capability
        ↓
Lead qualification
        ↓
Communication capability
        ↓
Draft outreach
        ↓
Approval
        ↓
n8n
        ↓
Send / CRM update
        ↓
Event tracking
        ↓
Evaluation
```

---

# 34. Sales Evaluator

Không đánh giá bằng cảm tính.

Metrics:

```text
new_leads
qualified_leads
contacted
reply_rate
meeting_rate
opportunity_rate
pipeline_value
win_rate
revenue
```

Agent learning chỉ được dùng để đề xuất thay đổi.

Không tự thay đổi sales policy.

---

# 35. Finance Agent 적용

Finance Agent dùng Agentic Runtime để:

```text
query
analyze
forecast
detect anomalies
prepare report
draft accounting action
```

Không tự:

```text
approve payment
post critical accounting entry
delete records
change accounting policy
```

Nếu Finance hiện đang theo TT58 thì policy/validation hiện tại vẫn là source of truth.

Agent chỉ đứng trên service đó.

---

# 36. Marketing Agent 적용

Marketing có thể:

```text
research
create campaign hypothesis
generate content
prepare campaign
measure
recommend
```

External posting:

```text
AI draft
 ↓
approval/policy
 ↓
n8n
 ↓
channel
```

---

# 37. Legal Agent 적용

Legal chỉ nên:

```text
research
compare
extract
summarize
draft
flag risks
```

Các quyết định pháp lý cuối cùng cần human verification.

Không cho Legal Agent tự ký hoặc nộp hồ sơ.

---

# 38. Learning Agent 적용

Learning Agent nên liên kết:

```text
Goal
Skill gap
Knowledge
Learning task
Reflection
Evidence
```

Không tách thành một chatbot độc lập.

Learning là một domain trong Founder OS.

---

# 39. Communication Agent không cần độc lập

Communication nên là shared capability.

Ví dụ:

```text
Sales → Communication → email
Finance → Communication → report
Founder → Communication → summary
Marketing → Communication → post
```

Như vậy tránh agent explosion.

---

# 40. Event-driven Agent

COSA cần hỗ trợ trigger từ event.

Ví dụ:

```text
deal.updated
invoice.overdue
lead.replied
task.failed
workflow.failed
weekly.review_due
```

Flow:

```text
Event
 ↓
Rule
 ↓
Policy
 ↓
Agent Run
```

Không phải event nào cũng gọi LLM.

Rule deterministic trước.

---

# 41. Agent Scheduler

Scheduler chỉ dùng khi cần:

```text
daily summary
weekly review
follow-up
sales check
finance check
knowledge refresh
```

Scheduler tạo event/job.

Không embed cron logic bên trong prompt.

---

# 42. Learning Loop

Không làm "AI tự học" bằng cách tự sửa prompt production.

Learning loop:

```text
Execute
 ↓
Observe
 ↓
Measure
 ↓
Evaluate
 ↓
Generate learning
 ↓
Propose change
 ↓
Human approve
 ↓
Update prompt/policy/workflow
```

Mọi thay đổi production phải versioned/audited.

---

# 43. PDCA Mapping

Agentic loop của COSA:

```text
PLAN
Goal → Context → Plan

DO
Agent → Tool → Execution

CHECK
Metrics → Events → Evaluator

ACT
Recommendation → Approval → Adjustment
```

Đây là implementation tự nhiên của PDCA.

---

# 44. 12 Week Year Mapping

Nếu module 12WY đang enable:

```text
12WY Goal
 ↓
Weekly target
 ↓
Agent plan
 ↓
Weekly action
 ↓
Score
 ↓
Weekly review
```

Week 13:

```text
Results
Lessons
What worked
What failed
Celebration
Next cycle proposal
```

Agent không tự tạo cycle mới nếu founder chưa approve.

---

# 45. API đề xuất

## Goal

```text
POST /api/agent/goals
GET  /api/agent/goals
GET  /api/agent/goals/{id}
PATCH /api/agent/goals/{id}
```

## Runs

```text
POST /api/agent/runs
GET  /api/agent/runs/{id}
POST /api/agent/runs/{id}/cancel
POST /api/agent/runs/{id}/retry
```

## Plans

```text
GET /api/agent/plans/{id}
POST /api/agent/plans/{id}/approve
```

## Approval

```text
GET  /api/approvals
POST /api/approvals/{id}/approve
POST /api/approvals/{id}/reject
```

## Events

```text
GET /api/agent/runs/{id}/events
```

---

# 46. Python module structure đề xuất

```text
app/
├── agentic/
│   ├── gateway/
│   ├── control_plane/
│   │   ├── intent.py
│   │   ├── context.py
│   │   ├── planner.py
│   │   ├── router.py
│   │   ├── execution.py
│   │   └── evaluator.py
│   │
│   ├── domains/
│   │   ├── founder/
│   │   ├── finance/
│   │   ├── sales/
│   │   ├── marketing/
│   │   ├── legal/
│   │   └── learning/
│   │
│   ├── capabilities/
│   │   ├── research/
│   │   ├── reasoning/
│   │   ├── data/
│   │   ├── action/
│   │   ├── communication/
│   │   └── evaluation/
│   │
│   ├── tools/
│   ├── memory/
│   ├── policies/
│   ├── approvals/
│   ├── observability/
│   ├── runtime/
│   │   └── deepseek_harness/
│   └── events/
```

Không bắt buộc di chuyển code cũ ngay.

Có thể tạo facade/adapter và migrate dần.

---

# 47. Runtime Adapter Interface

Không cho business code phụ thuộc DeepSeek Harness trực tiếp.

```python
class AgentRuntime:
    async def start_run(...):
        ...

    async def resume_run(...):
        ...

    async def cancel_run(...):
        ...

    async def get_status(...):
        ...
```

Implementation:

```text
DeepSeekHarnessRuntime
```

Sau này có thể thêm runtime khác mà không sửa business domain.

---

# 48. Tool Adapter Interface

```python
class ToolAdapter:
    async def execute(context, params):
        ...
```

Implementation:

```text
PostgresTool
N8nTool
OpenSandboxTool
WebSearchTool
FileTool
```

Tool luôn đi qua:

```text
permission
policy
validation
audit
```

---

# 49. Security

## Secret

Không lưu API key trong:

```text
Flutter
SQLite
prompt
agent memory
event payload
logs
```

Secret chỉ ở:

```text
server secret store
customer environment
n8n credential store
```

---

## 49.1 Data boundaries

Mọi query phải scope theo:

```text
user_id
company_id
workspace_id
```

Agent không có bypass quyền.

Tool call sử dụng server-side identity/context.

---

# 50. PII Protection

Trước khi gửi provider ngoài:

1. xác định data class;
2. redact nếu policy yêu cầu;
3. không gửi secret;
4. log model/provider;
5. log purpose;
6. lưu trace reference nhưng không lưu dữ liệu nhạy cảm dư thừa.

---

# 51. Prompt Governance

Prompt production được quản lý như configuration.

Mỗi prompt có:

```text
id
domain
capability
version
status
created_at
approved_by
```

Không cho agent tự overwrite system prompt.

---

# 52. Failure UX

Founder không được thấy:

> Internal server error.

Thay bằng:

```text
Sales research failed at Web Search step.
Reason: provider timeout.
Retry: 2/3.
Next: automatic retry in 15s.
```

Nếu fail final:

```text
[Retry]
[Use alternate provider]
[Open details]
```

Alternate provider chỉ hiển thị nếu configured.

---

# 53. Cost Control

Mỗi run ghi:

```text
provider
model
tokens
estimated_cost
tool_cost
duration
```

Có budget:

```text
per run
per day
per company
per domain
```

Khi vượt budget:

```text
pause
notify
request approval
```

---

# 54. Definition of "Autonomous"

COSA không dùng từ autonomous cho mọi agent.

Phân loại:

```text
Assistant
Copilot
Supervised Agent
Autonomous within policy
```

Default COSA:

> **Supervised Agent**

Chỉ task low-risk, repeatable và fully bounded mới cho autonomous within policy.

---

# 55. Phase triển khai

## Phase A — Control Plane Foundation

Triển khai:

```text
goal
run
plan
step
event
context resolver
policy
approval
```

Chưa cần multi-agent phức tạp.

### DoD

- user tạo goal;
- planner tạo steps;
- run có timeline;
- mỗi step có status;
- approval hoạt động;
- events được ghi.

---

## Phase B — Sales Pilot

Sales được chọn làm domain pilot.

Triển khai:

```text
Sales domain
Research
Data
Reasoning
Communication
Action
Evaluator
```

Tích hợp n8n.

### DoD

Một founder request có thể chạy end-to-end:

```text
find leads
→ qualify
→ draft outreach
→ approval
→ n8n
→ event
→ CRM update
→ metrics
```

---

## Phase C — Finance Integration

Bọc Finance hiện tại bằng Agentic layer.

Không rewrite finance engine.

### DoD

AI có thể:

- query;
- explain;
- forecast;
- identify anomaly;
- prepare action draft;
- request approval.

---

## Phase D — DeepSeek Harness Runtime

Đưa Harness vào sau AgentRuntime adapter.

### DoD

- run start;
- session map;
- tool invocation;
- resume;
- failure handling;
- trace link.

Business memory vẫn PostgreSQL.

---

## Phase E — OpenSandbox

Đưa code/file execution vào sandbox.

### DoD

- no host arbitrary execution;
- artifact captured;
- timeout;
- resource limit;
- audit.

---

## Phase F — Observability

Tạo:

```text
Agent Activity
Run Details
Metrics
Failure Dashboard
```

---

## Phase G — Other Domains

Enable dần:

```text
Marketing
Legal
Learning
Operations
```

Không enable tất cả cùng lúc.

---

# 56. Những thứ chưa nên triển khai

Không cần ở giai đoạn này:

```text
Kafka
separate vector DB
Kubernetes-only architecture
full autonomous multi-agent society
agent-to-agent free conversation
AI self-modifying production prompts
AI self-changing policy
distributed microservices per agent
custom replacement for n8n
custom realtime stack replacing LiveKit
```

---

# 57. Migration strategy

Không migrate big bang.

## Step 1

Tạo `agentic/` module.

## Step 2

Tạo Agent Gateway.

## Step 3

Bọc các function hiện tại thành tools.

## Step 4

Tạo Control Plane.

## Step 5

Pilot Sales.

## Step 6

Thêm Harness adapter.

## Step 7

Thêm Observability.

## Step 8

Migrate domain khác khi có use case.

---

# 58. Mapping kiến trúc cũ → mới

| Hiện tại | Agentic Architecture |
|---|---|
| Chat request | Intent / Goal |
| AI Router | Model Gateway |
| Agent service | Domain Agent |
| Function | Capability / Tool |
| n8n | External Workflow Gateway |
| PostgreSQL | Business Truth |
| pgvector | Knowledge Retrieval |
| Chat history | Working Memory |
| Audit log | Episodic / Audit |
| DeepSeek Harness | Agent Runtime |
| OpenSandbox | Execution Sandbox |
| LiveKit | Realtime Experience |
| Approval | Governance / HITL |

---

# 59. Reference flow hoàn chỉnh

```text
FOUNDER
   │
   ▼
Flutter / Voice
   │
   ▼
Agent Gateway
   │
   ▼
Intent
   │
   ├─ Chat → Chat Runtime
   ├─ Query → Data capability
   ├─ Command → Short run
   └─ Goal
        │
        ▼
Context Resolver
        │
        ▼
Planner
        │
        ▼
Policy Engine
        │
        ▼
Domain Router
        │
        ▼
Domain Agent
        │
        ├─ Research
        ├─ Reasoning
        ├─ Data
        ├─ Communication
        ├─ Action
        └─ Evaluation
        │
        ▼
Tool Registry
   ┌────┼───────────┬──────────────┐
   │    │           │              │
   ▼    ▼           ▼              ▼
 DB    n8n     OpenSandbox      Search
   │
   ▼
Event / Audit
   │
   ▼
Memory Update
   │
   ▼
Metrics
   │
   ▼
Founder
```

---

# 60. COSA Agentic Loop

Đây là loop chuẩn nên dùng toàn hệ thống:

```text
GOAL
 ↓
CONTEXT
 ↓
PLAN
 ↓
POLICY
 ↓
EXECUTE
 ↓
OBSERVE
 ↓
EVALUATE
 ↓
LEARN
 ↓
RECOMMEND NEXT ACTION
```

Không cho `LEARN` ghi thẳng vào policy hoặc prompt production.

---

# 61. Kiến trúc cuối cùng đề xuất

```text
                       ┌──────────────────────────┐
                       │      COSA EXPERIENCE     │
                       │ Flutter / Chat / Voice   │
                       └────────────┬─────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │      COSA CONTROL PLANE      │
                    │ Intent / Context / Planner   │
                    │ Router / Policy / Executor   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────┴───────────────┐
                    │                              │
                    ▼                              ▼
          ┌───────────────────┐          ┌────────────────────┐
          │   DOMAIN AGENTS   │          │  SHARED CAPABILITY │
          │ Founder           │          │ Research           │
          │ Finance           │          │ Reasoning          │
          │ Sales             │          │ Data               │
          │ Marketing         │          │ Communication      │
          │ Legal             │          │ Action             │
          │ Learning          │          │ Evaluation         │
          └─────────┬─────────┘          └─────────┬──────────┘
                    └────────────────┬──────────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │   TOOL REGISTRY   │
                           └─────────┬─────────┘
                                     │
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
            ▼                        ▼                        ▼
        Native                  n8n Gateway              OpenSandbox
        Tools
            │
            ▼
   PostgreSQL / Knowledge
            │
            ▼
     MEMORY + EVENT STORE
            │
            ▼
 POLICY / APPROVAL / AUDIT
            │
            ▼
       OBSERVABILITY
```

DeepSeek Harness nằm bên dưới Control Plane như runtime adapter, không thay Control Plane.

---

# 62. Thứ tự ưu tiên thực tế cho Claude Code

## P0

```text
Agent Gateway
Goal / Run / Plan / Step
Context Resolver
Policy
Approval
Event Log
```

## P1

```text
Sales pilot
Tool Registry
n8n adapter
Evaluator
Agent Activity UI
```

## P2

```text
DeepSeek Harness adapter
OpenSandbox
Cost metrics
Retry/fallback
```

## P3

```text
Finance agentic wrapper
Marketing
Legal
Learning
Advanced memory
```

---

# 63. Definition of Done toàn bộ adjustment

Adjustment được coi là thành công khi founder có thể nói:

> “Tìm thêm khách hàng tiềm năng cho COSA và chuẩn bị chiến dịch tiếp cận.”

Hệ thống phải:

1. Nhận diện đây là Goal hoặc Command.
2. Resolve company/context.
3. Lập plan.
4. Chọn Sales domain.
5. Gọi Research/Data capability.
6. Tạo danh sách prospect.
7. Score prospect.
8. Tạo outreach draft.
9. Yêu cầu approval trước external action.
10. Gọi n8n sau approval.
11. Ghi events.
12. Update sales data.
13. Tính metrics.
14. Hiển thị Agent Activity.
15. Cho founder xem kết quả.
16. Lưu lesson/recommendation để dùng cho vòng sau.

Founder phải luôn trả lời được:

```text
AI đang làm gì?
Tại sao?
Dùng dữ liệu nào?
Dùng model nào?
Dùng tool nào?
Chi phí bao nhiêu?
Có thay đổi dữ liệu không?
Ai phê duyệt?
Kết quả là gì?
```

Nếu COSA làm được các điều trên, COSA đã chuyển từ:

> **AI-enabled business app**

thành:

> **Supervised Agentic Founder Operating System**

mà không cần xây một hệ thống enterprise quá phức tạp.

---

# 64. Chỉ dẫn cho Claude Code

Khi triển khai tài liệu này:

1. Đọc codebase trước khi thay đổi.
2. Không giả định module/file tồn tại.
3. Không rewrite COSA v13.
4. Ưu tiên adapter/facade.
5. Mọi migration phải additive.
6. Không bật lại module đang disable.
7. Không tạo microservice mới nếu chưa cần.
8. Không thêm Kafka/vector DB riêng.
9. Không thay n8n.
10. Không thay LiveKit.
11. Không dùng Harness làm business memory.
12. Không để agent bypass policy.
13. Không cho external write không audit.
14. Không lưu secret trong logs/memory.
15. Mỗi phase phải chạy được end-to-end trước khi sang phase tiếp theo.
16. Viết test cho policy, approval, tool routing và run state machine.
17. Mọi thay đổi schema phải có migration.
18. Mọi tool/action phải đăng ký trong Tool Registry.
19. Mọi agent run phải trace được.
20. Giữ backward compatibility với chức năng đang chạy.

---

# 65. Kết luận kiến trúc

Điểm cốt lõi của adjustment này không phải là tạo thêm nhiều AI Agent.

Điểm cốt lõi là chuyển COSA sang mô hình:

```text
Founder Goal
      ↓
COSA Control Plane
      ↓
Domain + Capability
      ↓
Tools / Workflow
      ↓
Business Systems
      ↓
Observe / Evaluate
      ↓
Founder
```

Trong đó:

- **Control Plane** điều phối.
- **Domain Agent** cung cấp chuyên môn.
- **Capability** cung cấp năng lực dùng chung.
- **DeepSeek Harness** cung cấp Agent Runtime.
- **n8n** cung cấp external automation.
- **OpenSandbox** cung cấp execution sandbox.
- **PostgreSQL** giữ business truth.
- **pgvector** hỗ trợ knowledge retrieval.
- **LiveKit** xử lý realtime voice.
- **Policy + Approval** kiểm soát hành động.
- **Event + Observability** làm hệ thống minh bạch.
- **Founder** giữ quyền quyết định cuối cùng ở các hành động quan trọng.

Đây là kiến trúc phù hợp với mục tiêu COSA trở thành một **AI Founder OS cho One Person Company**: gọn, local-first, có khả năng mở rộng, thực thi được và không over-engineer.
