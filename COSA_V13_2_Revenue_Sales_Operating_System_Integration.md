# COSA V13.2 — Revenue & Sales Operating System
## Incremental Integration Specification for COSA V13.1 Company Runtime

**Product:** COSA / mCOSA — Company Operating System AI  
**Baseline:** V13 deployed; V13.1 Company Runtime adjustment defined  
**Purpose:** Upgrade the Sales Function into a complete Revenue Operating System for startup/one-person company execution  
**Implementation style:** Additive, feature-flagged, non-destructive  
**Primary principle:** Marketing creates demand; Sales converts demand into customers; Customer Success retains/expands customers; Finance confirms actual revenue/cash/profit  
**Reuse:** WorkItem, Run, Artifact, Approval, Handoff, Blocker, Needs You, Learning, LiveKit, Policy Engine  
**Do not create:** A second task engine, second runtime, second CRM truth, or separate customer-success platform  
**Frontend:** Flutter + GetX  
**Backend:** Python FastAPI + PostgreSQL  
**Realtime:** LiveKit  
**Routine AI:** DeepSeek / configured low-cost model profile  
**Strategic cycle/revenue planning:** Terra / configured strategic profile  
**Coding:** Claude Code CLI  
**Finance:** Existing V13 Finance + TT58 support  

---

# 1. Executive Decision

V13.2 should not add a generic “Sales chatbot.”

It should turn the existing Sales Function into a structured **Revenue Operating System**.

The Sales domain must answer:

```text
Who should we sell to?
Who is most likely to buy?
What stage is each buyer in?
What should happen next?
Which deals are blocked?
Which deals are likely to close?
Why are deals won/lost?
Which customers are at risk?
Where will future revenue come from?
How does pipeline compare with actual cash/revenue?
```

The target operating chain is:

```text
Marketing
   ↓
Demand
   ↓
Lead
   ↓
Qualification
   ↓
Opportunity
   ↓
Proposal
   ↓
Won / Lost
   ↓
Customer
   ↓
Onboard / Retain / Expand / Refer
   ↓
Finance
   ↓
Actual Revenue / Cash / Profit
   ↓
Learning
```

---

# 2. Product Boundary

V13.2 must preserve these responsibilities:

| Function | Primary responsibility |
|---|---|
| Marketing | Create demand, campaigns, ICP hypotheses, source leads |
| Sales | Convert qualified demand into customers and future revenue |
| Customer Success | Retain, renew, expand and generate referrals |
| Finance | Confirm accounting reality, cash, revenue, margin, runway |
| Legal | Review binding terms, contracts and regulatory risk |
| Tech | Resolve technical questions, product gaps and implementation work |

Customer Success remains **inside Sales/Revenue** in V13.2.

Do not create a sixth top-level AI Function yet.

---

# 3. Core Principle: Future Revenue vs Actual Revenue

Sales owns:

```text
pipeline
opportunity value
weighted pipeline
expected close
sales forecast
renewal/expansion opportunity
```

Finance owns:

```text
invoice
receivable
payment
recognized/accounted revenue
cash
expense
profit
runway
```

Hard rule:

> **Sales forecast is not accounting revenue.**

Example:

```text
Sales Pipeline = 100m
Weighted Pipeline = 42m
Actual Cash = 12m
```

These must remain separate fields and separate source-of-truth domains.

---

# 4. Revenue Operating Loop

```text
                       COMPANY CYCLE
                             │
                            OKRs
                             │
                       Weekly Mission
                             │
                             ▼
                    Company Runtime
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
        Marketing          Sales          Finance
            │                │                │
            ▼                ▼                │
          Demand           Leads              │
                             │                │
                             ▼                │
                         Qualified            │
                             │                │
                             ▼                │
                        Opportunity           │
                             │                │
                             ▼                │
                         Proposal             │
                             │                │
                        ┌────┴────┐           │
                        ▼         ▼           │
                       WON       LOST         │
                        │                     │
                        ▼                     │
                    Customer                  │
                        │                     │
             ┌──────────┼───────────┐         │
             ▼          ▼           ▼         │
          Retain      Expand      Refer       │
             │          │           │         │
             └──────────┴─────┬─────┘         │
                              ▼               ▼
                          Revenue Event → Finance
                              │
                              ▼
                         Actual Economic
                             Reality
                              │
                              ▼
                           Learning
```

---

# 5. Upgrade Sales Function to Revenue Function Internally

UI label may remain:

```text
Sales
```

Internal domain should be:

```text
RevenueFunction
```

with six capabilities:

```text
1. Revenue Planning
2. Prospecting
3. Qualification
4. Opportunity / Deal Execution
5. Customer Success
6. Revenue Intelligence
```

This keeps startup UX simple while supporting full revenue lifecycle.

---

# 6. Agent Architecture

Do not create many persistent agents.

Use:

```text
                     SALES LEAD AGENT
                        Persistent
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     Prospecting        Deal Copilot     Customer Success
      Specialist         Specialist         Specialist
      Ephemeral          Ephemeral          Ephemeral
```

Supporting deterministic services:

```text
LeadDedupService
LeadScoringService
FunnelMetricsService
PipelineForecastService
SequenceScheduler
OpportunityStallDetector
CustomerHealthService
RevenueAttributionService
SalesTargetCompiler
```

---

# 7. Sales Lead Agent

Mission:

> Convert target demand into accepted customers while keeping the pipeline accurate, clean, prioritized and aligned to the current Cycle/KRs.

Responsibilities:

```text
review sales target
review funnel
prioritize leads
review opportunities
detect stalled deals
recommend next actions
assign specialists
coordinate with Marketing
coordinate with Legal
coordinate with Finance
coordinate with Tech
review specialist outputs
forecast future revenue
escalate founder-required decisions
summarize learning
```

The Sales Lead should not spend all of its context writing cold emails.

---

# 8. Prospecting Specialist

Purpose:

```text
find possible customers
research organizations
identify relevant contacts
enrich lead data
match ICP
find buying triggers
prepare evidence-backed target rationale
```

Structured output:

```yaml
prospect_candidate:
  account_name:
  contact_name:
  role:
  source:
  fit_reason:
  problem_hypothesis:
  buying_trigger:
  evidence_refs: []
  confidence:
```

Do not directly contact a candidate before qualification/policy.

---

# 9. Qualification Specialist

Use a structured qualification model.

Recommended V13.2 dimensions:

```text
FIT
NEED
URGENCY
AUTHORITY
ABILITY_TO_PAY
```

Result:

```text
QUALIFIED
DISQUALIFIED
NEEDS_DISCOVERY
```

Do not rely only on an opaque 0–100 score.

---

# 10. Three Separate Scores

Use:

```text
fit_score
intent_score
engagement_score
```

Example:

```text
Lead A
Fit        90
Intent     20
Engagement 10

Lead B
Fit        70
Intent     85
Engagement 90
```

This is more explainable than:

```text
Lead Score = 78
```

---

# 11. Core CRM Entities

V13.2 must distinguish:

```text
Account
Contact
Lead
Opportunity
Customer
```

Definitions:

## Account

Organization or buying entity.

## Contact

Human person related to an Account.

## Lead

A Contact/Account being evaluated or nurtured for a potential sale.

## Opportunity

A qualified commercial opportunity with real potential value.

## Customer

An Account with at least one accepted/won relationship under the current product/business rules.

---

# 12. Account Entity

```yaml
account:
  id:
  organization_id:
  name:
  domain:
  industry:
  size_segment:
  country:
  source:
  lifecycle_status:
  owner_id:
  tags: []
  created_at:
  updated_at:
```

Lifecycle:

```text
TARGET
PROSPECT
CUSTOMER
FORMER_CUSTOMER
PARTNER
DISQUALIFIED
```

---

# 13. Contact Entity

```yaml
contact:
  id:
  organization_id:
  account_id: optional
  name:
  title:
  email:
  phone:
  social_profiles:
  source:
  consent_status:
  do_not_contact:
  owner_id:
  tags: []
  created_at:
  updated_at:
```

Do not duplicate a person per campaign.

---

# 14. Lead Entity

```yaml
lead:
  id:
  organization_id:
  account_id: optional
  contact_id: optional
  source:
  source_campaign_id: optional
  status:
  fit_score:
  intent_score:
  engagement_score:
  qualification_status:
  owner_id:
  last_contact_at:
  next_action_at:
  next_action_type:
  disqualification_reason: optional
  cycle_id: optional
  linked_kr_id: optional
  created_at:
  updated_at:
```

Lead status:

```text
NEW
RESEARCHING
QUALIFYING
QUALIFIED
NURTURING
DISQUALIFIED
CONVERTED
```

---

# 15. Opportunity Entity

```yaml
opportunity:
  id:
  organization_id:
  account_id:
  primary_contact_id:
  owner_id:
  cycle_id:
  linked_kr_id:
  product:
  stage:
  estimated_value:
  currency:
  probability:
  expected_close_date:
  source:
  pain_points: []
  needs: []
  objections: []
  competitors: []
  next_action:
  next_action_due_at:
  status:
  won_reason: optional
  lost_reason: optional
  created_at:
  updated_at:
```

---

# 16. Opportunity Stages

Recommended:

```text
DISCOVERY
QUALIFIED
SOLUTION
PROPOSAL
NEGOTIATION
WON
LOST
```

Do not overload funnel with too many custom stages initially.

---

# 17. Customer Entity

```yaml
customer:
  id:
  organization_id:
  account_id:
  acquired_from_opportunity_id:
  lifecycle_status:
  activation_status:
  owner_id:
  first_purchase_at:
  renewal_date: optional
  health_status:
  last_success_interaction_at:
  next_success_action_at:
  created_at:
  updated_at:
```

Lifecycle:

```text
ONBOARDING
ACTIVE
WATCH
AT_RISK
CHURNED
EXPANSION
```

---

# 18. Activity Entity

Every meaningful sales interaction should be stored structurally.

```yaml
sales_activity:
  id:
  organization_id:
  entity_type:
  entity_id:
  activity_type:
  channel:
  direction:
  summary:
  outcome:
  next_action:
  actor_id:
  occurred_at:
  artifact_refs: []
```

Activity types:

```text
RESEARCH
EMAIL
MESSAGE
CALL
MEETING
DEMO
PROPOSAL
FOLLOW_UP
NOTE
STATUS_CHANGE
```

---

# 19. Sales Funnel

Default funnel:

```text
TARGET
  ↓
LEAD
  ↓
QUALIFIED
  ↓
ENGAGED
  ↓
OPPORTUNITY
  ↓
PROPOSAL
  ↓
WON / LOST
  ↓
CUSTOMER
  ↓
RENEW / EXPAND / REFER
```

User-facing UI may simplify to:

```text
Leads
Qualified
Opportunity
Proposal
Won
```

---

# 20. Prospecting Workflow

```text
Current Cycle / KR
      ↓
ICP / Target Profile
      ↓
Prospecting Specialist
      ↓
Candidate Leads
      ↓
Enrichment
      ↓
Deduplication
      ↓
Qualification
      ↓
Sales Lead Review
      ↓
CRM
```

Do not auto-contact raw candidates.

---

# 21. Marketing → Sales Handoff

Reuse V13.1 structured Handoff.

Marketing sends:

```text
lead
campaign source
ICP context
message context
engagement evidence
qualification hypothesis
```

Sales returns:

```text
qualified?
opportunity?
lost/disqualified reason?
customer outcome?
```

This creates the Marketing→Revenue learning loop.

---

# 22. Outreach / SDR Workflow

After qualification:

```text
Qualified Lead
    ↓
Account/Contact Research
    ↓
Outreach Draft
    ↓
Review / Approval
    ↓
Sequence
    ↓
Response / No Response
    ↓
Opportunity / Nurture / Stop
```

---

# 23. Sales Channel Gateway

Create abstraction:

```text
SalesChannelGateway
```

Future adapters:

```text
Email
LinkedIn
Zalo
Telegram
SMS
Phone
```

V13.2 should not hard-code channel-specific logic into Sales domain.

---

# 24. Sales Sequence

```yaml
sales_sequence:
  id:
  organization_id:
  name:
  target_segment:
  status:
  stop_conditions: []
  created_by:
```

```yaml
sequence_step:
  id:
  sequence_id:
  position:
  day_offset:
  channel:
  action_type:
  template_ref:
  requires_approval:
```

Example:

```text
Day 0  Personalized introduction
Day 3  Follow-up
Day 7  Value/example
Day 12 Final follow-up
```

---

# 25. Mandatory Sequence Stop Conditions

```text
customer replies
customer opts out
lead becomes disqualified
opportunity created
customer requests no contact
max touches reached
manual stop
```

No unlimited AI outreach.

---

# 26. Outreach Governance

Initial autonomy:

```text
First outreach
→ founder approval

Approved sequence follow-ups
→ may use Cycle Grant

New pricing
→ review

New proposal
→ review

Binding terms
→ Legal / founder approval
```

Do not optimize for message volume.

---

# 27. Deal Copilot

Once qualified interest exists:

```text
Lead
→ Opportunity
```

Deal Copilot responsibilities:

```text
prepare discovery
research account
prepare meeting brief
capture pain points
capture requirements
capture objections
recommend next action
prepare deal strategy
prepare proposal
coordinate blockers
track stalled deals
```

---

# 28. Founder-Led Selling Mode

For OPC, default:

```text
AI prepares
Founder sells
AI records
AI follows up
```

The founder remains responsible for:

```text
high-value discovery
relationship building
negotiation
strategic customers
pricing exception
final commercial commitment
```

This preserves trust while multiplying founder capacity.

---

# 29. LiveKit Sales Copilot

Internal voice use cases:

```text
"COSA, sales hôm nay thế nào?"
"Chuẩn bị call với ABC."
"Khách này đang ở stage nào?"
"Tôi nên hỏi gì trong cuộc gọi?"
"Deal nào cần tôi?"
"Tại sao XYZ bị đứng?"
"Khách này đã phản đối điều gì?"
"Follow-up tiếp theo là gì?"
```

Do not implement customer-facing AI telephony in V13.2.

---

# 30. Pre-Meeting Brief

Sales Copilot should return:

```text
Account
Contact
Role
Why they may buy
Last interaction
Known pain
Known objection
Current opportunity stage
Goal for this call
Top discovery questions
Commercial guardrails
Open blockers
```

---

# 31. Post-Meeting Capture

Founder says:

> “Khách thích nhưng lo về bảo mật và giá.”

COSA creates:

```text
Meeting Activity
Objection: SECURITY
Objection: PRICING
```

Then Company Runtime can create:

```text
Tech WorkItem
→ Security architecture brief

Finance WorkItem
→ Pricing/margin check

Sales WorkItem
→ Follow-up
```

---

# 32. Proposal Workflow

```text
Opportunity
  ↓
Discovery complete
  ↓
Commercial inputs
  ↓
Finance pricing/margin validation
  ↓
Legal term review when required
  ↓
Proposal draft
  ↓
Review
  ↓
Founder/customer delivery
```

Proposal must never invent price or legal terms.

---

# 33. Proposal Entity

```yaml
sales_proposal:
  id:
  opportunity_id:
  version:
  status:
  problem_summary:
  solution_summary:
  scope:
  timeline:
  pricing_ref:
  commercial_terms_ref:
  assumptions: []
  artifact_id:
  approved_by:
  created_at:
```

Status:

```text
DRAFT
INTERNAL_REVIEW
APPROVED
SENT
ACCEPTED
REJECTED
SUPERSEDED
```

---

# 34. Pricing Boundary

Pricing source:

```text
Pricing Service
Finance rules
Approved commercial policies
```

LLM may explain and draft but not invent:

```text
price
discount
margin
payment terms
tax treatment
```

---

# 35. Sales → Finance Workflow

```text
Opportunity
   ↓
Proposed Price
   ↓
Finance
   ↓
Margin / Cash Impact
   ↓
Commercial Range
   ↓
Sales Proposal
```

When WON:

```text
Opportunity WON
   ↓
Finance Handoff
   ↓
Receivable / Invoice / Payment Tracking
```

---

# 36. Discount Approval

Model:

```text
standard discount range
→ auto/low-risk policy

above threshold
→ Needs You

below margin floor
→ Finance Blocker + Needs You
```

Use existing V13.1 Cycle Grant and Policy Engine.

---

# 37. Sales → Legal Workflow

Escalate when:

```text
custom contract
liability
refund condition
data processing
IP ownership
custom SLA
binding commercial exception
```

Flow:

```text
Sales
→ Legal Handoff
→ Legal WorkItem
→ Artifact/Decision
→ Sales resumes
```

---

# 38. Sales → Tech Workflow

When customer asks:

```text
security
integration
architecture
roadmap
technical feasibility
feature gap
```

Sales must not hallucinate promises.

Flow:

```text
Sales Blocker
→ Tech
→ Technical Artifact
→ Sales
```

---

# 39. Closed Won Workflow

```text
Opportunity
  ↓
WON
  ↓
Customer created/activated
  ↓
Finance handoff
  ↓
Customer Success onboarding
```

WON is not the end of revenue management.

---

# 40. Customer Success Lifecycle

```text
WON
 ↓
ONBOARD
 ↓
ACTIVATE
 ↓
ADOPT
 ↓
HEALTH
 ↓
RETAIN
 ↓
RENEW
 ↓
EXPAND
 ↓
REFER
```

Customer Success remains under Revenue/Sales for V13.2.

---

# 41. Customer Success Specialist

Responsibilities:

```text
onboarding checklist
activation monitoring
scheduled check-ins
open issue follow-up
customer health
renewal tracking
upsell signals
referral opportunities
churn-risk detection
```

---

# 42. Customer Health

Use deterministic/rule-based signals first.

Inputs may include:

```text
product usage
payment status
support incidents
last interaction
feature adoption
customer feedback
renewal proximity
```

Output:

```text
HEALTHY
WATCH
AT_RISK
```

LLM explains reasons; rules/data determine base status.

---

# 43. Churn Workflow

```text
Risk Signal
   ↓
Customer Success
   ↓
Reason classification
   ↓
Recovery action
```

Routing:

```text
price
→ Sales + Finance

bug
→ Tech

contract/legal
→ Legal

poor adoption
→ Customer Success / Product
```

---

# 44. Expansion Workflow

```text
usage/value signal
   ↓
Expansion Candidate
   ↓
Opportunity type = EXPANSION
   ↓
Sales
```

Finance only records actual result after commercial/accounting event.

---

# 45. Referral Workflow

Trigger candidates when:

```text
customer healthy
+
value milestone achieved
+
positive feedback
```

COSA recommends:

> Ask for a referral now.

Do not automatically solicit every customer.

---

# 46. Lost Deal Reasons

Required for `LOST`:

```text
PRICE
NO_NEED
NO_BUDGET
TIMING
COMPETITOR
TRUST
FEATURE_GAP
NO_RESPONSE
LEGAL
TECHNICAL
OTHER
```

Store both:

```text
structured reason
free-text evidence
```

---

# 47. Won Deal Reasons

Capture:

```text
why they bought
what value mattered
what channel/source worked
what objection was overcome
what trust signal mattered
```

This becomes high-value input to Marketing and Sales learning.

---

# 48. Revenue Learning Loop

```text
Lead Source
   ↓
Qualification
   ↓
Opportunity
   ↓
Won / Lost
   ↓
Customer Outcome
   ↓
Finance Actual
   ↓
Learning
   ↓
Marketing + Sales
```

The learning target is not:

```text
likes
impressions
emails sent
```

The learning target is:

```text
qualified demand
conversion
revenue
cash
retention
```

---

# 49. Sales Learning Entity

Reuse generic V13.1 Lesson but add structured sales context.

```yaml
sales_learning_context:
  lesson_id:
  account_segment:
  lead_source:
  funnel_stage:
  product:
  opportunity_id: optional
  campaign_id: optional
  won_lost_reason: optional
```

Do not create a separate learning engine.

---

# 50. Agent Experience

Confirmed lessons can update Sales Lead experience:

```text
successful patterns
failed patterns
common objections
effective channels
effective discovery sequence
pricing concerns
segment-specific conversion patterns
```

Use PostgreSQL first.

Agent Memory remains optional.

---

# 51. Funnel Metrics

Initial metrics:

```text
New Leads
Qualified Leads
Opportunities
Pipeline Value
Win Rate
Average Sales Cycle
Revenue Won
Retention / Renewal
Stalled Opportunities
```

Do not create dozens of vanity metrics.

---

# 52. FunnelMetricsService

Deterministic service calculates:

```text
lead_to_qualified_rate
qualified_to_opportunity_rate
opportunity_to_won_rate
average_sales_cycle_days
pipeline_value
weighted_pipeline
stage_velocity
```

No LLM arithmetic as source of truth.

---

# 53. Weighted Pipeline

```text
weighted value
=
estimated deal value × stage/deal probability
```

Store:

```text
raw_pipeline
weighted_pipeline
```

Probability source must be explicit:

```text
manual
stage-default
data-driven
AI-recommended-not-confirmed
```

---

# 54. Sales Forecast

Forecast modes:

```text
COMMITTED
BEST_CASE
PIPELINE
```

Sales owns the forecast.

Finance may consume it for scenario analysis:

```text
cash projection
runway scenarios
budget planning
```

Finance must not convert forecast directly to actual accounting revenue.

---

# 55. SalesTargetCompiler

Add deterministic/planning service:

```text
SalesTargetCompiler
```

Inputs:

```text
KR target
deadline
average deal size
historical conversion rates
current pipeline
```

Outputs:

```text
required wins
required opportunities
required qualified leads
required leads
weekly sales targets
```

---

# 56. Backward Funnel Planning

Example:

```text
KR:
5 paying customers

Historical:
Opportunity → Won = 25%
Qualified → Opportunity = 40%
```

Compiler can estimate:

```text
~20 opportunities
~50 qualified leads
```

If history is absent:

```text
use explicit assumptions
mark as ASSUMPTION
```

Never present assumptions as proven forecast.

---

# 57. Sales Weekly Mission Integration

Example:

```text
COMPANY WEEKLY MISSION
Get first 2 qualified beta opportunities.
```

Sales work:

```text
Generate 30 targets
Qualify top 15
Contact 10
Book 3 discovery calls
Create 2 opportunities
```

Marketing work:

```text
Prepare segment-specific message/content
```

Founder work:

```text
Run discovery calls
```

This links sales execution directly to 12WY.

---

# 58. Sales Next Best Action Engine

Add:

```text
SalesNextBestActionService
```

Signals:

```text
stage
last interaction
reply state
next action deadline
deal value
engagement
blockers
intent
customer health
renewal date
```

Possible actions:

```text
CALL
FOLLOW_UP
WAIT
DISCOVER
QUALIFY
DISQUALIFY
PREPARE_PROPOSAL
RESOLVE_BLOCKER
ASK_FOR_DECISION
RENEW
UPSELL
ASK_REFERRAL
```

---

# 59. Opportunity Stall Detector

Rule-based first.

Example:

```text
Opportunity
+
no meaningful activity for X days
+
not intentionally waiting
→ STALLED
```

Sales Lead reviews:

```text
why stalled
next best action
whether founder intervention is required
```

---

# 60. Revenue Health

Add lightweight company-level view:

```text
Revenue Health
```

Dimensions:

```text
Demand
Pipeline
Conversion
Sales Velocity
Retention
Expansion
Cash Conversion
```

Status:

```text
HEALTHY
WATCH
AT_RISK
```

Do not collapse into one opaque score.

---

# 61. Sales + Finance = Company Viability

Finance answers:

```text
What actually happened financially?
```

Sales answers:

```text
What is likely to happen commercially?
```

Together:

```text
Actual Revenue
+
Actual Cash
+
Pipeline
+
Expected Close
+
Expected Cash
+
Burn
+
Runway
```

This supports company-level viability reasoning.

---

# 62. CEO Brief Revenue Section

Add:

```text
SALES

Pipeline             85m
Weighted Pipeline    32m
Opportunities        8
Deals At Risk        2
New Customers        2 / 5 KR

FINANCE

Actual Revenue       12m
Cash Collected        9m
Runway              8.7 months

NEEDS YOU
- Approve ABC proposal
- Decide XYZ pricing exception
```

Do not merge sales forecast with actual revenue.

---

# 63. CRM UX Principle

Do not build a mini-Salesforce.

Founder default Sales navigation:

```text
TODAY
FUNNEL
CUSTOMERS
INSIGHTS
```

Optional advanced screens can exist later.

---

# 64. Sales Today View

Show:

```text
Needs You
Next Best Actions
Deals At Risk
Today's Meetings
Follow-ups Due
Pipeline Snapshot
```

Example:

```text
SALES TODAY

Needs You: 2

Next Actions
1. Call ABC
2. Approve XYZ proposal
3. Follow up Minh

Pipeline
75m

At Risk
2 opportunities
```

---

# 65. Funnel View

Kanban-like:

```text
LEADS
QUALIFIED
OPPORTUNITY
PROPOSAL
WON
```

Stage transitions should call domain services, not only update UI state.

---

# 66. Customer View

Show:

```text
Customer
Product / Plan
Revenue relationship
Health
Last interaction
Next action
Renewal
Open issues
```

---

# 67. Sales Insights View

COSA should generate insights such as:

```text
Founder-community leads convert better than generic social leads.

Three recent losses mention missing integration X.

Average sales cycle increased because proposal approval is slow.

Customers who receive a live demo convert more often.

Two healthy customers are strong referral candidates.
```

Insights must link back to evidence.

---

# 68. Sales Activity Timeline

Account/Opportunity detail should show:

```text
research
messages
meetings
proposals
stage changes
blockers
handoffs
reviews
payments/revenue events summary
```

Do not rely on chat history as CRM history.

---

# 69. Automation Levels

Recommended:

## A1 — Recommend

```text
lead priority
next action
deal strategy
customer risk
```

## A2 — Draft

```text
outreach
follow-up
meeting brief
proposal draft
renewal message
```

## A3 — Execute with Policy

```text
send approved sequence
update CRM
schedule follow-up
create internal WorkItem
```

## A4 — Delegated

Only after sufficient trust/learning.

Do not begin with autonomous outbound spam.

---

# 70. Company Runtime Integration

Reuse V13.1:

```text
WorkItem
Work Contract
Dependency DAG
Review/Rework
Handoff
Blocker
Needs You
Cycle Grant
Learning
```

Examples:

```text
Marketing → Sales
qualified lead handoff

Sales → Legal
contract blocker

Sales → Finance
pricing blocker / won deal

Sales → Tech
technical blocker

Sales → Customer Success
won customer
```

No parallel Sales orchestration engine.

---

# 71. Sales Work Contracts

Examples:

## Prospecting

```text
Outcome:
20 ICP-matched leads with evidence.

Acceptance:
- deduplicated
- source recorded
- fit reason available
- contact method verified where possible
```

## Proposal

```text
Outcome:
Approved proposal ready for customer.

Acceptance:
- pricing approved
- legal terms checked when required
- scope clear
- artifact generated
```

## Customer Onboarding

```text
Outcome:
Customer reaches activation milestone.

Acceptance:
- onboarding completed
- owner assigned
- success metric confirmed
```

---

# 72. Sales Blocker Types

```text
NO_CONTACT
NO_RESPONSE
MISSING_DISCOVERY
PRICING_NEEDED
DISCOUNT_APPROVAL
LEGAL_REVIEW
TECHNICAL_QUESTION
PRODUCT_GAP
BUDGET_UNKNOWN
DECISION_MAKER_UNKNOWN
CUSTOMER_TIMING
PAYMENT_ISSUE
```

Use V13.1 BlockerRouter.

---

# 73. Needs You Sales Types

```text
PRICING_DECISION
DISCOUNT_EXCEPTION
STRATEGIC_CUSTOMER
PROPOSAL_APPROVAL
CONTRACT_DECISION
PRODUCT_COMMITMENT
NEGOTIATION_DECISION
CUSTOMER_ESCALATION
```

Founder should not receive routine follow-up tasks unless explicitly configured.

---

# 74. Database Additions — P0

Minimum:

```text
revenue_accounts
revenue_contacts
sales_leads
sales_opportunities
sales_activities
customers
```

Reuse:

```text
work_items
artifacts
handoffs
blockers
needs_you
lessons
approvals
```

---

# 75. Database Additions — P1/P2

Later:

```text
lead_scores
sales_sequences
sales_sequence_steps
sales_messages
sales_meetings
sales_proposals
customer_health_snapshots
customer_success_actions
sales_forecasts
sales_targets
sales_learning_context
```

Do not create every table in the first migration unless needed.

---

# 76. FastAPI Structure

Suggested:

```text
app/functions/sales/
  domain/
    accounts.py
    contacts.py
    leads.py
    opportunities.py
    customers.py
    activities.py
    qualification.py
    funnel.py
    forecasts.py
    sequences.py
    proposals.py
    customer_success.py

  application/
    sales_lead_service.py
    prospecting_service.py
    qualification_service.py
    lead_scoring_service.py
    funnel_metrics_service.py
    sales_target_compiler.py
    next_best_action_service.py
    stall_detector.py
    proposal_service.py
    customer_health_service.py
    revenue_attribution_service.py

  api/
    routes.py
```

---

# 77. Flutter Structure

```text
lib/features/ai_team/sales/
  domain/
  data/
  presentation/
    sales_today_page.dart
    funnel_page.dart
    opportunity_detail_page.dart
    customer_page.dart
    sales_insights_page.dart
    sales_meeting_brief.dart
```

Use existing GetX conventions.

---

# 78. API Sketch — CRM

```text
POST /sales/accounts
GET  /sales/accounts
GET  /sales/accounts/{id}

POST /sales/contacts
GET  /sales/contacts/{id}

POST /sales/leads
GET  /sales/leads
POST /sales/leads/{id}/qualify
POST /sales/leads/{id}/convert

POST /sales/opportunities
GET  /sales/opportunities
GET  /sales/opportunities/{id}
POST /sales/opportunities/{id}/stage
POST /sales/opportunities/{id}/win
POST /sales/opportunities/{id}/lose

GET  /sales/customers
GET  /sales/customers/{id}
```

---

# 79. API Sketch — Intelligence

```text
GET  /sales/funnel
GET  /sales/metrics
GET  /sales/forecast
GET  /sales/next-actions
GET  /sales/stalled
GET  /sales/revenue-health
POST /sales/targets/compile
```

---

# 80. API Sketch — Execution

```text
POST /sales/prospect
POST /sales/leads/{id}/draft-outreach
POST /sales/leads/{id}/create-sequence
POST /sales/opportunities/{id}/meeting-brief
POST /sales/opportunities/{id}/proposal
POST /sales/customers/{id}/success-action
```

All consequential actions must use Policy/Approval.

---

# 81. Feature Flags

```yaml
features:

  revenue_os_v13_2: true

  sales_crm_core_v13_2: true
  account_contact_v13_2: true
  lead_management_v13_2: true
  opportunity_management_v13_2: true
  customer_core_v13_2: true

  sales_lead_agent_v13_2: true
  sales_next_best_action_v13_2: true
  marketing_sales_handoff_v13_2: true
  sales_finance_handoff_v13_2: true
  sales_legal_handoff_v13_2: true
  sales_tech_handoff_v13_2: true

  prospecting_agent_v13_2: false
  outreach_sequence_v13_2: false
  customer_success_v13_2: false
  sales_forecast_v13_2: false
  revenue_health_v13_2: false
  sales_voice_copilot_v13_2: false

  customer_facing_ai_calls: false
  autonomous_cold_outreach: false
```

Enable progressively.

---

# 82. P0 Implementation Scope

Implement first:

```text
Account
Contact
Lead
Opportunity
Customer

Lead qualification
Opportunity stages
Sales Activity
Next Action
Sales Lead Agent
Marketing→Sales handoff
Sales→Finance handoff
Sales→Legal handoff
Sales→Tech handoff
Won/Lost
Basic Funnel
Basic Sales Today
```

This is the minimum viable Revenue OS.

---

# 83. P1 Implementation Scope

Add:

```text
Prospecting Specialist
Lead scoring
Outreach drafts
Sales Sequence
Meeting Brief
Proposal workflow
Stalled Deal Detector
Sales Next Best Action
LiveKit internal Sales Copilot
```

---

# 84. P2 Implementation Scope

Add:

```text
Customer Success
Customer Health
Renewal
Expansion
Referral
Churn Risk
```

---

# 85. P3 Implementation Scope

Add:

```text
Sales Forecast
Backward Funnel Planning
Revenue Health
Revenue Attribution
Segment Learning
Marketing→Sales→Finance intelligence
```

---

# 86. Migration from Existing V13.1

V13.2 is additive.

## Step 1

Inventory existing Sales Function implementation.

Classify:

```text
KEEP
EXTEND
MIGRATE
HIDE
```

## Step 2

Map current Sales WorkItems to:

```text
Lead
Opportunity
Customer
```

where meaningful.

## Step 3

Add CRM tables.

## Step 4

Add Sales domain services.

## Step 5

Reuse V13.1 Handoff/Blocker/Needs You.

## Step 6

Connect existing Finance.

## Step 7

Connect Marketing lead source.

## Step 8

Enable one Cycle with real funnel.

Do not delete current Sales code before compatibility mapping.

---

# 87. Source of Truth Rules

```text
Lead/Opportunity/Customer state
→ PostgreSQL Sales domain

Work execution
→ V10/V13 WorkItem/Run

Actual accounting/cash
→ Finance

Learning
→ existing Lessons / Learning domain

Agent memory
→ optional recall only
```

Never let LLM memory override CRM stage.

---

# 88. Data Integrity

Required:

```text
lead deduplication
contact deduplication
account deduplication
stage transition validation
activity history
won/lost reason
next-action consistency
audit on pricing/proposal status
idempotent external message creation
```

---

# 89. Privacy and Outreach Safety

Sales must respect:

```text
consent status
do_not_contact
channel restrictions
opt-out
sender policy
rate limits
manual stop
```

Do not build a spam engine.

---

# 90. Sales Channel Security

For external messages:

```text
approved sender identity
allowed channel
approved sequence
idempotency key
audit event
```

Unknown/unapproved channels:

```text
deny
```

---

# 91. LiveKit Sales Voice Scope

Enable internal founder copilot only:

```text
Sales status
Meeting preparation
Opportunity lookup
Next action
Blocker explanation
Needs You
Proposal status
Customer health
```

Keep disabled:

```text
AI cold calling
AI customer negotiation
AI autonomous telephony
```

---

# 92. Sales Voice Examples

```text
"COSA, sales hôm nay thế nào?"

"Có deal nào sắp close?"

"Chuẩn bị call với ABC."

"Tại sao XYZ bị đứng?"

"Khách ABC phản đối điều gì?"

"Ai cần tôi follow-up?"

"Deal nào có giá trị cao nhưng rủi ro?"

"Khách nào có nguy cơ churn?"
```

---

# 93. Revenue Section in Week 13

Week 13 should review:

```text
Lead sources
Qualified leads
Opportunities
Proposals
Win rate
Sales cycle
Won revenue
Actual cash from Finance
Lost reasons
Customer health
Renewal
Expansion
Founder sales time
Lessons
```

---

# 94. Revenue Learning in Week 13

Generate:

```text
What channels created qualified demand?
Which segments converted?
Why did customers buy?
Why did deals fail?
What objections repeated?
Where did founder attention bottleneck?
Which customers are likely to expand?
Which Sales skills/checklists should improve?
```

---

# 95. Golden Scenario 1 — KR to Funnel

KR:

```text
Get 5 paying customers.
```

Expected:

```text
SalesTargetCompiler
→ funnel assumptions
→ weekly target
→ leads
→ qualification
→ opportunities
→ proposals
→ won customers
→ Finance handoff
→ actual cash/revenue
```

---

# 96. Golden Scenario 2 — Marketing to Sales

Marketing campaign generates 10 leads.

Expected:

```text
Marketing Handoff
→ 10 Lead records
→ dedupe
→ qualification
→ 4 qualified
→ Sales Next Actions
→ 2 opportunities
```

Marketing receives downstream quality feedback.

---

# 97. Golden Scenario 3 — Founder Discovery Call

Before call:

```text
LiveKit
→ meeting brief
```

After call:

```text
Founder voice note
→ Activity
→ pain points
→ objections
→ next action
→ Tech/Finance blocker if needed
```

---

# 98. Golden Scenario 4 — Proposal

Opportunity:

```text
customer wants proposal
```

Expected:

```text
Sales
→ Finance pricing validation
→ Legal review if required
→ Proposal Artifact
→ founder approval
→ SENT
```

No price hallucination.

---

# 99. Golden Scenario 5 — Won to Finance

Opportunity becomes WON.

Expected:

```text
Customer created
→ Finance Handoff
→ receivable/invoice tracking
→ Customer Success onboarding
```

Sales pipeline updates but actual revenue remains Finance-owned.

---

# 100. Golden Scenario 6 — Lost Learning

Three deals lost with:

```text
FEATURE_GAP = integration X
```

Expected:

```text
Lost Reason analysis
→ Lesson Candidate
→ Sales/Marketing insight
→ Tech/Product improvement candidate
```

---

# 101. Golden Scenario 7 — Churn Risk

Customer:

```text
no usage + payment issue
```

Expected:

```text
Customer Health = AT_RISK
→ Customer Success WorkItem
→ Finance check
→ founder escalation only if needed
```

---

# 102. Acceptance Criteria — P0

P0 is complete when:

1. Account/Contact/Lead/Opportunity/Customer are distinct entities.
2. Lead can be qualified/disqualified.
3. Qualified Lead can convert to Opportunity.
4. Opportunity has validated stage transitions.
5. Opportunity can be WON or LOST.
6. Won/Lost reason is captured.
7. Sales Activity history is visible.
8. Next Action is stored.
9. Sales Lead Agent can summarize funnel.
10. Marketing can hand off leads to Sales.
11. Sales can hand off pricing to Finance.
12. Sales can hand off legal issues to Legal.
13. Sales can hand off technical issues to Tech.
14. WON creates Customer.
15. WON can trigger Finance handoff.
16. Sales state remains PostgreSQL source of truth.
17. Finance remains source of actual economic truth.
18. Existing V13.1 Company Runtime is reused.
19. No second WorkItem engine is created.
20. No autonomous spam workflow is enabled.

---

# 103. Acceptance Criteria — P1

1. Prospecting can create candidate leads with evidence.
2. Lead deduplication works.
3. Lead scoring exposes fit/intent/engagement separately.
4. Outreach draft can be generated.
5. Sequence supports stop conditions.
6. Stalled opportunity detection works.
7. Meeting Brief works.
8. Proposal uses Finance-approved price source.
9. LiveKit can retrieve internal sales status.
10. Needs You receives material Sales decisions.

---

# 104. Acceptance Criteria — P2

1. Customer onboarding exists.
2. Customer health status is deterministic/rule-backed.
3. At-risk customers create WorkItems.
4. Renewal is tracked.
5. Expansion can create a new Opportunity.
6. Referral candidate can be suggested.
7. Customer Success remains inside Revenue Function.

---

# 105. Acceptance Criteria — P3

1. Funnel metrics are deterministic.
2. Weighted pipeline is deterministic.
3. Sales forecast is separate from Finance actuals.
4. SalesTargetCompiler supports KR backward planning.
5. Revenue Health is explainable.
6. Marketing source can be attributed to qualified/won outcomes.
7. Finance actuals can be compared with Sales forecast.
8. Week 13 creates revenue learning.

---

# 106. Claude Code Mandatory Rules

Claude Code must:

1. Treat V13 and V13.1 as implemented baselines.
2. Add V13.2 incrementally.
3. Never create a second runtime.
4. Never create a second WorkItem engine.
5. Never use agent memory as CRM truth.
6. Keep PostgreSQL as Sales source of truth.
7. Keep Finance as actual revenue/cash/accounting source of truth.
8. Keep Marketing as demand-generation owner.
9. Keep Customer Success inside Sales/Revenue for V13.2.
10. Reuse V13.1 Handoff/Blocker/Needs You.
11. Reuse existing Policy/Approval Engine.
12. Keep LiveKit as founder interface only.
13. Keep customer-facing AI telephony disabled.
14. Keep autonomous cold outreach disabled by default.
15. Enforce sequence stop conditions.
16. Respect do-not-contact and opt-out.
17. Use deterministic services for metrics and forecasts.
18. Do not let LLM calculate authoritative pipeline metrics.
19. Do not let LLM invent pricing.
20. Do not let Sales promise technical capability without Tech artifact.
21. Do not let Sales promise legal terms without Legal review.
22. Do not treat WON as Finance actual revenue.
23. Use additive migrations.
24. Preserve existing Sales data where possible.
25. Add idempotency to external messages.
26. Add audit events for proposal/pricing/stage transitions.
27. Add golden tests before enabling automation.
28. Implement P0 before P1/P2/P3.
29. Prefer founder-copilot workflows before autonomous seller workflows.
30. Keep feature scope focused on revenue outcomes, not CRM feature parity.

---

# 107. ADRs

Create:

```text
ADR-V13-2-001 Sales Function Becomes Revenue Operating Domain
ADR-V13-2-002 Marketing vs Sales vs Finance Boundaries
ADR-V13-2-003 Account/Contact/Lead/Opportunity/Customer Model
ADR-V13-2-004 Sales Forecast Is Not Accounting Revenue
ADR-V13-2-005 Founder-Led Selling Default
ADR-V13-2-006 Deterministic Funnel Metrics
ADR-V13-2-007 Customer Success Inside Revenue Function
ADR-V13-2-008 Sales Channel Gateway
ADR-V13-2-009 No Autonomous Spam
ADR-V13-2-010 Marketing→Sales→Finance Learning Loop
ADR-V13-2-011 LiveKit Internal Sales Copilot
ADR-V13-2-012 Sales Target Backward Planning from KRs
```

---

# 108. Sprint Plan

## Sprint 1 — CRM Core

```text
Account
Contact
Lead
Opportunity
Customer
Activity
```

## Sprint 2 — Funnel + Qualification

```text
Qualification
Stage transitions
Won/Lost
Next Action
Basic Funnel
Sales Today
```

## Sprint 3 — Company Runtime Integration

```text
Marketing→Sales handoff
Sales→Finance handoff
Sales→Legal handoff
Sales→Tech handoff
Blockers
Needs You
```

## Sprint 4 — Sales Lead Agent

```text
Pipeline summary
Lead priority
Opportunity priority
Stalled detection
Internal insights
```

## Sprint 5 — Founder Sales Copilot

```text
Meeting Brief
Post-meeting capture
LiveKit internal commands
```

## Sprint 6 — Proposal + Outreach

```text
Proposal workflow
Finance pricing validation
Legal review
Outreach drafts
Sequences
```

## Sprint 7 — Customer Success

```text
Onboarding
Health
Retention
Renewal
Expansion
Referral
```

## Sprint 8 — Revenue Intelligence

```text
Funnel metrics
Forecast
SalesTargetCompiler
Revenue Health
Attribution
Week 13 learning
```

---

# 109. Rollout Strategy

```text
Developer Workspace
→ one real/test Cycle
→ manual CRM data
→ Marketing handoff
→ founder-led sales
→ proposal workflow
→ Finance handoff
→ customer success
→ controlled outreach automation
```

Do not begin with autonomous prospecting + sending.

---

# 110. Product Success Metrics

Sales Function:

```text
qualified leads
opportunities
win rate
sales cycle
revenue won
founder sales hours
stalled deals
customer retention
expansion
```

System:

```text
% opportunities with clear next action
% won deals reaching Finance correctly
% lost deals with structured reason
% leads traceable to source
% customer risks acted on before churn
```

---

# 111. Founder Attention Objective

Sales automation should reduce:

```text
manual lead research
manual CRM updates
forgotten follow-ups
meeting preparation time
pipeline checking
cross-function chasing
```

Founder attention should be reserved for:

```text
discovery
relationship
negotiation
strategic decisions
high-value customer interaction
```

---

# 112. Final Architecture

```text
                         FOUNDER
                            │
                         LiveKit
                            │
                            ▼
                          COSA
                    AI Chief of Staff
                            │
                       Current Cycle
                            │
                           OKRs
                            │
                     Weekly Mission
                            │
                    Company Runtime
                            │
       ┌──────────────┬─────┼─────┬──────────────┐
       ▼              ▼     ▼     ▼              ▼
     Legal        Marketing Sales Tech         Finance
                      │      │                   │
                      │      ▼                   │
                      │  Revenue Function        │
                      │      │                   │
                      │  ┌───┼─────────┐         │
                      │  ▼   ▼         ▼         │
                      │ Leads Deals Customers    │
                      │  │   │         │         │
                      └──┼───┼─────────┘         │
                         │   │                   │
                         ▼   ▼                   │
                       Funnel WON ───────────────┤
                             │                   │
                             ▼                   ▼
                         Customer             Actual
                          Success         Revenue/Cash
                             │                   │
                             └─────────┬─────────┘
                                       ▼
                                    Learning
                                       │
                          ┌────────────┴────────────┐
                          ▼                         ▼
                      Marketing                   Sales
```

---

# 113. Final Implementation Principle

V13.2 should make Sales responsible for **commercial continuity**, not just outbound activity.

The full responsibility is:

> **Find the right customers → qualify real buying potential → manage the funnel → help the founder sell → coordinate Legal/Finance/Tech blockers → close deals → hand off to Finance → onboard and retain customers → expand/referral → learn from won/lost/customer outcomes.**

The company-level interpretation is:

> **Marketing tells COSA where demand comes from. Sales tells COSA where future revenue is likely to come from. Finance tells COSA what revenue, cash and profit actually occurred. Learning continuously improves all three.**

This is the Revenue Operating System that should sit inside COSA V13.2.
