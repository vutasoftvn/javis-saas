# COSA Capital Network & Investor Intelligence Specification

**Status:** Draft v1.0  
**Date:** 2026-08-21  
**Purpose:** Thiết kế chi tiết lớp Capital Network/Investor Intelligence cho COSA, tích hợp trực tiếp với Company Operating System, Project Portfolio, Startup Methodology, Validation/Evidence và kiến trúc Local PostgreSQL ↔ Central PostgreSQL hiện có.  
**Recommended repository path:** `docs/architecture/COSA_CAPITAL_NETWORK_INVESTOR_INTELLIGENCE.md`

---

## 1. Executive Summary

COSA Capital Network không được thiết kế như một “startup directory” hay một marketplace nơi founder tự nhập lại pitch deck. Nó phải là **lớp mạng vốn được sinh tự động từ dữ liệu vận hành có cấu trúc của COSA**.

```text
Founder operates startup in COSA
        ↓
COSA accumulates structured operating truth
        ↓
Local PostgreSQL
        ↓
Reliable event sync
        ↓
Central PostgreSQL
        ↓
Platform Intelligence
        +
Investor Projection
        +
Capital Network
        ↓
COSA Investor Mobile/Web
        ↓
Investor Discovery / Evaluation / Comments / Strategic Proposals
        ↓
Investor Signals return to startup
        ↓
AI Co-founder analyzes signals using private operating context
        ↓
Founder Decision / Next Best Action
```

COSA có hai trạng thái visibility đối với investor:

```text
PRIVATE
= Investor không được xem Company và Project.

PUBLIC
= Investor được xem Company + Material Project Portfolio
  thông qua Standard Investor Projection của COSA.
```

`PRIVATE/PUBLIC` chỉ là **investor visibility**, không quyết định việc dữ liệu nghiệp vụ có được đồng bộ về COSA Central cho mục đích platform operation/intelligence hay không.

Các nguyên tắc cốt lõi:

1. Central database của COSA là PostgreSQL, tách connection qua `CONTROL_PLANE_DATABASE_URL`.
2. Local PostgreSQL tiếp tục là source of truth của startup/company.
3. Central PostgreSQL là network/platform authority cho identity, public projection, investor network, community signals, capital relationships và platform analytics.
4. Không replicate thô toàn bộ local database; chỉ đồng bộ aggregate, state và analytics data được policy cho phép.
5. Khi Company chuyển sang `PUBLIC`, COSA tự động tạo và duy trì **Standard Investor Profile**; founder không cần nhập lại hồ sơ gọi vốn.
6. Investor nhìn Company trước, sau đó nhìn portfolio Project; một Project có thể hấp dẫn hơn company hiện tại và có thể dẫn đến đề xuất focus, stop, merge, direct project investment hoặc spin-out thành NewCo.
7. Founder/Co-founder phải là first-class public entities.
8. Verified investor có thể comment/evaluate công khai và gửi structured strategic proposal.
9. Investor opinions không tự động trở thành business evidence.
10. AI Co-founder sử dụng private operating context để phân tích investor signal, nhưng không tiết lộ private data cho investor.
11. COSA Platform Intelligence có thể dùng dữ liệu private được sync để cải tiến product/methodology/model, nhưng operator access và investment access phải được tách rõ.

---

## 2. Architectural Basis in Current COSA

### 2.1 PostgreSQL Local + PostgreSQL Central

Repository hiện đã cấu hình:

```text
DATABASE_URL
CONTROL_PLANE_DATABASE_URL
```

`CONTROL_PLANE_DATABASE_URL` được mô tả là Control Plane DB tách riêng khỏi app DB để có thể đổi sang managed PostgreSQL mà không đổi application architecture.

Vì vậy kiến trúc mới phải dùng thuật ngữ:

```text
Local PostgreSQL
Central PostgreSQL
```

Các comment/spec cũ còn ghi “Supabase Central” nên được xem là technical debt về nomenclature và cần cleanup dần, không phải dependency kiến trúc mới.

### 2.2 Existing synchronization primitives

COSA đã có:

```text
PlatformOutbox
PlatformInbox
PlatformOutboxService
sync worker
event envelope
data classification
retry
acknowledgement
```

`PlatformOutbox` hỗ trợ:
- event_id;
- event_type;
- aggregate_type;
- aggregate_id;
- company_id;
- classification;
- payload;
- retry/status tracking.

Đây là nền tảng phù hợp để bổ sung investor/public/network events. Không tạo sync engine thứ hai.

### 2.3 Existing data classification

Current `DataClassificationEnum`:

```text
PLATFORM_REQUIRED
ANALYTICS_REQUIRED
PUBLIC
COMPANY_PRIVATE
SENSITIVE
SECRET
```

Đây là seam tốt để xây publication/network policy. Không cần tạo một classification vocabulary song song nếu enum hiện tại có thể được formalize/extend.

### 2.4 Existing platform identity

Current models đã có:

```text
User.platform_user_id
Workspace.platform_company_id
Project.platform_project_id
```

Do đó Central identity có thể reuse UUID mapping hiện có. Không tạo thêm một global identity system cho cùng Company/Project.

### 2.5 Existing startup Project model

`Project` hiện có:
- workspace_id;
- title;
- description;
- status;
- project_type;
- strategic_priority;
- founder_attention_budget;
- portfolio_id;
- project_stage;
- stage_goal;
- critical_constraints;
- exit_criteria;
- stage_metadata;
- platform_project_id;
- sync_status.

Current `project_type` vocabulary:

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

Điều này rất quan trọng cho Investor Materiality.

### 2.6 Existing stage and validation intelligence

Project stage hiện dùng:

```text
S0_EXPLORE
S1_PROBLEM_VALIDATION
S2_SOLUTION_VALIDATION
S3_BUSINESS_VALIDATION
S4_GO_TO_MARKET
S5_OPERATE_GROWTH
S6_SCALE_GOVERN
```

COSA cũng đã có:
- StageTransitionAudit;
- PrematureScalingAlert;
- ValidationAssumption;
- ValidationHypothesis;
- ValidationExperiment;
- ValidationEvidence;
- ValidationReview;
- ValidationDecision;
- CustomerInterviewSession;
- VerbatimQuote;
- PainPattern;
- EarlyAdopterCandidate;
- ProblemSeverityScorecard.

Investor profile phải reuse những state này để sinh evidence-backed projection.

---

## 3. Core Product Definition

### 3.1 COSA Capital Network

COSA Capital Network là network layer kết nối:

```text
Company
Projects
Founders
Co-founders
Operating Evidence
Traction
Milestones
Capital Need
Investors
Investor Thesis
Investor Feedback
Strategic Proposal
Founder Decisions
Outcomes
```

Investor app chỉ là một client/surface của network này.

### 3.2 COSA Investor

COSA Investor Mobile/Web phục vụ:

```text
Discover
Search
Thesis Match
Analyze Company
Analyze Project Portfolio
Follow
Comment
Evaluate
Request Intro
Request Data Room
Submit Strategic Proposal
Track Opportunities
```

V1 không phải transaction platform.

Không bao gồm mặc định:
- securities purchase;
- payment;
- escrow;
- SPV;
- syndicate;
- automated investment execution;
- success-fee brokerage.

Những chức năng đó cần legal/regulatory architecture riêng.

---

## 4. Visibility Semantics

### 4.1 Company-level visibility

Canonical investor visibility:

```text
PRIVATE
PUBLIC
```

**PRIVATE**

Investor:
- không tìm thấy Company;
- không mở Company;
- không thấy Founder/Co-founder liên kết;
- không thấy Projects;
- không thấy Fundraising Opportunity;
- không comment/evaluate;
- không gửi strategic proposal.

COSA Platform:
- vẫn có thể nhận platform/analytics data theo sync policy;
- platform intelligence có thể phân tích;
- operator access phải theo governance/audit.

**PUBLIC**

Investor:
- thấy Company Standard Investor Profile;
- thấy Founder/Co-founder public profile;
- thấy Material Project Portfolio;
- thấy Fundraising Opportunity nếu Company đang raise;
- có thể follow/comment/evaluate/request intro;
- có thể gửi proposal ở Company hoặc Project scope.

### 4.2 Project visibility override

Company `PUBLIC` không có nghĩa mọi Project nội bộ phải xuất hiện.

Mỗi Project có logical investor visibility:

```text
INHERIT
INCLUDE
EXCLUDE
```

`INHERIT` là mặc định.

Publication policy:
- Project `INHERIT` → Investor Materiality Engine quyết định.
- `INCLUDE` → buộc đưa vào investor portfolio nếu không vi phạm hard security policy.
- `EXCLUDE` → không đưa vào investor projection.

### 4.3 Data Room

Data Room không phải visibility state của Company.

```text
Company PUBLIC
        ↓
Investor requests Data Room
        ↓
Founder approves
        ↓
DataRoomAccessGrant
        ↓
Investor sees restricted due-diligence materials
```

Có thể revoke độc lập với Company visibility.

---

## 5. Platform Data Access Model

### 5.1 Investor access ≠ Platform access

Phải tách:

```text
INVESTOR_ACCESS
PLATFORM_INTELLIGENCE_ACCESS
PLATFORM_OPERATOR_ACCESS
INVESTMENT_ACCESS
```

### 5.2 Platform Intelligence

Machine/system có thể sử dụng sync data để:
- product analytics;
- methodology evaluation;
- recommendation quality analysis;
- benchmark;
- stage funnel analysis;
- project portfolio analysis;
- AI model evaluation;
- feature improvement;
- failure-pattern discovery.

Ưu tiên aggregate, de-identify, purpose-limited processing và minimum necessary access.

### 5.3 Platform Operator Access

Khi COSA staff/operator xem một Company/Project private cụ thể:

```text
actor_id
reason_code
workspace_id
scope
timestamp
action
```

phải được audit.

Suggested reason codes:

```text
SUPPORT
SECURITY
INCIDENT
DATA_QUALITY
MODEL_EVALUATION
PRODUCT_RESEARCH
LEGAL_REQUEST
```

### 5.4 Investment Access

Nếu COSA owner sau này có COSA Ventures/investment arm/fund, investment access không được tự động kế thừa từ platform operator access.

Investment team phải hoạt động như Investor:
- thấy Company `PUBLIC`;
- hoặc được founder grant access.

---

## 6. Sync Policy

### 6.1 Sync không phụ thuộc PUBLIC/PRIVATE

```text
Local Business Event
        ↓
Data Classification
        ↓
Outbox
        ↓
Central Ingestion
        ↓
Platform State / Analytics
        ↓
If Company PUBLIC:
    build/update Investor Projection
```

Không dùng rule:

```text
IF private:
    do not sync anything
```

### 6.2 Data classes

**PLATFORM_REQUIRED**  
Global identity/lifecycle cần để COSA platform hoạt động.

**ANALYTICS_REQUIRED**  
Dữ liệu aggregate cần để cải tiến COSA, ví dụ stage durations, interview counts, experiment counts, validation outcomes, revenue band, team-size band.

Current `ProjectOutcomePayload` đã có pattern:
- first interview;
- first experiment;
- MVP launched;
- first customer;
- first revenue;
- revenue band;
- team size band.

**PUBLIC**  
Investor-facing projection data khi Company `PUBLIC`.

**COMPANY_PRIVATE**  
Business state cần xử lý nội bộ nhưng không public cho investor.

**SENSITIVE**  
PII/confidential business data cần policy nghiêm ngặt.

**SECRET**  
Không được đưa vào network analytics/public projection, ví dụ password, API key, OAuth credential, private key, secret token, bank credential.

### 6.3 No raw database replication

COSA Central không cần full byte-for-byte replica của local database.

Đồng bộ:
- structured state;
- aggregate;
- event;
- selected normalized records;
- approved document metadata;
- analytics facts.

Không mặc định sync:
- credentials;
- full raw customer email;
- password;
- API secret;
- raw private message;
- unnecessary customer PII.

---

## 7. Standard Investor Profile

Khi Company chuyển `PUBLIC`, COSA phải tự động tạo:

```text
StandardInvestorProfile v1
```

Founder:
1. xem preview;
2. xác nhận publish lần đầu;
3. sau đó profile auto-update theo policy.

### 7.1 Company Identity

Investor-facing fields:

```text
Company Name
Logo
Tagline
Short Description
Industry
Vertical
Sub-sector
Country
City
Founded Year
Website
Product URL
Primary Business Model
Current Company Stage
Last Updated
Profile Version
```

Current Workspace model chưa có đủ industry/location/founded-year/public description, do đó đây là một confirmed product/data gap.

### 7.2 Company Narrative

COSA generate từ structured state:

```text
Problem
Target Customer
Solution
Why Now
Differentiation
Business Model
Current Milestone
```

Founder có thể edit/confirm narrative. Narrative không thay thế structured fields.

---

## 8. Founder & Co-founder Public Profile

### 8.1 Current gap

Current `FounderProfile` chủ yếu là internal capacity/WIP:

```text
weekly_capacity_hours
max_active_strategic_projects
```

`User` hiện chủ yếu:
- email;
- phone;
- display_name;
- platform_user_id.

`WorkforceMember` hiện có:
- HUMAN / AI_AGENT;
- human_user_id;
- role_title;
- status.

Những model này chưa đủ cho investor-facing founder profile.

### 8.2 Recommended separation

Không gắn public biography trực tiếp vào FounderProfile nội bộ.

```text
PersonProfile
       │
       ├── StartupTeamMembership → Company A → Founder
       ├── StartupTeamMembership → Company B → Advisor
       └── InvestorMembership     → Fund C → Partner
```

### 8.3 PersonProfile

Recommended fields:

```text
person_id
platform_user_id
display_name
avatar_url
headline
short_bio
country
city
linkedin_url
github_url
portfolio_url
domain_expertise[]
functional_expertise[]
years_experience
previous_companies[]
previous_startups[]
previous_exits[]
education[]
awards[]
identity_verification_status
profile_last_verified_at
```

Do not public by default:
- phone;
- personal email;
- home address;
- compensation;
- personal financial information.

### 8.4 StartupTeamMembership

Recommended fields:

```text
company_id
person_id
role_type
title
responsibility_summary
commitment_type
joined_at
left_at
is_current
is_public
```

`role_type` examples:

```text
FOUNDER
COFOUNDER
CEO
CTO
COO
CPO
CFO
KEY_EXECUTIVE
ADVISOR
```

`commitment_type`:

```text
FULL_TIME
PART_TIME
ADVISORY
```

Investor-facing equity percentage is not public by default.

### 8.5 Team Capability View

COSA may compute:

```text
Domain Knowledge
Technology
Product
Commercial
Operations
Finance
Regulatory
```

Không tạo một single “Founder Score”.

---

## 9. Company Project Portfolio for Investors

### 9.1 Company before Project

Investor entry point:

```text
Company
  ↓
Founder Team
  ↓
Project Portfolio
  ↓
Project Detail
```

Vì investor có thể đầu tư vào Company, vào Project, hoặc đề xuất spin-out Project thành NewCo.

### 9.2 Investor Materiality Engine

Không đưa mọi internal project ra investor app.

Suggested dimensions:

```text
Revenue Impact
Strategic Importance
Capital Consumption
Customer Impact
Technology/IP Importance
Growth Impact
Founder Attention
Risk Materiality
Fundraising Relevance
```

Result:

```text
INVESTOR_MATERIAL
INTERNAL_ONLY
```

### 9.3 Default project-type policy

| Project Type | Default Investor Policy |
|---|---|
| NEW_BUSINESS | likely material |
| PRODUCT | likely material |
| GROWTH | material if linked to major expansion |
| STRATEGIC | material if capital/strategy significant |
| TECHNICAL | only if key product/moat/IP |
| EXPERIMENT | aggregate only unless strategically material |
| OPERATIONAL | normally internal |
| COMPLIANCE | normally internal; disclose only material risk |

Materiality phải rule-driven và overridable by founder.


## 10. Investor Project Profile

Each material Project should expose a standard view.

### 10.1 Project Identity

```text
Project Name
Short Description
Project Type
Stage
Stage Entered At
Strategic Priority
Current Objective
Current Milestone
```

Do not expose internal:
- raw constraints;
- confidential exit criteria;
- internal task list;
- private decision notes.

### 10.2 Problem

Investor sees:

```text
Problem Statement
Customer Segment
Pain Type
Problem Status
Interview Count
Recurring Pain Pattern Count
Commercial Signal Summary
```

### 10.3 Solution

```text
Solution Summary
Product/Service Type
Primary Use Case
Maturity
Prototype/Pilot/Production
Technology Category
Demo Link
Technical Evidence Summary
```

### 10.4 Evidence Map

Investor-facing evidence map:

```text
Problem
Customer
Solution
Pricing
Revenue
Channel
Technical
Operational
Legal
Finance
```

State representation:

```text
UNKNOWN
EARLY
TESTING
SUPPORTED
CHALLENGED
VALIDATED
```

Avoid fake precision. Do not show `Evidence Score = 82.43` unless underlying methodology truly justifies it.

---

## 11. Evidence Projection Rules

### 11.1 Public summary, not raw evidence

Local:

```text
18 interview transcripts
12 quotations
3 contracts
4 pilot reports
```

Investor Projection:

```text
Customer interviews: 18
Repeated pain pattern: 11
Action commitments: 4
Paid pilots: 2
```

Investor does not automatically receive:
- customer names;
- contact;
- transcript;
- exact contract;
- raw utility bill;
- invoice;
- confidential source.

### 11.2 Claim provenance

Each important investor-facing claim should have:

```text
claim
source_type
evidence_level
verification_status
last_updated
```

Possible display labels:

```text
Founder Disclosed
COSA Operating Data
Customer Confirmed
Measured
Externally Verified
```

### 11.3 Contradictions

COSA should not hide all uncertainty.

Public profile may show:

```text
Pricing:
TESTING

Channel:
UNTESTED

Technical deployment:
SUPPORTED

Current known risk:
installation cost
```

Do not expose raw internal arguments unless policy requires it.

---

## 12. Traction Projection

Recommended public-default investor metrics:

```text
Customer Interview Count
Pilot Count
Paid Pilot Count
Paying Customer Count
Active Customer Count
Active User Count
LOI Count
Preorder Count
Deposit Count
Revenue Status
Revenue Band
Revenue Growth
Retention Band
Major Partnership Count
```

Default privacy:

```text
customer names           PRIVATE
customer contact         PRIVATE
contract-by-contract     PRIVATE
invoice                  PRIVATE
bank transaction         PRIVATE
```

### 12.1 Revenue display

Default:

```text
Revenue Band
```

Example:

```text
0
<$10K ARR
$10–50K
$50–100K
$100–500K
$500K–1M
$1M+
```

Founder may explicitly enable exact ARR later.

---

## 13. Business Model Projection

Investor needs:

```text
Customer Type
Business Model
Pricing Model
Revenue Type
Average Contract Size Band
Gross Margin Band
Sales Motion
Sales Cycle Band
Delivery Model
```

Examples:

```text
B2B SaaS
Hardware + SaaS
Services
Marketplace
Licensing
Usage Based
Transaction Fee
Performance Based
Shared Savings
ESCO
EaaS
```

Do not infer a precise gross margin from weak data.

---

## 14. Market Projection

Public:

```text
ICP
Beachhead Segment
Geography
TAM
SAM
SOM
Market Drivers
Competition Category
```

Every market-size number should include provenance:

```text
Founder Supplied
AI Researched
External Source
```

plus `last_updated`.

---

## 15. Fundraising Domain

Current `ProjectFundingView` serves Policy/Funding Intelligence, not venture fundraising.

Do not overload it.

Introduce logical domain:

```text
Capital / Fundraising
```

### 15.1 FundraisingRound

Suggested state:

```text
round_id
company_id
target_scope
project_id?
round_type
target_amount
committed_amount
currency
instrument
minimum_ticket
status
opened_at
target_close_at
```

`target_scope`:

```text
COMPANY
PROJECT
```

### 15.2 CapitalNeed

```text
amount
purpose
runway_months
capital_category
```

### 15.3 UseOfFunds

Structured allocation:

```text
Product
Engineering
Sales
Marketing
Deployment
Operations
Hiring
Regulatory
Working Capital
Other
```

### 15.4 RaiseMilestone

Critical model:

```text
Capital
    ↓
Milestone
    ↓
Evidence Target
    ↓
Value Inflection
```

Fields:

```text
target_metric
current_value
target_value
deadline
hypothesis_to_de_risk
stage_target
```

Investor-facing sentence generated by COSA:

> “This round is intended to prove repeatable deployment across 10 paid industrial sites and reach $250K ARR.”

---

## 16. Investment Opportunity

Investor app should not assume every public startup is actively raising.

Logical states:

```text
NOT_RAISING
OPEN_TO_CONVERSATIONS
RAISING
CLOSED
```

Opportunity:

```text
company_id
project_id?
round_id?
opportunity_type
status
headline
capital_target
thesis_tags
opened_at
```

Opportunity types:

```text
COMPANY_EQUITY
PROJECT_FINANCE
STRATEGIC_INVESTMENT
JOINT_VENTURE
PARTNERSHIP
```

---

## 17. Investor Profile

Public discussion requires investor identity.

### 17.1 InvestorProfile

Fields:

```text
person_id
investor_type
firm_name
position
country
city
website
linkedin_url
verification_status
```

Investor types:

```text
ANGEL
VC
CVC
FAMILY_OFFICE
FUND
IMPACT_FUND
ACCELERATOR
STRATEGIC_CORPORATE
OTHER
```

### 17.2 InvestmentThesis

```text
stages[]
sectors[]
geographies[]
ticket_min
ticket_max
business_models[]
technology_preferences[]
impact_preferences[]
risk_preferences[]
lead_or_follow
```

---

## 18. Investor–Startup Thesis Fit

Personalized score is allowed because it is not a quality judgment.

```text
Thesis Fit
=
Stage Fit
+ Sector Fit
+ Geography Fit
+ Ticket Fit
+ Business Model Fit
+ Technology Fit
+ Impact Fit
```

Investor A:

```text
92% fit
```

Investor B:

```text
43% fit
```

This score must be labeled:

```text
YOUR THESIS FIT
```

Không gọi:

```text
Startup Investment Score
```

---

## 19. Investor Interaction Model

Investor can:

```text
FOLLOW
SAVE
EXPRESS_INTEREST
REQUEST_INTRO
REQUEST_DATA_ROOM
COMMENT
EVALUATE
SUBMIT_STRATEGIC_PROPOSAL
```

These signals are distinct.

### 19.1 Public counters

May display:

```text
followers
interested_investors
intro_requests
```

Do not public:
- active due diligence details;
- term sheet;
- committed amount by investor;
- confidential negotiation state.

---

## 20. Investor Comments

### 20.1 Purpose

Public comments should be a **professional investor discussion layer**, not social-media chatter.

Comment types:

```text
QUESTION
INSIGHT
CONCERN
ENDORSEMENT
```

Scopes:

```text
COMPANY
PROJECT
```

### 20.2 Founder reply

Founder/team can reply.

Example:

```text
Investor:
Has MRV been independently verified?

Founder:
Two pilots are customer-confirmed.
Independent verification is in progress.
```

COSA may update a structured “investor concern” signal, but must not automatically change business evidence.

### 20.3 Comment as signal

Investor comment becomes:

```text
ExternalInvestorSignal
```

not:

```text
ValidationEvidence
```

Possible fields:

```text
signal_id
investor_id
company_id
project_id?
signal_type
topic
body
created_at
verification_context
```

AI Co-founder can suggest:
- create Risk;
- create Assumption;
- create Task;
- run Research;
- run Experiment.

Founder decides.

---

## 21. Investor Evaluation

### 21.1 No single star rating

Do not show:

```text
Startup Rating: 4.1 stars
```

because it creates:
- herd behavior;
- gaming;
- stage bias;
- small-sample distortion;
- revenge rating;
- competitor manipulation.

### 21.2 Structured dimensions

Company evaluation:

```text
Team Confidence
Problem Attractiveness
Evidence Strength
Solution Differentiation
Business Model Confidence
Execution Confidence
Portfolio Focus
Capital Efficiency
```

Project evaluation:

```text
Problem
Evidence
Technical
Commercial
Strategic Fit
Execution
```

### 21.3 Public aggregation

Only show public aggregate when enough verified investor evaluations exist.

Example:

```text
Team Confidence       4.3 / 5   (12 verified investors)
Problem               4.5 / 5   (11)
Evidence              3.7 / 5   (10)
Business Model        3.6 / 5   (8)
```

Threshold should be methodology/platform config, not hardcoded in prompt.

### 21.4 Three scores must stay separate

```text
COSA Evidence Readiness
Investor Sentiment
Investor Thesis Fit
```

Never merge them into:

```text
Investment Score = 87
```

---

## 22. Investor Sentiment

Public aggregate example:

```text
Positive      62%
Neutral       23%
Concerned     15%

Based on 13 verified investor evaluations.
```

This is opinion, not evidence.

---

## 23. Strategic Investor Proposals

This is one of the strongest differentiators of COSA Capital Network.

Investor can send structured recommendations about Company/Project portfolio.

### 23.1 Proposal types

```text
FOCUS_PROJECT
DEPRIORITIZE_PROJECT
STOP_PROJECT
MERGE_PROJECTS
SPIN_OUT_PROJECT
PROJECT_INVESTMENT
COMPANY_INVESTMENT
JOINT_VENTURE
STRATEGIC_PARTNERSHIP
```

### 23.2 Proposal model

Suggested fields:

```text
proposal_id
investor_id
company_id
project_id?
proposal_type
title
rationale
capital_interest_amount?
conditions_jsonb
status
created_at
```

Status:

```text
SUBMITTED
UNDER_REVIEW
DISCUSSING
ACCEPTED_FOR_REVIEW
REJECTED
WITHDRAWN
CLOSED
```

### 23.3 Spin-out proposal

Example:

```text
Source Company:
ABC Energy

Project:
Battery AI

Proposal:
SPIN_OUT_PROJECT

Suggested NewCo:
BatteryMind

Investor Interest:
$750K

Conditions:
- IP transfer/license
- dedicated CTO
- 18-month runway
```

This proposal never automatically creates a company. Founder/board decides.

---

## 24. AI Co-founder Analysis of Investor Proposal

Investor only sees PUBLIC projection.

AI Co-founder may use PRIVATE context:

```text
Project Evidence
Economics
Cash
Team Capacity
Founder Attention
Customer Overlap
Technology Dependencies
IP Dependencies
Synergies
Risks
Capital Needs
```

Example output:

```text
Investor proposal:
SPIN_OUT Project D

COSA assessment:
- Market separation: strong
- Capital profile difference: strong
- Shared IP dependency: high
- Shared engineering dependency: critical
- Customer overlap: low
- Current project evidence: supported
- Recommendation: TEST STRUCTURE BEFORE SPIN-OUT
```

Do not expose the private inputs to investor unless founder grants them.

---

## 25. Portfolio Intelligence

COSA should analyze Company portfolio internally and produce a public-safe subset for investor.

### 25.1 Internal view

```text
Project
Founder Attention
Capital Consumption
Evidence Strength
Strategic Fit
Commercial Potential
Risk
Synergy
```

### 25.2 Investor view

```text
Project
Stage
Strategic Priority
Evidence State
Traction Summary
Current Milestone
Capital Relevance
```

Do not expose:
- internal conflict;
- raw cash allocation;
- confidential project notes;
- private customer dependencies.

---

## 26. Investor Portfolio Consensus

When enough verified investors submit proposals/evaluations, COSA may show:

```text
Project A
FOCUS                 76%

Project B
CONTINUE              62%

Project C
DEPRIORITIZE          54%

Project D
SPIN_OUT              41%
```

Label explicitly:

```text
Investor Opinion
```

Not:

```text
COSA Recommendation
```

---

## 27. Compare Investor Consensus with Internal Evidence

AI Co-founder should detect discrepancies.

Case A:

```text
Investor consensus:
STOP Project C

Internal evidence:
strong customer pull
good unit economics
low founder attention
```

COSA may conclude:

> “Investor perception differs from internal evidence; public profile may under-communicate customer pull.”

Case B:

```text
Investor enthusiasm:
very high

Internal evidence:
weak
technical blocker
high burn
```

COSA may conclude:

> “Use investor interest as a validation opportunity, not as justification for premature scale.”


## 28. Investor Feedback Loop into Startup COSA

Flow:

```text
Investor Comment / Evaluation / Proposal
        ↓
Central PostgreSQL
        ↓
Network Event
        ↓
PlatformInbox
        ↓
Local COSA
        ↓
AI Co-founder
        ↓
Signal Analysis
        ↓
NextActionCandidate
```

Reuse current Next Action engine. Do not create a second task/recommendation system.

---

## 29. Public Profile Auto-update

After Company is PUBLIC:

```text
New stage
New paying customer
New pilot
New evidence
New milestone
New founder
New fundraising state
```

can trigger:

```text
InvestorProjectionUpdated
```

Example:

```text
project.stage_changed
        ↓
PublicProjectionBuilder
        ↓
Central Investor Profile v32
        ↓
Follower feed
```

### 29.1 Auto-update policy

Fields should have update mode:

```text
AUTO
FOUNDER_CONFIRM
NEVER_PUBLIC
```

Examples:

| Field | Mode |
|---|---|
| Company name | AUTO |
| Stage | AUTO |
| Project count | AUTO |
| Evidence status | AUTO |
| Founder role | FOUNDER_CONFIRM |
| Exact ARR | FOUNDER_CONFIRM |
| Revenue band | AUTO |
| Customer names | NEVER_PUBLIC |
| Cash balance | NEVER_PUBLIC |
| Raw contract | NEVER_PUBLIC |

---

## 30. Public Profile Versioning

Every public profile should have:

```text
profile_version
generated_at
last_updated
source_revision
```

Investor UI:

```text
Source: COSA Operating Data
Last Updated: 2 hours ago
Profile Version: 31
```

---

## 31. Make Private / Unpublish

When founder changes:

```text
PUBLIC → PRIVATE
```

Central:

```text
network_visibility = PRIVATE
```

Effects:
- removed from discovery;
- public profile cannot be opened;
- projects hidden;
- comments/evaluations no longer publicly displayed;
- new investor interaction disabled.

Historical platform audit remains.

Data Room grants should be handled separately:
- revoke automatically by policy;
- or require founder confirmation.

This decision must be explicit in product settings.

---

## 32. Central PostgreSQL Logical Model

Recommended logical tables/entities:

```text
Identity
├── platform_people
├── person_profiles
├── investor_profiles
├── startup_team_memberships
└── identity_verifications

Companies
├── platform_companies
├── company_network_settings
├── public_company_profiles
└── public_company_profile_versions

Projects
├── platform_projects
├── project_network_settings
├── public_project_profiles
├── public_project_profile_versions
└── public_project_evidence_summaries

Capital
├── fundraising_rounds
├── investment_opportunities
├── capital_needs
├── use_of_funds
├── raise_milestones
└── investor_pipeline_entries

Investor Network
├── investor_theses
├── investor_follows
├── investor_interests
├── intro_requests
└── data_room_access_requests

Community
├── investor_comments
├── comment_replies
├── investor_evaluations
├── investor_reactions
├── strategic_proposals
├── content_reports
└── moderation_actions
```

This is a logical model. Physical ownership/path must be finalized through COSA canonical ownership rules before implementation.

---

## 33. Local PostgreSQL Ownership

Local continues to own business truth:

```text
Workspace
Project
Strategy
Validation
Evidence
Customer Discovery
Sales
Finance
Legal
Organization
Workforce
Tasks
Learning
Knowledge
Artifacts
```

Central public profile is projection, not authority for local business truth.

---

## 34. Proposed Platform Events

Extend `PlatformEventTypeEnum` carefully.

Recommended future events:

```text
company.visibility_changed
company.public_profile_updated

person.public_profile_updated
team.membership_public_updated

project.public_profile_updated
project.investor_visibility_changed

fundraising.round_opened
fundraising.round_updated
fundraising.round_closed

investor.followed_company
investor.interest_expressed
investor.intro_requested
investor.data_room_requested

investor.comment_created
investor.evaluation_submitted
investor.strategic_proposal_submitted
```

Use existing standard envelope:
- event_id;
- company_id;
- project_id;
- event_type;
- occurred_at;
- schema_version;
- classification;
- payload.

---

## 35. Data Classification Matrix

| Data | Platform | Investor Public | Data Room |
|---|---|---|---|
| Company name | Yes | Yes if PUBLIC | Yes |
| Project title | Yes | Material only | Yes |
| Project stage | Yes | Yes | Yes |
| Hypothesis status | Analytics | Summary | Detailed if approved |
| Interview count | Analytics | Summary | Yes |
| Raw transcript | Restricted | No | Only explicit |
| Customer name | Restricted | No | Explicit |
| Revenue band | Analytics | Yes | Yes |
| Exact revenue | Private | Optional | Yes |
| Cash balance | Private | No | Yes if approved |
| Founder name | Yes | Yes if PUBLIC | Yes |
| Founder email/phone | Sensitive | No | Explicit |
| API/OAuth secret | Secret | Never | Never |
| Investor comments | Network | Yes | Yes |
| Strategic proposal | Network | Limited/public by policy | Full parties |

---

## 36. Moderation and Trust

Public investor comments/evaluation require strong governance.

Required controls:

```text
Verified investor identity
Rate limiting
Spam detection
Abuse reporting
Founder reply
Investor edit history
Moderation audit
Conflict disclosure
Block/mute
Content policy
Appeal flow
```

Founder cannot delete negative investor comments merely because they are negative.

Founder can:
- reply;
- report;
- request moderation.

Platform moderator decides.

---

## 37. Conflict Disclosure

Investor comment/evaluation should carry context:

```text
Existing Shareholder
Portfolio Conflict
Competitor Exposure
Advisory Relationship
Commercial Relationship
```

This helps readers interpret sentiment.

---

## 38. Investor Feed

Investor home feed can rank:

```text
Thesis Fit
Fresh Evidence
Stage Progress
Fundraising Open
New Milestone
New Project
Investor Activity
```

Do not rank solely by popularity.

Avoid feedback loop where:

```text
popular startup → more visibility → more popularity
```

Need diversity/exploration logic.

---

## 39. Startup Investor Intelligence Dashboard

Founder side should include:

```text
Investor Reach
Followers
Interest
Intro Requests
Data Room Requests

Recurring Investor Questions

Investor Sentiment

Portfolio Feedback

Strategic Proposals

Investor Pipeline

Top Information Gaps
```

Example:

```text
12 investors reviewed this month

Recurring concerns:
1. Installation cost
2. Sales cycle
3. Founder bandwidth

Portfolio signals:
Project A — strongest conviction
Project C — low strategic fit
Project D — 4 spin-out proposals
```

AI Co-founder generates Next Best Action.

---

## 40. Company vs Project Investment

Capital Network must support two distinct investment intents.

### COMPANY

Investor believes in:
- team;
- whole portfolio;
- operating company;
- broad business strategy.

### PROJECT

Investor believes in:
- specific project;
- specific product;
- project finance;
- strategic JV;
- future spin-out.

This allows a weak/broad Company to contain one highly attractive Project.

---

## 41. Project Spin-out Workflow

Suggested flow:

```text
Investor submits SPIN_OUT_PROJECT
        ↓
Founder reviews
        ↓
COSA runs Spin-out Assessment
        ↓
Assess:
  IP
  Team
  Customer
  Finance
  Synergy
  Dependency
  Legal
  Capital
        ↓
Founder chooses:
  REJECT
  DISCUSS
  TEST
  ACCEPT_FOR_REVIEW
        ↓
If accepted:
  create strategic initiative/project
        ↓
optional NewCo formation workflow
```

Do not create new Workspace automatically.

Company hierarchy changes require explicit ownership/migration decision.

---

## 42. COSA Intelligence Learning Loop

COSA can learn from:

```text
Company State
Project Portfolio
Hypotheses
Evidence
Experiments
Founder Decisions
Investor Opinions
Strategic Proposals
Actual Outcomes
```

Examples:

```text
Do S1 startups with >5 active strategic projects progress slower?

Which investor concerns predict later business failure?

Which evidence pattern predicts a successful Seed raise?

When COSA recommends FOCUS, how often does founder acceptance improve outcomes?

Which stage-gate signals correlate with investor follow-up?
```

This data can improve:
- methodology;
- stage gates;
- project portfolio guidance;
- recommendation ranking;
- AI evaluation.

---

## 43. Methodology Integration

Startup methodology spec should add data exposure metadata.

For each structured field/artifact:

```text
visibility_policy:
  platform: PLATFORM_ANALYTICS
  investor: PUBLIC_DEFAULT
  data_room: AVAILABLE
```

Examples:

```yaml
field: project.stage
platform: PLATFORM_REQUIRED
investor: PUBLIC_DEFAULT
data_room: INCLUDED
```

```yaml
field: finance.cash_balance
platform: COMPANY_PRIVATE
investor: NEVER
data_room: FOUNDER_APPROVAL
```

```yaml
field: validation.interview_count
platform: ANALYTICS_REQUIRED
investor: PUBLIC_DEFAULT
data_room: INCLUDED
```

This should be methodology/config driven, not spread across UI code.

---

## 44. Current Code Reuse Map

| Requirement | Existing COSA | Recommended Action |
|---|---|---|
| Local PostgreSQL | Existing | Reuse |
| Central PostgreSQL config | `CONTROL_PLANE_DATABASE_URL` | Reuse/clarify docs |
| Platform IDs | User/Workspace/Project platform IDs | Reuse |
| Outbox/Inbox | `app/platform/sync` | Extend |
| Event envelope | Existing | Extend |
| DataClassificationEnum | Existing | Formalize/extend |
| Project portfolio | `core.strategy.Project` | Reuse |
| Startup stages | Project + sync schemas | Reuse |
| Stage gate | StageTransitionAudit | Reuse |
| Evidence | Validation domain | Reuse |
| Investor-ready aggregates | ProjectOutcomePayload pattern | Extend |
| Founder internal profile | FounderProfile | Keep internal |
| Human role | WorkforceMember | Reuse association |
| Public person profile | Missing | Add |
| Fundraising round | Missing in current Finance core | Add domain |
| Investor profile | Missing | Add |
| Investor thesis | Missing | Add |
| Comments/evaluation | Missing | Add |
| Strategic proposal | Missing | Add |
| Audit | AuditLog | Extend |
| Next action | NextAction engine | Reuse |

---

## 45. Architecture Decisions That Must NOT Be Made

Do not:
- add `Project.is_public` and expose Project JSON directly;
- mirror entire local database to Central;
- store secrets in Investor/Public tables;
- create a second sync engine;
- create a second Task/NextAction engine;
- use raw investor comments as ValidationEvidence;
- merge investor sentiment with COSA evidence into one score;
- create a single Founder quality score;
- let founder delete negative comments directly;
- give investment staff unrestricted private-company access because they are platform staff;
- auto-create a NewCo from an investor spin-out suggestion;
- make every internal operational project visible by default.


## 46. API Surface — Proposed

### Company network settings

```text
GET  /capital-network/company/settings
PUT  /capital-network/company/visibility
GET  /capital-network/company/public-preview
POST /capital-network/company/publish
POST /capital-network/company/unpublish
```

### Project visibility

```text
GET /capital-network/projects
PUT /capital-network/projects/{id}/investor-visibility
```

### Investor discovery

```text
GET /investor/companies
GET /investor/companies/{company_id}
GET /investor/projects/{project_id}
GET /investor/opportunities
```

### Investor interactions

```text
POST /investor/companies/{id}/follow
POST /investor/companies/{id}/interest
POST /investor/companies/{id}/intro-request
POST /investor/companies/{id}/data-room-request
```

### Community

```text
POST /investor/companies/{id}/comments
POST /investor/projects/{id}/comments
POST /investor/companies/{id}/evaluations
POST /investor/projects/{id}/evaluations
```

### Strategic proposals

```text
POST /investor/companies/{id}/proposals
POST /investor/projects/{id}/proposals
GET  /company/investor-proposals
POST /company/investor-proposals/{id}/decision
```

Exact route ownership should be selected after backend router audit.

---

## 47. Mobile Investor UX

Primary tabs:

```text
Discover
Following
Portfolio/Watchlist
Activity
Profile
```

Company detail:

```text
Overview
Team
Projects
Evidence
Traction
Business
Raise
Investor Discussion
```

Project detail:

```text
Overview
Problem
Solution
Evidence
Traction
Milestone
Investor View
```

Main CTAs:

```text
Follow
Interested
Ask
Request Intro
Request Data Room
Propose Strategy
```

---

## 48. Founder UX

Inside COSA Company:

```text
Capital Network
```

Subsections:

```text
Visibility
Public Profile Preview
Projects for Investors
Fundraising
Investor Activity
Comments
Evaluations
Strategic Proposals
Investor Pipeline
Data Room
```

Public switch UX:

```text
Investor Visibility
[ PRIVATE | PUBLIC ]

PUBLIC means:
- investors can view Company
- investors can view material Projects
- founder/co-founder public profiles are shown
- public evidence/traction summaries update automatically
```

Founder confirms once.

---

## 49. Security / Governance Acceptance Criteria

A valid implementation must ensure:

1. PRIVATE Company cannot be discovered by investor APIs.
2. PUBLIC Company exposes only projection tables/contracts.
3. Investor APIs never query local/private business tables directly.
4. Raw secrets never enter investor projection.
5. Operator access to private Company is audited.
6. Investment access is separate from platform operator access.
7. Investor comments require verified identity.
8. Comment edit/delete history is retained.
9. Founder cannot silently remove negative feedback.
10. Investor comment does not become validation evidence automatically.
11. Public profile has version/freshness.
12. Project `EXCLUDE` override is respected.
13. Company PUBLIC does not expose internal-only projects.
14. Unpublish removes discovery access.
15. Data Room grants are separately revocable.

---

## 50. Product Acceptance Criteria

COSA Capital Network is successful when:

1. Founder does not need to rebuild a startup profile manually.
2. Investor can understand Company in <60 seconds.
3. Investor can understand Project portfolio and identify focus/spin-out opportunities.
4. Founder/co-founder background is first-class.
5. Claims show evidence/provenance level.
6. Investor sees meaningful traction without exposing raw confidential data.
7. Investor can distinguish Company investment from Project investment.
8. Investor comments create useful external signals.
9. Structured proposals can flow back into COSA.
10. AI Co-founder can analyze proposals using private context.
11. Founder receives actionable investor intelligence.
12. COSA can use aggregate/private platform analytics to improve methodology/model under governance.

---

## 51. Implementation Phases

### Phase A — Architecture & Data Boundary

- formalize Local PostgreSQL / Central PostgreSQL terminology;
- audit old “Supabase Central” comments/specs;
- formalize DataClassificationEnum semantics;
- define Company investor visibility;
- define platform analytics/operator access policy;
- define public projection boundary.

Deliverable:

```text
COSA_CAPITAL_NETWORK_DATA_BOUNDARY_ADR.md
```

### Phase B — Public Company + Founder + Project Portfolio

Implement:
- company visibility;
- public company projection;
- PersonProfile;
- StartupTeamMembership;
- investor materiality;
- public Project projection;
- automatic profile updates.

### Phase C — Investor Identity + Discovery

Implement:
- InvestorProfile;
- InvestmentThesis;
- discovery;
- filter/search;
- thesis fit;
- follow/save.

### Phase D — Fundraising

Implement:
- FundraisingRound;
- InvestmentOpportunity;
- CapitalNeed;
- UseOfFunds;
- RaiseMilestone;
- intro request;
- investor pipeline.

### Phase E — Community

Implement:
- verified comments;
- structured evaluations;
- sentiment;
- moderation;
- founder reply.

### Phase F — Strategic Proposals

Implement:
- focus/deprioritize/stop/merge/spin-out;
- Company/Project investment proposal;
- AI Co-founder analysis;
- Next Best Action integration.

### Phase G — Intelligence Loop

Implement:
- investor concern clustering;
- portfolio consensus;
- outcome correlation;
- methodology/model evaluation;
- aggregate platform benchmark.

---

## 52. Recommended V1 Vertical Slice

Best V1:

```text
Company PRIVATE
      ↓
Founder completes Public Profile Preview
      ↓
Company → PUBLIC
      ↓
Auto-generate:
- Company profile
- Founder/Co-founder profiles
- Material Project Portfolio
- Evidence summary
- Traction summary
      ↓
Investor discovers
      ↓
Investor follows/comments/requests intro
      ↓
Feedback returns to COSA
      ↓
AI Co-founder summarizes recurring investor concerns
```

Do not start V1 with:
- investment transaction;
- complex data room;
- full rating marketplace;
- SPV;
- payment rails.

---

## 53. Recommended V2 Differentiator

After V1 proves discovery:

```text
Investor Strategic Proposal
```

especially:

```text
FOCUS_PROJECT
DEPRIORITIZE_PROJECT
SPIN_OUT_PROJECT
PROJECT_INVESTMENT
```

This uses COSA’s unique project portfolio data and is harder for a conventional startup marketplace to copy.

---

## 54. Strategic Positioning

Do not position as:

> “App để xem startup gọi vốn.”

Position as:

> **COSA Capital Network — evidence-backed company and project intelligence connecting founders, projects and investors directly from the startup operating system.**

For investor:

> **Discover companies, understand project portfolios, see evidence quality and engage founders with structured investment intelligence.**

For founder:

> **Operate once in COSA; your investor profile, project portfolio and fundraising narrative stay continuously updated from real operating data.**

---

## 55. North Star

```text
                     COSA COMPANY INTELLIGENCE GRAPH

Founder / Co-founder
        │
      Company
        │
    Project Portfolio
        │
    ┌───┼───────────────────┐
    │   │                   │
 Problem Solution        Business
    │   │                   │
Hypotheses              Metrics
    │                       │
Evidence               Traction
    │                       │
Experiments            Capital Need
    │                       │
Decisions              Fundraising
    │                       │
    └──────── Outcomes ─────┘
             │
             ↓
       Investor Projection
             │
             ↓
        Capital Network
             │
    ┌────────┼─────────────┐
    │        │             │
 Comments  Evaluation   Proposals
    │        │             │
    └────────┼─────────────┘
             ↓
      External Signals
             ↓
        AI Co-founder
             ↓
        Founder Decision
             ↓
          Outcomes
```

Core flywheel:

```text
Better COSA Operations
        ↓
Better Structured Data
        ↓
Better Investor Intelligence
        ↓
Better Capital/Strategic Feedback
        ↓
Better Founder Decisions
        ↓
Better Outcomes
        ↓
Better COSA Methodology
```

---

## Appendix A — Current Repository Anchors

Observed/current anchors used by this specification:

```text
.env.example
backend/app/platform/auth/models.py
backend/app/platform/core/models.py
backend/app/platform/organization/models.py
backend/app/platform/sync/models.py
backend/app/platform/sync/schemas.py
backend/app/platform/sync/outbox_service.py
backend/core/strategy/project.py
backend/core/strategy/founder.py
backend/core/validation/
backend/core/finance/
backend/app/platform/policy_funding/
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
```

Important current observations:

```text
Central Control Plane connection is PostgreSQL.
Some code comments still use older “Supabase Central” wording.
Outbox/Inbox and data classification already exist.
Project global UUID and Company global UUID already exist.
Project lifecycle aggregation already syncs stage/outcome facts.
FounderProfile is currently an internal WIP/capacity model.
Investor profile, venture fundraising, comments, evaluation
and strategic proposals are not yet canonical domains.
```

---

## Appendix B — Suggested Data Exposure Metadata

```yaml
project.stage:
  platform: PLATFORM_REQUIRED
  investor: PUBLIC_DEFAULT
  data_room: INCLUDED

validation.problem_status:
  platform: ANALYTICS_REQUIRED
  investor: PUBLIC_DEFAULT
  data_room: INCLUDED

validation.raw_interview_transcript:
  platform: COMPANY_PRIVATE
  investor: NEVER
  data_room: FOUNDER_APPROVAL

finance.revenue_band:
  platform: ANALYTICS_REQUIRED
  investor: PUBLIC_DEFAULT
  data_room: INCLUDED

finance.exact_revenue:
  platform: COMPANY_PRIVATE
  investor: FOUNDER_CONFIRM
  data_room: INCLUDED

finance.cash_balance:
  platform: COMPANY_PRIVATE
  investor: NEVER
  data_room: FOUNDER_APPROVAL

auth.oauth_token:
  platform: SECRET
  investor: NEVER
  data_room: NEVER
```

---

## Appendix C — Suggested Investor Evaluation Contract

```yaml
evaluation_scope: COMPANY

dimensions:
  team_confidence:
    min: 1
    max: 5

  problem_attractiveness:
    min: 1
    max: 5

  evidence_strength:
    min: 1
    max: 5

  solution_differentiation:
    min: 1
    max: 5

  business_model_confidence:
    min: 1
    max: 5

  execution_confidence:
    min: 1
    max: 5

  portfolio_focus:
    min: 1
    max: 5

  capital_efficiency:
    min: 1
    max: 5

comment: optional
conflict_disclosure: required
```

---

## Appendix D — Suggested Strategic Proposal Contract

```yaml
proposal_type: SPIN_OUT_PROJECT

scope:
  company_id: "<company>"
  project_id: "<project>"

rationale:
  "Project has distinct customers, economics and capital requirements."

proposed_structure:
  newco_name: "Optional"
  investment_interest: 750000
  currency: USD

conditions:
  - "Dedicated technical lead"
  - "IP license/transfer agreement"
  - "18 months runway"

investor_visibility:
  public_summary: true
  full_terms: parties_only
```

---

## Appendix E — Definition of Done

COSA Capital Network v1 is considered architecturally integrated only when:

```text
Private/Public investor visibility is deterministic.
Public profile is a projection, not raw Project serialization.
Company and Project remain canonical local business entities.
Local-to-Central sync reuses PlatformOutbox/Inbox.
Investor profile is generated from COSA operating truth.
Founder/Co-founder profiles are first-class.
Investor can inspect material Project portfolio.
Evidence is summarized with provenance.
Fundraising is separate from policy/grant funding.
Investor comments/evaluations are identity-bound and moderated.
Investor opinions stay separate from business evidence.
Strategic proposals can return to AI Co-founder.
Platform intelligence access is separated from investment access.
All sensitive operator access is auditable.
```

---

**End of Draft v1.0**
