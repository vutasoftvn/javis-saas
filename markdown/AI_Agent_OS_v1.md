# AI Agent OS — Integrated Architecture Specification

**Version:** vNext
**Status:** Architecture Proposal
**Primary language:** Python
**Business platform:** Encore TS/Go
**Architecture style:** Agent Kernel + Capability Platform + Business Services

---

# 1. Mục tiêu

AI Agent OS là nền tảng runtime dùng để xây dựng các AI Agent có khả năng:

* reasoning;
* lập kế hoạch;
* sử dụng tools;
* sử dụng memory;
* thực thi tác vụ nhiều bước;
* phân công công việc cho sub-agent;
* tương tác với business systems;
* yêu cầu con người phê duyệt;
* được theo dõi và đánh giá;
* đề xuất cải tiến chính bản thân;
* thay đổi model/provider mà không thay đổi business logic.

AI Agent OS **không phải chatbot framework** và cũng không phải wrapper quanh một LLM provider.

Định nghĩa kiến trúc:

```text
AI Agent OS
=
Execution Kernel
+ Context Engine
+ Capability Runtime
+ Memory Runtime
+ Model Runtime
+ Governance
+ Observability
+ Evaluation
+ Improvement Engine
```

LLM chỉ là một dependency có thể thay thế.

---

# 2. Nguyên lý thiết kế

## 2.1 Own the loop

Agent OS phải sở hữu vòng đời execution.

Không để model provider quyết định architecture.

```text
Goal
 ↓
Plan
 ↓
Act
 ↓
Observe
 ↓
Evaluate
 ↓
Continue / Finish / Ask Human
```

Runtime quyết định:

```text
until:
    goal_satisfied
    OR max_steps
    OR timeout
    OR max_tokens
    OR max_cost
    OR policy_denied
    OR human_approval_required
```

---

## 2.2 Model là swappable component

Agent không phụ thuộc trực tiếp:

```python
openai.chat(...)
```

Agent chỉ yêu cầu model capability:

```text
reasoning
fast
cheap
vision
embedding
private
```

Model Gateway quyết định provider/model phù hợp.

---

## 2.3 Business logic không nằm trong Agent Core

Agent reasoning bằng Python.

Business domain được quản lý bởi business platform.

```text
AI Agent
   ↓
Business Capability
   ↓
Encore
   ↓
Domain Logic
   ↓
Database
```

Agent không được truy cập trực tiếp business database để thay đổi dữ liệu.

---

## 2.4 Core nhỏ, capability mở rộng

Không xây một Agent framework khổng lồ.

Core chỉ cung cấp:

```text
execution
context
state
model
tools
memory
policy
observability
```

Business intelligence được bổ sung bằng:

```text
Skills
Plugins
Tools
Agents
Workflows
MCP
Knowledge
UI capabilities
```

---

## 2.5 Deterministic first

Không phải mọi thứ đều cần agent.

Nếu tác vụ có thể thực hiện bằng:

```text
function
service
query
workflow
rule
```

thì sử dụng cách deterministic.

Agent được dùng khi cần:

```text
reasoning
ambiguity resolution
planning
research
decision support
synthesis
```

---

# 3. Kiến trúc tổng thể

```text
┌──────────────────────────────────────────────────────┐
│                    USER / CLIENT                     │
│                                                      │
│ Web │ Mobile │ Chat │ API │ Automation │ Event       │
└─────────────────────────┬────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│                    CONTROL PLANE                     │
│                                                      │
│ Agent Registry                                       │
│ Capability Registry                                  │
│ Skill / Plugin Registry                              │
│ Prompt Registry                                      │
│ Model Profiles                                       │
│ Policies                                             │
│ Evals                                                │
│ Versions / Releases                                  │
└─────────────────────────┬────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│                     AGENT KERNEL                     │
│                                                      │
│ AgentRun                                             │
│ Run Controller                                       │
│ Execution Strategies                                 │
│ State Machine                                        │
│ Step Executor                                        │
│ Budget Controller                                    │
│ Checkpoint / Resume                                  │
│ Delegation Runtime                                   │
└──────────────┬─────────────────┬─────────────────────┘
               │                 │
        ┌──────▼───────┐ ┌──────▼─────────┐
        │Context Engine│ │Capability Runtime│
        └──────┬───────┘ └──────┬─────────┘
               │                 │
               │       ┌─────────┼─────────────┐
               │       │         │             │
               │      Tool      Skill        Agent
               │       │         │             │
               │      MCP     Workflow         UI
               │
        ┌──────▼───────┐
        │Memory Runtime│
        └──────┬───────┘
               │
        ┌──────▼────────┐
        │ Model Gateway │
        └──────┬────────┘
               │
       OpenAI / Claude /
       Gemini / DeepSeek /
       Local Models

────────────────────────────────────────────────────────

                    GOVERNANCE

Policy Engine
Authorization
Human Approval
Guardrails
Secrets Management
Tenant Isolation

────────────────────────────────────────────────────────

                 INTELLIGENCE OPS

Tracing
Agent Event Log
Metrics
Evals
Feedback
Experimentation
Improvement Engine

────────────────────────────────────────────────────────

                    BUSINESS

                     Encore

OKR │ 12 Week Year │ Task │ Project │ CRM │ Finance ...
```

---

# 4. AgentRun — primitive trung tâm

Không lấy `Agent` làm trung tâm execution.

Primitive trung tâm là:

```text
AgentRun
```

Một Agent Definition có thể chạy hàng nghìn AgentRun khác nhau.

```python
class AgentRun:
    id: str

    tenant_id: str
    user_id: str

    agent_id: str
    agent_version: str

    goal: str

    strategy: str

    status: RunStatus

    state: dict

    context_snapshot: dict

    budget: RunBudget

    parent_run_id: str | None

    trace_id: str

    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
```

Các trạng thái cơ bản:

```text
CREATED
RUNNING
WAITING_TOOL
WAITING_SUBAGENT
WAITING_APPROVAL
PAUSED
COMPLETED
FAILED
CANCELLED
```

AgentRun phải hỗ trợ:

```text
pause
resume
retry
replay
inspect
fork
evaluate
audit
```

---

# 5. Execution Kernel

Execution Kernel là trái tim của AI Agent OS.

```text
Execution Kernel
├── Run Controller
├── Step Executor
├── Strategy Engine
├── State Machine
├── Budget Controller
├── Retry Manager
├── Timeout Manager
├── Cancellation
├── Checkpoint
└── Delegation
```

Agent không sở hữu execution loop.

Ví dụ khai báo:

```yaml
agent:
  id: okr-coach
  version: 1.0

  strategy: plan_execute

  model_profile: reasoning

  skills:
    - okr-analysis
    - weekly-review

  capabilities:
    - okr.read
    - task.read

  limits:
    max_steps: 12
    timeout_seconds: 120
    max_cost_usd: 0.5
```

Kernel chịu trách nhiệm thực thi.

---

# 6. Execution Strategies

Không tồn tại một agent loop phù hợp với mọi nhiệm vụ.

Execution strategy phải là pluggable component.

```python
class ExecutionStrategy:

    async def initialize(self, run):
        ...

    async def next_step(self, run):
        ...

    async def observe(self, run, result):
        ...

    async def should_continue(self, run):
        ...
```

Các strategy mặc định:

```text
direct
react
plan_execute
reflect
workflow
parallel
supervisor
```

## Direct

```text
Input
 ↓
Model
 ↓
Output
```

Dùng cho tác vụ đơn giản.

---

## ReAct

```text
Reason
 ↓
Act
 ↓
Observe
 ↓
Reason
```

Dùng cho tool-based exploration.

---

## Plan Execute

```text
Goal
 ↓
Plan
 ↓
Step 1
 ↓
Step 2
 ↓
...
 ↓
Result
```

Phù hợp business reasoning.

---

## Workflow

```text
Analyze
 ↓
Propose
 ↓
Approval
 ↓
Execute
```

Phù hợp business operation.

---

## Parallel

```text
             Research
           ↗
Main ───────→ Analysis
           ↘
             Review
```

---

## Supervisor

```text
Supervisor
├── Research Agent
├── Analysis Agent
└── Review Agent
```

Multi-agent vì thế không cần trở thành framework độc lập.

Multi-agent chỉ là một dạng execution/delegation strategy.

---

# 7. Context Engine

Memory không đồng nghĩa với context.

```text
Memory
=
những gì hệ thống có thể biết

Context
=
những gì model cần biết tại thời điểm hiện tại
```

Context Engine chịu trách nhiệm biên dịch context cho từng model call.

```text
                   Business State
                         │
                   Agent State
                         │
Memory ──────────── Context Engine ─────── Skills
                         │
Knowledge ───────────────┤
                         │
Conversation ────────────┤
                         │
Tool Schemas ────────────┤
                         │
                         ▼
                  Model Context
```

Subsystem:

```text
Context Engine
├── Context Compiler
├── Token Budget
├── Context Ranking
├── Context Filtering
├── Compression
├── Prompt Prefix Cache
├── Tool Selection
├── Provenance
└── Context Policy
```

---

# 8. Context budget

Không gửi toàn bộ dữ liệu vào model.

Ví dụ:

```text
Available information
    2,000,000 tokens

Model context budget
       40,000 tokens
```

Context Engine phải quyết định:

```text
system instructions      5K
skill instructions       4K
tool schemas             5K
working state            5K
retrieved memories       8K
business data            8K
conversation             5K
```

Context compilation trở thành một optimization problem.

---

# 9. Memory Runtime

Memory không phải database.

Database chỉ là provider cho Memory Runtime.

```text
Memory Runtime

├── Working Memory
├── Episodic Memory
├── Semantic Memory
├── Procedural Memory
└── Entity Memory
```

## Working Memory

State của AgentRun hiện tại.

---

## Episodic Memory

Những trải nghiệm đã xảy ra:

```text
"Trong weekly review tuần trước,
team phát hiện QA thường bị underestimate."
```

---

## Semantic Memory

Kiến thức được tổng hợp:

```text
"QA của team này thường cần buffer khoảng 25–30%."
```

---

## Procedural Memory

Agent học cách thực hiện công việc:

```text
"Khi review OKR,
kiểm tra velocity trước khi đánh giá confidence."
```

---

## Entity Memory

Thông tin liên quan đến:

```text
person
team
project
objective
customer
organization
```

---

# 10. Memory Policy

Agent không được tự động lưu mọi thứ.

Pipeline:

```text
Experience
   ↓
Memory Candidate
   ↓
Memory Evaluator
   ↓
Useful?
 ┌─────┴─────┐
 No          Yes
              ↓
         Normalize
              ↓
         Deduplicate
              ↓
         Add confidence
              ↓
          Persist
```

Memory policy gồm:

```text
when_to_read
what_to_read

when_to_write
what_to_write

retention

confidence

provenance

deduplication
```

---

# 11. Memory Providers

Memory Runtime không phụ thuộc vendor.

```python
class MemoryProvider:

    async def search(...):
        ...

    async def write(...):
        ...

    async def delete(...):
        ...

    async def update(...):
        ...
```

Provider:

```text
TencentDB Agent Memory
PostgreSQL
Redis
Vector DB
Graph DB
```

TencentDB Agent Memory có thể là provider mạnh nhưng không định nghĩa kiến trúc memory của Agent OS.

---

# 12. Unified Capability System

Thay vì xem:

```text
Tool
Skill
Plugin
MCP
Agent
Workflow
Knowledge
UI
```

là các subsystem hoàn toàn tách biệt, AI Agent OS sử dụng abstraction chung:

```text
Capability
```

Capability Registry:

```text
Capability
├── Tool
├── Skill
├── Agent
├── Workflow
├── MCP
├── Knowledge
└── UI
```

---

# 13. Capability manifest

Ví dụ:

```yaml
id: okr.weekly-review
version: 1.2.0

type: skill

description: >
  Analyze weekly OKR execution and identify risks.

inputs:
  workspace_id:
    type: string

permissions:
  - okr.read
  - task.read

tools:
  - okr.get_objectives
  - okr.get_key_results
  - task.list

model_profile:
  reasoning

ui:
  renderer: okr.weekly-review

evals:
  - evals/basic.yaml
  - evals/risk-detection.yaml
```

Runtime không cần quan tâm capability được implement bởi:

```text
Python
Encore
MCP
HTTP API
Plugin
Remote agent
```

---

# 14. Plugin Architecture

Plugin phải đơn giản.

Không xây plugin runtime quá phức tạp.

Một plugin có thể có cấu trúc:

```text
plugins/
└── okr/
    ├── plugin.yaml
    │
    ├── skills/
    │   ├── weekly-review/
    │   │   └── SKILL.md
    │   │
    │   └── objective-planning/
    │       └── SKILL.md
    │
    ├── tools/
    │   ├── get_objectives.py
    │   └── analyze_progress.py
    │
    ├── agents/
    │   └── okr-coach.yaml
    │
    ├── workflows/
    │
    ├── ui/
    │
    └── evals/
```

Plugin có thể đăng ký:

```text
skills
tools
agents
workflows
UI
evaluations
```

---

# 15. Skill Architecture

Skill là capability cung cấp domain intelligence cho agent.

Ví dụ:

```text
skills/
└── weekly-review/
    ├── SKILL.md
    ├── prompts/
    ├── resources/
    └── evals/
```

`SKILL.md` mô tả:

```text
When to use
Objectives
Reasoning procedure
Relevant tools
Constraints
Expected output
Examples
```

Skill chỉ được load khi có liên quan.

Không nhét toàn bộ knowledge vào system prompt.

---

# 16. Tool Runtime

Tool Runtime chuẩn hóa execution của tất cả tools.

```text
Agent
 ↓
Tool Request
 ↓
Policy Engine
 ↓
Authorization
 ↓
Approval?
 ↓
Tool Executor
 ↓
Tool
 ↓
Validation
 ↓
Tool Result
```

Tool có contract:

```python
class Tool:

    name: str

    input_schema: dict

    output_schema: dict

    permissions: list[str]

    side_effect: bool

    risk_level: str
```

---

# 17. Native Tool và MCP

MCP được xem như một adapter trong Capability Runtime.

Không sử dụng MCP để thay thế toàn bộ business APIs.

```text
Capability Runtime

├── Native Business Tool
├── Native Python Tool
├── MCP Tool
├── HTTP Tool
└── Remote Tool
```

Ví dụ nên dùng MCP:

```text
GitHub
Slack
Google Drive
external databases
third-party SaaS
```

Ví dụ business operations nên dùng native contract:

```text
okr.update_target
task.create
project.change_status
invoice.approve
```

---

# 18. Delegation Protocol

Multi-agent được xây quanh delegation contract.

Parent agent không cần biết toàn bộ execution context của child agent.

```text
Parent
  ↓
Task Contract
  ↓
Subagent
  ↓
Result Contract
```

Task Contract:

```json
{
  "objective": "Analyze the cause of declining KR velocity",

  "constraints": {
    "max_steps": 8,
    "max_cost": 0.2
  },

  "expected_output": {
    "summary": "string",
    "evidence": [],
    "confidence": "number"
  }
}
```

Subagent Result:

```json
{
  "status": "completed",

  "summary": "...",

  "evidence": [],

  "confidence": 0.86,

  "artifacts": [],

  "usage": {
    "tokens": 12450,
    "cost": 0.13
  }
}
```

Parent chỉ nhận kết quả cần thiết.

---

# 19. Model Gateway

Agent không gọi provider trực tiếp.

```text
Agent
 ↓
Model Profile
 ↓
Model Gateway
 ↓
Provider
```

Model profile:

```yaml
reasoning:
  reasoning: high
  tool_calling: true
  latency: medium
  cost: medium

fast:
  reasoning: medium
  latency: low
  cost: low

private:
  deployment: local
```

Gateway xử lý:

```text
routing
fallback
retry
credentials
rate limits
token accounting
cost
cache
provider normalization
```

---

# 20. Prompt caching

Context nên được chia thành:

```text
Static Prefix

├── Core policy
├── Agent instructions
├── Stable skill instructions
└── Stable tool definitions

Dynamic Context

├── Current task
├── Agent state
├── Retrieved memory
├── Business data
└── Recent conversation
```

Static prefix có thể cache nếu model/provider hỗ trợ.

Metrics cần theo dõi:

```text
tokens/run
cost/run
cache hit ratio
cost/agent
cost/tenant
latency/model
```

---

# 21. Governance Layer

Agent không được tự do thực thi mọi action.

Governance gồm:

```text
Policy Engine
Authorization
Human Approval
Guardrails
Secrets
Tenant Isolation
Audit
```

---

# 22. Policy Engine

Model chỉ đề xuất action.

Runtime quyết định có cho phép action hay không.

```text
LLM
 ↓
Action Proposal
 ↓
Policy Engine
 ↓
Permission
 ↓
Approval
 ↓
Execution
```

Ví dụ:

```yaml
action: okr.update_target

rules:

  - roles:
      - workspace_owner
      - manager

  - change_percentage:
      max_without_approval: 10

  - change_percentage:
      above: 10
      approval_required: true
```

LLM không phải source of truth cho authorization.

---

# 23. Human Approval

Approval là primitive của runtime.

```text
RUNNING
   ↓
WAITING_APPROVAL
   ↓
 ┌─────────────┐
Approve     Reject
   │            │
Execute       Replan
```

ApprovalRequest:

```python
class ApprovalRequest:

    action: str

    rationale: str

    impact: str

    risk: str

    preview: dict

    required_role: str

    expires_at: datetime | None
```

---

# 24. Guardrails

Có ba lớp chính:

```text
Input Guard
Execution Guard
Output Guard
```

Input:

```text
prompt injection
malicious content
tenant violation
```

Execution:

```text
tool authorization
dangerous action
permission escalation
```

Output:

```text
secret leakage
PII
cross-tenant data
internal instructions
```

---

# 25. Observability

Agent observability không thể chỉ dựa vào application logs.

Mỗi execution phải có:

```text
trace_id
run_id
session_id
tenant_id
user_id
agent_id
```

Ví dụ trace:

```text
AgentRun
├── context.compile
├── model.plan
├── memory.search
├── tool.call
├── subagent.run
├── approval.wait
└── model.finalize
```

Có thể triển khai trên OpenTelemetry.

---

# 26. Agent Event Log

Trace dùng cho performance/debugging.

Event Log dùng cho state/audit/replay.

Ví dụ:

```text
RunCreated
ContextBuilt
PlanCreated
ModelCalled
ToolRequested
ToolAuthorized
ToolCompleted
SubagentStarted
SubagentCompleted
ApprovalRequested
ApprovalGranted
MemoryWritten
RunCompleted
```

Event stream hỗ trợ:

```text
audit
replay
debugging
resume
analytics
evaluation
dataset generation
```

---

# 27. Evaluation Platform

Không có eval thì không có cải tiến đáng tin cậy.

```text
Agent Definition
       ↓
      Evals
       ↓
 Release Gate
       ↓
 Production
```

Eval categories:

```text
Reasoning Evals
Tool-use Evals
Business Evals
Safety Evals
Regression Evals
Cost Evals
Latency Evals
```

---

# 28. Golden Dataset

Ví dụ OKR:

```text
Input:

Objective đang chậm 30%.

Expected:

✓ detect risk
✓ identify likely cause
✓ inspect related tasks
✓ make recommendation
✓ request approval before modifying objective
```

Có thể score:

```text
risk_detection       1.00
root_cause           0.82
recommendation       0.91
policy_compliance    1.00
cost_efficiency      0.88
```

---

# 29. Versioning

Mọi component ảnh hưởng đến agent behavior phải version được.

```text
agent_version
prompt_version
skill_version
tool_version
model_profile_version
context_policy_version
memory_policy_version
```

AgentRun lưu snapshot:

```json
{
  "agent": "okr-coach@3.2",
  "skill": "weekly-review@2.1",
  "model_profile": "reasoning@4",
  "context_policy": "business-default@2"
}
```

Nhờ đó regression có thể truy ngược nguyên nhân.

---

# 30. Improvement Engine

Không thiết kế agent theo kiểu:

```text
observe problem
 ↓
modify itself
 ↓
deploy automatically
```

Thay vào đó:

```text
Production Traces
       +
User Feedback
       +
Eval Failures
       +
Cost
       +
Latency
       ↓
Improvement Analyzer
       ↓
Improvement Proposal
       ↓
Human Review
       ↓
Evals
       ↓
Sandbox
       ↓
Canary
       ↓
Release
```

---

# 31. Improvement Proposal

Agent có thể đề xuất:

```text
modify prompt
add skill
modify skill
change tool description
change context policy
change memory policy
change model profile
add eval case
remove unnecessary context
introduce new workflow
```

Proposal:

```yaml
type: context_policy_change

reason:
  excessive irrelevant historical context

evidence:
  - trace_1032
  - trace_1044
  - eval_context_17

proposal:
  reduce episodic_memory_top_k: 12 -> 6

expected_effect:
  token_cost: -18%
  quality: unchanged

risk:
  low
```

Con người review trước khi apply.

---

# 32. Control Plane

Control Plane quản lý định nghĩa hệ thống.

```text
Control Plane

├── Agent Registry
├── Capability Registry
├── Plugin Registry
├── Skill Registry
├── Prompt Registry
├── Model Profiles
├── Policies
├── Evals
├── Versions
└── Releases
```

Control Plane không trực tiếp xử lý AgentRun.

---

# 33. Runtime Plane

Runtime Plane xử lý execution.

```text
Runtime Plane

├── AgentRun
├── Execution Kernel
├── Context Engine
├── Memory Runtime
├── Capability Runtime
├── Model Gateway
├── Policy Runtime
└── Approval Runtime
```

Control Plane gửi configuration vào Runtime Plane.

---

# 34. Business Architecture

Business platform chạy riêng với Agent OS.

Đề xuất:

```text
Encore TS hoặc Go
```

quản lý:

```text
identity
organization
workspace
OKR
12 Week Year
tasks
projects
notifications
billing
permissions
business events
```

---

# 35. Business Commands và Queries

Agent không truy cập DB trực tiếp.

Queries:

```text
okr.get_objectives
okr.get_progress
okr.get_health

task.list
task.get_blockers

project.get_status
```

Commands:

```text
okr.update_target
okr.close_objective

task.create
task.reschedule

project.change_status
```

Encore chịu trách nhiệm:

```text
validation
authorization
transactions
domain rules
audit
event publishing
```

---

# 36. Business Events

Encore có thể phát:

```text
ObjectiveCreated
KeyResultUpdated
TaskBlocked
TaskCompleted
ProjectDelayed
WeekClosed
```

Agent OS subscribe:

```text
Business Event
      ↓
Agent Trigger
      ↓
AgentRun
```

Ví dụ:

```text
TaskBlocked
 ↓
Project Risk Agent
 ↓
Analyze impact
 ↓
Recommendation
```

---

# 37. Ví dụ: OKR Agent

User:

```text
Đánh giá tiến độ OKR Q3.
```

Execution:

```text
User
 ↓
OKR Agent
 ↓
AgentRun created
 ↓
Context Engine
 ↓
Load OKR analysis skill
 ↓
Query business capabilities
 ↓
okr.get_objectives
okr.get_progress
task.get_blockers
 ↓
Planner
 ↓
Analysis
 ↓
Risk detection
 ↓
Recommendation
 ↓
UI Result
```

---

# 38. Ví dụ: Agent đề xuất thay đổi KR

```text
OKR Agent
 ↓
Detect:
KR velocity thấp hơn plan 37%
 ↓
Analyze causes
 ↓
Proposal:
reduce target 1M → 850K
 ↓
Policy Engine
 ↓
Approval required
 ↓
WAITING_APPROVAL
```

UI:

```text
KR #2 đang lệch kế hoạch 37%.

Đề xuất:
1,000,000 → 850,000

Reason:
Historical velocity không còn hỗ trợ target hiện tại.

[Approve]
[Reject]
[Ask Agent to Revise]
```

Nếu approve:

```text
ApprovalGranted
 ↓
okr.update_target
 ↓
Encore
 ↓
Domain validation
 ↓
Transaction
 ↓
KeyResultUpdated
 ↓
AgentRun resume
```

---

# 39. Ví dụ: 12 Week Year Agent

```text
Weekly Review Agent
        │
        ├── goals
        ├── weekly commitments
        ├── completion data
        ├── task blockers
        └── historical execution
               ↓
            Analyze
               ↓
     Weekly Execution Score
               ↓
       Root Cause Analysis
               ↓
       Next Week Proposal
```

Subagents có thể chạy song song:

```text
                   Execution Analysis
                 ↗
Weekly Agent ────→ Risk Analysis
                 ↘
                   Planning Review
```

Parent chỉ nhận summarized outputs.

---

# 40. UI Capability

Plugin có thể cung cấp UI schema.

Agent output không nên chỉ là Markdown.

Ví dụ:

```json
{
  "type": "okr.weekly_review",
  "version": "1",

  "data": {
    "score": 82,
    "risks": [],
    "recommendations": []
  }
}
```

Frontend:

```text
Output Type
    ↓
UI Registry
    ↓
Renderer
```

Ví dụ renderer:

```text
OKR Health Card
Risk Card
Recommendation Card
Approval Card
Timeline
Chart
```

Điều này tạo nền tảng cho generative/agentic UI mà không để LLM kiểm soát frontend code.

---

# 41. Vai trò của DeepSeek Harness

DeepSeek Harness được xem như:

```text
architectural inspiration
+
implementation reference
```

Có thể học:

```text
agent loop
tool execution
context management
filesystem patterns
skills
minimal harness philosophy
```

Nhưng:

```text
AI Agent OS ≠ DeepSeek Harness wrapper
```

Agent OS phải giữ interfaces độc lập.

---

# 42. Vai trò của Google ADK

Google ADK có thể cung cấp:

```text
agent patterns
workflow primitives
tool conventions
callbacks
multi-agent ideas
```

Có thể triển khai adapter:

```text
Agent OS
   ↓
ADK Adapter
```

Nhưng không được thiết kế:

```text
Agent OS
=
ADK + business code
```

Core interfaces phải thuộc quyền kiểm soát của dự án.

---

# 43. Vai trò của TencentDB Agent Memory

TencentDB Agent Memory phù hợp ở tầng:

```text
Memory Provider
```

Không phải:

```text
Memory Architecture
```

Cấu trúc đúng:

```text
Memory Runtime
      ↓
MemoryProvider Interface
      ↓
TencentDB Agent Memory
```

Có thể thay bằng provider khác mà không ảnh hưởng Agent Kernel.

---

# 44. Vai trò của MCP

MCP là interoperability layer.

```text
Agent OS
   ↓
Capability Runtime
   ↓
MCP Adapter
   ↓
External MCP Servers
```

Dùng MCP cho integration.

Không biến MCP thành domain layer.

---

# 45. Technology Stack

## Agent OS

```text
Python
```

Có thể sử dụng:

```text
FastAPI
Pydantic
asyncio
OpenTelemetry
PostgreSQL
Redis
```

Các framework agent bên ngoài chỉ nên là adapter hoặc source of ideas.

---

## Business Platform

```text
Encore TS
```

hoặc:

```text
Encore Go
```

Vai trò:

```text
API
domain service
database
auth
event
background jobs
business workflows
```

---

## Database

Business:

```text
PostgreSQL
```

Agent state:

```text
PostgreSQL / Redis
```

Memory:

```text
TencentDB Agent Memory
+
PostgreSQL
+
optional vector/index services
```

---

# 46. Repository Structure

Đề xuất monorepo:

```text
ai-agent-platform/
│
├── agent-os/
│   │
│   ├── kernel/
│   │   ├── run.py
│   │   ├── state.py
│   │   ├── executor.py
│   │   └── budget.py
│   │
│   ├── strategies/
│   │   ├── direct/
│   │   ├── react/
│   │   ├── plan_execute/
│   │   ├── parallel/
│   │   └── supervisor/
│   │
│   ├── context/
│   │
│   ├── memory/
│   │
│   ├── capabilities/
│   │
│   ├── models/
│   │
│   ├── policy/
│   │
│   ├── approvals/
│   │
│   ├── observability/
│   │
│   ├── evals/
│   │
│   ├── improvement/
│   │
│   └── sdk/
│
├── plugins/
│   ├── okr/
│   ├── twelve-week-year/
│   ├── tasks/
│   └── projects/
│
├── business/
│   ├── identity/
│   ├── workspace/
│   ├── okr/
│   ├── tasks/
│   ├── projects/
│   └── notifications/
│
├── frontend/
│
├── contracts/
│
├── evals/
│
└── infra/
```

---

# 47. Core Interfaces

AI Agent OS cần giữ core abstractions nhỏ.

Tối thiểu:

```text
Agent
AgentRun
ExecutionStrategy

ContextProvider
MemoryProvider

Capability
Tool
Skill

ModelProvider

Policy
Approval

Event
Evaluator
```

Không nên vượt quá khoảng:

```text
10–15 foundational primitives
```

trong phiên bản đầu tiên.

---

# 48. Phase P0 — Agent Kernel

Ưu tiên xây:

```text
AgentRun
Execution Kernel

Direct Strategy
PlanExecute Strategy

Context Engine

Tool Runtime

Model Gateway

Basic Memory

Policy Engine

Approval

Tracing

Event Log
```

Mục tiêu:

```text
Một agent business chạy ổn định,
có thể inspect, audit và resume.
```

---

# 49. Phase P1 — Capability Platform

Sau khi P0 hoạt động ổn:

```text
Skills
Plugin System
Capability Registry
MCP Adapter
Delegation
Parallel execution
Workflow
UI Registry
Evaluation Platform
```

---

# 50. Phase P2 — Intelligence Platform

Chỉ làm khi có production data:

```text
Advanced Memory
Improvement Engine
Automatic Context Optimization
Model Routing Optimization
Agent Experiments
Canary Releases
Feedback Learning
Agent Marketplace
```

---

# 51. Những thứ không nên xây sớm

## Không xây complex multi-agent framework

P0 chỉ cần:

```python
delegate(task, agent)

parallel(tasks)
```

---

## Không xây universal workflow engine

Business workflow dài hạn nên giao cho:

```text
Encore
```

hoặc dedicated durable workflow engine nếu sau này thật sự cần.

---

## Không xây universal memory brain

Bắt đầu:

```text
working memory
+
episodic memory
+
business retrieval
```

Sau đó dựa trên eval để mở rộng.

---

## Không xây MCP-first architecture

MCP là adapter.

Không phải core abstraction của business platform.

---

# 52. Top 5 Architectural Priorities

Nếu chỉ được thực hiện 5 hạng mục đầu tiên:

### 1. AgentRun + Execution Kernel

Foundation cho toàn OS.

### 2. Context Engine

Ảnh hưởng trực tiếp tới chất lượng, token và cost.

### 3. Capability / Plugin System

Giữ kernel nhỏ và business extensible.

### 4. Observability + Event Log + Evals

Điều kiện cần cho debugging và improvement.

### 5. Policy + Human Approval

Điều kiện cần để agent có thể sử dụng trong business production.

---

# 53. Kiến trúc mục tiêu cuối cùng

```text
                       BUSINESS APPLICATIONS

            OKR │ 12WY │ Tasks │ Projects │ CRM

                           │
                           │
                  Business Capabilities
                           │
                           ▼

┌────────────────────────────────────────────────────────┐
│                       AI AGENT OS                      │
│                                                        │
│                   Execution Kernel                     │
│                                                        │
│     Context         Capability         Memory           │
│      Engine           Runtime          Runtime          │
│                                                        │
│                   Model Gateway                        │
│                                                        │
│                Policy + Approval                       │
│                                                        │
│        Observability + Evals + Improvement             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼

                MODELS / TOOLS / SYSTEMS

       GPT │ Claude │ Gemini │ DeepSeek │ Local
       MCP │ APIs │ Databases │ SaaS
```

---

# 54. Architecture Principle

Nguyên tắc cốt lõi:

> **Build the Agent OS around the execution loop, not around the model.**

Model có thể thay đổi.

Provider có thể thay đổi.

Memory provider có thể thay đổi.

MCP server có thể thay đổi.

Framework có thể thay đổi.

Nhưng những abstraction sau phải thuộc quyền kiểm soát của AI Agent OS:

```text
AgentRun
Execution
Context
Capabilities
State
Policy
Evaluation
Improvement
```

---

# 55. Định nghĩa cuối cùng

AI Agent OS không phải một Agent Framework.

AI Agent OS là:

> **Một runtime và control plane cho phép AI agents quan sát, suy luận, lập kế hoạch, sử dụng capabilities, tương tác với business systems, phân công công việc, duy trì memory, xin phê duyệt, được đánh giá và liên tục đề xuất cải tiến dưới sự kiểm soát của con người.**

Công thức kiến trúc:

```text
AI Agent OS
=
Small Kernel
+
Composable Capabilities
+
Strong Context
+
Safe Execution
+
Measurable Intelligence
+
Human-Governed Improvement
```

Đây là nền tảng phù hợp để phát triển từ:

```text
AI Assistant
      ↓
Business Agent
      ↓
Multi-Agent System
      ↓
Agentic Business Platform
      ↓
AI-native Operating System
```

mà không bị khóa vào một model, framework hoặc vendor cụ thể.
