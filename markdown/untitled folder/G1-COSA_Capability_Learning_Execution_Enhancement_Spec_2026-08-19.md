# COSA Capability, Learning & Execution Enhancement Specification
## Tài liệu cập nhật, bổ sung và điều chỉnh COSA sau phân tích Hermes Agent

**Trạng thái:** Implementation Ready  
**Ngày:** 2026-08-19  
**Quan hệ tài liệu:** Bổ sung cho `COSA_Codebase_Consolidation_Refactor_Spec_2026-08-19.md`  
**Đối tượng:** Founder / Claude Code / Dev team / AI coding agents  
**Phạm vi:** COSA Co-Founder Runtime, Workforce, Skills, Tools, Memory, Learning, Automation, Sandbox, Channels, A2A  
**Nguyên tắc:** Adapt architectural patterns — không nhúng Hermes Agent thành runtime thứ hai.

---

# 0. Mục tiêu tài liệu

Tài liệu này cập nhật kiến trúc COSA dựa trên các pattern có giá trị cao từ Hermes Agent, nhưng vẫn tuân thủ toàn bộ nguyên tắc đã khóa trong tài liệu consolidation:

- COSA là **AI Co-Founder Operating System**.
- COSA có **1 Co-Founder + 5 Core Domain Agents**.
- Không tăng số lượng Agent chỉ vì có capability mới.
- Không tạo runtime song song.
- Không tạo model/table mới nếu entity tương đương đã tồn tại.
- Không dùng trạng thái giả.
- Không hard-code business metrics.
- Business data ưu tiên local.
- Central chỉ lưu identity/license/lifecycle/product intelligence tối thiểu.
- Founder là authority cuối cùng.
- Approval dựa trên risk.
- Stage-aware nhưng không stage-gated cứng.
- Outcome và Evidence là nền tảng của learning.

Mục tiêu bổ sung là tạo một vòng lặp mới:

```text
Founder
   ↓
COSA Co-Founder
   ↓
Mission
   ↓
AgentPlan
   ↓
Capability
   ↓
Skill
   ↓
Toolset / Tool
   ↓
Execution
   ↓
Artifact + Evidence
   ↓
Outcome
   ↓
Learning Review
   ↓
Memory / Skill Candidate
   ↓
Governance
   ↓
COSA làm tốt hơn ở lần sau
```

Đây là bước nâng COSA từ **AI điều phối công việc** thành **AI Co-Founder có khả năng tích lũy kinh nghiệm vận hành và cải thiện cách làm theo thời gian**.

---

# 1. Quyết định kiến trúc quan trọng nhất

## 1.1. Không tích hợp Hermes như một service runtime

Không triển khai:

```text
COSA
  ↓
Hermes Agent Service
  ↓
COSA tools
```

Không tạo `HermesAgentService`, `HermesRuntime`, `HermesMissionWorker`, `HermesAIAgentAdapter` nếu mục tiêu chỉ là dùng Hermes như orchestration engine thứ hai.

COSA đã có Mission, Agent planning/execution, Worker runtime, Execution jobs, Tool definitions, Governance, Approval, Outcomes, Memory, Skills và Sandbox. Do đó chỉ lấy các **architectural primitives**.

## 1.2. Sáu primitive mới cần hội tụ

Các pattern từ Hermes được chuyển thành 6 khối native COSA:

1. **Capability Registry**
2. **Skill Registry**
3. **Toolset Resolver**
4. **Learning Review Worker**
5. **Memory Promotion Pipeline**
6. **Execution Subruns**

Tất cả nằm dưới Mission runtime hiện tại.

---

# 2. Kiến trúc mục tiêu sau cập nhật

```text
┌───────────────────────────────────────────────────────────────────┐
│                        HUMAN FOUNDER                              │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                       COSA AI CO-FOUNDER                          │
│ Intent • Context • Challenge • Mission • Decision • Synthesis     │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                         MISSION ENGINE                            │
│ Mission • Success Criteria • Plan • Risk • Approval • Outcome     │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                       5 CORE DOMAIN AGENTS                        │
│ Finance • Marketing • Sales • Build/Tech • Legal                 │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     CAPABILITY RESOLVER                           │
│ “What business capability is required?”                          │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                        SKILL RESOLVER                             │
│ “How has COSA learned to perform this class of task?”             │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                       TOOLSET RESOLVER                            │
│ Availability • Permission • Stage • Risk • Environment           │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                         TOOL REGISTRY                             │
│ Web • Files • Browser • CRM • Finance • Deploy • MCP • Sandbox    │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                       EXECUTION RUNTIME                           │
│ ExecutionJob • Subrun • Workflow • Sandbox • Retry • Approval     │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                       ┌────────┴────────┐
                       ▼                 ▼
                 Artifacts           Evidence
                       └────────┬────────┘
                                ▼
                              Outcome
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────┐
│                      LEARNING REVIEW                              │
│ Durable fact? • Reusable method? • Failure lesson? • Preference?  │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
             Memory Candidate          Skill Revision
                   │                         │
                   └────────────┬────────────┘
                                ▼
                        Governance / Eval
                                │
                                ▼
                         Promote / Reject
```

---

# 3. Phân biệt Agent, Capability, Skill, Tool

## 3.1. Agent

Agent là **vai trò tổ chức dài hạn**. Ví dụ: Marketing, Finance, Sales, Build & Tech, Legal.

Một Agent có trách nhiệm dài hạn, domain context, permission, budget, memory scope, metrics/outcomes và capability set.

## 3.2. Capability

Capability trả lời câu hỏi:

> “COSA có khả năng thực hiện loại công việc gì?”

Ví dụ:

```text
market_research
customer_interview_analysis
landing_page_generation
lead_qualification
financial_forecasting
contract_review
deployment
```

Capability không phải Agent.

## 3.3. Skill

Skill trả lời:

> “COSA đã học cách thực hiện capability đó như thế nào?”

Ví dụ:

```text
Capability: lead_qualification
Skill: B2B SaaS Lead Qualification
Version: 3
```

Skill có thể chứa procedure, checklist, pitfalls, templates, scripts, references và evaluation criteria.

## 3.4. Tool

Tool là hành động kỹ thuật cụ thể runtime có thể thực hiện, ví dụ `web_search`, `crm_query`, `create_email_draft`, `send_email`, `read_file`, `write_file`, `run_command`, `deploy_nextjs`.

## 3.5. Toolset

Toolset là nhóm tools theo mục đích và policy, ví dụ:

```text
research_readonly
sales_crm
marketing_publish
finance_analysis
development_local
production_deploy
```

## 3.6. Quy tắc tạo Agent mới

Chỉ tạo Agent nếu phần lớn các điều kiện sau đúng:

- trách nhiệm dài hạn riêng;
- cần domain identity riêng;
- cần budget riêng;
- cần permission riêng;
- cần memory riêng;
- cần KPI/outcome riêng;
- founder có lý do nhìn thấy nó trong AI Workforce.

Nếu không, dùng **Capability / Skill / Tool**.

---

# 4. Capability Registry

## 4.1. Mục tiêu

Capability Registry cho phép COSA biết capability nào tồn tại, Agent nào sở hữu, stage nào phù hợp, cần skills/tools nào, plan/tier nào cho phép, risk baseline và điều kiện availability.

## 4.2. Ưu tiên reuse model hiện có

Trước khi tạo model mới, Claude Code phải search:

```text
backend/app/workforce/capabilities/*
backend/app/workforce/models.py
backend/app/workforce/skills/*
backend/app/business/packs/*
```

Nếu đã có entity tương đương, mở rộng thay vì tạo `CapabilityV2`.

## 4.3. Logical contract

Nếu model hiện tại chưa đủ, target logical contract:

```python
CapabilityDefinition
- id
- key
- name
- description
- domain
- owner_agent_key
- category
- status
- min_stage
- max_stage
- default_risk_level
- requires_features_jsonb
- required_toolsets_jsonb
- optional_toolsets_jsonb
- required_skills_jsonb
- metadata_jsonb
- version
- created_at
- updated_at
```

Không nhất thiết cần tất cả columns; phần ít query có thể đặt trong `metadata_jsonb`.

## 4.4. Capability status

```text
ACTIVE
OPTIONAL
EXPERIMENTAL
DEPRECATED
INTERNAL
```

## 4.5. Ví dụ

```yaml
key: market_research
domain: marketing
owner_agent_key: cmo_agent
min_stage: S1_PROBLEM_DISCOVERY
default_risk_level: R0
required_toolsets:
  - web_research
required_skills:
  - market-research-core
```

---

# 5. Skill Registry

## 5.1. Mục tiêu

Skill Registry là **procedural knowledge layer**.

- Prompt: instruction/role/behavior.
- Memory: điều gì đúng hoặc đã xảy ra.
- Skill: cách thực hiện một loại công việc.

## 5.2. Skill package structure

Local package có thể dùng:

```text
data/skills/
└── marketing/
    └── market-research/
        ├── SKILL.md
        ├── references/
        ├── templates/
        ├── scripts/
        └── assets/
```

File là distribution/edit surface. PostgreSQL vẫn là registry/source of truth runtime nếu hiện đã có skill models.

## 5.3. Skill Definition logical contract

```text
SkillDefinition
- id
- key
- name
- domain
- capability_key
- owner_scope
- owner_workspace_id nullable
- status
- current_version_id
- source
- protected
- created_at
```

`owner_scope`:

```text
PLATFORM
WORKSPACE
PROJECT
```

## 5.4. Skill Version

```text
SkillVersion
- id
- skill_id
- version
- content
- checksum
- procedure_jsonb
- evaluation_jsonb
- provenance_jsonb
- created_by_type
- created_by_id
- source_mission_id
- source_outcome_id
- confidence
- status
- created_at
```

## 5.5. Status

```text
DRAFT
STAGED
ACTIVE
EXPERIMENTAL
DEPRECATED
ARCHIVED
BLOCKED
```

## 5.6. Platform vs Workspace

Platform skill là immutable default. Workspace có thể fork/override nhưng không sửa platform copy trực tiếp.

---

# 6. Skill Provenance

Mỗi skill revision do AI đề xuất phải trả lời:

- tại sao học;
- học từ Mission nào;
- Outcome nào;
- Evidence nào;
- Founder correction nào;
- Agent nào.

Ví dụ:

```json
{
  "source_type": "MISSION_OUTCOME",
  "source_mission_id": "uuid",
  "source_outcome_id": "uuid",
  "evidence_ids": ["uuid1", "uuid2"],
  "trigger": "FOUNDER_CORRECTION",
  "summary": "Founder corrected qualification threshold",
  "confidence": 0.82
}
```

Không có provenance thì không auto-promote.

---

# 7. Skill Evaluation

Skill không được trở thành best practice chỉ vì model đánh giá chủ quan.

Evaluation dimensions:

```text
task_success_rate
quality_score
founder_acceptance
rework_rate
time_saved
cost
business_outcome
evidence_strength
sample_count
```

Có thể đặt learning policy theo hướng:

```text
1 mission   → EXPERIMENTAL
3+ missions → candidate ACTIVE
```

nhưng không hard-code toàn hệ thống; đưa vào `LearningPolicy` để có thể điều chỉnh.

---

# 8. Learning Review Worker

## 8.1. Không phải Agent mới

Không xuất hiện trong Hologram Workforce. Đây là background runtime function.

## 8.2. Trigger

Ưu tiên trigger khi:

```text
Mission completed
Mission failed
Founder corrected COSA
Founder rejected artifact
Founder approved artifact after revision
Experiment generated meaningful outcome
```

Không review greeting/chat tầm thường.

## 8.3. Input

```json
{
  "mission": {},
  "plan": {},
  "agent_runs": [],
  "artifacts": [],
  "evidence": [],
  "outcome": {},
  "founder_decisions": [],
  "founder_feedback": [],
  "existing_skills_used": []
}
```

## 8.4. Output

```json
{
  "memory_candidates": [],
  "skill_candidates": [],
  "no_learning_reason": null
}
```

## 8.5. Candidate types

Memory:

```text
FOUNDER_PREFERENCE
COMPANY_FACT
PROJECT_FACT
DOMAIN_FACT
ENVIRONMENT_FACT
DECISION_RULE
```

Skill:

```text
SKILL_CREATE
SKILL_PATCH
SKILL_DEPRECATE
SKILL_SUPPORT_FILE
```

## 8.6. Runtime permission

Learning Review chỉ có:

```text
READ mission/outcome/evidence
READ existing skills
WRITE LearningCandidate
```

Không có quyền send, publish, deploy, pay, delete, create mission, modify accounting, edit contract hoặc change production prompt.

---

# 9. LearningCandidate

Ưu tiên reuse model nếu đã có learning/governance entity. Nếu chưa có, logical contract:

```text
LearningCandidate
- id
- workspace_id
- project_id nullable
- domain
- candidate_type
- target_key
- proposed_content
- diff_jsonb
- rationale
- confidence
- source_mission_id
- source_outcome_id
- evidence_ids_jsonb
- status
- reviewed_by
- reviewed_at
- created_at
```

Status:

```text
PROPOSED
STAGED
APPROVED
REJECTED
APPLIED
SUPERSEDED
```

---

# 10. Founder Governance cho Learning

Founder/admin có thể chọn policy:

```text
STRICT
BALANCED
AUTONOMOUS
```

### STRICT
Mọi skill/memory candidate chờ founder.

### BALANCED
Low-risk preference/fact có evidence có thể auto memory; skill revision staged; production procedure cần approval.

### AUTONOMOUS
Auto-promote các candidate đủ policy/confidence.

Dù vậy không auto-promote những thay đổi liên quan finance/legal/high-risk actions, production deploy procedure, permission escalation, secret handling, payment hoặc data deletion.

---

# 11. Memory Architecture

COSA không copy memory file-size logic. COSA dùng layered memory.

## L0 — Turn Context
Request hiện tại.

## L1 — Founder Profile
Role, preferences, communication, work style, decision style, timezone.

## L2 — Company Memory
Company facts, business model, market, operating conventions, policies.

## L3 — Project Memory
Project facts, stage, goals, constraints, architecture, customer.

## L4 — Domain Memory
Marketing, Sales, Finance, Legal, Build.

## L5 — Episodic Memory
Mission, Decision, Outcome, Failure, Experiment.

## L6 — Procedural Memory
Skills.

## L7 — Evidence
Original source-backed truth. Memory có thể summarize evidence nhưng không thay thế Evidence.

---

# 12. Memory Promotion Pipeline

Raw chat không tự động trở thành durable memory.

```text
Observation
   ↓
MemoryCandidate
   ↓
Classify
   ↓
Deduplicate
   ↓
Check existing memory
   ↓
Evidence / confidence
   ↓
Promote / stage / reject
   ↓
Memory
```

Memory metadata cần có hoặc map được:

```text
scope
category
content
source_type
source_id
confidence
evidence_ids
valid_from
valid_until
last_confirmed_at
superseded_by
sensitivity
```

Categories:

```text
PREFERENCE
FACT
CONSTRAINT
DECISION
POLICY
LESSON
ENVIRONMENT
```

---

# 13. Memory Retrieval

Không dump toàn bộ memory vào prompt.

```text
intent
   ↓
required scopes
   ↓
retrieve relevant memories
   ↓
rank
   ↓
budget
```

Ranking có thể dùng semantic relevance, recency, scope match, confidence, evidence strength và importance.

Ví dụ:

- Greeting: 0/minimal memory.
- Marketing strategy: Founder profile + Company + Project + Marketing + relevant outcomes.
- Finance: Company + Project + Finance memory + actual Finance snapshot.

---

# 14. Context Layering & Prompt Stability

Prompt chia thành:

```text
Layer A — Stable Platform
Layer B — Workspace Policy
Layer C — Project Context
Layer D — Mission Context
Layer E — Retrieved Memory
Layer F — Evidence / Tool Result
```

Stable Platform gồm COSA identity, Co-Founder role, risk policy, tool-use rules và response conventions. Workspace Policy gồm founder overrides và company operating rules. Dynamic context không nên biến thành phần bất biến của system prompt nếu không cần.

---

# 15. Tool Registry nâng cấp

COSA đã có `ToolDefinition`; cần chuẩn hóa runtime resolver:

```text
ToolDefinition
  ↓
ToolAvailability
  ↓
Permission
  ↓
Risk
  ↓
ExecutionBackend
```

Logical metadata:

```text
name
description
schema
toolset
capabilities
handler
availability_check
required_env
risk_level
execution_backend
timeout
idempotent
side_effect_type
```

Side effect type:

```text
READ
INTERNAL_WRITE
EXTERNAL_DRAFT
EXTERNAL_WRITE
DESTRUCTIVE
FINANCIAL
LEGAL_COMMITMENT
PRODUCTION_DEPLOY
```

---

# 16. Tool Availability Resolver

Tool không available thì **không đưa schema cho model**.

Ví dụ `deploy_hostinger` chỉ available khi Hostinger connection configured, VPS reachable, credentials valid, project có deployment target và tier cho phép.

Nếu availability check crash, xem tool là **unavailable**.

---

# 17. Toolset Resolver

Input:

```text
Agent
Capability
Stage
Plan
Environment
Permissions
Risk
```

Output:

```text
enabled toolsets
enabled tools
```

Marketing research mission chỉ cần `web_research`, `browser_readonly`, `evidence_capture`; không đưa production deploy, finance payment hay legal signature tools.

---

# 18. Risk Engine mở rộng

Giữ R0–R4:

```text
R0 Read-only
R1 Internal write
R2 External draft
R3 External/high-impact
R4 Irreversible/founder-only
```

Bổ sung safety scanner:

```text
Tool Call
   ↓
Schema validation
   ↓
Workspace permission
   ↓
Tool availability
   ↓
Risk classification
   ↓
Danger scanner
   ↓
Hard block
   ↓
Approval policy
   ↓
Execution
```

---

# 19. Hardline Blocklist

Có những hành vi không cho bypass kể cả admin UI:

```text
filesystem root wipe
disk formatting
fork bomb
raw device destructive writes
known credential exfiltration
attempted entitlement private-key access
attempted cross-workspace data extraction
```

Legitimate operator use-case phải chạy ngoài COSA agent runtime.

---

# 20. Không hỗ trợ Production YOLO Mode

Không expose “Disable all approvals” trên production.

Development unsafe mode chỉ khi:

```text
environment=development
sandbox=isolated
admin=true
visible_warning=true
```

Vẫn giữ hardline blocklist.

---

# 21. Execution Subruns

Hermes delegation pattern được chuyển thành **Execution Subrun**.

Founder không thấy `Research Agent #27`; founder chỉ thấy `Marketing Agent`.

Ví dụ:

```text
Marketing Agent
   │
   ├─ Research Subrun
   ├─ Competitor Subrun
   └─ Content Analysis Subrun
   │
   ▼
Synthesis Step
```

Ưu tiên reuse `AgentRun`, `AgentStep`, `ExecutionJob`, control-plane execution và `worker_main.py`.

Logical contract:

```text
id
parent_run_id
parent_step_id
goal
context_bundle
allowed_toolsets
blocked_tools
risk_cap
status
started_at
finished_at
result_summary
artifact_ids
```

Nếu model hiện có metadata JSONB, ưu tiên dùng trước khi tạo table.

---

# 22. Subrun Permission

Mặc định Subrun có thể read, research, analyze, produce artifact.

Mặc định không thể:

```text
create another mission
modify shared memory
send external messages
publish
schedule automation
change permissions
change prompts
pay
deploy production
```

Plan step cần quyền cao hơn phải quay về parent/founder approval.

---

# 23. Delegation Depth & Budget

Default:

```text
Domain Agent → Subrun
max_depth = 1
```

Mỗi Subrun có:

```text
max_iterations
max_cost
timeout
tool limits
```

Parent Mission có tổng budget.

---

# 24. Interrupt, Cancel & Steering

Founder hoặc parent Agent có thể `pause`, `cancel`, `steer` Subrun.

State:

```text
QUEUED
RUNNING
PAUSED
COMPLETED
FAILED
CANCELLED
```

---

# 25. Observable Execution

Mọi tool call nên phát event:

```text
TOOL_CALL_STARTED
TOOL_CALL_BLOCKED
TOOL_CALL_APPROVAL_REQUIRED
TOOL_CALL_COMPLETED
TOOL_CALL_FAILED
```

Hologram không cần show mọi detail mặc định; có thể cung cấp “View activity”.

---

# 26. Event Hook Model

Không dùng exception làm policy contract.

Typed result:

```text
ALLOW
BLOCK
REQUIRE_APPROVAL
MODIFY
DEFER
```

Security hooks như `before_tool_call`, `before_external_write`, `before_deploy`, `before_payment`, `before_secret_access` phải **fail closed**.

Observer hooks như `after_tool_call`, `usage_telemetry`, `learning_signal`, `activity_log` có thể **fail open**.

Hook timeout phải configurable. Default proposal: Observer 2s, Policy 5s.

CI phải kiểm tra declared hook có dispatch site thật.

---

# 27. Automation nâng cấp

Không thay scheduler hiện tại bằng Hermes cron; chỉ bổ sung semantics.

Scheduled automation nên support:

```text
prompt
mission_template
skills
schedule
delivery
project_id
domain
model_policy
risk_policy
```

Mỗi scheduled run dùng **fresh execution context**:

```text
New runtime context
   ↓
load current company/project state
   ↓
load skill versions
   ↓
execute
```

Scheduled automation mặc định không được tự tạo một scheduled automation khác trừ policy explicit.

Delivery có thể qua Hologram, Telegram, Zalo, Email và các adapter tương lai.

---

# 28. Messaging/Channel Adapter

Không copy Hermes Gateway.

Chuẩn hóa COSA adapter:

```python
ChannelAdapter:
    receive()
    send()
    authorize()
    resolve_thread()
    supports_buttons()
    supports_files()
    supports_voice()
    health_check()
```

---

# 29. Voice là Transport

Giữ:

```text
Desktop → LiveKit Local
Mobile/Web → LiveKit Cloud
```

Flow:

```text
Voice
→ Transcript
→ COSA Co-Founder Runtime
→ Mission/Chat
→ Response
→ TTS
```

Không tạo voice-specific agent.

---

# 30. A2A — External Agent Interoperability

Đưa vào P2/P3.

Internal 5 core agents dùng local runtime/events/jobs, không A2A.

A2A dùng khi giao tiếp với partner agent, customer agent, external research service, ERP agent hoặc specialized remote execution.

Bắt buộc có:

```text
peer authentication
trusted peer registry
rate limit
capability allowlist
audit
prompt-injection framing
credential scrubbing
timeout
loop protection
```

---

# 31. AI Model Policy

Không expose `/model` như primary UX cho founder.

COSA quyết định qua `ModelPolicy` dựa trên:

```text
task type
risk
latency
cost
context size
tool calling quality
vision
coding
legal/finance sensitivity
```

Learning Review có thể dùng model rẻ hơn main reasoning model nhưng candidate vẫn qua governance.

---

# 32. Capability & Skill interaction với Stage

Stage điều chỉnh recommendation, không khóa cứng.

### S1
Customer discovery, problem interview, ICP, evidence capture.

### S4
Campaign, CRM, attribution, outreach, landing pages.

Founder ở S1 vẫn có thể request deploy landing page; COSA có thể challenge nhưng không cấm vì stage.

---

# 33. Capability Pack

Optional business packs nên bundle:

```text
Capabilities
Skills
Toolsets
Templates
Prompt fragments
Policies
```

Không nhất thiết bundle Agent.

Ví dụ Vietnam Microenterprise Finance Pack dùng Finance Agent với nhiều capabilities/skills/templates, không sinh Tax Agent, Bookkeeping Agent và Cashflow Agent riêng.

---

# 34. Skill Distribution từ Central

Central có thể phát Platform Skill Pack đã ký số.

Local:

```text
download
verify
diff
install
```

Workspace override không bị overwrite khi platform skill update. COSA có thể show upstream diff và offer rebase.

---

# 35. Skill Security

AI-generated skill luôn xem là `UNTRUSTED` trước khi active.

Scan:

```text
prompt injection
credential exfiltration
shell commands
filesystem writes
network calls
MCP references
dangerous code
path traversal
symlink escape
```

`references/` là read-only knowledge; `templates/` là starter artifacts; `scripts/` là executable và cần scrutiny cao hơn; `assets/` là non-executable resources.

Platform critical skills có `protected=true`; workspace/AI không delete, chỉ fork override.

Mọi skill revision phải rollback được; không delete history.

---

# 36. Hologram Hub cập nhật

Không tăng top-level cards. Giữ:

```text
COSA Co-Founder
Company Pulse
Top 3 Focus
Waiting for You
AI Workforce
```

Learning hiển thị trong **Waiting for You**:

```text
COSA learned a new sales qualification pattern.
Review skill update.
```

Buttons:

```text
Review
Approve
Reject
```

AI Workforce card có thể hiển thị `Capabilities`, `Active Skills`, `Missions`, `Status`, nhưng không show internal Subruns như agents.

Admin/Founder Settings có thể tổ chức:

```text
AI Workforce
  └── Marketing
      ├── Capabilities
      ├── Skills
      ├── Tools
      ├── Permissions
      └── Learning
```

---

# 37. API đề xuất

Không nhất thiết tạo hết ngay; ưu tiên reuse existing routers.

## Capability

```text
GET /api/v1/workforce/capabilities
GET /api/v1/workforce/capabilities/{key}
```

## Skills

```text
GET  /api/v1/workforce/skills
GET  /api/v1/workforce/skills/{key}
GET  /api/v1/workforce/skills/{key}/versions
POST /api/v1/workforce/skills/{key}/rollback
```

## Learning

```text
GET  /api/v1/workforce/learning/candidates
POST /api/v1/workforce/learning/candidates/{id}/approve
POST /api/v1/workforce/learning/candidates/{id}/reject
POST /api/v1/workforce/learning/review/{mission_id}
```

## Subruns

```text
GET  /api/v1/workforce/runs/{run_id}/subruns
POST /api/v1/workforce/subruns/{id}/cancel
POST /api/v1/workforce/subruns/{id}/steer
```

Tất cả phải dùng `WorkspaceContext`.

---

# 38. Events đề xuất

```text
CAPABILITY_RESOLVED
SKILL_LOADED
SKILL_REVISION_PROPOSED
SKILL_REVISION_APPROVED
SKILL_REVISION_REJECTED

SUBRUN_CREATED
SUBRUN_STARTED
SUBRUN_COMPLETED
SUBRUN_FAILED
SUBRUN_CANCELLED

LEARNING_REVIEW_STARTED
LEARNING_REVIEW_COMPLETED
MEMORY_CANDIDATE_CREATED
MEMORY_PROMOTED

TOOL_CALL_STARTED
TOOL_CALL_APPROVAL_REQUIRED
TOOL_CALL_BLOCKED
TOOL_CALL_COMPLETED
TOOL_CALL_FAILED
```

---

# 39. File-level Implementation Map

Các path phải audit trước khi chỉnh.

## Workforce

```text
backend/app/workforce/models.py
backend/app/workforce/capabilities/*
backend/app/workforce/skills/*
backend/app/workforce/agents/*
```

Mục tiêu: tìm canonical Capability/Skill/Run/Tool models; Capability Registry; Skill version/provenance; Subrun integration; không tạo visible agents mới.

## Co-Founder

```text
backend/app/workforce/orchestrator/cosa_cofounder_service.py
```

Bổ sung CapabilityResolver/SkillResolver sau Mission/Plan, không thay core.

## Memory

```text
backend/app/workforce/memory/*
```

Audit memory scopes, semantic retrieval, promotion và provenance. Không tạo file memory làm runtime source of truth nếu DB đã có.

## Worker

```text
backend/app/worker_main.py
```

Bổ sung learning-review job type nếu cần, nhưng ưu tiên reuse generic job infrastructure.

## Outcome

```text
backend/app/founder_os/outcomes/*
```

Mission Outcome là trigger chính của Learning Review.

## Approval

```text
backend/app/workforce/governance/*
backend/app/workforce/models.py
```

Kết hợp R0–R4 với dangerous-operation scanner.

## Automation

```text
backend/app/workforce/automation/*
backend/app/workforce/automations/*
```

Audit duplicate directories trước; không tạo scheduler mới nếu hiện tại đã có.

## Channels

```text
backend/app/channels/*
```

Chuẩn hóa ChannelAdapter khi cần.

## Flutter

```text
frontend/lib/modules/hologram_hub/*
frontend/lib/modules/ai_team/*
frontend/lib/modules/agents/*
frontend/lib/modules/ai_operations/*
frontend/lib/modules/approvals/*
```

Không tạo thêm top-level module trước inventory.

---

# 40. Migration Plan

## Migration 1 — Inventory

Không schema change. Tạo `docs/architecture/capability_skill_tool_inventory.md` map Capability, Skill, Tool, AgentRun, Memory, Learning và Automation entities.

## Migration 2 — Capability metadata

Chỉ khi thiếu. Ưu tiên JSONB.

## Migration 3 — Skill version/provenance

Migrate existing skills thành version 1, không mất content.

## Migration 4 — LearningCandidate

Chỉ tạo nếu chưa có generic proposal/review entity đủ dùng.

## Migration 5 — Memory metadata

Add provenance/scope fields nếu model hiện tại thiếu.

## Migration 6 — Subrun relation

Nếu AgentRun có parent relation thì reuse. Nếu không, ưu tiên `parent_run_id` + `run_kind` thay vì table mới.

---

# 41. Implementation Phases

## P1-H0 — Inventory & Contracts

Deliverables:

- capability inventory;
- skill inventory;
- tool inventory;
- memory inventory;
- canonical run model;
- no runtime change.

Exit: không còn ambiguity về entity canonical.

## P1-H1 — Capability + Toolset Runtime

Deliverables:

- Capability Registry;
- Tool Availability;
- Toolset Resolver;
- schema filtering;
- permissions;
- risk integration.

Exit: Marketing research mission chỉ nhận đúng toolset cần thiết.

## P1-H2 — Skill Registry

Deliverables:

- versioned skills;
- provenance;
- workspace overrides;
- platform immutable defaults;
- rollback.

Exit: AgentPlan resolve/load được skill version cụ thể.

## P1-H3 — Learning Review

Deliverables:

- trigger from Outcome;
- LearningCandidate;
- skill/memory candidate;
- founder review.

Exit: Mission complete có thể tạo skill revision proposal có evidence.

## P1-H4 — Execution Subruns

Deliverables:

- child runs;
- tool restriction;
- budget;
- parallel execution;
- cancel/steer;
- parent synthesis.

Exit: Marketing mission chạy 2–3 subruns song song mà UI vẫn chỉ show Marketing Agent.

## P1-H5 — Memory Promotion

Deliverables:

- layered retrieval;
- promotion pipeline;
- provenance;
- dedupe;
- validity.

Exit: COSA nhớ đúng founder/company/project mà không dump toàn bộ history.

## P2-H6 — Automation Enhancement

Skill-backed automation, fresh run context, delivery adapters, recursion guard.

## P2/P3-H7 — A2A

Peer registry, A2A adapter, security, external capability mapping. Không dùng cho internal core domains.

---

# 42. Test Strategy

## Capability tests

- resolve owner Agent;
- resolve stage recommendations;
- capability unavailable if feature disabled;
- founder override allowed where policy permits.

## Tool tests

- unavailable tool absent from model schema;
- permission denied;
- risk classification;
- hardline blocked;
- approval required;
- workspace isolation.

## Skill tests

- platform skill immutable;
- workspace can fork;
- version increment;
- rollback;
- checksum;
- protected skill cannot delete;
- malicious skill blocked.

## Learning tests

Founder rejects output and provides correction → `LearningCandidate` created, **không** mutate skill ngay. Approval → applied skill version.

## Memory tests

- duplicate candidate merged/rejected;
- cross-workspace memory impossible;
- expired fact not injected;
- evidence-backed fact outranks weak assumption;
- greeting does not retrieve heavy memory.

## Subrun tests

- no recursive delegation default;
- no memory write;
- no send message;
- parent can cancel;
- parallel outputs preserve attribution;
- child failure does not corrupt parent state.

---

# 43. Security Tests

```text
skill path traversal
symlink skill delete
script exfiltration
cross-workspace memory
tool schema spoofing
approval bypass
subrun permission escalation
automation recursion
A2A prompt injection
A2A credential leakage
```

---

# 44. CI Gates

Bổ sung:

```text
canonical-model-inventory-check
capability-resolution-tests
tool-availability-tests
skill-governance-tests
learning-review-tests
memory-provenance-tests
subrun-isolation-tests
hook-integrity-tests
security-hook-fail-closed-tests
```

---

# 45. Definition of Done

### Capability

- new feature mặc định là Capability/Skill/Tool, không Agent;
- model chỉ thấy tools cần thiết.

### Learning

- Outcome có thể sinh LearningCandidate;
- learning có evidence/provenance;
- founder có governance.

### Skills

- versioned;
- rollback;
- platform immutable;
- workspace override;
- scan trước active.

### Memory

- layered;
- retrieved on demand;
- provenance;
- không full dump.

### Execution

- Subruns parallel;
- isolated permissions;
- observable;
- cancelable.

### Security

- fail-closed security hooks;
- hardline blocklist;
- no production YOLO;
- no cross-workspace leakage.

---

# 46. Claude Code Prompt — Inventory

```text
Bạn đang triển khai COSA Capability & Learning Engine.

BƯỚC NÀY CHỈ AUDIT, KHÔNG TẠO MODEL/TABLE.

Search toàn repo cho:
Capability, Skill, ToolDefinition, AgentToolPermission, AgentRun, AgentStep,
ExecutionJob, Memory, Learning, Proposal, Outcome, Automation, WorkspaceAgent.

Đọc:
backend/app/db/base.py
backend/app/workforce/models.py
backend/app/workforce/capabilities/
backend/app/workforce/skills/
backend/app/workforce/memory/
backend/app/workforce/agents/
backend/app/founder_os/outcomes/

Tạo:
docs/architecture/capability_skill_tool_inventory.md

Mỗi entity ghi:
- Python class
- table
- responsibility
- read paths
- write paths
- migrations
- tests
- status ACTIVE/COMPATIBILITY/DEPRECATED
- canonical recommendation

KHÔNG tạo *_v2.
KHÔNG rename/drop.
```

---

# 47. Claude Code Prompt — Capability Resolver

```text
Triển khai Capability Registry native COSA.

Yêu cầu:
- reuse capability models hiện có nếu có;
- capability thuộc 1 core domain owner;
- support stage recommendation nhưng không hard block;
- support required toolsets;
- support required skills;
- support feature/tier availability;
- expose resolver service.

Không thêm Agent.

Tests:
- Marketing capability routes to cmo_agent;
- disabled feature unavailable;
- S1 recommends discovery capability;
- founder vẫn request capability ngoài stage được.
```

---

# 48. Claude Code Prompt — Toolset Resolver

```text
Triển khai Toolset Resolver.

Input:
WorkspaceContext
AgentDefinition
Capability
Mission
Environment

Output:
list tool definitions model được phép thấy.

Filter theo:
- availability
- workspace permission
- plan entitlement
- capability
- risk
- environment

Nếu availability check throw: exclude tool.
KHÔNG gửi toàn bộ ToolDefinition cho model.

Integration test:
Finance agent không thấy production deployment tools trong finance-read task.
```

---

# 49. Claude Code Prompt — Skill Registry

```text
Triển khai Skill Registry theo hướng versioned procedural memory.

Trước khi tạo schema:
audit existing workforce/skills models.

Yêu cầu:
- platform default immutable;
- workspace override/fork;
- version history;
- checksum;
- provenance;
- status DRAFT/STAGED/ACTIVE/EXPERIMENTAL/DEPRECATED/ARCHIVED/BLOCKED;
- rollback;
- protected skill;
- content + optional references/templates/scripts/assets metadata.

Không dùng file system làm source of truth runtime nếu DB model hiện có.
File package chỉ dùng import/export/edit/distribution.
```

---

# 50. Claude Code Prompt — Learning Review

```text
Triển khai Learning Review Worker.

Trigger trước:
Mission Outcome finalized.

Input:
mission, plan, agent runs, artifacts, evidence, founder feedback, existing skills.

Output:
LearningCandidate only.

Worker KHÔNG được:
- send external message
- publish
- deploy
- pay
- modify accounting
- create mission
- trực tiếp activate skill

Candidate types:
FOUNDER_PREFERENCE
COMPANY_FACT
PROJECT_FACT
SKILL_CREATE
SKILL_PATCH
SKILL_DEPRECATE

Mọi candidate phải có provenance và confidence.
Viết tests.
```

---

# 51. Claude Code Prompt — Memory Promotion

```text
Triển khai Memory Promotion Pipeline.

Không lưu raw chat thành durable memory trực tiếp.

Flow:
Observation → Candidate → classify → dedupe → evidence/confidence → promote/stage/reject.

Memory scopes:
FOUNDER
COMPANY
PROJECT
DOMAIN
EPISODIC

Fields cần có hoặc map:
source
source_id
confidence
evidence
validity
sensitivity
supersession

ContextAssembler chỉ retrieve relevant memory theo intent và token budget.
Greeting không load heavy memory.
```

---

# 52. Claude Code Prompt — Execution Subruns

```text
Triển khai Execution Subruns bằng canonical AgentRun/ExecutionJob hiện có.

Không tạo visible Agent mới.

Requirements:
- parent_run_id hoặc equivalent;
- isolated context;
- allowed toolsets;
- blocked side-effect tools mặc định;
- max depth=1;
- budget/timeout;
- parallel run support;
- cancel;
- steer;
- result attribution;
- parent synthesis.

Default child cannot:
memory write
external send
cron create
mission create
production deploy
payment

Tests cho isolation và cancellation.
```

---

# 53. Claude Code Prompt — Risk/Approval Enhancement

```text
Bổ sung Dangerous Operation Scanner vào existing R0-R4 policy.

Pipeline:
permission
availability
risk
danger scanner
hardline
approval
execution

Hardline không bypass production.
Security hooks fail closed.
Observer hooks fail open.
Hook timeout configurable.

Không thêm YOLO mode cho production.
```

---

# 54. Claude Code Prompt — Hologram Learning UX

```text
Cập nhật Hologram Hub mà KHÔNG tạo top-level navigation mới.

Waiting for You:
- Learning Candidate card
- Review
- Approve
- Reject

AI Workforce:
- mỗi core agent có số Capabilities / Skills
- không show execution subruns như agents

Company Pulse:
có thể show số learning candidates nhỏ nếu hữu ích.

Dùng backend state thật.
Không fake success.
```

---

# 55. DO NOT — bắt buộc

Claude Code không được:

```text
1. Clone Hermes làm service production.
2. Tạo HermesAgentService làm orchestration chính.
3. Tạo AIAgent runtime thứ hai.
4. Tạo thêm visible agents cho mỗi capability.
5. Tạo CapabilityV2/SkillV2 nếu model tương đương đã có.
6. Dùng jobs.json làm scheduler source of truth.
7. Dùng MEMORY.md làm enterprise memory DB.
8. Cho AI sửa platform skill trực tiếp.
9. Auto-activate AI-generated script skill.
10. Expose production YOLO mode.
11. Cho subrun tự send/publish/pay/deploy mặc định.
12. Expose toàn bộ tools cho model.
13. Dùng A2A cho 5 core internal agents.
14. Sync full private company memory lên Central.
15. Biến learning thành mandatory founder workflow.
```

---

# 56. Ví dụ E2E — Marketing

Founder:

```text
Tìm 20 khách hàng B2B phù hợp trong 30 ngày.
```

Runtime:

```text
COSA
↓
Mission
↓
Marketing + Sales
↓
Capabilities:
ICP Definition
Market Research
Lead Qualification
↓
Skills:
B2B ICP v2
Lead Qualification v3
↓
Toolsets:
web_research
crm
↓
Subruns:
research segments
competitor analysis
prospect sourcing
↓
Evidence
↓
20 lead artifacts
↓
Outcome
```

Founder phản hồi:

```text
Loại nhóm agency vì conversion rất thấp.
```

Learning:

```text
Learning Review
↓
Skill PATCH candidate: B2B Lead Qualification
↓
Evidence: mission outcome + founder correction
↓
STAGED
↓
Founder approve
↓
Skill v4
```

Lần sau COSA dùng v4.

---

# 57. Ví dụ E2E — Build

Founder:

```text
Tạo landing page cho project và deploy lên subdomain.
```

Runtime:

```text
Build & Tech
↓
Capabilities:
landing_page_build
deployment
↓
Skill:
COSA Landing Page Build
↓
Toolsets:
code
files
sandbox
hostinger
↓
Subruns:
copy/layout
implementation
test
↓
Artifact:
Next.js project
↓
Approval R3:
Deploy production?
↓
Founder approves
↓
Deploy
↓
Outcome
```

Nếu deploy fail vì Hostinger-specific issue, Learning Review tạo Skill Support Reference Candidate — **không tạo Hostinger Agent**.

---

# 58. Ví dụ E2E — Finance

Founder:

```text
Phân tích runway hiện tại.
```

Flow:

```text
Finance Agent
↓
finance_analysis capability
↓
cashflow skill
↓
read-only finance tools
↓
actual finance snapshot
↓
calculation
↓
Evidence-linked answer
```

Learning Review chỉ học workflow/convention; không biến số tài chính hiện tại thành permanent procedural skill.

---

# 59. Ví dụ E2E — Legal

Founder:

```text
Kiểm tra hợp đồng này.
```

Flow:

```text
Legal Agent
↓
contract_review capability
↓
Vietnam Contract Review Skill
↓
document tools
↓
relevant policy/legal evidence
↓
Artifact: review memo
```

Nếu founder nói “Công ty luôn yêu cầu điều khoản IP ownership này” thì tạo Company Policy Memory Candidate, không sửa platform legal skill.

---

# 60. Quan hệ với Central Control Plane

Central có thể biết:

```text
skill pack version adoption
capability usage aggregate
feature adoption
learning engine enabled
```

Central không cần nhận private skill content, founder memory, full mission transcript hay company evidence trừ consent/support use-case.

Memory/skill candidates có thể chứa sensitive data nên cần sensitivity classification, secret scanning, PII policy, local storage và redaction trước telemetry.

---

# 61. Cost & Performance Control

Learning Review không chạy mọi turn.

```text
skip greeting
skip trivial Q&A
run on mission outcome
run on explicit correction
run on meaningful failure
run on founder rejection/revision
```

Background model có thể rẻ hơn.

Không load toàn bộ Skill body vào prompt. Resolve metadata trước rồi chỉ inject selected skill. Tool schemas cũng chỉ inject sau filtering.

---

# 62. Observability & Success Metrics

Metrics local/runtime:

```text
capability_resolution_latency
tools_exposed_per_run
skill_load_count
learning_candidates_created
learning_candidates_approved
skill_reuse_rate
subrun_count
subrun_failure_rate
approval_wait_time
```

Không sync content private lên Central.

Sau 30–60 ngày nên đo:

```text
repeated mission completion time giảm
rework giảm
founder corrections giảm
approved skill reuse tăng
toolset size giảm so với all-tools prompt
cost/run giảm hoặc ổn định
```

Nếu learning không cải thiện outcome thì không coi self-improving loop là thành công.

---

# 63. Implementation Order chốt

Thứ tự bắt buộc:

```text
1. Hoàn thành P0 consolidation/security hiện tại.
2. Inventory canonical models.
3. Capability Registry.
4. Toolset Resolver.
5. Skill Registry/versioning.
6. Learning Review Candidate pipeline.
7. Memory Promotion.
8. Execution Subruns.
9. Automation enhancement.
10. A2A external interoperability.
```

Không xây self-learning trước khi runtime truth ổn định.

---

# 64. North Star sau cập nhật

Trước:

```text
Founder
→ COSA
→ Mission
→ Agent
→ Tool
→ Outcome
```

Sau:

```text
Founder
→ COSA
→ Mission
→ Agent
→ Capability
→ Skill
→ Toolset
→ Tool
→ Execution
→ Artifact
→ Evidence
→ Outcome
→ Learning Review
→ Memory / Skill Improvement
→ COSA làm tốt hơn lần sau
```

---

# 65. Product Meaning

Không quảng cáo COSA là “AI tự học hoàn toàn”. Cách diễn đạt chính xác:

> **COSA learns from approved operating outcomes, founder feedback, evidence, and repeated workflows to improve its reusable company knowledge and skills.**

Tiếng Việt:

> **COSA tích lũy kinh nghiệm từ kết quả vận hành, phản hồi của founder và bằng chứng thực tế để ngày càng hiểu công ty và thực hiện các công việc lặp lại tốt hơn.**

---

# 66. Kết luận

Hermes Agent không nên trở thành một component runtime bên trong COSA.

Giá trị lớn nhất cần hấp thụ là tư duy:

```text
Agent ≠ Skill ≠ Tool ≠ Memory
```

và vòng lặp:

```text
Execute
→ Observe
→ Learn
→ Improve
```

COSA phải hấp thụ các pattern đó trên nền Mission / Evidence / Outcome hiện có.

Sau cập nhật này, COSA được định nghĩa rõ hơn:

> **COSA là AI Co-Founder Operating System có khả năng điều phối doanh nghiệp bằng Mission, sử dụng 5 Core Domain Agents, lựa chọn Capability/Skill/Tool phù hợp, thực thi có governance, đo Outcome bằng Evidence và tích lũy kinh nghiệm đã được kiểm soát để cải thiện hoạt động trong các lần tiếp theo.**

Đây là hướng mở rộng phù hợp nhất mà không phá consolidation architecture đã khóa.
