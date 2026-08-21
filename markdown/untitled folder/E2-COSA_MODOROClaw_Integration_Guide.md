# COSA × MODOROClaw — Tài liệu tích hợp Agent Runtime, Capability, Skill, Memory và Automation

> Mục tiêu: học các pattern tốt từ `modoro-digital/MODOROClaw` để bổ sung vào COSA theo hướng **native**, **local-first**, **license-based**, không fork nguyên repo và không biến OpenClaw thành kernel của COSA.

---

## 1. Mục tiêu tài liệu

Tài liệu này mô tả cách tích hợp các ý tưởng phù hợp từ MODOROClaw vào COSA hiện tại, bao gồm:

- Company Workspace
- Capability Registry
- Skill Registry
- Context / Memory Resolver
- Execution Modes
- Policy Engine
- Channel Adapter
- Runtime Manager
- Model Gateway
- Automation Runtime
- VERIFY-BEFORE-CLAIM
- Self-Healing
- Architecture / Release Guards
- Migration và rollout theo từng giai đoạn

Tài liệu được viết để có thể đưa trực tiếp cho Claude Code triển khai theo module.

---

# 2. Nguyên tắc kiến trúc

## 2.1. Không fork MODOROClaw

COSA không nên phụ thuộc kiến trúc:

```text
COSA
  ↓
OpenClaw
  ↓
Everything
```

Kiến trúc đúng:

```text
COSA Core
   │
   ├── Agent Runtime
   ├── Workflow Runtime
   ├── Knowledge Runtime
   ├── Skill Runtime
   └── Tool / Capability Gateway
             │
             ├── Native COSA
             ├── Claude Code
             ├── Codex
             ├── n8n
             ├── OpenClaw
             ├── MCP
             ├── Telegram
             └── Zalo
```

OpenClaw chỉ là một **provider** có thể thay thế.

---

## 2.2. COSA vẫn giữ stack hiện tại

Giữ:

```text
Frontend:
- Flutter Desktop
- Flutter Mobile

Backend:
- Python FastAPI
- PostgreSQL
- pgvector khi cần semantic retrieval

Local:
- filesystem workspace
- local runtime manager
- local SQLite chỉ dùng cache / ephemeral data nếu cần
```

Không chuyển COSA sang Electron chỉ để giống MODOROClaw.

---

# 3. Kiến trúc mục tiêu

```text
┌──────────────────────────────────────────────┐
│                  COSA UI                     │
│ Flutter Desktop / Mobile / Hologram Hub      │
└──────────────────────┬───────────────────────┘
                       │
                Application API
                       │
┌──────────────────────▼───────────────────────┐
│               Founder OS Core                │
│                                              │
│ Company                                      │
│ Projects                                     │
│ OKRs / 12 Week Year                          │
│ Tasks                                        │
│ CRM                                          │
│ Finance                                      │
│ Marketing                                    │
│ Knowledge                                    │
│ Legal / Business Pack                        │
└──────────────────────┬───────────────────────┘
                       │
                AI Orchestration
                       │
        ┌──────────────┼──────────────┐
        │              │              │
 Intent Router   Context Builder   Policy Engine
        │              │              │
        └──────────────┼──────────────┘
                       │
                  Agent Runtime
                       │
                  Skill Registry
                       │
               Capability Resolver
                       │
                  Tool Gateway
                       │
 ┌─────────┬─────────┬─────────┬──────────┬─────────┐
 │         │         │         │          │         │
Claude   Codex      n8n      OpenClaw    MCP      Native
Code                          │
                           Zalo /
                          Telegram
```

---

# 4. Company Workspace

MODOROClaw cho thấy một workspace dạng file rất hiệu quả cho AI context. COSA nên chuẩn hóa thành Company Workspace nhưng không dùng file thay PostgreSQL.

## 4.1. Thư mục đề xuất

```text
~/.cosa/
└── companies/
    └── <company_id>/
        ├── company/
        │   ├── identity.md
        │   ├── vision.md
        │   ├── mission.md
        │   ├── core-values.md
        │   └── business-profile.md
        │
        ├── founder/
        │   ├── profile.md
        │   ├── preferences.md
        │   └── decision-style.md
        │
        ├── projects/
        │   └── <project_id>/
        │       ├── spec.md
        │       ├── context.md
        │       ├── decisions.md
        │       ├── research/
        │       └── artifacts/
        │
        ├── knowledge/
        │   ├── company/
        │   ├── product/
        │   ├── customer/
        │   ├── market/
        │   ├── legal/
        │   └── finance/
        │
        ├── agents/
        ├── skills/
        ├── prompts/
        ├── workflows/
        ├── policies/
        ├── templates/
        ├── memory/
        ├── learnings/
        └── runtime/
```

## 4.2. Quy tắc nguồn dữ liệu

PostgreSQL là source-of-truth cho:

- company
- projects
- tasks
- OKRs
- CRM
- campaigns
- finance
- workflow runs
- audit logs
- permissions

Filesystem là source cho:

- prompt
- skill definition
- company knowledge
- policy
- template
- project spec
- artifact
- decision log
- human-editable config

---

# 5. Context Compiler

Không load toàn bộ workspace vào prompt.

## 5.1. Các tầng context

```text
L0 — Session
L1 — Founder / Company Index
L2 — Project Context
L3 — Domain Context
L4 — Skill Context
L5 — Artifact / Raw Knowledge
```

## 5.2. Ví dụ

User:

```text
Chào
```

Context:

```text
L0 session
+ basic founder preferences
```

Không tự động load project.

User:

```text
Kiểm tra dự án COSA
```

Context:

```text
L0
+ company
+ COSA project
+ recent decisions
```

User:

```text
Phân tích landing page cho COSA
```

Context:

```text
company
+ COSA project
+ marketing domain
+ landing-page skill
+ relevant customer evidence
```

---

# 6. Intent Router

COSA phải sửa dứt điểm tình trạng chat đơn giản bị đưa nhầm vào project workflow.

## 6.1. Intent classes

```text
conversation
question
company_query
project_query
research
create_artifact
edit_artifact
execute_tool
automation
marketing
sales
crm
finance
legal
developer
settings
```

## 6.2. Rule quan trọng

```yaml
conversation:
  examples:
    - chào
    - hello
    - cảm ơn
    - bạn là ai
  tool_calls: false
  project_context: false
```

Không được trigger tool/project chỉ vì hiện có project active.

---

# 7. Capability Registry

Đây là abstraction quan trọng nhất cần bổ sung.

## 7.1. Capability khác Tool

Tool:

```text
telegram.send
openclaw.send_zalo
claude.exec
```

Capability:

```text
send_message
generate_code
search_web
generate_document
run_workflow
voice_realtime
```

Skill chỉ phụ thuộc capability.

---

## 7.2. Schema mẫu

```yaml
id: send_message
category: communication

providers:
  - id: telegram_native
    priority: 10
    channels:
      - telegram

  - id: openclaw_zalo
    priority: 20
    channels:
      - zalo

risk: external_write

approval:
  interactive: required
  approved_workflow: inherited
```

---

# 8. Provider Adapter

Mỗi provider phải implement contract chung.

```python
class CapabilityProvider:
    async def health(self) -> HealthResult:
        ...

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        ...

    async def capabilities(self) -> list[str]:
        ...
```

Ví dụ:

```text
OpenClawProvider
ClaudeCodeProvider
CodexProvider
N8NProvider
TelegramProvider
ZaloProvider
LiveKitProvider
```

---

# 9. Skill Registry

MODOROClaw dùng INDEX + keyword. COSA cần semantic + structured metadata.

## 9.1. Cấu trúc skill

```text
skills/
└── marketing/
    └── customer-interview/
        ├── SKILL.md
        ├── skill.yaml
        ├── prompts/
        ├── templates/
        └── tests/
```

## 9.2. skill.yaml

```yaml
id: marketing.customer_interview
version: 1

name: Customer Interview
domain: marketing

intents:
  - validate_problem
  - customer_interview
  - interview_customer

requires_context:
  - company
  - project

requires_capabilities:
  - document_create

optional_capabilities:
  - web_search
  - crm_write

outputs:
  - interview_plan
  - question_set
  - evidence_summary

risk: low
```

---

# 10. Skill Resolver

Flow:

```text
User request
   ↓
Intent Router
   ↓
Domain Resolver
   ↓
Skill Registry
   ↓
Candidate Skills
   ↓
Capability Check
   ↓
Permission Check
   ↓
Context Compiler
   ↓
Agent Runtime
```

Không hard-code logic vào prompt.

---

# 11. Agent Definition

Agent khác Skill.

Agent = role + responsibility + policies + allowed capabilities.

Skill = procedural knowledge.

Ví dụ:

```yaml
id: marketing_agent

role: Marketing Operator

skills:
  - marketing.customer_interview
  - marketing.positioning
  - marketing.landing_page
  - marketing.copywriting

allowed_capabilities:
  - web_search
  - document_create
  - crm_read
  - crm_write

forbidden_capabilities:
  - finance_payment
  - system_admin
```

---

# 12. Execution Modes

Học từ AUTO-MODE của MODOROClaw nhưng chuẩn hóa thành runtime state.

## 12.1. INTERACTIVE

Founder đang tương tác trực tiếp.

```text
analyze
→ propose
→ approval nếu external/destructive
→ execute
```

## 12.2. APPROVED_WORKFLOW

Founder đã approve workflow trước đó.

```text
trigger
→ execute
→ retry
→ continue
→ final result
```

Không hỏi lại từng bước.

## 12.3. AUTONOMOUS_SAFE

Dùng cho tác vụ:

- summarize
- classify
- extract
- index
- draft
- organize
- update internal memory
- internal analysis

Không được:

- gửi tin ra ngoài
- publish
- thanh toán
- xóa dữ liệu
- thay đổi permission

---

# 13. Policy Engine

Không nhét toàn bộ policy vào một AGENTS.md khổng lồ.

## 13.1. Cấu trúc

```text
policies/
├── base.md
├── tool-use.md
├── communication.md
├── external-write.md
├── automation.md
├── security.md
├── privacy.md
├── artifacts.md
└── admin.md
```

## 13.2. Policy compiler

Runtime:

```text
Base Policy
+
Agent Policy
+
Company Policy
+
Execution Mode Policy
+
Channel Policy
+
Skill Constraints
=
Compiled Runtime Policy
```

---

# 14. VERIFY-BEFORE-CLAIM

Đưa từ prompt rule thành runtime enforcement.

Agent không được nói:

```text
Đã gửi.
Đã cập nhật.
Đã tạo.
Đã chạy.
```

nếu không có evidence.

## 14.1. Evidence object

```json
{
  "action": "crm.contact.update",
  "execution_id": "exec_xxx",
  "status": "success",
  "timestamp": "2026-08-18T09:00:00+07:00"
}
```

## 14.2. Runtime check

```python
if response.contains_completion_claim():
    if not execution_context.has_success_evidence():
        raise ClaimVerificationError()
```

---

# 15. Tool Result Contract

Mọi tool/provider trả về format chuẩn.

```json
{
  "ok": true,
  "provider": "openclaw",
  "capability": "send_message",
  "execution_id": "exec_123",
  "data": {},
  "error": null,
  "evidence": {}
}
```

Không cho agent tự suy luận thành công từ text mơ hồ.

---

# 16. Retry Policy

APPROVED_WORKFLOW:

```text
execute
↓
fail
↓
retry once
↓
still fail
↓
record error
↓
continue if non-blocking
```

Skill/workflow phải khai báo:

```yaml
failure_policy:
  retry: 1
  blocking: false
```

---

# 17. Workflow Runtime

Workflow không chỉ là n8n.

COSA cần abstraction riêng.

```yaml
id: morning_market_brief

trigger:
  type: cron
  schedule: "0 6 * * *"

steps:
  - id: collect
    capability: web_search

  - id: analyze
    agent: market_research_agent

  - id: save
    capability: document_create

  - id: notify
    capability: send_message
    channel: telegram
```

n8n có thể là executor/provider cho một số workflow.

---

# 18. OpenClaw integration

OpenClaw chỉ nên phục vụ capability phù hợp.

Ví dụ:

```text
OpenClawProvider
├── Telegram
├── Zalo
├── message delivery
├── channel listener
└── optional cron compatibility
```

Không đưa vào:

- core project logic
- source-of-truth memory
- strategic data
- CRM core
- company permissions
- COSA workflow state

---

# 19. Channel Adapter

Chuẩn hóa channel.

```python
class ChannelAdapter:
    async def receive(self):
        ...

    async def send(self, message):
        ...

    async def resolve_identity(self):
        ...
```

Adapters:

```text
TelegramAdapter
ZaloAdapter
EmailAdapter
WebChatAdapter
MobileAdapter
VoiceAdapter
```

---

# 20. Channel flow

```text
Inbound message
      ↓
Channel Adapter
      ↓
Identity Resolver
      ↓
Permission Resolver
      ↓
Intent Router
      ↓
Agent Runtime
      ↓
Response Policy
      ↓
Channel Adapter
```

Không để Zalo logic trộn vào marketing/project logic.

---

# 21. Identity Resolver

Một người có thể có:

```text
COSA account
Telegram
Zalo
Email
Mobile device
```

Schema:

```text
persons
person_identities
channels
channel_accounts
```

Ví dụ:

```text
person_identities
- user_id
- channel
- external_id
- verified
- metadata
```

---

# 22. CRM

Không dùng markdown user file làm CRM chính.

PostgreSQL:

```text
contacts
organizations
leads
opportunities
activities
conversations
campaigns
tasks
sources
```

Memory:

```text
memory/customer/<id>.md
```

chỉ lưu AI summary và semantic context.

---

# 23. Memory Architecture

## 23.1. Memory classes

```text
session
episodic
semantic
customer
project
company
learning
```

## 23.2. Memory index

```text
memory/index.md
```

chỉ chứa pointers.

Không load full logs.

---

# 24. Learnings

Tạo:

```text
learnings/
├── ERRORS.md
├── LEARNINGS.md
├── PROVIDER_ISSUES.md
└── WORKFLOW_FAILURES.md
```

Có thể đồng bộ một phần vào PostgreSQL:

```text
agent_learnings
```

---

# 25. Runtime Manager

Học từ dependency pinning của MODOROClaw.

## 25.1. runtime-manifest.json

```json
{
  "python": "3.x",
  "node": "22.x",
  "postgresql": "17.x",
  "livekit": "...",
  "openclaw": "...",
  "n8n": "...",
  "claude_code": "...",
  "codex": "..."
}
```

Không bắt buộc tất cả provider phải cài.

---

# 26. Provider Health

API:

```text
GET /runtime/providers
GET /runtime/providers/{provider}/health
POST /runtime/providers/{provider}/repair
```

Status:

```text
available
missing
degraded
unhealthy
disabled
```

---

# 27. Self-Healing

Tự chữa chỉ trong giới hạn an toàn.

Ví dụ:

```text
process crash
→ restart

port unavailable
→ diagnostics

provider missing
→ reinstall pinned version

schema mismatch
→ rollback compatible config
```

Không tự động sửa user data.

---

# 28. Version Pinning

Canonical file:

```text
runtime/versions.json
```

Mọi installer/updater đọc chung file này.

Không hard-code version ở nhiều nơi.

---

# 29. Runtime upgrade policy

Chỉ update provider khi:

- security issue
- critical bug
- feature thực sự cần

Không update chỉ vì “latest”.

Flow:

```text
check changelog
→ update pin
→ install sandbox
→ smoke test
→ compatibility test
→ release
```

---

# 30. COSA Doctor

Command/internal API:

```text
cosa doctor
```

Kiểm tra:

```text
PostgreSQL
pgvector
workspace
prompt registry
agent registry
skill registry
capability registry
permissions
LiveKit
Telegram
Zalo
n8n
Claude Code
Codex
migrations
license
```

---

# 31. Architecture Guards

Trước build/release:

```text
Architecture Guard
Agent Contract Guard
Skill Contract Guard
Capability Contract Guard
Prompt Guard
Tool Permission Guard
Context Budget Guard
Migration Guard
Security Guard
Runtime Compatibility Guard
```

---

# 32. Context Budget Guard

Mỗi agent/skill có budget.

```yaml
context:
  max_tokens: 20000

  layers:
    company: 2000
    project: 4000
    skill: 3000
    memory: 4000
    artifacts: 5000
```

Nếu vượt budget:

```text
rank
→ summarize
→ retrieve only relevant chunks
```

---

# 33. Admin-only content

Các nội dung quan trọng:

```text
prompts
specs
policies
agent definitions
skill definitions
templates
```

mặc định:

```text
admin / founder only
```

Nhân viên tương lai chỉ được dùng nếu permission cho phép.

---

# 34. Reset mặc định

Mỗi system asset có:

```text
default version
company override
reset to default
```

Schema:

```text
system_assets
company_asset_overrides
```

Không sửa trực tiếp file mặc định.

---

# 35. Company Pack

Mỗi công ty khi cài COSA có một pack riêng.

```text
company-pack/
├── company/
├── prompts/
├── skills/
├── templates/
├── policies/
└── knowledge/
```

User được sửa local.

Sau này server có thể phát hành:

```text
pack updates
template updates
legal updates
skill updates
```

nhưng phải merge an toàn, không overwrite company override.

---

# 36. Update strategy

Tách:

```text
System Default
Company Override
User Data
```

Update chỉ thay:

```text
System Default
```

Không overwrite:

```text
Company Override
User Data
```

---

# 37. Legal / Business Pack

Các dữ liệu từ Vietnam Business Builder nên trở thành:

```text
knowledge/legal/
templates/legal/
templates/business/
skills/business/
```

Có metadata:

```yaml
source:
effective_date:
last_checked:
jurisdiction: VN
editable: true
```

---

# 38. Marketing Skill Pack

Marketingskills tích hợp như:

```text
skills/marketing/
├── customer-research/
├── positioning/
├── messaging/
├── content/
├── landing-page/
├── conversion/
├── retention/
└── analytics/
```

Không tạo marketing app riêng.

Marketing Agent gọi các skill theo intent.

---

# 39. Paperclip role

Pattern Paperclip phù hợp tầng:

```text
Company
Goals
Agents
Tasks
Execution
```

Không dùng Paperclip làm runtime dependency bắt buộc.

---

# 40. MODOROClaw role

Pattern MODOROClaw phù hợp tầng:

```text
Runtime
Channel
Skill Loading
Memory Loading
Automation
Packaging
Self-Healing
```

---

# 41. Capability examples cho COSA

```text
web_search
read_file
write_file
create_document
generate_image
generate_code
execute_code
send_message
receive_message
create_workflow
run_workflow
crm_read
crm_write
calendar_read
calendar_write
voice_realtime
database_query
database_write
```

---

# 42. Risk classification

```text
READ_ONLY
INTERNAL_WRITE
EXTERNAL_WRITE
DESTRUCTIVE
FINANCIAL
ADMIN
```

Ví dụ:

```text
web_search → READ_ONLY
save_memory → INTERNAL_WRITE
send_zalo → EXTERNAL_WRITE
delete_project → DESTRUCTIVE
payment → FINANCIAL
edit_prompt → ADMIN
```

---

# 43. Approval matrix

| Risk | Interactive | Approved Workflow | Autonomous Safe |
|---|---|---|---|
| READ_ONLY | auto | auto | auto |
| INTERNAL_WRITE | auto | auto | auto |
| EXTERNAL_WRITE | confirm | auto if pre-approved | deny |
| DESTRUCTIVE | confirm | explicit step approval | deny |
| FINANCIAL | confirm | explicit permission | deny |
| ADMIN | founder | founder | deny |

---

# 44. Audit Log

Mọi action quan trọng ghi:

```text
audit_events
```

Schema:

```text
id
company_id
user_id
agent_id
workflow_id
capability
provider
risk_level
input_hash
result
timestamp
```

Không log secret raw.

---

# 45. Secret Management

API key không lưu trong markdown.

Dùng:

```text
OS Keychain / secure storage
```

DB chỉ lưu reference.

Ví dụ:

```text
provider_credentials
- provider
- secret_ref
- metadata
```

---

# 46. Model Gateway

Tương tự ý tưởng 9Router nhưng native COSA.

```text
Model Gateway
├── OpenAI
├── Anthropic
├── Gemini
├── DeepSeek
├── Kimi
├── Ollama
└── future provider
```

Routing theo:

```text
task
cost
latency
quality
availability
context
```

---

# 47. Model policy

Ví dụ:

```yaml
coding:
  preferred: claude-code
  fallback:
    - codex

research:
  preferred: configurable_api_model

chat:
  preferred: configurable_fast_model
```

Không hard-code tên model vào skill.

---

# 48. Voice Capability

```text
voice_realtime
```

Provider:

```text
desktop:
  LiveKit Local

mobile:
  LiveKit Cloud
```

Skill/agent không cần biết provider cụ thể.

---

# 49. Developer Capability

```text
generate_code
inspect_repo
edit_repo
run_tests
```

Providers:

```text
Claude Code CLI
Codex CLI
```

Các provider này chạy local dưới quyền user.

---

# 50. Hologram Hub

Hologram Hub không cần chứa runtime logic.

Nó là surface để:

```text
Agent Cards
Workflow Cards
Progress
Artifacts
Visualizations
Alerts
Recent Execution
```

Visualize output từ agent được hiển thị thành card.

---

# 51. API đề xuất

## Capability

```text
GET    /api/capabilities
GET    /api/capabilities/{id}
POST   /api/capabilities/{id}/execute
```

## Skills

```text
GET    /api/skills
GET    /api/skills/{id}
POST   /api/skills/reload
```

## Agents

```text
GET    /api/agents
GET    /api/agents/{id}
POST   /api/agents/{id}/execute
```

## Runtime

```text
GET    /api/runtime/status
GET    /api/runtime/providers
POST   /api/runtime/providers/{id}/repair
```

## Context

```text
POST   /api/context/build
```

## Workflow

```text
POST   /api/workflows
POST   /api/workflows/{id}/run
GET    /api/workflow-runs/{id}
```

---

# 52. Database schema tối thiểu

```text
agents
skills
skill_versions
capabilities
capability_providers
provider_credentials
workflows
workflow_steps
workflow_runs
workflow_run_steps
audit_events
agent_memories
agent_learnings
system_assets
company_asset_overrides
```

---

# 53. Agent execution context

```python
class AgentExecutionContext:
    company_id: str
    user_id: str
    project_id: str | None
    agent_id: str
    skill_ids: list[str]
    execution_mode: str
    permissions: list[str]
    context_bundle: dict
    evidence: list
```

---

# 54. Agent runtime pseudocode

```python
async def execute_agent(request):
    intent = await intent_router.resolve(request)

    if intent.type == "conversation":
        return await simple_chat(request)

    skills = await skill_resolver.resolve(intent)

    context = await context_compiler.build(
        request=request,
        skills=skills
    )

    policy = await policy_engine.compile(
        user=request.user,
        mode=request.execution_mode,
        skills=skills
    )

    result = await agent_runtime.run(
        request=request,
        context=context,
        policy=policy,
        skills=skills
    )

    return await claim_verifier.validate(result)
```

---

# 55. Skill execution pseudocode

```python
async def execute_skill(skill, ctx):
    for capability in skill.requires_capabilities:
        provider = capability_resolver.resolve(capability, ctx)

        if not provider:
            raise CapabilityUnavailable(capability)

    return await runtime.execute(skill, ctx)
```

---

# 56. Workflow execution pseudocode

```python
for step in workflow.steps:
    try:
        result = await execute(step)

        if not result.ok:
            result = await retry(step, count=1)

        if not result.ok and step.blocking:
            stop()

        record(result)

    except Exception as exc:
        record_error(exc)

        if step.blocking:
            stop()

continue_workflow()
```

---

# 57. Fresh install

Flow:

```text
Install COSA
    ↓
Create local workspace
    ↓
Initialize DB
    ↓
Load default Company Pack
    ↓
Runtime health check
    ↓
Founder onboarding
    ↓
Optional provider setup
    ↓
Ready
```

Không bắt buộc user cài thủ công Node/Python/plugin ngoài.

---

# 58. First-run Provider Setup

Wizard:

```text
AI Providers
Claude Code
Codex
Telegram
Zalo
n8n
LiveKit
```

Mỗi provider:

```text
Not configured
Configured
Healthy
Error
```

---

# 59. Không ép cài tất cả

Provider là optional.

Ví dụ:

```text
Zalo unavailable
```

không được làm COSA unusable.

Skill yêu cầu Zalo thì báo:

```text
Capability send_message:zalo unavailable
```

---

# 60. Migration plan

## Phase 1 — Core abstractions

Triển khai:

```text
Capability Registry
Skill Registry
Agent Registry
Execution Modes
Policy Engine
```

## Phase 2 — Context

```text
Company Workspace
Context Compiler
Memory Resolver
```

## Phase 3 — Tool providers

```text
Claude Code
Codex
OpenClaw
Telegram
Zalo
n8n
```

## Phase 4 — Runtime

```text
Runtime Manager
Health
Pinning
Self-Healing
Doctor
```

## Phase 5 — Guards

```text
Architecture
Skill
Capability
Prompt
Migration
Security
Context
```

---

# 61. Thứ tự triển khai Claude Code

## Task 1

Audit codebase hiện tại và xác định:

```text
agent runtime
tool registry
prompt loading
project context
chat routing
workflow execution
```

Không viết lại trước khi map rõ code hiện tại.

---

## Task 2

Tạo module:

```text
backend/app/ai/capabilities/
```

với:

```text
models.py
registry.py
resolver.py
providers/
```

---

## Task 3

Tạo:

```text
backend/app/ai/skills/
```

---

## Task 4

Tạo:

```text
backend/app/ai/policies/
```

---

## Task 5

Tạo:

```text
backend/app/ai/context/
```

---

## Task 6

Refactor router chat:

```text
message
→ intent
→ context
→ agent/skill
```

Đảm bảo greeting không gọi project tool.

---

## Task 7

Bọc tool hiện tại thành capability providers.

Không rewrite tool nếu không cần.

---

## Task 8

Tích hợp OpenClaw bằng adapter.

Không import OpenClaw logic vào domain core.

---

## Task 9

Tạo Runtime Manager.

---

## Task 10

Tạo smoke tests và architecture guards.

---

# 62. Prompt Claude Code triển khai tổng thể

```text
Bạn đang triển khai COSA theo kiến trúc local-first, license-based.

Mục tiêu của thay đổi này là bổ sung một Agent Runtime architecture lấy cảm hứng từ các pattern tốt của MODOROClaw nhưng KHÔNG fork, KHÔNG phụ thuộc OpenClaw làm kernel.

Nguyên tắc bắt buộc:

1. Giữ Flutter + FastAPI + PostgreSQL hiện tại.
2. PostgreSQL là source-of-truth cho operational data.
3. Local workspace dùng cho knowledge, prompts, skills, policies, specs, templates và artifacts.
4. OpenClaw chỉ là capability provider.
5. Skill không hard-code tool/provider.
6. Tạo Capability Registry và Provider Adapter abstraction.
7. Tạo Skill Registry có metadata schema.
8. Tạo Policy Engine và ba execution modes:
   - INTERACTIVE
   - APPROVED_WORKFLOW
   - AUTONOMOUS_SAFE
9. Tạo Context Compiler theo progressive loading.
10. Chat greeting không được tự load hoặc execute project workflow.
11. Thực hiện VERIFY-BEFORE-CLAIM ở runtime.
12. Mọi external write phải qua approval policy.
13. Thêm audit evidence cho tool executions.
14. Không sửa phá vỡ module đang hoạt động nếu có thể wrap bằng adapter.
15. Viết migration và tests trước khi thay thế flow cũ.
16. Tạo architecture guards.
17. Mọi prompt/spec/skill quan trọng mặc định chỉ founder/admin được sửa.
18. Hỗ trợ reset asset về system default.
19. Company override không bị overwrite khi update app.
20. Mọi provider phải optional và có health status.

Trước khi code:
- audit codebase hiện tại;
- tạo SYSTEM_MAP.md;
- xác định file/module sẽ giữ, wrap, refactor hoặc deprecate;
- không tạo module trùng chức năng đang có.

Triển khai theo phase, mỗi phase phải có:
- schema
- service
- API
- tests
- migration nếu cần
- docs
- rollback considerations.
```

---

# 63. Acceptance criteria

Hệ thống được coi là hoàn thành phase kiến trúc khi:

- “Chào” không trigger project flow.
- Skill được resolve bằng registry.
- Skill không biết provider cụ thể.
- Provider có thể thay thế.
- OpenClaw bị disable thì COSA vẫn chạy.
- Zalo unavailable không làm chat core chết.
- External message yêu cầu approval trong interactive mode.
- Approved workflow không hỏi approval lặp lại.
- Tool claim phải có evidence.
- Context không load full workspace.
- Company override giữ nguyên sau app update.
- Runtime doctor phát hiện provider lỗi.
- Smoke test chạy trước release.
- Prompt/skill/spec chỉ admin sửa.
- Có reset về default.
- Có audit log.

---

# 64. Những phần KHÔNG nên sao chép từ MODOROClaw

Không:

```text
chuyển COSA sang Electron
dùng OpenClaw làm kernel
dùng markdown làm CRM database
dùng keyword-only skill matching
tạo AGENTS.md khổng lồ
hard-code Zalo/Telegram vào agent
hard-code model name vào skill
để AI tự xác nhận tool thành công
```

---

# 65. Những pattern NÊN áp dụng

```text
Company Workspace
Progressive Context Loading
Skill Loading
Execution Modes
VERIFY-BEFORE-CLAIM
Runtime Pinning
Self-Healing
Smoke Testing
Channel Abstraction
Provider Abstraction
Company-local customization
```

---

# 66. Vị trí MODOROClaw trong hệ sinh thái tham khảo COSA

```text
                     COSA
                      │
               Founder / Company OS
                      │
      ┌───────────────┼────────────────┐
      │               │                │
 Paperclip       Business Builder   MODOROClaw
      │               │                │
 Org + Work       VN Business       Agent Runtime
 Structure         Knowledge          Patterns
      │               │                │
      └───────────────┼────────────────┘
                      │
                 Skill Layer
                      │
             Marketingskills
```

---

# 67. Kết luận

MODOROClaw không nên trở thành dependency lõi của COSA.

Giá trị của MODOROClaw nằm ở việc chứng minh một số pattern thực tế:

- agent có workspace;
- skill được load theo nhu cầu;
- memory không nên load toàn bộ;
- runtime cần self-healing;
- provider cần pin version;
- workflow đã approve không nên hỏi lại;
- channel phải có policy;
- tool execution phải có evidence;
- desktop AI cần installer và runtime manager;
- release phải có smoke tests và guards.

COSA nên nâng các pattern đó thành kiến trúc tổng quát hơn:

```text
COSA Agent Runtime
=
Intent
+ Context
+ Agent
+ Skill
+ Capability
+ Policy
+ Workflow
+ Evidence
+ Runtime Manager
```

Đây là hướng phù hợp để COSA tiếp tục phát triển thành Company Operating System native, local-first và có khả năng mở rộng agent/tool/provider mà không phụ thuộc một framework cụ thể.
