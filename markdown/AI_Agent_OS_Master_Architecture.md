# AI Agent OS — Master Architecture & Integration Blueprint

**Loại tài liệu:** Master Architecture / Consolidated Design Specification  
**Trạng thái:** Historical baseline — xem `docs/architecture/specs/` (10 spec tách theo mục 104 bên dưới) để biết trạng thái triển khai hiện tại của từng layer, và `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` để biết đối chiếu chi tiết blueprint vs code thật (cập nhật 2026-08-22). Tài liệu này vẫn là nguồn kiến trúc cấp cao — các spec không được đi lệch khỏi nó — nhưng không còn là nơi duy nhất phản ánh trạng thái implementation.  
**Ngày cập nhật:** 2026-08-22  
**Phạm vi:** Agent Core, Multi-Agent, Memory, Skill Ecosystem, Tool/MCP, Business OS, Governance, Evaluation, Self-Improvement, Observability, Deployment  
**Ngôn ngữ triển khai chính:** Python cho Agent Core; Encore (TypeScript/Go) cho Business Services khi phù hợp  
**Mục tiêu:** Hợp nhất toàn bộ các phân tích và đề xuất trước đây thành một kiến trúc AI Agent OS duy nhất, có thể dùng làm tài liệu nền cho thiết kế, triển khai và mở rộng sản phẩm.

---

# 1. Tóm tắt điều hành

AI Agent OS được định nghĩa không phải là một chatbot có nhiều tool, mà là một **nền tảng điều phối tác nhân thông minh có trí nhớ, kỹ năng, công cụ, business state, khả năng tự đánh giá và tự đề xuất cải tiến dưới sự quản trị của con người**.

Kiến trúc tổng thể nên tuân theo nguyên tắc:

> **Core nhỏ, ổn định; capability mở rộng qua Skills, Tools, Memory, Business Services và Plugins.**

Mô hình tổng quát:

```text
AI Agent OS
=
Agent Core
+ Multi-Agent Runtime
+ Memory & Knowledge
+ Skill Ecosystem
+ Tool/MCP Runtime
+ Business Services
+ Event & Workflow Engine
+ Evaluation
+ Observability
+ Governance
+ Self-Improvement
```

Các kết luận quan trọng nhất:

1. **Python** phù hợp làm ngôn ngữ chính cho Agent Core vì hệ sinh thái AI/agent, eval, memory, model SDK và khả năng thử nghiệm nhanh.
2. **Google ADK** phù hợp làm một lớp orchestration/framework hỗ trợ agent, nhưng không nên trở thành kiến trúc lõi độc quyền của hệ thống.
3. **DeepSeek Harness** gợi ý đúng triết lý: core đơn giản, plugin/harness rõ ràng, filesystem-friendly, ít coupling.
4. **TencentDB Agent Memory** và các mô hình memory hiện đại nên được tích hợp qua abstraction riêng, không hard-code một backend duy nhất.
5. **Encore** phù hợp làm Business Services/API/Event layer cho các domain như OKR, Tasks, CRM, Marketing, Billing, Workflow.
6. **Multi-agent** nên hỗ trợ cả flow tuần tự, delegation và parallel execution; không nên mặc định mọi bài toán đều cần nhiều agent.
7. **Self-improvement** nên ưu tiên thay đổi qua skill/config/workflow/policy trước khi cho phép sửa Agent Core hoặc source code.
8. **Human approval** là điểm kiểm soát bắt buộc đối với thay đổi capability, permission, deploy, destructive actions và business side effects quan trọng.
9. **MarketingSkills** là ví dụ tốt cho domain skill pack.
10. **awesome-agent-skills** nên được xem như nguồn discovery cho Skill Registry/Supply Chain, không phải runtime dependency.
11. **Skill Registry + Skill Runtime + Skill Supply Chain + Evaluation** là một lớp kiến trúc bắt buộc nếu muốn AI Agent OS có khả năng tiến hóa an toàn.
12. **Business data phải thuộc Business Services**, không nằm trong prompt/memory như nguồn sự thật chính.

---

# 2. Tầm nhìn sản phẩm

AI Agent OS hướng tới một nền tảng có thể:

```text
Hiểu mục tiêu
    ↓
Phân rã công việc
    ↓
Lựa chọn agent / skill / tool phù hợp
    ↓
Truy xuất memory và business context
    ↓
Thực thi workflow
    ↓
Quan sát kết quả
    ↓
Tự đánh giá
    ↓
Phát hiện thiếu năng lực
    ↓
Đề xuất cải tiến
    ↓
Con người phê duyệt
    ↓
Hệ thống tiến hóa
```

Nó không chỉ trả lời câu hỏi, mà phải có khả năng:

- duy trì mục tiêu dài hạn,
- quản lý trạng thái công việc,
- phối hợp nhiều agent,
- thao tác lên business system,
- học từ lịch sử thực thi,
- lựa chọn capability tốt hơn theo thời gian,
- phát hiện lỗi lặp lại,
- đề xuất skill hoặc workflow mới,
- rollback khi thay đổi không hiệu quả.

---

# 3. Các nguyên tắc kiến trúc nền tảng

## 3.1 Stable Core

Agent Core phải nhỏ và thay đổi chậm.

Core nên chứa:

- reasoning,
- planning,
- tool calling,
- memory access,
- delegation,
- policy hooks,
- runtime contracts,
- tracing hooks.

Không nên nhồi domain logic vào Core.

---

## 3.2 Domain Capability Outside Core

Các capability như:

- OKR planning,
- SEO,
- sales follow-up,
- weekly review,
- task prioritization,
- finance analysis,

nên tồn tại dưới dạng:

```text
Skills
Business Services
Workflows
Policies
Plugins
```

---

## 3.3 Explicit State

Không dùng hội thoại làm nguồn trạng thái duy nhất.

Các trạng thái quan trọng phải có representation rõ ràng:

```text
Goal
Objective
Task
Plan
Run
Skill Version
Approval
Memory Item
Event
Workflow State
Business Entity
```

---

## 3.4 Event-Driven Where Valuable

Các domain business và improvement loop nên có event.

Ví dụ:

```text
task.completed
okr.progress_updated
skill.execution_failed
capability.gap_detected
approval.granted
workflow.blocked
memory.consolidation_requested
```

---

## 3.5 Human-Governed Autonomy

Agent có thể tự:

- phân tích,
- đề xuất,
- thử nghiệm,
- staging,
- đánh giá.

Nhưng các hành động rủi ro cao cần control:

```text
deploy production
send external message
delete data
grant permissions
install external capability
financial action
modify core policy
```

---

## 3.6 Progressive Disclosure

Chỉ load context khi cần.

```text
metadata
  ↓
selected instructions
  ↓
specific resources
```

Không load toàn bộ memory, knowledge hay skill catalog vào context.

---

# 4. Kiến trúc tổng thể

```text
┌──────────────────────────────────────────────────────────────┐
│                        EXPERIENCE LAYER                      │
│ Chat │ Dashboard │ Command Center │ Approval UI │ Mobile    │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                       BUSINESS OS LAYER                      │
│ OKR │ 12 Week Year │ Tasks │ Projects │ CRM │ Marketing    │
│ Finance │ Operations │ Workflow │ Identity │ Billing        │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                       AGENT RUNTIME                          │
│ Planner │ Executor │ Reviewer │ Critic │ Specialists        │
│ Delegation │ Parallelism │ Context Builder │ Policy Hooks    │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                       SKILL ECOSYSTEM                        │
│ Registry │ Router │ Loader │ Runtime │ Trust │ Permissions  │
│ Supply Chain │ Evaluation │ Lifecycle │ Discovery           │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                          TOOL LAYER                          │
│ MCP │ APIs │ Connectors │ Browser │ Shell │ Code Runner     │
│ Search │ Files │ Calendar │ Email │ SaaS Integrations       │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                MEMORY / KNOWLEDGE / DATA LAYER               │
│ Working │ Episodic │ Semantic │ Procedural │ Org Knowledge  │
│ Vector Search │ SQL │ Object Store │ Event Store             │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│              OBSERVABILITY / EVAL / GOVERNANCE              │
│ Traces │ Metrics │ Cost │ Evals │ Audit │ Policy │ Approval │
└──────────────────────────────────────────────────────────────┘
```

---

# 5. Agent Core

## 5.1 Vai trò

Agent Core là runtime reasoning chung.

Nó không sở hữu business state.

Các trách nhiệm:

```text
receive goal
build context
plan
select capability
execute
observe
review
retry/fallback
emit events
store trace
```

---

## 5.2 Interface gợi ý

```python
class Agent:
    async def run(
        self,
        task: TaskContext,
        *,
        memory: MemoryContext,
        skills: SkillContext,
        tools: ToolContext,
        policy: PolicyContext,
    ) -> AgentResult:
        ...
```

---

## 5.3 Agent Runtime Components

```text
AgentRuntime
├── ContextBuilder
├── Planner
├── SkillRouter
├── ToolBinder
├── Executor
├── Reviewer
├── RetryManager
├── PolicyEngine
└── TraceRecorder
```

---

# 6. Google ADK trong AI Agent OS

Google ADK có thể được sử dụng như một framework hỗ trợ:

- agent definition,
- orchestration,
- tool integration,
- multi-agent,
- session/state patterns,
- deployment integration.

Tuy nhiên AI Agent OS nên bọc ADK bằng abstraction riêng.

Không nên:

```text
Business Layer
    ↓
Google ADK-specific code everywhere
```

Nên:

```text
AI Agent OS Agent Interface
          ↓
ADK Adapter
          ↓
Google ADK
```

Lợi ích:

- thay model/framework dễ hơn,
- không khóa kiến trúc vào một vendor,
- test domain logic độc lập,
- hỗ trợ agent runtime khác trong tương lai.

---

# 7. DeepSeek Harness và triết lý Plugin

Điểm quan trọng rút ra:

> Một agent platform hiệu quả không cần một plugin system quá phức tạp.

Thiết kế nên ưu tiên:

```text
folder
+ manifest
+ instructions
+ tools
+ resources
+ optional UI
```

Ví dụ:

```text
plugins/
  marketing/
    manifest.yaml
    skills/
    tools/
    resources/
    ui/
```

Harness cần:

- detect plugin,
- validate manifest,
- resolve dependencies,
- register skills/tools,
- enforce permissions,
- expose lifecycle hooks.

---

# 8. Định nghĩa Plugin

Plugin là đơn vị mở rộng deployable.

```text
Plugin
├── Skills
├── Tools
├── MCP adapters
├── Event handlers
├── UI metadata
└── Business integration
```

Plugin không đồng nghĩa với Skill.

---

# 9. Multi-Agent Architecture

## 9.1 Không phải mọi bài toán đều multi-agent

Ưu tiên:

```text
single agent
    ↓ khi cần
delegation
    ↓ khi có parallelizable work
multi-agent parallel
```

---

## 9.2 Các dạng flow cần hỗ trợ

### Sequential

```text
Planner
  ↓
Researcher
  ↓
Executor
  ↓
Reviewer
```

### Parallel

```text
            ┌─ Market Research
Planner ────┼─ Competitor Research
            └─ Customer Research
                     ↓
                  Synthesizer
```

### Delegation

```text
Manager Agent
  ├── delegate SEO
  ├── delegate Finance
  └── delegate Product
```

### Debate / Critic

```text
Generator
   ↓
Critic
   ↓
Revision
```

### Supervisor

```text
Supervisor
  ├── Agent A
  ├── Agent B
  └── Agent C
```

---

# 10. Vai trò Agent chuẩn

Không cần quá nhiều role ở giai đoạn đầu.

Bộ tối thiểu:

```text
Planner
Executor
Reviewer
Specialist
```

Có thể mở rộng:

```text
Critic
Researcher
Coordinator
Skill Curator
Skill Reviewer
Eval Agent
Improvement Agent
```

---

# 11. Memory Architecture

Memory phải là subsystem độc lập.

Mục tiêu:

- continuity,
- preference,
- past execution,
- learned procedures,
- organizational knowledge,
- context compression.

---

## 11.1 Các loại Memory

### Working Memory

Context ngắn hạn của run hiện tại.

### Episodic Memory

Lịch sử sự kiện / trải nghiệm.

Ví dụ:

```text
"Campaign X failed because..."
"Last quarter OKR..."
```

### Semantic Memory

Fact đã chuẩn hóa.

```text
company strategy
customer profile
product facts
```

### Procedural Memory

Cách làm hiệu quả.

```text
weekly review procedure
deployment procedure
campaign launch checklist
```

### Organizational Memory

Knowledge chung của tổ chức.

---

# 12. TencentDB Agent Memory Integration

TencentDB Agent Memory hoặc backend tương tự nên nằm sau interface:

```python
class MemoryStore(Protocol):
    async def put(self, item): ...
    async def search(self, query, filters=None): ...
    async def delete(self, id): ...
    async def consolidate(self, scope): ...
```

Backend có thể thay đổi:

```text
TencentDB
PostgreSQL + pgvector
Qdrant
Redis
Elastic
managed vector DB
```

Agent Core không cần biết backend cụ thể.

---

# 13. Memory Retrieval

Không đưa toàn bộ memory vào prompt.

Pipeline:

```text
task
 ↓
memory query generation
 ↓
scope filter
 ↓
semantic retrieval
 ↓
recency / importance ranking
 ↓
policy filter
 ↓
context compression
 ↓
selected memory
```

---

# 14. Memory Consolidation

Các run có thể tạo rất nhiều memory thô.

Cần lifecycle:

```text
raw events
  ↓
episode
  ↓
summary
  ↓
fact extraction
  ↓
semantic memory
  ↓
archive
```

---

# 15. Memory và Business Data phải tách biệt

Không dùng memory làm nguồn sự thật chính cho:

```text
task status
invoice status
OKR score
CRM contact state
payment status
```

Các dữ liệu này thuộc Business Services.

Memory chỉ chứa context, interpretation và history.

---

# 16. Tool Layer

Tool là atomic capability.

Ví dụ:

```text
calendar.create_event
gmail.send
github.create_pr
crm.update_contact
task.complete
web.search
db.query
```

Tool nên:

- typed,
- narrow,
- observable,
- permission scoped,
- idempotent khi có thể,
- có timeout/retry,
- trả structured output.

---

# 17. MCP

MCP phù hợp làm chuẩn tích hợp capability.

AI Agent OS nên hỗ trợ:

```text
native tools
MCP tools
REST APIs
GraphQL
CLI adapters
internal RPC
```

MCP không thay thế business service.

Nó là interface capability.

---

# 18. Skill Ecosystem

Skill là capability package có thể tái sử dụng.

```text
Skill
=
Instructions
+ Domain Knowledge
+ Procedure
+ Tool Requirements
+ Policies
+ Validation
+ Resources
```

---

# 19. Tool vs Skill vs Agent vs Workflow

| Thành phần | Vai trò |
|---|---|
| Tool | hành động nguyên tử |
| Skill | capability/procedure tái sử dụng |
| Agent | actor có reasoning |
| Workflow | điều phối state/steps |
| Plugin | gói mở rộng |
| Business Service | sở hữu domain state |

---

# 20. Skill Registry

Registry là inventory chính thức.

Trạng thái:

```text
DISCOVERED
IMPORTED
SCANNED
VERIFIED
STAGED
ACTIVE
DEPRECATED
QUARANTINED
REJECTED
```

---

# 21. Canonical Skill Manifest

```yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.seo.keyword-research
  name: Keyword Research
  version: 1.4.2
  description: Research and prioritize search keywords

publisher:
  name: example
  type: official

source:
  type: git
  repository: https://github.com/example/skills
  path: skills/keyword-research
  commit: 4bc9a82c...
  license: MIT

capability:
  domain: marketing
  category: seo
  intents:
    - keyword research
    - seo planning

runtime:
  entrypoint: SKILL.md
  tools:
    - web.search
    - analytics.read

permissions:
  filesystem: workspace
  network: read
  business_write: false

risk:
  level: low

trust:
  tier: T1
  security_scan: passed

quality:
  eval_score: 0.91
  success_rate: 0.88
```

---

# 22. awesome-agent-skills Integration

`awesome-agent-skills` nên được dùng như:

```text
External Discovery Source
```

Pipeline:

```text
catalog
 ↓
parse
 ↓
normalize
 ↓
resolve repo
 ↓
registry discovered
```

Không nên:

- copy toàn bộ 1.000+ skills,
- load catalog vào context,
- execute trực tiếp từ GitHub main,
- xem curated = audited,
- tự động grant permissions.

---

# 23. MarketingSkills Integration

`marketingskills` phù hợp hơn với vai trò:

```text
Business Domain Skill Pack
```

Kiến trúc:

```text
Marketing
├── Research
├── Positioning
├── SEO
├── Content
├── Copywriting
├── Growth
├── Lifecycle
└── Analytics
```

Priority:

```text
internal approved
 ↓
official vendor
 ↓
reviewed community
 ↓
unknown external
```

---

# 24. Skill Progressive Disclosure

```text
Level 0: metadata
Level 1: SKILL.md
Level 2: references / templates / schemas
```

Metadata nên nhỏ.

Chỉ load skill được chọn.

---

# 25. Skill Router

Pipeline:

```text
user goal
 ↓
intent
 ↓
required capability
 ↓
registry search
 ↓
policy filter
 ↓
trust filter
 ↓
compatibility
 ↓
semantic ranking
 ↓
cost/risk ranking
 ↓
select
```

---

# 26. Skill Ranking

```text
Score
=
Relevance
+ Trust
+ EvalQuality
+ HistoricalSuccess
+ BusinessFit
- Cost
- Risk
- Latency
```

---

# 27. Skill Supply Chain

Pipeline bắt buộc:

```text
DISCOVER
 ↓
FETCH
 ↓
PIN VERSION
 ↓
NORMALIZE
 ↓
STATIC SCAN
 ↓
SEMANTIC REVIEW
 ↓
PERMISSION ANALYSIS
 ↓
EVAL
 ↓
APPROVAL
 ↓
STORE IMMUTABLE ARTIFACT
 ↓
INSTALL
 ↓
SANDBOX
 ↓
STAGE
 ↓
PROMOTE
 ↓
OBSERVE
```

---

# 28. Không chạy từ Git Branch động

Sai:

```yaml
ref: main
```

Đúng:

```yaml
commit: 4bc9a82...
sha256: ...
```

Update phải đi qua:

```text
diff → scan → eval → approval → promote
```

---

# 29. Skill Trust Tiers

| Tier | Nguồn | Chính sách |
|---|---|---|
| T0 | internal | trusted |
| T1 | approved official | verified |
| T2 | reviewed community | sandbox/scoped |
| T3 | unknown | disabled |
| T4 | rejected | quarantined |

---

# 30. Permission Model

Permission classes:

```text
READ_LOCAL
WRITE_WORKSPACE
READ_NETWORK
EXTERNAL_WRITE
SEND_MESSAGE
MODIFY_BUSINESS_DATA
DEPLOY
EXECUTE_CODE
ACCESS_SECRET
DELETE_DATA
FINANCIAL_ACTION
```

High risk cần approval.

---

# 31. Skill Runtime

```python
class SkillRuntime:
    async def execute(
        self,
        skill,
        task,
        agent,
        permissions,
    ):
        ...
```

Runtime phải:

- bind tools,
- enforce permissions,
- sandbox,
- trace,
- capture cost,
- record output,
- emit events.

---

# 32. Skill Evaluation

Các dimension:

```text
task success
accuracy
tool correctness
policy compliance
security
cost
latency
human acceptance
business outcome
```

Eval types:

```text
unit
scenario
regression
adversarial
permission
business
```

---

# 33. Skill Observability

Track:

```text
skill_id
skill_version
agent_id
task_id
model
tool calls
tokens
cost
latency
status
eval_score
human_feedback
```

---

# 34. Self-Improvement

Self-improvement nên ưu tiên capability layer.

Không bắt đầu bằng:

```text
agent rewrites core source code
```

Nên:

```text
observe
 ↓
detect repeated failure
 ↓
identify capability gap
 ↓
search skill
 ↓
evaluate candidates
 ↓
recommend
 ↓
human approval
 ↓
stage
 ↓
canary
 ↓
promote
```

---

# 35. Capability Gap Detection

```yaml
gap:
  capability: marketing.keyword-clustering

evidence:
  failed_tasks: 8
  average_eval: 0.54

proposal:
  install_skill:
    - candidate_a
    - candidate_b
```

---

# 36. Improvement Hierarchy

Khi hệ thống không đạt chất lượng, ưu tiên cải tiến theo thứ tự:

```text
1. Context / retrieval
2. Skill selection
3. Tool selection
4. Workflow
5. Prompt/instructions
6. Memory policy
7. Model choice
8. Business rule
9. Agent role
10. Core code
```

Core code là lựa chọn sau cùng.

---

# 37. Skill Distillation

Một hướng quan trọng:

```text
successful traces
 ↓
detect repeated pattern
 ↓
extract procedure
 ↓
draft SKILL.md
 ↓
generate evals
 ↓
sandbox
 ↓
human approval
 ↓
publish internal skill
```

Đây là cơ chế học tổ chức rất mạnh.

---

# 38. Business OS

Business OS sở hữu business state.

Các service gợi ý:

```text
Identity
Organizations
OKR
Tasks
Projects
CRM
Marketing
Sales
Finance
Billing
Workflow
Events
Notifications
```

---

# 39. Encore trong Business Layer

Encore phù hợp với:

- typed APIs,
- service boundaries,
- database-backed services,
- event/pub-sub,
- background jobs,
- observability,
- infra automation.

Kiến trúc:

```text
Python Agent Core
      ↓
Tool Adapter
      ↓
Encore Business API
      ↓
Database / Event
```

Agent Core không thao tác business database trực tiếp nếu có service API.

---

# 40. FastAPI vs Encore

## FastAPI mạnh ở:

- AI services,
- model endpoints,
- rapid prototyping,
- Python-native integration,
- flexible custom runtime.

## Encore mạnh ở:

- business backend,
- typed service boundary,
- distributed services,
- infra,
- event-driven service,
- production observability.

Kiến trúc tốt nhất không nhất thiết chọn một.

Khuyến nghị:

```text
Python
→ Agent Core / AI Runtime / Eval / Memory adapters

Encore
→ Business Services / API / Events / Workflow integration
```

---

# 41. OKR Example

Business state:

```text
Objective
Key Result
Check-in
Owner
Period
Score
```

Tools:

```text
okr.get_objectives
okr.create_objective
okr.update_key_result
okr.get_progress
```

Skills:

```text
okr.objective-design
okr.kr-quality-review
okr.weekly-checkin
okr.at-risk-analysis
okr.quarterly-review
```

Workflow:

```text
strategy context
 ↓
objective design
 ↓
KR review
 ↓
human approval
 ↓
persist
 ↓
weekly monitor
```

---

# 42. 12 Week Year Example

Business objects:

```text
Vision
12-week goal
Tactic
Weekly commitment
Score
Review
```

Skills:

```text
12wy.define-vision
12wy.build-plan
12wy.weekly-plan
12wy.score-execution
12wy.weekly-review
12wy.end-cycle-review
```

---

# 43. Tasks Example

Business objects:

```text
Task
Project
Owner
Status
Priority
Due date
Dependency
```

Skills:

```text
tasks.breakdown
tasks.prioritize
tasks.daily-plan
tasks.detect-blockers
tasks.weekly-review
```

---

# 44. Marketing Example

Business objects:

```text
Campaign
Audience
Channel
Asset
Experiment
Metric
Lead
Content
```

Skills:

```text
market-research
positioning
keyword-research
seo-plan
content-plan
copywriting
campaign-review
growth-experiment
analytics-review
```

---

# 45. Business Workflow vs Agent Workflow

Business workflow cần deterministic state.

Agent workflow có thể probabilistic.

Ví dụ:

```text
Business:
invoice approved → send → paid

Agent:
research → synthesize → propose
```

Không nên dùng LLM để thay thế state machine cho các business process rõ ràng.

---

# 46. Event Architecture

Events nên chuẩn hóa:

```text
entity.action
```

Ví dụ:

```text
task.created
task.completed
okr.updated
campaign.launched
skill.failed
skill.promoted
approval.requested
capability.gap_detected
```

---

# 47. Workflow Engine

Workflow nên hỗ trợ:

- deterministic steps,
- agent steps,
- tool steps,
- approval steps,
- wait conditions,
- retry,
- compensation,
- timeout,
- parallel branch.

Ví dụ:

```text
Start
 ↓
Agent Research
 ↓
Human Approval
 ↓
Business Write
 ↓
Notify
 ↓
End
```

---

# 48. Governance

Governance là lớp bắt buộc.

Bao gồm:

```text
Identity
RBAC
Permission
Policy
Approval
Audit
Risk
Data scope
Model policy
Skill trust
```

---

# 49. Approval Model

Approval object:

```yaml
id: apr_123
action: promote_skill
subject: skill_x@1.2
requester: agent
reviewer: user
status: approved
reason: passed eval
```

Approval không chỉ dành cho skill.

Có thể áp dụng cho:

```text
deploy
send communication
delete
financial operation
policy change
external integration
```

---

# 50. Policy Engine

Policy check trước tool/action.

```text
Agent intends action
      ↓
Policy Engine
      ↓
ALLOW / DENY / REQUIRE_APPROVAL
```

---

# 51. Evaluation Architecture

Eval phải là first-class component.

Eval layers:

```text
Model Eval
Agent Eval
Skill Eval
Workflow Eval
Business Outcome Eval
```

---

# 52. Agent Eval

Các metric:

```text
goal completion
plan quality
tool accuracy
retry count
cost
latency
policy compliance
human acceptance
```

---

# 53. Workflow Eval

```text
completion rate
time to completion
failure step
approval wait
retries
cost
business outcome
```

---

# 54. Business Outcome Eval

Ví dụ Marketing:

```text
CTR
conversion
qualified leads
CAC
revenue
```

Ví dụ OKR:

```text
progress quality
weekly execution
KR completion
```

Eval cuối cùng nên gắn với outcome thực, không chỉ LLM judge.

---

# 55. Observability

Các lớp:

```text
trace
log
metric
event
cost
audit
eval
```

Một run nên có trace tree:

```text
Agent Run
├── Context Retrieval
├── Skill Search
├── Skill Execution
│   ├── Tool Call
│   └── Tool Call
├── Review
└── Final Output
```

---

# 56. Cost Management

Theo dõi:

```text
token in/out
model cost
tool cost
search cost
storage cost
workflow cost
skill cost
cost per business outcome
```

---

# 57. Model Routing

Không cần một model duy nhất.

Router có thể chọn theo:

```text
reasoning complexity
latency
cost
tool calling
context window
structured output
privacy
```

Ví dụ:

```text
cheap model → classification
strong model → planning
specialized model → coding
vision model → image
```

---

# 58. Model Abstraction

```python
class ModelProvider(Protocol):
    async def generate(self, request): ...
    async def tool_call(self, request): ...
```

Không hard-code provider vào domain logic.

---

# 59. Context Builder

Context Builder nên hợp nhất có kiểm soát:

```text
system policy
agent role
task
business context
selected memory
selected skills
tool schemas
workflow state
```

Không cho skill override policy hệ thống.

---

# 60. Prompt Architecture

Prompt nên phân lớp:

```text
System
Platform Policy
Agent Role
Task Context
Skill Instructions
Business Constraints
Tool Result
```

Priority phải rõ.

---

# 61. Security

Threat model tối thiểu:

```text
prompt injection
tool poisoning
skill supply-chain attack
secret leakage
excessive permission
data exfiltration
malicious plugin
unsafe shell
cross-tenant data
business action abuse
model output injection
```

---

# 62. Sandbox

Các capability rủi ro nên chạy sandbox:

```text
code execution
external skill
browser automation
file manipulation
unknown plugin
```

Sandbox nên giới hạn:

```text
network
filesystem
CPU
memory
time
secrets
process
```

---

# 63. Multi-Tenant Isolation

Nếu AI Agent OS phục vụ nhiều tổ chức:

```text
tenant_id
```

phải xuất hiện trong:

- business data,
- memory,
- events,
- skill permissions,
- audit,
- secrets,
- workflow state.

Cross-tenant leakage là lỗi nghiêm trọng.

---

# 64. Secrets

Không inject mọi secret vào mọi agent.

Sử dụng:

```text
secret reference
 ↓
policy check
 ↓
scoped tool
 ↓
secret used server-side
```

---

# 65. Data Architecture

Gợi ý:

```text
PostgreSQL
→ business data
→ registry
→ workflow state
→ approvals

Vector Store
→ semantic memory
→ knowledge retrieval
→ skill embeddings

Object Storage
→ documents
→ artifacts
→ immutable skill packages

Event Bus
→ domain events
→ improvement events
```

---

# 66. Knowledge Layer

Knowledge khác Memory.

Knowledge là nguồn tài liệu:

```text
docs
wiki
policies
manuals
specs
web pages
files
```

Pipeline:

```text
ingest
 ↓
parse
 ↓
chunk
 ↓
metadata
 ↓
embed
 ↓
index
 ↓
retrieve
```

---

# 67. Memory vs Knowledge

| Memory | Knowledge |
|---|---|
| trải nghiệm hệ thống | tài liệu/fact |
| thay đổi theo run | ingest từ nguồn |
| có temporal context | thường ổn định hơn |
| liên quan user/agent | liên quan domain/org |

---

# 68. UI Architecture

UI nên là **command center** chứ không chỉ chat.

Các view:

```text
Chat
Goals
Tasks
Agents
Runs
Skills
Memory
Approvals
Workflows
Evals
Events
Business modules
```

---

# 69. Agent Run UI

Một run nên xem được:

```text
goal
plan
selected agents
selected skills
selected tools
memory used
actions
approvals
cost
eval
result
```

---

# 70. Skill UI

```text
name
publisher
trust
version
permissions
eval score
usage
update available
history
approve/promote/disable
```

---

# 71. Improvement UI

```text
Capability Gaps
Recommendations
Proposed Skills
Workflow Improvements
Model Routing Suggestions
Memory Improvements
```

Human có thể:

```text
approve
reject
edit
test
stage
rollback
```

---

# 72. Repository Layout

```text
ai-agent-os/
│
├── apps/
│   ├── web/
│   └── admin/
│
├── agentos/
│   ├── core/
│   ├── agents/
│   ├── skills/
│   ├── tools/
│   ├── memory/
│   ├── knowledge/
│   ├── policies/
│   ├── workflows/
│   ├── improvement/
│   ├── evals/
│   └── observability/
│
├── services/
│   ├── identity/
│   ├── okr/
│   ├── tasks/
│   ├── projects/
│   ├── crm/
│   ├── marketing/
│   ├── workflow/
│   └── events/
│
├── skillpacks/
│   ├── core/
│   ├── okr/
│   ├── 12-week-year/
│   ├── tasks/
│   └── marketing/
│
├── plugins/
├── registry/
├── evals/
├── infra/
└── docs/
```

---

# 73. Python Package Layout

```text
agentos/
├── core/
│   ├── agent.py
│   ├── runtime.py
│   ├── planner.py
│   ├── context.py
│   └── policy.py
│
├── agents/
├── skills/
│   ├── registry.py
│   ├── router.py
│   ├── loader.py
│   ├── runtime.py
│   ├── trust.py
│   ├── permissions.py
│   └── supply_chain.py
│
├── tools/
├── memory/
├── adapters/
├── workflows/
├── improvement/
├── evals/
└── observability/
```

---

# 74. Core Database Entities

```text
agents
agent_versions
tasks
runs
plans
workflows
workflow_runs
skills
skill_versions
skill_runs
skill_evaluations
approvals
events
memory_items
knowledge_sources
tool_calls
incidents
capability_gaps
improvement_proposals
```

---

# 75. Run Object

```yaml
run:
  id: run_123
  task_id: task_123
  agent: planner@2.1
  status: completed
  model: ...
  skills:
    - skill_a@1.2
  started_at: ...
  completed_at: ...
  cost: ...
  eval_score: ...
```

---

# 76. Improvement Proposal Object

```yaml
proposal:
  id: imp_123
  type: install_skill
  trigger: repeated_failure
  evidence:
    - run_1
    - run_2
  candidate:
    skill: ...
  expected_gain: 0.18
  risk: medium
  status: awaiting_approval
```

---

# 77. Architecture Decision Records

Nên quản lý ADR.

Ví dụ:

```text
ADR-001 Python Agent Core
ADR-002 Encore Business Layer
ADR-003 Memory Abstraction
ADR-004 Skill Ecosystem
ADR-005 Human-Governed Improvement
ADR-006 Event-Driven Business Integration
ADR-007 Provider-Agnostic Model Layer
```

---

# 78. Testing Strategy

Các tầng test:

```text
unit
integration
contract
agent eval
skill eval
workflow eval
end-to-end
security
load
chaos/failure
```

---

# 79. Contract Tests

Đặc biệt quan trọng giữa:

```text
Agent Core ↔ Business Services
Skill ↔ Tool
Plugin ↔ Runtime
Memory Adapter ↔ Backend
```

---

# 80. Failure Model

Phân loại lỗi:

```text
MODEL_ERROR
TOOL_ERROR
POLICY_DENIED
PERMISSION_REQUIRED
BUSINESS_CONFLICT
SKILL_FAILURE
WORKFLOW_TIMEOUT
MEMORY_FAILURE
EXTERNAL_SERVICE_FAILURE
```

---

# 81. Retry Policy

Không retry mù.

Ví dụ:

```text
429 → exponential retry
invalid input → repair once
permission denied → stop
business conflict → re-read state
destructive failure → human escalation
```

---

# 82. Idempotency

Tool business write cần idempotency key.

```text
agent retry
≠
duplicate invoice / duplicate task / duplicate email
```

---

# 83. Background Jobs

Dùng background job cho:

```text
memory consolidation
catalog sync
skill scan
eval suite
long research
report generation
scheduled review
event processing
```

---

# 84. Scheduled Agents

Ví dụ:

```text
daily task review
weekly OKR review
weekly 12WY score
monthly skill audit
nightly eval
```

Scheduled agent vẫn phải đi qua policy.

---

# 85. Business Autonomy Levels

Có thể định nghĩa:

### L0 — Observe

Chỉ đọc.

### L1 — Recommend

Đề xuất.

### L2 — Draft

Chuẩn bị thay đổi.

### L3 — Execute Scoped

Thực thi action ít rủi ro.

### L4 — Execute with Approval

Action rủi ro.

### L5 — Autonomous Policy-Bounded

Chỉ cho domain được kiểm soát chặt.

---

# 86. Default Autonomy Policy

Khuyến nghị MVP:

```text
read → auto
analysis → auto
draft → auto
internal update → scoped
external communication → approval
delete → approval
finance → approval
deploy → approval
permission change → approval
```

---

# 87. Roadmap triển khai

## Phase 0 — Architecture Baseline

- chuẩn hóa interfaces,
- ADR,
- entity model,
- event naming,
- repository layout.

---

## Phase 1 — Agent Core MVP

- Python runtime,
- model adapter,
- tool calling,
- context builder,
- trace,
- single-agent loop.

---

## Phase 2 — Business OS MVP

Ưu tiên:

```text
Tasks
OKR
12 Week Year
```

Thêm:

- Encore services,
- typed API,
- events,
- PostgreSQL.

---

## Phase 3 — Memory

- episodic,
- semantic,
- backend abstraction,
- retrieval,
- consolidation.

---

## Phase 4 — Skill Layer

- manifest,
- registry,
- router,
- loader,
- internal skillpacks,
- permissions.

---

## Phase 5 — Marketing Skill Pack

- tích hợp các pattern từ MarketingSkills,
- research,
- SEO,
- content,
- growth.

---

## Phase 6 — External Skill Supply Chain

- awesome-agent-skills adapter,
- import,
- scan,
- pin,
- eval,
- stage,
- approval.

---

## Phase 7 — Multi-Agent

- delegation,
- sequential,
- parallel,
- reviewer,
- specialist agents.

---

## Phase 8 — Workflow & Approval

- state machine,
- event integration,
- approval UI,
- rollback.

---

## Phase 9 — Evaluation & Observability

- agent eval,
- skill eval,
- workflow eval,
- cost dashboards,
- business outcome metrics.

---

## Phase 10 — Self-Improvement

- capability gap,
- recommendation,
- skill distillation,
- upgrade proposal,
- canary.

---

# 88. MVP thực tế khuyến nghị

Để tránh over-engineering, MVP nên chỉ gồm:

```text
Python Agent Core
PostgreSQL
FastAPI hoặc internal Python API cho AI runtime
Encore cho 2–3 business services
Tasks
OKR
basic Memory
filesystem Skills
Skill Registry
Tool permissions
single Agent
Reviewer
basic Workflow
Approval
Tracing
```

Chưa cần marketplace.

---

# 89. MVP Agent Loop

```python
async def run_task(task):
    context = await build_context(task)

    plan = await planner.plan(context)

    skills = await skill_router.select(plan, context)

    tools = await bind_tools(skills, context.policy)

    result = await executor.execute(
        plan=plan,
        skills=skills,
        tools=tools,
        context=context,
    )

    review = await reviewer.evaluate(result, task)

    await record_run(result, review)

    return result
```

---

# 90. MVP Improvement Loop

```python
async def improvement_cycle():
    failures = await analytics.repeated_failures()

    gaps = await detect_capability_gaps(failures)

    for gap in gaps:
        candidates = await skill_registry.search_external(gap)

        evaluated = await evaluate_candidates(candidates)

        proposal = await create_improvement_proposal(
            gap,
            evaluated,
        )

        await request_human_approval(proposal)
```

---

# 91. Những gì không nên làm

Không nên:

- nhồi business logic vào system prompt,
- dùng memory như database,
- để agent query/write DB tùy ý,
- load toàn bộ skill catalog,
- cho external skill chạy từ `main`,
- cho plugin có `tools: ["*"]`,
- tự động promote external skill,
- tạo quá nhiều agent role ngay từ đầu,
- dùng LLM thay state machine cho business flow rõ ràng,
- coupling toàn bộ hệ thống vào một framework/vendor,
- để self-improvement sửa core không kiểm soát.

---

# 92. Những gì nên chuẩn hóa sớm

```text
Agent interface
Tool schema
Skill manifest
Event naming
Run model
Approval model
Memory API
Policy API
Eval API
Business service contracts
Tracing format
```

Nếu chuẩn hóa sớm, các module có thể tiến hóa độc lập.

---

# 93. Nguyên tắc “Business State Outside Agent”

Agent không nên là nơi lưu trạng thái sản phẩm.

Ví dụ:

```text
Agent biết task
```

không có nghĩa:

```text
task chỉ tồn tại trong agent memory
```

Task phải ở Task Service.

Agent chỉ:

```text
read
reason
act
```

---

# 94. Nguyên tắc “Capability as Data”

Một hướng thiết kế mạnh:

Skill metadata, model config, permission, routing rule nên lưu như data/config.

Điều này cho phép:

```text
update capability
without redeploying core
```

---

# 95. Nguyên tắc “Eval Before Autonomy”

Mức autonomy chỉ tăng sau khi có bằng chứng.

```text
observe
 ↓
recommend
 ↓
draft
 ↓
scoped execute
 ↓
autonomous
```

Mỗi bước dựa trên eval.

---

# 96. Nguyên tắc “Human Approval Is a Feature”

Approval không phải friction bắt buộc phải loại bỏ.

Nó là:

- trust mechanism,
- audit mechanism,
- learning signal,
- safety boundary.

---

# 97. Nguyên tắc “Self-Improvement Is a Product Loop”

Improvement Engine không nên là hidden prompt.

Nó nên có:

```text
evidence
proposal
expected impact
risk
eval
approval
deployment
post-eval
rollback
```

---

# 98. Architecture Maturity Levels

## Level 1 — Assistant

```text
chat + tools
```

## Level 2 — Agent

```text
planning + tool loop + memory
```

## Level 3 — Agent OS

```text
multi-agent + business state + skills + workflows
```

## Level 4 — Adaptive Agent OS

```text
eval + skill routing + capability gap
```

## Level 5 — Self-Improving Governed OS

```text
distillation + proposals + canary + human governance
```

Mục tiêu dài hạn của kiến trúc này là Level 5.

---

# 99. Success Metrics

## Platform

```text
task completion
latency
cost
tool success
incident rate
approval rate
rollback rate
```

## Intelligence

```text
eval score
planning quality
skill selection quality
memory usefulness
retry rate
```

## Improvement

```text
detected gaps
accepted proposals
performance uplift
regression rate
time to capability
```

## Business

Theo từng domain.

---

# 100. Blueprint kết luận

Kiến trúc mục tiêu cuối:

```text
                           USER / ORG
                               │
                               ▼
                        EXPERIENCE LAYER
                               │
                               ▼
                         BUSINESS OS
                               │
                     typed APIs / events
                               │
                               ▼
                         AGENT RUNTIME
                    ┌──────────┼──────────┐
                    │          │          │
                 Planner    Executor   Reviewer
                    │          │          │
                    └──────────┼──────────┘
                               │
                               ▼
                         SKILL ROUTER
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
             Built-in      Verified      Community
                 │             │             │
                 └─────────────┼─────────────┘
                               │
                               ▼
                         SKILL RUNTIME
                               │
                    scoped permission
                               │
                               ▼
                         TOOL / MCP
                               │
                               ▼
                    BUSINESS / EXTERNAL
                               │
                               ▼
                 TRACE / EVENT / MEMORY
                               │
                               ▼
                            EVAL
                               │
                               ▼
                    IMPROVEMENT ENGINE
                               │
                               ▼
                       HUMAN APPROVAL
                               │
                               ▼
                    SAFE CAPABILITY UPGRADE
```

---

# 101. Kết luận kiến trúc

AI Agent OS nên được xây như một **capability operating system**, không phải một monolithic autonomous agent.

Các lớp có trách nhiệm rõ ràng:

```text
Agent Core
→ reasoning

Skills
→ reusable capability

Tools
→ atomic action

Workflows
→ orchestration

Memory
→ experience/context

Knowledge
→ information

Business Services
→ domain truth/state

Eval
→ quality evidence

Governance
→ authority

Improvement Engine
→ evolution
```

Công thức cốt lõi:

```text
Smart Agent
≠
Bigger Prompt
```

Mà là:

```text
Smart Agent
=
Good Context
+ Good Memory
+ Good Skill Selection
+ Good Tools
+ Good Planning
+ Good Evaluation
+ Good Governance
+ Continuous Improvement
```

Mục tiêu quan trọng nhất:

> **AI Agent OS phải có khả năng phát hiện mình thiếu gì, tìm hoặc tạo capability phù hợp, đánh giá nó, đề xuất cho con người, sau đó nâng cấp có kiểm soát.**

Đó là điểm khác biệt giữa một hệ thống agent chạy được và một **Agent Operating System có khả năng tiến hóa**.

---

# 102. Quyết định cuối cùng

## Adopt

- Python Agent Core
- provider-agnostic model layer
- Google ADK qua adapter khi hữu ích
- DeepSeek Harness-style plugin philosophy
- memory abstraction
- multi-agent flow/delegation/parallelism
- Skill Registry
- progressive disclosure
- scoped tools
- human approval
- eval-first autonomy
- Encore cho business services khi phù hợp
- event-driven integration
- capability gap detection
- skill distillation

## Extend

- trust model
- permission model
- supply chain
- immutable skill artifact
- lifecycle
- observability
- business outcome eval
- improvement proposal workflow

## Avoid

- monolithic agent
- monolithic prompt
- database access trực tiếp từ LLM
- mutable external skill execution
- unbounded autonomy
- vendor lock-in
- hidden self-modification
- skill catalog as runtime
- memory as business source of truth

---

# 103. Tài liệu nguồn / chủ đề đã được tổng hợp

Tài liệu master này hợp nhất các kết luận từ các phân tích trước về:

- Google ADK
- DeepSeek Harness
- TencentDB Agent Memory
- Python Agent Core
- FastAPI vs Encore TS/Go
- Multi-Agent architecture
- flow vs parallel agent execution
- self-improving agents / Hermes-style improvement concepts
- human approval / governance
- OKR
- 12 Week Year
- Tasks
- MarketingSkills
- Awesome Agent Skills
- Skill Registry
- Skill Runtime
- Skill Supply Chain
- Trust & Permission
- Evaluation / Observability
- Plugin-based capability extension

---

# 104. Tài liệu tiếp theo nên tách ra khi triển khai

Từ master blueprint này, khi bắt đầu code nên tách thành các spec nhỏ:

```text
01-agent-core-spec.md
02-memory-spec.md
03-skill-spec.md
04-tool-mcp-spec.md
05-business-services-spec.md
06-workflow-event-spec.md
07-governance-policy-spec.md
08-evaluation-observability-spec.md
09-self-improvement-spec.md
10-deployment-infrastructure-spec.md
```

Master document vẫn là nguồn kiến trúc cấp cao để đảm bảo các spec không đi lệch khỏi kiến trúc chung.

---

# 105. North Star

> **AI Agent OS = một nền tảng nơi reasoning có thể thay đổi model, capability có thể thay đổi skill, business state vẫn ổn định, mọi hành động đều quan sát được, và mọi cải tiến quan trọng đều có bằng chứng + governance.**


# Phụ lục A — Skill Ecosystem Integration Specification

## 1. Executive Summary

This document extends the current AI Agent OS architecture with a first-class **Skill Ecosystem Layer**.

The main architectural conclusion is:

> `awesome-agent-skills` should not be embedded into AI Agent OS as runtime code.  
> It should be treated as an **external discovery source** for a governed Skill Registry and Skill Supply Chain.

AI Agent OS should therefore add the following core capabilities:

1. **Canonical Skill Model**
2. **Skill Registry**
3. **Skill Discovery**
4. **Skill Router**
5. **Skill Loader**
6. **Skill Runtime**
7. **Skill Trust & Permission Model**
8. **Skill Supply Chain**
9. **Skill Evaluation**
10. **Skill Observability**
11. **Skill Lifecycle Management**
12. **Capability Gap Detection**
13. **Self-Improvement with Human Approval**

The resulting system allows agents to:

- discover relevant capabilities,
- select only the skills needed for a task,
- load skill instructions progressively,
- execute through restricted tools,
- collect effectiveness metrics,
- detect capability gaps,
- propose new skills,
- evaluate them in a sandbox,
- request human approval,
- and evolve safely without modifying the Agent Core directly.

This architecture is aligned with the AI Agent OS design principle:

> **Core remains small and stable; intelligence and domain capability evolve through composable skills, tools, memory, policies, and business modules.**

---

# 2. Context

The Agent Skills ecosystem is converging around portable directory-based capability packages, commonly centered on a `SKILL.md` file and supporting resources.

The `awesome-agent-skills` repository is valuable because it provides:

- a broad catalog of real-world Agent Skills,
- official skills from major engineering teams,
- community skills,
- cross-platform compatibility signals,
- naming conventions,
- quality guidelines,
- security warnings,
- and a practical taxonomy of capabilities.

However, it is fundamentally a **curated index**, not a runtime.

The repository itself mainly contains:

- `README.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `.gitignore`

The referenced skills live in external repositories.

Therefore, its correct place in AI Agent OS is:

```text
External Skill Catalogs
        ↓
Skill Discovery
        ↓
Skill Registry
        ↓
Security / Eval / Approval
        ↓
AI Agent OS Runtime
```

Not:

```text
awesome-agent-skills
        ↓
copy all skills
        ↓
Agent context
```

---

# 3. Architectural Decision

## ADR-SKILL-001 — Introduce a governed Skill Ecosystem Layer

### Decision

AI Agent OS will introduce a dedicated Skill Layer between the Agent Layer and Tool Layer.

```text
┌───────────────────────────────────────────────────────────┐
│                     BUSINESS OS                           │
│ OKR │ 12 Week Year │ Tasks │ CRM │ Marketing │ Finance  │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                      AGENT LAYER                          │
│ Planner │ Executor │ Reviewer │ Critic │ Specialist      │
│ Sequential Flow │ Parallel Flow │ Delegation             │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                      SKILL LAYER                          │
│ Skill Registry │ Router │ Loader │ Runtime │ Evaluator    │
│ Trust │ Permissions │ Supply Chain │ Lifecycle            │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│                       TOOL LAYER                          │
│ MCP │ APIs │ Connectors │ Browser │ Shell │ Code Runner  │
└─────────────────────────┬─────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────┐
│ MEMORY │ KNOWLEDGE │ EVENTS │ AUDIT │ OBSERVABILITY      │
└───────────────────────────────────────────────────────────┘
```

### Consequences

Positive:

- smaller Agent Core,
- reusable skills,
- portable domain capability,
- easier testing,
- safer self-improvement,
- easier governance,
- multi-model compatibility,
- better observability,
- lower context usage,
- independent lifecycle for capability packages.

Trade-offs:

- adds registry complexity,
- needs security scanning,
- needs version pinning,
- needs evaluation infrastructure,
- needs permission enforcement,
- requires canonical metadata normalization.

---

# 4. Core Definitions

AI Agent OS should define the following objects separately.

## 4.1 Tool

A **Tool** is an atomic callable capability.

Examples:

```text
github.create_pull_request()
crm.update_contact()
calendar.create_event()
browser.open()
sql.query()
send_email()
```

A tool should be:

- narrow,
- typed,
- permission-scoped,
- auditable,
- deterministic where possible.

---

## 4.2 Skill

A **Skill** is a reusable capability package containing knowledge and procedure that may orchestrate one or more tools.

Recommended definition:

```text
Skill
=
Instructions
+ Domain Knowledge
+ Procedure
+ Tool Requirements
+ Policies
+ Validation Rules
+ Optional Resources
```

Example:

```text
Skill: ship-feature
```

may perform:

```text
inspect changes
    ↓
run tests
    ↓
review code
    ↓
commit
    ↓
push
    ↓
create PR
    ↓
monitor CI
```

The skill itself is not the GitHub API.

The GitHub API is a tool dependency.

---

## 4.3 Workflow

A **Workflow** coordinates multiple steps, skills, agents, or approvals.

```text
Workflow
=
State Machine
+ Skills
+ Agents
+ Business Rules
+ Events
+ Approvals
```

---

## 4.4 Agent

An **Agent** is a reasoning actor.

Recommended abstraction:

```text
Agent
=
Model
+ Instructions
+ Memory
+ Skills
+ Tools
+ Policies
+ Runtime
```

---

## 4.5 Plugin

A **Plugin** is a deployable extension unit.

A plugin may contain:

- skills,
- tools,
- MCP adapters,
- UI components,
- event handlers,
- business integrations.

Therefore:

```text
Plugin != Skill
```

A plugin can provide many skills.

---

# 5. Design Principles

## 5.1 Stable Core, Extensible Capability

The Agent Core should contain only generic intelligence primitives:

- planning,
- reasoning,
- tool calling,
- memory usage,
- agent delegation,
- reflection,
- evaluation hooks,
- policy checks.

Domain knowledge should live outside the Core.

---

## 5.2 Progressive Disclosure

Do not load all skill content into the model context.

Recommended flow:

```text
User Request
    ↓
Intent Detection
    ↓
Skill Metadata Search
    ↓
Candidate Ranking
    ↓
Select 1–3 skills
    ↓
Load selected SKILL.md
    ↓
Load resources only when needed
```

Three context levels are recommended:

### Level 0 — Registry metadata

Very small metadata:

```yaml
id: marketing.seo.keyword-research
name: Keyword Research
description: Research and cluster commercial search keywords
domain: marketing
intents:
  - keyword research
  - seo planning
```

### Level 1 — Skill instructions

Load only after routing.

```text
SKILL.md
```

### Level 2 — Supporting resources

Load on demand:

```text
references/
schemas/
examples/
templates/
scripts/
```

---

## 5.3 Least Privilege

A skill must declare only the tools and permissions it actually needs.

Avoid:

```yaml
tools:
  - "*"
```

Prefer:

```yaml
tools:
  - web.search
  - analytics.read
  - docs.create
```

---

## 5.4 External Skills Are Untrusted by Default

External skill instructions are data until reviewed.

AI Agent OS must assume that external skills may contain:

- prompt injection,
- tool poisoning,
- malicious shell commands,
- secret exfiltration,
- destructive instructions,
- hidden network calls,
- unsafe data handling.

---

## 5.5 Never Execute Moving Git References in Production

Do not install production skills by:

```yaml
ref: main
```

Always resolve to:

```yaml
commit: 4bc9a82...
```

and optionally store:

```yaml
sha256: ...
```

---

## 5.6 Human Approval for Capability Promotion

Agents may:

- discover,
- compare,
- evaluate,
- propose,
- stage.

Agents should not silently promote high-risk external capabilities into production.

---

# 6. Skill Sources

AI Agent OS should support multiple skill sources.

```text
Skill Sources
│
├── Built-in
├── Internal Organization
├── Official Vendor
├── Curated Community
├── Git Repository
├── Marketplace
└── Generated Candidate Skill
```

---

## 6.1 Built-in Skills

Owned by AI Agent OS.

Examples:

```text
core/
business/
productivity/
memory/
planning/
evaluation/
```

These are the most trusted skills.

---

## 6.2 Business Domain Packs

Examples:

```text
okr/
12-week-year/
tasks/
marketing/
crm/
sales/
finance/
projects/
```

The previously analyzed `marketingskills` repository fits this category better than a generic external catalog.

It can become a curated **Marketing Skill Pack**.

---

## 6.3 Official Vendor Skills

Examples may include skills published by:

- OpenAI
- Anthropic
- Google
- Microsoft
- Cloudflare
- Vercel
- Stripe
- Notion
- Figma
- HashiCorp
- Trail of Bits

These should still be version-pinned and evaluated.

Official does not mean unrestricted.

---

## 6.4 Community Skills

Community skills must pass additional review.

Default behavior:

```text
discoverable
but
not automatically trusted
```

---

# 7. `awesome-agent-skills` Integration Model

The repository should be integrated as a **Discovery Provider**.

Recommended adapter:

```text
AwesomeAgentSkillsProvider
```

Responsibilities:

```text
fetch catalog
    ↓
parse entries
    ↓
normalize metadata
    ↓
resolve source repository
    ↓
store discovery records
```

It must not:

- execute skills,
- automatically install every skill,
- grant permissions,
- bypass security,
- treat README inclusion as audit approval.

---

# 8. Skill Registry

The Skill Registry is the authoritative inventory of known skills.

Recommended registry scopes:

```text
discovered
verified
installed
active
deprecated
quarantined
```

---

## 8.1 Canonical Skill Manifest

Recommended AI Agent OS manifest:

```yaml
apiVersion: agentos.ai/v1
kind: Skill

metadata:
  id: marketing.seo.keyword-research
  name: Keyword Research
  version: 1.4.2
  description: Research, cluster and prioritize search keywords
  tags:
    - marketing
    - seo
    - research

publisher:
  name: example-org
  type: community
  verified: false

source:
  type: git
  repository: https://github.com/example/skills
  path: skills/keyword-research
  commit: 4bc9a82c...
  license: MIT

capability:
  domain: marketing
  category: seo
  intents:
    - keyword research
    - keyword clustering
    - seo planning
  inputs:
    - website
    - target_market
  outputs:
    - keyword_clusters
    - opportunity_report

runtime:
  format: skill-md
  entrypoint: SKILL.md
  resources:
    - references/**
    - templates/**
  tools:
    - web.search
    - analytics.read
    - docs.create

permissions:
  network:
    mode: allowlist
    hosts:
      - "*.google.com"
      - "*.bing.com"
  filesystem:
    mode: workspace
  secrets: []
  business_actions:
    write: false

risk:
  level: low
  destructive_actions: false
  external_side_effects: false

trust:
  tier: T2
  human_reviewed: true
  security_scan: passed

quality:
  eval_score: 0.91
  success_rate: 0.88
  runs: 523

compatibility:
  agentos: ">=0.4"
  platforms:
    - claude-code
    - codex
    - cursor
    - gemini-cli
```

---

# 9. Canonical Skill Adapter Layer

Different ecosystems use different folder paths and metadata.

AI Agent OS should normalize them.

```text
Claude Skill
       │
Codex Skill
       │
Cursor Skill
       │
Gemini Skill
       │
OpenCode Skill
       │
Internal Skill
       ↓
Skill Normalizer
       ↓
Canonical Skill Manifest
```

Recommended interface:

```python
class SkillAdapter(Protocol):
    def detect(self, source: SkillSource) -> bool: ...
    def parse(self, source: SkillSource) -> CanonicalSkill: ...
    def validate(self, skill: CanonicalSkill) -> ValidationResult: ...
```

Possible implementations:

```text
ClaudeSkillAdapter
CodexSkillAdapter
GeminiSkillAdapter
CursorSkillAdapter
OpenCodeSkillAdapter
GenericSkillMdAdapter
AgentOSNativeSkillAdapter
```

---

# 10. Skill Trust Model

Recommended trust tiers:

| Tier | Source | Default Policy |
|---|---|---|
| T0 | AI Agent OS internal | trusted |
| T1 | approved official vendor | verified |
| T2 | reviewed community | sandbox / scoped |
| T3 | unknown external | disabled by default |
| T4 | rejected / malicious | quarantined |

---

## 10.1 Trust Is Not Binary

Trust score can combine:

```text
publisher reputation
source integrity
human review
security scan
evaluation score
usage history
incident history
permission scope
update stability
```

Example:

```text
TrustScore
=
0.20 Publisher
+ 0.15 Integrity
+ 0.20 Security
+ 0.20 Evaluation
+ 0.15 Runtime History
+ 0.10 Human Review
```

---

# 11. Skill Permission Model

A skill may request permissions.

Example capability classes:

```text
READ_LOCAL
WRITE_WORKSPACE
READ_NETWORK
EXTERNAL_WRITE
SEND_MESSAGE
MODIFY_BUSINESS_DATA
DEPLOY
EXECUTE_CODE
ACCESS_SECRET
DELETE_DATA
FINANCIAL_ACTION
```

Recommended policy:

```text
read-only                 → automatic when trusted
workspace write           → scoped
external write            → policy dependent
send email/message        → user/business policy
delete                    → approval
financial action          → approval
secret access             → explicit allowlist
production deploy         → approval or controlled workflow
```

---

# 12. Skill Lifecycle

Recommended states:

```text
DISCOVERED
    ↓
IMPORTED
    ↓
SCANNED
    ↓
VERIFIED
    ↓
STAGED
    ↓
ACTIVE
    ↓
DEPRECATED
```

Alternative states:

```text
QUARANTINED
REJECTED
DISABLED
REVOKED
```

---

## 12.1 Update Lifecycle

Never update an active skill in place.

```text
ACTIVE v1
    │
    └── upstream v2 detected
             ↓
          IMPORTED
             ↓
            DIFF
             ↓
            SCAN
             ↓
            EVAL
             ↓
          STAGED v2
          /       \
      PROMOTE    REJECT
```

---

# 13. Skill Supply Chain

This is a required production component.

Recommended pipeline:

```text
DISCOVER
    ↓
FETCH
    ↓
RESOLVE VERSION
    ↓
NORMALIZE
    ↓
STATIC INSPECTION
    ↓
SECURITY SCAN
    ↓
PERMISSION ANALYSIS
    ↓
EVALUATION
    ↓
HUMAN / POLICY APPROVAL
    ↓
PIN COMMIT
    ↓
STORE ARTIFACT
    ↓
INSTALL
    ↓
SANDBOX TEST
    ↓
PROMOTE
    ↓
OBSERVE
```

---

## 13.1 Artifact Store

For reproducibility, store a local immutable copy or content-addressed package:

```text
skills-cache/
  sha256/
    ab/
      abcd1234...
```

Metadata should record:

```yaml
source_commit: ...
content_hash: ...
scan_result: ...
eval_version: ...
approval_id: ...
installed_at: ...
```

---

# 14. Skill Security Pipeline

Minimum checks:

## Static

- suspicious shell commands,
- environment variable access,
- secret references,
- arbitrary network access,
- file deletion,
- recursive writes,
- prompt injection markers,
- hidden encoded payloads,
- dependency downloads,
- executable scripts.

## Semantic

Use an evaluator model to inspect:

- whether the instructions try to override system policy,
- whether the skill asks the model to reveal secrets,
- whether it instructs unauthorized side effects,
- whether its declared permissions match actual behavior.

## Runtime

Run in sandbox:

```text
no production secrets
no production network
test dataset
restricted filesystem
synthetic tools
```

---

# 15. Skill Router

The Skill Router determines which skills should be loaded.

Recommended pipeline:

```text
User Goal
   ↓
Intent Extraction
   ↓
Required Capabilities
   ↓
Metadata Retrieval
   ↓
Policy Filter
   ↓
Trust Filter
   ↓
Compatibility Filter
   ↓
Semantic Ranking
   ↓
Cost / Latency Ranking
   ↓
Select Skill Set
```

---

## 15.1 Routing Score

A possible score:

```text
Score(skill)
=
w1 * Relevance
+ w2 * Trust
+ w3 * EvalQuality
+ w4 * HistoricalEffectiveness
+ w5 * BusinessFit
- w6 * Cost
- w7 * Risk
- w8 * Latency
```

---

## 15.2 Skill Composition

The router should support:

```text
single skill
skill chain
parallel skills
fallback skill
review skill
```

Example:

```text
marketing campaign
   ↓
market-research
   ↓
positioning
   ↓
copywriting
   ↓
seo
   ↓
review
```

or:

```text
                   ┌─ competitor research
campaign planner ──┼─ seo research
                   └─ customer research
                           ↓
                        synthesis
```

---

# 16. Skill Runtime

The Skill Runtime is responsible for executing skill instructions safely.

Responsibilities:

- load skill context,
- bind allowed tools,
- enforce permissions,
- track token budget,
- track tool calls,
- record traces,
- enforce timeout,
- isolate files,
- apply business policies,
- capture outputs,
- emit evaluation signals.

Suggested object:

```python
class SkillRuntime:
    async def execute(
        self,
        skill: SkillVersion,
        task: TaskContext,
        agent: AgentContext,
        permissions: PermissionGrant,
    ) -> SkillExecutionResult:
        ...
```

---

# 17. Skill Context Budget

To prevent context explosion:

```yaml
context:
  metadata_tokens: 100
  instruction_tokens_max: 6000
  resource_tokens_max: 12000
  total_tokens_max: 18000
```

Resources should be fetched on demand.

---

# 18. Skill Evaluation

Every production-grade skill should have evals.

Recommended dimensions:

```text
task success
accuracy
hallucination rate
tool correctness
policy compliance
cost
latency
human acceptance
output quality
side-effect correctness
```

---

## 18.1 Eval Types

### Unit Eval

One skill, fixed input.

### Scenario Eval

Skill inside a realistic task.

### Regression Eval

Run after upstream changes.

### Adversarial Eval

Prompt injection / malformed input.

### Permission Eval

Ensure unauthorized actions are blocked.

### Business Eval

Measure whether the output improves the target KPI.

---

# 19. Skill Observability

Record:

```text
skill_id
skill_version
agent_id
task_id
model
input intent
selected tools
tool success/failure
duration
token usage
cost
final result
evaluation score
human feedback
exceptions
```

---

## 19.1 Skill Performance Store

Example schema:

```sql
skill_run (
  id,
  skill_id,
  skill_version,
  agent_id,
  task_id,
  status,
  started_at,
  finished_at,
  tokens_in,
  tokens_out,
  tool_calls,
  cost,
  eval_score,
  user_feedback
)
```

This enables learning from experience.

---

# 20. Self-Improvement Through Skills

AI Agent OS should favor **capability evolution through skills** before modifying Agent Core prompts or source code.

Recommended loop:

```text
Observe
   ↓
Detect repeated failures
   ↓
Classify capability gap
   ↓
Search Skill Registry
   ↓
Search External Sources
   ↓
Evaluate candidates
   ↓
Generate recommendation
   ↓
Human Approval
   ↓
Stage new skill
   ↓
A/B or canary
   ↓
Promote
```

This is a safer form of self-improvement.

---

## 20.1 Capability Gap Object

Example:

```yaml
gap:
  id: gap_123
  domain: marketing
  capability: keyword clustering

evidence:
  failed_tasks: 8
  period: 14d
  average_eval_score: 0.54

recommendation:
  type: install_skill
  candidates:
    - skill_a
    - skill_b
```

---

# 21. Human Governance

AI Agent OS should allow agents to make proposals, but preserve human control.

Agent may propose:

```text
install new skill
upgrade skill
change trust level
grant additional permission
deprecate underperforming skill
replace skill
promote staged skill
```

Approval records should be auditable.

Example:

```yaml
approval:
  id: apr_456
  action: promote_skill
  skill: marketing.seo.keyword-research@1.5.0
  reviewer: user
  created_at: ...
  reason: ...
```

---

# 22. Integration with Multi-Agent Architecture

Skills and agents should remain separate.

Example:

```text
Planner Agent
    ↓
selects skills
    ↓
delegates
 ┌──────────────┬──────────────┐
 │              │              │
SEO Agent   Research Agent   Copy Agent
 │              │              │
skills         skills         skills
```

A specialist agent is a persistent reasoning role.

A skill is a portable capability.

---

# 23. Integration with Google ADK / Python Agent Core

The Python Agent Core remains the orchestration layer.

Recommended modules:

```text
agentos/
├── core/
│   ├── agent.py
│   ├── planner.py
│   ├── runtime.py
│   └── policies.py
│
├── skills/
│   ├── registry.py
│   ├── router.py
│   ├── loader.py
│   ├── runtime.py
│   ├── evaluator.py
│   ├── trust.py
│   ├── permissions.py
│   ├── lifecycle.py
│   └── supply_chain.py
│
├── adapters/
│   ├── claude_skill.py
│   ├── codex_skill.py
│   ├── gemini_skill.py
│   └── generic_skill.py
│
├── tools/
├── memory/
├── agents/
├── improvement/
└── observability/
```

Google ADK can be used for agent orchestration while the Skill Layer remains an AI Agent OS abstraction.

Do not couple the canonical skill registry directly to one agent framework.

---

# 24. Integration with DeepSeek Harness Philosophy

The architecture should preserve the simple plugin/harness philosophy:

```text
small core
+ explicit extension points
+ filesystem-friendly packages
+ simple conventions
+ on-demand loading
```

Recommended:

```text
plugin
 ├── manifest.yaml
 ├── skills/
 ├── tools/
 ├── resources/
 └── ui/
```

A business plugin may provide:

```text
okr-plugin
 ├── skills/
 │   ├── create-objective/
 │   ├── weekly-review/
 │   └── score-key-results/
 │
 ├── tools/
 │   └── okr_api.py
 │
 └── ui/
```

---

# 25. Integration with Encore Business Layer

Encore should remain responsible for typed business services and domain state.

Example services:

```text
identity
organizations
okr
tasks
projects
crm
marketing
billing
events
workflow
```

The Agent Core should interact with them through tools/APIs.

```text
Agent
  ↓
Skill
  ↓
Tool Adapter
  ↓
Encore Business API
  ↓
Database
```

Encore does not need to parse `SKILL.md`.

---

# 26. Example — OKR

Business service:

```text
OKR Service
```

Tools:

```text
okr.get_objectives
okr.create_objective
okr.update_key_result
okr.get_progress
```

Skills:

```text
okr.objective-design
okr.weekly-checkin
okr.score-key-results
okr.identify-at-risk-krs
okr.quarterly-review
```

Workflow:

```text
Quarterly OKR Planning
    ↓
strategy context
    ↓
objective-design skill
    ↓
KR quality review
    ↓
human approval
    ↓
persist via OKR service
```

---

# 27. Example — 12 Week Year

Skills:

```text
12wy.define-vision
12wy.build-12-week-plan
12wy.weekly-plan
12wy.score-execution
12wy.weekly-accountability
12wy.review-cycle
```

Tools:

```text
tasks.*
calendar.*
metrics.*
notes.*
```

The 12 Week Year implementation therefore becomes a domain skill pack layered over business APIs.

---

# 28. Example — Tasks

Tools:

```text
task.create
task.update
task.complete
task.assign
task.query
```

Skills:

```text
tasks.prioritize
tasks.breakdown
tasks.daily-plan
tasks.detect-blockers
tasks.weekly-review
```

The task database remains business state.

The skills contain planning behavior.

---

# 29. Example — Marketing

Recommended integration:

```text
Marketing Skill Pack
│
├── research
├── positioning
├── seo
├── content
├── copywriting
├── lifecycle
├── analytics
└── growth
```

External skills from the broader ecosystem can complement internal marketing skills.

Preferred priority:

```text
internal approved
    ↓
official verified
    ↓
reviewed community
    ↓
unknown external
```

---

# 30. Skill Registry Storage Model

Recommended core tables:

```text
skills
skill_versions
skill_sources
skill_permissions
skill_dependencies
skill_evaluations
skill_runs
skill_reviews
skill_approvals
skill_incidents
skill_tags
capability_embeddings
```

---

## 30.1 `skills`

```sql
skills (
  id,
  canonical_name,
  display_name,
  domain,
  category,
  description,
  publisher_id,
  trust_tier,
  status,
  created_at,
  updated_at
)
```

---

## 30.2 `skill_versions`

```sql
skill_versions (
  id,
  skill_id,
  version,
  source_repo,
  source_path,
  source_commit,
  content_hash,
  manifest_json,
  status,
  created_at
)
```

---

## 30.3 `skill_evaluations`

```sql
skill_evaluations (
  id,
  skill_version_id,
  eval_suite,
  score,
  security_score,
  policy_score,
  latency_ms,
  cost,
  report_json,
  created_at
)
```

---

# 31. Registry APIs

Suggested API surface:

```text
GET    /skills
GET    /skills/:id
GET    /skills/:id/versions
POST   /skills/discover
POST   /skills/import
POST   /skills/:id/evaluate
POST   /skills/:id/stage
POST   /skills/:id/promote
POST   /skills/:id/disable
POST   /skills/:id/upgrade
GET    /capabilities/search
GET    /skill-runs
```

---

# 32. Domain Events

Recommended events:

```text
skill.discovered
skill.imported
skill.scan_completed
skill.evaluation_completed
skill.approval_requested
skill.approved
skill.rejected
skill.staged
skill.activated
skill.execution_started
skill.execution_completed
skill.execution_failed
skill.incident_detected
skill.update_available
skill.deprecated
capability.gap_detected
```

These events can feed the Event Bus and Improvement Engine.

---

# 33. Skill Search Architecture

Use hybrid retrieval.

```text
Metadata Filtering
+
Keyword Search
+
Semantic Embedding Search
+
Historical Performance Ranking
```

Search fields:

```text
name
description
domain
category
intents
tool dependencies
business capabilities
platform compatibility
trust tier
eval score
```

---

# 34. Skill Conflict Resolution

Multiple skills may serve the same capability.

Resolver should compare:

```text
relevance
trust
business fit
tool compatibility
model compatibility
eval score
cost
latency
recent success rate
permission risk
```

A default skill may be assigned per capability.

Example:

```yaml
capability: marketing.seo.keyword-research

default:
  skill: internal.keyword-research

fallback:
  - openai-compatible.skill-x
  - community.skill-y
```

---

# 35. Dependency Management

Skills may depend on:

```text
tools
other skills
runtime packages
MCP servers
business services
secrets
models
```

Manifest:

```yaml
dependencies:
  skills:
    - research.web@^2
  tools:
    - browser.search
  services:
    - marketing-analytics
  models:
    minimum_context: 32000
```

The installer must resolve dependencies before activation.

---

# 36. Compatibility Matrix

A skill version should declare:

```yaml
compatibility:
  agentos: ">=0.4,<1.0"
  python: ">=3.12"
  platforms:
    - agentos
    - codex
  models:
    capabilities:
      - tool_calling
      - structured_output
```

---

# 37. Built-in vs External Skills

Recommended hierarchy:

```text
Layer A — Core Skills
Layer B — Business Skills
Layer C — Organization Skills
Layer D — Verified External
Layer E — Community
```

Routing preference should generally follow this hierarchy unless evaluation data indicates otherwise.

---

# 38. Skill Marketplace — Future Direction

The Registry can later evolve into a marketplace.

Potential features:

```text
search
install
version history
trust badges
permissions
eval score
usage metrics
reviews
publisher verification
signed packages
enterprise allowlists
private skill catalogs
```

Important:

Marketplace is a product layer.

The underlying Registry, Trust, Supply Chain, and Runtime should exist first.

---

# 39. Signed Skill Packages

Future production hardening:

```text
skill package
    ↓
publisher signature
    ↓
registry verification
    ↓
content hash
    ↓
organization allowlist
```

This provides stronger supply-chain integrity.

---

# 40. Self-Generated Skills

AI Agent OS may eventually generate candidate skills.

However, generated skills must not become active automatically.

Recommended lifecycle:

```text
Agent detects repeated procedure
        ↓
draft skill
        ↓
generate tests
        ↓
sandbox eval
        ↓
human review
        ↓
publish internal skill
```

This turns successful repeated behavior into reusable organizational capability.

---

# 41. Skill Distillation

A useful long-term capability:

```text
successful task traces
       ↓
pattern mining
       ↓
repeatable procedure
       ↓
skill draft
       ↓
eval
       ↓
human approval
       ↓
internal skill
```

This is a practical mechanism for organizational learning.

---

# 42. Memory Integration

Skill runtime should interact with memory carefully.

Recommended scopes:

```text
task memory
agent memory
user memory
organization memory
skill execution memory
```

Skill instructions should not receive all memory by default.

Use policy-based retrieval.

---

# 43. Skill Learning from Execution History

Historical metrics may influence routing.

Example:

```text
Skill A
success: 92%
cost: $0.04
latency: 8s

Skill B
success: 89%
cost: $0.01
latency: 3s
```

For low-risk tasks:

```text
choose B
```

For high-value tasks:

```text
choose A
```

This creates adaptive skill selection without changing the core model.

---

# 44. Failure Handling

Skill execution should support:

```text
retry
fallback
alternate skill
alternate tool
human escalation
rollback
```

Example:

```text
skill A fails
    ↓
classify error
    ↓
tool issue? → retry
skill issue? → fallback skill B
policy issue? → stop
high risk? → human escalation
```

---

# 45. Skill Review Agent

Introduce an optional internal specialist:

```text
Skill Review Agent
```

Responsibilities:

- inspect new skill manifests,
- compare permission requests,
- identify suspicious instructions,
- review updates,
- generate human-readable risk reports.

This agent does not have authority to approve by itself.

---

# 46. Skill Curator Agent

Optional internal specialist:

```text
Skill Curator Agent
```

Responsibilities:

```text
monitor sources
deduplicate
classify
tag
compare
score relevance
recommend adoption
```

Useful with `awesome-agent-skills`.

---

# 47. Skill Eval Agent

Optional internal specialist:

```text
Skill Eval Agent
```

Responsibilities:

```text
generate test cases
run benchmark
compare skill versions
detect regressions
produce scorecard
```

---

# 48. Reference Implementation Flow

User asks:

```text
"Create an SEO launch plan for product X"
```

System:

```text
1. Planner identifies:
   - market research
   - keyword research
   - content planning
   - SEO review

2. Skill Router searches registry.

3. Policy prefers:
   internal skills > verified vendor > reviewed community.

4. Selected skills:
   marketing.market-research@2.1
   marketing.keyword-research@1.4
   marketing.content-plan@3.0
   web.seo-review@1.2

5. Runtime loads only selected SKILL.md files.

6. Each skill receives scoped tools.

7. Outputs are passed between skills.

8. Reviewer Agent evaluates final result.

9. Skill run metrics are recorded.

10. If repeated failures occur in keyword clustering:
    capability.gap_detected event is emitted.
```

---

# 49. Proposed Repository Layout for AI Agent OS

```text
ai-agent-os/
│
├── apps/
├── services/
├── agentos/
│   ├── core/
│   ├── agents/
│   ├── skills/
│   ├── tools/
│   ├── memory/
│   ├── policies/
│   ├── improvement/
│   └── observability/
│
├── skillpacks/
│   ├── core/
│   ├── okr/
│   ├── 12-week-year/
│   ├── tasks/
│   ├── marketing/
│   └── engineering/
│
├── registry/
│   ├── sources.yaml
│   ├── approved.yaml
│   ├── blocked.yaml
│   └── policies/
│
├── evals/
│   ├── skills/
│   ├── agents/
│   └── workflows/
│
└── docs/
```

---

# 50. Proposed Fork Role for `vutasoftvn/awesome-agent-skills`

The fork should not merely mirror upstream forever.

Recommended role:

> **AI Agent OS Curated Skill Intelligence Feed**

Potential additions:

```text
registry/
  sources.yaml

catalog/
  official.yaml
  community.yaml
  recommended.yaml

policies/
  trust-policy.yaml
  permission-policy.yaml

evals/
  skill-scorecards/

approved/
  ai-agent-os.yaml

blocked/
  skills.yaml
```

This repository can remain lightweight while becoming useful to the Agent OS ecosystem.

---

# 51. Recommended Adoption Policy

## Automatically discover

- official sources,
- curated community catalogs,
- approved private repositories.

## Automatically import metadata

Allowed.

## Automatically download source for inspection

Allowed in isolated environment.

## Automatically execute

Not allowed for unknown external skills.

## Automatically stage

Allowed for low-risk candidates after successful scans/evals.

## Automatically promote to production

Only for explicitly allowed trust/policy classes.

For most external skills:

```text
human approval required
```

---

# 52. Phase Plan

## Phase 1 — Foundation

Build:

- Canonical Skill Manifest
- local Skill Registry
- Skill Loader
- Skill Router
- built-in skills
- trust tiers
- basic tool permission model

Target:

```text
AI Agent OS can execute internal skills cleanly.
```

---

## Phase 2 — External Import

Build:

- Git source importer
- `awesome-agent-skills` discovery adapter
- skill format adapters
- version pinning
- content hashing
- basic static scanner

Target:

```text
AI Agent OS can discover and safely stage external skills.
```

---

## Phase 3 — Eval & Governance

Build:

- eval harness,
- skill scorecards,
- approval workflow,
- update diff,
- canary promotion,
- rollback.

Target:

```text
external skills can enter production through governance.
```

---

## Phase 4 — Adaptive Routing

Build:

- semantic capability search,
- historical performance ranking,
- fallback selection,
- cost/risk-aware routing.

Target:

```text
agents choose skills dynamically.
```

---

## Phase 5 — Self-Improvement

Build:

- capability gap detector,
- skill recommendation engine,
- candidate evaluator,
- generated skill proposals,
- human approval UI.

Target:

```text
AI Agent OS can safely propose its own capability upgrades.
```

---

# 53. MVP Scope

For the first implementation, avoid overbuilding.

MVP:

```text
1. skills stored in filesystem
2. manifest.yaml
3. SKILL.md
4. registry in PostgreSQL
5. Python SkillLoader
6. semantic search
7. scoped tools
8. commit pinning
9. manual approval
10. basic evaluation
```

Do not start with a full marketplace.

---

# 54. MVP Skill Folder

```text
skills/
  marketing/
    keyword-research/
      manifest.yaml
      SKILL.md
      references/
      tests/
```

---

# 55. MVP Router Pseudocode

```python
async def select_skills(task, registry, policy):
    intent = await extract_intent(task)

    candidates = await registry.search(
        query=intent.summary,
        capabilities=intent.capabilities,
    )

    candidates = [
        skill
        for skill in candidates
        if policy.is_allowed(skill)
    ]

    ranked = rank(
        candidates,
        relevance=True,
        trust=True,
        eval_score=True,
        historical_success=True,
        risk=True,
    )

    return ranked[:3]
```

---

# 56. MVP Loader Pseudocode

```python
async def load_skill(skill_version):
    verify_hash(skill_version)

    manifest = read_manifest(skill_version)
    instructions = read_skill_md(skill_version)

    return LoadedSkill(
        manifest=manifest,
        instructions=instructions,
        resources=LazyResourceLoader(skill_version),
    )
```

---

# 57. MVP Runtime Pseudocode

```python
async def run_skill(skill, task, agent):
    allowed_tools = permission_engine.bind(
        skill.manifest.runtime.tools,
        skill.manifest.permissions,
    )

    with sandbox(skill):
        result = await agent.execute(
            task=task,
            instructions=skill.instructions,
            tools=allowed_tools,
        )

    record_skill_run(skill, task, result)

    return result
```

---

# 58. Acceptance Criteria

The Skill Layer is considered production-ready when:

- no external skill executes from a moving branch,
- every active skill has a pinned version,
- every skill has explicit tool dependencies,
- every external skill has a trust tier,
- every side-effecting skill has permission declarations,
- every active external skill has an evaluation report,
- skill execution is traceable,
- skill rollback is supported,
- external updates never silently replace active versions,
- agents can discover but cannot self-promote high-risk skills,
- a human approval path exists,
- capability gaps can generate recommendations.

---

# 59. Non-Goals

This architecture does not require:

- copying every skill from public catalogs,
- loading thousands of skills into context,
- tying AI Agent OS to one LLM provider,
- tying AI Agent OS to one coding assistant,
- making every tool a skill,
- making every workflow a skill,
- allowing arbitrary shell execution,
- allowing autonomous production upgrades.

---

# 60. Final Architecture

The revised AI Agent OS architecture becomes:

```text
AI Agent OS
│
├── Agent Core
│   ├── reasoning
│   ├── planning
│   ├── delegation
│   └── policy hooks
│
├── Multi-Agent Runtime
│
├── Skill Ecosystem
│   ├── Registry
│   ├── Discovery
│   ├── Router
│   ├── Loader
│   ├── Runtime
│   ├── Trust
│   ├── Permissions
│   ├── Supply Chain
│   ├── Evaluation
│   └── Lifecycle
│
├── Tools & MCP
│
├── Memory & Knowledge
│
├── Business OS
│   ├── OKR
│   ├── 12 Week Year
│   ├── Tasks
│   ├── CRM
│   ├── Marketing
│   └── other domains
│
├── Improvement Engine
│   ├── capability gap detection
│   ├── skill recommendation
│   ├── skill distillation
│   └── upgrade proposals
│
├── Governance
│   ├── approvals
│   ├── audit
│   ├── risk policy
│   └── trust policy
│
└── Observability & Evaluation
```

---

# 61. Final Recommendation

`awesome-agent-skills` should be integrated into AI Agent OS as:

```text
External Discovery Source
```

not as:

```text
Runtime Dependency
```

The correct architectural value is to use it to bootstrap:

```text
Skill Registry
+
Skill Discovery
+
Trust & Permission Model
+
Skill Supply Chain
+
Evaluation
+
Self-Improvement
```

The long-term design goal is:

> AI Agent OS should not need to know every capability in advance.

Instead, it should be able to:

```text
understand the goal
    ↓
identify required capabilities
    ↓
discover available skills
    ↓
select trusted skills
    ↓
execute with scoped permissions
    ↓
measure effectiveness
    ↓
detect capability gaps
    ↓
propose improvements
    ↓
obtain human approval
    ↓
evolve safely
```

This makes the Skill Layer one of the core pillars of AI Agent OS, alongside:

```text
Agent Core
Memory
Tools
Business Services
Evaluation
Governance
```

and creates a practical path toward a **self-improving but human-governed Agent Operating System**.

---

# 62. Related Sources

- `https://github.com/vutasoftvn/awesome-agent-skills`
- `https://github.com/VoltAgent/awesome-agent-skills`
- `https://github.com/vutasoftvn/marketingskills`
- Google ADK
- DeepSeek Harness
- TencentDB Agent Memory

---

# 63. Decision Summary

**Adopt**

- portable skill concept,
- progressive disclosure,
- scoped tools,
- external discovery,
- cross-platform skill compatibility,
- curated official/community sources.

**Extend**

- canonical manifest,
- trust tiers,
- version pinning,
- integrity hashes,
- permission model,
- eval score,
- observability,
- lifecycle,
- approval workflow,
- supply-chain security.

**Do not adopt directly**

- README as production registry,
- mutable Git branch execution,
- automatic trust based on catalog inclusion,
- bulk context loading,
- unrestricted tool access.

**AI Agent OS principle**

> Skills are replaceable capabilities.  
> Tools are atomic actions.  
> Agents are reasoning actors.  
> Workflows coordinate execution.  
> Business services own domain state.  
> Governance controls change.  
> Evaluation determines what should be trusted.
