# COSA — Master Agentic Runtime, Governance & Integration Specification

**Status:** Proposed Integration Specification  
**Target:** COSA / mCOSA Founder OS  
**Primary audience:** Founder/Admin, Claude Code/Codex implementation agents  
**Architecture goal:** Consolidate COSA into one coherent Founder Agentic Operating System instead of a collection of disconnected agents, prompts, workflows, tools, dashboards, and integrations.

---

## 0. Executive Summary

COSA should not continue growing by adding more visible modules, more agents, more prompt screens, or more technical cards on the main dashboard.

The next phase should consolidate the platform around a single runtime model:

```text
Founder
  ↓
Chat / Voice
  ↓
COSA Companion
  ↓
Conversation Guard
  ↓
Intent Router
  ↓
Verb Router
  ↓
Domain Router
  ↓
Specialist Router
  ↓
Mission Orchestrator
  ↓
COSA Agent Kernel
  ↓
COSA Governance Kernel
  ↓
Tool / MCP / n8n / Agent Host
  ↓
Real System
  ↓
Reality Verifier
  ↓
Outcome Certificate
  ↓
Finish / Learn
  ↓
COSA Brain
```

The architecture draws useful patterns from four recent research directions:

- **MyIris** → intent/verb routing, stateful vs stateless work, background execution, review gates, voice continuity.
- **Agency Agents** → specialist profiles, deliverable contracts, handoff contracts, quality gates, agent compilation to different runtimes.
- **Awesome AI Anatomy** → production agent kernel: context cascade, tool inspection, budgets, stuck detection, sandboxing, event-driven runtime, evidence-based completion.
- **Awesome AI Agents** → ecosystem radar, governance, reality verification, mission-as-code, benchmarking, evaluation, secret brokering, deterministic orchestration.

COSA should learn patterns from these projects without becoming dependent on them as the core runtime.

---

# 1. Product Positioning

COSA is a **Founder Agentic Operating System** for a One Person Company (OPC) and later small teams.

The product should feel like:

> “I talk to COSA. COSA understands what I want, organizes the work, chooses the right expertise, performs the work safely, proves the result, and remembers useful lessons.”

The founder should **not** need to understand:

- Agent names
- Prompt versions
- Skills
- MCP
- n8n workflow IDs
- Model providers
- Tool registries
- Vector databases
- Sandbox engines
- DSPy
- LiveKit topology
- Claude Code/Codex runtime details

Those belong in the Admin/Infrastructure layer.

---

# 2. Core Product Principles

## 2.1 NO INTENT = NO TOOL

This is a mandatory invariant.

```text
NO INTENT
   =
NO CAPABILITY
   =
NO TOOL
```

Examples:

| Founder says | Expected behavior |
|---|---|
| “Chào COSA” | Conversational reply only |
| “Cảm ơn nhé” | Conversational reply only |
| “Hôm nay thế nào?” | Founder Brief capability |
| “Project mID đang thế nào?” | Project read capability |
| “Tìm 20 khách hàng cho sản phẩm X” | Sales prospecting mission |
| “Gửi email cho 20 khách hàng này” | Draft → Policy → Approval → Send |

A greeting must never trigger project lookup, database retrieval, CRM search, or other tools.

---

## 2.2 Intent and Verb are different

**Intent** answers:

> Người dùng muốn gì?

**Verb** answers:

> Hệ thống phải thực hiện loại công việc gì?

Example:

```text
User:
“Xem landing page này có ổn không.”
```

```yaml
intent: landing_page_review
verb: JUDGE
domain: marketing
```

Another:

```text
User:
“Sửa landing page theo các góp ý đó.”
```

```yaml
intent: landing_page_modify
verb: EXECUTE
domain: build
```

---

## 2.3 Use AI for ambiguity, code for certainty

Use AI for:

- Intent classification
- Research
- Planning
- Analysis
- Judgment
- Drafting
- Content
- Qualification
- Summarization

Use deterministic code for:

- State transitions
- Permissions
- Budgets
- Retry limits
- Timeouts
- Approval requirements
- Idempotency
- Deduplication
- Scheduling
- Accounting invariants
- Completion verification
- External action control

---

## 2.4 Runtime policy is stronger than prompt instruction

Do not depend on prompts such as:

```text
“Không được tự gửi email.”
```

Instead enforce:

```text
email.send
  ↓
Governance Policy
  ↓
approval_required = true
```

Prompts explain behavior.  
Backend policy controls behavior.

---

## 2.5 DONE is not SUCCESS

An agent saying “done” is not proof.

COSA must distinguish:

```text
Tool said SUCCESS
≠
Real system changed correctly
```

Every high-value action should support real-world verification.

---

# 3. Target System Architecture

```text
                             FOUNDER
                                │
                         Chat / Voice / IM
                                │
                                ▼
                         COSA COMPANION
                                │
                      Conversation Guard
                                │
                                ▼
                         INTENT ROUTER
                                │
                          VERB ROUTER
                                │
                         DOMAIN ROUTER
                                │
                      SPECIALIST ROUTER
                                │
                     MISSION ORCHESTRATOR
                                │
                          Mission Ledger
                                │
                                ▼
╔════════════════════════ COSA AGENT KERNEL ═══════════════════════╗
║                                                                  ║
║  Context Manager         Event Bus            Run State           ║
║  Budget Manager          Provider Router      Tool Registry       ║
║  Tool Sentinel           Stuck Detector       Sandbox Manager     ║
║  Memory Manager          Evidence Manager     Observability       ║
║  Handoff Manager         Quality Gate         Feature Flags       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
                                │
                                ▼
╔══════════════════════ COSA GOVERNANCE KERNEL ════════════════════╗
║                                                                  ║
║ Identity  Permission  Scope  Policy  Risk  Approval              ║
║ Secret Broker  Egress Control  Audit  Rate Limit                 ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
                                │
                                ▼
                   Tool / MCP / n8n / Agent Host
                       │       │        │
                       ▼       ▼        ▼
                      APIs   External  Claude/Codex
                              Systems
                                │
                                ▼
                         REAL SYSTEM STATE
                                │
                                ▼
                         REALITY VERIFIER
                                │
                                ▼
                       OUTCOME CERTIFICATE
                                │
                     ┌──────────┴──────────┐
                     ▼                     ▼
                  FINISH                 FAILED
                     │
                     ▼
                   LEARN
                     │
                     ▼
                  COSA BRAIN
```

---

# 4. Conversation Guard

The Conversation Guard is the first runtime layer after Companion input.

Its purpose:

1. Detect simple conversational turns.
2. Prevent accidental tool use.
3. Normalize user input.
4. Check channel/session metadata.
5. Decide whether routing is needed.

Suggested outputs:

```yaml
conversation_mode: converse | actionable | ambiguous
should_route: true | false
reason: string
```

Examples:

```yaml
message: "chào"
conversation_mode: converse
should_route: false
```

```yaml
message: "tìm 30 khách sạn tiềm năng ở Vũng Tàu"
conversation_mode: actionable
should_route: true
```

---

# 5. Verb Architecture

Recommended canonical verbs:

```text
CONVERSE
SHAPE
INVESTIGATE
JUDGE
EXECUTE
FINISH
LEARN
```

## 5.1 CONVERSE

Use for ordinary conversation.

No Mission required by default.  
No tool unless the user clearly requests information/action.

## 5.2 SHAPE

Clarify and structure an ambiguous goal.

Examples:

- Define requirements
- Turn idea into scope
- Create plan
- Create specification
- Ask necessary questions

This is commonly stateful.

## 5.3 INVESTIGATE

Read/research/analyze evidence.

Examples:

- Competitor research
- Prospect research
- Market research
- Project status inspection
- Source gathering

Usually stateless/background.

## 5.4 JUDGE

Evaluate something against criteria.

Examples:

- Review proposal
- Score lead
- Review contract risk
- Evaluate landing page
- Compare options

## 5.5 EXECUTE

Change internal or external state.

Examples:

- Create task
- Update CRM
- Modify file
- Build landing page
- Create campaign draft
- Deploy
- Send message

EXECUTE must always pass Governance.

## 5.6 FINISH

Verify and close a Mission.

FINISH should never be called based only on agent self-report.

Required path:

```text
EXECUTE
→ EVIDENCE
→ VERIFY
→ FINISH
```

## 5.7 LEARN

Extract reusable learning from completed work.

Examples:

- Campaign insight
- Customer preference
- Failed tactic
- Reusable workflow
- Prompt improvement candidate
- Skill candidate

LEARN is not unrestricted memory write.

---

# 6. Domain Agent Architecture

Keep the number of visible Domain Agents small.

Recommended:

```text
Founder Agent
Sales Agent
Marketing Agent
Finance Agent
Legal Agent
Build/Tech Agent
```

Optional later:

```text
Support Agent
Operations Agent
HR/People Agent
```

Do not create one Agent per micro-function.

---

# 7. Specialist Architecture

Specialists are internal profiles, not dashboard modules.

Example:

```text
Sales Agent
├── Outbound Specialist
├── Discovery Specialist
├── Pipeline Analyst
├── Deal Strategist
├── Proposal Specialist
└── Account Specialist
```

```text
Marketing Agent
├── Market Research Specialist
├── Campaign Strategist
├── Content Specialist
├── Landing Page Specialist
├── SEO Specialist
└── Attribution Analyst
```

```text
Finance Agent
├── Accounting Specialist
├── Cashflow Analyst
├── FP&A Specialist
└── Finance Analyst
```

```text
Build Agent
├── Architecture Specialist
├── Implementation Specialist
├── Testing Specialist
└── Deployment Specialist
```

---

# 8. Agent Contract

An Agent must be a structured contract, not just a prompt.

Suggested schema:

```yaml
id: sales.outbound
version: 1

domain: sales
role: Outbound Strategist

mission:
  Generate qualified pipeline from approved ICP

verbs:
  - INVESTIGATE
  - SHAPE
  - JUDGE

capabilities:
  - icp_analysis
  - prospect_search
  - buying_signal_analysis
  - lead_qualification
  - outreach_planning

inputs:
  - product
  - market
  - icp
  - campaign_context

outputs:
  - prospect_list
  - signal_report
  - qualification_report
  - outreach_draft

quality_gates:
  - evidence_required
  - duplicate_check
  - icp_fit_required

external_actions:
  email.send:
    approval_required: true

memory:
  read:
    - sales_learnings
    - customer_context
  write_candidate:
    - experiment_results

prompt:
  id: sales.outbound.system
  version: 3

skills:
  - sales.icp
  - sales.buying_signals
  - sales.outreach

tools:
  - web.search
  - browser.extract
  - crm.read
```

---

# 9. Canonical Agent Spec + Agent Compiler

Do not maintain separate manually-written agents for Claude Code, Codex, Gemini, etc.

Create one canonical COSA Agent Spec.

```text
COSA Agent Spec
      │
      ▼
 Agent Compiler
 ┌────┼─────┬─────┐
 ▼    ▼     ▼     ▼
Claude Codex Gemini OpenClaw
```

Suggested structure:

```text
agents/
  sales/
    outbound.agent.yaml
  marketing/
    campaign.agent.yaml
  finance/
    analyst.agent.yaml
```

Compiler adapters:

```text
compiler/
  claude_code.py
  codex.py
  gemini.py
  openclaw.py
```

---

# 10. Mission Model

Mission is the central unit of agentic work.

Suggested hierarchy:

```text
Goal
  ↓
Mission
  ↓
Task
  ↓
Workflow Run
  ↓
Action
```

Example:

```text
Goal:
Increase qualified pipeline

Mission:
Generate 20 qualified leads

Tasks:
1. Confirm ICP
2. Search companies
3. Detect buying signals
4. Enrich contacts
5. Score leads
6. Save qualified leads
```

---

# 11. Mission Modes

## 11.1 QUICK

One worker, short task.

Examples:

- Summarize a document
- Check project status
- Rewrite text

## 11.2 MISSION

Multi-step work with one or more specialists.

Examples:

- Find 30 prospects
- Prepare campaign
- Review legal document

## 11.3 PROGRAM

Multiple missions with milestones.

Examples:

- Launch product in six weeks
- Enter new market
- Build and deploy CRM

---

# 12. Dynamic Mission vs Mission-as-Code

## Dynamic Mission

Created from natural language.

```text
"Tìm 20 khách hàng cho sản phẩm X"
```

Planner creates execution plan dynamically.

## Mission-as-Code

Use for repeated or high-value workflows.

Example:

```yaml
mission:
  id: sales.prospecting.v1

inputs:
  count: 20
  icp: approved

steps:
  - research
  - verify_company
  - enrich
  - qualify
  - crm_import

policy:
  external_action: false

budget:
  max_cost_usd: 0.30
  max_duration_minutes: 20
  max_pages: 50

finish:
  verified_leads_required: 20
```

Recommended evolution:

```text
Dynamic Mission
→ successful repeated runs
→ pattern detected
→ Mission Template Candidate
→ Founder/Admin approval
→ Mission-as-Code
```

---

# 13. Mission State Machine

Recommended states:

```text
RECEIVED
CLASSIFIED
SHAPING
READY
QUEUED
RUNNING
WAITING_USER
WAITING_APPROVAL
WAITING_EXTERNAL
VERIFYING
COMPLETED
FAILED
CANCELLED
EXPIRED
DENIED
```

Rules:

- Every outstanding obligation must settle exactly once.
- Every waiting state must have timeout/expiry policy.
- No Mission may wait forever.

---

# 14. Stateful vs Stateless Workers

## Stateful

Use when the agent must pause and interact directly with user.

Best for:

- SHAPE
- requirement clarification
- interactive planning

## Stateless

Use for:

- INVESTIGATE
- JUDGE
- EXECUTE background work
- FINISH verification
- LEARN extraction

Important:

> Stateless does not mean no continuity.

Mission context remains persistent even when a worker process ends.

---

# 15. Mission Ledger

Do not rely on full chat transcript as the shared state between agents.

Create a durable Mission Ledger.

Recommended entities:

```text
missions
mission_steps
mission_events
mission_handoffs
mission_artifacts
mission_evidence
mission_verifications
mission_approvals
mission_outcomes
```

Mission Ledger stores:

- Goal
- Plan
- Tasks
- Specialist assignment
- Handoffs
- Evidence
- Decisions
- Artifacts
- Tool calls
- Approvals
- Verification
- Outcome
- Learning candidates

---

# 16. Handoff Contract

Agents must not hand off work with vague text such as “I’m done”.

Recommended contract:

```yaml
handoff:
  mission_id: mis_123
  task_id: task_456

  completed:
    - researched 30 companies
    - filtered 12 ICP-fit accounts

  artifacts:
    - artifact://prospects.csv

  evidence:
    - evidence://src_001
    - evidence://src_002

  decisions:
    - exclude companies under 10 employees

  assumptions:
    - market focus is Vietnam

  unresolved:
    - 3 companies missing verified contact

  risks:
    - 2 websites may contain stale staff data

  recommended_next_specialist:
    sales.qualification

  next_action:
    qualify 12 accounts
```

Agent B should consume this contract, not re-read the entire Agent A conversation.

---

# 17. COSA Agent Kernel

The Agent Kernel should be owned by COSA.

Do not make LangGraph, CrewAI, n8n, OpenClaw, Claude Code, or any other framework the core runtime.

Recommended modules:

```text
cosa_runtime/
  conversation/
  router/
  verbs/
  domains/
  specialists/
  missions/
  context/
  events/
  tools/
  policy/
  approval/
  budget/
  sandbox/
  stuck/
  evidence/
  verification/
  memory/
  providers/
  observability/
  features/
```

The agent loop should be thin.

---

# 18. Middleware Architecture

Suggested middleware pipeline:

```text
Input
→ Conversation Guard
→ Intent
→ Verb
→ Domain
→ Specialist
→ Context Build
→ Budget Check
→ Planning
→ Tool Resolution
→ Tool Inspection
→ Approval
→ Sandbox
→ Execution
→ Observation
→ Stuck Check
→ Quality Gate
→ Evidence
→ Verification
→ Finish
→ Learn
```

Each middleware should:

- have typed input/output
- have tests
- declare dependencies
- avoid hidden ordering assumptions

Use explicit dependency ordering rather than comments such as “this middleware must be last”.

---

# 19. Context Management

COSA requires a Context Cascade.

## L0 — Working Context

- Current message
- Current Mission
- Current Task
- Recent results

## L1 — Lossless cleanup

Remove:

- duplicated state
- acknowledgements
- irrelevant boilerplate
- verbose completed tool responses

## L2 — Ephemeral context

Large one-turn data:

- DOM
- API dump
- logs
- browser state
- temporary search results

These should disappear after use.

## L3 — Structured Summary

Use structured schema:

```yaml
goal:
completed:
decisions:
constraints:
evidence:
files:
pending:
risks:
next:
```

## L4 — Full Compaction

Only when required.

---

# 20. Context Provenance

Every important context item should include provenance.

```text
RAW
RETRIEVED
SUMMARIZED
COMPRESSED
INFERRED
```

Example:

```yaml
context_item:
  source_type: compressed
  source_revision: ctx_082
  confidence: medium
```

For high-risk decisions, if relevant context is compressed:

```text
retrieve original evidence
```

before execution.

---

# 21. Context Pool Budget

Do not use only a global vector `top_k`.

Reserve context capacity by category.

Example:

```text
25% current mission
20% company knowledge
15% founder memory
15% customer context
10% relevant skills
10% historical learnings
5% anti-patterns
```

Example retrieval configuration:

```yaml
retrieve:
  mission: 5
  customer: 3
  knowledge: 4
  learning: 3
  anti_pattern: 2
  skill: 3
```

Then rerank.

---

# 22. Memory Architecture

COSA should maintain both:

## Curated Memory

- Founder preferences
- Company facts
- Decisions
- Customer insight
- Confirmed learning
- Approved strategy
- Reusable patterns

## Raw Event History

- Conversations
- Tool events
- Mission events
- Workflow runs
- Approvals
- Results
- Verification

Raw history is for audit/reconstruction.  
Curated memory is for frequent AI retrieval.

---

# 23. Memory Confidence and Lifecycle

Example:

```yaml
fact:
  key: customer_prefers_basic_plan
  value: true

source:
  campaign_id: cmp_021

confidence: 0.74

observed_at: 2026-08-16

status: active

expiry_policy:
  revalidate_after_days: 90
```

Do not treat every memory as permanent truth.

---

# 24. COSA Brain Structure

Recommended:

```text
Brain/
  Sources/
  Knowledge/
  Wiki/
  Memory/
  Decisions/
  Projects/
  People/
  Customers/
  Skills/
  Prompts/
  Agents/
  Workflows/
  Playbooks/
  Patterns/
  AntiPatterns/
  Experiments/
  Learnings/
  Templates/
```

---

# 25. Anti-Pattern Registry

Example:

```yaml
name: bulk-email-without-buying-signal
domain: sales

symptom:
  low_response_rate

evidence:
  - campaign_124

better_alternative:
  buying-signal-first

confidence:
  0.87

status:
  confirmed
```

Future agents can retrieve anti-patterns before repeating failed behavior.

---

# 26. Tool Registry

Tools should be structured capabilities.

Suggested tool contract:

```yaml
id: crm.upsert_contact
version: 1

category: crm
mutating: true
external: false

permissions:
  - crm.write

risk: medium

approval:
  mode: policy

timeout_seconds: 30

idempotent: true

verification:
  type: database_state
  target: contacts
```

---

# 27. Tool Sentinel / Tool Inspection Pipeline

Every tool call must pass inspection.

Recommended inspectors:

```text
PermissionInspector
ScopeInspector
SecretInspector
EgressInspector
InjectionInspector
RepetitionInspector
RiskInspector
BudgetInspector
```

Possible verdicts:

```text
ALLOW
REQUIRE_APPROVAL
DENY
```

---

# 28. COSA Governance Kernel

The Governance Kernel must be independent from the LLM.

Responsibilities:

- Agent identity
- User identity
- Role/permission
- Workspace scope
- Tool policy
- Risk classification
- Approval requirement
- Egress control
- Secret isolation
- Rate limiting
- Audit
- Fail-closed policy for critical actions

Suggested policy:

```yaml
policy:
  id: email.send.default

match:
  action: email.send

rules:
  - external_action: true
  - allowed_source: crm_contacts
  - max_recipients_per_run: 20
  - approval_required: true
  - secret_access: broker_only
```

---

# 29. Founder/Admin Governance

Initial deployment is founder-only.

Recommended role model:

```text
owner/founder
admin
editor/contributor
viewer
service_account
```

Initially:

```text
Founder = owner + admin
```

Only Founder/Admin may edit:

- System Specs
- Agent Definitions
- Prompt Definitions
- Skill enable/disable
- Model policy
- Tool registry
- Workflow configuration
- Automation configuration
- Secrets
- Permissions
- Feature Flags

Backend must enforce this.

---

# 30. Prompt Registry

Prompts should not be scattered strings in source code.

Recommended structure:

```text
prompts/
  cosa/
    system.md
    routing.md
    planning.md

  sales/
    prospect.md
    qualify.md
    proposal.md

  marketing/
    research.md
    campaign.md
    landing_page.md

  finance/
    analyze.md

  legal/
    review.md
```

Each AI run records:

```text
agent_version
prompt_version
skill_version
model
provider
context_revision
tools
output
cost
latency
```

---

# 31. Prompt Lifecycle

```text
Production Prompt
      ↓
Candidate change
      ↓
Eval Suite
      ↓
Regression Compare
      ↓
Admin Review
      ↓
Promote / Reject
```

DSPy belongs here.

DSPy must never automatically promote a production prompt.

---

# 32. Skill Registry

Skill = reusable SOP/instructions/knowledge unit.

Do not load all skills into every system prompt.

Recommended skill metadata:

```yaml
id: hostinger.nextjs_deploy
version: 4
status: active

success_rate: 0.91
usage_count: 32

positive_feedback: 28
negative_feedback: 4

scope:
  - build
  - deployment
```

Skill lifecycle:

```text
candidate
→ evaluation
→ admin approval
→ active
→ review
→ deprecated
```

---

# 33. Skill Learning

After a Mission:

```text
Completed Mission
↓
Trajectory Analyzer
↓
Learning Candidate
↓
PII / Secret Scan
↓
Skill Candidate
↓
Evaluation
↓
Founder/Admin Approval
↓
Skill Registry
```

Do not auto-promote skills.

---

# 34. Mission Budget

Every Mission should have infrastructure-level limits.

Example:

```yaml
budget:
  max_steps: 60
  max_wall_time_seconds: 1200
  max_api_cost_usd: 0.30
  max_tokens: 120000
  max_tool_calls: 80
  max_parallel_workers: 3
  max_external_actions: 0
```

Exceeded budget → state:

```text
BUDGET_EXCEEDED
```

Do not trust the model to self-terminate.

---

# 35. Stuck Detector

COSA should detect:

```text
SAME_ACTION_LOOP
SAME_ERROR_LOOP
NO_PROGRESS_LOOP
TOOL_PING_PONG
APPROVAL_LOOP
AGENT_HANDOFF_LOOP
```

Suggested behavior:

```text
repeat 2 → observe
repeat 3 → warning + recovery instruction
repeat 5 → terminate run
```

Recovery may:

- change tool
- change specialist
- request user input
- reduce scope
- return partial result
- escalate

---

# 36. Event Architecture

Use a Command/Event pattern.

```text
Chat
Voice
Telegram
Zalo
Mobile
Hologram
   │
   ▼
COMMAND BUS
   │
   ▼
COSA Runtime
   │
   ▼
EVENT BUS
   │
   ├── Hub
   ├── Voice
   ├── Mobile
   ├── Notifications
   ├── Audit
   └── Automations
```

Recommended events:

```text
MISSION_CREATED
MISSION_STARTED
MISSION_PROGRESS
MISSION_WAITING_USER
MISSION_WAITING_APPROVAL
MISSION_COMPLETED
MISSION_FAILED

TOOL_REQUESTED
TOOL_APPROVED
TOOL_DENIED
TOOL_COMPLETED

VERIFICATION_STARTED
VERIFICATION_PASSED
VERIFICATION_FAILED

LEARNING_CANDIDATE_CREATED
```

---

# 37. Voice Architecture

Voice is a modality, not a separate agent.

Desktop:

```text
LiveKit local
```

Mobile:

```text
LiveKit Cloud
```

Voice and Chat must share:

- Session
- Intent
- Verb
- Memory
- Mission
- Agent routing
- Tool policy
- Event stream

Long work must run in background.

Example:

```text
Founder:
“Phân tích 20 đối thủ.”
```

COSA:

```text
MISSION_STARTED
run_id: ...
```

Voice remains available.

When worker finishes:

```text
MISSION_COMPLETED
```

COSA proactively reports completion.

---

# 38. Sandbox Manager

Build/Tech execution must not run unrestricted on the host.

Control:

```text
filesystem scope
network scope
environment scope
CPU
RAM
timeout
process
secret access
```

Recommended flow:

```text
Build Specialist
↓
Claude Code / Codex
↓
Sandbox
↓
Tests
↓
Diff
↓
Approval
↓
Commit / Deploy
```

OpenSandbox can be used as an implementation capability, not as a top-level product module.

---

# 39. Secret Broker

Agents should not see raw secrets.

Do not inject:

```text
RESEND_API_KEY=...
```

into model context.

Use:

```text
Agent
↓
email.send()
↓
Tool Gateway
↓
Secret Broker
↓
Resend
```

Agent sees only:

```yaml
credential:
  configured: true
```

---

# 40. MCP, n8n, API Boundaries

## MCP

MCP = tool protocol for service capability.

## n8n

n8n = Automation Runtime.

It is not the COSA brain.

Correct flow:

```text
Agent
↓
Action Request
↓
Governance
↓
AutomationProvider
↓
N8nAdapter
↓
n8n
↓
External System
```

## API

Direct APIs can be Tool Registry entries.

All paths still go through Governance.

---

# 41. Channel Adapter Pattern

Recommended:

```text
Incoming Event
↓
Verify
↓
Dedupe
↓
Normalize
↓
COSA Runtime
↓
Draft / Plan
↓
Policy
↓
Approval
↓
Outbox
↓
Channel Adapter
↓
Delivery Event
```

Priority:

1. Telegram
2. Email
3. Zalo
4. Public social channels

Zalo should not be the sole critical channel if relying on unofficial personal connectors.

---

# 42. Reality Verifier

This is mandatory for high-value actions.

Do not verify only by tool trace.

Examples:

## CRM

```text
crm.upsert
↓
verify PostgreSQL row
```

## Email

```text
email.send
↓
verify provider message/delivery ID
```

## Deployment

```text
deploy
↓
verify commit
↓
verify HTTP endpoint
```

## Finance

```text
journal draft/write
↓
verify ledger state
↓
verify accounting invariants
```

## Build

```text
code change
↓
tests
↓
build
↓
expected artifact state
```

---

# 43. Outcome Certificate

Recommended schema:

```yaml
outcome:
  mission_id: mis_123
  requested: create_customer

  execution:
    tool: crm.upsert_contact
    tool_result: success

  verification:
    source: postgres
    state: matched

  evidence:
    - contact_id: con_123

  verdict: VERIFIED
  confidence: high

  unresolved: []
```

Canonical verdicts:

```text
VERIFIED
PARTIAL
FAILED
UNKNOWN
```

Only Reality Verifier can assign VERIFIED.

---

# 44. Evidence Manager

Evidence must be first-class.

Suggested evidence record:

```yaml
id: ev_123
mission_id: mis_123

type: web_source | db_state | api_response | file | test | screenshot | human_approval

source:
  uri: ...

captured_at: ...

integrity:
  hash: ...

supports:
  - claim_001
```

---

# 45. Quality Gate

Quality should be a cross-cutting capability, not a visible Domain Agent.

Examples:

```text
Build → Code QA
Marketing → Campaign QA
Sales → Lead QA
Finance → Reconciliation QA
Legal → Document QA
```

A Mission may fail Quality Gate before Finish.

---

# 46. COSA Eval Lab

Admin-only.

Suggested location:

```text
Admin
→ AI Lab
→ Evaluations
```

Metrics:

```text
Intent accuracy
Verb routing accuracy
Domain routing accuracy
Specialist selection accuracy
Tool selection accuracy
Tool success
Hallucination rate
Evidence completeness
Mission completion rate
Cost
Latency
Loop rate
Approval correctness
Memory retrieval relevance
Prompt regression
```

---

# 47. Regression Evaluation

Any change to:

```text
model
prompt
skill
agent
workflow
tool
```

should support before/after evaluation.

Compare:

```text
tool calls
arguments
cost
latency
outcome
evidence
safety
```

Do not promote candidate versions that regress critical metrics.

---

# 48. Fault Injection Tests

COSA should deliberately test failures such as:

```text
tool returns success but DB unchanged
corrupted tool result
fake completion claim
stale context
silent no-op
altered handoff
missing evidence
approval bypass attempt
repeated loop
```

The system passes only if Governance/Verifier/Quality layers detect the fault.

---

# 49. Technology Radar

Do not turn every new GitHub project into a COSA feature.

Create Technology Radar:

```text
Runtime
Orchestration
Memory
Browser
Security
Governance
Evaluation
Coding
Communication
Research
```

Example:

```yaml
name: AgentSkeptic
category: verification
status: watch
maturity: experimental
potential: high
cosa_use: pattern
integration: no
last_reviewed: 2026-08-16
```

Recommended statuses:

```text
ADOPT
TRIAL
ASSESS
WATCH
REJECT
```

---

# 50. Feature Registry

Feature flags are mandatory.

Example:

```yaml
features:
  strategy:
    enabled: false

  sales_v2:
    enabled: true

  livekit_desktop:
    enabled: true

  livekit_mobile:
    enabled: true

  dspy_optimizer:
    enabled: false
```

Important distinction:

```text
FEATURE:
Does COSA have this capability enabled?

PERMISSION:
Can this user use it?

POLICY:
Can this action execute in this context?
```

---

# 51. Strategy Module

Current Strategy capability must remain **feature-flagged/disabled in the main v13 flow** until the core runtime is stable.

Do not delete its existing work.

Keep:

```text
Vision
Mission
3 Core Values
PESTEL
SWOT
TOWS
3 Strategic Goals
BSC
OKRs
12 Week Year
Week 13
```

but:

```yaml
strategy:
  enabled: false
```

It can be re-enabled after:

- Intent/Verb runtime stable
- Mission runtime stable
- Governance stable
- Evidence/Verification stable
- Founder UX simplified

---

# 52. Main Founder Navigation

Recommended visible navigation:

```text
Hub
COSA
Work
Company
Brain
Admin
```

## Company

```text
Overview
Sales
Marketing
Finance
Legal
Customers
Projects
```

## Admin

```text
Agents
Prompts
Skills
Workflows
Automations
Models
Tools
MCP
Channels
Secrets
Permissions
Audit
Features
AI Lab
System
```

---

# 53. Hologram Hub

Hologram Hub is a **CEO Command Center**, not an app launcher.

It should answer:

```text
What matters?
What needs me?
What is COSA doing?
How is the company doing?
What should I do next?
```

Recommended top cards:

```text
Today / Top 3
Approvals
Active Missions
Company Pulse
Waiting for You
Ask COSA
```

---

# 54. Mission Card UX

Default:

```text
Find 30 Prospects
███████░░ 72%

Sales
Running

12 qualified
```

Expanded Inspector:

```text
Verb
INVESTIGATE

Specialist
Outbound Strategist

Context
52%

Budget
$0.12 / $0.30

Steps
18 / 60

Tools
24

Workers
2 / 3

Loop Health
Healthy

Risk
Low

Evidence
17 sources

Verification
Pending
```

Technical runtime details should only appear in expanded Inspector.

---

# 55. Company Pulse

Suggested founder-level metrics:

```text
Sales
Pipeline
Qualified opportunities
Next actions

Cash
Cash balance
Runway
Receivables
Payables

Marketing
Active campaigns
Leads
Conversion

Operations
Open missions
Blocked work
Approvals

Legal
Upcoming obligations
Open risks
```

---

# 56. Revenue Engine — First End-to-End Vertical

The first business vertical should be:

```text
Market Research
↓
ICP
↓
Buying Signals
↓
Prospect Discovery
↓
Enrichment
↓
Qualification
↓
CRM
↓
Outreach Draft
↓
Approval
↓
Send
↓
Follow-up
↓
Opportunity
↓
Revenue
```

This proves the full COSA architecture.

---

# 57. Sales Agent

Core capabilities:

```text
prospect search
company research
contact enrichment
buying-signal analysis
lead qualification
deal scoring
outreach strategy
email/Zalo/Telegram drafting
follow-up planning
pipeline analysis
proposal drafting
conversion monitoring
```

CRM core entities:

```text
Company
Contact
Signal
Lead
Opportunity
Interaction
Sequence
Deal
Proposal
Customer
Activity
```

Important fields:

```text
signal_type
signal_date
signal_strength
icp_fit
deal_score
next_action
last_touch
next_touch
```

---

# 58. Marketing Closed Loop

```text
Market Research
↓
ICP
↓
Campaign
↓
Content
↓
Landing Page
↓
Form
↓
Lead
↓
CRM
↓
Qualification
↓
Sales
↓
Result
↓
Attribution
↓
Marketing Learning
```

Landing page generator should remain module-based:

```text
Hero
Features
Benefits
SocialProof
Pricing
FAQ
CTA
LeadForm
Footer
```

Reusable across subdomains/projects.

---

# 59. Finance Agent

## Finance Lite

Founder daily view:

```text
cash
revenue
expenses
receivables
payables
runway
burn
profit estimate
```

## Full accounting layer

Keep accounting support aligned with Vietnamese legal/accounting requirements, including TT58-related implementation already designed.

AI may:

- analyze
- classify
- draft
- explain
- detect anomalies

AI must not autonomously:

- approve accounting
- submit legal filings
- finalize high-risk entries
- spend money

---

# 60. Legal Agent

MVP:

```text
Company legal profile
Contract repository
Compliance calendar
Legal checklist
Document analysis
Risk detection
Legal research
Draft documents
```

Flow:

```text
Document
↓
Extract
↓
Classify
↓
Check requirements
↓
Identify risks
↓
Draft recommendation
↓
Founder review
```

---

# 61. Build/Tech Agent

Flow:

```text
Founder request
↓
Intent
↓
Verb
↓
Build Specialist
↓
Repo Context
↓
Plan
↓
Claude Code / Codex
↓
Sandbox
↓
Tests
↓
Evidence
↓
Reality Verify
↓
Founder Approval
↓
Commit / Deploy
```

Use OpenSpec only for sufficiently large feature/architecture changes.

Do not create a full spec for trivial edits.

---

# 62. OpenSpec Decision Policy

## Small change

Examples:

```text
fix typo
change button color
small bug
```

→ direct execution.

## Feature

Example:

```text
add CRM pipeline
```

→ SHAPE → Spec → Approval → EXECUTE.

## Architecture

Example:

```text
redesign Sales Engine
```

→ SHAPE → OpenSpec → Review → Implementation.

---

# 63. Browser Capability

Preferred hierarchy:

```text
API
↓
Structured HTTP
↓
DOM
↓
Accessibility Tree
↓
Screenshot / Vision
```

Principle:

```text
API FIRST
DOM SECOND
VISION LAST
```

Use vision for:

- charts
- canvas
- images
- layout/design review
- cases impossible to parse structurally

---

# 64. Extract Capability

Create shared:

```text
information.extract
```

Works with:

```text
Web
PDF
Email
Contract
Invoice
CRM
Research data
```

The main agent should receive concise structured results, not huge raw content whenever possible.

---

# 65. Provider Router

Model choice belongs in Provider Router.

Do not expose model selection in normal founder UX.

Suggested modes:

```text
interactive_personal
background_api
local_embedding
```

Examples:

```text
interactive_personal
→ Claude Code / Codex CLI where appropriate

background_api
→ DeepSeek / OpenAI / other API providers

local_embedding
→ local model
```

Do not automatically consume subscription-based interactive tools as background API fallbacks.

---

# 66. n8n Positioning

n8n is not the brain.

Correct positioning:

```text
COSA Agent Runtime
↓
Action Request
↓
Governance
↓
AutomationProvider
↓
N8nAdapter
↓
n8n
```

n8n handles:

- integration
- scheduling
- external workflow
- message sending
- webhook
- SaaS automation

COSA owns:

- intent
- mission
- agent reasoning
- policy
- approval
- outcome
- learning

---

# 67. Suggested PostgreSQL Data Model

Core tables:

```text
users
workspaces
roles
permissions

missions
mission_steps
mission_events
mission_handoffs
mission_artifacts
mission_evidence
mission_verifications
mission_outcomes
mission_budgets

tasks
task_dependencies

agents
agent_versions
specialists
specialist_versions

prompts
prompt_versions
skills
skill_versions

tools
tool_versions
tool_policies

approvals
outbox
audit_events

memory_items
memory_sources
memory_revisions

feature_flags

companies
contacts
signals
leads
opportunities
interactions
deals
customers
campaigns

provider_configs
runtime_runs
runtime_metrics
```

---

# 68. Suggested Runtime API Surface

Examples:

```text
POST /v1/companion/messages

POST /v1/missions
GET  /v1/missions/{id}
POST /v1/missions/{id}/cancel
POST /v1/missions/{id}/resume

GET  /v1/missions/{id}/events

POST /v1/approvals/{id}/approve
POST /v1/approvals/{id}/deny

GET  /v1/outcomes/{mission_id}

GET  /v1/hub/brief

GET  /v1/admin/agents
GET  /v1/admin/prompts
GET  /v1/admin/skills
GET  /v1/admin/tools
GET  /v1/admin/features

POST /v1/admin/evals/run
GET  /v1/admin/evals/{id}
```

---

# 69. Suggested Folder Structure

```text
backend/
  app/
    companion/
    routing/
      intent/
      verbs/
      domains/
      specialists/

    missions/
    tasks/

    runtime/
      kernel/
      middleware/
      context/
      events/
      budget/
      stuck/
      evidence/
      verification/
      providers/

    governance/
      identity/
      permissions/
      policies/
      approvals/
      secrets/
      audit/

    brain/
      memory/
      knowledge/
      learning/
      retrieval/

    tools/
      registry/
      adapters/
      mcp/
      n8n/

    domains/
      sales/
      marketing/
      finance/
      legal/
      build/

    evals/
    features/
```

---

# 70. Migration From Current COSA

Do not rewrite the whole application.

Migration strategy:

## Step 1 — Freeze surface-area growth

Stop adding new founder-facing modules temporarily.

## Step 2 — Inventory existing capabilities

Map existing:

```text
screen
agent
prompt
skill
workflow
tool
automation
```

to the new architecture.

## Step 3 — Classify each feature

For every existing function decide:

```text
Founder Surface
Domain Capability
Runtime Capability
Admin/Infrastructure
Deprecated
Feature-Flagged
```

## Step 4 — Build core routing

Implement:

```text
Conversation Guard
Intent Router
Verb Router
Domain Router
Specialist Router
```

## Step 5 — Mission Runtime

Implement Mission, Task, Run, Event, Budget, State.

## Step 6 — Governance

Implement Tool Sentinel, Policy, Approval, Secret Broker, Audit.

## Step 7 — Verification

Implement Evidence Manager, Reality Verifier, Outcome Certificate.

## Step 8 — Reconnect domains

Start with Sales + CRM + Marketing.

---

# 71. Mandatory Acceptance Tests

## Conversation

```text
Input: "chào"
Expected:
CONVERSE
no tool
no mission
```

## Founder Brief

```text
Input: "COSA hôm nay có gì?"
Expected:
Founder Brief capability
```

## Project

```text
Input: "project mID thế nào?"
Expected:
project.read
no unrelated tool
```

## Sales

```text
Input: "tìm 20 khách hàng cho sản phẩm X"
Expected:
Sales Mission
INVESTIGATE
background run
```

## External action

```text
Input: "gửi email cho 20 khách hàng này"
Expected:
Draft
Governance
Approval required
Outbox
Send only after approval
```

## Verification

```text
Tool result says CRM write success
DB row missing
Expected:
Outcome = FAILED/UNKNOWN
never VERIFIED
```

---

# 72. P0 Implementation Plan

P0 is the critical runtime foundation.

Build:

```text
Conversation Guard
Intent Router
Verb Router
Domain Router
Specialist Router

Mission
Task
Run State
Event Bus
Mission Ledger

Prompt Registry
Agent Registry
Tool Registry

Context Cascade
Context Pool Budget

Mission Budget
Stuck Detector

Governance Gate
Approval
Audit
Secret Broker

Evidence Manager
Reality Verifier
Outcome Certificate
```

Do not add new major business modules before P0 is stable.

---

# 73. P1 — Founder Command Center

Build:

```text
Hologram Hub
Daily Brief
Top 3
Active Missions
Approvals
Company Pulse
Waiting for You
Notifications
Mission Inspector
```

Fix all chat routing issues.

---

# 74. P2 — Revenue Engine

Implement full vertical:

```text
Market Research
→ ICP
→ Prospect
→ Buying Signal
→ Enrichment
→ Qualification
→ CRM
→ Outreach Draft
→ Approval
→ Send
→ Follow-up
→ Opportunity
→ Revenue
```

This becomes the first business proof of the architecture.

---

# 75. P3 — Automation & Channels

Integrate:

```text
n8n
Telegram
Email
Zalo
Resend
Social
Webhooks
```

All external actions:

```text
Tool Registry
→ Governance
→ Approval
→ Outbox
→ Adapter
```

---

# 76. P4 — Company Operations

Add or reconnect:

```text
Finance Lite
Full Finance/TT58
Legal
Landing Page
Build Agent
Customer operations
```

---

# 77. P5 — Intelligence & Self-Improvement

Only after core runtime is stable:

```text
DSPy
Prompt optimization
Agent eval
Skill learning
Pattern discovery
Anti-pattern learning
Mission template generation
Regression diff
Fault injection
Technology Radar
```

---

# 78. Anti-Patterns COSA Must Avoid

Do not:

1. Create one Agent per function.
2. Show all technical modules to founder.
3. Use n8n as the brain.
4. Let LLM call arbitrary tools directly.
5. Let prompts enforce security.
6. Trust tool trace as proof of success.
7. Store all chat as long-term memory.
8. Put all skills into system prompt.
9. Let workers spawn unlimited sub-workers.
10. Depend on one external agent framework for the core loop.
11. Build a god file for runtime.
12. Add cost tracking without hard budgets.
13. Allow indefinite waiting states.
14. Let any external action bypass approval policy.
15. Auto-promote prompts or skills.
16. Automatically rewrite approved business data from AI inference.
17. Expose secrets to models.
18. Use screenshot/vision when structured API/DOM is available.
19. Re-enable Strategy before core runtime is stable.
20. Add another dashboard card when the function belongs in Admin/Inspector.

---

# 79. Architectural Invariants

These should be implemented as automated tests where possible.

```text
NO INTENT = NO TOOL

NO EXTERNAL ACTION WITHOUT GOVERNANCE

NO HIGH-RISK ACTION WITHOUT POLICY

NO APPROVAL WAIT WITHOUT TIMEOUT

NO VERIFIED STATUS WITHOUT REALITY CHECK

NO SECRET IN MODEL CONTEXT

NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS

NO UNBOUNDED WORKER SPAWNING

NO UNBOUNDED COST

NO HIDDEN STATE TRANSITION

NO FINISH WITHOUT EVIDENCE WHEN EVIDENCE IS REQUIRED
```

---

# 80. Final Architecture Decision

COSA should become a **Harness-first Founder OS**.

The founder experiences:

```text
Ask
→ COSA understands
→ COSA organizes
→ COSA works
→ COSA asks only when necessary
→ COSA proves the result
→ COSA learns
```

The technical runtime performs:

```text
DECIDE
→ DELEGATE
→ EXECUTE
→ GOVERN
→ VERIFY
→ LEARN
```

Conceptual mapping:

```text
MyIris
→ Decide

Agency Agents
→ Delegate

Awesome AI Anatomy
→ Execute Safely

Awesome AI Agents
→ Govern + Verify + Evaluate + Technology Radar
```

COSA should sit above these patterns and own its runtime.

---

# 81. Definition of Done for the Consolidation Phase

The consolidation phase is complete when:

- “chào” never invokes a tool.
- Every actionable request has Intent + Verb.
- Every Mission has state, budget, events, and ownership.
- Every tool call passes Governance.
- Every external write has correct policy/approval.
- Every high-value action can be reality-verified.
- Hub shows business outcomes, not technical clutter.
- Sales vertical runs end-to-end.
- Prompts/skills/agents are versioned and testable.
- Strategy remains safely feature-flagged until intentionally re-enabled.
- Founder can operate COSA primarily through Chat/Voice without choosing agents/tools/models manually.

---

# 82. Recommended Immediate Implementation Order for Claude Code

```text
01. Audit current routes and tool calls
02. Fix greeting/tool accidental routing
03. Implement Conversation Guard
04. Implement Intent Router
05. Implement Verb Router
06. Implement Domain/Specialist Router
07. Add Mission + Mission Ledger
08. Add Event Bus
09. Add Budget + Stuck Detector
10. Add Tool Registry
11. Add Governance Kernel
12. Add Approval + Outbox
13. Add Secret Broker
14. Add Evidence Manager
15. Add Reality Verifier
16. Add Outcome Certificate
17. Refactor Hologram Hub
18. Build Sales end-to-end vertical
19. Add Eval Lab
20. Add self-improvement only after regression tests are stable
```

---

## Appendix A — Example Full Routing Trace

```yaml
message:
  "Tìm cho tôi 20 khách sạn tại Vũng Tàu có khả năng cần giải pháp AI."

conversation_guard:
  actionable: true

intent:
  id: sales.prospect_search
  confidence: 0.96

verb:
  id: INVESTIGATE

domain:
  id: sales

specialist:
  id: sales.outbound

mission:
  id: mis_abc
  type: MISSION

budget:
  max_cost_usd: 0.30
  max_duration_minutes: 20

capabilities:
  - market_search
  - company_research
  - buying_signal_analysis
  - lead_qualification

tools:
  - web.search
  - browser.extract
  - crm.read

governance:
  external_action: false
  approval_required: false

finish:
  require_evidence: true
  require_verified_company_records: true
```

---

## Appendix B — Example External Action

```yaml
request:
  "Gửi email cho 10 khách hàng đã duyệt."

intent: sales.outreach_send
verb: EXECUTE
domain: sales

action:
  tool: email.send
  recipients: 10

governance:
  permission: allow
  scope: crm_approved_contacts
  risk: medium
  approval_required: true

state:
  WAITING_APPROVAL
```

After Founder approves:

```text
Outbox
→ Secret Broker
→ Resend
→ Provider Message IDs
→ Reality Verifier
→ VERIFIED / PARTIAL / FAILED
```

---

## Appendix C — Example Outcome Certificate

```json
{
  "mission_id": "mis_123",
  "requested": "send_approved_outreach",
  "execution": {
    "tool": "email.send",
    "requested_count": 10,
    "tool_result": "success"
  },
  "verification": {
    "provider_receipts": 10,
    "failed": 0
  },
  "verdict": "VERIFIED",
  "evidence_count": 10,
  "unresolved": []
}
```

---

## Appendix D — Recommended Founder UX Rule

The founder should see:

```text
Goal
Mission
Progress
Approvals
Outcome
Next Action
```

The founder should not normally see:

```text
prompt_id
model_id
MCP server
n8n workflow ID
tool schema
vector index
sandbox implementation
middleware chain
DSPy config
```

These belong in Inspector/Admin.

---

**End of specification.**
