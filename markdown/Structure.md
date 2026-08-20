# COSA AGENT HARNESS ARCHITECTURE

**Architecture Refactoring & Claude Code Implementation Specification**

**Trạng thái:** Proposed Target Architecture
**Phạm vi:** Toàn bộ COSA
**Mục tiêu:** Chuyển COSA từ kiến trúc nhiều AI Agent rời rạc thành Founder/Company Operating System sử dụng một Agent Harness có khả năng composition.

---

# 1. Mục tiêu tái cấu trúc

COSA không được tiếp tục phát triển theo mô hình:

```text
Marketing Agent
Sales Agent
Finance Agent
Legal Agent
Research Agent
Coding Agent
...
```

trong đó mỗi agent có runtime, prompt, tool và logic riêng.

Kiến trúc mục tiêu:

```text
COSA
=
Founder / Company Operating System
+
Composable Agent Harness
```

Công thức chuẩn:

```text
COSA Agent
=
Agent Profile
+
Model
+
Context
+
Skills
+
Tools
+
Workflows
+
Memory
+
Permissions
+
Agent Runtime
```

Các "Agent" Marketing, Sales, Finance... vẫn tồn tại về mặt trải nghiệm người dùng và business role nhưng KHÔNG phải những runtime độc lập.

---

# 2. Nguyên tắc kiến trúc

## 2.1 One Runtime — Multiple Capabilities

COSA chỉ duy trì một abstraction chung:

```text
COSA Agent Runtime
```

Các vai trò khác nhau được compose từ:

```text
Agent Profile
Skills
Tools
Workflows
Knowledge
Permissions
Model Policy
```

Ví dụ:

```yaml
agent:
  id: marketing
  role: CMO

skills:
  - market-research
  - positioning
  - copywriting

tools:
  - web-search
  - crm
  - analytics

workflows:
  - market-analysis
  - campaign-planning

permissions:
  - internet.read
  - crm.read
  - crm.write
```

---

# 3. Không fork DeepSeek Harness

DeepSeek Harness là nguồn kiến trúc và có thể trở thành runtime adapter.

Không biến COSA thành fork của DeepSeek Harness.

Bắt buộc:

```text
COSA Business Core
        ↓
COSA Agent Runtime Interface
        ↓
Runtime Adapter
        ↓
DeepSeek Harness
```

Không:

```text
COSA
↓
DeepSeek Harness internals
```

Mục tiêu là COSA có thể thay runtime mà không thay Business Core.

---

# 4. Kiến trúc tổng thể

```text
┌───────────────────────────────────────┐
│                COSA UI                │
│                                       │
│ Desktop │ Mobile │ Hologram Hub       │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│          COSA APPLICATION API         │
│                                       │
│ Auth │ Project │ Task │ Chat │ Agent  │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│          COSA BUSINESS CORE           │
│                                       │
│ Company                               │
│ Project                               │
│ Startup Stage                         │
│ OKR                                   │
│ 12 Week Year                          │
│ Task                                  │
│ CRM                                   │
│ Marketing                             │
│ Sales                                 │
│ Finance                               │
│ Legal                                 │
│ Knowledge                             │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│       CO-FOUNDER ORCHESTRATOR         │
│                                       │
│ Intent Router                         │
│ Context Resolver                      │
│ Capability Resolver                   │
│ Workflow Selector                     │
│ Agent Composer                        │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│          COSA AGENT HARNESS           │
│                                       │
│ Runtime                               │
│ Agent Loop                            │
│ Model Router                          │
│ Context Engine                        │
│ Skills                                │
│ Tools                                 │
│ Workflows                             │
│ Subagents                             │
│ Sessions                              │
│ Memory                                │
│ Permissions                           │
│ Sandbox                               │
│ Event Store                           │
│ Trajectory                            │
└──────┬─────────────┬────────────┬─────┘
       │             │            │
       ▼             ▼            ▼
DeepSeek Harness  Native       Executors
Adapter           Runtime         │
                                 ├ Claude Code
                                 ├ Codex
                                 ├ Shell
                                 ├ Browser
                                 ├ MCP
                                 ├ n8n
                                 └ APIs
```

---

# 5. Business Core phải độc lập với AI

Đây là nguyên tắc bắt buộc.

Các entity:

```text
Company
Project
Customer
Lead
Opportunity
Invoice
OKR
Task
Campaign
```

không được phụ thuộc:

```text
DeepSeek
Claude
OpenAI
Harness
Prompt
LLM
```

Ví dụ không được:

```python
class Project:
    deepseek_session_id
    claude_prompt
```

Nên:

```text
Project
   │
AgentSession
   │
RuntimeSession
```

Business data tồn tại ngay cả khi không có AI.

---

# 6. Company Architecture

COSA tiếp tục theo mô hình:

```text
ONE INSTALLATION
=
ONE COMPANY
```

Không thiết kế multi-tenant SaaS vào local application.

Company sở hữu:

```text
projects
users
roles
API keys
business data
knowledge
agent sessions
prompts
skills
workflows
```

Founder ban đầu là:

```text
ADMIN
```

Sau này có:

```text
Admin
Manager
Member
Viewer
Agent Operator
```

---

# 7. COSA Central Service

Central service chỉ quản lý những dữ liệu COSA thực sự cần:

```text
license
company registration
subscription/tier
entitlements
installation
version
update metadata
project statistics
startup stage statistics
anonymous/consented success metrics
```

Không mặc định đồng bộ:

```text
chat
CRM customers
financial data
legal documents
API keys
internal company knowledge
```

---

# 8. Agent Profile

Agent Profile chỉ định vai trò.

Ví dụ:

```yaml
id: marketing
name: Marketing
role: CMO

description:
  Chịu trách nhiệm nghiên cứu thị trường,
  positioning, acquisition và marketing execution.

skills:
  - market-research
  - customer-research
  - positioning
  - content-strategy

tools:
  - web
  - crm
  - analytics

workflows:
  - market-research
  - campaign-planning

model_policy:
  default: reasoning
```

Không nhúng implementation vào profile.

---

# 9. Skill Architecture

Skill là kiến thức/hướng dẫn để agent biết **cách thực hiện một năng lực**.

Ví dụ:

```text
skills/

marketing/
    market-research/
    positioning/
    customer-interview/
    copywriting/

sales/
    lead-generation/
    lead-qualification/
    follow-up/

startup/
    problem-discovery/
    jtbd/
    hypothesis-testing/
    pmf/

management/
    okr/
    12-week-year/
    weekly-review/
```

Skill KHÔNG phải agent.

---

# 10. Tool Architecture

Tool là khả năng thực hiện hành động.

Interface chuẩn:

```text
Tool
├── id
├── description
├── input_schema
├── output_schema
├── permissions
├── timeout
├── concurrency
├── execute()
└── presenter
```

Ví dụ:

```text
crm.search_leads
crm.create_lead

project.read
project.update

knowledge.search

web.search

filesystem.read
filesystem.write

n8n.trigger

hostinger.deploy
```

---

# 11. Tool Result phải chuẩn hóa

Không để mỗi integration trả JSON tùy ý.

Chuẩn:

```json
{
  "status": "success",
  "data": {},
  "metadata": {
    "duration_ms": 850
  },
  "error": null
}
```

Tool execution phải tạo event.

---

# 12. Tool Presenter

Mỗi tool có thể định nghĩa presentation cho Hologram Hub.

Ví dụ:

```text
crm.search_leads
```

không hiển thị raw JSON.

Hiển thị:

```text
Lead Research

Found       37
Qualified   12
High Intent 4

Completed
```

Presenter phải dùng được cho:

```text
live execution
session replay
trajectory
```

---

# 13. Workflow Architecture

Workflow mô tả business/agent process.

Ví dụ:

```yaml
id: lead-generation

steps:

  - skill: define-icp

  - tool: research.market

  - tool: leads.search

  - tool: leads.enrich
    parallel: true

  - skill: lead-scoring

  - tool: crm.save

  - skill: outreach-copy

  - tool: outreach.queue
```

Không viết workflow dài trong system prompt.

---

# 14. Co-founder Orchestrator

COSA Co-founder là entry point chính.

Nhiệm vụ:

```text
understand request
      ↓
classify intent
      ↓
resolve context
      ↓
select capability
      ↓
select workflow/agent
      ↓
execute
      ↓
present result
```

Co-founder không tự thực hiện mọi việc.

Nó điều phối capabilities.

---

# 15. Intent Router

Đây là component quan trọng để giải quyết lỗi COSA tự chạy flow khi không được yêu cầu.

Ví dụ:

```text
"chào"
```

phải:

```json
{
  "intent": "conversation.greeting",
  "project": null,
  "tools": [],
  "workflow": null
}
```

Không được tự:

```text
load project
search database
run analysis
```

---

# 16. Explicit Context Rule

Project context chỉ load khi có ít nhất một điều kiện:

```text
user explicitly mentions project
current session already scoped to project
workflow requires project
UI explicitly selected project
```

Greeting/general question không được trigger project lookup.

---

# 17. Context Engine

Context không phải toàn bộ database.

Pipeline:

```text
Intent
 ↓
Context Requirement
 ↓
Context Resolver
 ↓
Relevant Context
 ↓
Agent
```

Các scope:

```text
company
project
startup_stage
customer
campaign
task
knowledge
conversation
```

---

# 18. Context Budget

Không đưa toàn bộ dữ liệu vào LLM.

Context Engine phải:

```text
search
rank
filter
compress
inject
```

và log:

```text
context source
reason
token estimate
```

---

# 19. Session Architecture

Session phải append-only về mặt execution history.

```text
AgentSession
    │
    └── Events
```

Event types ví dụ:

```text
session.started

user.message

intent.detected

context.loaded

skill.loaded

workflow.started

model.requested

tool.requested

tool.completed

subagent.started

subagent.completed

artifact.created

workflow.completed

assistant.message

session.completed
```

---

# 20. Event Schema

Chuẩn tối thiểu:

```json
{
  "id": "evt_xxx",
  "session_id": "ses_xxx",
  "timestamp": "...",

  "type": "tool.completed",

  "actor": {
    "type": "agent",
    "id": "marketing"
  },

  "payload": {},

  "metadata": {
    "runtime": "deepseek-harness",
    "model": "...",
    "duration_ms": 1200
  }
}
```

---

# 21. Resume

Session có thể tiếp tục:

```text
Session
 ↓
restore state
 ↓
continue execution
```

---

# 22. Fork

Founder có thể fork analysis.

Ví dụ:

```text
Pricing Strategy
      │
 ┌────┼──────────┐
 ▼    ▼          ▼
License SaaS    Hybrid
```

Mỗi branch giữ:

```text
parent_session_id
fork_event_id
```

---

# 23. Replay

Replay dùng event log để reconstruct execution.

Mục tiêu:

```text
debug
audit
testing
UI
comparison
```

Không replay side effects mặc định.

Ví dụ:

```text
send_email
delete_file
deploy
payment
```

không được thực hiện lại khi replay.

---

# 24. Trajectory

Trajectory là operational explanation.

Không expose private chain-of-thought.

Hiển thị:

```text
09:00 Request received

09:00 Intent
market.research

09:01 Context
Project mID

09:01 Skill
market-research

09:02 Web Research
12 sources

09:04 Competitor Analysis

09:06 Result generated

09:07 Knowledge updated
```

---

# 25. Hologram Hub trở thành Agent Operations Center

Hologram Hub không chỉ là dashboard.

Nó phải hiển thị:

```text
Active runs
Recent runs
Waiting approvals
Failures
Completed workflows
Scheduled workflows
Agent activity
Artifacts
Important signals
```

Card:

```text
Market Research

Project
mID

Agent
Marketing

Status
RUNNING

Progress
3 / 5

Tools
8

Sources
24
```

Click mở trajectory.

---

# 26. Permission Architecture

Định nghĩa permission theo capability.

Ví dụ:

```text
filesystem.read
filesystem.write

shell.execute

network.read
network.write

crm.read
crm.write

finance.read
finance.write

deployment.execute

automation.trigger

prompt.admin

skill.admin

spec.admin
```

---

# 27. Risk Level

Mọi tool phải có risk:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Ví dụ:

```text
web.search
LOW

crm.create_lead
MEDIUM

deploy.production
HIGH

delete_database
CRITICAL
```

---

# 28. Approval Policy

Ví dụ:

```text
LOW
→ automatic

MEDIUM
→ policy dependent

HIGH
→ user approval

CRITICAL
→ admin approval
```

Không để model tự quyết định permission.

---

# 29. Prompt/Skill/Spec Protection

Các tài sản quan trọng:

```text
CLAUDE.md
system prompts
agent profiles
skills
workflow definitions
business specs
permission policy
```

chỉ Admin được sửa.

Phải hỗ trợ:

```text
version
history
reset to default
```

---

# 30. Model Router

Không hardcode một LLM.

Interface:

```text
ModelProvider
```

Provider có thể:

```text
DeepSeek
Anthropic
OpenAI
OpenAI-compatible
Local
```

Policy:

```text
fast
reasoning
coding
vision
local-private
```

Agent yêu cầu capability:

```text
reasoning
```

Router quyết định model.

Không để business code gọi trực tiếp model name.

---

# 31. Executor Architecture

Phân biệt:

```text
Agent Runtime
```

và:

```text
Executor
```

Executor:

```text
Claude Code
Codex
Shell
Browser
n8n
Hostinger
MCP
```

Ví dụ:

```text
Coding Workflow
      ↓
COSA Harness
      ↓
Coding Executor
      ↓
Claude Code
```

Claude Code không phải COSA runtime.

---

# 32. Claude Code Executor

Claude Code chủ yếu dùng:

```text
code generation
refactoring
tests
migration
project scaffolding
landing page generation
deployment preparation
```

Agent gửi:

```text
BuildSpec
Workspace
Constraints
Task
```

không gửi prompt tùy tiện.

---

# 33. BuildSpec

Mọi coding task lớn nên tạo BuildSpec:

```yaml
task:
project:
objective:

requirements: []

constraints: []

allowed_paths: []

forbidden_paths: []

acceptance_criteria: []

tests: []

deployment:
```

BuildSpec lưu local và Admin có quyền chỉnh sửa.

---

# 34. Sandbox

Coding/command execution phải scoped.

Ví dụ:

```text
company/
projects/mid/
workspace/
```

Không cho shell mặc định truy cập toàn máy.

Sandbox policy:

```text
workspace-only
project
temporary
container
full-access
```

`full-access` không phải default.

---

# 35. Persistent Shell

Coding workflow có thể giữ shell session:

```text
install
↓
edit
↓
run
↓
test
↓
fix
↓
test
```

nhưng shell phải thuộc:

```text
session
+
workspace
```

và terminate khi session policy yêu cầu.

---

# 36. Code Mode

COSA nên nghiên cứu pattern Code Mode:

```text
Agent
 ↓
generate orchestration program
 ↓
execute multiple tools
 ↓
aggregate result
```

Dùng cho:

```text
research
CRM enrichment
marketing analytics
data processing
coding
```

Không dùng Code Mode để bypass permission.

Mọi tool call bên trong vẫn phải kiểm tra permission.

---

# 37. Subagents

Subagent là execution scope.

Không nhất thiết là service/process.

Ví dụ:

```text
Market Research
       │
       ├── competitor researcher
       ├── customer researcher
       └── trend researcher
```

Subagent dùng cùng runtime.

---

# 38. Agent không được tự sinh agent vĩnh viễn

Dynamic subagent có thể tồn tại trong session.

Nhưng việc tạo permanent:

```text
Agent Profile
Skill
Workflow
Tool
```

phải qua Admin approval.

---

# 39. Memory Architecture

Phân biệt:

```text
Conversation Memory
Working Memory
Project Memory
Company Knowledge
Learned Skill
```

Không gọi tất cả là memory.

---

# 40. Learning Engine

Áp dụng ý tưởng Hermes nhưng không nhúng Hermes vào core.

Pipeline:

```text
Execution
 ↓
Outcome
 ↓
Feedback
 ↓
Pattern extraction
 ↓
Learning candidate
 ↓
Review
 ↓
Skill update
```

Không tự động sửa production skill ngay.

---

# 41. Knowledge Architecture

Local-first:

```text
knowledge/

company/
projects/
legal/
finance/
marketing/
sales/
templates/
```

Markdown/file là first-class knowledge.

Có metadata/index để search.

---

# 42. Business Data vs Knowledge

Không nhầm:

```text
CRM lead
```

với:

```text
knowledge about lead generation
```

Business data → PostgreSQL.

Knowledge → local documents/index.

Agent state → SQLite/event store.

---

# 43. Storage Strategy

Khuyến nghị:

```text
PostgreSQL
→ structured business data

SQLite
→ sessions
→ traces
→ local cache
→ indexes

Markdown/files
→ knowledge
→ specs
→ prompts
→ templates

COSA Server
→ license
→ entitlement
→ update metadata
```

---

# 44. n8n

n8n vẫn là automation layer.

```text
COSA Agent
 ↓
Harness
 ↓
n8n Tool
 ↓
Workflow
```

Harness không thay thế n8n.

---

# 45. Marketing/Sales/CRM

Không xây một Marketing Agent khổng lồ.

Ví dụ Marketing domain:

```text
Marketing Profile

Skills
├ market-research
├ positioning
├ copywriting
├ seo
└ campaign-planning

Tools
├ web
├ analytics
├ crm
└ social

Workflows
├ research-market
├ create-campaign
├ monitor-competitor
└ generate-content
```

Sales tương tự.

---

# 46. Startup Stage Awareness

Stage phải trở thành Context.

Ví dụ:

```text
IDEA
PROBLEM_DISCOVERY
VALIDATION
MVP
EARLY_REVENUE
PMF
GROWTH
```

Workflow và advice phải stage-aware.

Không áp dụng Growth workflow cho startup đang Problem Discovery.

---

# 47. OKR / 12 Week Year

Harness không thay thế management framework.

Pipeline:

```text
Founder Strategy
 ↓
Objective
 ↓
OKR
 ↓
12WY
 ↓
Weekly Tactic
 ↓
Task
 ↓
Agent Workflow
 ↓
Execution
 ↓
Evidence
 ↓
Scoreboard
```

Agent execution phải liên kết được Task/OKR khi thích hợp.

---

# 48. Evidence

Agent không tự đánh dấu business goal "thành công" chỉ vì workflow hoàn tất.

Phân biệt:

```text
execution_completed
```

với:

```text
business_outcome_achieved
```

Outcome cần evidence.

---

# 49. Folder Structure mục tiêu

```text
cosa/

apps/
    desktop/
    mobile/
    api/

core/
    company/
    projects/
    startup/
    okr/
    twelve_week_year/
    tasks/
    crm/
    marketing/
    sales/
    finance/
    legal/

agent/
    runtime/
    orchestrator/
    routing/
    context/
    models/
    sessions/
    events/
    trajectory/
    memory/
    permissions/
    sandbox/

agents/
    cofounder/
    marketing/
    sales/
    finance/
    legal/
    research/

skills/
    startup/
    marketing/
    sales/
    finance/
    legal/
    management/

tools/
    filesystem/
    shell/
    web/
    crm/
    knowledge/
    n8n/
    hostinger/
    mcp/

workflows/
    startup/
    marketing/
    sales/
    coding/
    management/

executors/
    claude_code/
    codex/
    shell/

runtime_adapters/
    deepseek_harness/

knowledge/

templates/

specs/

prompts/

storage/

tests/

CLAUDE.md
```

---

# 50. Migration Strategy

Không rewrite toàn bộ một lần.

## Phase 0 — Inventory

Claude Code phải lập inventory:

```text
existing agents
prompts
tools
workflows
services
DB tables
API endpoints
UI screens
duplicated logic
```

Không code trước inventory.

---

## Phase 1 — Core Contracts

Tạo:

```text
AgentRuntime
AgentProfile
Skill
Tool
Workflow
Session
AgentEvent
Permission
ModelProvider
Executor
```

Chưa migrate chức năng.

---

## Phase 2 — Event + Session

Implement:

```text
Session
Event Store
Trajectory
Resume
Fork
```

---

## Phase 3 — Intent + Context

Implement:

```text
Intent Router
Context Resolver
Capability Resolver
```

Fix greeting/project bug.

---

## Phase 4 — Tool Registry

Migrate existing tools vào registry.

---

## Phase 5 — Skills

Di chuyển prompt knowledge thành skills.

Không copy nguyên prompt cũ nếu trùng lặp.

---

## Phase 6 — Workflow

Extract business process khỏi prompt.

---

## Phase 7 — Agent Profiles

Chuyển 12 agent thành profiles/compositions.

---

## Phase 8 — DeepSeek Harness Adapter

Implement adapter.

Không cho Business Core import DeepSeek Harness.

---

## Phase 9 — Hologram Operations Center

Implement:

```text
runs
trajectory
approval
artifacts
status
errors
```

---

## Phase 10 — Learning Engine

Chỉ triển khai sau khi event/trajectory đủ ổn định.

---

# 51. Definition of Done

Refactor chỉ được xem là hoàn thành khi:

```text
✓ Business Core không phụ thuộc LLM vendor

✓ Agent profiles không chứa runtime implementation

✓ Tools dùng registry

✓ Skills độc lập agent

✓ Workflows độc lập prompt

✓ Sessions có event log

✓ Trajectory hiển thị được

✓ Greeting không trigger project

✓ Project context có explicit rule

✓ Model router hoạt động

✓ Permission được enforce ngoài model

✓ Claude Code/Codex là executors

✓ DeepSeek Harness nằm sau adapter

✓ Existing business functions vẫn hoạt động
```

---

# 52. Nguyên tắc cuối cùng

Khi bổ sung repository/framework mới, KHÔNG hỏi mặc định:

> Có tạo thêm Agent không?

Phải phân loại nó vào:

```text
MODEL
RUNTIME
AGENT PROFILE
SKILL
TOOL
WORKFLOW
MEMORY
KNOWLEDGE
EXECUTOR
INTEGRATION
UI
```

Chỉ tạo Agent Profile mới khi thực sự xuất hiện **business role mới**.

---

# 53. Architecture Decision

Kiến trúc chuẩn kể từ tài liệu này:

```text
COSA
=
Business OS
+
Co-founder Orchestrator
+
Composable Agent Harness
+
Domain Capabilities
+
Execution Infrastructure
```

Không:

```text
COSA
=
Collection of AI Agents
```

Đây là foundation để COSA tiếp tục phát triển mà không biến thành một hệ thống agent chồng chéo và khó kiểm soát.
