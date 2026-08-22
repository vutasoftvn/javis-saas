> **[ARCHIVED 2026-08-22]** Tài liệu này đã lỗi thời, được di chuyển vào `_archive/` để không gây nhầm lẫn khi tìm kiếm. Tham khảo tài liệu hiện hành: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/architecture/adr/ADR-012-legacy-backend-agentos-services-integration-plan.md`, và các ADR mới nhất trong `docs/architecture/adr/`. Nội dung gốc giữ nguyên bên dưới để tra cứu lịch sử.

# mCOSA V13 — Focused Company Cycle OS
## Detailed Claude Code Implementation Specification

**Product:** mCOSA — *my Company One System AI*  
**Target:** One-person company / micro startup  
**Baseline:** V10 Hybrid Workforce already implemented; V12.x architecture/docs exist  
**V13 strategy:** Reduce product scope without deleting previous architecture  
**Primary operating loop:** Cycle → OKRs → 12 Week Year → Weekly Mission → Execution → Weekly Review → Learning → Week 13 → Next Cycle  
**Core AI Functions:** Legal, Marketing, Sales, Tech, Finance  
**Realtime:** LiveKit  
**Routine chat:** DeepSeek  
**Strategic planning:** ChatGPT Terra profile / assisted workflow  
**Coding:** Claude Code CLI  
**Finance compliance target:** Vietnamese micro enterprises using accounting regime under Circular 58/2026/TT-BTC  
**Frontend:** Flutter + GetX  
**Backend:** Python FastAPI + PostgreSQL  
**Local execution:** mCOSA Desktop Execution Node  

---

# 1. Executive Decision

V13 is a deliberate product-focus release.

Do **not** continue expanding every subsystem from V12.3 at the same time.

The initial product must prove one strong promise:

> **The founder tells mCOSA what the company needs to achieve in the next 12 weeks. mCOSA builds the cycle, coordinates Legal, Marketing, Sales, Tech and Finance AI Functions, speaks with the founder in realtime, tracks outcomes, learns every week, and closes the cycle in Week 13.**

The V13 core is:

```text
                  FOUNDER / CEO
                       │
                 LiveKit Voice
                       │
                       ▼
                     mCOSA
                AI CHIEF OF STAFF
                       │
                       ▼
                   COMPANY CYCLE
                       │
                       ▼
                     OKRs
                       │
                       ▼
                12 WEEK YEAR
                       │
                       ▼
                WEEKLY MISSION
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
         Founder    AI Functions  Automation
                       │
       ┌───────────────┼────────────────────┐
       ▼               ▼           ▼        ▼        ▼
     LEGAL          MARKETING      SALES    TECH    FINANCE
       │               │           │        │        │
       └───────────────┼───────────┼────────┼────────┘
                       ▼
                    RESULTS
                       │
                       ▼
                WEEKLY REVIEW
                       │
                       ▼
                    LESSONS
                       │
                       ▼
                   NEXT WEEK
                       │
                      ...
                       │
                       ▼
                    WEEK 13
              REFLECT • LEARN •
              CELEBRATE • RESET
                       │
                       ▼
                   NEXT CYCLE
```

---

# 2. Product Scope Principle

V13 does **not** delete V12 functionality.

Instead:

```text
KEEP CODE
+
DISABLE FEATURE
+
HIDE UI
+
HIDE NORMAL API DISCOVERY
+
KEEP MIGRATION COMPATIBILITY
```

This allows later restoration without rebuilding.

Do not perform destructive cleanup merely because a module is not in V13 MVP.

---

# 3. Modules Enabled in V13

The user-facing MVP should enable only:

```text
1. Company Cycle
2. OKRs
3. 12 Week Year
4. Weekly Mission
5. Work / Hybrid Workforce
6. Weekly Review
7. Week 13
8. Legal AI Function
9. Marketing AI Function
10. Sales AI Function
11. Tech AI Function
12. Finance AI Function
13. LiveKit Voice
14. Learning / Lessons
15. CEO Brief
16. Next Actions — simple version
17. Artifacts / Approvals required by the above
```

---

# 4. Modules Temporarily Disabled / Hidden

The following V12.x modules should remain in source code but be disabled by default:

```text
Full Strategic Canvas UI
Full PESTEL UI
Full SWOT UI
Full TOWS UI
BSC UI
Portfolio Strategy UI
Portfolio PESTEL
Portfolio SWOT/TOWS
Complex Capacity Planner
Complex Founder Attention Engine
Complex Portfolio Dependency Graph
Agent Marketplace
Large Agent Hierarchy
Large Org Chart UI
Telephony/SIP
Realtime video AI
Screen-control automation
Full TencentDB Agent Memory production integration
Complex SOP marketplace
Complex Playbook marketplace
Advanced Finance/accounting ERP functions
Advanced tax engine
Multi-company enterprise features
```

Some backend/domain code may still be reused internally.

---

# 5. Feature Flag Policy

Create a centralized feature flag service.

Suggested flags:

```yaml
features:

  # V13 Core
  cycle_v13: true
  okr_v13: true
  twelve_week_year_v13: true
  weekly_mission_v13: true
  weekly_review_v13: true
  week13_v13: true

  legal_function_v13: true
  marketing_function_v13: true
  sales_function_v13: true
  tech_function_v13: true
  finance_function_v13: true

  livekit_voice_v13: true
  learning_v13: true
  ceo_brief_v13: true
  next_actions_basic_v13: true

  # Existing runtime needed by V13
  hybrid_workforce_v10: true
  work_items_v10: true
  artifacts_v10: true
  approvals_v10: true
  claude_code_worker_v10: true

  # Temporarily hidden
  strategic_canvas_full: false
  pestel_full: false
  swot_full: false
  tows_full: false
  bsc_full: false

  portfolio_full: false
  portfolio_capacity_advanced: false
  portfolio_dependency_graph: false

  tencentdb_agent_memory_production: false
  agent_marketplace: false
  advanced_org_chart: false
  telephony: false
  realtime_video: false
  advanced_finance_erp: false
```

---

# 6. Disable Means Hide, Not Delete

For a disabled feature:

## Frontend
- Remove from normal navigation.
- Do not render dashboard cards.
- Do not show onboarding steps.
- Deep links should show `FeatureNotEnabled` rather than crash.
- Admin/Developer mode may optionally expose a hidden feature-preview page.

## Backend
- Keep services/repositories/migrations.
- Route may remain compiled but return controlled `FEATURE_DISABLED`.
- Prefer route-level feature dependency.
- Background jobs must not execute disabled feature workflows.
- Disabled feature should not be called by AI router.

## AI
- Tool registry should exclude disabled tools.
- Prompt/context should not advertise unavailable capabilities.
- Intent router should map deprecated intents to a supported simpler flow or a clear unavailable response.

---

# 7. V13 Core Domain

Primary domain:

```text
Organization
  ↓
Cycle
  ↓
Objectives
  ↓
Key Results
  ↓
12WY Plan
  ↓
Weekly Missions
  ↓
WorkItems
  ↓
Artifacts / Results
  ↓
Weekly Reviews
  ↓
Lessons
  ↓
Week 13 Review
```

V10 Hybrid Workforce is reused for execution.

---

# 8. Cycle as Primary Operating Object

`Cycle` becomes the highest-level object in normal founder UX.

Suggested:

```yaml
cycle:
  id:
  organization_id:
  title:
  description:
  start_date:
  week_1_start:
  current_week:
  status:
  objective_ids: []
  capacity_hours_per_week:
  budget:
  created_by:
  activated_at:
  completed_at:
```

Status:

```text
DRAFT
PLANNING
READY
ACTIVE
PAUSED
WEEK_13
COMPLETED
ARCHIVED
```

---

# 9. V13 Onboarding

First-use onboarding should be:

```text
"What does your company need to achieve
in the next 12 weeks?"
```

Optional inputs:

```text
Available founder hours/week
Budget
Target date
Short company context
Existing project
```

Do not require Vision, Mission, PESTEL, SWOT, TOWS, Portfolio, or complex org setup during initial onboarding.

---

# 10. Cycle Planning Model Routing

Recommended:

```text
Create Cycle
→ DeepSeek extracts structured intent
→ Terra handles high-value Cycle planning
→ Founder reviews
→ Activate
```

Terra is used only for:

```text
Initial cycle design
Major cycle re-plan
Week 13 deep review
```

Routine operation remains DeepSeek/rules.

---

# 11. OKR Scope

Recommended default:

```text
1 Objective
3 Key Results
```

Allow:

```text
1–3 Objectives
1–3 KRs each
```

but strongly recommend the simplest structure to OPC founders.

---

# 12. Objective and KR

```yaml
objective:
  id:
  cycle_id:
  project_id: optional
  title:
  description:
  why:
  priority:
  owner_id:
  status:
  progress:

key_result:
  id:
  objective_id:
  title:
  metric_type:
  baseline:
  target:
  current:
  unit:
  due_date:
  evidence_refs: []
  progress:
  status:
```

Metric types:

```text
NUMBER
PERCENTAGE
CURRENCY
BOOLEAN
MILESTONE
CUSTOM
```

---

# 13. OKR Must Drive 12WY

Never treat OKR and 12WY as separate apps.

Flow:

```text
Objective
  ↓
Key Results
  ↓
12 Week Plan
  ↓
Weekly Missions
  ↓
WorkItems
```

Every meaningful WorkItem should ideally trace to:

```text
Weekly Mission
→ KR
→ Objective
→ Cycle
```

---

# 14. Weekly Mission

Each week gets one main mission.

```yaml
weekly_mission:
  id:
  cycle_id:
  week_number:
  title:
  mission:
  success_criteria: []
  linked_kr_ids: []
  founder_work_items: []
  ai_work_items: []
  status:
```

Main UI:

```text
WEEK 4

MISSION
Complete the first end-to-end mCOSA beta build.

SUCCESS
- Login works
- Main workflow works
- Android build installs
```

---

# 15. Five Core AI Functions

V13 introduces exactly five operational Functions:

```text
LEGAL
MARKETING
SALES
TECH
FINANCE
```

They are capability containers, not mandatory formal departments.

Founder should normally talk to mCOSA, not choose a worker manually.

---

# 16. Legal AI Function

Purpose:

> Help a micro startup identify, prepare, track and review legal/compliance work while preserving Human/Professional authority for material legal decisions.

Capabilities:

```text
Legal research
Legal readiness checklist
Contract analysis
Terms drafting
Privacy policy drafting
Compliance checklist
Legal obligation tracking
Risk summaries
Expert escalation packages
```

Not allowed to make final legal determinations, sign agreements, or submit regulated filings autonomously.

---

# 17. Marketing AI Function

Purpose:

> Create measurable demand linked directly to Cycle KRs.

Capabilities:

```text
ICP
Positioning
Market research
Content strategy
Campaign plan
Content creation
SEO
Social media
Landing page brief
Campaign analytics
Experiment design
```

Capture:

```text
Campaign
Audience
Message
Channel
Spend
Result
Conversion
Lesson
```

---

# 18. Sales AI Function

Purpose:

> Convert qualified demand into customers/revenue.

Capabilities:

```text
Lead research
Lead qualification
Sales brief
Outreach drafts
Follow-up
Proposal drafting
Pipeline tracking
Conversion analysis
Objection learning
```

Founder/Human remains important for high-value negotiations and binding commercial commitments.

---

# 19. Tech AI Function

Purpose:

> Turn Product/Technology WorkItems into tested software artifacts.

Primary executor:

```text
Claude Code CLI
```

Flow:

```text
Tech WorkItem
  ↓
Claude Code Worker
  ↓
Git worktree
  ↓
Implementation
  ↓
Tests
  ↓
Build
  ↓
Artifact
  ↓
Approval
```

---

# 20. Finance AI Function — Product Role

Finance is a V13 core Function.

Primary V13 target:

> **Financial operations and simplified accounting support for Vietnamese micro enterprises applying Circular 58/2026/TT-BTC.**

Finance has two different responsibilities:

```text
MANAGEMENT FINANCE
+
ACCOUNTING ASSISTANCE
```

Do not conflate accounting rules with tax determination.

---

# 21. Circular 58/2026/TT-BTC Boundary

Circular 58/2026/TT-BTC guides accounting documents, accounting books, and preparation/presentation of financial statements for micro enterprises in scope.

Tax obligations are determined under tax law.

Therefore:

```text
AccountingEngine
≠
TaxEngine
```

V13 must not implement a tax engine from Circular 58 alone.

---

# 22. Accounting Profile

Create:

```yaml
accounting_profile:
  organization_id:
  country: VN
  regime: TT58_2026
  entity_classification: MICRO_ENTERPRISE
  fiscal_year_start:
  vat_method:
  cit_method:
  accounting_regime_effective_from:
  status:
  confirmed_by:
```

Do not auto-classify final legal eligibility without founder/accountant confirmation.

---

# 23. TT58 Accounting Modes

Represent the four combinations explicitly:

```text
TT58_MODE_1
VAT_REVENUE_PERCENT
CIT_REVENUE_PERCENT

TT58_MODE_2
VAT_REVENUE_PERCENT
CIT_TAXABLE_INCOME

TT58_MODE_3
VAT_CREDIT_METHOD
CIT_REVENUE_PERCENT

TT58_MODE_4
VAT_CREDIT_METHOD
CIT_TAXABLE_INCOME
```

The selected mode determines required book configuration.

Never mix modes silently.

---

# 24. Finance Setup Wizard

```text
Step 1
Confirm TT58 applicability

Step 2
Fiscal year

Step 3
VAT method

Step 4
CIT method

Step 5
Accounting mode

Step 6
Opening balances / migration source

Step 7
Review

Step 8
Activate
```

For uncertainty:

```text
ASK ACCOUNTANT
```

rather than guessing.

---

# 25. TT58 Mode 1 First

For VAT and CIT both calculated as a percentage of revenue, Circular 58 provides the simplest bookkeeping path and identifies the sales/service revenue book `S1-DNSN`.

V13 should implement and validate this mode first.

---

# 26. Regulation-Driven Book Registry

Do not hard-code accounting forms into screens.

```yaml
book_template:
  id:
  regulation:
  regulation_version:
  mode:
  code:
  title:
  columns_schema:
  validation_rules:
  effective_from:
  effective_to:
```

Examples include:

```text
S1-DNSN
S2a-DNSN
S2b-DNSN
S2c-DNSN
S2d-DNSN
...
```

Exact templates must be verified against authoritative Circular text/appendices before production use.

---

# 27. Financial Statement Registry

Create a versioned registry:

```yaml
financial_statement_template:
  regulation:
  code:
  title:
  schema:
  validation_rules:
```

Do not embed legal/reporting forms directly in Flutter widgets.

---

# 28. Finance V13 Functional Scope

Enable:

```text
Cash tracking
Bank tracking
Revenue capture
Expense capture
Receivables
Payables
Basic inventory/material tracking when required
Accounting document attachment
Book generation based on TT58 mode
Financial statement draft generation
Cashflow overview
Burn
Runway
Revenue
AI/tool cost
Budget vs actual
Accounting checklist
Period closing checklist
```

---

# 29. Finance V13 Non-Goals

Do not build yet:

```text
Full ERP
Payroll engine
Complex tax calculation engine
Automated tax filing
Bank payment execution
Treasury management
Consolidation
Multi-country accounting
Complex fixed asset system
Audit firm workflow
```

---

# 30. Management Finance Dashboard

Founder needs:

```text
Cash
Monthly burn
Runway
Revenue
Expenses
Receivables
Payables
AI/tool cost
Cycle budget
Budget vs actual
```

This is separate from statutory accounting reports.

---

# 31. Finance and Cycle

Finance must connect to Cycle KRs.

Example:

```text
Objective:
Launch mCOSA beta

KR:
5 paying customers

Finance:
Revenue
Cash collected
Outstanding receivables
Acquisition spend
AI/tool spend
```

Week 13 can then evaluate economic reality, not just task completion.

---

# 32. Finance Exceptions

```text
MISSING_DOCUMENT
UNCLASSIFIED_TRANSACTION
DUPLICATE_TRANSACTION
CASH_MISMATCH
BANK_MISMATCH
OVERDUE_RECEIVABLE
OVERDUE_PAYABLE
BUDGET_OVERRUN
RUNWAY_RISK
ACCOUNTING_MODE_CONFLICT
PERIOD_CLOSE_BLOCKER
PROFESSIONAL_REVIEW_REQUIRED
```

Founder sees only exceptions requiring attention.

---

# 33. Accounting Documents and Transactions

```yaml
accounting_document:
  id:
  organization_id:
  type:
  date:
  counterparty:
  reference_number:
  amount:
  tax_amount:
  currency:
  attachment_id:
  source:
  status:
  classification:

financial_transaction:
  id:
  organization_id:
  accounting_profile_id:
  date:
  transaction_type:
  amount:
  currency:
  counterparty:
  document_refs: []
  category:
  project_id:
  cycle_id:
  work_item_id:
  status:
  reviewed_by:
```

---

# 34. Accounting Record

Avoid overbuilding a general-ledger engine if not needed for the selected TT58 mode.

```yaml
accounting_record:
  id:
  book_template_id:
  period_id:
  transaction_id:
  fields:
  source_document_refs:
  validation_status:
```

This supports simplified books.

---

# 35. Accounting Period

```yaml
accounting_period:
  organization_id:
  fiscal_year:
  period:
  status:
```

Status:

```text
OPEN
REVIEW
CLOSED
LOCKED
```

Locked periods require explicit authorized reopening.

---

# 36. Finance Agent Capabilities

```text
capture_transaction
classify_transaction
request_missing_document
generate_book_preview
reconcile_cash
reconcile_bank
calculate_management_metrics
prepare_period_close
prepare_financial_statement_draft
explain_finance_status
flag_compliance_risk
prepare_accountant_review_package
```

---

# 37. Finance Agent Authority

Default autonomy:

```text
A1 Recommend
A2 Draft
```

Human/accountant approval governs:

```text
final period close
final statutory statements
material accounting policy change
regime/mode change
external filing
```

No autonomous money transfer.

---

# 38. Finance Professional Escalation

Create:

```text
ACCOUNTANT_REVIEW_REQUIRED
```

when:

```text
regime uncertain
tax/accounting method uncertain
material discrepancy
regulatory interpretation
period closing conflict
transition between regimes
possible loss of micro-enterprise eligibility
```

mCOSA should prepare a structured review package.

---

# 39. Finance Collaborations

## Finance + Legal

```text
Compliance/accounting issue
→ Legal Review WorkItem
→ Artifact
→ CEO/Finance
```

## Finance + Sales

```text
Deal
→ Receivable
→ Payment
→ Revenue/Cash
→ KR progress
```

## Finance + Marketing

```text
Campaign spend
→ Leads
→ Customers
→ Revenue
→ simple CAC/spend insight
```

## Finance + Tech

Track:

```text
AI API
Cloud
LiveKit
Developer tools
Hosting
```

against Cycle/Project where practical.

---

# 40. Startup Health

Create lightweight `StartupHealth`:

```text
Cash
Burn
Runway
Revenue
Sales pipeline
Cycle progress
Critical legal risks
Tech blockers
```

CEO Brief summarizes only what matters.

---

# 41. LiveKit Remains Core

V13 keeps realtime voice.

MVP actions:

```text
Talk
Interrupt
Ask status
Give command
Approve
Navigate
```

Desktop:

```text
Flutter Desktop
→ LiveKit Local
→ Voice Runtime
→ DeepSeek / mCOSA Tools
```

Mobile:

```text
Flutter Mobile
→ LiveKit Cloud
→ Voice Agent
→ mCOSA Control Plane
→ Desktop Node when required
```

---

# 42. CEO Brief

Recommended:

```text
WEEK 4 / 13

MISSION
Complete mCOSA beta end-to-end.

KR PROGRESS
MVP             62%
Beta Users      6 / 20
Paid Customers  1 / 5

NEEDS YOU
1 Legal review
1 Tech approval

AI TEAM
Marketing: campaign running
Sales: 3 qualified leads
Tech: authentication testing
Finance: books reconciled

CASH
Runway: 9.6 months

TOP 3 ACTIONS
...
```

---

# 43. Learning Is Core

Learning begins with structured PostgreSQL data.

```text
PLAN
 ↓
WORK
 ↓
RESULT
 ↓
REVIEW
 ↓
LESSON
 ↓
IMPROVE
 ↓
NEXT WEEK
```

---

# 44. Lesson Entity

```yaml
lesson:
  id:
  organization_id:
  cycle_id:
  week_number:
  function:
  project_id: optional
  observation:
  evidence_refs: []
  interpretation:
  recommendation:
  confidence:
  status:
```

Status:

```text
DRAFT
CONFIRMED
REJECTED
APPLIED
SUPERSEDED
```

---

# 45. Function Learning

```text
Legal:
issue → lesson → improved checklist

Marketing:
campaign → result → lesson → better message/channel

Sales:
conversation → conversion → lesson → better qualification

Tech:
build/test → lesson → coding/deployment improvement

Finance:
reconciliation/error/cash pattern → lesson → improved process
```

---

# 46. Weekly Review

At end of week:

```text
Mission
Planned
Completed
Execution Score
KR Progress
Function Results
Founder Attention
Finance Status
Risks
Lessons
AI Recommendation
```

Founder chooses:

```text
Accept next plan
Adjust
Major replan
```

---

# 47. Execution Score + Outcome

Execution Score:

```text
completed committed WorkItems
──────────────────────────────
planned committed WorkItems
```

Also show KR movement.

mCOSA should warn on:

```text
high activity
+
low outcome movement
```

---

# 48. Week 13

Week 13 is mandatory first-class experience.

```text
REFLECT
 ↓
LEARN
 ↓
CELEBRATE
 ↓
RESET
```

Review:

```text
Objectives
KRs
Weekly execution
Legal readiness
Marketing performance
Sales performance
Tech delivery
Finance results
Cash/runway
Founder attention
Lessons
```

---

# 49. Week 13 Finance Review

Include:

```text
Revenue
Cash collected
Expenses
Burn
Runway
Outstanding AR/AP
Cycle budget variance
Missing documents
Accounting period status
Compliance exceptions
```

---

# 50. Week 13 Celebration

LiveKit can speak a concise completion summary and ask:

```text
"What are you most proud of?"
```

Founder reflection becomes a confirmed Cycle artifact/lesson.

---

# 51. Next Best Actions — Simple

Do not implement complex portfolio scoring.

Use:

```text
Founder-required
+
Urgency
+
Dependency
+
KR relevance
+
Risk
```

Return Top 3.

---

# 52. WorkItem Integration

Reuse V10.

Add:

```yaml
work_item:
  cycle_id:
  objective_id:
  key_result_id:
  weekly_mission_id:
  function:
```

No second task engine.

---

# 53. Function Routing

Rules first:

```text
legal/compliance/contract → LEGAL
campaign/content/positioning → MARKETING
lead/customer/proposal → SALES
code/build/test → TECH
cash/accounting/revenue/expense → FINANCE
```

Ambiguous cases can use DeepSeek classification.

---

# 54. Model Routing

```text
Routine chat → DeepSeek
Cycle creation → Terra
Major replan → Terra
Week 13 synthesis → Terra
Coding → Claude Code
Finance calculations → deterministic code first
Legal/Finance explanation → model + structured sources/data
```

Important:

> LLMs explain and suggest; deterministic services calculate authoritative financial figures.

---

# 55. Finance Regulation Registry

```yaml
regulation:
  code: TT58_2026_TT_BTC
  jurisdiction: VN
  authority: Ministry of Finance
  issued_date: 2026-05-25
  effective_date: 2026-07-01
  type: accounting_regime
  status:
```

All templates link to regulation/version.

---

# 56. Regulation Versioning

Architecture:

```text
Regulation
  ↓
Version
  ↓
Applicability
  ↓
Templates
  ↓
Validation rules
```

Do not hard-code TT58 forever.

---

# 57. TT58 Transition Support

Future-compatible service:

```text
AccountingRegimeTransitionService
```

Responsibilities:

```text
validate transition date
map opening balances
archive old configuration
activate new regime version
produce transition report
```

No silent mid-period switch.

---

# 58. Reports

Separate clearly:

```text
MANAGEMENT REPORTS
Cash / Burn / Runway / Revenue / Expense / AR/AP / Budget

STATUTORY ACCOUNTING OUTPUTS
TT58-prescribed books/statements
```

Do not mix UI labels.

---

# 59. Finance Data Integrity

Requirements:

```text
immutable audit trail
document links
review state
period locking
change history
rounding rules
currency handling
duplicate detection
```

---

# 60. Finance Audit Events

```text
TRANSACTION_CREATED
TRANSACTION_EDITED
DOCUMENT_ATTACHED
CLASSIFICATION_CHANGED
BOOK_GENERATED
PERIOD_CLOSED
PERIOD_REOPENED
STATEMENT_GENERATED
STATEMENT_APPROVED
REGIME_CHANGED
```

---

# 61. Learning Storage and Agent Memory

V13 production learning uses PostgreSQL:

```text
Lessons
WeeklyReview
CycleReview
Decisions
Improvement proposals
```

TencentDB Agent Memory remains hidden/experimental:

```yaml
tencentdb_agent_memory_production: false
claude_memory_poc: true
```

Do not delete V12.3 memory code.

---

# 62. Navigation

Default:

```text
Home
Cycle
Work
AI Team
Finance
Knowledge
Settings
```

Do not show PESTEL, SWOT, TOWS, Portfolio, Agent Memory, or Advanced Org in normal navigation.

---

# 63. AI Team UI

Show exactly:

```text
Legal
Marketing
Sales
Tech
Finance
```

Each card:

```text
Current work
Status
Latest result
Needs founder?
Key metric
```

---

# 64. Finance UI

Tabs:

```text
Overview
Transactions
Documents
Books
Reports
Periods
Exceptions
Settings
```

Avoid ERP complexity.

---

# 65. Suggested FastAPI Structure

```text
app/
  cycles/
  okrs/
  twelve_week_year/
  weekly/
  learning/

  functions/
    legal/
    marketing/
    sales/
    tech/
    finance/

  realtime/
  work/
  approvals/
  artifacts/
  knowledge/
  features/
```

Finance:

```text
app/functions/finance/
  domain/
  application/
  regulations/
    tt58_2026/
      registry.py
      modes.py
      templates/
      validations/
  api/
```

---

# 66. Regulation Data Files

Prefer:

```text
regulations/
  vn/
    tt58_2026/
      metadata.yaml
      modes.yaml
      books/
      statements/
      validations/
```

Avoid scattering regulatory constants across Python/Flutter.

---

# 67. API Sketch

Cycle:

```text
POST /cycles
POST /cycles/{id}/plan
POST /cycles/{id}/activate
GET  /cycles/current
GET  /cycles/{id}/weeks/{week}
POST /cycles/{id}/weekly-review
POST /cycles/{id}/week13
```

Finance:

```text
GET  /finance/profile
PUT  /finance/profile
GET  /finance/overview
POST /finance/documents
POST /finance/transactions
GET  /finance/books
POST /finance/books/generate
GET  /finance/reports
POST /finance/reports/generate
GET  /finance/periods
POST /finance/periods/{id}/close
GET  /finance/exceptions
```

---

# 68. Database Additions

```text
cycles
objectives
key_results
weekly_missions
weekly_reviews
lessons
function_status

accounting_profiles
accounting_regulations
accounting_regulation_versions
accounting_book_templates
financial_statement_templates
accounting_documents
financial_transactions
accounting_records
accounting_periods
finance_exceptions
finance_management_snapshots
```

Reuse V10 execution tables.

---

# 69. No Destructive Migration

Rules:

```text
NO DROP TABLE
NO destructive rename
NO data deletion
```

for hidden V12 modules unless separately reviewed.

---

# 70. Developer Mode

Optional hidden path:

```text
Settings → Developer → Experimental Features
```

Can expose old Strategic Canvas, Portfolio, Agent Memory for testing.

---

# 71. Tool Registry

Standard V13:

```text
cycle.*
okr.*
weekly.*
work.*
legal.*
marketing.*
sales.*
tech.*
finance.*
approval.*
artifact.*
knowledge.*
ui.*
```

Disabled by default:

```text
portfolio.*
pestel.*
tows.*
agent_memory_admin.*
```

---

# 72. First Vertical Slice

Founder:

> “Trong 12 tuần tới tôi muốn ra mắt mCOSA và có 5 khách hàng trả tiền.”

Expected:

```text
1. Create Cycle
2. Terra proposes Objective + 3 KRs
3. Founder approves
4. mCOSA generates 12WY
5. Week 1 Mission created
6. Work split across 5 Functions
7. Founder speaks via LiveKit
8. Tech routes to Claude Code
9. Marketing creates launch work
10. Sales creates lead work
11. Legal produces readiness checklist
12. Finance initializes startup health/accounting checklist
13. Weekly Review produces Lessons
14. Week 13 closes Cycle
```

---

# 73. Finance Vertical Slice

Scenario:

```text
Micro enterprise
TT58 applicability confirmed
Mode selected
```

Flow:

```text
1. Configure Accounting Profile
2. Capture source document
3. Create transaction
4. Finance Agent suggests classification
5. Human confirms if needed
6. Generate relevant book record
7. Update cash/revenue/expense
8. Reconcile
9. Produce management dashboard
10. Period-close checklist
11. Draft applicable TT58 outputs
12. Escalate uncertainty to accountant
```

---

# 74. Accounting Template Verification Gate

Before any TT58 output is marked production-ready:

```text
1. Verify against official Circular text
2. Verify appendices
3. Build deterministic fixtures
4. Accountant review
5. Add regression tests
6. Version-lock templates
```

Until then use:

```text
DRAFT / REVIEW
```

---

# 75. Testing

Required:

```text
Cycle domain
OKR progress
Weekly Mission
Week transitions
Week 13
Feature flags
Hidden navigation
AI tool registry
Function routing

Finance:
TT58 mode selection
Transaction validation
Book templates
Period closing
Financial calculations
Audit history

Security:
finance authorization
legal authorization
feature-disabled routes
voice approval
```

---

# 76. Finance Golden Tests

Use deterministic fixtures:

```text
Known documents
Known transactions
Known accounting mode
Known expected book rows
Known expected totals
```

No LLM judging accounting-number correctness.

---

# 77. Definition of Done

V13 MVP is complete when the founder can:

1. Create a 12-week Company Cycle.
2. Generate/review OKRs.
3. Activate a 12WY plan.
4. See one clear Weekly Mission.
5. See Founder Work vs AI Work.
6. Use Legal AI.
7. Use Marketing AI.
8. Use Sales AI.
9. Use Tech AI with Claude Code.
10. Use Finance AI for startup finance/accounting assistance.
11. Configure TT58 accounting mode when applicable.
12. Track cash/burn/runway.
13. Capture accounting documents and transactions.
14. Generate verified applicable accounting books/templates.
15. Speak to mCOSA through LiveKit.
16. Interrupt mCOSA naturally.
17. Ask status and issue commands.
18. Receive Weekly Reviews.
19. Store and reuse Lessons.
20. Complete Week 13.
21. Review all five AI Functions.
22. Celebrate cycle completion.
23. Create next Cycle.
24. Run without exposing disabled V12 modules in normal UX.
25. Re-enable hidden modules later without restoring deleted code.

---

# 78. Non-Goals

Do not implement now:

```text
Full PESTEL
Full SWOT/TOWS
Portfolio strategy
Complex BSC
Full ERP
Tax filing automation
Payment automation
Telephony
Video AI
Agent marketplace
Autonomous legal decision making
Production TencentDB Agent Memory
Complex multi-manager hierarchy
```

---

# 79. Migration Plan

```text
Step 1 — Inventory current routes/navigation/services/models/workers/tools
Step 2 — Classify KEEP_ENABLED / KEEP_HIDDEN / REUSE_INTERNAL
Step 3 — Add centralized Feature Flags
Step 4 — Hide advanced V12 UX
Step 5 — Build Cycle/OKR/12WY/Weekly/Week13
Step 6 — Compile Weekly Missions into V10 WorkItems
Step 7 — Implement 5 Functions
Step 8 — Implement Finance TT58 profile/registry/templates
Step 9 — Keep LiveKit core, reduce scope
Step 10 — Implement structured Learning
Step 11 — Hardening/security/tests
```

---

# 80. Claude Code Mandatory Rules

1. Treat this V13 document as product scope authority.
2. Preserve V10 Hybrid Workforce.
3. Reuse V10 WorkItem/Run/Artifact/Approval.
4. Never create a second execution engine.
5. Never delete V12 advanced modules only because they are disabled.
6. Hide disabled functionality behind feature flags.
7. Remove disabled tools from normal AI tool registry.
8. Keep database compatibility.
9. Create additive migrations.
10. Keep PostgreSQL as system of record.
11. Keep GetX confined to presentation/navigation/DI.
12. Keep model/provider logic behind adapters.
13. Use deterministic code for financial calculations.
14. Never let an LLM become authoritative financial arithmetic.
15. Version accounting regulations/templates.
16. Do not hard-code TT58 forms in UI.
17. Require explicit Accounting Profile.
18. Do not infer TT58 eligibility as final fact.
19. Separate accounting regulation from tax-law determination.
20. Preserve audit trail for financial changes.
21. Never auto-pay money.
22. Never autonomously file legal/tax submissions.
23. Require policy checks for external consequential actions.
24. Keep LiveKit voice as interface, not business logic.
25. Store learning as structured Lessons before advanced memory.
26. Keep TencentDB Agent Memory production-disabled in V13.
27. Keep Claude memory PoC optional.
28. Build tests before marking TT58 outputs production-ready.
29. Add an ADR for meaningful deviation.
30. Prefer complete vertical slices over adding subsystems.

---

# 81. Required ADRs

```text
ADR-V13-001 Cycle as Primary Founder Operating Unit
ADR-V13-002 OKR to 12WY Unified Planning
ADR-V13-003 Five Core AI Functions
ADR-V13-004 Feature Flags Preserve V12 Code
ADR-V13-005 LiveKit Core but Scope-Limited
ADR-V13-006 Learning via Structured Lessons First

ADR-FIN-001 Finance Function Boundary
ADR-FIN-002 TT58 Regulation Registry
ADR-FIN-003 Accounting vs Tax Separation
ADR-FIN-004 Deterministic Finance Calculations
ADR-FIN-005 Micro-Enterprise Accounting Profile
ADR-FIN-006 TT58 Mode Configuration
ADR-FIN-007 Accounting Template Verification
ADR-FIN-008 Period Locking and Audit
```

---

# 82. Recommended Sprints

```text
Sprint 1 — Feature flags + navigation focus
Sprint 2 — Cycle + OKR + 12WY
Sprint 3 — Weekly Mission + Review + Lessons
Sprint 4 — Legal/Marketing/Sales/Tech/Finance shells
Sprint 5 — Finance core + TT58 modes + management finance
Sprint 6 — Finance books/templates/period close
Sprint 7 — LiveKit core
Sprint 8 — Week 13 + function reviews + celebration
Sprint 9 — Security + golden tests + UX hardening
```

---

# 83. Product Metrics

Primary:

```text
Cycle activation
Weekly return rate
Weekly Mission completion
KR progress
Week 13 completion
Next Cycle creation
```

North-star:

> **Accepted business outcomes per hour of founder attention.**

---

# 84. Product Positioning

> **mCOSA helps a founder run the next 12 weeks of the company with an AI team for Legal, Marketing, Sales, Tech and Finance — through realtime conversation, measurable OKRs and continuous learning.**

---

# 85. Final V13 Architecture

```text
                         FOUNDER
                            │
                     LIVEKIT VOICE
                            │
                            ▼
                          mCOSA
                   AI CHIEF OF STAFF
                            │
                            ▼
                       COMPANY CYCLE
                            │
                            ▼
                           OKRs
                            │
                            ▼
                     12 WEEK YEAR
                            │
                            ▼
                     WEEKLY MISSION
                            │
       ┌────────────────────┼─────────────────────┐
       ▼                    ▼                     ▼
   FOUNDER WORK          AI TEAM              AUTOMATION
                            │
       ┌──────────┬─────────┼─────────┬──────────┐
       ▼          ▼         ▼         ▼          ▼
     LEGAL    MARKETING   SALES      TECH      FINANCE
       │          │         │         │          │
       │          │         │     Claude Code    │
       └──────────┴─────────┼────────────────────┘
                            ▼
                         RESULTS
                            │
                            ▼
                      WEEKLY REVIEW
                            │
                            ▼
                          LESSONS
                            │
                            ▼
                         NEXT WEEK
                            │
                           ...
                            │
                            ▼
                         WEEK 13
                 REFLECT • LEARN •
                 CELEBRATE • RESET
                            │
                            ▼
                        NEXT CYCLE
```

---

# 86. Final Finance Architecture

```text
                         FINANCE AI
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     MANAGEMENT FINANCE  ACCOUNTING       EXCEPTIONS
            │                │                │
      Cash / Burn /       TT58 Profile     Missing docs
      Runway / Revenue        │            Mismatch
      Budget / Cost           ▼            Risk
                       Regulation Registry
                             │
                             ▼
                         TT58 Mode
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
              Documents              Transactions
                 │                       │
                 └───────────┬───────────┘
                             ▼
                     Accounting Records
                             │
                             ▼
                       Books / Reports
                             │
                             ▼
                    Human/Accountant Review
                             │
                             ▼
                         Period Close
```

---

# 87. Regulatory Notes for Implementation

- Circular 58/2026/TT-BTC was issued by Vietnam's Ministry of Finance on 25 May 2026 and is titled as guidance for the accounting regime for micro enterprises.
- It covers accounting documents, bookkeeping, and financial-statement preparation/presentation for micro enterprises in scope.
- The Circular explicitly separates this from determination of tax obligations, which follows tax law.
- Bookkeeping is organized according to four VAT/CIT method combinations in Articles 5–8.
- For the case where both VAT and CIT are paid as percentages of revenue, the Circular identifies `S1-DNSN` as the sales/service revenue book.
- Other modes require more detailed book sets.
- Production outputs must be checked against the official Circular and appendices and reviewed with deterministic test fixtures before being labelled filing-ready.

---

# 88. Final Instruction to Claude Code

Build V13 as a **focused vertical company operating loop**, not a collection of independent feature islands.

Every enabled feature should materially help answer:

```text
What are we trying to achieve this Cycle?
What must happen this week?
What does the founder need to do?
What can the five AI Functions do?
What result did we get?
What changed in our KRs?
What did we learn?
What changed financially?
What requires Legal/Finance attention?
What should change next week?
```

If a proposed feature does not help answer one of these questions, keep it disabled for V13.

The target is not maximum architecture.

The target is:

> **A founder can complete a full 13-week company operating cycle with mCOSA, supported by realtime AI and five practical company functions, while the system learns every week and remains financially/accounting-aware for a Vietnamese micro enterprise.**
