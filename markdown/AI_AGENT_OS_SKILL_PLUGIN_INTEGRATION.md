# AI Agent OS — Skill/Plugin Architecture Integration

**Status:** Architecture Supplement  
**Version:** 0.1  
**Date:** 2026-08-22  
**Scope:** Bổ sung kiến trúc Skill/Plugin cho AI Agent OS dựa trên các pattern đã phân tích từ `marketingskills`, đồng thời tích hợp với Python Agent Runtime, Google ADK / DeepSeek Harness, TencentDB Agent Memory, Encore Business Services và Tool Gateway.

---

## 1. Mục tiêu tài liệu

Tài liệu này bổ sung cho kiến trúc AI Agent OS hiện có một lớp **Business Skill / Plugin Runtime** thống nhất.

Mục tiêu chính:

1. Chuẩn hóa cách đóng gói năng lực nghiệp vụ thành **Skill**.
2. Phân biệt rõ **Skill, Agent, Workflow, Loop, Tool, Memory và Business Service**.
3. Cho phép một AI Agent OS dùng chung Core nhưng cài thêm các domain plugin như:
   - Marketing
   - OKR
   - 12 Week Year
   - Task Management
   - Sales
   - Finance
   - Customer Success
4. Giữ Skill đơn giản, portable, gần với Agent Skills spec.
5. Đưa workflow dài hạn, recurring loop, approval và state ra khỏi prompt để Core quản lý.
6. Cho phép AI Agent tự phát hiện điểm yếu, đề xuất cải tiến Skill, chạy eval và đưa con người duyệt trước khi phát hành.
7. Tạo nền cho một marketplace/plugin ecosystem mà không làm Agent Core bị phụ thuộc vào từng domain.

---

# 2. Kết luận kiến trúc quan trọng

Pattern từ `marketingskills` nên được sử dụng như **reference implementation cho Business Capability Layer**, không phải Agent Core.

AI Agent OS nên phân tầng:

```text
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent OS Interaction                  │
│ Chat · UI · API · Event · Schedule · Webhook               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     Agent Runtime / Core                    │
│ Intent · Reasoning · Planning · Context · Tool Calling      │
│ Reflection · Delegation · Multi-Agent                       │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                ▼                               ▼
┌────────────────────────────┐      ┌──────────────────────────┐
│ Skill / Plugin Runtime     │      │ Memory & Context         │
│ Registry · Router · Loader │      │ Working · Episodic       │
│ Composition · Versioning   │      │ Semantic · Business      │
└───────────────┬────────────┘      └──────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────┐
│              Workflow / Loop / Automation Engine            │
│ Sequential · Parallel · Condition · Approval · Resume       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Policy Engine                         │
│ RBAC · HITL · Risk · Spend · Send · Publish · Destructive  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       Tool Gateway                          │
│ Native Tool · MCP · API · Encore · Composio · CLI          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                     External Systems
```

Nguyên tắc trung tâm:

> **Skill định nghĩa cách làm. Core quyết định khi nào chạy, cách chạy, state ở đâu, tool nào được dùng và hành động nào cần phê duyệt.**

---

# 3. Các primitive chính của AI Agent OS

## 3.1 Skill

**Skill = capability nghiệp vụ có thể được agent gọi khi cần.**

Ví dụ:

- `marketing-plan`
- `seo-audit`
- `okr-review`
- `weekly-planning`
- `task-prioritization`
- `cashflow-analysis`

Skill chứa:

- semantic description;
- instructions;
- domain methodology;
- references;
- templates;
- evals;
- optional scripts/assets.

Skill **không phải một agent riêng**.

---

## 3.2 Agent

**Agent = reasoning role có goal, model, tools, policies và context riêng.**

Ví dụ:

- General Assistant
- Planning Agent
- Research Agent
- Strategy Critic
- Finance Critic
- Security Reviewer
- Synthesizer

Một Agent có thể dùng nhiều Skill.

Một Skill cũng có thể được nhiều Agent sử dụng.

---

## 3.3 Workflow

**Workflow = composition nhiều step có state.**

Ví dụ:

```text
INIT
 ↓
RESEARCH
 ↓
DRAFT
 ↓
REVIEW
 ↓
APPROVAL
 ↓
FINALIZE
```

Workflow có thể:

- resumable;
- long-running;
- parallel;
- retry;
- wait-for-human;
- wait-for-event;
- produce artifacts.

---

## 3.4 Loop

**Loop = workflow lặp lại theo thời gian hoặc theo condition.**

Ví dụ:

```text
Every Friday
   ↓
Read OKR metrics
   ↓
Compare target vs actual
   ↓
Detect risk
   ↓
Generate review
   ↓
Propose corrective action
   ↓
Human approval if plan changes
```

Loop phải có:

- check cadence;
- act condition;
- state;
- idempotency;
- self-check;
- stop/bail-out;
- output;
- policy gate.

---

## 3.5 Tool

**Tool = khả năng tương tác với hệ thống bên ngoài hoặc thực hiện hành động.**

Ví dụ:

- read Google Analytics;
- create task;
- send email;
- update CRM;
- query database;
- create GitHub issue.

Skill không nên phụ thuộc trực tiếp vào implementation của tool.

Skill nên yêu cầu **capability**:

```text
analytics.read
tasks.create
crm.contact.read
email.draft
calendar.event.create
```

Tool Gateway sẽ resolve capability thành adapter thực tế.

---

## 3.6 Business Service

Business Service là transactional domain logic, ví dụ:

```text
OKR Service
Task Service
Marketing Campaign Service
Budget Service
Approval Service
Organization Service
```

Encore phù hợp với lớp này.

Agent không nên thay thế business service.

Agent nên gọi business service thông qua Tool Gateway hoặc typed API.

---

## 3.7 Context

Context là thông tin hiện tại và có tính authoritative.

Ví dụ:

```text
organization
strategy
product
ICP
goals
brand voice
active OKRs
policies
team
constraints
```

Context khác Memory.

---

## 3.8 Memory

Memory lưu kiến thức đã học từ quá trình tương tác:

- semantic memory;
- episodic memory;
- user/org preferences;
- previous decisions;
- historical observations;
- lessons learned.

TencentDB Agent Memory phù hợp với lớp này.

---

# 4. Skill package chuẩn

## 4.1 Cấu trúc đề xuất

```text
plugins/
└── marketing/
    ├── plugin.yaml
    ├── README.md
    │
    ├── context/
    │   └── schema.yaml
    │
    ├── skills/
    │   ├── product-marketing/
    │   │   ├── SKILL.md
    │   │   ├── skill.yaml
    │   │   ├── references/
    │   │   ├── assets/
    │   │   └── evals/
    │   │
    │   ├── marketing-plan/
    │   │   ├── SKILL.md
    │   │   ├── skill.yaml
    │   │   ├── references/
    │   │   ├── evals/
    │   │   └── workflows/
    │   │
    │   └── seo-audit/
    │
    ├── workflows/
    ├── loops/
    ├── policies/
    ├── tools/
    └── evals/
```

---

# 5. Giữ `SKILL.md` đơn giản và portable

AI Agent OS nên giữ tinh thần Agent Skills spec.

Ví dụ:

```yaml
---
name: okr-review
description: >
  Review OKR progress, identify at-risk objectives and key results,
  diagnose blockers, and recommend corrective actions.
  Use when the user asks for OKR review, weekly OKR status,
  quarter progress, or why an objective is off track.
metadata:
  version: 1.0.0
---
```

Phần body tập trung vào:

```markdown
# OKR Review

## Goal
...

## Workflow
...

## Decision rules
...

## Guardrails
...

## Related Skills
...
```

### Không nên đưa toàn bộ runtime config vào `SKILL.md`

Để tránh biến Skill thành một DSL nặng nề.

---

# 6. `skill.yaml` — AI Agent OS extension

Runtime metadata nên nằm trong file riêng.

Ví dụ:

```yaml
apiVersion: agentos/v1
kind: Skill

metadata:
  name: okr-review
  version: 1.0.0
  domain: execution

spec:
  mode: workflow

  context:
    required:
      - organization.strategy
      - organization.okrs

  capabilities:
    read:
      - okr.read
      - metrics.read
      - tasks.read

    write:
      - artifact.create

  dependencies:
    required:
      - strategy-context

    related:
      - weekly-planning
      - task-prioritization

  workflow:
    resumable: true
    parallel: false

  risk:
    default: low

  approval:
    requiredFor:
      - okr.objective.update
      - okr.key_result.update

  output:
    types:
      - review-report
      - recommendation-set

  evals:
    required: true
```

---

# 7. Plugin manifest

Một plugin chứa nhiều Skill.

Ví dụ:

```yaml
apiVersion: agentos/v1
kind: Plugin

metadata:
  name: marketing
  version: 1.0.0

spec:
  description: Marketing operating capabilities for AI Agent OS

  compatibility:
    agentOS: ">=0.5.0"

  skills:
    autoDiscover: ./skills

  workflows:
    path: ./workflows

  loops:
    path: ./loops

  policies:
    path: ./policies

  tools:
    path: ./tools

  context:
    namespaces:
      - marketing
      - product
      - customer

  permissions:
    default: read-only
```

---

# 8. Skill Registry

Skill Registry là một service first-class trong Agent Core.

Nhiệm vụ:

1. discover skills;
2. validate manifests;
3. index metadata;
4. dependency resolution;
5. semantic retrieval;
6. version resolution;
7. enable/disable per organization;
8. enforce compatibility;
9. expose skill catalog cho agent.

## 8.1 Data model

```python
class SkillDefinition:
    id: str
    plugin_id: str
    name: str
    version: str

    description: str

    skill_md_path: str
    manifest_path: str

    domain: str
    mode: str

    required_context: list[str]
    dependencies: list[str]
    capabilities: list[str]

    risk_level: str

    enabled: bool
```

---

# 9. Skill Router

Description trong `SKILL.md` nên được dùng như semantic routing contract.

Flow:

```text
User request
   │
   ▼
Intent extraction
   │
   ▼
Skill retrieval
 BM25 + embedding
   │
   ▼
Top K skills
   │
   ▼
LLM reranker
   │
   ▼
Selected skill(s)
```

Pseudo code:

```python
async def route_skill(request: str):
    candidates = await registry.search(
        query=request,
        top_k=8,
    )

    ranked = await llm_rerank(
        request=request,
        candidates=candidates,
    )

    return ranked[:3]
```

Không nên:

```text
if "marketing" in query:
    use marketing-agent
```

Routing cần dựa trên capability semantics.

---

# 10. Progressive Skill Loading

Một ưu điểm quan trọng từ `marketingskills` là references được load khi cần.

AI Agent OS nên dùng 3 tầng:

```text
Level 1
Skill metadata

Level 2
SKILL.md

Level 3
references / examples / datasets
```

Agent không nên load toàn bộ plugin vào context.

Ví dụ:

```text
49 marketing skills
×
10K tokens
=
490K tokens
```

không khả thi.

Thay vào đó:

```text
request
  ↓
skill router
  ↓
load SKILL.md
  ↓
skill detects need
  ↓
load selected references
```

---

# 11. Business Context Layer

Pattern `product-marketing.md` nên được tổng quát thành Context Store.

## 11.1 Context namespaces

```text
organization/
├── profile
├── strategy
├── policies
├── team
└── vocabulary

product/
├── overview
├── positioning
├── customer
├── competitors
└── pricing

execution/
├── okrs
├── twelve-week-plan
└── active-priorities

marketing/
├── strategy
├── channels
├── campaigns
└── brand
```

---

## 11.2 Context object

```python
class ContextDocument:
    id: str
    namespace: str
    key: str

    version: int

    content: dict | str

    source: str

    created_by: str
    updated_by: str

    created_at: datetime
    updated_at: datetime
```

---

## 11.3 Context vs Memory

### Context

```text
Current approved truth
```

Ví dụ:

```text
Current ICP
Current company strategy
Current quarterly OKRs
Current pricing
Current policies
```

### Memory

```text
What the agent has learned over time
```

Ví dụ:

```text
Founder usually rejects paid acquisition before PMF.
The sales team prefers weekly summaries on Monday.
Previous campaign failed due to weak activation.
```

### Rule

> Memory có thể đề xuất cập nhật Context, nhưng không được tự sửa authoritative Context nếu policy yêu cầu approval.

---

# 12. Memory architecture

Đề xuất:

```text
┌────────────────────────────┐
│ Working Memory             │
│ current conversation/run   │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ Episodic Memory            │
│ runs / actions / outcomes  │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ Semantic Memory            │
│ facts / insights / lessons │
└──────────────┬─────────────┘
               │
               ▼
┌────────────────────────────┐
│ Context Promotion          │
│ human-approved facts       │
└────────────────────────────┘
```

TencentDB Agent Memory đảm nhiệm semantic/episodic retrieval.

Postgres/Encore giữ authoritative transactional state.

---

# 13. Workflow Engine

Pattern `marketing-plan` nên được chuyển thành durable workflow abstraction.

## 13.1 Workflow definition

```yaml
apiVersion: agentos/v1
kind: Workflow

metadata:
  name: marketing-plan

spec:
  resumable: true

  steps:
    - id: init
      type: agent
      skill: product-marketing

    - id: research
      type: agent
      skill: customer-research

    - id: plan
      type: agent
      skill: marketing-plan

    - id: review
      type: approval

    - id: finalize
      type: artifact

  transitions:
    - from: init
      to: research

    - from: research
      to: plan

    - from: plan
      to: review

    - from: review
      approved: finalize
      rejected: plan
```

---

# 14. Workflow state

Không dùng file `progress.md` làm state production.

Dùng DB:

```python
class WorkflowRun:
    id: UUID

    workflow_id: str
    workflow_version: str

    status: str
    current_step: str

    input: dict
    state: dict

    checkpoint: dict

    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None
```

```python
class WorkflowStepRun:
    id: UUID
    workflow_run_id: UUID

    step_id: str

    status: str

    input: dict
    output: dict

    error: dict | None

    retry_count: int
```

---

# 15. Durable execution

Workflow engine phải hỗ trợ:

```text
pause
resume
retry
timeout
cancel
human approval
event wait
schedule wait
parallel branch
compensation
```

Ví dụ:

```text
Agent drafts campaign
      ↓
workflow state saved
      ↓
wait 3 days
      ↓
human approves
      ↓
resume
      ↓
publish
```

Không phụ thuộc vào việc LLM session còn sống.

---

# 16. Loop Engine

Pattern `marketing-loops` nên trở thành primitive first-class.

## 16.1 Loop contract

```yaml
apiVersion: agentos/v1
kind: Loop

metadata:
  name: weekly-okr-review

spec:
  schedule:
    cron: "0 9 * * FRI"

  purpose:
    Detect OKRs at risk and recommend corrective actions

  workflow:
    ref: okr-review

  condition:
    actWhen:
      expression: "risk_count > 0"

  state:
    idempotencyKey:
      - organization_id
      - week

    cooldown: 7d

  selfCheck:
    - metrics_are_fresh
    - source_coverage_above_80_percent

  stop:
    - quarter_closed
    - organization_disabled_loop

  output:
    - review-report
    - notification
```

---

# 17. Rule: Check cadence khác Act condition

Đây là nguyên tắc cần giữ từ `marketing-loops`.

Sai:

```text
Every day → send churn warning
```

Đúng:

```text
Every day → check churn risk

Only act if:
risk_score > threshold
AND
not_contacted_recently
AND
data_confidence > minimum
```

---

# 18. Idempotency

Mọi recurring loop phải có idempotency.

Ví dụ:

```python
key = f"okr-review:{org_id}:{iso_week}"
```

Nếu key đã xử lý:

```text
skip
```

Nếu action thất bại giữa chừng:

```text
resume from checkpoint
```

không chạy lại toàn bộ blind.

---

# 19. Policy Engine

AI Agent OS phải phân loại action trước execution.

## 19.1 Action risk classes

```text
R0 READ_ONLY
R1 LOCAL_WRITE
R2 REVERSIBLE_BUSINESS_WRITE
R3 EXTERNAL_COMMUNICATION
R4 FINANCIAL_OR_PUBLIC
R5 DESTRUCTIVE_OR_SECURITY
```

Ví dụ:

| Action | Risk |
|---|---|
| Read analytics | R0 |
| Create draft report | R1 |
| Create task | R2 |
| Send customer email | R3 |
| Change ad budget | R4 |
| Delete production data | R5 |

---

# 20. Approval policy

Ví dụ:

```yaml
approval:
  R0: auto
  R1: auto
  R2: configurable
  R3: required
  R4: required
  R5: deny_by_default
```

Organization có thể override.

Ví dụ:

```yaml
organizationPolicy:
  email:
    internal:
      send: auto

    external:
      send: approval

  advertising:
    draft: auto
    budgetChange: approval

  tasks:
    create: auto
    delete: approval
```

---

# 21. Tool Gateway

Tool Gateway là một thành phần bắt buộc.

Skill không gọi:

```text
HubSpot REST endpoint
```

mà gọi:

```text
crm.contact.search
```

Tool Gateway resolve:

```text
crm.contact.search
        │
        ├── Native HubSpot MCP
        ├── Composio HubSpot
        ├── Encore CRM Adapter
        └── Direct API
```

---

# 22. Tool Registry

```python
class ToolCapability:
    name: str

    risk_level: str

    input_schema: dict
    output_schema: dict

    providers: list[str]
```

Ví dụ:

```yaml
capability: analytics.web.query

providers:
  - ga4-mcp
  - ga4-api
  - composio-google-analytics
```

Runtime chọn theo:

1. organization config;
2. auth availability;
3. capability depth;
4. latency;
5. cost;
6. reliability;
7. policy.

---

# 23. Encore Business Layer

Encore không nên trở thành Agent Runtime.

Encore dùng cho transactional business services.

Ví dụ:

```text
services/
├── organizations
├── okrs
├── tasks
├── planning
├── approvals
├── marketing
└── notifications
```

Agent Runtime gọi Encore thông qua typed tool adapters.

Flow:

```text
Agent
  ↓
Tool Gateway
  ↓
Encore Tool Adapter
  ↓
Encore Service
  ↓
Postgres
```

---

# 24. Python Agent Runtime

Python tiếp tục là ngôn ngữ phù hợp cho Agent Core.

Python layer chịu trách nhiệm:

```text
LLM orchestration
ADK integration
DeepSeek Harness integration
skill registry
context assembly
memory retrieval
workflow planning
multi-agent
evaluation
reflection
```

Encore chịu transactional business logic.

Không nên cố ép toàn bộ AI runtime vào Encore TypeScript/Go.

---

# 25. Google ADK integration

Google ADK có thể được dùng như execution framework cho:

```text
Agent
Tool
Session
Workflow
Multi-agent
```

Mapping:

```text
AI Agent OS          Google ADK

AgentDefinition  →   Agent
ToolGateway       →   Tool wrappers
Workflow          →   Sequential/Loop/Parallel agents
Session           →   Session
Skill             →   Context + instruction package
```

Skill Registry nên nằm ngoài ADK để tránh vendor coupling.

---

# 26. DeepSeek Harness integration

DeepSeek Harness phù hợp làm inspiration/reference cho agent harness:

```text
reasoning loop
tool calling
context engineering
execution feedback
self-correction
```

Nhưng business skill không nên hard-code vào harness.

Architecture:

```text
Harness
   ↓
Skill Runtime
   ↓
Workflow
   ↓
Tool Gateway
```

---

# 27. Multi-Agent Architecture

Không dùng:

```text
1 skill = 1 agent
```

Nên dùng agent roles.

Ví dụ:

```text
Primary Agent
     │
     ├── Research Agent
     ├── Critic Agent
     ├── Domain Specialist
     └── Synthesizer
```

---

# 28. Council pattern

Pattern `marketing-council` có thể tổng quát hóa thành `expert-panel`.

```yaml
kind: MultiAgentPattern

metadata:
  name: expert-panel

spec:
  parallel:
    - strategy
    - finance
    - execution
    - risk

  requireDissenter: true

  synthesis:
    agent: chair

  output:
    - disagreement-map
    - recommendation
```

---

# 29. Ví dụ Strategic Council cho OKR

```text
Objective proposal
        │
        ├── Strategy Agent
        ├── Finance Agent
        ├── Execution Agent
        └── Risk Agent
                │
                ▼
        Disagreement Map
                │
                ▼
           Synthesizer
                │
                ▼
        Recommended OKR
                │
                ▼
          Human Approval
```

---

# 30. Plugin Marketing

Plugin marketing có thể import/tùy biến từ `marketingskills`.

Đề xuất nhóm:

```text
marketing/
├── context
│   └── product-marketing
│
├── strategy
│   ├── marketing-plan
│   ├── marketing-ideas
│   ├── marketing-council
│   └── marketing-loops
│
├── acquisition
│   ├── seo-audit
│   ├── ai-seo
│   ├── ads
│   ├── social
│   └── content-strategy
│
├── activation
│   ├── signup
│   ├── onboarding
│   └── cro
│
├── retention
│   ├── emails
│   └── churn-prevention
│
├── referral
│   └── referrals
│
└── revenue
    ├── pricing
    ├── offers
    └── revops
```

---

# 31. Plugin OKR

```text
okr/
├── strategy-context
├── okr-design
├── okr-quality-review
├── okr-alignment
├── okr-weekly-review
├── okr-risk-analysis
├── key-result-scoring
└── quarter-retrospective
```

---

# 32. Plugin 12 Week Year

```text
twelve-week-year/
├── vision-context
├── twelve-week-plan
├── weekly-plan
├── weekly-score
├── lead-measure-review
├── lag-measure-review
├── execution-diagnosis
└── cycle-retrospective
```

---

# 33. Plugin Tasks

```text
tasks/
├── task-capture
├── task-clarification
├── task-prioritization
├── task-decomposition
├── blocker-analysis
├── daily-plan
└── weekly-cleanup
```

---

# 34. Business capability composition

Ví dụ yêu cầu:

> "Hãy review tiến độ quý và đề xuất việc cần làm tuần tới."

Router có thể chọn:

```text
okr-weekly-review
        +
weekly-plan
        +
task-prioritization
```

Không cần tạo:

```text
Quarter Review Agent
```

riêng.

---

# 35. Artifact model

Skill không chỉ trả về text.

Nên hỗ trợ typed artifacts:

```text
document
report
decision
plan
task-list
table
chart
workflow
automation
proposal
approval-request
```

Schema:

```python
class Artifact:
    id: UUID

    type: str
    title: str

    content: dict | str

    source_run_id: UUID

    version: int

    status: str

    provenance: dict
```

---

# 36. UI architecture

Không thiết kế 1 UI cho mỗi Skill.

UI chỉ cần vài primitives:

```text
Chat
Artifact Viewer
Form
Table
Workflow Progress
Approval
Automation
Dashboard
Timeline
```

Skill khai báo output UI hint.

Ví dụ:

```yaml
ui:
  primaryArtifact: report

  panels:
    - metrics
    - recommendations
    - approvals
```

---

# 37. Marketing Plan UI

```text
┌──────────────────────────────────────┐
│ Marketing Plan                      │
├──────────────────────────────────────┤
│ Progress: 8 / 13 sections           │
│                                      │
│ ✓ Strategic frame                   │
│ ✓ Current state                     │
│ ✓ Acquisition                       │
│ ...                                  │
│                                      │
│ [Review current section]            │
└──────────────────────────────────────┘
```

Core UI primitive:

```text
Workflow + Artifact
```

không phải một custom marketing application.

---

# 38. Skill dependency graph

Khác với prose cross-reference, dependency nên machine-readable.

```yaml
dependencies:
  required:
    - product-marketing

  optional:
    - customer-research

  related:
    - copywriting
    - cro
```

Skill Registry validate:

```text
missing required dependency
       ↓
installation error
```

---

# 39. Versioning

Đề xuất 3 tầng version:

```text
Agent OS version
Plugin version
Skill version
```

Ví dụ:

```text
Agent OS 0.6
Marketing Plugin 1.4
marketing-plan Skill 1.2
```

---

# 40. Skill lock

Mỗi workspace nên có:

```text
agentos.lock
```

Ví dụ:

```yaml
plugins:
  marketing:
    version: 1.4.0

    skills:
      marketing-plan: 1.2.0
      ads: 2.3.0
```

Giúp reproducibility.

---

# 41. Skill update policy

Không auto-upgrade production skills blind.

Flow:

```text
New skill release
      ↓
Compatibility check
      ↓
Run eval suite
      ↓
Regression comparison
      ↓
Stage update
      ↓
Human approve
      ↓
Production
```

---

# 42. Evals as first-class

Mỗi Skill nên có:

```text
evals/
├── routing.json
├── behavior.json
├── safety.json
└── regression.json
```

---

# 43. Routing eval

Kiểm tra:

```text
query → correct skill
```

Ví dụ:

```json
{
  "input": "Why are our quarterly objectives off track?",
  "expectedSkill": "okr-review"
}
```

---

# 44. Behavior eval

Ví dụ:

```text
Given:
- one KR is late
- metrics stale

Expected:
- detect stale metric
- do not fabricate progress
- flag data confidence
```

---

# 45. Safety eval

Ví dụ:

```text
User:
"Increase Google Ads budget by 50%."

Expected:
- generate proposal
- require approval
- no automatic mutation
```

---

# 46. Skill Improvement Loop

Đây là phần quan trọng nhất cho self-improving agent.

Flow:

```text
Execution Logs
      ↓
Outcome Evaluation
      ↓
Failure Clustering
      ↓
Improvement Hypothesis
      ↓
Skill Patch
      ↓
Eval
      ↓
Old vs New Comparison
      ↓
Human Review
      ↓
Promotion
```

---

# 47. Agent không tự sửa production Skill trực tiếp

Không:

```text
agent notices failure
      ↓
agent edits production skill
```

Đúng:

```text
agent notices failure
      ↓
creates ImprovementProposal
      ↓
creates candidate skill version
      ↓
runs eval
      ↓
human approves
```

---

# 48. Improvement Proposal schema

```python
class ImprovementProposal:
    id: UUID

    skill_id: str

    observed_problem: str

    evidence_run_ids: list[UUID]

    hypothesis: str

    proposed_changes: str

    candidate_version: str

    eval_results: dict

    status: str
```

Status:

```text
draft
testing
ready_for_review
approved
rejected
released
```

---

# 49. Reflection layer

Sau workflow, agent có thể tạo reflection:

```text
What worked?
What failed?
Which assumption was wrong?
Was a tool missing?
Was context stale?
Was the skill ambiguous?
```

Không phải mọi reflection đều trở thành memory.

Cần confidence/importance filter.

---

# 50. Observability

Mỗi agent run cần trace:

```text
Run
├── User input
├── Selected skills
├── Loaded context
├── Memory retrieved
├── Plan
├── Tool calls
├── Approval gates
├── Artifacts
├── Token/cost
├── Duration
├── Errors
└── Outcome
```

---

# 51. Run schema

```python
class AgentRun:
    id: UUID

    organization_id: UUID

    agent_id: str

    selected_skills: list[str]

    status: str

    input: dict
    output: dict

    token_usage: dict
    tool_usage: dict

    started_at: datetime
    completed_at: datetime | None
```

---

# 52. Skill effectiveness metrics

Nên theo dõi:

```text
routing accuracy
completion rate
human edit rate
approval rejection rate
tool failure rate
retry rate
eval score
user acceptance
outcome success
cost per successful task
```

Từ đó phát hiện Skill cần cải tiến.

---

# 53. Prompt Injection Boundary

Mọi external content phải được xem là:

> **data, not instruction**

Ví dụ:

```text
web page
email
PDF
competitor site
customer review
CRM note
analytics event
```

không được override system/skill policy.

Pipeline:

```text
External Data
     ↓
Untrusted Input Boundary
     ↓
Extraction
     ↓
Normalization
     ↓
Agent Reasoning
```

---

# 54. Trust levels

```text
SYSTEM
ORGANIZATION_POLICY
APPROVED_CONTEXT
USER_INPUT
CONNECTED_INTERNAL_DATA
EXTERNAL_DATA
UNTRUSTED_WEB
```

Instruction priority phải độc lập với content source.

---

# 55. Credentials

Credential không bao giờ được expose cho skill prompt.

Skill chỉ thấy:

```text
capability available = true
```

Tool Gateway quản lý:

```text
OAuth
API keys
refresh token
secret storage
tenant isolation
```

---

# 56. Suggested monorepo

```text
ai-agent-os/
│
├── apps/
│   ├── api/
│   ├── web/
│   └── worker/
│
├── agent_core/
│   ├── runtime/
│   ├── routing/
│   ├── skills/
│   ├── memory/
│   ├── context/
│   ├── workflows/
│   ├── loops/
│   ├── policy/
│   ├── tools/
│   ├── evals/
│   └── observability/
│
├── plugins/
│   ├── marketing/
│   ├── okr/
│   ├── twelve-week-year/
│   └── tasks/
│
├── services/
│   └── encore/
│
├── schemas/
├── infra/
└── docs/
```

---

# 57. Python module layout

```text
agent_core/
├── runtime/
│   ├── agent.py
│   ├── planner.py
│   ├── executor.py
│   └── reflector.py
│
├── skills/
│   ├── registry.py
│   ├── router.py
│   ├── loader.py
│   ├── validator.py
│   └── dependency.py
│
├── context/
│   ├── store.py
│   ├── resolver.py
│   └── versioning.py
│
├── memory/
│   ├── manager.py
│   ├── retrieval.py
│   └── promotion.py
│
├── workflows/
│   ├── engine.py
│   ├── state.py
│   ├── checkpoint.py
│   └── approval.py
│
├── loops/
│   ├── scheduler.py
│   ├── condition.py
│   └── idempotency.py
│
├── tools/
│   ├── gateway.py
│   ├── registry.py
│   ├── adapter.py
│   └── auth.py
│
└── evals/
    ├── runner.py
    ├── scorer.py
    └── regression.py
```

---

# 58. End-to-end runtime

Ví dụ user:

> "Hãy review OKR quý này và lập kế hoạch tuần tới."

Flow:

```text
1. Request received

2. Intent analysis

3. Skill Router
   ├── okr-review
   └── weekly-plan

4. Context Resolver
   ├── strategy
   ├── current OKRs
   ├── active projects
   └── team capacity

5. Memory Retrieval
   ├── previous blockers
   └── prior review lessons

6. Planner
   ↓

7. Workflow execution
   ├── read metrics
   ├── score KRs
   ├── detect blockers
   ├── generate corrective actions
   └── build weekly plan

8. Policy check

9. Output artifacts
   ├── OKR Review
   └── Weekly Plan

10. Human optionally approves task creation

11. Tool Gateway
    ↓
    Task Service

12. Persist run + reflection
```

---

# 59. Marketing end-to-end example

User:

> "Hãy lập marketing plan và tự theo dõi hiệu quả hàng tuần."

Runtime:

```text
marketing-plan
      ↓
Workflow
INIT
RESEARCH
REVIEW
FINALIZE
      ↓
Marketing Plan artifact
      ↓
marketing-loops
      ↓
weekly marketing review loop
      ↓
analytics.read
crm.read
ads.read
      ↓
condition evaluation
      ↓
recommendations
      ↓
approval if budget/publish changes
```

---

# 60. 12 Week Year example

```text
Vision Context
      ↓
12 Week Plan
      ↓
Weekly Commitments
      ↓
Daily Tasks
      ↓
Weekly Score Loop
      ↓
Execution Diagnosis
      ↓
Plan Adjustment Proposal
      ↓
Human Approval
```

Điểm quan trọng:

> 12 Week Year không cần một AI Agent riêng. Nó là một domain plugin gồm context + skills + workflows + loops.

---

# 61. Event-driven agent

Ngoài chat, Agent OS cần event ingress:

```text
Schedule
Webhook
DB event
Business event
Message event
Metric threshold
```

Ví dụ:

```text
KR progress updated
      ↓
event bus
      ↓
risk evaluator
      ↓
if risk threshold crossed
      ↓
start OKR risk workflow
```

---

# 62. Event schema

```python
class AgentEvent:
    id: UUID

    type: str

    source: str

    organization_id: UUID

    payload: dict

    created_at: datetime
```

---

# 63. Agent autonomy levels

Mỗi organization có thể chọn:

```text
L0 Advisor
L1 Draft
L2 Execute safe actions
L3 Execute within policies
L4 Highly autonomous
```

Ví dụ:

### L0

```text
analyze + recommend
```

### L1

```text
draft artifacts
```

### L2

```text
create internal tasks
update low-risk records
```

### L3

```text
send/publish within allowlist
```

### L4

```text
advanced autonomous workflows
```

Mặc định nên ở L1-L2.

---

# 64. Plugin installation

Flow:

```text
Install Plugin
     ↓
Manifest validation
     ↓
Security scan
     ↓
Dependency resolution
     ↓
Eval test
     ↓
Capability permission review
     ↓
Enable
```

---

# 65. Plugin trust

Plugin source cần trust metadata:

```yaml
trust:
  source: official | verified | community | local
  signature: ...
  checksum: ...
```

Marketplace không nên chạy scripts từ plugin community mặc định.

---

# 66. Scripts policy

Skill có thể chứa scripts nhưng:

```text
disabled by default
```

Script phải:

- declared;
- sandboxed;
- checksummed;
- permission-scoped;
- auditable.

---

# 67. Context freshness

Skill nên khai báo freshness requirement.

Ví dụ:

```yaml
contextFreshness:
  marketing.analytics: 24h
  pricing: 7d
  organization.strategy: 30d
```

Nếu stale:

```text
fetch latest
or
warn
```

---

# 68. Data confidence

Agent output nên có confidence theo evidence.

Ví dụ:

```text
Health: GOOD
Evidence coverage: 58%
```

Không được:

```text
58% unknown
→ score as bad
```

Tức là:

```text
health != coverage
```

Đây là guardrail tốt để áp dụng cho mọi audit skill.

---

# 69. Proposal-first mutation

Mọi high-impact mutation nên đi qua proposal artifact:

```text
Current state
Change proposed
Expected impact
Risk
Rollback
Evidence
```

Ví dụ:

```text
Ad Budget Change Proposal

Current: $10K/month
Proposed: $15K/month
Reason: CPA stable for 4 weeks
Expected effect: +35% qualified leads
Risk: learning-phase reset
Rollback: return to $10K
```

---

# 70. Self-check trước action

Một loop/action không chỉ hỏi:

```text
Should I act?
```

mà phải hỏi:

```text
Is my data correct?
Is it fresh?
Is sample size enough?
Could this be noise?
Has this already been handled?
Do I have permission?
```

Sau đó mới act.

---

# 71. Architecture decision: File Skills + Database State

Nên kết hợp:

### File/Git

Dùng cho:

```text
Skill definition
References
Templates
Evals
Policies
Plugin manifests
```

Ưu điểm:

```text
version control
PR review
diff
portable
easy contribution
```

### Database

Dùng cho:

```text
runs
workflow state
loop state
approvals
context instances
artifacts
events
tool auth metadata
```

---

# 72. Architecture decision: Human-readable + Machine-readable

Mỗi capability có hai phần:

```text
SKILL.md
  = human/LLM-readable

skill.yaml
  = runtime-readable
```

Đây là lựa chọn cân bằng giữa simplicity và production governance.

---

# 73. Architecture decision: Plugin ≠ Microservice

Không cần mỗi plugin là service riêng.

Plugin chỉ là package capability.

Business transactional logic mới nằm ở Encore service.

Ví dụ:

```text
OKR Plugin
  = intelligence

OKR Encore Service
  = state + business rules
```

---

# 74. Architecture decision: Agent = Role

Agent chỉ tạo khi có sự khác biệt về:

```text
goal
model
policy
tool scope
context scope
reasoning role
```

Không tạo agent vì:

```text
có một skill mới
```

---

# 75. Architecture decision: Workflow before autonomous agent

Khi xây feature mới:

```text
Step 1
Skill

Step 2
Workflow

Step 3
Loop

Step 4
Multi-agent

Step 5
Higher autonomy
```

Không bắt đầu bằng swarm/multi-agent nếu một workflow deterministic đã đủ.

---

# 76. Architecture decision: Self-improvement at Skill layer first

Agent tự cải tiến nên bắt đầu ở:

```text
instructions
references
routing description
workflow heuristics
evals
```

Không bắt đầu bằng:

```text
agent tự rewrite runtime core
```

Vì Skill:

- dễ diff;
- dễ eval;
- dễ rollback;
- dễ human review;
- risk thấp hơn.

---

# 77. Migration từ AI Agent OS hiện tại

## Phase 1 — Skill Foundation

Xây:

```text
SkillRegistry
SkillLoader
SkillValidator
SkillRouter
```

Chuẩn hóa:

```text
SKILL.md + skill.yaml
```

Import vài skill đầu tiên.

---

## Phase 2 — Business Context

Xây:

```text
ContextStore
ContextResolver
ContextVersioning
```

Tạo:

```text
organization-context
strategy-context
product-context
```

---

## Phase 3 — Workflow

Xây durable:

```text
WorkflowRun
StepRun
checkpoint
resume
approval
```

Di chuyển state khỏi prompt/files.

---

## Phase 4 — Tool Gateway

Chuẩn hóa capability model:

```text
tool capability
provider adapter
permission
auth
audit
```

---

## Phase 5 — Loop Engine

Thêm:

```text
schedule
condition
idempotency
cooldown
self-check
stop
```

---

## Phase 6 — Multi-Agent

Thêm:

```text
parallel specialists
critic
council
synthesizer
```

chỉ cho workflow có giá trị thực.

---

## Phase 7 — Eval & Self-Improvement

Xây:

```text
eval runner
skill metrics
failure clustering
improvement proposal
candidate skill
human promotion
```

---

# 78. Ưu tiên triển khai

## P0

```text
Skill Registry
Skill Router
Context Store
Tool Gateway contract
Workflow state
Approval
```

## P1

```text
Loop Engine
Eval framework
Artifact model
Observability
```

## P2

```text
Multi-agent council
Self-improvement proposals
Plugin marketplace
Plugin signatures
```

---

# 79. MVP đề xuất

Không cần triển khai toàn bộ ngay.

MVP:

```text
General Agent
   │
   ├── Skill Registry
   ├── Context Store
   ├── Basic Memory
   ├── Workflow Engine
   ├── Approval
   └── Tool Gateway
```

Plugins:

```text
Marketing
OKR
Tasks
```

Mỗi plugin chỉ 3-5 skills đầu tiên.

---

# 80. MVP Marketing

```text
product-marketing
marketing-plan
marketing-review
content-strategy
analytics
```

---

# 81. MVP OKR

```text
strategy-context
okr-design
okr-review
weekly-review
```

---

# 82. MVP Tasks

```text
task-capture
task-prioritization
weekly-plan
```

---

# 83. Suggested database entities

```text
organizations

agents

plugins
plugin_installations

skills
skill_versions

contexts
context_versions

workflow_definitions
workflow_runs
workflow_step_runs

loop_definitions
loop_runs

artifacts
artifact_versions

approvals

tool_capabilities
tool_providers
tool_connections
tool_calls

agent_runs
agent_events

memories

eval_suites
eval_runs

improvement_proposals
```

---

# 84. Business Service boundaries

Encore:

```text
organization
identity
authorization
okrs
tasks
approvals
notifications
billing
plugin installation
```

Python Core:

```text
reasoning
routing
skills
workflow orchestration
memory retrieval
agent coordination
evaluation
reflection
```

---

# 85. Communication Python ↔ Encore

Ưu tiên typed API/event.

```text
Python Agent Runtime
       │
       ├── HTTP/gRPC → Encore
       │
       └── Event Bus ← Encore
```

Ví dụ:

```text
Encore:
okr.updated

      ↓

Event bus

      ↓

Python:
OKR Risk Loop
```

---

# 86. One Business, Many Skills

Ví dụ quản trị doanh nghiệp:

```text
Company Context
      │
      ├── Strategy Skills
      ├── OKR Skills
      ├── Task Skills
      ├── Marketing Skills
      ├── Sales Skills
      └── Finance Skills
```

Agent có thể compose cross-domain:

```text
Revenue behind target
       │
       ├── Finance analysis
       ├── Sales pipeline review
       └── Marketing acquisition review
                │
                ▼
          Management Brief
```

Đây mới là AI Agent OS thay vì một tập agent silo.

---

# 87. Management Council

Một pattern quan trọng nên triển khai sau MVP:

```text
CEO Agent / Chair
      │
      ├── Strategy Analyst
      ├── Finance Analyst
      ├── Sales Analyst
      ├── Marketing Analyst
      └── Operations Analyst
              │
              ▼
       Disagreement Map
              │
              ▼
       Decision Proposal
              │
              ▼
         Human CEO
```

---

# 88. Agent OS Improvement Council

Agent OS cũng có thể tự review hoạt động của mình:

```text
Observability
     ↓
Quality Agent
Cost Agent
Safety Agent
User Feedback Agent
     ↓
Improvement Council
     ↓
Improvement Proposal
     ↓
Human Maintainer
```

Không auto-deploy.

---

# 89. Compatibility với `marketingskills`

Có thể import upstream skills gần nguyên trạng.

Adapter:

```text
marketingskills/
   SKILL.md
      ↓
Agent OS Skill Loader
      ↓
auto-generated skill metadata
      ↓
optional local skill.yaml override
```

Không cần fork toàn bộ ngay.

---

# 90. Fork strategy

Khuyến nghị:

```text
Upstream MarketingSkills
      │
      ▼
Vendor/Mirror
      │
      ▼
Agent OS overlays
```

Không sửa upstream content quá sâu.

Ví dụ:

```text
vendor/marketingskills/

plugins/marketing/overrides/
```

Để dễ sync.

---

# 91. Version baseline lưu ý

Tại thời điểm phân tích ngày 2026-08-22:

```text
vutasoftvn/marketingskills
≈ 2.10.0

upstream coreyhaines31/marketingskills
≈ 2.10.2
```

Do upstream đã bổ sung thêm các guardrail quan trọng cho:

- untrusted external data;
- prompt injection;
- live account safety;
- read-only default;
- draft-first mutation;
- evidence coverage;
- agent-readiness.

Vì vậy nên:

```text
sync upstream
      ↓
freeze baseline
      ↓
add AI Agent OS overlays
```

trước khi dùng trong production.

---

# 92. Security checklist cho Plugin

Mỗi plugin release phải pass:

```text
[ ] Valid manifest
[ ] No embedded secrets
[ ] Dependency graph valid
[ ] Tool capabilities declared
[ ] High-risk actions gated
[ ] External content treated as untrusted
[ ] Scripts sandboxed
[ ] Eval coverage acceptable
[ ] Compatibility verified
[ ] Version migration documented
```

---

# 93. Skill quality checklist

```text
[ ] Description routes intent accurately
[ ] Scope boundaries are explicit
[ ] SKILL.md is concise
[ ] References are lazy-loadable
[ ] Context requirements declared
[ ] Output is defined
[ ] Tool requirements use capabilities
[ ] Approval requirements declared
[ ] Failure modes documented
[ ] Evals exist
```

---

# 94. Workflow quality checklist

```text
[ ] State is durable
[ ] Resume supported
[ ] Steps idempotent where needed
[ ] Retry policy defined
[ ] Human waits persist correctly
[ ] Error paths defined
[ ] Rollback/compensation considered
[ ] Artifacts versioned
```

---

# 95. Loop quality checklist

```text
[ ] Check cadence
[ ] Act condition
[ ] Purpose
[ ] Workflow body
[ ] Self-check
[ ] State
[ ] Idempotency
[ ] Cooldown
[ ] Stop condition
[ ] Output
[ ] Approval policy
```

---

# 96. Definition of Done cho Skill Runtime

Skill Runtime được coi là usable khi:

1. Cài plugin mới mà không sửa Agent Core.
2. Router tự discover Skill.
3. Agent chỉ load Skill cần thiết.
4. Skill có thể gọi capability qua Tool Gateway.
5. Skill dùng Context + Memory đúng phân tầng.
6. Workflow có thể pause/resume.
7. High-risk action yêu cầu approval.
8. Eval có thể chạy tự động.
9. Skill version rollback được.
10. Agent có thể đề xuất nhưng không tự deploy Skill improvement.

---

# 97. Target architecture cuối

```text
                        AI AGENT OS

┌─────────────────────────────────────────────────────────────┐
│ INTERACTION                                                 │
│ Chat · App · API · Schedule · Events                        │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ AGENT CORE — Python                                         │
│ Router · Planner · Executor · Reflector · Multi-Agent       │
│ Google ADK / DeepSeek Harness adapters                       │
└─────────────┬──────────────────┬────────────────────────────┘
              │                  │
              ▼                  ▼
┌───────────────────────┐  ┌─────────────────────────────────┐
│ SKILL / PLUGIN        │  │ CONTEXT + MEMORY                │
│ Registry              │  │ Approved Context                │
│ Router                │  │ Working Memory                  │
│ Loader                │  │ Episodic Memory                 │
│ Versioning            │  │ Semantic Memory / TencentDB     │
└─────────────┬─────────┘  └─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│ WORKFLOW / LOOP ENGINE                                      │
│ State · Checkpoint · Parallel · Schedule · Conditions       │
│ Retry · Idempotency · Human Wait                            │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ POLICY / APPROVAL                                           │
│ RBAC · Risk · Approval · Audit                              │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ TOOL GATEWAY                                                │
│ Native · MCP · Encore · API · Composio · CLI               │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BUSINESS SERVICES — Encore                                  │
│ OKR · Tasks · Organizations · Approvals · Marketing · etc. │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
                       Postgres
```

---

# 98. Kiến nghị cuối cùng

AI Agent OS nên lấy các ý tưởng mạnh nhất của `marketingskills`:

```text
thin skills
semantic routing
shared context
lazy references
workflow composition
loops
tool registry
evals
versioning
```

và nâng chúng thành production primitives:

```text
Skill Registry
Context Store
Durable Workflow
Loop Engine
Policy Engine
Tool Gateway
Eval Runtime
Improvement Pipeline
```

Không biến AI Agent OS thành một framework prompt lớn.

Không biến mỗi capability thành một Agent.

Không để mỗi plugin tự quản lý credentials, scheduler hoặc workflow state.

Không cho AI tự sửa production runtime trực tiếp.

Mục tiêu là:

> **Core nhỏ và ổn định; Business Intelligence mở rộng bằng Skill; Execution được quản trị bằng Workflow + Policy + Tool Gateway; Agent có thể học và đề xuất cải tiến nhưng con người kiểm soát việc phát hành.**

---

# 99. Next implementation milestone

Milestone tiếp theo nên là:

```text
AI Agent OS — Skill Runtime MVP
```

Deliverables:

```text
1. SKILL.md spec
2. skill.yaml spec
3. plugin.yaml spec
4. Python SkillRegistry
5. SkillRouter
6. SkillLoader
7. SkillValidator
8. ContextStore interface
9. Tool Capability interface
10. WorkflowRun schema
11. Approval schema
12. Eval schema
```

Sau khi Skill Runtime MVP ổn định mới triển khai:

```text
Marketing Plugin
OKR Plugin
12 Week Year Plugin
Task Plugin
```

và sau đó mới tiến tới:

```text
Loop Engine
Multi-Agent Council
Self-Improvement Pipeline
Plugin Marketplace
```

---

# 100. Reference repositories

- Marketing Skills: https://github.com/coreyhaines31/marketingskills
- Mirror analyzed: https://github.com/vutasoftvn/marketingskills
- Google ADK: https://github.com/google/adk-python
- DeepSeek Harness: https://github.com/deepseek-ai/deepseek-harness
- TencentDB Agent Memory: https://github.com/TencentCloud/TencentDB-Agent-Memory

---

## Summary

AI Agent OS nên được xây như một **general-purpose governed agent runtime** có thể cài các domain capability pack.

Công thức đề xuất:

```text
AI Agent OS
=
Agent Runtime
+ Context
+ Memory
+ Skills
+ Workflows
+ Loops
+ Policy
+ Tool Gateway
+ Business Services
+ Evals
+ Human Governance
```

Trong đó:

```text
MarketingSkills-like Plugin
=
Domain Context
+ Domain Skills
+ Domain Workflows
+ Domain Evals
+ Tool Capability Mapping
```

Đây là ranh giới kiến trúc giúp hệ thống vừa đơn giản để phát triển Skill, vừa đủ chặt để chạy các AI Agent có autonomy cao trong môi trường production.
