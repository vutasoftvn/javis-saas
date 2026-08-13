# COSA V13.1 — Company Runtime Adjustment
## Incremental Implementation Specification for an Already-Deployed V13

**Product:** COSA / mCOSA — Company Operating System AI  
**Baseline:** V13 Focused Company Cycle OS already implemented  
**Purpose:** Deepen V13 execution by adding a Company Runtime inspired by the strongest OpenOPC patterns  
**Implementation style:** Additive, feature-flagged, non-destructive  
**Do not do:** Do not integrate OpenOPC as a production runtime dependency  
**Preserve:** Cycle, OKRs, 12WY, Weekly Mission, five AI Functions, LiveKit, Finance TT58, Claude Code, Learning  
**Add:** Intent classification, Quick Task vs Company Work, WorkItem state machine, dependency DAG, review/rework, structured handoff, blockers, Needs You, checkpoint/resume, role attribution, experience and skills  

---

# 1. Executive Decision

V13 is already deployed. V13.1 must therefore **not restart the architecture**.

The adjustment is:

```text
V13:
Cycle
→ OKRs
→ 12WY
→ Weekly Mission
→ AI Functions
→ Result
→ Review
→ Learning
→ Week 13

V13.1:
Weekly Mission
→ Company Runtime
→ AI Functions
→ Review/Rework
→ Result
→ Attribution
→ Learning
```

The new `CompanyRuntimeManager` sits between planning and execution.

---

# 2. What to Learn from OpenOPC

Adopt these ideas:

```text
Self-Built
→ choose/reuse/create suitable workers

Self-Run
→ WorkItem lifecycle
→ dependency DAG
→ delegation
→ manager review
→ rework
→ escalation

Self-Grown
→ trace outcome to role
→ extract lessons
→ reuse experience
→ promote repeated lessons into skills/checklists/playbooks
```

Translate to COSA:

```text
PLAN
RUN
LEARN
```

OpenOPC is a **reference architecture**, not a new runtime layer to embed.

---

# 3. Why This Matters for COSA

Without V13.1, V13 can still feel like:

```text
Cycle planner
+
five AI function assistants
```

With V13.1:

```text
Founder
→ COSA Chief of Staff
→ managed runtime
→ five functions collaborate through work
→ blockers are routed
→ outputs are reviewed
→ only exceptions reach founder
→ lessons improve future execution
```

This is the difference between an AI planning product and an AI company operating runtime.

---

# 4. Do Not Clone OpenOPC

Do not implement:

```text
COSA
→ OpenOPC runtime
→ OpenOPC tasks
→ OpenOPC agents
→ OpenOPC approvals
```

COSA already owns:

```text
WorkItem
Run
Artifact
Approval
Hybrid Workforce
Policy Engine
LiveKit
Claude Code Worker
Finance
Learning
```

A second runtime would create duplicate truth.

Rule:

> **Adopt patterns; preserve COSA ownership.**

---

# 5. Company Runtime Position

```text
                    FOUNDER
                       │
                    LiveKit
                       │
                       ▼
                     COSA
                AI Chief of Staff
                       │
                       ▼
                Work Intent Router
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
       CHAT        QUICK TASK    COMPANY WORK
     DeepSeek          │             │
                       ▼             ▼
                Single WorkItem   Current Cycle
                                     │
                                    OKRs
                                     │
                                    12WY
                                     │
                                Weekly Mission
                                     │
                                     ▼
                           CompanyRuntimeManager
                                     │
                              Decompose + DAG
                                     │
             ┌─────────┬─────────┬─────────┬─────────┐
             ▼         ▼         ▼         ▼         ▼
           Legal   Marketing    Sales      Tech     Finance
                                             │
                                         Claude Code
             └─────────┴─────────┴─────────┴─────────┘
                                     │
                                     ▼
                              Review / Integrate
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
                        Accept     Rework    Escalate
                          │                     │
                          ▼                     ▼
                        Result               Needs You
                          │
                          ▼
                      Evaluation
                          │
                          ▼
                    Role Attribution
                          │
                          ▼
                        Lesson
                          │
                   repeated pattern?
                    ┌─────┴─────┐
                    ▼           ▼
                  retain    Improvement
                              Candidate
```

---

# 6. New Runtime Service

Create:

```text
CompanyRuntimeManager
```

Responsibilities:

```text
classify work intent
decompose Company Work
create WorkItems
create Work Contracts
build dependency DAG
determine runnable WorkItems
assign Function
resolve executor
track lifecycle
route blockers
create structured handoffs
request review
request rework
integrate artifacts
escalate exceptions
checkpoint runtime
resume runtime
trigger evaluation
trigger learning
```

It does not replace V10/V13 execution services.

---

# 7. P0 — Work Intent Classifier

Add:

```text
WorkIntentClassifier
```

Intent types:

```text
CHAT
QUICK_TASK
COMPANY_WORK
CYCLE_CHANGE
STRATEGIC
APPROVAL
```

Routing:

```text
CHAT
→ DeepSeek

QUICK_TASK
→ one Function / executor

COMPANY_WORK
→ CompanyRuntimeManager

CYCLE_CHANGE
→ Cycle Planner
→ Terra if material

STRATEGIC
→ Terra strategic workflow

APPROVAL
→ existing Approval/Policy services
```

---

# 8. Quick Task vs Company Work

This distinction prevents V13.1 from becoming bureaucratic.

## Quick Task

Examples:

```text
Fix a typo
Draft one follow-up email
Check Claude Code status
Record a software expense
Summarize a customer call
```

Flow:

```text
Intent
→ Function
→ WorkItem
→ Executor
→ Result
```

No decomposition or DAG unless needed.

## Company Work

Examples:

```text
Prepare beta launch
Get 10 beta users
Reduce monthly burn
Complete beta legal readiness
Close Week 6 with all critical milestones accepted
```

Flow:

```text
Intent
→ Cycle / Weekly Mission
→ CompanyRuntimeManager
→ multi-function decomposition
→ DAG
→ execution
→ integration
```

---

# 9. P0 — WorkItem State Machine

Reuse existing WorkItem entity.

Normalize states:

```text
PLANNED
WAITING_DEPENDENCY
READY
RUNNING
WAITING_HUMAN
WAITING_AGENT
REVIEW
REWORK
BLOCKED
ESCALATED
DONE
FAILED
CANCELLED
```

Preferred transition:

```text
PLANNED
   ↓
WAITING_DEPENDENCY / READY
   ↓
RUNNING
   ↓
REVIEW
   ├── DONE
   ├── REWORK
   ├── BLOCKED
   └── ESCALATED
```

---

# 10. WorkItem State Semantics

```text
PLANNED
Defined but not runnable.

WAITING_DEPENDENCY
Upstream work is incomplete.

READY
Can be executed.

RUNNING
Executor is actively working.

WAITING_HUMAN
Founder/human input or approval required.

WAITING_AGENT
Waiting for another Function/worker.

REVIEW
Output exists but has not been accepted.

REWORK
Output failed review and must be revised.

BLOCKED
Cannot progress due to missing input/capability.

ESCALATED
Requires founder/expert/authorized decision.

DONE
Output accepted.

FAILED
Execution failed and automatic recovery is unavailable.

CANCELLED
Stopped intentionally.
```

---

# 11. State Transition Guard

Do not allow arbitrary state mutation.

Create:

```text
WorkItemStateService
```

Responsibilities:

```text
validate transition
record actor
record timestamp
record reason
emit domain event
trigger dependency reevaluation
trigger checkpoint
```

Example:

```text
RUNNING → DONE
```

must normally pass:

```text
RUNNING → REVIEW → DONE
```

for meaningful WorkItems.

---

# 12. P0 — Dependency DAG

Add simple WorkItem-level dependencies.

```yaml
work_item_dependency:
  id:
  organization_id:
  cycle_id:
  weekly_mission_id:
  upstream_work_item_id:
  downstream_work_item_id:
  dependency_type:
  status:
```

Types:

```text
BLOCKS
REQUIRES_OUTPUT
REQUIRES_APPROVAL
REQUIRES_DECISION
REQUIRES_DOCUMENT
```

---

# 13. DAG Example — Beta Launch

```text
Legal Terms Review
        │
        ├─────────────┐
        ▼             ▼
Marketing Copy    Sales Proposal
        │
        ▼
Tech Landing Page
        │
        ▼
Marketing Launch
        │
        ▼
Sales Outreach
        │
        ▼
Finance Receivable
```

Independent work should run in parallel when safe.

---

# 14. DAG Execution Rules

Runtime must:

```text
1. Compute READY WorkItems.
2. Keep blocked children in WAITING_DEPENDENCY.
3. Re-evaluate downstream work whenever an upstream state changes.
4. Parallelize independent safe work.
5. Stop consequential external work at approval boundaries.
6. Detect circular dependencies before activation.
7. Record dependency failure reasons.
```

---

# 15. P0 — Work Contract

Every meaningful WorkItem requires a clear outcome definition.

```yaml
work_contract:
  id:
  work_item_id:
  desired_outcome:
  acceptance_criteria: []
  required_artifacts: []
  reviewer_id: optional
  review_type:
  linked_kr_ids: []
  validation_rules: []
```

Example:

```text
WorkItem:
Launch beta landing page

Desired outcome:
A working public beta landing page.

Acceptance:
- staging/production URL available
- mobile responsive
- CTA works
- analytics event fires
- legal links are correct
- reviewer accepts
```

---

# 16. P0 — Review / Rework / Integrate

Outputs are not DONE merely because an agent stopped.

Flow:

```text
Output
  ↓
REVIEW
  ├── ACCEPT
  ├── REWORK
  ├── INTEGRATE
  └── ESCALATE
```

Reviewers can be:

```text
Function Lead
COSA Chief of Staff
Founder
External Expert
Deterministic Validator
```

---

# 17. Review Types

```text
SELF_CHECK
FUNCTION_LEAD_REVIEW
COSA_REVIEW
FOUNDER_REVIEW
EXPERT_REVIEW
DETERMINISTIC_VALIDATION
```

Examples:

```text
Tech
→ tests/build validator
→ reviewer

Finance
→ deterministic accounting validation
→ accountant/founder review where required

Marketing
→ COSA review
→ founder approval before external publish

Legal
→ expert/founder review for material legal matters
```

---

# 18. Work Review Entity

```yaml
work_review:
  id:
  work_item_id:
  reviewer_type:
  reviewer_id:
  result:
  feedback:
  evidence_refs: []
  created_at:
```

Results:

```text
ACCEPTED
REWORK_REQUIRED
ESCALATED
```

---

# 19. Rework Loop

```text
REVIEW
  ↓
REWORK_REQUIRED
  ↓
REWORK
  ↓
RUNNING
  ↓
REVIEW
```

Track:

```text
rework_count
review_feedback
new_artifact_refs
```

Use a configurable maximum rework count before escalation.

---

# 20. P0 — Structured Handoff

Functions must collaborate through structured handoffs rather than unrestricted agent chat.

```yaml
handoff:
  id:
  organization_id:
  cycle_id:
  weekly_mission_id:
  from_function:
  to_function:
  source_work_item_id:
  target_work_item_id: optional
  handoff_type:
  requested_action:
  artifact_refs: []
  decision_refs: []
  due_at:
  status:
```

Types:

```text
REQUEST_INPUT
TRANSFER_ARTIFACT
ASK_REVIEW
ASK_DECISION
REPORT_BLOCKER
HANDOFF_TO_NEXT_FUNCTION
```

---

# 21. Handoff Examples

```text
Marketing → Sales
ICP + messaging + qualified-lead definition

Sales → Finance
Won deal + amount + payment terms

Finance → Legal
Accounting/revenue ambiguity + source documents

Tech → Marketing
Landing page URL + deployment status

Legal → Marketing
Approved terms/privacy copy
```

---

# 22. P0 — Blocker Model

Add a first-class blocker.

```yaml
blocker:
  id:
  work_item_id:
  cycle_id:
  weekly_mission_id:
  blocker_type:
  description:
  requested_capability:
  assigned_function:
  status:
  resolution_artifact_id: optional
  escalated_to: optional
  created_at:
  resolved_at: optional
```

Status:

```text
OPEN
ROUTED
RESOLVING
RESOLVED
ESCALATED
CANCELLED
```

---

# 23. Blocker Router

Add:

```text
BlockerRouter
```

Examples:

```text
pricing/margin
→ Finance + Sales

contract/legal
→ Legal

technical implementation
→ Tech

campaign/message
→ Marketing

customer response
→ Sales

founder-only strategic decision
→ Needs You
```

Founder receives only blockers that internal Functions cannot resolve safely.

---

# 24. P0 — Needs You Queue

Create a unified founder exception queue.

```text
NEEDS YOU
```

Sources:

```text
approval
decision
blocked work
missing information
high-risk action
finance exception
legal exception
cycle change
recovery ambiguity
```

Entity:

```yaml
needs_you_item:
  id:
  organization_id:
  cycle_id:
  source_type:
  source_id:
  priority:
  reason:
  requested_action:
  due_at:
  status:
```

Status:

```text
OPEN
SNOOZED
RESOLVED
CANCELLED
```

---

# 25. Needs You UX

Home:

```text
Needs You: 3

1. Approve launch message
2. Confirm SaaS expense classification
3. Choose pricing option
```

LiveKit:

> “Anh có 3 việc cần quyết định. Việc quan trọng nhất là duyệt thông điệp launch.”

---

# 26. P0 — Runtime Checkpoint

COSA must survive:

```text
desktop sleep
app restart
worker crash
network interruption
LiveKit disconnect
Claude Code long run
```

Add:

```yaml
runtime_checkpoint:
  id:
  organization_id:
  cycle_id:
  weekly_mission_id:
  sequence:
  work_item_states:
  dependency_state:
  pending_approvals:
  pending_needs_you:
  active_executors:
  checkpoint_reason:
  created_at:
```

---

# 27. Checkpoint Reasons

```text
PERIODIC
WORK_ITEM_STATE_CHANGE
APPROVAL_CREATED
BEFORE_EXTERNAL_ACTION
SESSION_END
DEVICE_SLEEP
ERROR_RECOVERY
```

Do not store hidden chain-of-thought.

Store operational state only.

---

# 28. P0 — Runtime Resume

On restart:

```text
1. Load active Cycle.
2. Load Weekly Mission.
3. Restore WorkItem states.
4. Restore dependency graph.
5. Refresh live worker status.
6. Mark orphaned RUNNING tasks as recovery-required.
7. Rebuild Needs You.
8. Resume safe work.
9. Ask founder when recovery is ambiguous.
```

No duplicate WorkItems.

---

# 29. Recovery State

If needed, add:

```text
RECOVERY_NEEDED
```

as an internal runtime marker, not necessarily a public WorkItem state.

The resolver decides:

```text
resume
retry
mark failed
wait for device
ask founder
```

---

# 30. P0 — Work Inspector

Add a transparent operational view.

Show:

```text
Outcome
Function
Executor
Status
Dependencies
Current Run/Tool
Artifacts
Reviews
Handoffs
Blockers
Approvals
Timeline
Learning notes
```

Do not expose raw chain-of-thought.

---

# 31. Work Inspector Example

```text
WorkItem
Launch landing page

Outcome
Beta waitlist page live

Status
REVIEW

Dependencies
DONE — Legal terms
DONE — Tech deploy
WAITING — Analytics validation

Artifacts
- Landing page URL
- Copy doc
- Screenshot

Reviews
- Marketing self-check passed
- COSA review pending

Blockers
None

Learning
Possible lesson: beta application CTA outperforms waitlist CTA
```

---

# 32. New Data Model — Additive Only

Add:

```text
work_item_dependencies
work_contracts
work_reviews
handoffs
blockers
needs_you_items
runtime_checkpoints
contribution_evaluations
agent_experiences
function_skills
cycle_grants
lesson_candidates
improvement_candidates
```

Do not drop V13/V12 tables.

---

# 33. P1 — ExecutorResolver

After P0 stabilizes, add:

```text
ExecutorResolver
```

Inputs:

```text
Function
Work type
Required capability
Risk
Human-required flag
Available workers
Available tools
Experience profile
Current load
Cycle policy
```

Outputs:

```text
Human
Persistent Function Lead
Ephemeral Specialist
Claude Code
Automation
External Expert
```

---

# 34. P1 — Persistent vs Ephemeral

Persistent Function Leads:

```text
Legal Lead
Marketing Lead
Sales Lead
Tech Lead
Finance Lead
```

Ephemeral examples:

```text
SEO Researcher
Contract Reviewer
Lead Researcher
UI Tester
Finance Reconciliation Specialist
```

Lifecycle:

```text
create for WorkItem
→ execute
→ artifact
→ evaluation
→ close
```

Do not expose a complex org chart.

---

# 35. P1 — Cycle Grants

Reduce repeated low-risk approvals.

```yaml
cycle_grant:
  id:
  cycle_id:
  actor_id:
  capability:
  scope:
  max_risk:
  max_amount:
  max_frequency:
  expires_at:
  granted_by:
```

Examples:

```text
Marketing AI:
may publish already-approved posts during this Cycle

Tech:
may run local tests automatically

Finance:
may classify recurring low-risk software expenses
```

Never use grants to bypass critical financial/legal controls.

---

# 36. P1 — Contribution Evaluation

After accepted WorkItem:

```yaml
contribution_evaluation:
  id:
  work_item_id:
  workforce_member_id:
  function:
  outcome:
  result_quality:
  acceptance_status:
  evidence_refs: []
  lesson_refs: []
  created_at:
```

Purpose:

```text
attribute outcomes
improve execution
update experience
generate lessons
```

Not for leaderboard gamification.

---

# 37. P1 — Agent Experience

Use PostgreSQL first.

```yaml
agent_experience:
  id:
  agent_id:
  function:
  successful_patterns: []
  known_failures: []
  domain_experience: []
  preferred_tools: []
  last_updated:
```

TencentDB Agent Memory remains optional/experimental in V13.1.

---

# 38. P1 — Function Skills

Add built-in internal skills.

```yaml
function_skill:
  id:
  function:
  name:
  description:
  version:
  status:
  source:
  activation_rules:
```

Examples:

```text
Legal
- Contract Review
- Privacy Checklist
- Beta Legal Readiness

Marketing
- ICP Research
- Launch Message
- Campaign Analysis

Sales
- Lead Qualification
- Proposal Draft
- Follow-up

Tech
- Claude Code Feature
- Bug Fix
- Test/Build

Finance
- TT58 Transaction Classification
- Reconciliation
- Period Checklist
```

---

# 39. Function Skill States

```text
DRAFT
ACTIVE
DEPRECATED
DISABLED
```

No skill marketplace in V13.1.

---

# 40. Learning Flow Upgrade

V13:

```text
Weekly Review
→ Lesson
```

V13.1:

```text
WorkItem
  ↓
Outcome
  ↓
Review
  ↓
Contribution Evaluation
  ↓
Lesson Candidate
  ↓
Confirmed Lesson
  ↓
Repeated?
  ├── No → retain
  └── Yes → Improvement Candidate
```

Weekly Review becomes a synthesis layer rather than the first place learning is created.

---

# 41. Lesson Candidate

```yaml
lesson_candidate:
  id:
  organization_id:
  cycle_id:
  source_work_item_id:
  function:
  observation:
  evidence_refs: []
  proposed_lesson:
  confidence:
  status:
```

States:

```text
PROPOSED
CONFIRMED
REJECTED
APPLIED
SUPERSEDED
```

---

# 42. Improvement Candidate

```yaml
improvement_candidate:
  id:
  organization_id:
  function:
  candidate_type:
  title:
  rationale:
  evidence_refs: []
  proposed_change:
  status:
```

Types:

```text
SKILL
CHECKLIST
PLAYBOOK
SOP
ROUTING_RULE
VALIDATION_RULE
```

States:

```text
PROPOSED
APPROVED
REJECTED
IMPLEMENTED
MEASURED
```

---

# 43. Function Learning Examples

## Legal

```text
Repeated beta launches require:
privacy review + terms + AI disclaimer

→ Beta Launch Legal Checklist candidate
```

## Marketing

```text
High engagement
Low signup

→ CTA mismatch lesson
→ new campaign rule candidate
```

## Sales

```text
Qualified leads convert better after quantified pain discovery

→ qualification skill improvement
```

## Tech

```text
Repeated build failures from migration mismatch

→ pre-build migration checklist
```

## Finance

```text
Recurring vendor repeatedly classified identically

→ classification rule candidate
```

Finance deterministic services remain authoritative.

---

# 44. P2 — Keep Disabled

Do not implement now:

```text
OpenOPC runtime dependency
Talent marketplace
Skill marketplace
Company package marketplace
Animated office
Large auto-generated org chart
Full multi-channel ecosystem
Agent free-chat rooms
```

Feature flags:

```yaml
openopc_runtime_dependency: false
talent_marketplace: false
skill_marketplace: false
company_package_marketplace: false
office_animation_ui: false
agent_free_chat: false
```

---

# 45. External Channel Gateway — Stub Only

Optional abstraction:

```text
ExternalChannelGateway
```

Default:

```text
disabled
```

Future:

```text
Telegram
Email
Zalo
Slack
```

Security:

```text
deny-by-default
explicit allowlist
policy checks
idempotency
```

---

# 46. LiveKit Runtime Integration

LiveKit remains the realtime interface.

New questions/commands:

```text
What is blocked?
What needs me?
Why is Marketing waiting?
Resume work.
Show this WorkItem.
Approve this.
Rework this output.
What depends on this task?
```

Voice calls structured COSA services, not direct agent chats.

---

# 47. LiveKit + DAG Example

Founder:

> “Tại sao Marketing chưa launch?”

COSA:

> “Marketing đang chờ Legal Terms được duyệt. WorkItem LEGAL-12 đang ở REVIEW và nằm trong Needs You.”

This is the target realtime operating experience.

---

# 48. LiveKit + Rework

Founder:

> “Bài này chưa đúng thông điệp, làm lại.”

Flow:

```text
LiveKit
→ work.review
→ REWORK_REQUIRED
→ WorkItem REWORK
→ Marketing executor reruns
→ new Artifact
→ REVIEW
```

---

# 49. Finance Runtime Integration

Preserve V13 TT58 architecture.

Add:

```text
Finance blockers
Finance handoffs
Finance review contracts
Finance exception → Needs You
Recurring classification lessons
Cycle Grants for safe deterministic routines
```

Examples:

```text
Sales win
→ Finance receivable

Marketing spend
→ Finance budget variance

Missing accounting document
→ handoff or Needs You

Recurring vendor
→ classification improvement candidate
```

---

# 50. Finance Governance Remains Strong

V13.1 does not weaken:

```text
TT58 accounting support ≠ tax engine

Finance AI ≠ licensed accountant

LLM ≠ authoritative calculation engine

statutory output
→ deterministic validation
→ Human/professional review when material

payment
→ explicit authorization
```

---

# 51. Legal Runtime Integration

Add:

```text
Legal blocker routing
Legal handoffs
Legal work contracts
Legal review/rework
Legal checklist candidates
Expert escalation
```

Material legal uncertainty always escalates.

---

# 52. Marketing Runtime Integration

Add:

```text
campaign work contracts
Marketing→Sales structured handoff
review/rework
campaign outcome attribution
message/channel lessons
```

Drafting content does not automatically mean DONE.

---

# 53. Sales Runtime Integration

Add:

```text
lead work contracts
Marketing→Sales handoff
Sales→Finance handoff
Sales→Legal handoff
objection learning
conversion attribution
```

Sales completion is contract-specific.

---

# 54. Tech Runtime Integration

Keep existing Claude Code Worker.

Add:

```text
work contract
review/rework
build/test validation
checkpoint/resume
technical lesson candidates
```

Do not create a new coding agent runtime.

---

# 55. AI Tool Registry

Enable:

```text
runtime.classify_intent
runtime.decompose_work
runtime.get_status
runtime.get_dag
runtime.get_blockers
runtime.get_needs_you
runtime.resolve_blocker
runtime.create_handoff
runtime.request_review
runtime.request_rework
runtime.checkpoint
runtime.resume

work.get_inspector
work.create_contract
work.review
work.rework

learning.evaluate_contribution
learning.create_lesson_candidate
learning.create_improvement_candidate
```

Disable:

```text
openopc.*
marketplace.*
office_ui.*
agent_free_chat.*
```

---

# 56. API Sketch

```text
POST /runtime/classify-intent
POST /runtime/decompose
GET  /runtime/status
GET  /runtime/dag
POST /runtime/checkpoint
POST /runtime/resume

GET  /work-items/{id}/inspector
POST /work-items/{id}/contract
POST /work-items/{id}/review
POST /work-items/{id}/rework

POST /handoffs
GET  /handoffs

POST /blockers
GET  /blockers
POST /blockers/{id}/resolve

GET  /needs-you
POST /needs-you/{id}/resolve
POST /needs-you/{id}/snooze

POST /learning/contribution-evaluations
POST /learning/lesson-candidates
POST /learning/improvement-candidates
```

---

# 57. FastAPI Structure

```text
app/company_runtime/
  domain/
    intent.py
    work_state.py
    dependencies.py
    contracts.py
    reviews.py
    handoffs.py
    blockers.py
    needs_you.py
    checkpoints.py

  application/
    runtime_manager.py
    intent_classifier.py
    decomposition_service.py
    dependency_service.py
    review_service.py
    blocker_router.py
    needs_you_service.py
    checkpoint_service.py
    executor_resolver.py

  api/
    routes.py
```

Extend existing:

```text
app/work/
app/learning/
app/functions/
app/realtime/
```

Do not duplicate V10/V13 WorkItem logic.

---

# 58. Flutter Structure

```text
lib/features/company_runtime/
  domain/
    runtime_status.dart
    work_state.dart
    dependency.dart
    blocker.dart
    handoff.dart
    needs_you_item.dart

  presentation/
    runtime_status_card.dart
    work_inspector_page.dart
    needs_you_panel.dart
    dependency_view.dart
```

Update:

```text
Home
Cycle
Weekly Mission
AI Team
LiveKit controllers
```

---

# 59. Visible UI Changes

Add only:

```text
Runtime Status
Needs You
Blocked Work
Work Inspector
Work state badge
Dependency hints
Handoff history
Lesson Candidate review
```

Do not expose:

```text
OpenOPC office simulation
Marketplace
Large org builder
Agent free chat
```

---

# 60. Home Dashboard Update

Example:

```text
WEEK 5 / 13

MISSION
Launch beta waitlist

RUNTIME
8 work items
3 done
2 running
2 waiting
1 needs you

NEEDS YOU
Approve Legal Terms

TOP BLOCKER
Marketing campaign waits on Legal Terms

TOP 3
1. Approve Terms
2. Test signup
3. Review first 5 leads
```

---

# 61. AI Team Page

Each Function shows:

```text
State
Current WorkItems
Blocked?
Waiting Review?
Latest Result
Latest Lesson
```

Example:

```text
Marketing
RUNNING

2 WorkItems
Waiting on Legal

Latest lesson:
Founder pain-point posts outperform feature posts
```

---

# 62. Migration from Implemented V13

Use incremental migration only.

## Step 1 — Inventory

Inspect current:

```text
WorkItem statuses
Run lifecycle
Approval lifecycle
Weekly Mission compiler
Function routing
Learning entities
LiveKit commands
```

## Step 2 — Mapping

Create explicit mapping from old state model to V13.1 state model.

## Step 3 — Additive migrations

Create new tables/columns only.

## Step 4 — Feature flag runtime

Start:

```yaml
company_runtime_v13_1: false
```

## Step 5 — Developer Mode

Enable only for a test workspace.

## Step 6 — One Weekly Mission

Run V13.1 runtime on one real/test Weekly Mission.

## Step 7 — Enable P0

Only after migrations and compatibility tests pass.

## Step 8 — Enable P1

Only after runtime stability is measured.

---

# 63. Feature Flags

```yaml
features:

  company_runtime_v13_1: true

  work_intent_classifier_v13_1: true
  quick_task_v13_1: true
  company_work_v13_1: true
  workitem_state_machine_v13_1: true
  dependency_dag_v13_1: true
  work_contract_v13_1: true
  review_rework_v13_1: true
  structured_handoff_v13_1: true
  structured_blocker_v13_1: true
  needs_you_queue_v13_1: true
  runtime_checkpoint_v13_1: true
  work_inspector_v13_1: true

  executor_resolver_v13_1: false
  ephemeral_specialist_v13_1: false
  cycle_grants_v13_1: false
  role_attribution_v13_1: false
  agent_experience_v13_1: false
  function_skills_v13_1: false

  openopc_runtime_dependency: false
  talent_marketplace: false
  skill_marketplace: false
  company_package_marketplace: false
  office_animation_ui: false
  agent_free_chat: false
```

---

# 64. P0 Implementation Order

Recommended:

```text
1. WorkItem State Machine
2. Work Contract
3. Review/Rework
4. Dependency DAG
5. Needs You
6. Blocker
7. Handoff
8. Checkpoint/Resume
9. Work Inspector
10. Intent Classifier
11. CompanyRuntimeManager
```

Do not implement all in parallel.

---

# 65. P1 Implementation Order

```text
1. ExecutorResolver
2. Ephemeral Specialists
3. Cycle Grants
4. Contribution Evaluation
5. Role Attribution
6. Agent Experience
7. Function Skills
8. Improvement Candidates
```

---

# 66. Acceptance Criteria — P0

P0 is complete when:

1. Existing V13 Cycles still work.
2. Existing WorkItems remain valid.
3. Old states map safely to V13.1 states.
4. Weekly Mission can decompose into WorkItems.
5. WorkItems can have dependencies.
6. Only READY work starts.
7. WorkItem output enters REVIEW.
8. Review supports ACCEPT and REWORK.
9. Rework produces a new reviewed output.
10. Blocked WorkItem creates Blocker.
11. Blocker can route to another Function.
12. Founder sees unresolved exception in Needs You.
13. Runtime checkpoint stores operational state.
14. Runtime resumes without duplicate work.
15. Work Inspector displays dependency/review/artifact state.
16. LiveKit can answer runtime status questions.
17. No OpenOPC production dependency is introduced.
18. Existing Policy Engine remains authoritative.
19. Finance and Legal controls are preserved.
20. No existing V13 feature is removed.

---

# 67. Acceptance Criteria — P1

P1 is complete when:

1. ExecutorResolver chooses Human/AI/Claude Code/Automation/Expert.
2. Ephemeral worker can execute one WorkItem and close.
3. Cycle Grant reduces repeat approvals for low-risk work.
4. Accepted WorkItems produce contribution evaluation.
5. Lessons are attributable to Function/worker.
6. Confirmed lessons update experience.
7. Repeated lessons create improvement candidates.
8. Function Skills can be versioned.
9. Skills remain internal; no marketplace.
10. Finance deterministic engine remains source of numeric truth.

---

# 68. Finance Acceptance Criteria

1. Finance WorkItem uses a Work Contract.
2. Finance exceptions can create Needs You.
3. Sales win can hand off to Finance.
4. Missing source document can create a Blocker.
5. Finance uncertainty can escalate to Legal/accountant review.
6. Recurring classifications can create lessons.
7. Deterministic TT58 validation runs before statutory review.
8. WorkItem DONE requires acceptance criteria.
9. No autonomous payment is introduced.
10. No autonomous tax filing is introduced.

---

# 69. Legal Acceptance Criteria

1. Legal WorkItems support REVIEW.
2. Marketing/Sales/Finance can route Legal blockers.
3. Legal can return structured artifact/handoff.
4. Material uncertainty escalates.
5. Repeated legal patterns can create checklist candidates.
6. No autonomous final legal determination.

---

# 70. Marketing & Sales Acceptance Criteria

1. Marketing→Sales handoff is structured.
2. Campaign WorkItem has outcome criteria.
3. Sales pipeline change can update relevant KR.
4. Sales→Finance handoff exists.
5. Sales→Legal handoff exists.
6. Lessons distinguish engagement, qualified demand and conversion.

---

# 71. Tech Acceptance Criteria

1. Tech still uses existing Claude Code Worker.
2. Tech WorkItem can enter REVIEW.
3. Build/test results can satisfy deterministic validation.
4. Rework can call Claude Code again.
5. Checkpoint protects long-running task state.
6. Tech lessons can create checklist/skill candidates.

---

# 72. Model Routing

Preserve V13 routing:

```text
DeepSeek
→ routine chat
→ intent classification
→ summaries
→ simple routing

Terra
→ Cycle planning
→ major replan
→ Week 13 deep synthesis

Claude Code
→ coding execution

Deterministic services
→ finance calculations
→ accounting validations
→ test/build validations where possible

LiveKit
→ realtime interaction
```

CompanyRuntimeManager should not use Terra for ordinary WorkItem routing.

---

# 73. Runtime Context Boundary

Runtime context should include:

```text
Current Cycle
Current Objectives/KRs
Current Weekly Mission
Available Functions
Enabled tools
Current WorkItems
Dependencies
Policies
Recent confirmed lessons
```

Exclude by default:

```text
all old chat history
all V12 advanced strategy
raw accounting ledger
secrets
disabled tools
unbounded agent logs
```

---

# 74. Security

All external/consequential actions remain behind Policy Engine.

Examples:

```text
publish campaign
send binding proposal
deploy production
close accounting period
change accounting regime
make payment
submit legal/tax filing
```

Company Runtime cannot bypass governance.

---

# 75. Deny-by-Default Remote Commands

If Telegram/Zalo/Email are enabled later:

```text
unknown sender
→ deny

unverified sender
→ deny

unsupported command
→ deny

high-risk command
→ approval
```

All create-work commands need idempotency.

---

# 76. Idempotency

Every voice/chat command that can create work receives:

```text
command_id
idempotency_key
```

Prevent duplicates from:

```text
network retry
LiveKit reconnect
mobile retry
worker restart
```

---

# 77. Observability

Track:

```text
work_items_created
work_items_completed
work_items_reworked
work_items_escalated
blocked_items
mean_blocker_resolution_time
needs_you_count
founder_decisions
handoff_count
checkpoint_count
resume_success_rate
runtime_error_count
cycle_progress
```

---

# 78. Founder Attention Metrics

V13.1 should reduce:

```text
random interruptions
repeat approvals
manual routing
status checking
task resumption overhead
```

Keep the V13 north-star:

> **Accepted business outcomes per hour of founder attention.**

---

# 79. Golden Scenario 1 — Beta Launch

Weekly Mission:

```text
Prepare beta launch.
```

Runtime decomposition:

```text
Legal
→ Beta Legal Readiness

Tech
→ Deploy landing page

Marketing
→ Campaign message

Sales
→ Qualified lead list

Finance
→ Budget / payment readiness
```

Dependencies:

```text
Legal Terms
→ Marketing Launch

Tech Landing Page
→ Marketing Launch

Marketing Launch
→ Sales Outreach

Sales Win
→ Finance Receivable
```

---

# 80. Golden Scenario 2 — Finance Exception

Input:

```text
Transaction missing source document
```

Expected:

```text
Finance WorkItem
→ validation fails
→ MISSING_DOCUMENT
→ Blocker
→ handoff/Needs You
→ document received
→ validation reruns
→ REVIEW
→ DONE
→ lesson if recurring
```

---

# 81. Golden Scenario 3 — Marketing Rework

Input:

```text
Marketing creates campaign copy
```

Review:

```text
CTA does not support the current KR
```

Expected:

```text
REVIEW
→ REWORK
→ updated instruction
→ Marketing reruns
→ new artifact
→ REVIEW
→ ACCEPTED
→ lesson candidate
```

---

# 82. Golden Scenario 4 — Runtime Resume

Scenario:

```text
Desktop sleeps while Claude Code is running
```

Expected:

```text
checkpoint exists
desktop returns
runtime loads checkpoint
Claude Code run status refreshed
WorkItem status reconciled
dependencies restored
Needs You restored
no duplicate work
```

---

# 83. Golden Scenario 5 — Cross-Function Blocker

Scenario:

```text
Sales needs final pricing
```

Expected:

```text
Sales WorkItem → BLOCKED
BlockerRouter → Finance
Finance calculates margin/pricing support
Finance artifact → Handoff to Sales
Sales WorkItem → READY
```

Founder is not interrupted unless pricing requires strategic approval.

---

# 84. ADRs

Create:

```text
ADR-V13-1-001 Company Runtime Layer
ADR-V13-1-002 OpenOPC as Reference, Not Dependency
ADR-V13-1-003 Quick Task vs Company Work
ADR-V13-1-004 WorkItem State Machine
ADR-V13-1-005 Dependency DAG
ADR-V13-1-006 Work Contract + Review/Rework
ADR-V13-1-007 Structured Handoff + Blocker Routing
ADR-V13-1-008 Needs You Queue
ADR-V13-1-009 Runtime Checkpoint/Resume
ADR-V13-1-010 Role Attribution + Self-Growing Functions
ADR-V13-1-011 Built-In Skills Before Marketplace
ADR-V13-1-012 Deny-by-Default Remote Commands
```

---

# 85. Claude Code Mandatory Rules

Claude Code must:

1. Treat V13 as deployed and working.
2. Add V13.1 incrementally.
3. Preserve existing V13 behavior when V13.1 flags are disabled.
4. Never integrate OpenOPC as a production runtime dependency.
5. Never create duplicate WorkItem/Run/Approval systems.
6. Reuse V10/V13 domain entities and services.
7. Use additive migrations.
8. Do not delete hidden V12/V13 code.
9. Feature-gate all new V13.1 behavior.
10. Implement P0 before P1.
11. Preserve Legal and Finance governance.
12. Preserve LiveKit as an interaction layer only.
13. Preserve DeepSeek/Terra/Claude Code role boundaries.
14. Keep deterministic finance calculations authoritative.
15. Keep Policy Engine authoritative for consequential actions.
16. Add idempotency for work-creating commands.
17. Add transition tests for every WorkItem state.
18. Add DAG cycle-detection tests.
19. Add checkpoint/resume tests.
20. Add Finance/Legal escalation tests.
21. Implement Work Inspector before building any complex agent visualization.
22. Do not build marketplace or office simulation.
23. Do not enable agent free-chat.
24. Do not make P1 features prerequisites for P0 runtime.
25. Document deviations through ADRs.
26. Preserve backward compatibility for existing V13 cycles.
27. Prefer one complete end-to-end Weekly Mission vertical slice over many isolated features.
28. Keep runtime operations observable.
29. Never store hidden chain-of-thought.
30. Keep founder interruptions exception-driven.

---

# 86. Sprint Plan

## Sprint 1 — State + Contracts

```text
state machine
state transition guard
Work Contract
Work Review
feature flags
```

## Sprint 2 — Dependency Runtime

```text
Dependency DAG
ready-work resolver
cycle detection
parallel-safe execution
```

## Sprint 3 — Review + Exceptions

```text
Review/Rework
Blocker
BlockerRouter
Needs You
```

## Sprint 4 — Collaboration

```text
Structured Handoff
cross-function routing
Work Inspector
```

## Sprint 5 — Recovery

```text
Runtime Checkpoint
Resume/Reconciliation
Desktop/Cloud consistency
```

## Sprint 6 — Runtime Manager

```text
Intent Classifier
Quick Task vs Company Work
CompanyRuntimeManager
Weekly Mission decomposition
```

## Sprint 7 — Learning Upgrade

```text
Contribution Evaluation
Role Attribution
Lesson Candidate
Improvement Candidate
```

## Sprint 8 — P1 Workforce Intelligence

```text
ExecutorResolver
Ephemeral Specialist
Cycle Grants
Agent Experience
Function Skills
```

---

# 87. Rollout Strategy

Recommended rollout:

```text
Developer Workspace
→ Internal Cycle
→ One Weekly Mission
→ One Function
→ Multi-Function Mission
→ LiveKit commands
→ Finance/Legal runtime
→ Founder default
```

Do not enable `company_runtime_v13_1` globally before golden scenarios pass.

---

# 88. What to Keep Disabled

Continue to hide:

```text
Full PESTEL/SWOT/TOWS
Portfolio strategy
OpenOPC runtime dependency
Talent marketplace
Skill marketplace
Company package marketplace
Large org chart
Office animation
Agent free chat
Telephony
Video AI
Production TencentDB Agent Memory
```

These are future options, not V13.1 dependencies.

---

# 89. Product Positioning After V13.1

V13:

> COSA helps a founder run a 13-week company cycle with Legal, Marketing, Sales, Tech and Finance AI Functions.

V13.1:

> **COSA manages that cycle like an AI Chief of Staff: it decomposes weekly missions, coordinates the five functions, executes dependencies, routes blockers, reviews work, asks the founder only when needed, resumes after interruptions, and teaches the company to work better each week.**

---

# 90. Final Architectural Principle

V13.1 must make COSA **deeper, not wider**.

Do not add more feature domains.

Strengthen the core loop:

```text
Cycle
→ OKRs
→ 12WY
→ Weekly Mission
→ Company Runtime
→ Five AI Functions
→ Review/Rework
→ Result
→ Learning
→ Next Week
→ Week 13
```

---

# 91. One-Sentence Instruction to Claude Code

> **Build COSA V13.1 as an incremental Company Runtime layer under the already-deployed V13: classify work, separate Quick Task from Company Work, decompose Weekly Missions, execute dependency-aware WorkItems, route blockers and handoffs, review/rework outputs, preserve runtime checkpoints, surface only Needs You exceptions, and turn accepted outcomes into function-specific learning — without replacing the existing V10/V13 execution engine or expanding the user-facing product scope.**

---

# 92. Reference Architecture Note

OpenOPC should remain a **reference source for runtime orchestration patterns**, especially:

```text
work item state machines
dependency-aware execution
manager decomposition
delegation
review/rework
human escalation
runtime recovery
role-level learning
```

Do not create a hard dependency on OpenOPC versioning, storage, agent identity, task state, or package ecosystem.

This allows COSA to benefit from OpenOPC ideas while preserving its differentiators:

```text
13-week Company Cycle
OKRs + 12WY
LiveKit realtime CEO interaction
Vietnam-focused Legal/Finance
TT58 micro-enterprise accounting
Claude Code first-class execution
Founder attention optimization
```
