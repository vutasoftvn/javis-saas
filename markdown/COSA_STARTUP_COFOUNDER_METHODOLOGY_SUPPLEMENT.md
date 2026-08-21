# COSA Startup Co-founder Methodology Supplement

**Status:** Draft v1.0  
**Purpose:** Bổ sung phương pháp luận Startup Co-founder cho COSA dựa trên Sổ tay hướng dẫn khởi nghiệp sáng tạo về hiệu quả năng lượng tại Việt Nam (AIS4EE) và kiến trúc hiện có của `vutasoftvn/javis-saas`.  
**Recommended repository path:** `docs/architecture/COSA_STARTUP_COFOUNDER_METHODOLOGY.md`  
**Scope:** Product methodology, stage flow, question graph, hypothesis/evidence logic, stage gates, next-best-action, capability routing, knowledge integration, vertical playbook architecture.  
**Non-goal:** Không tạo một hệ thống startup song song với Business Core, Validation, Strategy, Agent Runtime, Workflows hay Knowledge hiện có.

---

## 1. Executive Summary

Mục tiêu của tài liệu này là chuẩn hóa COSA thành một **AI Co-founder** có khả năng:

1. hiểu startup đang ở giai đoạn nào;
2. xác định câu hỏi quan trọng nhất cần trả lời tiếp theo;
3. phân biệt niềm tin của founder với giả định, giả thuyết, bằng chứng và quyết định;
4. chuyển hội thoại tự nhiên thành trạng thái kinh doanh có cấu trúc;
5. phát hiện giả định rủi ro cao;
6. đề xuất thí nghiệm nhỏ nhất có ích để thu bằng chứng;
7. đánh giá readiness theo stage;
8. phản biện founder khi bằng chứng chưa đủ;
9. đề xuất `PROCEED / TEST_MORE / PIVOT / PAUSE / STOP`;
10. tự động hoặc bán tự động thực thi các công việc phù hợp thông qua Skill + Tool + Workflow + Agent Profile hiện hữu.

COSA không nên trở thành một LMS, một thư viện “10 chương”, hoặc một chatbot trả lời chung chung. Sổ tay AIS4EE phải được chuyển thành **methodology, rule, question, evidence requirement, experiment pattern, artifact template, capability routing và knowledge context**.

North Star:

```text
Founder Input
    ↓
Epistemic Classification
    ↓
Stage Context
    ↓
Highest-Risk Assumption
    ↓
Best Question / Best Experiment
    ↓
Evidence
    ↓
Review
    ↓
Founder Decision
    ↓
Next Best Action
    ↓
Execution
    ↓
Learning
```

---

## 2. Basis and Source Boundaries

### 2.1 Nội dung lấy trực tiếp từ Sổ tay AIS4EE

Sổ tay tổ chức hành trình thành sáu giai đoạn:

- Giai đoạn 1: Ý tưởng — tìm kiếm ý tưởng và định hình đúng vấn đề.
- Giai đoạn 2: Xác thực — chứng minh ý tưởng có thị trường.
- Giai đoạn 3: Phát triển mô hình kinh doanh.
- Giai đoạn 4: Tạo mẫu và thử nghiệm.
- Giai đoạn 5: Ra mắt.
- Giai đoạn 6: Mở rộng quy mô.

Các chương tiếp theo bổ sung:
- tài chính và cơ hội đầu tư;
- nhân lực và cơ sở hạ tầng;
- công nghệ, đổi mới sáng tạo và SHTT;
- nghiên cứu thị trường, thu hút khách hàng, thương hiệu;
- scale readiness, risk và KPI.

Trong Customer Discovery, sổ tay nhấn mạnh:
- mục tiêu là lắng nghe, quan sát và học hỏi, không pitch giải pháp quá sớm;
- cần nhận diện người ra quyết định, người dùng và người có ảnh hưởng;
- tương tác trực tiếp trong bối cảnh Việt Nam có giá trị đặc biệt;
- prototype và pilot là công cụ học hỏi và chứng minh;
- mô hình kinh doanh cần được kiểm chứng;
- scale phải dựa trên readiness thay vì tăng trưởng bằng mọi giá.

### 2.2 Nội dung là thiết kế bổ sung của COSA

Các khái niệm sau là đề xuất sản phẩm/kiến trúc của COSA, không phải nguyên văn từ sổ tay:

- Question Graph.
- Stage Question Policy.
- Highest-Leverage Question.
- Readiness Gate Policy.
- Core Startup Methodology Pack.
- Energy Efficiency Vertical Pack.
- Co-founder State Snapshot.
- capability routing theo stage.
- deterministic + evidence + AI reasoning.
- cách ánh xạ nội dung sổ tay vào model, service, workflow và UX hiện có.

Mọi threshold cụ thể như “cần N cuộc phỏng vấn” phải là **versioned methodology configuration**, không được coi là quy định mặc định có tính phổ quát nếu nguồn không quy định như vậy.

---

## 3. Architecture Principles

Tài liệu này phải tuân thủ `CLAUDE.md` và `COSA_CANONICAL_OWNERSHIP_MAP.md`.

### 3.1 Không tạo một Startup OS song song

Không tạo các subsystem mới dạng:

```text
new_startup_core/
new_evidence_engine/
new_scale_engine/
new_cofounder_agents/
```

nếu capability tương ứng đã có owner.

COSA hiện đã có:
- Business Core;
- Strategy;
- Validation;
- Finance;
- Legal;
- Marketing;
- Sales;
- Organization;
- Tasks;
- Learning;
- Agent Runtime;
- Agent Profiles;
- Workflows;
- Tools;
- Knowledge;
- Next Action;
- Stage transition audit.

### 3.2 Business logic phải deterministic khi có thể

Ví dụ:

```text
IF project.stage == S1_PROBLEM_VALIDATION
AND no buyer evidence
THEN block S2 transition
```

không được chỉ viết trong prompt kiểu:

> “Hãy cân nhắc xem startup có đủ bằng chứng người mua chưa.”

LLM giải thích, phản biện và đề xuất.  
Code quyết định invariants, permission, state transition và gate.

### 3.3 Conversation không phải source of truth

Chat là input surface.

Source of truth phải là structured state:

```text
Claim
Assumption
Hypothesis
Experiment
Evidence
Customer
Interview
Metric
Milestone
Decision
Stage
Task
Artifact
```

### 3.4 AI recommendation không thay founder decision

COSA:
- chẩn đoán;
- đưa khuyến nghị;
- chỉ ra bằng chứng thiếu;
- đề xuất hành động.

Founder hoặc decision owner:
- xác nhận claim quan trọng;
- chấp thuận pivot;
- quyết định stage transition;
- chấp thuận hành động có rủi ro cao.

---

## 4. Canonical Startup Journey

Sổ tay AIS4EE dùng sáu giai đoạn. COSA hiện có stage vocabulary ở `Project.project_stage`:

```text
S0_EXPLORE
S1_PROBLEM_VALIDATION
S2_SOLUTION_VALIDATION
S3_BUSINESS_VALIDATION
S4_GO_TO_MARKET
S5_OPERATE_GROWTH
S6_SCALE_GOVERN
```

Đề xuất: đây là **startup stage backbone** cho methodology mới.

### 4.1 Mapping

| COSA Stage | AIS4EE | Câu hỏi điều hành |
|---|---|---|
| S0_EXPLORE | Ý tưởng | Có cơ hội đáng để đầu tư thời gian khám phá không? |
| S1_PROBLEM_VALIDATION | Ý tưởng + Xác thực | Có một vấn đề thực, đủ đau, của khách hàng cụ thể không? |
| S2_SOLUTION_VALIDATION | Xác thực + Tạo mẫu | Giải pháp có tạo ra outcome và khách hàng chấp nhận không? |
| S3_BUSINESS_VALIDATION | Mô hình kinh doanh | Mô hình tạo, giao và thu giá trị có khả thi không? |
| S4_GO_TO_MARKET | Ra mắt | Có thể tìm, thuyết phục và chuyển đổi khách hàng lặp lại không? |
| S5_OPERATE_GROWTH | Ra mắt + đầu Scale | Có thể vận hành tăng trưởng với economics và chất lượng kiểm soát được không? |
| S6_SCALE_GOVERN | Mở rộng quy mô | Có thể nhân rộng mà không phá economics, team, quality, compliance và capital efficiency không? |

### 4.2 Architecture warning

`backend/core/validation/enums.py` hiện còn một `ProjectStage` khác:

```text
IDEA
VALIDATION
MVP
EARLY_TRACTION
GROWTH
SCALE
PAUSED
SUNSET
```

Không được tạo vocabulary thứ ba.

Trước implementation:
1. consumer scan hai stage vocabularies;
2. xác định canonical transition model;
3. giữ adapter/compatibility nếu cần;
4. methodology pack chỉ tham chiếu canonical stage ID.

---

# 5. COSA Co-founder Operating Loop

Mỗi lượt meaningful co-founder interaction phải đi qua chu trình sau.

```text
1. Understand
2. Classify
3. Diagnose
4. Challenge
5. Ask
6. Structure
7. Test
8. Review
9. Decide
10. Execute
11. Learn
```

### 5.1 Understand

Thu thập context đúng phạm vi:
- workspace/company;
- project;
- current stage;
- active milestone;
- recent decisions;
- open risks;
- evidence state;
- active experiments;
- relevant finance/sales/legal/operations state.

Không load toàn công ty nếu user chỉ chào hoặc hỏi chung.

### 5.2 Classify

Mỗi statement quan trọng phải phân loại epistemic:

```text
FACT
BELIEF
ASSUMPTION
HYPOTHESIS
EVIDENCE
DECISION
```

Ví dụ:

Founder:
> “Nhà máy sẽ tiết kiệm 30%.”

COSA không lưu thành fact.

Đề xuất:

```json
{
  "type": "ASSUMPTION",
  "dimension": "SOLUTION",
  "statement": "Target factories can reduce energy consumption by 30%",
  "source": "FOUNDER_CHAT",
  "confidence": 0.3
}
```

### 5.3 Diagnose

COSA xác định:
- stage hiện tại;
- stage goal;
- dimension yếu nhất;
- assumption có risk score cao nhất;
- evidence gap;
- blocker;
- readiness.

### 5.4 Challenge

COSA phải chủ động hỏi:
- “Bạn biết điều này hay đang tin điều này?”
- “Bằng chứng nào khiến bạn tin vậy?”
- “Có evidence nào đi ngược lại không?”
- “Nếu giả định này sai, dự án thiệt hại bao nhiêu?”
- “Cách kiểm chứng rẻ nhất là gì?”

AI Co-founder không chỉ hỗ trợ; nó phải chống confirmation bias.

### 5.5 Ask

Không hỏi một questionnaire dài.

Ưu tiên:

```text
Highest-Leverage Question
=
question giúp giảm uncertainty lớn nhất
trên assumption quan trọng nhất
với effort hợp lý
```

### 5.6 Structure

Câu trả lời phải cập nhật structured state:
- StructuredClaim;
- DimensionState;
- ValidationAssumption;
- CustomerContact;
- Problem score;
- Hypothesis;
- Experiment;
- Evidence;
- Milestone;
- Metric;
- Next Action.

### 5.7 Test → Review → Decide

Flow chuẩn:

```text
Assumption
   ↓
Testable Hypothesis
   ↓
Smallest Useful Experiment
   ↓
Evidence
   ↓
AI/Human Review
   ↓
Founder Decision
```

Codebase hiện đã có chính chuỗi:
`ValidationAssumption → ValidationHypothesis → ValidationExperiment → ValidationEvidence → ValidationReview → ValidationDecision`.

Đây phải là validation chain chính thay vì tạo schema mới.

---

# 6. Stage 0 — EXPLORE

## 6.1 Objective

Biến “ý tưởng” thành một opportunity statement đủ rõ để quyết định:
- khám phá tiếp;
- defer;
- bỏ;
- hoặc chuyển thành S1.

## 6.2 Câu hỏi trọng tâm

### Founder fit
- Vì sao founder/team quan tâm vấn đề này?
- Có access đặc biệt nào tới customer/domain/data không?
- Team có lợi thế hiểu biết/công nghệ/quan hệ gì?
- Tại sao bây giờ?
- Điều gì khiến opportunity này đáng theo đuổi hơn các opportunity khác?

### Problem landscape
- Vấn đề bạn quan sát là gì?
- Nó xảy ra ở đâu?
- Ai chịu hậu quả?
- Hậu quả là tiền, thời gian, chất lượng, rủi ro, compliance hay năng lượng?
- Họ đang xử lý thế nào?
- Điều gì đã thay đổi khiến vấn đề trở nên cấp bách?

### Opportunity
- Market driver nào tạo cơ hội?
- Có regulation, technology shift, cost pressure hoặc behavior shift nào?
- Có evidence sơ bộ nào ngoài trực giác founder?

## 6.3 Assumptions cần tạo

```text
FOUNDER
CUSTOMER
PROBLEM
TECHNICAL
LEGAL
FINANCE
```

Chưa cần tạo đầy đủ pricing/channel/revenue nếu chưa có problem clarity.

## 6.4 Evidence phù hợp

- desk research;
- domain expert conversation;
- public market data;
- regulation;
- observed workflow/problem;
- founder experience được đánh dấu là founder evidence, không tự nâng thành market evidence.

## 6.5 Exit Gate đề xuất

S0 → S1 khi:
- có customer context đủ cụ thể;
- có problem candidate;
- có reason-to-believe;
- có access path tới real customers;
- không có obvious fatal constraint chưa được acknowledge.

Output:
- Opportunity Brief;
- Initial Assumption Map;
- Top 3 Unknowns;
- Customer Discovery Plan.

---

# 7. Stage 1 — PROBLEM VALIDATION

Đây là stage quan trọng nhất đối với startup mới.

Sổ tay yêu cầu định hình vấn đề theo context, customer, root cause và impact; customer discovery phải tập trung vào lắng nghe và quan sát trước khi pitch solution.

## 7.1 Objective

Chứng minh:

> Một nhóm khách hàng cụ thể thực sự gặp một vấn đề đủ quan trọng để họ thay đổi hành vi, đầu tư thời gian, ngân sách hoặc chấp nhận thử giải pháp.

## 7.2 Problem Decomposition

COSA phải dẫn founder đi qua:

```text
Context
Customer
Job / Workflow
Trigger
Problem
Root Cause
Frequency
Severity
Current Alternative
Economic Impact
Operational Impact
Emotional/Risk Impact
Decision Ownership
Urgency
```

## 7.3 Question Graph — Problem

### Q1. Context
“Vấn đề này xảy ra trong bối cảnh cụ thể nào?”

Follow-up:
- ngành;
- quy mô;
- location;
- workflow;
- equipment/process;
- thời điểm.

### Q2. Customer
“Ai là người trực tiếp chịu hậu quả?”

Follow-up:
- user;
- buyer;
- decision maker;
- influencer.

### Q3. Past behavior
“Lần gần nhất vấn đề xảy ra là khi nào?”

Mục tiêu: tránh hypothetical answer.

### Q4. Frequency
“Trong 30/90 ngày gần đây nó xảy ra bao nhiêu lần?”

### Q5. Severity
“Lần đó gây mất bao nhiêu tiền, thời gian, sản lượng, chất lượng hoặc rủi ro?”

### Q6. Current alternative
“Hiện tại họ xử lý bằng cách nào?”

### Q7. Cost of alternative
“Cách hiện tại tốn bao nhiêu?”

### Q8. Root cause
“Tại sao cách hiện tại chưa giải quyết được?”

### Q9. Decision process
“Ai có quyền phê duyệt việc thay đổi?”

### Q10. Urgency
“Điều gì khiến họ phải xử lý trong 3–12 tháng tới?”

## 7.4 Question Quality Rules

Ưu tiên:
- `PAST_BEHAVIOR`
- `CURRENT_BEHAVIOR`
- `COST_DISCOVERY`
- `ALTERNATIVE_DISCOVERY`

Cảnh báo hoặc hạ trọng số:
- `OPINION`
- `HYPOTHETICAL_FUTURE`

Không dùng sớm:
- `LEADING`
- `SOLUTION_PITCH`

Codebase đã có `QuestionTypeEnum`; methodology phải dùng enum này để kiểm soát chất lượng interview.

## 7.5 Customer Role Coverage

Sổ tay yêu cầu phân biệt người ra quyết định, người dùng, người ảnh hưởng.

COSA phải kiểm tra interview portfolio:

```text
USER
BUYER
DECISION_MAKER
INFLUENCER
```

Ví dụ:
- 12 user interviews;
- 0 buyer;
- 0 decision maker.

Kết luận:
> “Pain evidence khá tốt, nhưng commercial evidence chưa đủ.”

## 7.6 Interview Processing

Input:
- note;
- transcript;
- voice-to-text;
- founder summary.

COSA phân tích thành:
- immutable verbatim quotes;
- interpretation;
- tags;
- buying signal;
- linked assumption;
- pain pattern;
- early adopter candidate.

Codebase đã support:
- `VerbatimQuote`;
- `PainPattern`;
- `EarlyAdopterCandidate`;
- `ProblemSeverityScorecard`.

## 7.7 Evidence Hierarchy

Một ví dụ ranking:

```text
Founder belief               → rất yếu
Desk research                → context
Survey answer                → stated
Customer interview           → stated + qualitative
Time investment              → behavioral
Observed behavior            → stronger
Action commitment            → stronger
Deposit / preorder           → very strong
Real payment                 → strongest commercial signal
```

Không equate:
> “Khách hàng nói thích” = “khách hàng sẽ mua”.

## 7.8 Exit Gate S1 → S2

Gate không phụ thuộc chỉ vào số interview.

Phải kiểm tra:
- customer segment specificity;
- repeated pain pattern;
- evidence-backed severity;
- current alternative;
- buyer/decision process evidence;
- urgency;
- problem hypothesis status;
- contradictory evidence;
- founder acknowledged risks.

Kết quả gate:
- `PASS`;
- `CONDITIONAL_PASS`;
- `TEST_MORE`;
- `CHALLENGED`;
- `FAIL`.

Founder decision:
- `PROCEED`;
- `TEST_MORE`;
- `PIVOT`;
- `PAUSE`;
- `STOP`.

---

# 8. Stage 2 — SOLUTION VALIDATION

## 8.1 Objective

Trả lời:

> “Giải pháp đề xuất có giải quyết vấn đề đủ tốt để khách hàng sử dụng, cam kết hoặc trả tiền không?”

## 8.2 Không nhảy thẳng vào build

COSA phải chặn pattern:

```text
weak problem evidence
+
large engineering commitment
```

bằng warning / guardrail.

## 8.3 Solution hypotheses

Tối thiểu:
- outcome hypothesis;
- usability hypothesis;
- technical feasibility;
- implementation/deployment;
- adoption;
- switching friction;
- trust;
- safety/compliance nếu liên quan.

## 8.4 Testable Hypothesis Standard

Codebase đã định nghĩa hypothesis gồm 5 thành phần:

```text
Action
Target
Metric
Threshold
Timeframe
```

COSA phải giúp founder chuyển assumption mơ hồ:

> “Khách hàng sẽ thích dashboard.”

thành:

> “Nếu 5 facility managers dùng prototype trong 7 ngày, ít nhất X người hoàn thành workflow Y mà không cần hướng dẫn ngoài onboarding.”

## 8.5 Experiment Selection

Ưu tiên experiment nhỏ nhất có ích:

- customer interview;
- prototype test;
- concierge MVP;
- landing page;
- fake door;
- waitlist;
- preorder;
- paid offer;
- sales call;
- pricing test;
- channel test;
- A/B test.

Không chọn experiment theo trend; chọn theo assumption.

## 8.6 Prototype vs Pilot

### Prototype
Mục tiêu:
- test usability;
- test workflow;
- test technical principle;
- test outcome direction;
- học nhanh với cost thấp.

### Pilot
Mục tiêu:
- chứng minh trong môi trường thật;
- đo outcome;
- đo implementation friction;
- tạo customer proof;
- tạo commercial proof.

Đối với vertical HQNL:

```text
Baseline
→ Intervention
→ Measurement
→ Reporting
→ Verification
→ Savings
→ Economic Value
```

## 8.7 S2 Exit Gate

- problem đã supported;
- key solution hypotheses được test;
- prototype/pilot tạo evidence;
- critical technical assumption không còn unknown;
- deployment risk understood;
- customer action signal xuất hiện;
- không có fatal compliance issue chưa xử lý.

---

# 9. Stage 3 — BUSINESS VALIDATION

## 9.1 Objective

Chứng minh startup có một mô hình có khả năng:
- tạo giá trị;
- giao giá trị;
- thu giá trị;
- có economics hợp lý.

## 9.2 Business model không phải form tĩnh

BMC/Lean Canvas phải là **projection của hypothesis state**, không phải source of truth.

Ví dụ:

```text
Customer Segment ← validated customer hypotheses
Problem          ← validated problem hypotheses
UVP              ← validated outcomes
Channels         ← channel experiments
Revenue          ← pricing/revenue tests
Costs            ← actual prototype/pilot costs
Partners         ← delivery constraints
```

## 9.3 Hypothesis taxonomy

- `CUSTOMER`
- `PROBLEM`
- `SOLUTION`
- `PRICING`
- `CHANNEL`
- `REVENUE`
- `TECHNICAL`
- `OPERATIONAL`
- `LEGAL`
- `FINANCE`
- `GROWTH`
- `FOUNDER`

## 9.4 Key questions

### Pricing
- Ai trả?
- Trả cho outcome hay output?
- Budget owner là ai?
- Payback kỳ vọng?
- Giá hiện tại của alternative?
- CapEx barrier?
- Subscription/leasing/shared-savings phù hợp không?

### Revenue
- One-time?
- Recurring?
- Usage?
- Performance-based?
- Services?
- Hardware + software?

### Cost
- COGS?
- Deployment?
- Support?
- Hardware?
- Cloud?
- Sales?
- Working capital?
- Warranty?

### Channel
- Founder-led sales?
- Partner?
- Distributor?
- ESCO/EPC?
- Digital?
- Enterprise outbound?

### Delivery
- Từ contract tới go-live mất bao lâu?
- Những bước nào custom?
- Có thể standardize gì?

## 9.5 Financial model integration

Không tạo Finance subsystem mới.

Kết nối với Finance core:
- revenue;
- expense;
- cash;
- burn;
- runway;
- budget variance.

Startup-specific financial readiness có thể là methodology layer trên Finance core.

## 9.6 Exit Gate

- có pricing evidence;
- revenue model rõ;
- delivery cost được ước lượng bằng actual data khi có;
- unit economics sơ bộ;
- customer willingness-to-pay hoặc commercial commitment;
- legal/business model risks acknowledged;
- path to repeatability hợp lý.

---

# 10. Stage 4 — GO TO MARKET

## 10.1 Objective

Chứng minh startup có thể tìm và chuyển đổi khách hàng theo một motion có khả năng lặp lại.

## 10.2 ICP

ICP không được chỉ là:
> “Nhà máy.”

Phải có:
- industry;
- size;
- geography;
- use case;
- trigger;
- pain intensity;
- budget characteristics;
- technical fit;
- procurement fit;
- compliance pressure;
- early-adopter characteristics.

## 10.3 First Customer Cohort

Nên theo dõi cohort khách hàng đầu tiên:

```text
Customer
Problem
Promise
Buyer
Sales Cycle
Objections
Deployment
Outcome
ROI
Payment
Feedback
Testimonial
Referral
Case Study Permission
```

Mục tiêu:
- học sales;
- học onboarding;
- học deployment;
- tạo proof;
- tạo reference;
- tạo case study.

## 10.4 GTM hypotheses

- ICP;
- trigger;
- message;
- channel;
- sales cycle;
- conversion;
- proof required;
- procurement;
- pricing acceptance;
- onboarding;
- retention.

## 10.5 Capability routing

COSA có thể route:
- research → Research capability;
- ICP → Marketing;
- outreach → Sales;
- CRM → Sales;
- contract → Legal;
- pricing → Finance + Sales;
- content → Marketing;
- customer proof → Marketing + Sales.

Không tạo agent mới cho từng task nếu profile/capability hiện hữu xử lý được.

## 10.6 Exit Gate

- một ICP có evidence;
- repeatable messaging bắt đầu xuất hiện;
- channel có signal;
- sales pipeline structured;
- conversion evidence;
- commercial objections được biết;
- onboarding/deployment có playbook;
- customer proof.

---

# 11. Stage 5 — OPERATE & GROW

## 11.1 Objective

Chuyển từ founder-dependent traction sang operating system.

## 11.2 Questions

- Sales có phụ thuộc founder 100% không?
- Delivery có SOP không?
- Deployment time có giảm?
- Margin có ổn định?
- Customer support có measurable?
- Cash conversion cycle?
- Working capital?
- Hiring bottleneck?
- Quality?
- Reliability?
- Churn?
- Customer success?
- Compliance?
- Incident handling?

## 11.3 Cross-domain routing

- Organization: role/capability gaps.
- Finance: cash, burn, runway.
- Sales: pipeline.
- Marketing: demand gen.
- Legal: contract/compliance.
- Strategy: milestones/OKRs.
- Tasks: execution.
- Learning: lessons.

## 11.4 Exit Gate

- growth không còn chỉ là one-off;
- operations có repeatability;
- financial runway understood;
- team/capacity plan;
- quality/risk controls;
- KPI ownership.

---

# 12. Stage 6 — SCALE & GOVERN

Sổ tay có Scale Readiness Scorecard, scale paths, risk matrix và KPI.

## 12.1 Objective

Trả lời:

> “Có thể nhân rộng mô hình mà economics, quality, culture, compliance và capital efficiency vẫn chấp nhận được không?”

## 12.2 Scale dimensions

- Product repeatability.
- Market repeatability.
- Sales repeatability.
- Deployment repeatability.
- Unit economics.
- Organization.
- Finance.
- Technology reliability.
- Compliance.
- Customer success.
- Capital readiness.

## 12.3 Strategic paths

Sổ tay nêu ba hướng lớn:
- đi sâu trong vertical hiện tại;
- geographic expansion;
- product-line expansion.

COSA nên yêu cầu founder chọn explicit strategy và đánh đổi.

## 12.4 Premature Scaling Rules

Ví dụ methodology rules:

```text
NO_SCALE_WITHOUT_REPEATABLE_CUSTOMER_EVIDENCE
NO_LARGE_SALES_HIRING_WITHOUT_REPEATABLE_SALES_MOTION
NO_GEOGRAPHIC_EXPANSION_WITHOUT_UNIT_ECONOMIC_VISIBILITY
NO_PRODUCT_LINE_EXPANSION_WHILE_CORE_DELIVERY_UNSTABLE
```

Energy pack có thể thêm:

```text
NO_EE_SCALE_WITHOUT_VERIFIED_SAVINGS
NO_PERFORMANCE_CONTRACT_SCALE_WITHOUT_MRV
NO_HARDWARE_SCALE_WITHOUT_DEPLOYMENT_COST_DATA
```

## 12.5 Stage output

- Scale Readiness Review;
- Risk Matrix;
- Scale Strategy;
- KPI Dashboard;
- Hiring/Capability Plan;
- Financing Plan;
- Governance Plan.

---

# 13. Cross-Stage Capability Tracks

Các chương 2, 3, 5, 6, 7, 8 của sổ tay không nên là stage riêng. Chúng là tracks chạy xuyên suốt.

| Track | Early stage | Mid stage | Growth/Scale |
|---|---|---|---|
| Market | problem/customer research | positioning/ICP | segmentation/expansion |
| Finance | funding need | unit economics/investor readiness | runway/growth capital |
| Team | founder fit | capability gaps | org design/hiring |
| Technology | feasibility | prototype/pilot/IP | reliability/scale |
| Legal/Policy | fatal constraints, market drivers | contracts/IP/compliance | governance/regulatory expansion |
| Ecosystem | mentors/access | pilot partners/funders | strategic partners |
| Impact | outcome hypothesis | pilot metrics | verified impact/reporting |

---

# 14. Question Graph Specification

Question Graph là methodology config, không nhất thiết là bảng DB mới.

## 14.1 Required fields

```yaml
id: problem.last_incident
version: 1
stage:
  - S1_PROBLEM_VALIDATION

dimension:
  - PROBLEM

question_type: PAST_BEHAVIOR

prompt:
  vi: "Lần gần nhất vấn đề này xảy ra là khi nào?"

purpose:
  "Chuyển thảo luận từ ý kiến sang hành vi thực tế."

required_when:
  - "problem.last_incident == null"

updates:
  - structured_claim
  - dimension_state

possible_followups:
  - when: "incident_found == true"
    ask: problem.frequency
  - when: "incident_found == false"
    action: challenge_problem_frequency

evidence_policy:
  accepted:
    - CUSTOMER_INTERVIEW
    - OBSERVED_BEHAVIOR

risk_effect:
  dimension: PROBLEM
```

## 14.2 Question selection score

Đề xuất:

```text
QuestionPriority =
AssumptionRisk
× EvidenceGap
× StageRelevance
× InformationGain
× Actionability
÷ ExpectedEffort
```

Formula cụ thể cần được kiểm nghiệm, nhưng selection phải deterministic/rule-driven trước, LLM chỉ rerank trong phạm vi cho phép.

## 14.3 Conversation rule

Một lượt chỉ nên hỏi:
- 1 câu chính;
- tối đa 1–2 follow-up thật cần thiết.

COSA không nên biến co-founder experience thành onboarding survey.

---

# 15. Epistemic State Machine

COSA đã có `EpistemicType` và claim confirmation state.

Đề xuất chuẩn hóa UX:

```text
BELIEF
  ↓ founder confirms importance
ASSUMPTION
  ↓ made testable
HYPOTHESIS
  ↓ experiment runs
EVIDENCE
  ↓ review
DECISION
```

State không nhất thiết tuyến tính; evidence có thể challenge hypothesis.

## 15.1 Claim policy

AI-inferred claim:
- không tự coi là founder-confirmed;
- phải có source;
- có thể bị superseded;
- phải trace được.

## 15.2 Contradictory evidence

COSA phải chủ động lưu evidence:
- supports;
- challenges;
- complicates;
- neutral.

Không cherry-pick evidence phù hợp narrative founder.

---

# 16. Validation Chain — Canonical Reuse

Codebase hiện có:

```text
ValidationAssumption
ValidationHypothesis
ValidationExperiment
ValidationEvidence
ValidationReview
ValidationDecision
```

Đây là lõi rất phù hợp với AIS4EE.

Không tạo:
- `StartupAssumptionV2`;
- `CofounderHypothesis`;
- `PilotEvidence2`.

Thay vào đó, mở rộng:
- taxonomy;
- experiment types khi có case thực;
- evidence policy;
- methodology config;
- UI.

---

# 17. Customer Discovery Protocol

## 17.1 Before Interview

COSA phải biết:
- segment;
- role;
- assumption cần test;
- interview goal;
- prohibited leading questions;
- expected evidence.

Output:
- interview brief;
- question guide;
- target roles.

## 17.2 During Capture

Founder có thể:
- ghi note;
- upload transcript;
- dictate;
- paste summary.

## 17.3 After Interview

COSA:
1. extract verbatim quote;
2. tách interpretation khỏi quote;
3. tag pain/cost/behavior/alternative/WTP/root cause/consequence;
4. identify buying signal;
5. link assumption;
6. update pattern;
7. identify contradiction;
8. propose next interview;
9. update scorecard.

## 17.4 Anti-bias rules

COSA cảnh báo:
- câu hỏi dẫn dắt;
- hỏi future hypothetical quá nhiều;
- chỉ phỏng vấn bạn bè;
- chỉ phỏng vấn user mà không buyer;
- pitch trước khi hiểu problem;
- summarize mà không giữ quote gốc.

---

# 18. Experiment Design Protocol

Mỗi experiment cần:

```text
Hypothesis
Experiment Type
Smallest Useful Scope
Target Segment
Metric
Success Threshold
Budget
Duration
Evidence Capture
Stop Condition
Decision Rule
```

COSA không chỉ nói:
> “Hãy chạy pilot.”

Nó phải biến thành test.

Ví dụ:

```text
Hypothesis:
A facility manager can identify actionable energy waste using the prototype.

Experiment:
PROTOTYPE_TEST

Scope:
1 dashboard, 1 site, 7 days

Metric:
Number of actionable recommendations accepted

Threshold:
Configured by methodology/project

Evidence:
usage log + interview + action commitment

Decision:
PROCEED / TEST_MORE / PIVOT
```

---

# 19. Energy Efficiency Vertical Pack

Universal startup methodology nên tách khỏi domain-specific content.

```text
COSA Startup Core Methodology
            │
            └── Energy Efficiency Vietnam Pack
```

## 19.1 Core Startup Pack

Bao gồm:
- stages;
- problem validation;
- customer discovery;
- hypothesis/evidence;
- solution validation;
- pricing;
- business model;
- GTM;
- finance readiness;
- team;
- scale;
- risk;
- decision.

## 19.2 EE Vietnam Pack

Bao gồm:
- industrial/building/transport context;
- energy baseline;
- energy savings;
- cost savings;
- ROI/payback;
- MRV;
- ESCO;
- EaaS;
- performance contracting;
- energy audit;
- BMS/EMS/HVAC/IoT context;
- energy regulation;
- certification;
- impact metrics;
- energy-specific pilot templates.

## 19.3 EE Evidence

Ví dụ:

```text
Founder estimate
Vendor lab result
Simulation
Site baseline
Short controlled test
Customer pilot
Verified pilot
Multi-site repeatability
Commercial repeatability
```

Cần thiết kế ladder mapping cẩn thận với EvidenceType hiện tại thay vì tạo parallel evidence engine.

---

# 20. Knowledge Integration

Sổ tay không nên xuất hiện chủ yếu dưới dạng “đọc chương”.

Knowledge phải là **just-in-time coaching**.

Ví dụ khi COSA hỏi “Ai là economic buyer?”:
- hiển thị giải thích ngắn;
- ví dụ;
- link source;
- template;
- case study phù hợp.

## 20.1 Knowledge metadata

Đề xuất:

```text
source
source_version
source_page
topic
stage
dimension
industry
jurisdiction
valid_from
last_verified
regulatory_sensitivity
```

## 20.2 Regulatory sensitivity

Nội dung policy/legal từ sổ tay có thể thay đổi.

Không được sử dụng như current legal truth nếu chưa verify.

Knowledge item pháp lý cần:
- version;
- effective date;
- source authority;
- last verified;
- stale flag.

---

# 21. Stage-Aware Capability Routing

COSA đã có StageServiceAssessment/StageAssignment và frontend stage workspace.

Methodology pack cần map capability theo stage.

Ví dụ:

```yaml
stage: S1_PROBLEM_VALIDATION

required:
  - customer_discovery
  - assumption_mapping
  - evidence_review

recommended:
  - market_research
  - legal_signal_scan

optional:
  - competitive_landscape

avoid:
  - investor_pitch_deck
  - large_scale_hiring
```

## 21.1 Execution mode

Capability có thể:
- MANUAL;
- AI_ASSISTED;
- AUTOMATED;
- EXPERT_REVIEW_REQUIRED.

High-risk legal/financial/regulatory outcomes phải hiện professional review requirement theo governance hiện có.

---

# 22. Co-founder Next Best Action

Codebase đã có `NextActionCandidate` và `NextActionRanking`.

Methodology phải tạo candidate từ:
- stage gap;
- assumption risk;
- missing evidence;
- experiment status;
- milestone;
- commercial urgency;
- runway;
- compliance risk.

## 22.1 Candidate examples

```text
Interview 3 decision makers
Run pricing test
Complete prototype test
Ask pilot customer for usage data
Resolve contract blocker
Measure baseline
Review runway
Create hiring scorecard
```

## 22.2 Ranking

R0:
- deterministic urgency/impact/effort.

R1:
- business rules.

R2:
- AI contextual rerank.

AI không được vượt qua hard blocker.

---

# 23. Co-founder State Snapshot

Mỗi project cần có một view tổng hợp, có thể là read model thay vì table mới.

```text
Project
Stage
Stage Goal
Validated
Supported
Testing
Challenged
Invalidated
Top Assumptions
Top Risks
Active Experiments
Strongest Evidence
Missing Evidence
Current Milestone
Next Best Actions
Founder Decisions
```

Ví dụ UX:

```text
Current Stage: S1 Problem Validation

Validated
✓ Segment: mid-size seafood processors

Supported
~ refrigeration energy waste

Testing
→ economic buyer willingness to pilot

Challenged
! "30% saving" claim

Top Risk
No verified baseline

Next Best Action
Interview 2 plant managers with budget authority
```

---

# 24. UX Principles for AI Co-founder

## 24.1 Chat + Workspace

Chat:
- conversational reasoning;
- questions;
- explanations;
- challenge;
- recommendation.

Workspace:
- structured state;
- evidence;
- scorecards;
- experiments;
- stage;
- decisions;
- tasks.

Không buộc user hiểu database concepts.

## 24.2 Show why

Mỗi recommendation nên có:

```text
Recommendation
Why
Evidence
Missing Evidence
Risk
Action
```

## 24.3 Confidence visible

Không dùng confidence giả chính xác.

Phân biệt:
- no evidence;
- weak;
- mixed;
- supported;
- strongly supported.

## 24.4 Progressive disclosure

Founder giai đoạn đầu không cần nhìn:
- term sheet;
- Series A data room;
- scale KPI.

UI nên stage-aware.

---

# 25. Artifact Generation

COSA có thể tạo artifact từ cùng structured state.

Ví dụ:

```text
Validated Problem
      ↓
Problem Statement
      ↓
Lean Canvas
      ↓
Pilot Brief
      ↓
Case Study
      ↓
Sales One-pager
      ↓
Investor Slide
```

Không nhập lại cùng dữ liệu ở nhiều nơi.

Artifacts phải có:
- source state;
- generated_at;
- version;
- founder approval nếu dùng externally.

---

# 26. Finance and Investor Readiness

Sổ tay Chương 5 cung cấp:
- funding ladder;
- funding instrument;
- investor readiness;
- data room;
- valuation;
- pitch deck;
- term sheet;
- reporting.

Methodology:
- không đưa fundraising lên quá sớm;
- funding recommendation phụ thuộc stage, evidence, use of funds;
- phân biệt R&D capital, working capital, project finance, growth equity.

COSA phải challenge:
> “Vì sao bạn cần VC ngay lúc này?”

và kiểm tra:
- milestone;
- use of funds;
- traction;
- business model;
- team;
- runway;
- data room;
- investor fit.

---

# 27. Team and Capability Development

Sổ tay Chương 6 phù hợp với Organization + Capability.

COSA không chỉ hỏi:
> “Bạn cần tuyển ai?”

Mà:
> “Milestone tiếp theo cần capability nào mà team hiện không có?”

Flow:

```text
Next Milestone
↓
Required Capability
↓
Current Coverage
↓
Gap
↓
Build / Hire / Contractor / Advisor / Partner / AI
```

Tôn trọng unified `WorkforceMember` model; không tách AI workforce và human workforce thành hai khái niệm song song.

---

# 28. Technology and IP

Chương 7 bổ sung:
- technology trends;
- sector applications;
- tech challenges;
- deployment;
- IP.

COSA phải tách:
- technical hypothesis;
- deployment hypothesis;
- defensibility;
- IP decision;
- certification;
- integration risk.

Không phải mọi moat đều là patent.

COSA có thể hỏi:
- dữ liệu độc quyền?
- integration know-how?
- certification?
- installed base?
- customer reference?
- proprietary algorithm?
- trade secret?
- patentable invention?

---

# 29. Market, GTM and Trust

Chương 8 đặc biệt quan trọng cho B2B HQNL.

Customer thường cần proof:
- đã triển khai ở đâu;
- tiết kiệm bao nhiêu;
- downtime;
- ROI;
- verifier;
- warranty;
- reference.

COSA phải biến technical feature thành customer outcome.

Ví dụ:

```text
Feature:
AI predictive control

Outcome:
reduce energy cost while retaining operating constraints
```

Nhưng outcome claim chỉ được dùng externally khi evidence policy cho phép.

---

# 30. Learning Loop

COSA đã có `Lesson`.

Sau mỗi:
- interview batch;
- experiment;
- pilot;
- lost sale;
- week review;
- stage gate;

COSA nên tạo candidate lesson:

```text
Observation
Evidence
Interpretation
Recommendation
Confidence
```

Founder approve lesson quan trọng.

Lesson có thể:
- cập nhật methodology locally;
- tạo next action;
- challenge assumption;
- inform strategy.

Không tự thay global methodology từ một startup đơn lẻ.

---

# 31. Audit and Traceability

Mỗi meaningful co-founder decision phải trace:

```text
Input
Claim
Assumption
Hypothesis
Experiment
Evidence
Review
Recommendation
Founder Decision
Action
Result
```

Không lưu private chain-of-thought.

Lưu:
- summary rationale;
- policy/rule;
- evidence references;
- structured result.

---

# 32. Current Codebase Mapping

| Requirement | Existing COSA owner | Action |
|---|---|---|
| Canonical company/project | Workspace + Project | Reuse |
| Startup stages | `core.strategy.project.Project` | Reuse; audit duplicate enum |
| Stage gate | `StageTransitionAudit` | Extend rules |
| Anti-premature scale | `PrematureScalingAlert` | Extend rules |
| Assumption | `core.validation.ValidationAssumption` | Reuse |
| Testable hypothesis | `ValidationHypothesis` | Reuse |
| Experiment | `ValidationExperiment` | Reuse |
| Evidence | `ValidationEvidence` | Reuse |
| Review | `ValidationReview` | Reuse |
| Decision | `ValidationDecision` | Reuse |
| Customer | `CustomerContact` | Reuse |
| Interview | `CustomerInterviewSession` | Reuse |
| Verbatim quote | `VerbatimQuote` | Reuse |
| Pain pattern | `PainPattern` | Reuse |
| Early adopter | `EarlyAdopterCandidate` | Reuse |
| Problem score | `ProblemSeverityScorecard` | Reuse |
| Methodology | `MethodologyPlan` | Extend |
| Milestone | `Milestone` | Reuse |
| Template | `WorkspaceTemplateVersion` | Extend/seed |
| Playbook link | `playbook_document_id` | Reuse |
| Next action | `NextActionCandidate/Ranking` | Extend generation rules |
| Learning | `Lesson` | Reuse |
| Stage UI | `project_stage_workspace_view.dart` | Extend |
| Agent routing | StageServiceAssessment/Assignment + workforce runtime | Reuse |
| Workflow | `app/integrations/workflows` | Extend only |
| Tools | core tool registry + workforce tools | Extend only |

---

# 33. Important Architecture Gaps / Risks to Resolve Before Coding

## 33.1 Duplicate stage vocabulary

Observed:
- `Project.project_stage`: S0–S6.
- `core.validation.enums.ProjectStage`: IDEA/VALIDATION/MVP/...

Action:
- consumer audit;
- designate one canonical business stage model;
- adapter/migration plan;
- no third vocabulary.

## 33.2 Overlapping hypothesis/evidence concepts

Observed:
- Strategy has `Hypothesis`, `Evidence`, `EvidenceItem`.
- Validation has `ValidationAssumption`, `ValidationHypothesis`, `ValidationEvidence`.

Không xóa ngay.

Cần consumer report:
- semantic purpose;
- ownership;
- API usage;
- FK usage;
- read models;
- backward compatibility.

Likely desired separation:
- Validation chain = startup experimentation truth.
- Strategy EvidenceItem = reusable strategic/context source.

Nhưng phải xác minh bằng code usage trước khi formalize.

## 33.3 Methodology configuration schema

`WorkspaceTemplateVersion.config_jsonb` có thể đủ cho v1.

Không tạo DB table QuestionGraph ngay nếu:
- config versioning;
- validation schema;
- indexing nhu cầu thấp.

Chỉ promotion thành table khi có requirement rõ:
- per-question analytics;
- collaborative editing;
- querying;
- cross-pack overrides;
- localization lifecycle.

## 33.4 Pilot semantics

Pilot có thể là:
- ValidationExperiment type mới;
- Project/MvpStage;
- Initiative;
- workflow run;
- linked artifact set.

Không tạo `Pilot` table trước khi xác định lifecycle/FK/reporting requirement.

---

# 34. Methodology Pack Structure

Recommended logical layout:

```text
methodologies/
  startup_core/
    manifest.yaml
    stages.yaml
    questions/
      s0_explore.yaml
      s1_problem.yaml
      s2_solution.yaml
      s3_business.yaml
      s4_gtm.yaml
      s5_growth.yaml
      s6_scale.yaml
    gates/
    experiments/
    artifacts/
    metrics/
    risks/
    capability_routing/
    knowledge_links/

  verticals/
    energy_efficiency_vn/
      manifest.yaml
      questions/
      metrics/
      pilot_patterns/
      regulations/
      knowledge_links/
      case_patterns/
```

Đây là logical structure; physical path phải follow owner được duyệt sau repository scan. Không tự tạo root `skills/` hay `workflows/` mới vì canonical ownership map đã đánh dấu các root scaffolds cũ là retirement candidates.

---

# 35. Example End-to-End Co-founder Flow

Founder:

> “Tôi muốn dùng AI để giảm điện cho nhà máy.”

### Step 1 — classify
COSA nhận:
- opportunity;
- chưa có customer specificity;
- chưa có evidence.

### Step 2 — stage
Project:
`S0_EXPLORE` hoặc `S1_PROBLEM_VALIDATION` tùy context.

### Step 3 — question
> “Loại nhà máy cụ thể nào bạn đã quan sát thấy vấn đề này?”

Founder:
> “Nhà máy thủy sản.”

### Step 4 — structure
Create/update:
- CUSTOMER assumption;
- PROBLEM assumption.

### Step 5 — question
> “Lần gần nhất bạn thấy một nhà máy thủy sản lãng phí điện là khi nào và điều gì xảy ra?”

Founder:
> “Hệ thống cấp đông chạy không tối ưu.”

### Step 6 — challenge
> “Bạn biết mức lãng phí từ đo đạc hay đang ước tính?”

Founder:
> “Ước tính khoảng 30%.”

### Step 7 — epistemic correction
Record:
- 30% = assumption;
- evidence = founder belief.

### Step 8 — risk
High importance × high uncertainty.

### Step 9 — experiment
COSA đề xuất:
- interview facility/energy manager;
- collect utility/process data;
- baseline analysis.

### Step 10 — evidence
Sau interview:
- quote;
- pain;
- current workaround;
- cost;
- buying signal.

### Step 11 — review
COSA:
> “Problem có dấu hiệu supported; claim 30% vẫn chưa được hỗ trợ.”

### Step 12 — next best action
> “Thu baseline của một site trước khi thiết kế full AI control.”

Đó là hành vi mong muốn của AI Co-founder.

---

# 36. Acceptance Criteria for Product Behavior

Một implementation được coi là đúng khi:

1. COSA không biến founder statement thành fact mặc định.
2. COSA biết current project stage.
3. COSA hỏi stage-appropriate questions.
4. COSA ưu tiên past/current behavior hơn hypothetical answer trong problem validation.
5. COSA phân biệt user/buyer/decision maker/influencer.
6. COSA tạo assumption/hypothesis có structured state.
7. COSA đề xuất experiment nhỏ nhất hữu ích.
8. COSA lưu contradictory evidence.
9. COSA có thể nói “chưa đủ bằng chứng”.
10. COSA không recommend scale/fundraising chỉ vì founder yêu cầu nếu gate/risk cho thấy chưa phù hợp.
11. Stage transition dựa trên deterministic criteria + evidence + explicit decision.
12. AI recommendation trace tới evidence và rule.
13. Founder có quyền override với rationale, nếu policy cho phép.
14. Existing Business Core không phụ thuộc model provider.
15. Không tạo duplicate architecture.
16. Knowledge sổ tay được cung cấp just-in-time.
17. Legal/regulatory knowledge có version/staleness treatment.
18. Energy-specific methodology tách khỏi universal startup methodology.
19. Next Best Action dùng engine hiện hữu.
20. UI không phụ thuộc parse free-form AI text để xác định status.

---

# 37. Implementation Phases

## Phase A — Architecture Audit

- stage vocabulary consumer scan;
- hypothesis/evidence concept map;
- validation API/service scan;
- strategy stage service scan;
- frontend controller/service scan;
- template seed mechanism;
- workflow integration;
- knowledge/vault integration.

Deliverable:
`COSA_STARTUP_METHODOLOGY_GAP_ANALYSIS.md`.

## Phase B — Startup Core Methodology v1

Scope:
- S0;
- S1;
- S2;
- question graph;
- validation chain;
- stage gates;
- next action;
- customer discovery UX.

Không triển khai toàn Chương 5–9 cùng lúc.

## Phase C — Business + GTM

- S3;
- S4;
- pricing;
- business model projection;
- ICP;
- sales;
- first customer cohort.

## Phase D — Growth + Scale

- S5;
- S6;
- readiness;
- operating metrics;
- scale risks;
- capability plan.

## Phase E — Energy Efficiency VN Pack

- energy-specific questions;
- pilot;
- baseline/MRV;
- policy knowledge;
- HQNL business models;
- impact metrics;
- AIS4EE case patterns.

---

# 38. Recommended First Build

Nếu chỉ chọn một vertical slice để chứng minh COSA là AI Co-founder:

```text
Founder conversation
        ↓
Structured Claim
        ↓
Problem Assumption
        ↓
Customer Discovery Question
        ↓
Interview Capture
        ↓
Verbatim + Pattern
        ↓
Problem Score
        ↓
Validation Review
        ↓
Founder Decision
        ↓
Next Best Action
```

Đây là slice tốt vì:
- trực tiếp thể hiện co-founder behavior;
- tận dụng nhiều model đã tồn tại;
- không phụ thuộc full finance/scale stack;
- dễ test với startup thật;
- giá trị khác biệt rõ so với chatbot.

---

# 39. Product Principle

COSA không nên hỏi:

> “Bạn muốn sử dụng công cụ nào?”

COSA nên nói:

> “Giả định rủi ro nhất của bạn hiện tại là X. Bằng chứng hiện tại chỉ ở mức Y. Việc có giá trị nhất tiếp theo là Z. Tôi có thể chuẩn bị interview guide / experiment / analysis cho bạn.”

Đó là định nghĩa vận hành của **AI Co-founder**.

---

# 40. Definition of Done for Methodology Integration

AIS4EE được coi là “đã tích hợp” khi nội dung của sổ tay không chỉ searchable trong Knowledge mà đã được chuyển thành:

- stage mapping;
- question logic;
- hypothesis taxonomy;
- evidence requirement;
- experiment pattern;
- gate rule;
- capability routing;
- artifact template;
- risk rule;
- metric definition;
- contextual coaching;
- source-linked knowledge;
- vertical extensions.

Mục tiêu cuối:

```text
Knowledge
   +
Structured Business State
   +
Deterministic Governance
   +
Evidence
   +
AI Reasoning
   +
Execution
=
COSA AI Co-founder
```

---

## Appendix A — Suggested Initial Question Families

### Problem
- context;
- last incident;
- frequency;
- severity;
- cost;
- root cause;
- current alternative;
- urgency.

### Customer
- user;
- buyer;
- decision maker;
- influencer;
- procurement;
- budget owner;
- early adopter.

### Solution
- desired outcome;
- adoption friction;
- workflow fit;
- technical feasibility;
- trust;
- switching cost.

### Business
- pricing;
- revenue;
- channel;
- cost;
- delivery;
- margin.

### GTM
- ICP;
- trigger;
- message;
- channel;
- sales cycle;
- objection;
- proof.

### Growth
- repeatability;
- retention;
- customer success;
- operational bottleneck;
- hiring.

### Scale
- unit economics;
- deployment repeatability;
- capital;
- governance;
- compliance;
- geographic/product expansion.

---

## Appendix B — Suggested Energy-Specific Question Families

### Energy baseline
- current consumption;
- energy intensity;
- load profile;
- operating condition;
- data availability.

### Saving hypothesis
- expected kWh saving;
- expected percentage;
- cost saving;
- payback;
- confidence basis.

### MRV
- baseline method;
- measurement period;
- confounding factors;
- verification responsibility.

### Pilot
- site;
- equipment;
- installation;
- downtime;
- success metric;
- financial value;
- customer acceptance.

### Business model
- CapEx;
- subscription;
- leasing;
- EaaS;
- shared saving;
- ESCO/performance contract.

### Regulation
- applicable duty;
- reporting;
- audit;
- certification;
- incentive;
- stale/current source status.

---

## Appendix C — Source References

### Sổ tay AIS4EE
**Tên:** *Sổ tay hướng dẫn khởi nghiệp sáng tạo về hiệu quả năng lượng tại Việt Nam: Hành trình từ ý tưởng đến thực tế*  
Các phần chính dùng cho tài liệu:
- Chương 4, tr. 55–105: sáu giai đoạn startup.
- Chương 5: tài chính và investor readiness.
- Chương 6: team và hạ tầng.
- Chương 7: technology và IP.
- Chương 8: market, customer acquisition và trust.
- Chương 9: scale readiness, risk và KPI.
- Chương 10: case study.

### COSA codebase
Các anchor đã đối chiếu:
- `CLAUDE.md`
- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`
- `backend/core/strategy/project.py`
- `backend/core/strategy/stage.py`
- `backend/core/strategy/evidence.py`
- `backend/core/strategy/methodology.py`
- `backend/core/strategy/templates.py`
- `backend/core/strategy/next_action.py`
- `backend/core/validation/models.py`
- `backend/core/validation/enums.py`
- `backend/core/validation/evidence_chain.py`
- `backend/core/validation/customer_discovery.py`
- `backend/core/finance/models.py`
- `backend/core/learning/models.py`
- `frontend/lib/modules/strategy/views/project_stage_workspace_view.dart`

---

**End of Draft v1.0**
