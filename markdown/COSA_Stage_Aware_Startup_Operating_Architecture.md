# COSA — Stage-Aware Startup & Company Operating Architecture
## Tài liệu điều chỉnh, bổ sung và tích hợp khung phát triển startup theo Stage

**Mục tiêu:** Điều chỉnh COSA từ mô hình “nhiều framework/chức năng độc lập” sang một **AI Founder & Company Operating System** vận hành theo giai đoạn phát triển thực tế của công ty và từng project.

---

## 1. Quyết định kiến trúc cần chốt

### 1.1. COSA không phải nền tảng học giáo trình SIHUB

Kiến thức từ SIHUB được sử dụng như **business methodology knowledge** để COSA:

- nhận biết startup đang ở giai đoạn nào;
- xác định rủi ro hoặc giả định quan trọng nhất;
- chọn đúng phương pháp quản trị;
- yêu cầu đúng dữ liệu;
- kích hoạt đúng Agent/Skill/Workflow;
- đề xuất đúng hành động tiếp theo;
- đo mức sẵn sàng chuyển sang giai đoạn sau.

Không thiết kế UI theo kiểu:

```text
Khóa học
├── Module 1
├── Module 2
├── Module 3
└── ...
```

Không bắt founder “học xong bài” mới được tiếp tục.

COSA phải vận hành theo logic:

```text
Current Stage
    ↓
Current Goal
    ↓
Current Constraint / Critical Risk
    ↓
Required Evidence
    ↓
Recommended Method / Skill / Agent
    ↓
Experiment / Decision / Objective
    ↓
Execution
    ↓
New Evidence
    ↓
Stage Readiness
```

---

## 2. Triết lý quản trị mới của COSA

### 2.1. Framework phục vụ Stage, không phải Stage phục vụ Framework

Không quay lại kiến trúc cũ:

```text
PESTEL
  ↓
SWOT
  ↓
TOWS
  ↓
Objectives
  ↓
OKRs
```

Thay bằng:

```text
Stage
  ↓
Strategic Question
  ↓
Available Evidence
  ↓
Management Policy Engine
  ↓
Select Appropriate Method
  ↓
Decision / Experiment / Objective
```

PESTEL, SWOT, TOWS, BSC, OKRs, 12 Week Year, Customer Discovery, JTBD, Unit Economics, CRM, Marketing Funnel... chỉ là **method/tool** được COSA gọi đúng lúc.

---

## 3. Hai lớp Stage bắt buộc

### 3.1. Company Stage

Phản ánh mức trưởng thành chung của doanh nghiệp.

Ví dụ:

```text
COSA Company = Operate & Grow
```

### 3.2. Project Stage

Mỗi project có vòng đời riêng.

Ví dụ:

```text
COSA Company              = Operate & Grow
Project A: Hotel AI       = Problem Validation
Project B: Marketing Hub  = Go-to-Market
Project C: Finance Agent  = Solution Validation
```

### 3.3. Quy tắc

Không lấy `company_stage` áp cứng cho tất cả project.

Mỗi Project phải có:

```yaml
project_stage:
  current_stage:
  stage_started_at:
  confidence:
  critical_constraints: []
  required_evidence: []
  exit_criteria: []
  transition_status:
```

---

# 4. Startup / Company Lifecycle chuẩn

Đề xuất 7 Stage chính.

---

## S0 — EXPLORE

### Câu hỏi chính

> Có cơ hội đủ đáng để tiếp tục nghiên cứu không?

### Quản trị ưu tiên

- Opportunity research
- Market signals
- Customer assumptions
- Problem assumptions
- Technology feasibility
- Regulatory constraints
- Initial Risk Map

### Artifacts chính

- Project Brief
- Opportunity Hypotheses
- Assumption Map
- Initial Research Pack
- Initial Risk Map

### Metric

Không dùng Growth Metrics.

Theo dõi:

- số giả định critical;
- mức evidence;
- market signals;
- feasibility signals.

### Framework có thể sử dụng

- Market Research
- Assumption Mapping
- PESTEL-lite khi môi trường ngoài ảnh hưởng lớn

### Không ưu tiên

- BSC
- NPS
- Churn
- Department OKRs
- Full SOP
- Full CRM
- Scale metrics

---

## S1 — PROBLEM VALIDATION

### Câu hỏi chính

> Có customer thật và problem đủ đau để đáng giải quyết không?

### Quản trị ưu tiên

- Customer Discovery
- Interview
- ICP
- Jobs-to-be-Done
- Problem Evidence
- Existing Alternatives

### Artifacts

- Interview Plan
- Interview Script
- Interview Logs
- ICP
- Problem Statement
- JTBD
- Alternative Map
- Evidence Pack

### Metrics

- Qualified interviews
- Problem match rate
- Pain frequency
- Pain severity
- Behavioral evidence
- Existing spend / workaround
- Pilot interest

### Gate sang S2

Không dùng số interview cố định như điều kiện cứng.

COSA đánh giá:

```text
Problem importance
× Evidence strength
× Behavioral confirmation
× Customer consistency
```

---

## S2 — SOLUTION VALIDATION

### Câu hỏi chính

> Giải pháp có tạo giá trị đủ mạnh để khách hàng thay đổi hành vi hoặc cam kết không?

### Quản trị ưu tiên

- Solution Hypothesis
- Prototype
- MVP
- Value Proposition
- Pricing Hypothesis
- Willingness-to-pay
- Experiment Design

### Artifacts

- Solution Hypothesis
- Value Proposition
- Prototype/MVP Spec
- Pricing Hypothesis
- Experiment Backlog
- Experiment Results

### Metrics

- activation;
- demo acceptance;
- pilot acceptance;
- willingness-to-pay;
- paid pilot;
- task success;
- time-to-value.

### Framework

- Lean Experiment
- Value Proposition
- Pricing Test
- Prototype/MVP Testing

### Không ưu tiên

- BSC
- NPS nếu chưa có customer usage thực
- full-scale Growth Dashboard

---

## S3 — BUSINESS VALIDATION

### Câu hỏi chính

> Có thể biến giải pháp thành business sống được không?

### Quản trị ưu tiên

- Revenue Model
- Pricing
- Unit Economics
- Sales Validation
- Cost Model
- Cash / Runway
- Initial Business Model

### Artifacts

- Business Model
- Revenue Model
- Pricing Model
- Unit Economics
- Sales Evidence
- Cash Forecast
- Runway

### Metrics

- paid customers;
- revenue;
- gross margin;
- CAC hypothesis/observed;
- payback;
- conversion;
- cash burn;
- runway.

### Framework

- Business Model Canvas dưới dạng View
- Unit Economics
- Cash Model
- SWOT nếu đã có dữ liệu thật
- TOWS khi cần tạo strategic options

### Gate sang S4

Cần có ít nhất:

- tín hiệu revenue thật;
- pricing evidence;
- sales process sơ bộ;
- unit economics đủ khả thi để tiếp tục.

---

## S4 — GO-TO-MARKET

### Câu hỏi chính

> Có cách tiếp cận và chuyển đổi khách hàng lặp lại được không?

### Quản trị ưu tiên

- Positioning
- Channel Selection
- Marketing
- Sales
- CRM
- Funnel
- GTM Experiments
- Beachhead Market

### Artifacts

- Positioning
- Channel Matrix
- GTM Plan
- Funnel
- CRM Pipeline
- Campaigns
- Sales Playbook
- GTM Experiment Backlog

### Metrics

Tùy business model:

#### B2B

- lead → qualified;
- opportunity;
- win rate;
- sales cycle;
- ACV;
- pipeline coverage.

#### SaaS

- acquisition;
- activation;
- retention;
- MRR;
- expansion;
- churn.

#### E-commerce

- traffic;
- conversion;
- AOV;
- repeat purchase;
- contribution margin.

### Framework

- Marketing Channel Playbooks
- Sales Funnel
- CRM
- GTM Experiments
- Positioning
- TOWS khi cần chọn market/channel strategy

---

## S5 — OPERATE & GROW

### Câu hỏi chính

> Làm sao vận hành ổn định, có lợi nhuận hoặc tăng trưởng bền vững?

### Quản trị ưu tiên

- OKRs
- 12 Week Year
- Weekly Tactics
- Task execution
- Daily Top 3
- Weekly Review
- Finance
- Customer Health
- Process
- SOP
- Automation
- AI Workforce
- Team Capability

### Artifacts

- Objectives
- OKRs
- 12 Week Cycle
- Weekly Tactics
- Scoreboard
- SOP
- Process Map
- Automation
- Customer Health
- Operating Review

### Metrics

- revenue;
- margin;
- cash;
- retention;
- churn;
- productivity;
- delivery quality;
- support;
- customer health.

### Framework

- OKRs
- 12 Week Year
- PDCA / Review loops
- Company Health
- SWOT/TOWS khi strategic review
- PESTEL khi external change

### BSC

Không cần expose bắt buộc dưới tên BSC.

Có thể sử dụng tư duy BSC phía sau **Company Health**.

---

## S6 — SCALE & GOVERN

### Câu hỏi chính

> Làm sao mở rộng tổ chức mà không mất kiểm soát?

### Quản trị ưu tiên

- Portfolio
- Organization
- Department
- Delegation
- Governance
- Risk
- Compliance
- Capital Allocation
- Management Reporting
- Multi-project alignment

### Metrics

Cân bằng:

```text
Financial
Customer
Operations
Capability
Risk
```

### Framework

- BSC / Strategy Balance
- TOWS
- PESTEL
- Portfolio Management
- Risk Management
- Governance

---

# 5. Stage không chỉ liên kết với các bảng Startup

Stage phải là context ảnh hưởng toàn hệ thống.

## 5.1. Các nhóm entity chính

```text
Company
Project

Hypothesis
Evidence
Experiment
Decision

CustomerSegment
ICP
Customer
Interview
Problem
JTBD

Solution
Product
Feature
ValueProposition
Pricing

Channel
Campaign
Lead
Opportunity
CustomerAccount
CRMActivity

Revenue
Expense
Cashflow
FinancialMetric

Objective
KeyResult
Cycle
Tactic
Task
DailyTop3
Review
Scoreboard

Risk
LegalItem
ComplianceItem
Contract
IPAsset

Agent
Skill
Workflow
Automation

Artifact
KnowledgeSource
```

Mỗi entity quan trọng nên có khả năng truy ngược:

```yaml
context:
  company_id:
  project_id:
  company_stage:
  project_stage:
  source:
  evidence_refs: []
  confidence:
```

Không nhất thiết duplicate stage vào mọi table nếu có thể resolve qua Project, nhưng service layer phải luôn cung cấp **resolved stage context**.

---

# 6. Management Policy Engine

Đây là component mới nên bổ sung vào COSA.

## 6.1. Trách nhiệm

Management Policy Engine trả lời:

1. Stage hiện tại là gì?
2. Primary Goal là gì?
3. Metric nào quan trọng?
4. Artifact nào bắt buộc?
5. Framework nào nên dùng?
6. Framework nào chưa nên dùng?
7. Agent nào được ưu tiên?
8. Workflow nào phù hợp?
9. Review cadence nào phù hợp?
10. Điều kiện chuyển Stage là gì?

---

## 6.2. Ví dụ policy cho S2

```yaml
stage: solution_validation

primary_goal:
  validate_solution_value

primary_questions:
  - Does the solution change customer behavior?
  - Will the customer commit?
  - Will the customer pay?

required_entities:
  - hypothesis
  - evidence
  - experiment
  - solution
  - pricing

primary_metrics:
  - activation
  - pilot_commitment
  - willingness_to_pay
  - time_to_value

recommended_methods:
  - lean_experiment
  - value_proposition
  - pricing_test
  - prototype_test

optional_lenses:
  - pestel

deemphasized:
  - bsc
  - nps
  - departmental_okrs
  - full_sop

review_frequency:
  weekly
```

---

## 6.3. Ví dụ policy cho S5

```yaml
stage: operate_growth

primary_goal:
  sustainable_growth

required_entities:
  - objective
  - key_result
  - twelve_week_cycle
  - metric
  - customer_account
  - cashflow

primary_metrics:
  - revenue
  - margin
  - retention
  - cash
  - productivity

recommended_methods:
  - okr
  - twelve_week_year
  - company_health
  - process_management
  - automation

strategy_lenses:
  - swot
  - tows
  - pestel

review_frequency:
  weekly_and_quarterly
```

---

# 7. Assumption & Evidence Engine

Đây phải là xương sống từ S0 đến ít nhất S4.

## 7.1. Hypothesis entity

```yaml
hypothesis:
  id:
  company_id:
  project_id:

  category:
    # customer | problem | solution | pricing
    # channel | revenue | cost | technology
    # legal | operational

  statement:

  importance:
  uncertainty:
  risk_score:

  evidence_score:
  confidence:

  status:
    # untested | testing | supported
    # contradicted | invalidated

  evidence_refs: []
  experiment_refs: []

  next_action:
```

---

## 7.2. Evidence entity

```yaml
evidence:
  id:
  project_id:

  type:
    # interview
    # observation
    # behavioral
    # transaction
    # usage
    # campaign
    # financial
    # legal
    # market_signal

  source:
  captured_at:

  claim_supported:

  strength:
    # weak | medium | strong

  direction:
    # supports | contradicts | neutral

  hypothesis_refs: []

  artifact_refs: []
```

---

## 7.3. Evidence Ladder

COSA nên có thang bằng chứng:

```text
E0 Opinion
   ↓
E1 Stated Interest
   ↓
E2 Observed Problem
   ↓
E3 Behavioral Commitment
   ↓
E4 Economic Commitment
   ↓
E5 Repeat Behavior
   ↓
E6 Repeatable / Scalable Evidence
```

Không cho AI coi:

> “khách hàng nói thích sản phẩm”

tương đương:

> “khách hàng đã trả tiền”.

---

# 8. Stage Transition Engine

Không để founder đơn giản bấm:

> Advance to next stage

mà COSA phải đánh giá.

## 8.1. Transition

```text
Stage
   ↓
Exit Criteria
   ↓
Evidence
   ↓
Readiness Score
   ↓
Recommendation
```

Kết quả:

```text
CONTINUE
ADVANCE
PIVOT
PAUSE
STOP
```

Founder/admin vẫn giữ quyền quyết định cuối cùng.

---

## 8.2. Readiness không chỉ là một số %

Readiness cần kèm giải thích:

```yaml
stage_readiness:

  score: 68

  strong:
    - customer_problem
    - solution_usage

  weak:
    - willingness_to_pay
    - pricing

  blockers:
    - hypothesis_PRICING_03

  recommended_next_actions:
    - run_paid_pilot_experiment
    - interview_5_buyers
```

---

# 9. Điều chỉnh PESTEL

## 9.1. Có đưa lại

**Có.**

Nhưng không đưa lại thành mandatory workflow.

### Vai trò mới

> External Environment Lens

Dùng khi:

- regulation cao;
- legal exposure cao;
- công nghệ biến động nhanh;
- macro economy ảnh hưởng business;
- market entry;
- strategic review.

---

## 9.2. Output PESTEL mới

Không lưu một bài phân tích dài.

Lưu thành External Signals:

```yaml
external_signal:
  factor: legal
  event:
  impact:
  direction:
  affected_projects: []
  affected_hypotheses: []
  affected_metrics: []
  required_action:
```

Pipeline:

```text
External Signal
    ↓
Impact
    ↓
Risk / Opportunity
    ↓
Affected Assumption
    ↓
Decision / Action
```

---

# 10. Điều chỉnh SWOT

## 10.1. Không bắt buộc

SWOT chỉ có giá trị khi đã có dữ liệu thật.

Nên bật chủ yếu từ S3 trở đi.

## 10.2. Evidence-backed SWOT

Mỗi Strength/Weakness/Opportunity/Threat phải tham chiếu evidence.

Ví dụ:

```yaml
swot_item:
  type: weakness
  statement: onboarding takes too long
  evidence_refs:
    - metric_onboarding_01
    - customer_support_23
  confidence: high
```

Không cho AI sinh SWOT chung chung mà không có căn cứ.

---

# 11. Điều chỉnh TOWS

TOWS nên quay lại với vai trò:

> **Strategy Option Generator**

Input:

```text
Internal Evidence
+
External Environment
+
Current Stage
+
Current Constraint
```

Output:

```text
Strategic Option A
Strategic Option B
Strategic Option C
```

Mỗi option phải có:

```yaml
strategy_option:
  hypothesis:
  rationale:
  evidence_refs: []
  expected_impact:
  risk:
  cost:
  time_to_evidence:
  recommended_experiment:
```

Founder quyết định chọn option.

---

# 12. Điều chỉnh BSC

## 12.1. Không dùng ở startup early stage

Không ưu tiên trong:

- S0
- S1
- S2
- S3

## 12.2. Dùng tư duy BSC từ S5-S6

Không cần đưa lại một menu “BSC” nếu chưa cần.

Có thể implement dưới dạng:

# Company Health

```text
FINANCIAL
Revenue
Margin
Cash

CUSTOMER
Retention
Customer Health
NPS/CSAT

OPERATIONS
Quality
Cycle Time
Delivery
Automation

CAPABILITY
People
Knowledge
AI Workforce
Process Maturity
```

BSC trở thành methodology phía sau Company Health.

---

# 13. OKRs phải Stage-aware

Không dùng cùng một kiểu OKR cho mọi Stage.

## S1 — Learning OKR

```text
Objective:
Validate that hotel marketing teams have
a painful competitor monitoring problem.

KR:
- 15 qualified interviews
- 8 verified pain cases
- 5 pilot interests
```

## S2 — Validation OKR

```text
Objective:
Validate solution value and willingness-to-pay.

KR:
- 5 qualified prototype tests
- 3 pilot commitments
- 2 paid pilots
```

## S4 — GTM OKR

```text
Objective:
Find one repeatable acquisition channel.
```

## S5 — Operating OKR

```text
Objective:
Grow revenue while maintaining retention
and healthy cash flow.
```

---

# 14. 12 Week Year phải Stage-aware

12 Week Year vẫn là execution engine mạnh của COSA.

Nhưng template thay đổi theo Stage.

```text
S1 → Problem Validation Cycle
S2 → Solution Validation Cycle
S3 → Business Validation Cycle
S4 → GTM Cycle
S5 → Operating/Growth Cycle
S6 → Scale/Transformation Cycle
```

Quan hệ:

```text
Stage
  ↓
Objective Type
  ↓
12 Week Cycle Template
  ↓
Weekly Tactics
  ↓
Tasks
  ↓
Daily Top 3
  ↓
Scoreboard
  ↓
Weekly Review
```

---

# 15. Finance phải Stage-aware

## S0-S1

Chỉ cần:

- available cash;
- spending limit;
- validation budget.

## S2

- MVP budget;
- experiment cost;
- pricing hypotheses.

## S3

- revenue;
- gross margin;
- CAC;
- LTV hypothesis;
- runway.

## S4

- channel CAC;
- sales cost;
- contribution margin;
- cash efficiency.

## S5-S6

- full management finance;
- forecasting;
- budgeting;
- variance;
- profitability;
- capital allocation.

Phân biệt:

```text
Management Finance
≠
Accounting / Regulatory Finance
```

---

# 16. Marketing / Sales / CRM phải Stage-aware

## S0-S1

Không bật CRM nặng.

Chỉ cần:

```text
Interview contacts
Research contacts
Problem signals
```

## S2

```text
Pilot candidates
Demo tracking
Pricing conversations
```

## S3

```text
Lead
Opportunity
Proposal
Paid pilot
Won/Lost
```

## S4

CRM đầy đủ:

```text
Audience
→ Lead
→ Qualified
→ Opportunity
→ Proposal
→ Won/Lost
→ Customer
→ Retention
```

## S5-S6

Bổ sung:

- account management;
- customer health;
- expansion;
- renewal;
- forecasting;
- team ownership.

---

# 17. Legal phải Stage-aware

## S0-S1

- founder ownership;
- basic NDA nếu cần;
- critical regulatory check.

## S2-S3

- IP ownership;
- contracts;
- business registration requirements;
- data/privacy implications.

## S4-S5

- tax;
- invoice;
- employment;
- customer contracts;
- trademark;
- compliance.

## S6

- governance;
- risk;
- corporate controls;
- advanced compliance.

Legal knowledge phải nằm trong **local knowledge packs**, có metadata:

```yaml
jurisdiction:
source:
effective_date:
retrieved_at:
version:
verification_status:
```

---

# 18. Agent Architecture

Không tạo Agent theo bài học/framework.

Đề xuất domain agents:

```text
Research Agent
Customer Agent
Product Agent
Marketing Agent
Sales / CRM Agent
Finance Agent
Legal / Knowledge Agent
Execution Agent
```

Phía trên:

```text
COSA Router
    ↓
Context Resolver
    ↓
Stage Resolver
    ↓
Management Policy Engine
    ↓
Agent / Skill / Workflow
```

Pipeline:

```text
Founder Request
      ↓
Intent
      ↓
Company + Project Context
      ↓
Current Stage
      ↓
Current Constraint
      ↓
Relevant Agent
      ↓
Skills
      ↓
Artifact / Evidence / Action
```

---

# 19. Knowledge Architecture

Kiến thức SIHUB không hard-code vào system prompt.

Đề xuất:

```text
knowledge/
├── startup/
│   ├── customer-discovery/
│   ├── jtbd/
│   ├── value-proposition/
│   ├── business-model/
│   ├── pricing/
│   ├── gtm/
│   ├── experiments/
│   └── metrics/
│
├── strategy/
│   ├── pestel/
│   ├── swot/
│   ├── tows/
│   └── bsc/
│
├── management/
│   ├── okr/
│   ├── 12-week-year/
│   ├── review/
│   └── operating-health/
│
└── legal/
    └── vietnam/
```

Mỗi knowledge item cần:

```yaml
id:
title:
domain:
applicable_stages: []
source:
version:
effective_date:
tags: []
```

---

# 20. Hologram Hub — Stage-aware UI

Không đưa tất cả chức năng ra dashboard cùng lúc.

Homepage ưu tiên:

```text
PROJECT

Current Stage
Current Goal
Current Constraint
Stage Readiness
Critical Evidence Gap
Next Best Action
```

Ví dụ:

```text
Project: COSA Hotel Intelligence

STAGE
Business Validation

CURRENT GOAL
Prove repeatable paid demand

READINESS
Customer    92%
Problem     85%
Solution    74%
Pricing     56%
Revenue     31%

CRITICAL CONSTRAINT
Revenue validation

NEXT BEST ACTION
Run 3 paid pilot offers
```

Sau đó mới hiển thị Domain Cards liên quan Stage.

### S1

Ưu tiên:

- Customer
- Interview
- Evidence
- Problem

### S3

Ưu tiên:

- Sales
- Pricing
- Finance
- Evidence

### S4

Ưu tiên:

- Marketing
- Sales
- CRM
- GTM

### S5

Ưu tiên:

- OKRs
- 12WY
- Finance
- Operations
- Customer Health

---

# 21. Chat / Voice Behavior

Stage phải trở thành context nhưng **không được ép vào mọi câu chat**.

Ví dụ user nói:

> Chào

COSA chỉ trả lời hội thoại bình thường.

Không tự động:

> “Project của bạn đang ở S2...”

Chỉ sử dụng Project/Stage context khi intent có liên quan:

- dự án;
- startup;
- chiến lược;
- planning;
- marketing;
- finance;
- sales;
- validation;
- execution.

Ví dụ:

> Tôi nên làm gì tiếp theo với project X?

Lúc này:

```text
Intent
→ Resolve project
→ Resolve stage
→ Evaluate constraints
→ Recommend next action
```

---

# 22. Artifact Contract

Mọi artifact quan trọng nên có format chung:

```yaml
artifact:
  id:
  type:
  company_id:
  project_id:

  title:
  status:
  version:

  stage_created:
  stage_applicable:

  inputs: []

  hypothesis_refs: []
  evidence_refs: []

  confidence:

  conclusions: []
  decisions: []
  next_actions: []

  dependencies: []

  created_by:
  created_at:
  updated_at:
```

Điều này giúp COSA hiểu:

> Artifact dựa vào dữ liệu nào và còn đáng tin hay không.

---

# 23. Decision Log

Bổ sung entity bắt buộc:

```yaml
decision:
  id:
  project_id:

  question:
  selected_option:

  alternatives: []

  rationale:
  evidence_refs: []

  stage:

  expected_result:
  review_date:

  status:
```

Về lâu dài, đây trở thành **Company Memory**.

COSA phải có khả năng trả lời:

> Tại sao trước đây chúng ta chọn phân khúc này?

bằng Decision + Evidence, không phải dựa vào chat history mơ hồ.

---

# 24. Next Best Action Engine

COSA cần một service đánh giá:

```text
Stage
+
Goal
+
Constraints
+
Evidence Gaps
+
Tasks
+
Cash / Capacity
```

và trả về tối đa 1–3 Next Best Actions.

Không đổ 20 đề xuất lên founder.

Ví dụ:

```yaml
next_best_action:

  title:
    Run paid pilot experiment

  reason:
    Pricing confidence is currently low

  related_hypothesis:
    pricing_03

  expected_evidence:
    economic_commitment

  estimated_effort:
    medium

  priority:
    critical
```

---

# 25. Migration từ kiến trúc hiện tại

Không cần phá cấu trúc COSA hiện có.

Triển khai từng bước.

## Phase 1 — Foundation

Bổ sung:

```text
company_stage
project_stage
stage_history
stage_policy
```

Tạo:

- Stage Resolver
- Stage Policy Service

Không thay UI lớn ngay.

---

## Phase 2 — Evidence Core

Bổ sung:

```text
hypotheses
evidence
experiments
decisions
```

Liên kết với Project và Artifact.

---

## Phase 3 — Stage-aware Existing Modules

Điều chỉnh:

- Objectives
- OKRs
- 12WY
- Tasks
- Finance
- Marketing
- Sales/CRM
- Legal

để nhận `StageContext`.

---

## Phase 4 — Strategy Lens Engine

Đưa lại:

- PESTEL
- SWOT
- TOWS
- BSC

theo nguyên tắc:

```text
Method = callable lens
NOT mandatory module
```

---

## Phase 5 — Hologram Hub

Bổ sung:

- Current Stage
- Current Goal
- Current Constraint
- Readiness
- Evidence Gaps
- Next Best Action

Ẩn/de-emphasize domain chưa cần.

---

## Phase 6 — Adaptive Agent Routing

Router sử dụng:

```text
intent
+
project
+
stage
+
policy
+
permissions
```

để chọn:

- Agent
- Skill
- Knowledge Pack
- Workflow

---

# 26. Không được triển khai các anti-pattern sau

## Anti-pattern 1

```text
Tạo menu riêng:
PESTEL / SWOT / TOWS / BSC
```

rồi bắt user thực hiện tuần tự.

**Không làm.**

---

## Anti-pattern 2

Startup nào cũng dùng đầy đủ:

```text
AARRR
NPS
OKR
BSC
CRM
SOP
```

**Không làm.**

---

## Anti-pattern 3

Chỉ dùng Stage để hiển thị badge.

```text
Stage: S2
```

nhưng workflow không thay đổi.

**Không làm.**

Stage phải thực sự thay đổi:

- metric;
- agent;
- method;
- UI;
- workflow;
- review;
- objective type.

---

## Anti-pattern 4

Cho AI tự tăng Stage chỉ bằng suy luận.

**Không làm.**

AI recommend.

Founder/admin quyết định nếu transition quan trọng.

---

## Anti-pattern 5

Artifact không có evidence lineage.

**Không làm.**

Mọi artifact chiến lược phải biết nó dựa trên:

- assumption nào;
- evidence nào;
- confidence nào.

---

# 27. Acceptance Criteria

Tích hợp được xem là thành công khi:

### AC-01

Một Company có thể ở S5 trong khi một Project mới ở S1.

### AC-02

COSA dùng Project Stage để thay đổi đề xuất hành động.

### AC-03

S1 không hiển thị NPS/BSC như KPI chính.

### AC-04

S4 ưu tiên Marketing/Sales/CRM.

### AC-05

S5 ưu tiên OKRs/12WY/Finance/Operations.

### AC-06

PESTEL không chạy bắt buộc khi tạo Project.

### AC-07

SWOT item phải tham chiếu evidence khi dùng cho decision.

### AC-08

TOWS tạo strategic options thay vì tạo báo cáo mô tả.

### AC-09

BSC không xuất hiện bắt buộc trước S5.

### AC-10

Stage transition phải có Exit Criteria + Evidence.

### AC-11

Artifact chiến lược chứa `evidence_refs`.

### AC-12

Hologram Hub hiển thị:

```text
Stage
Goal
Constraint
Readiness
Evidence Gap
Next Action
```

### AC-13

Chat “chào” không tự động trigger Project Analysis.

### AC-14

Câu hỏi:

> Tôi nên làm gì tiếp theo?

kích hoạt Stage-aware recommendation.

### AC-15

COSA có thể giải thích:

> Vì sao đề xuất hành động này?

bằng Evidence + Stage Policy.

---

# 28. Kiến trúc cuối cùng cần hướng tới

```text
                 COSA INTERFACE
          Chat / Voice / Hologram Hub
                       │
                       ▼
                  Intent Router
                       │
                       ▼
                Context Resolver
                       │
            ┌──────────┴──────────┐
            ▼                     ▼
      Company Context       Project Context
            │                     │
            └──────────┬──────────┘
                       ▼
                 Stage Resolver
                       │
                       ▼
            Management Policy Engine
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Strategy      Operating     Knowledge
       Lenses        Methods       Methods
          │            │            │
          └────────────┼────────────┘
                       ▼
                Agent Orchestrator
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
       Skills       Workflows      Tools
          │            │             │
          └────────────┼─────────────┘
                       ▼
     Artifact / Evidence / Experiment / Decision
                       │
                       ▼
              Objectives / 12WY
                       │
                       ▼
             Tactics / Tasks
                       │
                       ▼
              Metrics / Results
                       │
                       ▼
                Weekly Review
                       │
                       ▼
               Stage Readiness
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
      Continue        Pivot        Advance
```

---

# 29. Quyết định cuối cùng về BSC / PESTEL / SWOT / TOWS

| Framework | Quyết định | Vai trò trong COSA |
|---|---|---|
| PESTEL | Đưa lại | External Environment Lens |
| SWOT | Đưa lại có điều kiện | Evidence-backed Strategic Snapshot |
| TOWS | Đưa lại | Strategic Option Generator |
| BSC | Đưa lại ở late stage | Company Health / Strategy Balance |
| OKRs | Giữ | Stage-aware Objective Engine |
| 12 Week Year | Giữ | Stage-aware Execution Engine |

Không framework nào được phép trở thành “cổng bắt buộc” nếu Stage và Strategic Question không yêu cầu.

---

# 30. Kết luận kiến trúc

COSA cần chuyển từ:

> **Feature-driven Founder App**

sang:

> **Stage-aware AI Founder & Company Operating System**

Kiến thức startup từ SIHUB được tích hợp vào **Startup Methodology / Knowledge Layer**, không phải biến thành khóa học.

Stage trở thành **management context** điều phối:

- dữ liệu;
- metric;
- framework;
- Agent;
- Skill;
- Workflow;
- Objective;
- OKR;
- 12 Week Year;
- Marketing;
- Sales/CRM;
- Finance;
- Legal;
- Risk;
- UI;
- review cadence.

PESTEL/SWOT/TOWS/BSC có thể quay lại, nhưng ở cấp độ trưởng thành hơn:

> **Không phải các module user phải đi qua.  
> Chúng là các công cụ COSA tự lựa chọn khi chúng thực sự giúp đưa ra quyết định tốt hơn.**

Nguyên tắc cốt lõi cuối cùng:

```text
STAGE
  ↓
QUESTION
  ↓
EVIDENCE
  ↓
METHOD
  ↓
DECISION
  ↓
EXECUTION
  ↓
RESULT
  ↓
LEARNING
  ↓
NEXT STAGE
```

Đây phải là vòng lặp vận hành trung tâm mới của COSA.
