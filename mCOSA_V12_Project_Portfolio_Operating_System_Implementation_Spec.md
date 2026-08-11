# mCOSA V12 — Project & Portfolio Operating System
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
