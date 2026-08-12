# mCOSA V12.3 — Consolidated Project, Portfolio, Realtime & Agent Memory Operating System
## Master Implementation Specification for Claude Code

**Product:** mCOSA — *my Company One System AI*  
**Baseline:** V10 Hybrid Workforce already implemented  
**Purpose of this file:** Single implementation source combining V12 Project/Portfolio OS, V12.2 Hybrid LiveKit Local/Cloud realtime architecture, and V12.3 Hierarchical Agent Memory integration.  
**Upgrade principle:** Additive only; preserve the V10 execution runtime and System-of-Record boundaries.

---

# Document Structure

- **Part A:** V12 Project & Portfolio Operating System
- **Part B:** V12.2 LiveKit Local + Cloud Realtime Architecture
- **Part C:** V12.3 Hierarchical Agent Memory & Context Offload

Key provider roles:

```text
DeepSeek     → routine chat / routing
ChatGPT Terra → strategic analysis
Claude Code  → coding / developer execution
LiveKit      → realtime interaction transport
Gemini Live  → optional/default natural realtime voice model
TencentDB Agent Memory → local hierarchical Agent Memory sidecar
PostgreSQL   → authoritative structured company state
mCOSA Knowledge Engine → governed company knowledge
```

---

# Part A — V12 Project & Portfolio Operating System
## Implementation Specification for the Existing V10 Codebase

**Product:** mCOSA — *my Company One System AI*  
**Baseline:** V10 Hybrid Workforce already implemented  
**Upgrade strategy:** Additive migration; do not rebuild V10  
**Frontend:** Flutter + GetX  
**Backend:** Python FastAPI  
**Database:** PostgreSQL  
**Desktop execution:** Local AI Worker Runtime  
**Coding:** Claude Code CLI  
**Strategic analysis profile:** ChatGPT Terra  
**Daily chat profile:** DeepSeek  
**Knowledge:** Local-first Markdown/TXT + PostgreSQL structured state + optional object-storage replica  

---

# 1. V12 objective

V10 already provides Organization, Hybrid Workforce, Human + AI members, Outcomes, WorkItems, Agents, Workers, Tools/MCP, Approval, Artifact, Evaluation, Desktop Execution Node, Mobile Remote Client, Hologram Hub, Knowledge Engine and Claude Code Worker.

V12 does **not** replace that architecture. It adds the operating layer that answers:

> **What should the founder work on, in what order, across one or many projects, for the next 12 weeks?**

V12 adds:

1. Project Intelligence.
2. AI Methodology Router.
3. Evidence-backed strategic analysis.
4. Project 12 Week Year.
5. Stage / Milestone / Gate.
6. Weekly Mission.
7. Next Best Action.
8. Portfolio Intelligence for multiple concurrent projects.
9. Founder Attention and capacity allocation.
10. Week 13 Review / Learn / Celebrate / Reset.
11. Model routing: Terra / DeepSeek / Claude Code.
12. Additive migration from the already-running V10.

---

# 2. Core OPC operating loop

```text
Founder
   ↓
Create Project
   ↓
Name + Description
   ↓
Project Classifier
   ↓
Methodology Router
   ↓
Research + Company Knowledge
   ↓
Strategic Analysis
   ↓
CEO Review
   ↓
Goals / OKRs
   ↓
12 Week Year
   ↓
Stages / Milestones / Gates
   ↓
Weekly Missions
   ↓
Next Best Actions
   ↓
Hybrid Workforce V10
   ↓
Artifacts / Evidence
   ↓
Weekly Reviews
   ↓
Week 13
   ↓
Reflect / Learn / Celebrate / Reset
   ↓
Next Cycle
```

For multi-project OPC:

```text
Company Strategy
      ↓
Portfolio Strategy
      ↓
Shared PESTEL
      ↓
Project Impact Matrix
      ↓
Project SWOTs + Portfolio SWOT
      ↓
Project TOWS + Portfolio TOWS
      ↓
3 Portfolio Options
      ↓
CEO Decision
      ↓
Company / Portfolio OKRs
      ↓
Project OKRs
      ↓
Founder Attention + Capacity Allocation
      ↓
Portfolio 12WY
      ↓
Project Journeys
      ↓
Weekly Company Mission
      ↓
Next Best Actions
```

---

# 3. Founder attention is the scarce resource

For a one-person company the primary bottleneck is not agent count. It is founder attention.

mCOSA should optimize for:

```text
Accepted Business Outcomes
──────────────────────────
Founder Attention Consumed
```

Founder responsibility:

- Direction.
- Strategic decisions.
- Human interactions that genuinely require the founder.
- Consequential approvals.
- Exceptions.

AI/automation/tools/external experts should perform the rest where appropriate.

---

# 4. Project as an operating unit

Suggested Project fields:

```yaml
project:
  id:
  organization_id:
  portfolio_id: optional
  name:
  description:
  type:
  status:
  strategic_priority:
  company_goal_links: []
  owner_member_id:
  current_cycle_id: optional
  knowledge_scope_id:
  budget_id:
  founder_attention_budget:
```

Recommended project types:

```text
STRATEGIC
NEW_BUSINESS
PRODUCT
GROWTH
OPERATIONAL
TECHNICAL
EXPERIMENT
COMPLIANCE
```

Statuses:

```text
IDEA
ANALYSIS
ACTIVE
ACCELERATE
MAINTAIN
MONITOR
HOLD
STOP
COMPLETED
ARCHIVED
```

---

# 5. Do not force every project through full PESTEL/SWOT/TOWS

Frameworks must be selected by the problem.

| Project | Recommended planning |
| --- | --- |
| New business | Full strategic analysis + 12WY |
| New market | PESTEL + SWOT/TOWS + OKR + 12WY |
| Product launch | Market analysis + SWOT/TOWS + launch playbook |
| New product | Discovery/validation + strategy + 12WY |
| Feature | Outcome + milestone + technical workflow |
| Bug | Technical workflow |
| Marketing campaign | Campaign playbook |
| Experiment | Hypothesis → test → evidence → gate |
| Compliance | Checklist + evidence + expert escalation |

---

# 6. Project Classifier

After name + description, classify:

```yaml
classification:
  project_type:
  strategic_depth:
  uncertainty_level:
  risk_level:
  research_required:
  external_evidence_required:
  internal_context_required:
  recommended_methodologies:
  human_required_areas:
```

Use a fast structured model by default. Escalate to strategic analysis only when uncertainty matters.

---

# 7. AI Methodology Router

Supported methodology primitives:

```text
Vision / Mission / Core Values
PESTEL
SWOT
TOWS
BSC
OKR
12 Week Year
PDCA
Lean Validation
Experiment
Stage-Gate
Playbook
SOP
Risk Analysis
Portfolio Analysis
```

Example:

```text
Project: Launch mCOSA beta
→ Product Launch
→ External scan
→ SWOT/TOWS
→ Goals
→ OKRs
→ 12WY
→ Launch Playbook
→ Milestones/Gates
```

Technical bug:

```text
→ TECHNICAL
→ No PESTEL
→ No SWOT
→ Claude Code Worker
→ Tests
→ Artifact
```

---

# 8. Evidence model

Every strategic item should classify its origin:

```text
FACT
FOUNDER_INPUT
COMPANY_DATA
AI_INFERENCE
AI_HYPOTHESIS
UNKNOWN
```

Evidence metadata:

```yaml
evidence:
  source_type:
  source_ref:
  captured_at:
  last_verified_at:
  confidence:
  project_scope:
```

AI must never silently convert a hypothesis into a fact.

---

# 9. Strategic Canvas 1–1–3

For OPC simplicity:

```text
1 Vision
1 Mission
3 Core Values
```

PESTEL:

```text
6 categories × top 3 signals
```

SWOT:

```text
4 quadrants × top 3 factors
```

TOWS:

```text
SO/ST/WO/WT × top 3 strategies
```

Then generate only:

```text
3 Strategic Options
3 Recommended Goals
```

CEO approves, edits, rejects or asks why.

---

# 10. Strategy traceability

Every strategic recommendation should trace:

```text
Evidence
   ↓
PESTEL Signal
   ↓
SWOT Factor
   ↓
TOWS Strategy
   ↓
Strategic Option
   ↓
Goal
   ↓
Objective
   ↓
KR
   ↓
12WY Stage
   ↓
Weekly Mission
   ↓
WorkItem
   ↓
Artifact / Result
```

Generic link:

```yaml
strategy_link:
  source_type:
  source_id:
  relation:
  target_type:
  target_id:
  rationale:
```

---

# 11. CEO review wizard

Before activation:

```text
1 Project Context
2 Assumptions / Unknowns
3 PESTEL
4 SWOT
5 TOWS
6 3 Strategic Options
7 3 Goals
8 OKRs
9 12 Week Year
10 Workforce / Execution Strategy
11 Cycle Contract
12 Activate
```

Each step supports:

```text
Approve
Edit
Ask Why
Regenerate
Mark Unknown
Request Research
```

No committed WorkItems are created before activation.

---

# 12. Cycle Contract

Before activation ask:

> **Is this what success looks like after 12 weeks?**

Example:

```text
MVP production ready
10 beta users
5 paying customers
Revenue target X
Founder workload ≤ Y hours/week
Critical legal assumptions resolved
```

Suggested fields:

```yaml
cycle_contract:
  cycle_id:
  success_definition:
  goal_ids: []
  kr_ids: []
  founder_capacity_per_week:
  reserved_buffer_percent:
  ai_budget:
  operating_budget:
  risk_constraints:
  approved_by:
```

---

# 13. 12 Week Year is stage-based, not task division

Example:

```text
Weeks 1–2    DISCOVERY
Weeks 3–4    VALIDATION
Weeks 5–7    MVP
Weeks 8–9    BETA
Weeks 10–11  ACQUISITION
Week 12      CLOSING / RESULT
Week 13      REVIEW / LEARN / CELEBRATE / RESET
```

Stages vary by project type.

---

# 14. Stage, Milestone and Gate

Stage:

```yaml
cycle_stage:
  cycle_id:
  name:
  purpose:
  start_week:
  end_week:
  expected_outcomes: []
  milestone_ids: []
  gate_id:
```

Milestone:

```yaml
milestone:
  project_id:
  cycle_id:
  stage_id:
  name:
  due_week:
  required_artifacts: []
  required_metrics: []
  required_evidence: []
  acceptance_criteria:
```

Gate:

```text
GO
ITERATE
HOLD
STOP
PIVOT
```

Gate decisions preserve evidence and authorized human decision.

---

# 15. Weekly Mission

The primary weekly interface is one clear mission.

```text
WEEK 3

MISSION
Validate the core problem.

SUCCESS
- 10 customer interviews.
- 3 assumptions tested.
- Evidence threshold reached.

FOUNDER WORK
- Conduct 2 key interviews.
- Approve interview framework.

AI WORK
- Recruit candidates.
- Prepare briefs.
- Analyze transcripts.
- Update evidence.
```

Suggested entity:

```yaml
weekly_mission:
  cycle_id:
  project_id:
  week_number:
  mission:
  success_criteria:
  founder_commitments:
  ai_commitments:
  automation_commitments:
  milestone_id:
```

---

# 16. Weekly scoring

Use at least:

**Execution Score**

```text
Completed committed actions / Planned committed actions
```

**Outcome Score**

Evidence-based movement toward milestone/KR.

Example:

```text
Execution 92%
Outcome   63%
```

This detects “all tasks completed, wrong outcome.”

---

# 17. Weekly Review

Generate:

```text
Planned
Actual
Execution Score
Outcome Score
KR Progress
Evidence Learned
Assumptions Confirmed
Assumptions Invalidated
Risks
Blockers
Founder Attention Used
AI/Tool Cost
Recommendation
```

Recommendations:

```text
KEEP PLAN
REPLAN
REDUCE SCOPE
INCREASE VALIDATION
SHIFT CAPACITY
HOLD
ESCALATE
```

---

# 18. Week 13 — Reflect • Learn • Celebrate • Reset

Week 13 is not a normal execution week.

## Reflect

```text
Goals vs actual
KR achievement
Milestones
Founder attention
Budget
Cycle results
```

## Learn

```text
What worked?
What failed?
Which assumptions were false?
What should stop?
What should continue?
```

## Improve

Candidates:

```text
Knowledge
Playbooks
SOPs
Skills
Agents
Model routing
Automation
Policy
Strategy
Organization
```

## Celebrate

Example:

```text
12 WEEK CYCLE COMPLETE

2 major goals achieved
MVP launched
5 paying customers
47 outcomes completed
3 workflows automated

Founder highlight:
...

Most important lesson:
...
```

Store as Company Memory.

---

# 19. Week 13 is also the next-cycle gate

```text
Week 13
   ↓
Project Review
   ↓
Strategy Still Valid?
   ├─ Yes → Adjust and create next cycle
   └─ No  → Refresh relevant strategic analysis
```

Do not automatically copy the previous cycle.

---

# 20. Multi-project OPC requires Portfolio Intelligence

Do not create three independent plans each consuming 100% founder capacity.

Add:

```text
Company Strategy
      ↓
Portfolio Strategy
      ↓
Projects
      ↓
Execution
```

---

# 21. Portfolio entity

```yaml
portfolio:
  id:
  organization_id:
  name:
  purpose:
  owner_member_id:
  current_cycle_id:
  founder_capacity_per_week:
  reserved_buffer_percent:
```

Bridge:

```yaml
portfolio_project:
  portfolio_id:
  project_id:
  portfolio_status:
  strategic_priority:
  capacity_allocation:
  founder_attention_allocation:
```

Portfolio is optional for one simple project.

---

# 22. Portfolio Detector

Trigger when:

```text
2+ strategic projects active
or founder capacity conflict
or cross-project dependency
or CEO explicitly asks for portfolio analysis
```

Suggested UX:

> You have 3 strategic projects. I recommend Portfolio Analysis before committing the next 12-week cycle.

---

# 23. Shared PESTEL

Do external research once.

```text
Shared External Research
      ↓
Portfolio PESTEL
      ↓
Project Impact Lens A
Project Impact Lens B
Project Impact Lens C
```

Project impact:

```yaml
project_pestel_impact:
  signal_id:
  project_id:
  impact_direction:
  impact_strength:
  timeframe:
  rationale:
```

---

# 24. Project Impact Matrix

Example:

| Signal | mCOSA | mVault | VT Signal |
| --- | ---: | ---: | ---: |
| AI-agent adoption | +++ | + | ++ |
| Regulatory change | ++ | +++ risk | + |
| SME AI demand | +++ | + | ++ |
| Blockchain sentiment | 0 | ++ | 0 |

Shared evidence, project-specific interpretation.

---

# 25. Project SWOT + Portfolio SWOT

Project SWOT remains separate.

Portfolio SWOT analyzes combined reality.

Examples:

**Strengths**
- Shared AI infrastructure.
- Shared knowledge.
- Shared founder expertise.

**Weaknesses**
- One founder.
- Limited capital.
- Three concurrent products.

**Opportunities**
- Reusable platform components.
- Shared distribution.
- Cross-selling.

**Threats**
- Founder overload.
- Context switching.
- Fragmented focus.

---

# 26. Portfolio TOWS

Portfolio TOWS answers:

> **How should the projects coexist?**

Examples:

```text
SO: Use mCOSA internally to operate other projects.
ST: Centralize governance/security.
WO: Sequence launches instead of concurrent launches.
WT: Hold/stop low-evidence project.
```

---

# 27. Synergy and dependency

Analyze:

```text
Shared code
Shared infrastructure
Shared knowledge
Shared customer segment
Shared distribution
Shared legal/compliance
Shared agents/skills
Shared data
Dependencies
Cannibalization
Conflict
```

Dependency example:

```text
Shared mCOSA Knowledge Engine
        ↓
VT Signal research runtime
```

Work that unblocks multiple projects receives higher Next Best Action priority.

---

# 28. Portfolio priority

Inputs:

```text
Strategic alignment
Evidence strength
Market opportunity
Revenue potential
Time-to-value
Founder fit
Capital requirement
Risk
Dependencies
Synergy
Opportunity cost
Founder attention
```

Output is recommendation, not truth.

Use Rule of 3 for allocation options.

Example:

```text
Option A — Focus
mCOSA 70%
mVault 30%
VT Signal HOLD

Option B — Balanced
mCOSA 50%
mVault 30%
VT Signal 20%

Option C — Platform-first
Build shared mCOSA capabilities first.
```

---

# 29. OKR cascade

Preferred:

```text
Company Goals
    ↓
Company / Portfolio OKRs
    ↓
Project Contribution
    ↓
Project OKRs
```

A Project KR that does not map upward must be classified and justified:

```text
OPERATIONAL
COMPLIANCE
EXPLORATION
MANDATORY
```

---

# 30. Founder Attention and capacity allocation

Example:

```text
Founder available 40h/week
Reserve buffer 20%
Allocatable 32h/week
```

Allocation:

```text
mCOSA     50%
mVault    30%
VT Signal 20%
```

Track founder attention separately from AI/tool budget.

---

# 31. OPC WIP limits

Suggested configurable limits:

```text
max_active_strategic_projects
max_founder_critical_tasks_per_day
max_active_founder_milestones
min_buffer_percent
```

Example:

```text
Active strategic projects ≤ 2
Founder critical tasks/day ≤ 3
Reserved capacity buffer ≥ 20%
```

Third project can be MONITOR/HOLD/AUTOMATED.

---

# 32. Portfolio sequencing

Do not let all projects enter peak phases at once.

Example:

```text
W1–W4
mCOSA MVP
mVault Research
VT Signal Monitor

W5–W7
mCOSA Beta
mVault Prototype
VT Signal Automated Research

W8–W10
mCOSA Acquisition
mVault Validation
VT Signal Experiment

W11–W12
Portfolio Closing
```

---

# 33. 12 Week Portfolio Contract

Before activation show:

```text
ACCELERATE: mCOSA
VALIDATE:   mVault
MONITOR:    VT Signal
```

Also show:

```text
Founder hours/week
Buffer
AI/tool budget
External expert budget
Expected CEO decisions/week
Highest risks
```

CEO activates the portfolio cycle.

---

# 34. Weekly Company Mission

Example:

```text
WEEK 4

COMPANY MISSION
Validate market demand while completing mCOSA MVP.

mCOSA
Milestone: MVP feature complete
Founder: 2 decisions
AI: 14 tasks

mVault
Milestone: Legal feasibility
Founder: 1 expert interview
AI: Research

VT Signal
MONITOR
AI: Weekly report only
```

---

# 35. Portfolio Weekly Review

Example:

```text
mCOSA
Execution 91%
Outcome   82%
ON TRACK

mVault
Execution 75%
Outcome   54%
ATTENTION

VT Signal
MONITOR

PORTFOLIO
Founder capacity used: 88%
Strategic progress: 74%
New risk: mVault legal

Recommendation:
Shift 10% capacity to mCOSA next week.
```

---

# 36. Week 13 Portfolio Review

Review each Project plus the Portfolio.

Questions:

```text
Which project created most value?
Which consumed most founder attention?
Which has strongest evidence?
Which should accelerate?
Which should maintain?
Which should monitor?
Which should stop?
What synergy appeared?
What dependency changed?
```

Then recommend next-cycle allocation.

---

# 37. Next Best Action Engine

Inputs:

```text
Company Strategy
Portfolio Priority
Project Stage
Milestones
Dependencies
Deadlines
Risks
Founder Availability
Founder Profile
Evidence Gaps
KR Impact
Dependency Unlock
Required Human Authority
Current AI Work
```

Initial scoring:

```text
Strategic Impact
× Urgency
× Evidence Value
× Dependency Unlock
× Risk Reduction
÷ Founder Effort
```

Implement transparent weighted rules first, then AI reranking.

Output:

```text
TOP 3 NEXT ACTIONS
```

---

# 38. Human-required work

Add:

```text
human_required: true|false
```

Typical human-required:

```text
Founder vision
Strategic choice
Customer interview
Investor pitch
Key partnership
High-value sales
Legal/financial authority
Exception outside policy
```

AI may prepare, analyze and follow up.

---

# 39. Founder Operating Profile

Suggested inputs:

```text
Domain expertise
Technical capability
Marketing capability
Sales capability
Finance capability
Available hours/week
Capital constraints
Risk tolerance
Tasks founder wants to keep
Tasks founder wants to delegate
```

This influences allocation, not identity/personality labeling.

---

# 40. Model architecture — three logical roles

Use logical model profiles:

```text
STRATEGIC_ANALYZER
CONVERSATION_ROUTER
DEVELOPER_WORKER
```

Founder-selected defaults:

```text
STRATEGIC_ANALYZER → ChatGPT Terra
CONVERSATION_ROUTER → DeepSeek
DEVELOPER_WORKER → Claude Code CLI
```

Never hard-code provider-specific names into domain logic.

---

# 41. Strategic Analyzer — ChatGPT Terra

Use Terra for high-value reasoning:

```text
PESTEL synthesis
SWOT/TOWS
Portfolio analysis
3 strategic options
Goal/OKR design
12WY design
Portfolio trade-offs
Week 13 strategic review
```

## Important implementation boundary

ChatGPT Plus is a ChatGPT subscription; it does **not** include API usage.

Therefore mCOSA must not treat a $20 Plus subscription as an API key.

Define:

```python
class StrategicAnalyzer:
    async def analyze(self, request): ...
```

Support adapters:

```text
ASSISTED_CHATGPT_TERRA
OPENAI_API
OTHER_REASONING_API
LOCAL_REASONING_MODEL
```

### ASSISTED_CHATGPT_TERRA

Recommended initially for the founder's current setup:

1. mCOSA builds a structured analysis package.
2. Export/copy prompt + context.
3. Founder runs it in ChatGPT with the Terra profile.
4. Import/paste structured result.
5. mCOSA validates schema/evidence.
6. Store as versioned Strategy Artifact.
7. Continue CEO Review Wizard.

Do **not** automate consumer ChatGPT login/session scraping.

This keeps V12 compatible with the $20 subscription workflow while remaining technically clean.

---

# 42. Strategic Analysis package

Request:

```yaml
strategic_analysis_request:
  analysis_id:
  organization_context:
  portfolio_context:
  projects:
  founder_profile:
  external_evidence:
  internal_resources:
  previous_cycle_results:
  requested_methodology:
  output_schema_version:
```

Result:

```yaml
strategic_analysis_result:
  assumptions:
  unknowns:
  pestel:
  swot:
  tows:
  strategic_options:
  recommended_goals:
  risks:
  confidence:
  evidence_links:
  questions_for_founder:
```

Later an API reasoning adapter can replace assisted mode without changing domain entities.

---

# 43. DeepSeek for chat and routing

Use DeepSeek for high-frequency tasks:

```text
General chat
Intent classification
Project classification
Simple extraction
Command routing
Dashboard summaries
Status summaries
Low-risk Knowledge Q&A
Light drafting
```

Define:

```python
class ConversationGateway:
    async def chat(...): ...
    async def structured(...): ...
```

Default adapter:

```text
DeepSeekConversationGateway
```

Keep model ID in configuration/env.

---

# 44. Claude Code CLI for coding

Keep V10 design.

```text
Technology WorkItem
   ↓
Local AI Worker Runtime
   ↓
Claude Code Worker
   ↓
Git Worktree
   ↓
Code
   ↓
Tests / Build
   ↓
Artifact
   ↓
Policy / Approval
```

Rules:

- mCOSA does not store the user's Claude subscription password/token.
- User authenticates Claude Code using the installed CLI.
- mCOSA invokes Claude Code as a local developer tool/worker.
- Do not proxy consumer subscription credentials for other users.
- Hosted inference later should use approved API/provider auth.

---

# 45. Model routing matrix

| Work | Default |
| --- | --- |
| Daily chat | DeepSeek |
| Intent/router | DeepSeek |
| Project classifier | DeepSeek structured |
| PESTEL deep analysis | Terra |
| SWOT/TOWS | Terra |
| Portfolio strategy | Terra |
| OKR design | Terra |
| 12WY design | Terra |
| Next Best Action explanation | DeepSeek |
| Strategic conflict rerank | Terra |
| Weekly summary | DeepSeek |
| Week 13 strategic review | Terra |
| Coding | Claude Code CLI |
| Simple extraction | DeepSeek |

Routing levels:

```text
R0 deterministic rules / SQL
R1 DeepSeek
R2 Strategic Analyzer / Terra
R3 Human / Professional Expert
```

---

# 46. Strategic triggers

Escalate to Terra when:

```text
Create/revise PESTEL
Create/revise SWOT/TOWS
Portfolio conflict
Major priority shift
Goals/OKRs
12WY cycle creation
Material re-plan
Week 13 strategic review
Deep strategic comparison
```

Do not escalate for routine status/chat.

---

# 47. Versioning

Version:

```text
project_analysis_version
portfolio_analysis_version
pestel_version
swot_version
tows_version
okr_version
cycle_plan_version
```

Status:

```text
DRAFT
REVIEW
APPROVED
SUPERSEDED
```

Record:

```text
created_by
model_profile
input_hash
evidence_snapshot
created_at
```

---

# 48. Living PESTEL

PESTEL signal:

```yaml
pestel_signal:
  category:
  statement:
  evidence_refs:
  affected_projects:
  direction:
  confidence:
  first_seen:
  last_verified:
  status:
```

Material change flow:

```text
Signal
↓
Impact Analysis
↓
SWOT/TOWS impact?
↓
Goal/KR impact?
↓
Cycle impact?
```

Small → update knowledge.  
Material → CEO exception.

---

# 49. Hologram Hub V12

Keep:

> Speak first → summarize first → open dashboard only when necessary.

Examples:

> "Phân tích 3 project này."

Hub:

```text
I found shared external factors and a founder-capacity conflict.
I recommend Portfolio Analysis.

[Analyze]
[Choose Projects]
```

> "Hôm nay tôi cần làm gì?"

Hub returns Top 3 Next Best Actions.

---

# 50. Mobile V12

Prioritize:

```text
CEO Brief
Next Best Actions
Weekly Company Mission
Portfolio Status
Project Status
Approvals
Gate Decisions
Week 13 Review
Artifacts
Remote Claude Code status
```

Complex strategic matrix editing remains desktop/web-first.

---

# 51. PostgreSQL additions

Suggested additive entities:

```text
project_classifications
methodology_plans
strategic_analysis_versions
evidence_items
strategy_links

cycles
cycle_contracts
cycle_stages
milestones
milestone_evidence
gate_decisions
weekly_missions
weekly_reviews
weekly_scores
cycle_reviews
celebration_records

portfolios
portfolio_projects
portfolio_analysis_versions
portfolio_pestel_signals
project_pestel_impacts
portfolio_swot_items
portfolio_tows_items
portfolio_synergies
portfolio_dependencies
portfolio_options
capacity_allocations
founder_attention_allocations
portfolio_cycles
portfolio_weekly_reviews

founder_profiles
next_action_candidates
next_action_rankings

model_profiles
model_runs
analysis_imports
```

Reuse all suitable V10 entities.

---

# 52. Planning Compiler — reuse V10 execution

Do not build a second task engine.

```text
V12 Strategy / Portfolio / 12WY
        ↓
Planning Compiler
        ↓
V10 Outcome
        ↓
V10 WorkItem
        ↓
V10 Worker / Human
        ↓
V10 Run
        ↓
V10 Artifact / Approval / Evaluation
```

Interface:

```python
class PlanningCompiler:
    async def compile_cycle(self, cycle_id): ...
```

Compile only approved/activated plans.

---

# 53. Backend modules

```text
app/
  projects/
  strategy/
    classifier/
    methodology_router/
    evidence/
    analysis/
    traceability/

  cycles/
    planning/
    milestones/
    weekly/
    reviews/
    week13/

  portfolios/
    detector/
    pestel/
    impact/
    swot_tows/
    priority/
    capacity/
    dependencies/
    synergy/

  next_actions/

  model_gateway/
    contracts/
    deepseek/
    assisted_chatgpt/
    reasoning_api/
    claude_code/

  workforce/   # existing V10
  execution/   # existing V10
  knowledge/   # existing V10
```

---

# 54. Flutter modules

```text
features/
  projects/
    create/
    overview/
    strategy_review/
    cycle/
    milestones/
    weekly_mission/
    week13/

  portfolios/
    overview/
    analyze/
    pestel/
    impact_matrix/
    options/
    capacity/
    cycle/

  ceo/
    brief/
    next_actions/
    decisions/

  hologram_hub/  # existing
  workforce/     # existing
  approvals/     # existing
```

Keep GetX in presentation/navigation/DI boundaries.

---

# 55. API sketch

```text
POST /projects
POST /projects/{id}/classify
POST /projects/{id}/methodology
POST /projects/{id}/analysis
POST /projects/{id}/analysis/import
POST /projects/{id}/analysis/{version}/approve

POST /projects/{id}/cycles
POST /cycles/{id}/activate
GET  /cycles/{id}
POST /cycles/{id}/weekly-reviews
POST /cycles/{id}/week13/finalize

POST /portfolios
POST /portfolios/{id}/analyze
GET  /portfolios/{id}/analysis
POST /portfolios/{id}/options/{option_id}/select
POST /portfolios/{id}/cycles
POST /portfolio-cycles/{id}/activate

GET /ceo/next-actions
GET /ceo/brief

POST /strategic-analyzer/export
POST /strategic-analyzer/import

GET /model-profiles
PUT /model-profiles/{profile}
```

---

# 56. Model-run audit

Record:

```yaml
model_run:
  id:
  logical_profile:
  provider:
  model_or_profile:
  execution_mode:
  purpose:
  project_id:
  portfolio_id:
  input_hash:
  context_refs:
  output_artifact_id:
  duration:
  cost_if_known:
  status:
```

Do not store hidden chain-of-thought. Store inputs, operational metadata, structured output, evidence and user-visible rationale.

---

# 57. Security

Rules:

- Existing V10 permissions remain authoritative.
- Show data exported in Assisted Terra mode.
- Support redaction before export.
- Never export credentials/secrets.
- Claude Code receives only allowed project/worktree paths.
- Portfolio analysis respects per-project ACLs.
- Portfolio membership never automatically grants restricted project access.
- External actions still pass V10 Policy Engine.

---

# 58. Migration from implemented V10

## V12.0 — Contracts

Add Project Classification, Methodology Plan, Cycle, Milestone, Weekly Mission, Portfolio and Model Profile.

## V12.1 — Single Project Journey

```text
Create Project
→ Classify
→ Methodology
→ Assisted Strategic Analysis
→ Review
→ Goals/OKRs
→ 12WY
→ Weekly Mission
```

## V12.2 — Compile to V10

Implement Planning Compiler.

## V12.3 — Weekly Review + Week 13

Implement weekly evidence review, cycle review and celebration.

## V12.4 — Portfolio Intelligence

```text
Portfolio Detector
Shared PESTEL
Impact Matrix
Portfolio SWOT/TOWS
Synergy / Dependency
```

## V12.5 — Portfolio Planning

```text
3 options
Company/Portfolio OKRs
Founder Attention
Capacity
WIP limits
Portfolio 12WY
```

## V12.6 — Next Best Action

Cross-project founder action ranking.

## V12.7 — Living strategy signals

Living PESTEL and material change alerts.

---

# 59. First vertical slice

Use:

> **Founder selects 3 projects and asks mCOSA to decide how to allocate the next 12 weeks.**

Flow:

```text
1 Create/select 3 projects
2 Classify
3 Portfolio Detector
4 Shared evidence package
5 Terra Strategic Analysis: Shared PESTEL
6 Project Impact Matrix
7 Project SWOTs + Portfolio SWOT
8 Portfolio TOWS
9 Three Portfolio Options
10 CEO selects option
11 Company/Portfolio Objective + KRs
12 Map Project OKRs
13 Allocate founder capacity
14 Generate Portfolio 12WY
15 Generate Project Stages/Milestones
16 Generate Week 1 Company Mission
17 Compile to V10 Outcomes/WorkItems
18 Coding work → Claude Code
19 Routine chat/status → DeepSeek
20 Weekly Review
21 Week 13 Review/Learn/Celebrate
```

This validates the complete V12 thesis.

---

# 60. Acceptance criteria

V12 MVP is done when:

1. Founder can create a strategic project with only name + description.
2. AI classifies project before methodology.
3. Full strategy frameworks are not forced on trivial work.
4. Strategic output separates facts, founder input and hypotheses.
5. CEO approves strategy before activation.
6. Strategy traces to Goals/OKRs/WorkItems.
7. 12WY is milestone/stage based.
8. Weekly Mission is explicit.
9. Founder Work vs AI Work is visible.
10. Weekly Review has Execution + Outcome scores.
11. Week 13 supports Reflect/Learn/Celebrate/Reset.
12. 2+ projects can use Portfolio Analysis.
13. Shared PESTEL avoids duplicated research.
14. Project PESTEL impacts remain distinct.
15. Portfolio SWOT/TOWS detects cross-project risks/synergies.
16. Founder capacity is enforced.
17. Portfolio 12WY prevents impossible workload.
18. Next Best Action ranks across projects.
19. V10 WorkItem/Run/Artifact runtime remains intact.
20. Claude Code remains local developer execution.
21. DeepSeek handles routine chat.
22. Terra is available through the configured strategic analyzer workflow.
23. Strategic analyses are versioned/auditable.
24. Founder can close Week 13 and create a new cycle.

---

# 61. Non-goals

Do not build initially:

- Huge methodology marketplace.
- Hundreds of playbooks.
- Fully autonomous CEO.
- Automated legal signing/payment.
- Complex mathematical portfolio optimizer.
- Full graph-database migration.
- New agent framework replacing V10.
- Custom Claude credential proxy.
- Consumer ChatGPT session automation.
- Duplicate task/run system.

---

# 62. Claude Code implementation rules

1. Treat V10 as production baseline.
2. Reuse existing V10 entities/services whenever semantics match.
3. Never create a second execution runtime.
4. Create ADR for architectural deviations.
5. Do not hard-code Terra/DeepSeek/Claude model IDs in domain code.
6. Use logical model profiles and adapters.
7. Every strategic entity must be versionable/auditable.
8. Every Portfolio query must enforce workspace/project authorization.
9. Every Gate preserves evidence.
10. Week 13 is mandatory for normal cycle close unless explicitly overridden.
11. Existing V10 Policy Engine remains the only consequential-action gate.
12. mCOSA must not store Claude consumer credentials.
13. Do not automate consumer ChatGPT authentication/session.
14. Knowledge updates generated by AI remain governed candidates according to existing policy.
15. Add migrations + repositories + tests for every new persisted entity.
16. Add feature flags for all large V12 modules.

---

# 63. Recommended ADRs

```text
ADR-V12-001 Project Methodology Router
ADR-V12-002 Evidence Classes and Strategy Provenance
ADR-V12-003 13-Week Cycle Model
ADR-V12-004 Portfolio Strategy Layer
ADR-V12-005 Founder Attention as Capacity
ADR-V12-006 Model Profiles: Terra / DeepSeek / Claude Code
ADR-V12-007 Assisted ChatGPT Terra Analyzer
ADR-V12-008 Planning Compiler Reuses V10 Runtime
ADR-V12-009 Week 13 Review/Learn/Celebrate
ADR-V12-010 Next Best Action Engine
```

---

# 64. Feature flags

```text
project_classifier_v12
methodology_router_v12
strategy_traceability_v12
cycle_13week_v12
milestones_gates_v12
weekly_missions_v12

portfolio_v12
shared_pestel_v12
portfolio_swot_tows_v12
capacity_planner_v12
founder_attention_v12
portfolio_cycle_v12

next_best_action_v12

deepseek_chat_v12
assisted_terra_v12
claude_code_worker_v12
```

---

# 65. Implementation sequence for Claude Code

## Sprint 1
Domain contracts + migrations.

## Sprint 2
Single Project create/classify/methodology/strategy review.

## Sprint 3
12WY + Milestone + Weekly Mission.

## Sprint 4
Planning Compiler → V10.

## Sprint 5
Weekly Review + Week 13.

## Sprint 6
Portfolio + Shared PESTEL + Impact Matrix.

## Sprint 7
Portfolio SWOT/TOWS + options + capacity.

## Sprint 8
Portfolio 12WY + WIP + Founder Attention.

## Sprint 9
Next Best Action.

## Sprint 10
Hologram/Mobile CEO surfaces + hardening.

---

# 66. Final V12 architecture

```text
                          FOUNDER / CEO
                               │
                               ▼
                             mCOSA
                      AI CHIEF OF STAFF
                               │
                ┌──────────────┴──────────────┐
                │                             │
              CHAT                        STRATEGY
            DeepSeek                    Terra Profile
                │                             │
                └──────────────┬──────────────┘
                               ▼
                       COMPANY STRATEGY
                               │
                               ▼
                      PORTFOLIO STRATEGY
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
          PROJECT A        PROJECT B        PROJECT C
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                    AI METHODOLOGY ROUTER
                               │
                               ▼
              PESTEL / SWOT / TOWS / OKRs
                               │
                               ▼
                      PORTFOLIO 12WY
                               │
                               ▼
                    PROJECT 12WY JOURNEYS
                               │
                               ▼
                 STAGE → MILESTONE → GATE
                               │
                               ▼
                      WEEKLY MISSIONS
                               │
                               ▼
                  NEXT BEST ACTION ENGINE
                               │
                               ▼
                    HYBRID WORKFORCE V10
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
           HUMAN           AI AGENTS        AUTOMATION
                                                 │
                               ┌─────────────────┼─────────────┐
                               ▼                 ▼             ▼
                          CLAUDE CODE         MCP/TOOLS      BROWSER
                               │
                               ▼
                         ARTIFACT / EVIDENCE
                               │
                               ▼
                       WEEKLY / GATE REVIEW
                               │
                               ▼
                            WEEK 13
                  REFLECT → LEARN → CELEBRATE
                               │
                               ▼
                          NEXT CYCLE
```

---

# 67. Core product loop

Single project:

> **Create Project → AI selects methodology → evidence-backed strategy → CEO approves → 12 Week Year → weekly guided missions → V10 Hybrid Workforce executes → CEO handles exceptions → Week 13 review/learn/celebrate → next cycle.**

Multi-project:

> **Company Strategy → Portfolio Analysis → Shared PESTEL → Project Impact → Portfolio SWOT/TOWS → 3 Options → CEO allocates Founder Attention → Portfolio 12WY → Project Journeys → Next Best Actions → Week 13 Portfolio Review.**

This is the V12 operating model to implement on top of the deployed V10 foundation.

---

# Appendix A — Subscription/provider boundaries

The architecture must preserve these current product boundaries:

- ChatGPT Plus is a consumer ChatGPT subscription; API usage is separately billed. Therefore `ASSISTED_CHATGPT_TERRA` is the safe initial V12 integration for the founder's current $20 ChatGPT workflow.
- Claude Pro currently includes Claude Code access for individual use. mCOSA should treat the locally authenticated Claude Code CLI as a local tool and must not proxy consumer subscription credentials on behalf of other users.
- DeepSeek provides programmatic APIs. Exact model identifiers/pricing may change, so keep them in configuration/adapters.

---

# Appendix B — Primary references

- OpenAI — ChatGPT Plus: https://help.openai.com/en/articles/6950777-what-is-chatgpt-plus
- OpenAI — ChatGPT/API billing are separate: https://help.openai.com/en/articles/8156019-how-can-i-move-my-chatgpt-subscription-to-the-api
- Anthropic — Claude Code with Pro/Max: https://support.anthropic.com/en/articles/11145838-using-claude-code-with-your-pro-or-max-plan
- Anthropic — Claude Code authentication: https://docs.anthropic.com/en/docs/claude-code/iam
- Anthropic — Claude Code legal/compliance: https://docs.anthropic.com/en/docs/claude-code/legal-and-compliance
- DeepSeek API Docs: https://api-docs.deepseek.com/

---

# Part B — V12.2 Hybrid LiveKit Local + Cloud Realtime Architecture
## Implementation Specification — V12.1 Baseline + V12.2 Desktop Local / Mobile Cloud Update

**Product:** mCOSA — *my Company One System AI*  
**Baseline:** V10 Hybrid Workforce implemented; V12 Project & Portfolio OS planned/implementing  
**Upgrade type:** Additive architecture update  
**Primary goal:** Add production-grade realtime voice/multimodal interaction without coupling mCOSA directly to one realtime model provider  
**Realtime transport:** LiveKit  
**Default realtime voice model:** Gemini Live through LiveKit Agents  
**Routine text chat:** DeepSeek  
**Strategic reasoning:** ChatGPT Terra profile  
**Coding:** Claude Code CLI  
**Frontend:** Flutter + GetX  
**Backend:** Python FastAPI + PostgreSQL  
**Execution:** Existing mCOSA Local AI Worker Runtime  
**Core architectural rule:** Realtime interaction is a separate plane from business truth and execution

---

# 1. Executive Decision

mCOSA should adopt **LiveKit as the Realtime Interaction Plane**.

LiveKit is not the AI brain and must not replace:

- mCOSA Core.
- Strategy OS.
- Portfolio OS.
- Knowledge Engine.
- Hybrid Workforce.
- Policy Engine.
- Local AI Worker Runtime.
- DeepSeek.
- ChatGPT Terra.
- Claude Code.

Its role is:

```text
Realtime Transport
Voice / Video / Screen / Data
Turn-taking
Interruption / Barge-in
Session lifecycle
Realtime agent participant
```

Recommended north-star:

```text
Flutter Mobile/Desktop/Web
          │
          ▼
        LiveKit
     WebRTC / Data
          │
          ▼
 mCOSA Voice Agent Runtime
          │
   ┌──────┼───────────┐
   ▼      ▼           ▼
Gemini   mCOSA       Context
 Live    Tools       Builder
          │
          ▼
       mCOSA Core
          │
  ┌───────┼─────────────────┐
  ▼       ▼                 ▼
DeepSeek Terra          Hybrid Workforce
                         │
                  ┌──────┼─────────┐
                  ▼      ▼         ▼
              Claude   Agents   Automation
               Code
```

The central principle is:

> **LiveKit carries realtime interaction. mCOSA remains the source of truth.**

---

# 2. Why LiveKit

LiveKit should be used to avoid building and maintaining a custom realtime media stack.

Verified LiveKit capabilities relevant to mCOSA include:

- WebRTC-based realtime communication between frontend and agents.
- Voice, video and realtime data transport.
- Agent participants.
- Turn detection and interruption handling.
- Support for both realtime speech-to-speech models and STT → LLM → TTS pipelines.
- Flutter SDK and Flutter voice-agent starter application.
- LiveKit Cloud or self-hosted deployment.
- Gemini Live realtime plugin.
- Agent observability and cloud session metering.

This makes LiveKit a stronger abstraction boundary than wiring Flutter directly to Gemini Live.

---

# 3. Architectural Boundary

Do not design:

```text
Flutter
  ↓
Gemini Live
  ↓
mCOSA
```

Use:

```text
Flutter
  ↓
LiveKit
  ↓
mCOSA Realtime Agent
  ↓
Realtime Model Adapter
  ├── Gemini Live
  ├── OpenAI Realtime
  └── STT + LLM + TTS Pipeline
```

This allows model switching without rewriting Flutter voice architecture.

---

# 4. Realtime Interaction Plane vs Execution Plane

These are separate systems.

## Realtime Interaction Plane

Use for:

```text
Voice conversation
Video
Screen sharing
Realtime captions
Turn-taking
Interruption
Human–AI session
Phone/SIP later
```

## Execution Plane

Use for:

```text
Research worker
Marketing worker
Finance worker
Claude Code
Browser automation
Scheduled workflows
Document generation
Background jobs
```

Therefore:

```text
LiveKit Agents
≠
mCOSA Agent Runtime
```

LiveKit Agents are realtime participants. mCOSA Workers are business/execution workers. Do not merge the two frameworks.

---

# 5. Voice Is a Modality, Not the Brain

Voice should not own strategic or operational business logic.

Example:

Founder says:

> “Hôm nay tôi cần làm gì?”

Incorrect:

```text
Voice model invents answer
```

Correct:

```text
Voice
 ↓
LiveKit Agent
 ↓
mCOSA Tool:
get_next_best_actions()
 ↓
Portfolio / Project OS
 ↓
Structured result
 ↓
Voice model explains result
```

Business truth stays inside mCOSA.

---

# 6. Recommended Model Roles

```yaml
ai:
  voice_realtime:
    transport: livekit
    default_model: gemini_live

  chat:
    provider: deepseek

  strategy:
    provider: chatgpt
    profile: terra

  coding:
    provider: claude_code_cli
```

| Capability | Default |
| --- | --- |
| Realtime voice | LiveKit + Gemini Live |
| Routine chat | DeepSeek |
| Intent / lightweight commands | LiveKit agent + mCOSA router |
| Strategic PESTEL/SWOT/TOWS/Portfolio | Terra |
| Coding | Claude Code CLI |
| Business data | mCOSA services/PostgreSQL |
| Knowledge retrieval | mCOSA Knowledge Engine |

---

# 7. LiveKit Voice Agent Runtime

Create a dedicated Python service/process:

```text
mCOSA Voice Agent Runtime
```

Suggested modules:

```text
voice_runtime/
  session_manager/
  livekit_transport/
  realtime_model/
  tool_bridge/
  context_builder/
  turn_manager/
  policy_bridge/
  event_bridge/
  cost_tracker/
  observability/
```

FastAPI remains the Control Plane API. The Voice Runtime is a long-lived realtime worker.

---

# 8. FastAPI Responsibilities

FastAPI should handle:

- User authentication.
- Workspace authorization.
- Voice session creation.
- LiveKit access token issuance.
- Session metadata.
- Device/workspace context.
- Tool authorization.
- Policy checks.
- Usage/budget configuration.
- Audit.
- Session history metadata.
- Links to Project / Portfolio / Current Cycle.

FastAPI should **not** directly process the realtime audio loop.

---

# 9. Flutter Responsibilities

Flutter should handle:

- Microphone permission.
- Audio capture/playback.
- LiveKit room connection.
- Audio track subscription/publication.
- Optional video/camera.
- Optional screen share.
- Realtime transcript display.
- Realtime state animation.
- Mute/unmute.
- Push-to-talk.
- Conversation Mode.
- Session start/end.
- Device audio routing.
- Reconnect UX.
- User-visible error states.

Do not embed provider API keys in Flutter.

---

# 10. Flutter SDK Strategy

Use LiveKit Flutter client as the realtime client abstraction.

Recommended service boundary:

```dart
abstract class RealtimeSessionGateway {
  Future<void> connect(...);
  Future<void> disconnect();
  Future<void> setMicrophoneEnabled(bool enabled);
  Stream<RealtimeSessionEvent> get events;
}
```

Implementation:

```text
LiveKitRealtimeSessionGateway
```

Presentation:

```text
VoiceSessionController
HologramStateController
RealtimeTranscriptController
```

Keep GetX in Presentation / Navigation / DI, consistent with existing mCOSA architecture.

---

# 11. Voice Session Lifecycle

Suggested lifecycle:

```text
CREATING
CONNECTING
READY
LISTENING
THINKING
RETRIEVING
ACTING
WAITING_APPROVAL
SPEAKING
INTERRUPTED
RECONNECTING
ERROR
ENDED
```

The Hologram Hub should map animation/state to these actual events.

---

# 12. Hologram Hub State Mapping

```text
LiveKit connected
   ↓
IDLE / READY

User speech detected
   ↓
LISTENING

Turn ends
   ↓
THINKING

Tool call started
   ↓
RETRIEVING / ACTING

Approval required
   ↓
WAITING APPROVAL

Agent audio publishing
   ↓
SPEAKING

User interrupts
   ↓
INTERRUPTED → LISTENING
```

Do not expose private chain-of-thought.

---

# 13. Barge-in Is an MVP Requirement

Realtime voice must support user interruption.

Scenario:

```text
mCOSA:
"mVault currently has three—"

Founder:
"Dừng. Mở dashboard."
```

Expected behavior:

```text
Agent speaking
   ↓
User activity detected
   ↓
Interruption
   ↓
Stop agent audio
   ↓
Capture new turn
   ↓
Process new intent
```

Do not ship a voice MVP that forces the user to wait for full TTS completion.

---

# 14. Turn Detection

Turn detection determines when the user has finished speaking.

V1 should use LiveKit-supported turn/activity detection and allow tuning:

```yaml
voice:
  turn_detection:
    mode:
    min_endpointing_delay:
    max_endpointing_delay:
    interruption_enabled: true
    interruption_threshold:
```

Avoid hard-coding one timing profile for every device/language. Vietnamese should be benchmarked independently.

---

# 15. Voice Modes

## 15.1 Push-to-Talk

Recommended initial mobile mode.

```text
Hold button
→ speak
→ release
→ process
```

Benefits:

- Easy to understand.
- Fewer false turns.
- Lower idle cost.
- Strong privacy boundary.

## 15.2 Conversation Mode

```text
Start Conversation
→ continuous realtime session
```

Useful for:

- Weekly review.
- Strategy discussion.
- Project walkthrough.
- Hands-free interaction.

## 15.3 Ambient Desktop Mode

```text
Local Wake Word
→ open LiveKit session
```

Do not stream microphone audio continuously to cloud while idle.

---

# 16. Wake Word

Wake word should be local where feasible.

```text
Microphone
  ↓
Local Wake Word Detector
  ↓
"mCOSA"
  ↓
Start / wake realtime session
```

Do not implement:

```text
Mic 24/7
→ Cloud realtime model
```

Benefits:

- Privacy.
- Lower bandwidth.
- Lower usage cost.
- Lower unnecessary cloud processing.

Wake-word implementation remains provider-neutral.

---

# 17. Realtime Model Adapter

Create a provider-neutral contract:

```python
class RealtimeVoiceModel:
    async def attach(self, session_context): ...
    async def update_context(self, context): ...
    async def send_tool_result(self, result): ...
    async def close(self): ...
```

Initial implementation:

```text
GeminiLiveRealtimeModel
```

Future options:

```text
OpenAIRealtimeModel
PipelineRealtimeModel
```

Do not expose Gemini-specific protocol to Flutter.

---

# 18. Gemini Live Default

Gemini Live is the recommended initial realtime speech model behind LiveKit because LiveKit provides a Google realtime plugin with a `RealtimeModel` abstraction for low-latency two-way voice interaction.

Use it for:

- Natural voice conversation.
- Low-latency spoken responses.
- Audio input/output.
- Optional multimodal scenarios when enabled.

Do not use it as the sole source for strategic truth.

---

# 19. STT → LLM → TTS Alternative

LiveKit Agents also supports:

```text
Speech
 ↓
STT
 ↓
LLM
 ↓
TTS
```

This can be used when:

- Cost is more important than native speech-to-speech behavior.
- A text model must remain the conversation brain.
- Better transcript control is required.
- A specific TTS voice is required.
- Native realtime audio provider is unavailable.

Potential V2 profile:

```yaml
voice:
  profile: pipeline
  stt: configurable
  llm: deepseek
  tts: configurable
```

Do not hard-code this into V1.

---

# 20. Voice Session Router

```text
User Speech
   ↓
Realtime Session Router
   ├── Conversational
   ├── Operational Command
   ├── Strategic Analysis
   ├── Knowledge Query
   ├── Approval
   └── Coding Request
```

Routing:

```text
Conversational
→ realtime model

Operational command
→ mCOSA tool

Strategic
→ Terra strategic job

Knowledge
→ Knowledge Engine

Approval
→ V10 Policy / Approval service

Coding
→ Technology WorkItem → Claude Code
```

---

# 21. Tool Bridge

The Voice Agent must call mCOSA application services through a controlled Tool Bridge.

Example tools:

```text
CEO:
- get_ceo_brief
- get_next_best_actions
- get_needs_you

Project:
- get_project_status
- get_weekly_mission
- get_milestone
- open_project_dashboard

Portfolio:
- get_portfolio_status
- get_project_priorities
- get_founder_capacity

Work:
- create_work_item
- get_run_status
- get_artifact

Approval:
- get_pending_approvals
- approve_action
- reject_action

Knowledge:
- knowledge_search
- knowledge_read

Navigation:
- open_dashboard
- open_project
- open_portfolio
```

Do not expose raw database or shell access to the realtime agent.

---

# 22. Policy Bridge

No voice command may bypass the V10 Policy Engine.

Founder says:

> “Đăng luôn bài Facebook.”

Correct path:

```text
Voice Command
  ↓
mCOSA Action
  ↓
Policy Engine
  ↓
Risk / Authority / Budget
  ↓
Approval if needed
  ↓
Execute
```

Incorrect:

```text
Voice model → Facebook API directly
```

---

# 23. Approval by Voice

Voice can be an approval surface, but approval semantics remain in mCOSA.

```text
mCOSA:
"Chiến dịch này sẽ sử dụng 3 triệu đồng ngân sách quảng cáo. Anh có muốn duyệt không?"

Founder:
"Duyệt."
```

Record:

```text
approval_request_id
approved_by
voice_session_id
timestamp
action_ref
policy_result
```

For high-risk actions, stronger confirmation/authentication may still be required.

---

# 24. Voice Context Builder

A realtime session should receive only compact context.

Default context:

```text
User
Role
Organization
Current Portfolio
Current Project
Current Cycle
Current Week
Current UI screen
Top active goals
Top 3 Next Best Actions
Pending approvals count
Short conversation summary
Available tool definitions
```

Do not inject:

```text
Entire Knowledge vault
All chat history
All project artifacts
All run logs
```

Retrieve on demand.

---

# 25. Knowledge Retrieval During Voice

Founder:

> “Tại sao mVault tuần này bị cảnh báo?”

Voice agent calls:

```text
portfolio.get_project_health()
knowledge.search()
project.get_risks()
```

mCOSA returns structured evidence; voice model explains.

---

# 26. Voice + Terra Strategic Analysis

Strategic request:

> “Phân tích lại 3 project và đề xuất tôi nên tập trung vào cái nào.”

Flow:

```text
Speech
 ↓
LiveKit
 ↓
Intent: STRATEGIC_PORTFOLIO_ANALYSIS
 ↓
Create Strategic Analysis Job
 ↓
Terra Strategic Analyzer
 ↓
Portfolio Analysis Artifact
 ↓
mCOSA Review State
 ↓
Voice summary
```

Do not ask the realtime voice model to replace Terra for deep strategy work.

---

# 27. Voice + Claude Code

Founder:

> “Triển khai Portfolio Impact Matrix.”

Flow:

```text
LiveKit
 ↓
mCOSA Tool Bridge
 ↓
Technology WorkItem
 ↓
V10 Execution Runtime
 ↓
Desktop Device Agent
 ↓
Claude Code CLI
 ↓
Git Worktree
 ↓
Tests / Build
 ↓
Artifact
 ↓
Voice notification
```

The realtime session must not execute shell commands itself.

---

# 28. Realtime Events from Desktop Execution

Expose selected events to Voice Runtime:

```text
JOB_STARTED
PLAN_READY
TESTS_RUNNING
TESTS_PASSED
TESTS_FAILED
WAITING_APPROVAL
ARTIFACT_READY
JOB_FAILED
```

Then voice can answer:

> “Claude Code đang làm tới đâu?”

without reading raw logs.

---

# 29. Human + AI Realtime Sessions

LiveKit room architecture can later support:

```text
Founder
Human Manager
mCOSA Voice Agent
```

Possible uses:

- Weekly company review.
- Project review.
- Planning session.
- Team meeting.
- Customer call with AI assistant.

Avoid creating rooms where many AI agents freely talk to each other. Internal AI collaboration should remain structured through Task, Artifact, Evidence and Decision.

---

# 30. Human Meeting Copilot

Future feature:

```text
Human meeting
  ↓
LiveKit room
  ↓
mCOSA listens with permission
  ↓
Transcript
  ↓
Decisions
Actions
Evidence
Follow-ups
  ↓
Knowledge candidates
```

Explicit participant consent/privacy rules must apply. Do not silently record meetings.

---

# 31. Video and Screen Sharing

Possible use cases:

```text
Screen share dashboard
→ "Giải thích tại sao project này màu đỏ."

Screen share Claude Code
→ "Tình trạng build thế nào?"
```

V1 does not need to make video mandatory. Architecture should simply avoid preventing it later.

---

# 32. Screen Context Rule

Differentiate:

```text
SCREEN_VIEW
SCREEN_CONTROL
LOCAL_TOOL_EXECUTION
```

V1 may support `SCREEN_VIEW` while actual control remains through authorized mCOSA tools.

---

# 33. Telephony Future Path

Possible future uses:

```text
Customer support calls
Sales qualification
Appointment calls
Inbound company assistant
External expert call assistant
```

This is V2/V3, not MVP.

Telephony requires additional privacy, consent, call recording, escalation and legal review.

---

# 34. RealtimeTransport Interface

```python
class RealtimeTransport:
    async def create_session(self, ...): ...
    async def close_session(self, ...): ...
    async def send_data(self, ...): ...
    async def publish_event(self, ...): ...
```

Implementation:

```text
LiveKitRealtimeTransport
```

This prevents LiveKit identifiers from spreading throughout domain code.

---

# 35. VoiceGateway Interface

```python
class VoiceGateway:
    async def start_session(self, request): ...
    async def end_session(self, session_id): ...
    async def push_context(self, session_id, context): ...
    async def notify(self, session_id, event): ...
```

Implementation:

```text
LiveKitVoiceGateway
```

---

# 36. Session Domain

```yaml
realtime_session:
  id:
  organization_id:
  user_id:
  device_id:
  project_id: optional
  portfolio_id: optional
  mode: push_to_talk|conversation|ambient
  transport: livekit
  model_profile:
  started_at:
  ended_at:
  status:
  room_ref:
  agent_ref:
  cost_summary:
```

Do not store raw provider credentials.

---

# 37. Realtime Event Domain

```yaml
realtime_event:
  id:
  session_id:
  sequence:
  type:
  timestamp:
  payload_ref:
  project_id:
  run_id:
  work_item_id:
  approval_id:
```

Events:

```text
SESSION_CONNECTED
USER_SPEECH_STARTED
USER_SPEECH_ENDED
USER_TRANSCRIPT
AGENT_THINKING
TOOL_CALL_STARTED
TOOL_CALL_FINISHED
APPROVAL_REQUIRED
AGENT_SPEECH_STARTED
AGENT_SPEECH_STOPPED
USER_INTERRUPTED
SESSION_RECONNECTED
SESSION_ERROR
SESSION_ENDED
```

Persist only what is useful for audit/UX.

---

# 38. Transcript Policy

Configurable:

```text
OFF
EPHEMERAL
SESSION_ONLY
SAVE_SUMMARY
SAVE_FULL_TRANSCRIPT
```

Recommended OPC default:

```text
SAVE_SUMMARY
```

unless user requests full transcript.

---

# 39. Audio Recording Policy

Do not record audio by default.

```text
record_audio: false
```

When enabled:

- User knows recording is active.
- Retention policy is explicit.
- Access control is applied.
- Recording classification is set.
- Deletion is supported.

---

# 40. Privacy Architecture

Rules:

- No API secrets in audio context.
- No passwords in logs.
- Sensitive content can disable transcript persistence.
- Knowledge permissions still apply.
- Cross-project access still applies.
- Screen share is user-controlled.
- Microphone is visibly active.
- Session termination must actually stop media publication.
- Local wake word should not upload idle microphone audio.

---

# 41. Authentication

```text
Flutter
  ↓
mCOSA Auth
  ↓
POST /realtime/sessions
  ↓
FastAPI validates user/workspace/device
  ↓
Issue short-lived LiveKit connection credentials
  ↓
Flutter joins room
```

Do not ship long-lived LiveKit admin credentials in the app.

---

# 42. Authorization

Session token scope should reflect:

```text
organization
user
device
room
participant identity
media permissions
```

mCOSA Tool Bridge separately verifies:

```text
RBAC
ABAC
Project access
Portfolio access
Knowledge scope
Action authority
```

Realtime room participation never implies business permission.

---

# 43. Cloud vs Self-Hosted

Keep deployment provider-neutral:

```text
RealtimeTransport
   ↓
LiveKit
   ├── LiveKit Cloud
   └── Self-Hosted
```

## Recommended MVP

Use LiveKit Cloud.

Reasons:

- Faster deployment.
- Avoid operating WebRTC infrastructure.
- Easier NAT/network handling.
- Easier production testing.

## Re-evaluate self-hosting when

- Enterprise/on-prem demand.
- Data residency constraints.
- Privacy requirements.
- Cost at meaningful scale.
- Private-network use cases.

For a one-person company MVP, operating WebRTC infrastructure is usually a poor use of Founder Attention.

---

# 44. Local-First Boundary

LiveKit improves online realtime interaction but does not make voice fully offline.

mCOSA remains local-first because:

- Knowledge can remain local.
- Claude Code runs local.
- Desktop files remain local.
- Worker runtime remains local.
- Cloud sync remains controlled.

When internet is unavailable:

```text
Cloud realtime voice
→ OFFLINE / DEGRADED

Local text/desktop functions
→ continue
```

---

# 45. Offline Fallback

V1:

```text
No network
→ Voice unavailable
→ Text/local command fallback
```

V2 possible:

```text
Local wake word
Local STT
Local small router/model
Local TTS
```

Use the same abstraction boundaries where practical.

---

# 46. Cost Model

Realtime cost may include:

```text
LiveKit session
+
Realtime model
+
Optional STT
+
Optional TTS
+
Optional LLM
```

Implement:

```yaml
voice_budget:
  monthly_budget:
  per_session_limit:
  warning_threshold:
  max_conversation_minutes:
  idle_timeout:
```

Do not assume voice is free because one layer has a free allowance.

---

# 47. Idle Timeout

Conversation Mode should end or suspend after inactivity.

```yaml
voice:
  idle_timeout_seconds:
  max_session_minutes:
```

Do not leave realtime sessions connected indefinitely.

---

# 48. Cost-Aware Voice Modes

```text
Push-to-Talk
→ default mobile, low cost

Conversation
→ user explicitly starts session

Ambient
→ local wake word, cloud session only after wake
```

---

# 49. Observability

Track:

```text
Session duration
Connection failures
Reconnect count
User speech latency
End-of-turn latency
Time-to-first-agent-audio
Tool-call latency
Interruption rate
False interruption rate
Model errors
Tool errors
Cost
```

End-to-end conversational latency matters more than raw model latency alone.

---

# 50. Voice Quality KPIs

Recommended:

```text
P50 / P95 response latency
P50 / P95 tool response latency
Successful interruption rate
False interruption rate
Session completion rate
Reconnect recovery rate
User correction rate
Voice command success rate
Cost per successful session
```

---

# 51. Hologram Voice UX

Hologram Hub should render:

```text
IDLE
LISTENING
THINKING
RETRIEVING
ACTING
WAITING APPROVAL
SPEAKING
WARNING
ERROR
OFFLINE
```

Visuals can respond to audio amplitude and actual operational states.

---

# 52. Voice UX — CEO Brief

Founder:

> “mCOSA, tình hình hôm nay?”

Tool:

```text
get_ceo_brief()
```

Response data:

```text
Company health
Current 12WY week
Top portfolio risks
Top 3 next actions
Approvals
Founder capacity
```

Voice model summarizes only the important parts.

---

# 53. Voice UX — Weekly Mission

Founder:

> “Tuần này mục tiêu gì?”

Tool:

```text
get_weekly_company_mission()
```

Voice:

```text
"Tuần này mục tiêu chính là hoàn tất MVP mCOSA
và xác thực rủi ro pháp lý của mVault.
Anh có ba việc cần trực tiếp xử lý..."
```

---

# 54. Voice UX — Portfolio

Founder:

> “So sánh 3 project.”

Light comparison:

```text
DeepSeek / deterministic portfolio data
```

Deep strategic reconsideration:

```text
Create Terra analysis job
```

Voice should say when a deeper job is being created instead of pretending it completed instantly.

---

# 55. Voice UX — Approval

Founder:

> “Có gì chờ tôi duyệt?”

Tool:

```text
get_pending_approvals()
```

Return highest-risk first; do not read long lists.

Example:

```text
"Anh có 4 yêu cầu. Một yêu cầu mức rủi ro cao liên quan triển khai production.
Anh muốn xem nó trước không?"
```

---

# 56. Voice UX — Coding

Founder:

> “Claude Code đã xong chưa?”

Tool:

```text
get_developer_run_status()
```

Response:

```text
"Đã hoàn thành code và build.
38 test pass, còn 2 warning.
Đang chờ anh duyệt merge."
```

---

# 57. Voice UX — Navigation

Examples:

```text
"Mở Portfolio."
"Mở mVault."
"Cho tôi xem Week 4."
"Mở approval."
```

Use a structured navigation event to Flutter. Do not let the voice model fabricate routes.

---

# 58. Flutter Navigation Event

```yaml
ui_command:
  type: OPEN_ROUTE
  route: /portfolio/{id}
  params:
```

Flutter validates route and user state.

---

# 59. Realtime Data Channel

Use realtime data for:

```text
UI commands
Structured tool progress
State events
Captions
Approval cards
Artifact notifications
```

Do not send large artifacts through realtime messages; send artifact references.

---

# 60. Artifacts

If voice triggers long work:

```text
Research report
Code diff
Portfolio analysis
Spreadsheet
```

return:

```text
artifact_id
title
status
summary
```

Voice can say:

> “Báo cáo đã hoàn thành. Tôi đã mở artifact trên màn hình.”

---

# 61. Long-Running Jobs

Voice must never hold the realtime model “thinking” for minutes.

```text
User command
 ↓
Create WorkItem / Job
 ↓
Voice acknowledges
 ↓
Background execution
 ↓
Realtime event when ready
 ↓
Voice/notification surfaces result
```

---

# 62. Notifications After Session Ends

If a job completes after voice session ends:

```text
Cloud event
 ↓
Mobile/Desktop notification
 ↓
User reopens
 ↓
mCOSA can speak result
```

Do not require the LiveKit room to stay connected for background work.

---

# 63. Room Design

Recommended default:

```text
1 user session
1 mCOSA realtime agent
```

Future:

```text
multiple humans
1 mCOSA agent
```

Avoid:

```text
1 user
12 speaking agents
```

Internal agent orchestration remains behind mCOSA.

---

# 64. Participant Identity

Examples:

```text
human:{user_id}
mcosa:voice:{session_id}
```

Do not expose internal workers as room participants unless a real use case requires it.

---

# 65. Python Agent Service

Recommended package:

```text
services/realtime_agent/
```

Responsibilities:

```text
LiveKit agent lifecycle
Gemini Live adapter
Tool bridge
Session context
Turn/interruption events
Operational telemetry
```

Keep separate from:

```text
services/local_worker/
services/control_plane/
```

---

# 66. Deployment Topology

MVP:

```text
Flutter Client
    │
    ▼
LiveKit Cloud
    │
    ▼
mCOSA Realtime Agent Service
    │
    ├── Gemini Live
    └── FastAPI / mCOSA Core
              │
              ▼
          PostgreSQL
              │
              ▼
      Desktop Execution Node
```

---

# 67. Desktop Local Voice Option

Desktop can use LiveKit for online conversation.

If future privacy/local requirements justify it, add:

```text
Flutter Desktop
 ↓
Local Voice Gateway
```

Do not entangle it with V1 LiveKit implementation.

---

# 68. Failure Handling

Handle:

```text
LiveKit disconnect
Model disconnect
Tool timeout
Tool error
Permission denied
Microphone error
Audio device change
Network degradation
Provider quota
Invalid session
Desktop worker offline
```

User-facing messages must distinguish voice failure from mCOSA Core or Desktop Worker failure.

---

# 69. Reconnect

On transient network loss:

```text
RECONNECTING
```

Flutter should:

- Preserve UI.
- Stop claiming the agent is listening.
- Attempt reconnect.
- Rehydrate compact context if necessary.
- Avoid duplicate action execution.

Use idempotency keys for voice-triggered commands.

---

# 70. Voice Command Idempotency

Every consequential command should receive:

```text
voice_command_id
```

If reconnect/retry occurs, mCOSA must not create duplicate:

```text
payments
posts
jobs
approvals
work items
```

---

# 71. Audit

Audit:

```text
who asked
what action was interpreted
which tool was called
policy result
approval result
which worker executed
artifact/result
```

Do not audit hidden model reasoning.

---

# 72. Transcript vs Action Audit

These are separate.

A transcript can be deleted while consequential action audit remains.

Example:

```text
Transcript retention: 0 days
Action audit: retained according to company policy
```

---

# 73. Voice and Knowledge Memory

Do not promote all voice conversations into permanent knowledge.

```text
Voice Session
 ↓
Session Summary
 ↓
Candidate Memories
 ↓
Evaluation
 ↓
Approved Knowledge
```

Important decisions can be proposed as Knowledge candidates.

---

# 74. Decision Capture

Founder says:

> “Chu kỳ này tạm dừng VT Signal và tập trung mCOSA.”

Create a structured decision proposal:

```text
VT Signal → HOLD
mCOSA → ACCELERATE
```

If confirmed/authorized:

```text
Decision
→ Portfolio state update
→ Knowledge
→ Audit
```

---

# 75. Voice Security Levels

Map voice actions onto the existing V10 risk policy.

Example:

```text
"Open dashboard"
→ informational

"Create draft"
→ local/reversible

"Publish campaign"
→ external consequential

"Transfer money"
→ critical + strong confirmation
```

---

# 76. Voice Authentication Is Not Enough for Critical Actions

Voice recognition alone should not be assumed to be strong identity proof.

For critical actions:

```text
Voice command
 ↓
Policy
 ↓
App confirmation / biometric / strong auth
 ↓
Execute
```

Do not implement voiceprint-only payment authorization in V1.

---

# 77. LiveKit Cloud First

Recommended:

```text
V1 → LiveKit Cloud
```

Reasons:

- Faster implementation.
- Lower operational complexity.
- Easier WebRTC deployment.
- Good Flutter support.
- Easier production testing.

Keep deployment interfaces so self-hosting remains possible.

---

# 78. Self-Hosted Later

Evaluate self-hosting only when evidence supports it.

Decision inputs:

```text
Monthly realtime minutes
Concurrent sessions
Region/data residency
Enterprise contract
Network topology
Operational staffing
Privacy requirements
```

For an OPC MVP, operating WebRTC infrastructure is usually a poor use of Founder Attention.

---

# 79. Provider Lock-In Control

Avoid three forms of lock-in.

## Transport lock-in

Use:

```text
RealtimeTransport
```

## Realtime model lock-in

Use:

```text
RealtimeVoiceModel
```

## Tool lock-in

Voice tools call mCOSA application services, not provider-specific function schemas directly.

---

# 80. LiveKit Inference vs Direct Provider Plugin

Architecture should allow both:

```text
LiveKit Inference
```

and:

```text
Direct Gemini plugin / provider billing
```

Decision factors:

```text
latency
billing
rate limits
deployment
data handling
cost
```

Do not make this a domain decision.

---

# 81. Feature Flags

```text
livekit_transport_v12_1
voice_agent_runtime_v12_1
gemini_live_voice_v12_1
voice_tools_v12_1
voice_barge_in_v12_1
voice_transcript_v12_1
voice_navigation_v12_1
voice_approval_v12_1
voice_screen_share_v12_1
voice_multi_human_v12_1
telephony_v12_1
```

---

# 82. Database Additions

Suggested:

```text
realtime_sessions
realtime_session_participants
realtime_events
voice_commands
voice_command_tool_calls
voice_session_summaries
voice_usage_records
voice_recording_policies
voice_preferences
```

Reuse:

```text
users
organizations
projects
portfolios
work_items
runs
approvals
artifacts
audit
knowledge
```

---

# 83. API Sketch

```text
POST /realtime/sessions
GET  /realtime/sessions/{id}
POST /realtime/sessions/{id}/end

POST /realtime/token
GET  /realtime/config

POST /voice/commands/{id}/confirm
POST /voice/commands/{id}/cancel

GET  /voice/preferences
PUT  /voice/preferences

GET  /voice/usage

POST /voice/session/{id}/summary
```

Most realtime events flow through LiveKit rather than normal REST endpoints.

---

# 84. Internal Tool API

Use application service contracts such as:

```text
CEOService
ProjectService
PortfolioService
NextBestActionService
ApprovalService
KnowledgeService
NavigationService
WorkService
ArtifactService
DeviceService
```

Voice Runtime must not directly query database tables for business decisions.

---

# 85. MVP Scope

V12.1 MVP should implement:

```text
LiveKit Cloud
Flutter audio session
1 user + 1 mCOSA voice agent
Gemini Live default
Push-to-Talk
Conversation Mode
Barge-in
Realtime transcript
Hologram state mapping
CEO Brief tool
Next Best Actions tool
Project status tool
Portfolio status tool
Approval listing
Navigation commands
Claude Code run status
Session usage tracking
```

Do not include telephony or multi-human meetings in MVP.

---

# 86. First Vertical Slice

Founder opens Hologram Hub and asks:

> “Hôm nay tôi cần làm gì?”

Expected:

```text
1. Flutter joins LiveKit room.
2. Microphone is published.
3. Voice Agent detects the turn.
4. Agent calls mCOSA get_next_best_actions().
5. mCOSA returns structured portfolio-aware priorities.
6. Gemini Live verbalizes the answer.
7. Hologram transitions through real states.
8. Founder interrupts mid-sentence.
9. Agent immediately stops and listens.
10. Founder says “Mở project mVault.”
11. Voice Agent sends a structured UI navigation event.
12. Flutter opens mVault Project dashboard.
13. Session remains active.
```

This validates transport, tool bridge, interruption and UI integration.

---

# 87. Second Vertical Slice

Founder asks:

> “Claude Code đang làm tới đâu?”

Expected:

```text
Voice
→ mCOSA Device/Run service
→ Existing V10 run events
→ Structured status
→ Spoken response
```

No Claude Code shell execution from the voice process.

---

# 88. Third Vertical Slice

Founder asks:

> “Phân tích lại 3 project và đề xuất project ưu tiên.”

Expected:

```text
Voice
→ classify as strategic
→ create Portfolio Strategic Analysis Job
→ Terra workflow
→ acknowledge job
→ background result
→ artifact ready event
→ voice/mobile notification
```

Do not block the realtime session for long strategic reasoning.

---

# 89. Implementation Phases

## Phase LK-0 — Contracts

Implement:

```text
RealtimeTransport
VoiceGateway
RealtimeVoiceModel
RealtimeSession domain
VoiceCommand domain
```

## Phase LK-1 — Flutter Connection

Implement:

```text
LiveKit token endpoint
Flutter join/leave
Mic/audio
Session states
```

## Phase LK-2 — Voice Agent

Implement:

```text
Python LiveKit Agents runtime
Gemini Live
Basic transcript
```

## Phase LK-3 — Tool Bridge

Implement:

```text
CEO Brief
Next Best Action
Project/Portfolio status
```

## Phase LK-4 — Hologram Integration

Map realtime operational events to UI animation.

## Phase LK-5 — Interruption

Tune VAD/turn detection/barge-in for Vietnamese.

## Phase LK-6 — Work / Approval / Navigation

Connect V10 work, approval and Flutter routing.

## Phase LK-7 — Observability / Cost

Add metrics, usage policy and idle timeout.

## Phase LK-8 — Optional Multimodal

Screen share/video.

## Phase LK-9 — Future Telephony

Only after clear business need.

---

# 90. Claude Code Implementation Rules

1. Read existing V10/V12 realtime-related code first.
2. Do not replace V10 Worker Runtime.
3. Do not put long-lived audio processing inside FastAPI request handlers.
4. Use LiveKit Flutter SDK for media transport.
5. Do not put Gemini API credentials in Flutter.
6. Implement `RealtimeTransport` before provider-specific integrations.
7. Implement `RealtimeVoiceModel` before Gemini-specific logic.
8. Implement `VoiceGateway` before exposing voice to domain services.
9. Business tools must call application services, not repositories directly.
10. All consequential actions pass V10 Policy Engine.
11. Add idempotency for voice-triggered actions.
12. Do not persist raw audio by default.
13. Do not persist full transcript by default.
14. Do not store private chain-of-thought.
15. Do not implement voiceprint-based critical authorization.
16. Keep LiveKit Cloud/self-host choice in infrastructure configuration.
17. Add tests for reconnect and duplicate command prevention.
18. Add tests for project/portfolio authorization.
19. Add instrumentation for latency and interruptions.
20. Keep telephony out of MVP.

---

# 91. Suggested Backend Package

```text
backend/app/realtime/
  domain/
    session.py
    events.py
    commands.py

  application/
    session_service.py
    voice_gateway.py
    tool_bridge.py
    context_builder.py

  infrastructure/
    livekit/
      transport.py
      token_service.py
      agent_dispatch.py

    models/
      realtime_model.py
      gemini_live.py

  api/
    routes.py
```

Realtime agent service:

```text
services/realtime_agent/
  main.py
  agent.py
  tools.py
  session_context.py
  event_bridge.py
```

---

# 92. Suggested Flutter Package

```text
lib/features/realtime_voice/
  data/
    livekit_gateway.dart

  domain/
    realtime_session.dart
    realtime_event.dart

  presentation/
    controllers/
      voice_session_controller.dart
      transcript_controller.dart

    widgets/
      push_to_talk_button.dart
      conversation_controls.dart
      transcript_view.dart
```

Integrate with existing:

```text
hologram_hub/
navigation/
approvals/
projects/
portfolios/
```

---

# 93. Config Example

```yaml
realtime:
  transport:
    provider: livekit
    deployment: cloud

  voice:
    default_mode: push_to_talk
    conversation_mode_enabled: true
    ambient_mode_enabled: false

  model:
    provider: gemini_live

  transcript:
    retention: summary_only

  recording:
    enabled: false

  interruption:
    enabled: true

  security:
    critical_actions_require_strong_confirmation: true

  cost:
    idle_timeout_seconds: 120
    session_warning_minutes: 30
```

---

# 94. Environment Variables

```text
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET

GOOGLE_API_KEY

VOICE_SESSION_MAX_MINUTES
VOICE_IDLE_TIMEOUT_SECONDS
```

Secrets stay server-side.

---

# 95. Acceptance Criteria

V12.1 is accepted when:

1. Flutter Mobile/Desktop can open a LiveKit voice session.
2. No provider secret is embedded in Flutter.
3. User speech reaches the realtime agent.
4. Agent audio reaches Flutter.
5. User can interrupt agent speech.
6. Hologram state reflects actual realtime state.
7. Voice can retrieve CEO Brief.
8. Voice can retrieve Next Best Actions.
9. Voice can query Project/Portfolio status.
10. Voice can report Claude Code job state.
11. Voice can send UI navigation commands.
12. Consequential actions still pass V10 Policy Engine.
13. Reconnect does not duplicate actions.
14. Transcript retention follows policy.
15. Raw audio is not recorded by default.
16. Long jobs are executed asynchronously outside voice session.
17. Strategic requests can route to Terra jobs.
18. Routine chat remains available through DeepSeek where appropriate.
19. LiveKit is isolated behind a `RealtimeTransport` abstraction.
20. Gemini Live is isolated behind a `RealtimeVoiceModel` abstraction.
21. Existing V10 Hybrid Workforce remains unchanged.
22. Existing V12 Project/Portfolio logic remains the source of truth.

---

# 96. Non-Goals

Do not build in V12.1 MVP:

```text
Fully offline realtime speech
Custom WebRTC server
Voiceprint payment authorization
12-agent realtime AI conference
Always-on cloud microphone
Full telephony contact center
Automatic call recording
Realtime agent-to-agent brainstorming rooms
Direct voice shell access
Direct voice database access
Direct Gemini integration inside Flutter
```

---

# 97. ADRs to Create

```text
ADR-LK-001 LiveKit as Realtime Interaction Plane
ADR-LK-002 Realtime Interaction vs Execution Plane
ADR-LK-003 LiveKit Cloud First
ADR-LK-004 Gemini Live Behind RealtimeVoiceModel
ADR-LK-005 Voice Tool Bridge Uses mCOSA Application Services
ADR-LK-006 Barge-in as MVP Requirement
ADR-LK-007 Transcript and Recording Retention
ADR-LK-008 Voice Critical Action Authentication
ADR-LK-009 Voice Session Idempotency
ADR-LK-010 Realtime Context Minimization
```

---

# 98. Final Architecture

```text
                         FOUNDER / CEO
                               │
                               ▼
                        FLUTTER CLIENT
                  Mobile / Desktop / Web
                               │
                               ▼
                            LIVEKIT
                  WebRTC / Audio / Video / Data
                               │
                               ▼
                    mCOSA REALTIME AGENT
                               │
              ┌────────────────┼─────────────────┐
              │                │                 │
              ▼                ▼                 ▼
        GEMINI LIVE       TOOL BRIDGE       CONTEXT BUILDER
                               │
                               ▼
                           mCOSA CORE
                               │
          ┌────────────────────┼─────────────────────┐
          ▼                    ▼                     ▼
       DEEPSEEK              TERRA               KNOWLEDGE
      routine chat       strategy jobs            ENGINE
                               │
                               ▼
                    PROJECT / PORTFOLIO OS
                               │
                               ▼
                     HYBRID WORKFORCE V10
             ┌─────────────────┼──────────────────┐
             ▼                 ▼                  ▼
           HUMAN            AI AGENTS         AUTOMATION
                                                  │
                         ┌────────────────────────┼───────────┐
                         ▼                        ▼           ▼
                    CLAUDE CODE                 MCP         BROWSER
                         │
                         ▼
                  ARTIFACT / RESULT
                         │
                         ▼
                     POLICY / AUDIT
                         │
                         ▼
                   LIVEKIT RESPONSE
```

---

# 99. Architectural Summary

The correct abstraction is:

> **LiveKit = Realtime Interaction Plane**

> **Gemini Live = Default realtime voice model**

> **DeepSeek = Routine conversational model**

> **ChatGPT Terra = Strategic analysis model/profile**

> **Claude Code CLI = Developer execution worker**

> **mCOSA Core = Company truth, strategy, portfolio, projects, policy, tools, knowledge, work and audit**

LiveKit must make mCOSA more realtime and multimodal without making the system dependent on a single voice model or moving business logic into the voice layer.

---

# 100. Implementation Recommendation

Implement V12.1 in this order:

```text
LiveKit Transport
   ↓
Flutter Audio Session
   ↓
Python Realtime Agent
   ↓
Gemini Live
   ↓
Tool Bridge
   ↓
CEO Brief / Next Best Actions
   ↓
Hologram State
   ↓
Barge-in
   ↓
Project / Portfolio Tools
   ↓
Approval / Work Status
   ↓
Observability / Cost
```

The first production objective is not “voice everywhere.”

It is:

> **A founder can open mCOSA, speak naturally, interrupt naturally, ask what matters now, and securely control the existing Project/Portfolio/Hybrid Workforce system without touching a complex dashboard.**

---

# Appendix A — Verified LiveKit Capabilities Used in This Specification

This specification relies on LiveKit capabilities documented by LiveKit:

- LiveKit Agents uses WebRTC between frontend and agent and is designed for realtime voice/video agents.
- LiveKit Agents supports both STT–LLM–TTS pipelines and realtime models.
- Turn-taking includes user activity detection and interruption handling.
- LiveKit provides a Flutter SDK and Flutter voice-agent starter.
- LiveKit's Google plugin provides a realtime model wrapper for Gemini Live.
- LiveKit can connect clients to LiveKit Cloud or a self-hosted LiveKit server.
- LiveKit Cloud publishes separate agent-session quotas, metering and pricing.

Provider models, prices, quotas and allowances may change, so model IDs and cost values must remain configuration rather than domain constants.

---

# Appendix B — Primary References

- LiveKit Agents: https://docs.livekit.io/agents/
- Agent speech/audio: https://docs.livekit.io/agents/multimodality/audio/
- Turn detection: https://docs.livekit.io/agents/logic/turns/
- Turn-taking tuning / interruption handling: https://docs.livekit.io/agents/logic/turns/tuning/
- Gemini Live plugin: https://docs.livekit.io/agents/models/realtime/plugins/gemini/
- Flutter quickstart: https://docs.livekit.io/transport/sdk-platforms/flutter/
- Flutter starter app: https://docs.livekit.io/frontends/start/starter-apps/flutter/
- Flutter SDK reference: https://docs.livekit.io/reference/client-sdk-flutter/
- LiveKit Cloud billing: https://docs.livekit.io/deploy/admin/billing/
- LiveKit quotas/limits: https://docs.livekit.io/deploy/admin/quotas-and-limits/
- LiveKit pricing: https://livekit.io/pricing
- LiveKit open-source server: https://github.com/livekit/livekit

# V12.2 Update — Hybrid LiveKit Local + Cloud Voice Architecture

## 101. Decision Summary

V12.2 refines the V12.1 realtime design into a hybrid deployment model:

```text
Desktop
→ LiveKit Local
→ Local Realtime Agent
→ Local-first mCOSA Runtime

Mobile
→ LiveKit Cloud
→ Cloud Realtime Agent
→ mCOSA Cloud Control Plane
→ Desktop Execution Node when required
```

The default model responsibilities remain:

```text
Desktop routine conversation
→ Local / DeepSeek-backed conversational path

Mobile realtime voice
→ Gemini Live through LiveKit Cloud

Strategic reasoning
→ ChatGPT Terra assisted workflow or configured reasoning API

Coding
→ Claude Code CLI on Desktop
```

Key product rule:

> **Realtime transport selection and AI-model selection are independent decisions.**

For example:

```text
LiveKit Local + cloud LLM
```

is valid.

So is:

```text
LiveKit Local + local STT/TTS + DeepSeek
```

---

# 102. Desktop Realtime Architecture

Desktop is already an mCOSA Execution Node, therefore it should preferentially run the realtime media plane locally.

Recommended topology:

```text
Flutter Desktop
      │
      ▼
LiveKit Local Server
      │
      ▼
mCOSA Local Voice Agent
      │
 ┌────┼─────────────────────┐
 ▼    ▼                     ▼
STT  Conversation        mCOSA Tools
     Model                  │
                            ▼
                   Local AI Worker Runtime
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
        Knowledge       Claude Code      Browser/MCP
```

Benefits:

- Lower local audio transport latency.
- No LiveKit Cloud minutes for local desktop conversations.
- Better privacy boundary.
- Direct access to local mCOSA services through controlled interfaces.
- Better integration with local Knowledge Engine.
- Better integration with Claude Code CLI.
- Reduced dependence on cloud availability for the realtime transport layer.

---

# 103. Desktop Does Not Mean Fully Offline

Important distinction:

```text
LOCAL TRANSPORT
≠
LOCAL AI
```

LiveKit can be local while the selected model remains cloud-based.

Examples:

```text
LiveKit Local
→ Gemini Live

LiveKit Local
→ DeepSeek API

LiveKit Local
→ OpenAI API

LiveKit Local
→ Local STT + Local LLM + Local TTS
```

The architecture must therefore separate:

```text
RealtimeTransport
RealtimeVoiceModel
ConversationModel
STT
TTS
```

---

# 104. Recommended Desktop Voice Profiles

## Profile A — Local Efficient

Recommended default for long desktop usage.

```text
LiveKit Local
→ Local STT
→ DeepSeek / low-cost conversation model
→ Local TTS
```

Use for:

- General conversation.
- Task lookup.
- CEO brief.
- Project status.
- Next Best Action.
- Navigation.
- Knowledge queries.
- Operational commands.

Advantages:

- Low transport cost.
- Reduced cloud-audio exposure.
- Predictable cost.
- Suitable for frequent daily use.

---

## Profile B — Natural Realtime

Use when natural low-latency speech-to-speech is more important.

```text
LiveKit Local
→ Gemini Live
```

The audio transport between Flutter Desktop and the local Voice Agent stays local, while model inference can still use the cloud.

Use for:

- Longer conversational sessions.
- Hands-free reviews.
- Natural interruption-heavy interaction.
- Multimodal sessions.

---

## Profile C — Local Private

Future option:

```text
LiveKit Local
→ Local STT
→ Local LLM
→ Local TTS
```

Use for:

- Sensitive local-only Projects.
- Offline/degraded connectivity.
- Privacy-sensitive sessions.

This is not required for V12.2 MVP.

---

# 105. Mobile Realtime Architecture

Mobile should default to LiveKit Cloud.

```text
Flutter Mobile
      │
      ▼
LiveKit Cloud
      │
      ▼
mCOSA Cloud Voice Agent
      │
      ├── Gemini Live
      ├── mCOSA Tool Bridge
      └── Cloud Context Builder
               │
               ▼
        FastAPI Control Plane
               │
          ┌────┴─────┐
          ▼          ▼
     PostgreSQL   Desktop Node
                     │
                     ▼
                Claude Code
                Local Files
                Local Knowledge
```

Mobile is a remote surface, not the primary execution node.

---

# 106. Why Mobile Uses LiveKit Cloud

Mobile connectivity must handle:

- Wi-Fi ↔ 4G/5G switching.
- NAT.
- Network degradation.
- Foreground/background changes.
- Remote access to Desktop.
- Reconnection.
- Geographic distance.

Operating a publicly exposed self-hosted LiveKit stack solely for an OPC mobile client is not recommended in the initial architecture.

LiveKit Cloud should therefore be the default Mobile transport.

---

# 107. AUTO Realtime Transport Mode

Add:

```text
Voice Transport

○ Local
○ Cloud
● Auto
```

Recommended routing:

```text
IF device == Desktop
AND local LiveKit available
AND local Voice Runtime healthy
THEN
    transport = LOCAL
ELSE
    transport = CLOUD
```

Mobile:

```text
transport = CLOUD
```

Future trusted-LAN mobile mode may optionally connect locally, but should not complicate MVP.

---

# 108. Realtime Transport Resolver

Introduce:

```python
class RealtimeTransportResolver:
    async def resolve(self, context) -> TransportDecision:
        ...
```

Inputs:

```text
Device type
Network state
Local LiveKit health
Cloud availability
Project privacy policy
Voice mode
User preference
Cost policy
```

Output:

```yaml
transport_decision:
  transport: livekit_local|livekit_cloud
  reason:
  fallback:
```

---

# 109. Voice Intelligence AUTO Mode

Add:

```text
Voice Intelligence

○ Local Efficient
○ Natural Realtime
○ Private Local
● Auto
```

Suggested AUTO routing:

```text
Routine information / command
→ efficient conversation path

Natural conversational session
→ Gemini Live

Strategic request
→ Terra strategic job

Coding request
→ Claude Code WorkItem
```

The founder should not need to think in provider names during normal use.

---

# 110. ChatGPT Plus / Terra Boundary

Critical architecture rule:

> **ChatGPT Plus is not an OpenAI API entitlement.**

Therefore:

```text
LiveKit Local
→ ChatGPT Plus API
```

must **not** be implemented.

Terra remains a strategic reasoning profile through one of these supported modes:

```text
ASSISTED_CHATGPT_TERRA
OPENAI_API_REASONING
OTHER_REASONING_API
LOCAL_REASONING
```

Recommended current configuration:

```text
ASSISTED_CHATGPT_TERRA
```

---

# 111. Assisted Terra Strategic Workflow

Desktop or Mobile strategic request:

```text
"Phân tích lại PESTEL của 3 project."
```

Flow:

```text
Voice / Chat
    ↓
Strategic Intent
    ↓
mCOSA builds Analysis Package
    ↓
Terra Assisted Workflow
    ↓
Founder uses ChatGPT Plus / Terra
    ↓
Import result into mCOSA
    ↓
Schema + Evidence validation
    ↓
CEO Review
```

mCOSA must not:

- scrape ChatGPT sessions;
- automate consumer login;
- store browser cookies to emulate an API;
- treat Plus subscription as backend API credits.

---

# 112. Optional OpenAI API Realtime

If the founder later wants OpenAI realtime API:

```text
LiveKit Local
→ OpenAI Realtime API
```

or:

```text
LiveKit Cloud
→ OpenAI Realtime API
```

is architecturally valid.

However:

```text
OpenAI API billing
```

is separate from:

```text
ChatGPT Plus subscription
```

The adapter boundary should make this an infrastructure/configuration change, not a domain change.

---

# 113. Claude Code Subscription Boundary

Claude Code remains a local developer worker.

Recommended:

```text
Desktop Node
→ installed Claude Code CLI
→ user-authenticated Claude Code environment
```

mCOSA should:

- detect availability;
- launch allowed jobs;
- supply worktree/context;
- collect results/events;

but should not:

- store the user's Claude password;
- proxy consumer subscription credentials for other users;
- expose Claude credentials to Cloud Control Plane.

---

# 114. DeepSeek Role

DeepSeek remains the default routine conversational model.

Use for:

```text
Text chat
Intent classification
Project classification
Simple extraction
Command interpretation
Dashboard explanation
Weekly summaries
Status narration
Low-risk Knowledge Q&A
```

For Desktop efficient voice, DeepSeek can sit behind:

```text
Local STT
→ DeepSeek
→ Local TTS
```

Provider identifiers and credentials remain infrastructure configuration.

---

# 115. Unified RealtimeSession

Do not create separate business-session models for Desktop and Mobile.

Use:

```yaml
realtime_session:
  id:
  user_id:
  organization_id:
  device_id:
  device_type:
  transport:
  voice_profile:
  model_profile:
  project_id:
  portfolio_id:
  cycle_id:
  started_at:
  ended_at:
```

Examples:

```text
Desktop:
transport = LIVEKIT_LOCAL

Mobile:
transport = LIVEKIT_CLOUD
```

Both use the same mCOSA Project/Portfolio/Work/Approval state.

---

# 116. Session Continuity Across Devices

mCOSA business context should be transferable across devices.

Example:

```text
Desktop:
Founder reviews mVault.

Leaves office.

Mobile:
"Tiếp tục phần mVault vừa rồi."
```

Mobile can load:

```text
Current Project
Current Cycle
Recent decision context
Pending approval
Last session summary
```

Do not attempt to migrate a raw LiveKit room between deployments.

Transfer **mCOSA session context**, not media-session identity.

---

# 117. Desktop Local Discovery

Flutter Desktop should detect:

```text
Local LiveKit Server
Local Voice Agent
Local Worker Runtime
```

Health model:

```yaml
local_realtime_health:
  livekit:
  voice_agent:
  worker_runtime:
  last_checked_at:
```

If unhealthy:

```text
AUTO
→ fallback to LiveKit Cloud
```

with user-visible notification.

---

# 118. Local LiveKit Binding

For Desktop single-machine mode:

```text
127.0.0.1 / localhost
```

should be preferred unless LAN access is intentionally enabled.

Do not expose the local LiveKit server publicly by default.

---

# 119. Desktop LAN Mode — Future

Optional future:

```text
Trusted local network
Mobile
→ local LiveKit Desktop server
```

Only add after:

- device pairing;
- TLS;
- access tokens;
- network trust model;
- discovery security;
- firewall guidance.

Not part of MVP.

---

# 120. Mobile Remote Desktop Execution

Mobile request:

> “Triển khai feature này.”

Flow:

```text
Mobile
 ↓
LiveKit Cloud
 ↓
Cloud Voice Agent
 ↓
mCOSA Control Plane
 ↓
Create Technology WorkItem
 ↓
Desktop Device Agent
 ↓
Claude Code CLI
 ↓
Artifact / Events
 ↓
Cloud
 ↓
Mobile
```

Mobile voice never executes local shell directly.

---

# 121. Desktop Voice Execution

Desktop request:

> “Chạy test module Portfolio.”

Flow:

```text
Desktop Voice
 ↓
LiveKit Local
 ↓
Local Voice Agent
 ↓
mCOSA Tool Bridge
 ↓
Policy
 ↓
Local WorkItem
 ↓
Claude Code / Local Worker
```

The architecture may avoid a cloud roundtrip for safe local operations, while audit/sync can occur asynchronously.

---

# 122. Cloud Control Plane Boundary

Cloud remains authoritative for:

```text
Identity
Workspace
Device registry
Remote jobs
Sync metadata
Cross-device approvals
Notifications
Audit aggregation
```

Desktop local runtime remains authoritative for local execution state until synchronized.

Voice transport does not change this boundary.

---

# 123. Local-First Voice Privacy

Recommended Desktop default:

```text
Audio transport:
LOCAL

Transcript:
SUMMARY_ONLY or SESSION_ONLY

Raw audio recording:
OFF
```

If cloud AI is called, send only what the selected model requires.

Future optimization:

```text
Local STT
→ send text only to cloud
```

to avoid uploading raw audio for routine requests.

---

# 124. Cloud Mobile Privacy

Mobile LiveKit Cloud must still respect:

```text
Knowledge scopes
Project restrictions
Data classifications
Transcript policy
Recording policy
Tool permissions
```

A Cloud voice session must not gain access to Desktop-local secrets merely because the Desktop is online.

---

# 125. Local vs Cloud Tool Availability

Desktop Local session may expose:

```text
Local Knowledge
Local Files
Claude Code
Git
Browser
Local MCP
```

Mobile Cloud session may expose:

```text
Cloud-safe Project data
Portfolio data
Remote WorkItem creation
Remote status
Approval
Artifacts
```

Access to local-only tools happens through the Desktop Device Agent and policy.

---

# 126. Tool Capability Discovery

Voice Runtime should retrieve:

```text
available_capabilities
```

from mCOSA rather than assuming tools exist.

Example:

```yaml
capabilities:
  claude_code:
    online: true
    device_id:
  local_knowledge:
    online: true
  browser:
    online: false
```

Voice response can then be accurate.

---

# 127. Hybrid Failure Modes

Handle:

```text
Desktop local LiveKit down
→ Cloud fallback

Cloud unavailable
→ Desktop local continues

Desktop offline while Mobile requests Claude Code
→ WAITING_FOR_DEVICE

Gemini quota unavailable
→ fallback voice profile

DeepSeek unavailable
→ configured fallback

Terra assisted analysis pending
→ show WAITING_FOR_FOUNDER
```

Do not surface all failures as “AI unavailable.”

---

# 128. Voice Profile Configuration

Suggested config:

```yaml
realtime:

  transport:
    desktop: auto
    mobile: livekit_cloud

  desktop_profiles:

    efficient:
      transport: livekit_local
      stt: local
      conversation: deepseek
      tts: local

    natural:
      transport: livekit_local
      realtime_model: gemini_live

    private:
      transport: livekit_local
      stt: local
      conversation: local_model
      tts: local

  mobile_profile:
    transport: livekit_cloud
    realtime_model: gemini_live

  strategy:
    profile: terra
    mode: assisted_chatgpt

  coding:
    provider: claude_code_cli
    execution: desktop_local
```

---

# 129. User Settings

Expose simple settings, not infrastructure complexity.

```text
Voice Mode
● Auto
○ Local
○ Cloud

Desktop Voice Quality
● Efficient
○ Natural
○ Private

Mobile Voice
● Realtime
○ Push-to-Talk only

Strategic Analysis
ChatGPT Terra — Assisted

Coding
Claude Code — Connected
```

Advanced provider configuration lives in Developer/System Settings.

---

# 130. Cost Strategy for OPC

V12.2 is designed around a fixed/low-variable-cost philosophy where practical.

Recommended:

```text
Desktop:
LiveKit Local
+ local audio processing where possible
+ DeepSeek for routine conversation
+ Terra assisted for strategic analysis
+ Claude Code subscription for coding

Mobile:
LiveKit Cloud
+ Gemini Live only when realtime voice is actually used
```

This pushes high-frequency interaction toward lower-cost/local paths and reserves usage-based cloud realtime for mobile or high-value sessions.

---

# 131. Founder Attention vs Compute Cost

Do not optimize only for monetary cost.

Example:

A local voice stack that saves $5/month but causes:

```text
poor recognition
repeated commands
high latency
founder frustration
```

is a bad OPC optimization.

Optimization order:

```text
1. Accepted outcome
2. Founder attention
3. Reliability
4. Privacy/risk
5. Latency
6. Cost
```

within practical budget constraints.

---

# 132. Recommended V12.2 Vertical Slice

Implement:

> Founder uses Desktop local voice during work, then leaves and continues from Mobile cloud voice.

## Desktop

```text
1. Flutter Desktop detects local LiveKit.
2. AUTO selects LOCAL.
3. Founder asks: "Hôm nay tôi cần làm gì?"
4. Local Voice Agent calls NextBestActionService.
5. Response is spoken.
6. Founder says: "Triển khai Portfolio Impact Matrix."
7. Technology WorkItem created.
8. Claude Code begins locally.
```

## Mobile

```text
9. Founder leaves Desktop running.
10. Flutter Mobile uses LiveKit Cloud.
11. Founder asks: "Claude Code đang tới đâu?"
12. Cloud Voice Agent queries Desktop run through Control Plane.
13. Mobile receives spoken status.
14. Job completes.
15. Mobile receives notification/result.
16. Founder approves next action.
```

This validates the entire distributed realtime model.

---

# 133. Second V12.2 Vertical Slice — Strategic Request

Desktop or Mobile:

> “Phân tích PESTEL của mCOSA, mVault và VT Signal.”

Expected:

```text
Voice recognizes strategic intent
 ↓
mCOSA builds Portfolio Analysis request
 ↓
Terra Assisted Analysis package created
 ↓
Founder is told:
"Đây là phân tích chiến lược sâu. Tôi đã chuẩn bị gói phân tích Terra."
 ↓
Founder completes Terra workflow
 ↓
Result imported
 ↓
mCOSA validates evidence
 ↓
Portfolio analysis updated
```

Realtime voice remains responsive instead of pretending to perform deep strategic reasoning immediately.

---

# 134. Migration from V12.1

No destructive migration.

Add:

```text
transport_mode
voice_profile
local_realtime_health
device_realtime_capabilities
session_origin
```

Update `RealtimeTransportResolver`.

Keep:

```text
LiveKitRealtimeTransport
LiveKitVoiceGateway
RealtimeVoiceModel
GeminiLiveRealtimeModel
```

Add:

```text
LiveKitLocalTransport
LiveKitCloudTransport
DesktopVoiceProfileResolver
```

---

# 135. New ADRs

Add:

```text
ADR-LK-011 Hybrid Local/Cloud LiveKit Deployment
ADR-LK-012 Desktop LiveKit Local First
ADR-LK-013 Mobile LiveKit Cloud First
ADR-LK-014 Realtime Transport Resolver AUTO Mode
ADR-LK-015 Local Transport Does Not Imply Local AI
ADR-LK-016 ChatGPT Plus Is Not an API Credential
ADR-LK-017 Terra Assisted Strategic Workflow
ADR-LK-018 Cross-Device Session Context Continuity
ADR-LK-019 OPC Voice Cost Strategy
```

---

# 136. V12.2 Feature Flags

```text
desktop_livekit_local_v12_2
mobile_livekit_cloud_v12_2
realtime_transport_auto_v12_2
desktop_voice_efficient_v12_2
desktop_voice_natural_v12_2
desktop_voice_private_v12_2
cross_device_session_context_v12_2
remote_claude_status_voice_v12_2
```

---

# 137. V12.2 Acceptance Criteria

V12.2 is accepted when:

1. Desktop can run voice through a local LiveKit server.
2. Desktop AUTO mode selects local transport when healthy.
3. Desktop can fall back to cloud transport.
4. Mobile defaults to LiveKit Cloud.
5. Desktop and Mobile map to the same mCOSA business context.
6. Raw LiveKit room identity is not used as the business-session identity.
7. Desktop can use an efficient non-realtime-model voice profile.
8. Desktop can optionally use Gemini Live for natural realtime speech.
9. ChatGPT Plus/Terra is never treated as an API credential.
10. Strategic Terra workflow remains assisted/configurable.
11. Claude Code remains a local Desktop worker.
12. Mobile can query Claude Code status remotely.
13. Mobile can create a remote coding WorkItem.
14. Desktop safe-local operations can execute without unnecessary cloud roundtrips when policy allows.
15. Audit/sync remains consistent after local execution.
16. Tool availability is capability-driven.
17. Desktop local failure is clearly distinguishable from cloud failure.
18. Cloud outage does not unnecessarily break local Desktop voice.
19. No long-lived provider secrets are embedded in Flutter.
20. V10 Hybrid Workforce and V12 Project/Portfolio execution remain unchanged.

---

# 138. Final V12.2 Architecture

```text
                           FOUNDER / CEO
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
          FLUTTER DESKTOP                FLUTTER MOBILE
                 │                             │
                 ▼                             ▼
          LIVEKIT LOCAL                  LIVEKIT CLOUD
                 │                             │
                 ▼                             ▼
        LOCAL VOICE AGENT               CLOUD VOICE AGENT
                 │                             │
       ┌─────────┼─────────┐                   ▼
       ▼         ▼         ▼               GEMINI LIVE
 Local STT    DeepSeek   Gemini                 │
 Local TTS      Chat      Live                  │
       │                   │                    │
       └─────────┬─────────┘                    │
                 ▼                              │
             mCOSA TOOLS ◄──────────────────────┘
                 │
                 ▼
               mCOSA CORE
                 │
       ┌─────────┼─────────────────────────────┐
       ▼         ▼                             ▼
   PROJECT OS  PORTFOLIO OS                 KNOWLEDGE
       │         │                             │
       └─────────┼─────────────────────────────┘
                 ▼
          HYBRID WORKFORCE V10
       ┌─────────┼──────────────┐
       ▼         ▼              ▼
     HUMAN    AI AGENTS      AUTOMATION
                                 │
                     ┌───────────┼───────────┐
                     ▼           ▼           ▼
                CLAUDE CODE    MCP        BROWSER
                     │
                     ▼
                  ARTIFACT
                     │
                     ▼
              POLICY / APPROVAL
                     │
                     ▼
              AUDIT / KNOWLEDGE

Strategic deep reasoning:
mCOSA → Terra Assisted Workflow → CEO Review
```

---

# 139. V12.2 Implementation Recommendation

For the current OPC architecture, use:

## Desktop

```text
LiveKit Local
+
Local STT/TTS where practical
+
DeepSeek for frequent conversational work
+
Gemini Live as optional Natural Voice profile
+
ChatGPT Terra assisted for strategic analysis
+
Claude Code CLI for coding
```

## Mobile

```text
LiveKit Cloud
+
Gemini Live
+
mCOSA Cloud Control Plane
+
Remote Desktop Execution Node
```

## Principle

> **Use local infrastructure for frequent work, cloud realtime where mobility requires it, subscription-assisted reasoning for high-value strategic analysis, and local Claude Code for software execution.**

This model best matches mCOSA's local-first, distributed, one-person-company operating philosophy.

---

# Part C — V12.3 Hierarchical Agent Memory & Context Offload

## 140. V12.3 Decision

Integrate TencentCloud/TencentDB-Agent-Memory as an **optional mCOSA Agent Memory Engine / Sidecar**.

It must **not** replace:

- PostgreSQL as System of Record.
- mCOSA Knowledge Engine.
- Project / Portfolio data.
- Strategy / OKR / 12WY data.
- Approval / authority / policy state.
- Artifact registry.
- Company decisions.

Its purpose is narrower:

> **Give agents efficient cross-session memory, context offloading, task continuation and experience recall without turning raw conversations into official company knowledge.**

Recommended topology:

```text
mCOSA Core
   │
   ├── Knowledge Engine
   │     └── Official / governed company knowledge
   │
   └── AgentMemoryGateway
         └── TencentDB Agent Memory Sidecar
               ├── Working context offload
               ├── Cross-session recall
               ├── Task memory
               ├── Scenario memory
               └── Founder / Agent profile candidates
```

---

## 141. Why This Is Useful for mCOSA

mCOSA has four workloads that create long, repetitive context:

1. Claude Code development sessions.
2. DeepSeek daily chat.
3. LiveKit realtime voice sessions.
4. Long-running departmental agents.

Without a dedicated Agent Memory layer, mCOSA risks:

```text
Every session
→ reload large chat history
→ reload tool logs
→ reload project files
→ reload previous errors
→ high token/cost/latency
→ inconsistent continuation
```

V12.3 introduces:

```text
Raw execution/history
      ↓
Agent Memory
      ↓
Compact recall/context
      ↓
Context Builder
      ↓
Current agent/model
```

---

## 142. Four Memory Domains in mCOSA

mCOSA should distinguish four memory/knowledge layers.

| Layer | Purpose | Authoritative? |
| --- | --- | --- |
| Working Memory | Current turn/task/run context | No |
| Agent Memory | Cross-session experience and recall | No |
| Company Knowledge | Approved facts, decisions, SOPs, evidence | Yes, governed |
| Company Memory | Lessons and institutional experience promoted from execution | Governed |

Architecture:

```text
                  mCOSA MEMORY SYSTEM

                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 WORKING MEMORY      AGENT MEMORY     COMPANY KNOWLEDGE
        │                │                │
 Current task       TencentDB-style    Markdown / PG
 Tool results       hierarchical       Evidence
 Context canvas     memory             Decisions
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                    EVALUATION
                         │
                         ▼
                 MEMORY CANDIDATE
                         │
                    GOVERNANCE
                  ┌──────┴──────┐
                  ▼             ▼
              DISCARD        PROMOTE
                                  │
                                  ▼
                           COMPANY MEMORY
```

---

## 143. Mapping TencentDB Memory Concepts to mCOSA

Recommended conceptual mapping:

| TencentDB concept | mCOSA use |
| --- | --- |
| L0 Conversation | Raw conversation/run/tool event references |
| L1 Atom | Candidate fact/preference/lesson |
| L2 Scenario | Project/task/operating experience |
| L3 Persona | Founder/Agent operating profile candidate |
| Task canvas | Compact current execution context |
| Raw refs | Artifact/evidence/tool-output references |
| Hybrid retrieval | Keyword + semantic + metadata search |
| Memory gateway | `AgentMemoryGateway` |
| Memory→Skill | Skill/SOP/Playbook improvement candidate |

mCOSA must not assume L3 Persona is automatically true.

---

## 144. Memory State and Confidence

Every promoted or inferred memory should have explicit state:

```text
OBSERVED
INFERRED
CONFIRMED
DISPUTED
EXPIRED
SUPERSEDED
```

Suggested metadata:

```yaml
memory_item:
  id:
  organization_id:
  project_id: optional
  agent_id: optional
  human_id: optional
  type:
  status:
  confidence:
  source_refs: []
  valid_from:
  valid_until:
  created_at:
  last_used_at:
```

An inferred founder preference is not equal to a confirmed founder setting.

---

## 145. AgentMemoryGateway

mCOSA domain code must not depend directly on TencentDB classes.

Define:

```python
class AgentMemoryGateway:
    async def capture(self, event): ...
    async def recall(self, query): ...
    async def search(self, query): ...
    async def get_task_context(self, task_id): ...
    async def get_scenario(self, scenario_id): ...
    async def get_profile(self, subject_id): ...
    async def end_session(self, session_id): ...
    async def promote_candidate(self, candidate_id): ...
    async def forget(self, memory_id): ...
    async def export(self, scope): ...
```

Initial adapter:

```text
TencentDBAgentMemoryAdapter
```

Future adapters may include:

```text
CustomMemoryAdapter
LocalOnlyMemoryAdapter
OtherMemoryEngineAdapter
```

---

## 146. Deployment as a Sidecar

Recommended Desktop deployment:

```text
mCOSA Desktop
│
├── Flutter Desktop
├── Local Worker Runtime
├── Claude Code CLI
├── Knowledge Engine
├── LiveKit Local
└── Agent Memory Sidecar
      ├── Memory Gateway
      ├── SQLite
      └── vector index
```

Communication:

```text
FastAPI / Local Worker
      ↓
AgentMemoryGateway
      ↓
localhost Memory Service
```

Do not import Node-specific memory implementation into mCOSA Python domain.

---

## 147. Local Storage First

For the initial implementation:

```text
Agent Memory
→ local SQLite/vector storage
```

Avoid introducing Tencent Cloud database dependency.

mCOSA already has:

```text
PostgreSQL / pgvector
```

for structured/system-of-record and governed search needs.

The Agent Memory sidecar should remain replaceable.

---

## 148. Claude Code Is the First PoC

Do not integrate memory everywhere at once.

First PoC:

```text
Claude Code session
      ↓
Tool output / test logs / errors / decisions
      ↓
Agent Memory capture
      ↓
Session end
      ↓
Compact task/scenario memory
      ↓
Next Claude Code session
      ↓
Recall
      ↓
Context Builder
      ↓
Continue task
```

Target use case:

> “Tiếp tục implementation Portfolio Impact Matrix hôm qua.”

Expected recall:

```text
Task status
Changed files
Tests
Known issue
Pending step
Last artifact
Relevant refs
```

---

## 149. Claude Code Context Offload

Long developer runs generate large output:

```text
grep
build logs
test logs
compiler output
terminal output
large files
tool results
```

Do not keep all of this in the active model context.

Use:

```text
Raw output
   ↓
Artifact / raw ref
   ↓
Compact memory node
   ↓
Task canvas
   ↓
Current Claude context
```

Claude retrieves detailed refs only when needed.

This should reduce repeated rereading and context pressure.

---

## 150. Claude Code Memory Tools

Expose through the existing Claude Code plugin/MCP boundary:

```text
memory.recall
memory.search
memory.task_context
memory.capture
memory.forget
```

Optional:

```text
memory.explain_source
memory.list_refs
```

Do not let Claude directly mutate official Company Knowledge.

---

## 151. Context Builder Integration

Update V12 Context Builder:

```text
Context Builder
    │
    ├── Project state
    ├── Portfolio state
    ├── Current 12WY
    ├── Relevant Knowledge
    ├── Agent Memory
    ├── Recent Artifacts
    └── Tool capabilities
```

Context selection priority:

```text
Authority / current truth
→ Project/Portfolio state

Approved facts
→ Knowledge Engine

Relevant previous experience
→ Agent Memory

Raw details
→ Artifact/reference on demand
```

---

## 152. Source-of-Truth Priority

If Agent Memory conflicts with current System of Record:

```text
PostgreSQL / approved Knowledge
wins
```

Example:

```text
Agent Memory:
"Project mVault is ACTIVE"

Current Project state:
"HOLD"
```

mCOSA must use:

```text
HOLD
```

and can mark the memory stale.

---

## 153. Founder Memory

Founder memory can reduce repeated preference/context questions.

Example hierarchy:

```text
L0
"I prefer three strategic options."

L1
Candidate:
Founder prefers a Rule of 3.

L2
Scenario:
Strategic planning preferences.

L3
Founder Operating Profile candidate.
```

Before promoting material preferences:

```text
inferred
→ repeated evidence
→ confirmation or high confidence
→ governed profile
```

Do not use memory inference as a sensitive identity label.

---

## 154. Founder Operating Profile Integration

V12 already has Founder Operating Profile.

Use Agent Memory only as an input source:

```text
Conversation history
      ↓
Agent Memory
      ↓
Profile candidate
      ↓
Founder review / governance
      ↓
Founder Operating Profile
```

The official profile remains mCOSA structured data.

---

## 155. DeepSeek Chat Memory

DeepSeek routine chat should receive:

```text
Current organization/project context
+
Short session summary
+
Relevant Agent Memory
+
Relevant Knowledge
```

Do not send:

```text
entire chat history
entire Knowledge vault
all run logs
```

Retrieval should be selective.

---

## 156. LiveKit Voice Memory

LiveKit realtime voice must prioritize low latency.

Voice session context:

```text
User
Current Project
Current Portfolio
Current Week
Next Best Actions
Session summary
Top relevant memories
Available tools
```

When user asks:

> “Chúng ta hôm qua đã thống nhất gì?”

Voice agent calls:

```text
memory.recall()
```

rather than loading all past audio/transcripts.

---

## 157. Voice Transcript → Memory

Do not save every voice transcript permanently.

Flow:

```text
Voice Session
     ↓
Session Summary
     ↓
Candidate memories
     ↓
Evaluation
     ↓
Agent Memory
     ↓
Optional promotion
     ↓
Company Knowledge
```

Transcript retention remains governed by V12.2 voice privacy settings.

---

## 158. Strategic Analysis Memory Boundary

Terra strategic analysis should consume:

```text
Approved Knowledge
Current Project/Portfolio state
Evidence
Previous approved strategy
Relevant lessons
```

Agent Memory may contribute:

```text
previous research experience
founder working preferences
known workflow pitfalls
```

but must not silently become strategic evidence.

Every PESTEL/SWOT/TOWS claim still requires evidence classification/provenance.

---

## 159. Memory and Portfolio Isolation

Memory must be scoped at least by:

```text
organization_id
project_id
agent_id
human_id
memory_classification
```

Required tests:

```text
Organization A cannot recall Organization B.

Project A cannot recall restricted Project B.

Marketing Agent cannot recall restricted Finance memory.

Human A personal memory cannot appear for Human B.

Mobile cloud session cannot retrieve Desktop-local restricted memory
without an allowed bridge/policy.
```

Isolation is a P0 security requirement.

---

## 160. Agent Memory ACL

Suggested scope:

```text
PERSONAL
AGENT_PRIVATE
PROJECT
TEAM
DEPARTMENT
ORGANIZATION
SYSTEM
```

Memory ACL must be checked before retrieval, not only before rendering.

---

## 161. Memory Classification

Add:

```text
PUBLIC_INTERNAL
INTERNAL
CONFIDENTIAL
RESTRICTED
LOCAL_ONLY
```

`LOCAL_ONLY` memory must not sync to cloud by default.

---

## 162. Memory Sync

Do not sync the entire memory database.

Recommended:

```text
Local Agent Memory
      ↓
Selective summary / candidate sync
      ↓
Cloud metadata or governed Company Memory
```

Possible classes:

```text
LOCAL_ONLY
METADATA_ONLY
ENCRYPTED_REPLICA
PROMOTED_KNOWLEDGE
```

---

## 163. Retrieval Architecture

Recommended retrieval:

```text
Query
  ↓
Scope filter
  ↓
Keyword search
+
Semantic search
+
Metadata filters
+
Recency
+
Project relevance
+
Authority
  ↓
Rerank
  ↓
Top memories
```

Avoid vector-only retrieval.

---

## 164. Retrieval Priority

Suggested ranking signals:

```text
Exact project/task match
Authority / scope
Semantic similarity
Keyword match
Recency
Memory confidence
Usage success
Current stage/milestone relevance
```

---

## 165. Raw Evidence Preservation

A memory summary must retain links to source material when practical.

Example:

```text
Memory:
"Build failed due to migration mismatch."

Refs:
- run_id
- tool_call_id
- artifact_id
- log_ref
```

This provides white-box debugging and reduces fabricated continuity.

---

## 166. Memory → Company Knowledge Promotion

Never implement:

```text
Agent Memory
→ automatic official knowledge
```

Use:

```text
Memory Candidate
   ↓
Evaluation
   ↓
Governance
   ↓
Approve
   ↓
Knowledge Object
```

Promotable examples:

```text
Repeated deployment lesson
Confirmed founder preference
Approved technical decision
Validated customer insight
Stable project procedure
```

---

## 167. Memory → SOP / Skill / Playbook Improvement

V12 already has continuous learning.

Add memory as an evidence source:

```text
Repeated successful runs
       ↓
Scenario memories
       ↓
Pattern detection
       ↓
Improvement Proposal
       ↓
SOP / Skill / Playbook candidate
       ↓
Review
       ↓
Activate new version
```

This is a key mCOSA differentiator.

---

## 168. Example: Claude Code Learning Loop

```text
Release attempt #1
→ failure

Release attempt #2
→ workaround

Release attempt #3
→ successful pattern

Agent Memory
→ common solution detected

Improvement Proposal:
"Update Flutter Release SOP"

Human/authorized manager approves

SOP v2 activated
```

---

## 169. Example: Research Agent Learning

```text
Research runs
→ certain sources repeatedly low quality

Agent Memory
→ source reliability pattern

Improvement Proposal
→ change research source ranking

Evaluation
→ compare next runs

If improved
→ update Research SOP/Skill
```

---

## 170. Example: Founder Preference

```text
Founder repeatedly asks:
"Only show top 3 options."

Memory:
Rule-of-3 preference

Candidate profile update

Founder confirms

Official Founder Operating Profile updated
```

---

## 171. Memory Garbage Collection

Agent memory must not grow forever.

Policies:

```text
TTL
last_used
confidence
superseded
duplicate
project archived
user requested forget
```

Actions:

```text
KEEP
COMPACT
MERGE
EXPIRE
DELETE
ARCHIVE
```

---

## 172. Forget / Delete

Provide:

```text
Forget this
Forget this project memory
Forget this agent memory
Delete personal memory
```

Deletion should respect:

- local memory.
- synced replicas.
- indexes.
- derived caches.

Official audit/regulated records remain governed separately.

---

## 173. Memory Evaluation

Measure memory usefulness.

Metrics:

```text
Recall precision
Wrong-memory rate
Stale-memory rate
Cross-project leakage rate
Time-to-resume
Context tokens saved
Task success
Correction rate
Retrieval latency
```

Do not optimize token savings if recall accuracy degrades.

---

## 174. PoC Benchmark A — Claude Code Continuation

Test:

```text
Day 1:
Implement half of a feature.

End session.

Day 2:
"Continue yesterday's implementation."
```

Compare:

```text
Without Agent Memory
vs
With Agent Memory
```

Measure:

```text
Time to resume
Files reread
Tokens/context
Incorrect assumptions
Tests passed
Final task success
```

---

## 175. PoC Benchmark B — Founder Memory

Create multiple sessions containing:

```text
confirmed preference
changed preference
temporary request
contradictory statement
```

Test:

```text
Which preference is current?
Can source be explained?
Can disputed memory be excluded?
```

---

## 176. PoC Benchmark C — Isolation

Create intentionally conflicting memories.

```text
Project A:
Database = PostgreSQL

Project B:
Database = SQLite
```

Ensure retrieval never cross-contaminates when project scope is explicit.

---

## 177. PoC Go / No-Go Gate

Adopt TencentDB Agent Memory beyond PoC only if:

```text
Cross-project leakage = 0 in security test suite
Recall quality acceptable
Resume time improves materially
Context/token pressure decreases
Memory service remains stable
Operational complexity acceptable
Backup/forget works
```

If not:

```text
retain AgentMemoryGateway
replace adapter
```

without domain rewrite.

---

## 178. Security Requirements

Mandatory:

- Bind local memory service to loopback by default.
- Use authentication even for localhost where supported/practical.
- Do not expose memory gateway publicly.
- Do not store plaintext secrets.
- Do not store API keys as memories.
- Enforce organization/project/user/agent scope before retrieval.
- Redact sensitive tool output before memory capture.
- Audit administrative memory access.
- Support delete/forget.
- Encrypt sensitive backups/replicas.

---

## 179. Secrets Exclusion

Memory capture filters must exclude patterns such as:

```text
API keys
access tokens
refresh tokens
passwords
private keys
seed phrases
session cookies
authorization headers
connection strings with credentials
```

Secrets belong in the existing mCOSA Secret Vault, never Agent Memory.

---

## 180. Memory Service Health

Add:

```yaml
agent_memory_health:
  status:
  latency_ms:
  backend:
  index_status:
  last_compaction:
  last_backup:
  last_error:
```

Possible states:

```text
HEALTHY
DEGRADED
UNAVAILABLE
REBUILDING
```

mCOSA must continue operating without Agent Memory.

---

## 181. Graceful Degradation

If memory sidecar is unavailable:

```text
Agent Memory
→ unavailable

mCOSA
→ uses current Project state
→ Knowledge Engine
→ Recent artifacts
→ normal execution continues
```

Agent Memory is an optimization/capability, not a hard dependency for company truth.

---

## 182. Backup

Local Agent Memory backup should be separate from canonical company records.

Recommended:

```text
Scheduled encrypted backup
+
versioned metadata
```

Backup frequency should reflect usefulness, not financial-ledger requirements.

---

## 183. Database Additions in mCOSA

Do not duplicate memory-engine internal tables.

mCOSA only needs integration metadata:

```text
agent_memory_engines
agent_memory_scopes
memory_candidates
memory_promotions
memory_evaluations
memory_sync_records
memory_health_snapshots
```

TencentDB sidecar maintains its own internal schema.

---

## 184. Suggested `memory_candidate`

```yaml
memory_candidate:
  id:
  organization_id:
  project_id:
  source_memory_ref:
  candidate_type:
  statement:
  confidence:
  source_refs: []
  proposed_target:
  status:
  created_by:
  reviewed_by:
  created_at:
  reviewed_at:
```

Status:

```text
PROPOSED
APPROVED
REJECTED
PROMOTED
EXPIRED
```

---

## 185. API Additions

Suggested mCOSA APIs:

```text
GET  /memory/status
POST /memory/recall
POST /memory/search
POST /memory/forget

GET  /memory/candidates
POST /memory/candidates/{id}/approve
POST /memory/candidates/{id}/reject
POST /memory/candidates/{id}/promote

GET  /memory/health
POST /memory/compact
```

Internal worker APIs can be more specialized.

---

## 186. MCP Tools

Recommended:

```text
memory.recall
memory.search
memory.task_context
memory.explain
memory.capture_candidate
```

Administrative tools should not automatically be given to normal agents:

```text
memory.delete
memory.promote
memory.change_scope
```

---

## 187. LiveKit + Agent Memory

Desktop:

```text
LiveKit Local
   ↓
Voice Runtime
   ↓
AgentMemoryGateway
   ↓
Local Memory Sidecar
```

Mobile:

```text
LiveKit Cloud
   ↓
Cloud Voice Agent
   ↓
mCOSA Control Plane
   ↓
Allowed memory request
   ↓
Desktop Device Agent
   ↓
Local Memory Sidecar
```

Do not replicate local private memory into mobile cloud just for convenience.

---

## 188. DeepSeek + Agent Memory

Routine chat flow:

```text
User Message
   ↓
Intent
   ↓
Context Builder
   ├── Current state
   ├── Knowledge
   └── Agent Memory recall
   ↓
DeepSeek
```

Memory query should be intentional and scoped.

---

## 189. Terra + Agent Memory

Strategic analysis package may include:

```text
Approved lessons
Confirmed founder preferences
Relevant previous-cycle experience
```

It must not include unverified memory as factual evidence without marking it as such.

---

## 190. Claude Code + Agent Memory

Recommended integration priority:

```text
P0:
Task continuation

P1:
Context offload

P1:
Known-errors recall

P2:
Cross-project reusable coding lessons

P2:
SOP/Skill improvement proposals
```

---

## 191. Agent Memory + Project OS

Project page can show:

```text
Project Memory

Recent scenarios
Known pitfalls
Previous decisions
Reusable lessons
Pending memory candidates
```

But official strategy/data remains in its existing tabs.

---

## 192. Agent Memory + Portfolio OS

Portfolio memory should focus on:

```text
cross-project conflicts
capacity lessons
dependency patterns
portfolio decisions
repeated resource bottlenecks
```

Do not allow project-private memory to leak into the portfolio unless its policy permits.

---

## 193. Week 13 Integration

Week 13 should consume memory evidence.

```text
12-week execution
   ↓
Scenario memories
   ↓
Weekly reviews
   ↓
Artifacts
   ↓
Week 13
```

Outputs:

```text
Lessons
Memory candidates
SOP candidates
Skill candidates
Playbook improvements
Founder profile updates
```

Then:

```text
Review → Promote / Reject
```

---

## 194. Memory During New 12WY Cycle

When building a new cycle:

```text
Current strategy
+
Current evidence
+
Previous cycle review
+
Promoted company lessons
+
Relevant agent scenarios
```

This allows the new plan to learn from execution without treating every prior conversation as strategy truth.

---

## 195. Automatic Compaction Trigger

Possible triggers:

```text
session ended
context threshold reached
run completed
week review completed
milestone passed
week 13 closed
```

Compaction should be asynchronous and should not block primary work.

---

## 196. Memory Capture Events

Integrate with existing event bus:

```text
conversation.completed
run.completed
artifact.approved
decision.confirmed
milestone.closed
weekly_review.completed
cycle.completed
```

Each event may generate a memory candidate.

---

## 197. Event Capture Policy

Not every event should be memorized.

Suggested filter:

```text
Is it reusable?
Is it surprising?
Did it change behavior?
Did a Human confirm it?
Did it resolve a recurring problem?
Will it help a future task?
```

Otherwise:

```text
do not promote
```

---

## 198. Agent Performance Feedback

Memory can support agent evaluation.

Example:

```text
Repeated failure pattern
→ agent memory
→ evaluation
→ lower autonomy / skill update / model change
```

Agent Memory is evidence; Performance domain remains authoritative.

---

## 199. Operational Cost

Track Agent Memory separately:

```text
disk usage
embedding cost
compaction cost
retrieval latency
background CPU
```

For Desktop OPC, prioritize:

```text
low maintenance
local storage
graceful degradation
```

over complex distributed memory infrastructure.

---

## 200. Memory Engine Configuration

Suggested:

```yaml
memory:
  enabled: true

  engine:
    provider: tencentdb_agent_memory
    deployment: local_sidecar

  storage:
    mode: local

  capture:
    conversations: selective
    tool_results: refs_and_summary
    claude_code: true
    voice: summary_only

  retrieval:
    keyword: true
    semantic: true
    metadata: true

  promotion:
    auto_official_knowledge: false

  security:
    bind_loopback_only: true
    auth_required: true
    secrets_filter: true
```

---

## 201. New Backend Package

Suggested:

```text
backend/app/agent_memory/
  domain/
    contracts.py
    candidates.py
    scopes.py

  application/
    memory_service.py
    promotion_service.py
    evaluation_service.py

  infrastructure/
    tencentdb_agent_memory/
      client.py
      adapter.py
      health.py

  api/
    routes.py
```

Local worker integration:

```text
services/local_worker/memory/
```

---

## 202. Context Builder Contract Update

Before:

```python
build_context(project, user, task)
```

After:

```python
build_context(
    project,
    user,
    task,
    include_knowledge=True,
    include_agent_memory=True,
    memory_budget=...,
)
```

Return structured sections:

```yaml
context:
  authoritative_state:
  approved_knowledge:
  relevant_memory:
  recent_artifacts:
  unresolved_unknowns:
```

Do not flatten everything into one undifferentiated prompt.

---

## 203. Model Context Priority

Recommended:

```text
1. System/policy
2. Current authoritative state
3. Current task/outcome
4. Approved Knowledge
5. Relevant Agent Memory
6. Recent operational artifacts
7. Optional raw refs
```

This hierarchy reduces stale-memory errors.

---

## 204. User-Facing Memory Controls

Settings:

```text
Agent Memory
● Enabled

Remember:
● Work context
● Project lessons
○ Full conversations

Voice memory:
● Summary only

Personal memory:
[View]
[Edit]
[Forget]

Project memory:
[View]
[Compact]
[Clear]
```

Keep advanced memory-engine details out of normal founder UX.

---

## 205. Memory Inspector

For debugging and trust, provide a white-box view.

```text
Memory item
Source
Confidence
Scope
Status
Last used
Related Project
Raw refs
Promoted?
```

Actions:

```text
Confirm
Dispute
Forget
Promote
Restrict scope
```

---

## 206. Why Memory Inspector Matters

mCOSA is an operating system for real company decisions.

A black-box memory system creates risks:

```text
wrong preference
stale project status
cross-project contamination
untraceable recall
```

Therefore inspectability is a product feature, not only a developer tool.

---

## 207. Feature Flags

```text
agent_memory_v12_3
tencentdb_memory_adapter_v12_3
claude_memory_v12_3
memory_context_offload_v12_3
founder_memory_v12_3
deepseek_memory_v12_3
livekit_memory_v12_3
memory_promotion_v12_3
memory_inspector_v12_3
memory_to_sop_v12_3
```

---

## 208. ADRs

Create:

```text
ADR-MEM-001 Agent Memory vs Company Knowledge
ADR-MEM-002 AgentMemoryGateway Abstraction
ADR-MEM-003 TencentDB Agent Memory as Local Sidecar
ADR-MEM-004 PostgreSQL Remains System of Record
ADR-MEM-005 Memory Source-of-Truth Priority
ADR-MEM-006 Memory Isolation and ACL
ADR-MEM-007 Memory Promotion Governance
ADR-MEM-008 Claude Code Memory PoC First
ADR-MEM-009 Memory Context Offload
ADR-MEM-010 Memory → SOP/Skill Improvement
ADR-MEM-011 Voice Transcript Memory Policy
ADR-MEM-012 Memory Graceful Degradation
```

---

## 209. Implementation Phases

### MEM-0 — Adapter Boundary

Implement:

```text
AgentMemoryGateway
TencentDB adapter
health check
feature flag
```

No production prompt integration yet.

### MEM-1 — Claude Code PoC

Implement:

```text
capture run context
end-session compaction
task recall
next-session restore
```

Run benchmarks.

### MEM-2 — Context Offload

Move large tool results to refs/artifacts and keep compact context.

### MEM-3 — Isolation / Security

Implement:

```text
organization
project
agent
human
classification
```

and adversarial leakage tests.

### MEM-4 — DeepSeek Chat

Add selective memory recall.

### MEM-5 — Founder Memory

Add Memory Inspector and confirmed profile candidate flow.

### MEM-6 — LiveKit Voice

Use summary/candidate memory only.

### MEM-7 — Learning

Memory → Improvement Proposal → SOP/Skill/Playbook.

Do not advance beyond MEM-1 if PoC quality is poor.

---

## 210. Claude Code Implementation Instructions

When implementing V12.3:

1. Do not replace mCOSA Knowledge Engine.
2. Do not replace PostgreSQL.
3. Do not let memory engine become authority for Project/Portfolio/OKR/12WY.
4. Introduce `AgentMemoryGateway` before TencentDB-specific code.
5. Run the memory engine as a local sidecar.
6. Bind local service to loopback by default.
7. Enable authentication if supported.
8. Add secrets-redaction filters before capture.
9. Add organization/project/user/agent scope to every recall call.
10. Implement Claude Code PoC before DeepSeek/LiveKit integration.
11. Preserve raw refs for important memories.
12. Do not auto-promote memory into official Knowledge.
13. Do not treat Persona/Profile inference as confirmed.
14. Add forget/delete support.
15. Add graceful fallback when memory service is unavailable.
16. Do not block WorkItem execution on memory compaction.
17. Do not load all memory into context.
18. Use Context Builder budgets.
19. Add leakage/security tests before enabling multi-project use.
20. Add memory evaluation metrics.
21. Keep memory-engine internal DB schema outside mCOSA migrations.
22. Create ADR for any design that makes TencentDB a hard dependency.

---

## 211. V12.3 Acceptance Criteria

V12.3 is accepted when:

1. mCOSA works normally with Agent Memory disabled.
2. TencentDB memory sidecar can start locally.
3. FastAPI/Local Worker accesses it only through `AgentMemoryGateway`.
4. Claude Code can resume a prior task with meaningful compact context.
5. Large tool outputs can be offloaded without losing traceability.
6. Raw refs can be retrieved when needed.
7. Project A memory never appears in Project B under restricted scope.
8. Organization isolation tests pass.
9. Personal founder memory is separated from official company knowledge.
10. Inferred memories are visibly marked.
11. Memory can be confirmed/disputed/forgotten.
12. DeepSeek receives only scoped relevant memory.
13. LiveKit voice does not automatically persist full conversations.
14. Terra analysis does not treat unverified Agent Memory as strategic fact.
15. Agent Memory conflict never overrides authoritative current Project state.
16. Memory sidecar failure does not stop core mCOSA operation.
17. Secrets are excluded from memory capture.
18. Week 13 can generate governed memory/learning candidates.
19. Memory can produce an Improvement Proposal for SOP/Skill/Playbook.
20. PostgreSQL remains System of Record.
21. Knowledge Engine remains canonical governed knowledge.
22. Claude Code benchmark demonstrates measurable improvement before broad rollout.

---

## 212. Recommended First Production Use

The first production-enabled use should be:

```text
Claude Code task continuation
```

not general founder memory.

Reason:

- Clear success criteria.
- Easier benchmark.
- Lower privacy ambiguity.
- High context volume.
- High probability of token/time savings.
- Easy rollback.

Only after success should memory extend to:

```text
DeepSeek chat
→ LiveKit voice
→ departmental agents
→ founder operating profile
```

---

## 213. Final Consolidated Memory Architecture

```text
                         FOUNDER / CEO
                              │
                   ┌──────────┴──────────┐
                   ▼                     ▼
                VOICE                  CHAT
              LiveKit               DeepSeek
                   │                     │
                   └──────────┬──────────┘
                              ▼
                       CONTEXT BUILDER
                              │
             ┌────────────────┼─────────────────┐
             ▼                ▼                 ▼
      AUTHORITATIVE       KNOWLEDGE        AGENT MEMORY
      PROJECT/PORTFOLIO    ENGINE           SIDECAR
          PostgreSQL       Markdown/PG      TencentDB
             │                │                 │
             │                │          Working / L0-L3
             │                │          Context Offload
             └────────────────┼─────────────────┘
                              ▼
                        CONTEXT PACKAGE
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
           DeepSeek          Terra         Claude Code
                              │                │
                              ▼                ▼
                          STRATEGY            WORK
                              │                │
                              └────────┬───────┘
                                       ▼
                                  ARTIFACTS
                                       │
                                  EVALUATION
                                       │
                                       ▼
                                MEMORY CANDIDATE
                                       │
                                   GOVERNANCE
                                ┌──────┴──────┐
                                ▼             ▼
                            DISCARD        PROMOTE
                                               │
                                               ▼
                                  KNOWLEDGE / SOP / SKILL
```

---

## 214. V12.3 North-Star Rule

> **Agent Memory remembers experience. Knowledge records truth. PostgreSQL records company state. Strategy decides direction. Hybrid Workforce executes.**

This boundary must remain explicit throughout implementation.

---

## 215. Final Recommendation

Adopt TencentDB Agent Memory as:

```text
mCOSA Agent Memory Engine
```

with these constraints:

```text
Local sidecar
Provider adapter
Claude Code PoC first
Strict scope isolation
No secrets
No automatic official knowledge
No System-of-Record responsibility
White-box memory inspection
Graceful degradation
Memory → Improvement Proposal
```

The expected product benefit is not simply “longer memory.”

The goal is:

> **mCOSA agents can continue long-running work with less repeated context, retain useful operating experience, and convert validated experience into better company knowledge, SOPs, skills and playbooks without contaminating authoritative company state.**

---

## 216. Reference

Primary project reviewed for this integration:

- TencentCloud/TencentDB-Agent-Memory  
  https://github.com/TencentCloud/TencentDB-Agent-Memory

Implementation must pin/test a specific compatible release during PoC rather than automatically tracking the repository's latest branch.
