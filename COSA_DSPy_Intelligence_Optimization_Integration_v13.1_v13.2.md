# COSA — DSPy Intelligence Optimization Integration Specification

> **Baseline sản phẩm:** COSA **v13.1 / v13.2**  
> **Ngày phân tích:** 2026-08-15  
> **Mục đích:** Tài liệu kiến trúc + triển khai cho Claude Code  
> **Trạng thái:** Implementation-ready proposal  
> **Nguyên tắc version:** **KHÔNG tạo v14/v15 hoặc chuỗi version sản phẩm mới từ tài liệu này.** Chỉ triển khai bằng technical phases, feature flags và migration nội bộ trên baseline v13.1/v13.2.  
> **DSPy baseline được kiểm tra:** **DSPy 3.3.0** là release latest trên repository chính thức tại thời điểm 2026-08-15.  
> **Quan trọng:** Tài liệu này tuân thủ V13 Focused Company Cycle OS. **Không bật lại PESTEL, SWOT, TOWS, BSC, Strategic Canvas hoặc Portfolio Strategy.**

---

# 0. Executive Decision

DSPy **nên được tích hợp vào COSA**, nhưng không phải Agent Runtime và không phải một workflow engine mới.

Vai trò đề xuất:

> **DSPy = Intelligence Program + Evaluation + Optimization Layer**

DSPy chịu trách nhiệm cho các phần:

- khai báo những tác vụ AI có input/output rõ ràng;
- chuẩn hóa structured output;
- đánh giá chất lượng bằng metric;
- benchmark nhiều model/prompt/program;
- tối ưu instruction/few-shot bằng optimizer;
- lưu program artifact đã tối ưu;
- hỗ trợ offline learning/evaluation loop;
- cung cấp các cognitive component tái sử dụng cho AI Functions.

DSPy **không chịu trách nhiệm** cho:

- business truth;
- Company Cycle state;
- OKR/12WY state;
- task/work item state;
- agent session/runtime lifecycle;
- long-running orchestration;
- external automation;
- approval;
- policy;
- accounting ledger;
- credential ownership;
- realtime voice;
- sandbox execution;
- persistent business memory.

Kiến trúc trách nhiệm sau khi tích hợp:

```text
COSA FastAPI/PostgreSQL = Business Core + Source of Truth
DeepSeek Harness        = Agent Runtime
DSPy                    = Intelligence Program / Eval / Optimization
n8n                     = Automation Runtime
OpenSandbox             = Safe Execution Runtime
LiveKit                 = Realtime Voice Transport
MCP                     = Tool Contract / Integration Boundary
Claude Code CLI         = Tech Coding Executor
COSA Policy/Approval    = Governance Authority
```

Nguyên tắc cốt lõi:

> **COSA owns the company. Harness runs agents. DSPy improves bounded AI programs. OpenSandbox executes untrusted code. n8n automates external systems. Humans retain authority over consequential actions.**

---

# 1. Baseline COSA hiện tại — phải tuân thủ tuyệt đối

Tài liệu này căn cứ hai baseline gần nhất:

1. `mCOSA_V13_Focused_Company_Cycle_OS_Claude_Code_Implementation.md`
2. `COSA_Agentic_Architecture_Adjustment_v13.1_v13.2.md`

## 1.1 V13 Core đang bật

User-facing MVP hiện tại tập trung vào:

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
16. Next Actions — simple
17. Artifacts / Approvals
```

Primary operating loop:

```text
FOUNDER
   ↓
COMPANY CYCLE
   ↓
OKRs
   ↓
12 WEEK YEAR
   ↓
WEEKLY MISSION
   ↓
WORK / AI FUNCTIONS / AUTOMATION
   ↓
RESULTS
   ↓
WEEKLY REVIEW
   ↓
LESSONS
   ↓
NEXT WEEK
   ↓
WEEK 13
   ↓
REFLECT • LEARN • CELEBRATE • RESET
```

## 1.2 Các module đang tạm disable/hidden

Các module sau **không được DSPy integration bật lại**:

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

Rule bắt buộc:

```text
KEEP CODE
+
DISABLE FEATURE
+
HIDE UI
+
EXCLUDE FROM AI TOOL REGISTRY
+
DO NOT CALL FROM DSPy
```

DSPy program registry **không được chứa**:

```text
pestel.*
swot.*
tows.*
bsc.*
portfolio_strategy.*
```

trong production default.

---

# 2. DSPy là gì và vì sao phù hợp COSA

DSPy là Python framework theo tư duy:

> **Program, don't prompt.**

Thay vì quản lý hàng loạt prompt string thủ công, DSPy cho phép định nghĩa:

```text
Task Signature
    ↓
Module
    ↓
Structured Prediction
    ↓
Metric
    ↓
Evaluation
    ↓
Optimizer
    ↓
Compiled Program Artifact
```

Các primitive phù hợp COSA:

```text
Signature
Predict
ChainOfThought
ReAct
Tool
Module
Example
Evaluate
GEPA
MIPROv2
BootstrapFewShot
save/load
asyncify
streamify
```

Tuy nhiên COSA **không nên dùng tất cả ngay từ đầu**.

### Production recommendation cho COSA

Ưu tiên:

```text
Signature
Predict
ChainOfThought
Module
Evaluate
GEPA
save/load
asyncify
```

Thử nghiệm sau:

```text
ReActV2
Flex
RLM
fine-tuning optimizer
```

Lý do:

- COSA đã có DeepSeek Harness làm Agent Runtime;
- COSA đã có OpenSandbox làm execution isolation;
- COSA không cần thêm một agent loop thứ hai trong production;
- `ReActV2` và `Flex` trong DSPy 3.3.0 còn được upstream đánh dấu experimental.

---

# 3. Quyết định kiến trúc quan trọng nhất: DSPy KHÔNG thay DeepSeek Harness

Sai:

```text
Flutter
  ↓
DSPy ReAct Agent
  ↓
all tools
  ↓
COSA
```

Sai vì sẽ tạo hai runtime cạnh tranh:

```text
DeepSeek Harness
vs
DSPy ReAct
```

Đúng:

```text
Flutter
  ↓
FastAPI / COSA Control Plane
  ↓
Agent Gateway
  ↓
DeepSeek Harness
  ↓
Agent / Capability
  ↓
DSPy Cognitive Program
  ↓
Structured Result
  ↓
Harness continues planning/execution
```

DSPy được gọi cho các reasoning unit có boundary rõ.

Ví dụ:

```text
Sales Agent
  ↓
Task: qualify lead
  ↓
DSPy LeadQualificationProgram
  ↓
{
  fit_score,
  need_score,
  urgency_score,
  evidence,
  next_action
}
  ↓
Sales Agent
  ↓
Policy
  ↓
Draft follow-up
  ↓
Approval
  ↓
n8n
```

DSPy không sở hữu:

- session;
- task graph;
- retry lifecycle cấp agent;
- approval state;
- external action.

---

# 4. Kiến trúc đích

```text
┌───────────────────────────────────────────────────────────┐
│ EXPERIENCE                                                │
│ Flutter/GetX • Desktop • Mobile • Chat • LiveKit Voice   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│ COSA FASTAPI CORE                                         │
│ Cycle • OKR • 12WY • Work • Review • Learning            │
│ Legal • Marketing • Sales • Tech • Finance               │
│ Policy • Approval • Audit • Artifact • Memory             │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────┐
│ COSA CONTROL PLANE / AGENT GATEWAY                        │
│ Goal/Intent • Context Resolver • Router • Policy          │
│ AgentRuntime abstraction • Model Policy • Trace           │
└──────────────┬────────────────────────────┬───────────────┘
               │                            │
               ▼                            ▼
┌──────────────────────────┐    ┌───────────────────────────┐
│ DeepSeek Harness         │    │ DSPy Intelligence Layer   │
│ Agent Runtime            │───▶│ Program Registry          │
│ Planning / Tool Loop     │    │ Signatures / Modules      │
│ Session / Delegation     │◀───│ Eval / Metrics            │
└──────────────┬───────────┘    │ Compiled Artifacts        │
               │                └─────────────┬─────────────┘
               │                              │
               ▼                              │
┌─────────────────────────────────────────────┼─────────────┐
│ TOOL / EXECUTION / AUTOMATION               │             │
│ MCP Gateway                                 │             │
│ OpenSandbox                                 │             │
│ n8n                                         │             │
│ Internal APIs                               │             │
└───────────────────────┬─────────────────────┘             │
                        │                                   │
                        ▼                                   │
┌───────────────────────────────────────────────────────────┐
│ DATA / MEMORY / EVAL STORE                                │
│ PostgreSQL + pgvector                                     │
│ Business Data • Agent Runs • Feedback • Eval Dataset      │
│ Program Versions • Optimization Runs • Deployments        │
└───────────────────────────────────────────────────────────┘
```

---

# 5. Vị trí code đề xuất

Không rải `import dspy` vào business domain.

Tạo boundary riêng:

```text
backend/
└── app/
    ├── ai/
    │   ├── programs/
    │   │   ├── base.py
    │   │   ├── registry.py
    │   │   ├── schemas.py
    │   │   ├── loader.py
    │   │   ├── runtime.py
    │   │   ├── artifacts.py
    │   │   │
    │   │   ├── cycle/
    │   │   ├── okr/
    │   │   ├── twelve_week/
    │   │   ├── weekly/
    │   │   ├── ceo_brief/
    │   │   ├── next_actions/
    │   │   ├── legal/
    │   │   ├── marketing/
    │   │   ├── sales/
    │   │   ├── tech/
    │   │   ├── finance/
    │   │   └── learning/
    │   │
    │   ├── evaluation/
    │   │   ├── datasets.py
    │   │   ├── metrics.py
    │   │   ├── evaluators.py
    │   │   ├── judges.py
    │   │   ├── outcomes.py
    │   │   └── regression.py
    │   │
    │   ├── optimization/
    │   │   ├── service.py
    │   │   ├── gepa.py
    │   │   ├── bootstrap.py
    │   │   ├── artifact_store.py
    │   │   └── promotion.py
    │   │
    │   └── model_policy/
    │       ├── resolver.py
    │       ├── dspy_lm_factory.py
    │       └── usage.py
    │
    └── agents/
        └── runtime/
            └── ...
```

Business modules gọi abstraction:

```text
AIProgramService.run(program_key, input)
```

Không gọi trực tiếp:

```python
dspy.ChainOfThought(...)
```

trong `sales/service.py`, `finance/service.py`, `okr/service.py`, v.v.

---

# 6. AIProgram abstraction

Tạo contract trung lập:

```python
class AIProgramRequest(BaseModel):
    company_id: UUID
    user_id: UUID
    program_key: str
    program_version: str | None = None

    input: dict
    context_refs: list[str] = []

    model_policy: str | None = None
    correlation_id: UUID | None = None
    parent_agent_run_id: UUID | None = None


class AIProgramResult(BaseModel):
    program_key: str
    program_version: str

    status: Literal[
        "completed",
        "failed",
        "validation_failed"
    ]

    output: dict | None
    user_visible_rationale: str | None

    model_profile: str
    latency_ms: int | None
    usage: dict

    metric_snapshot: dict | None = None
    artifact_hash: str | None = None
```

Interface:

```python
class AIProgramRuntime(ABC):
    @abstractmethod
    async def run(
        self,
        request: AIProgramRequest
    ) -> AIProgramResult:
        ...
```

Implementation ban đầu:

```text
DSPyProgramRuntime
MockProgramRuntime
LegacyPromptProgramRuntime
```

Cho phép A/B test:

```text
legacy prompt
vs
DSPy program
```

mà không sửa business service.

---

# 7. DSPy Program Registry

Không hard-code program bằng tên class ở router.

Ví dụ registry:

```yaml
key: sales.lead_qualification
enabled: true
engine: dspy
program_class: LeadQualificationProgram
program_artifact: sales_lead_qualification_v3.json

model_policy: sales_reasoning_fast
timeout_seconds: 30

input_schema: LeadQualificationInput
output_schema: LeadQualificationOutput

evaluation_profile: sales_lead_qualification_v1

allowed_context:
  - lead
  - company
  - crm_history

forbidden_context:
  - unrelated_company_data
  - raw_credentials

production_status: active
```

Feature flags có thể disable toàn bộ DSPy:

```text
COSA_DSPY_ENABLED=false
```

hoặc theo program:

```text
COSA_DSPY_SALES_LEAD_QUALIFICATION_ENABLED=true
```

Quy ước đặt tên: mọi flag boolean đều có hậu tố `_ENABLED` (khớp mục 51.1 và mục 71) — tránh lẫn với biến giá trị như `COSA_DSPY_VERSION`.

Fallback:

```text
DSPy unavailable
  ↓
legacy bounded prompt
  ↓
same output schema
```

Không để DSPy failure làm hỏng COSA Core.

---

# 8. Model routing — DSPy không được bypass COSA Model Policy

COSA hiện có model/provider routing riêng.

DSPy không được tự quyết:

```text
model = "openai/..."
```

trong business code.

Tạo:

```text
DSPyLMFactory
```

nhận:

```text
COSA model_policy
```

và build model config phù hợp.

Flow:

```text
Program
  ↓
model_policy = sales_reasoning_fast
  ↓
COSA ModelPolicyResolver
  ↓
Provider Profile
  ↓
DSPyLMFactory
  ↓
dspy.LM(...)
```

Ví dụ model policy:

```yaml
sales_reasoning_fast:
  provider_priority:
    - apiai_vn
    - deepseek_direct
    - openrouter
  model_class: fast_reasoning
  max_cost_per_run: 0.05
  timeout: 25
  data_policy: standard_business
```

DSPy chỉ nhận provider/model **sau khi COSA policy đã quyết định**.

Không cho DSPy optimizer tự đổi sang provider có policy khác mà không qua COSA.

---

# 9. DSPy release policy

Tại thời điểm lập tài liệu:

```text
DSPy latest release: 3.3.0
Release date: 2026-08-03
```

Khuyến nghị:

```text
dspy==3.3.0
```

Không dùng:

```text
dspy>=3.3
```

trong production.

Rule:

```text
PIN EXACT VERSION
+
RUN CONTRACT TESTS
+
MANUAL UPGRADE
```

Lý do:

- DSPy phát triển nhanh;
- 3.3.0 có thay đổi LM boundary;
- ReActV2 và Flex còn experimental;
- optimization artifacts phải reproducible.

---

# 10. Program design principle

Mỗi DSPy program phải:

1. làm đúng **một cognitive job**;
2. có input/output schema rõ;
3. có metric;
4. có eval dataset;
5. không trực tiếp mutate business state;
6. không tự gửi external action;
7. không chứa secret;
8. không đọc database tùy ý;
9. không lưu hidden chain-of-thought;
10. có fallback.

Sai:

```text
FounderAgentProgram
- hiểu mọi thứ
- lập kế hoạch
- gọi tool
- làm sales
- làm finance
- gửi email
- update DB
- tự đánh giá
```

Đúng:

```text
CyclePlanDraftProgram
LeadQualificationProgram
CampaignBriefProgram
FinanceInsightProgram
WeeklyReviewSynthesisProgram
NextActionRankerProgram
```

---

# 11. Program cho Company Cycle

## 11.1 `cycle.intent_extractor`

Mục tiêu:

> Chuyển yêu cầu tự nhiên của founder thành Cycle Planning Intent.

Input:

```yaml
founder_request:
company_context:
available_hours:
budget:
target_date:
existing_cycle_context:
```

Output:

```yaml
cycle_intent:
  outcome:
  success_signals: []
  constraints: []
  risks: []
  unknowns: []
  suggested_time_horizon:
  confidence:
```

Metric:

```text
schema_validity
constraint_recall
outcome_clarity
unsupported_assumption_penalty
founder_edit_distance
```

Không tạo PESTEL/SWOT/TOWS.

---

## 11.2 `cycle.plan_draft`

Mục tiêu:

> Tạo draft Cycle từ intent đã chuẩn hóa.

Output:

```yaml
cycle_title:
cycle_outcome:
objectives: []
risks: []
assumptions: []
recommended_focus:
founder_attention_notes:
```

Rule:

- chỉ tạo draft;
- founder review trước activate;
- không tự tạo business commitment.

DSPy phù hợp vì đây là high-value structured reasoning task.

---

# 12. Program cho OKR

## 12.1 `okr.draft`

Input:

```text
Cycle outcome
constraints
current company state
available capacity
```

Output:

```yaml
objectives:
  - title:
    why:
    key_results:
      - metric:
        baseline:
        target:
        unit:
        deadline:
        evidence_source:
```

Metric:

```text
measurability
outcome_alignment
baseline_target_validity
duplicate_kr_penalty
activity_as_kr_penalty
capacity_realism
founder_acceptance
```

Hard validators vẫn do COSA code xử lý:

```text
1–3 objectives
1–3 KRs per objective
required fields
valid date
valid numeric range
```

DSPy không thay deterministic validation.

---

# 13. Program cho 12 Week Year

## 13.1 `twelve_week.plan_draft`

Input:

```text
approved OKR
capacity
budget
known dependencies
existing work
```

Output:

```yaml
weekly_outcomes:
  week_1:
  ...
  week_12:

milestones: []
dependencies: []
critical_path: []
```

Metric:

```text
okr_traceability
weekly_feasibility
dependency_consistency
capacity_fit
milestone_quality
overplanning_penalty
```

Không lập PESTEL/SWOT/TOWS.

---

# 14. Weekly Mission

## 14.1 `weekly.mission_draft`

Input:

```text
current week
KR status
unfinished work
new blockers
capacity
previous lesson
```

Output:

```yaml
mission:
success_criteria: []
top_work_items: []
defer_candidates: []
risks: []
```

Metric:

```text
KR relevance
focus
workload feasibility
dependency validity
carryover handling
```

V13 founder attention là scarce resource.

Do đó metric nên phạt:

```text
too_many_tasks
too_many_priorities
non-KR work
low-impact busywork
```

---

# 15. Weekly Review + Learning

## 15.1 `weekly.review_synthesis`

Input:

```text
planned mission
work results
artifacts
KR deltas
finance signals
sales signals
marketing signals
founder notes
```

Output:

```yaml
what_completed: []
what_missed: []
outcomes: []
blockers: []
lessons: []
next_week_recommendations: []
confidence:
```

Metric:

```text
evidence_grounding
outcome_vs_activity_separation
lesson_quality
no_hallucinated_result
actionability
founder_acceptance
```

## 15.2 `learning.lesson_extractor`

Output:

```yaml
lesson:
  statement:
  evidence_refs: []
  scope:
  confidence:
  reusable:
  expiration_or_review_date:
```

Memory Policy quyết định có lưu hay không.

DSPy không tự ghi long-term memory.

---

# 16. Week 13

## 16.1 `week13.cycle_retrospective`

Input:

```text
cycle target
OKR final status
12WY execution
weekly reviews
sales/revenue
finance
marketing
tech artifacts
legal/compliance
founder notes
```

Output:

```yaml
wins: []
misses: []
root_causes: []
lessons: []
carry_forward: []
stop_doing: []
celebration_summary:
next_cycle_questions: []
```

Metric:

```text
evidence_grounding
root_cause_quality
business_outcome_focus
learning_quality
no_false_causality
```

Không tự tạo next Cycle active.

Chỉ tạo:

```text
next_cycle_questions
+
draft recommendations
```

---

# 17. CEO Brief

Đây là một trong các use case DSPy phù hợp nhất.

## `ceo.brief`

Input:

```text
current Cycle
OKR/KR
Weekly Mission
Sales
Finance
Marketing
Legal
Tech
Approvals
Exceptions
```

Output:

```yaml
headline:
wins: []
risks: []
exceptions: []
decisions_required: []
today_top_3: []
watch_next: []
```

Metric:

```text
decision_relevance
critical_issue_recall
noise_penalty
accuracy
evidence_grounding
brevity
founder_attention_saved
```

Metric cuối rất quan trọng:

> CEO Brief tốt không phải brief dài nhất; là brief giúp founder quyết định nhanh nhất.

---

# 18. Next Actions — simple

## `next_actions.rank`

Input:

```text
open WorkItems
blocked WorkItems
KR gaps
sales opportunities
finance exceptions
pending approvals
deadlines
```

Output:

```yaml
ranked_actions:
  - action_id:
    score:
    rationale:
    urgency:
    business_impact:
    dependency:
```

Không để model tự quyết score hoàn toàn.

Khuyến nghị hybrid:

```text
deterministic score
+
DSPy explanation / tie-break / contextual adjustment
```

Ví dụ:

```text
base_score =
  impact
  + urgency
  + deadline
  + KR relevance
  + blocker release

DSPy:
  contextual_rationale
  risk notes
  tie breaker
```

---

# 19. Sales AI Function — ưu tiên POC cao nhất

DSPy đặc biệt phù hợp Sales vì output có thể liên kết tới business outcome thật.

## 19.1 `sales.lead_qualification`

Input:

```yaml
lead:
company:
interaction_history:
product:
icp:
```

Output:

```yaml
fit_score:
need_score:
timing_score:
authority_signal:
budget_signal:
confidence:
evidence: []
disqualifiers: []
recommended_stage:
recommended_next_action:
```

Metric:

```text
human_sales_review
future_stage_progression
meeting_booked
qualified_opportunity
false_positive_penalty
evidence_grounding
```

Không train chỉ theo `closed_won` vì sample ít và delayed.

---

## 19.2 `sales.followup_strategy`

Output:

```yaml
objective:
message_angle:
objection_to_address:
cta:
channel:
timing:
draft:
```

External send vẫn:

```text
DSPy
  ↓
Draft
  ↓
COSA Policy
  ↓
Approval
  ↓
n8n
  ↓
Email / CRM / channel
```

---

## 19.3 `sales.pipeline_analysis`

Output:

```yaml
pipeline_health:
risks: []
stalled_deals: []
high_priority_opportunities: []
forecast_notes: []
recommended_actions: []
```

Không tự ghi CRM stage nếu chưa policy.

---

# 20. Marketing AI Function

## 20.1 `marketing.campaign_brief`

Input:

```text
Cycle KR
product
audience
budget
channel constraints
previous campaign results
```

Output:

```yaml
campaign_goal:
audience:
message:
channels: []
experiments: []
conversion_event:
budget_notes:
measurement_plan:
```

Metric:

```text
KR alignment
audience specificity
measurement quality
budget consistency
founder approval
campaign outcome
```

---

## 20.2 `marketing.content_brief`

DSPy phù hợp với:

- intent classification;
- content brief;
- message variation;
- CTA selection;
- content QA.

Không nên tối ưu chỉ theo:

```text
likes
```

Nên ưu tiên:

```text
qualified leads
CTR
conversion
sales contribution
cost
```

---

## 20.3 Research

Marketing research có thể dùng:

```text
DeepSeek Harness
  ↓
Research capability
  ↓
MCP / Browser
  ↓
OpenSandbox
  ↓
structured evidence
  ↓
DSPy Synthesis Program
```

DSPy không tự browser production ở phase đầu.

---

# 21. Finance AI Function

Finance phải tách:

```text
Deterministic Finance / Accounting
vs
AI Insight
```

## 21.1 DSPy được dùng cho

```text
finance.status_explanation
finance.exception_triage
finance.cashflow_insight
finance.budget_variance_explanation
finance.period_close_assistant
finance.document_classification_suggestion
finance.accountant_review_summary
```

## 21.2 DSPy KHÔNG dùng làm source of truth cho

```text
ledger posting
accounting book calculation
period lock
statutory statement arithmetic
tax determination
money transfer
final accounting classification
```

Mọi số liệu:

```text
PostgreSQL / deterministic Finance Engine
  ↓
DSPy
  ↓
Explain / summarize / recommend
```

Không:

```text
raw prompt
  ↓
LLM invents totals
```

---

# 22. Legal AI Function

Legal là domain cần metric và governance chặt.

DSPy phù hợp:

```text
legal.issue_classification
legal.contract_clause_extraction
legal.risk_summary
legal.checklist_draft
legal.expert_escalation_package
```

Không cho optimizer học theo:

```text
user accepted = legally correct
```

Evaluation cần nhiều tầng:

```text
schema validation
+
citation/evidence validation
+
rule-based safety checks
+
expert-reviewed test cases
+
optional LLM judge
```

Final legal determination vẫn Human/Professional authority.

---

# 23. Tech AI Function

Claude Code CLI vẫn là coding executor.

DSPy không thay Claude Code.

DSPy phù hợp cho:

```text
tech.work_item_refinement
tech.requirement_extraction
tech.bug_triage
tech.test_plan_draft
tech.release_summary
tech.artifact_quality_summary
```

Flow:

```text
Tech WorkItem
  ↓
DSPy Spec Refiner
  ↓
Structured coding task
  ↓
Claude Code CLI
  ↓
OpenSandbox / Git worktree
  ↓
Tests
  ↓
Artifacts
  ↓
DSPy Result Reviewer optional
  ↓
Human approval
```

Không dùng DSPy Flex để generate production implementation trong phase đầu.

---

# 24. Evaluation là giá trị lớn nhất của DSPy đối với COSA

COSA không nên định nghĩa "AI tốt" bằng cảm giác.

Mỗi program cần:

```text
eval dataset
+
metric
+
baseline score
+
candidate score
+
business outcome
```

Ba loại metric:

## A. Deterministic Metric

Ví dụ:

```text
schema valid
exact field
numeric consistency
citation exists
no forbidden action
```

## B. Semantic / Judge Metric

Ví dụ:

```text
clarity
usefulness
business relevance
risk awareness
```

## C. Outcome Metric

Ví dụ:

```text
founder accepted
edit distance
lead advanced stage
reply received
meeting booked
campaign converted
KR moved
```

Không để LLM-as-a-judge là metric duy nhất.

---

# 25. Evaluation score mẫu

Ví dụ `sales.lead_qualification`:

```text
quality_score =
    0.25 × evidence_grounding
  + 0.20 × human_review
  + 0.15 × stage_prediction_quality
  + 0.15 × next_action_quality
  + 0.15 × schema_correctness
  + 0.10 × calibration
```

Ví dụ `ceo.brief`:

```text
quality_score =
    0.25 × critical_issue_recall
  + 0.20 × decision_relevance
  + 0.20 × accuracy
  + 0.15 × evidence_grounding
  + 0.10 × brevity
  + 0.10 × founder_acceptance
```

Có hard gate:

```text
if hallucinated_finance_number:
    FAIL

if missing_critical_approval:
    FAIL

if cross-company data:
    FAIL
```

---

# 26. Feedback Loop

Không gọi đây là "AI tự học" nếu chưa có kiểm soát.

Đúng hơn:

> **Controlled Offline Optimization Loop**

```text
Production Runs
  ↓
Founder edits / accepts / rejects
  ↓
Business outcomes
  ↓
Curated Eval Dataset
  ↓
Offline Evaluation
  ↓
Optimizer
  ↓
Candidate Program
  ↓
Regression Test
  ↓
Human Promotion
  ↓
Production
```

Không:

```text
one bad answer
  ↓
model edits own prompt
  ↓
production immediately changes
```

---

# 27. Feedback events cần thu thập

Ví dụ:

```yaml
ai_feedback:
  run_id:
  program_key:
  program_version_id:

  feedback_type:
    - accepted
    - edited
    - rejected
    - regenerated
    - outcome_positive
    - outcome_negative
    - expert_corrected

  original_output:
  edited_output:
  reason_code:
  note:

  business_entity_type:
  business_entity_id:

  created_by:
  created_at:
```

Không lưu secret.

Không lưu hidden reasoning.

---

# 28. Datasets

Mỗi dataset có:

```yaml
dataset:
  key:
  version:
  program_key:
  status:
  source:
  created_at:
  schema_version:
  case_count:
```

Case:

```yaml
eval_case:
  id:
  dataset_key:
  input:
  expected:
  reference:
  rubric:
  tags:
  source_run_id:
  human_reviewed:
```

Tags:

```text
happy_path
edge_case
missing_data
contradiction
low_confidence
high_risk
vietnamese
finance
sales
legal
```

Dataset production phải immutable theo version.

---

# 29. Optimizer strategy

DSPy docs khuyến nghị thường bắt đầu prompt-only trước fine-tuning.

COSA nên theo thứ tự:

```text
1. Baseline manual / zero-shot
2. LabeledFewShot / BootstrapFewShot
3. GEPA
4. MIPROv2 nếu phù hợp
5. Fine-tune chỉ khi prompt optimization plateau
```

## 29.1 GEPA

GEPA phù hợp khi:

- metric có textual feedback;
- instruction quality là bottleneck;
- muốn optimize bounded reasoning program.

Use cases tốt:

```text
CEO Brief
Lead Qualification
Weekly Review
Cycle Plan Draft
Finance Exception Explanation
Legal Risk Summary
```

## 29.2 Không chạy GEPA realtime

Sai:

```text
User asks
  ↓
GEPA compile
  ↓
answer
```

Đúng:

```text
AI Lab
  ↓
GEPA compile offline
  ↓
candidate artifact
  ↓
eval
  ↓
promote
```

DSPy docs lưu ý compile có thể đắt; phải:

```text
compile once
save
reload many times
```

---

# 30. Program artifact

Lưu compiled artifact theo immutable version.

Ví dụ:

```text
artifacts/
  dspy/
    sales.lead_qualification/
      1.0.0/
        program.json
        manifest.json
        metrics.json
        sha256.txt
```

Manifest:

```yaml
program_key:
program_version:
dspy_version:
created_at:
optimizer:
optimizer_config_hash:
train_dataset:
validation_dataset:
model_policy:
baseline_score:
candidate_score:
artifact_hash:
approved_by:
```

Không overwrite artifact production.

---

# 31. Database schema đề xuất

## `ai_programs`

```text
id
program_key
domain
description
enabled
default_version
evaluation_profile
created_at
updated_at
```

## `ai_program_versions`

```text
id
program_id
version
engine
artifact_location
artifact_hash
dspy_version
status
model_policy
schema_version
created_at
promoted_at
promoted_by
```

Status:

```text
DRAFT
EVALUATING
SHADOW
CANDIDATE
CANARY
PRODUCTION
RETIRED
FAILED
```

`SHADOW` = chạy song song sau lưng legacy path (mục 55 Shadow Mode), chưa từng hiển thị cho user, dùng để tích lũy dataset trước khi vào `EVALUATING`/`CANDIDATE`.

## `ai_eval_datasets`

```text
id
dataset_key
version
program_key
status
source
schema_version
case_count
created_at
```

`source` khớp với field `source` đã định nghĩa ở mục 28 (ví dụ: `shadow_mode`, `production_feedback`, `manual_curated`, `expert_authored`) — bắt buộc để truy vết provenance theo yêu cầu governance ở mục 44.3/45.

## `ai_eval_cases`

```text
id
dataset_id
input_json
expected_json
reference_json
rubric_json
tags
source_run_id
human_reviewed
created_at
```

`reference_json` khớp với field `reference` đã định nghĩa ở mục 28 — lưu ground-truth/evidence tham chiếu dùng cho metric `evidence_grounding` (mục 15.1, 17, 19.1) và cho judge metric, tách biệt với `expected_json` (kết quả mong đợi chính xác dạng structured).

## `ai_eval_runs`

```text
id
program_version_id
dataset_id
model_profile
status
started_at
completed_at
aggregate_score
cost
metadata
```

## `ai_metric_results`

```text
id
eval_run_id
case_id
metric_key
score
feedback
hard_fail
created_at
```

## `ai_optimizer_runs`

```text
id
program_key
base_program_version_id
optimizer
optimizer_config
train_dataset_id
validation_dataset_id
status
started_at
completed_at
cost
best_score
candidate_artifact_hash
```

## `ai_feedback`

như mục 27.

## `ai_program_deployments`

```text
id
program_key
program_version_id
environment
rollout_percent
status
started_at
ended_at
approved_by
```

Quy ước version reference: mọi bảng tham chiếu tới một `ai_program_versions` cụ thể (`ai_eval_runs`, `ai_optimizer_runs`, `ai_program_deployments`, `ai_program_runs` ở mục 32) đều dùng FK `*_id` trỏ về `ai_program_versions.id`, không lưu version dạng chuỗi tự do — tránh lệch dữ liệu (typo, version bị retire nhưng string cũ vẫn "tồn tại") và cho phép JOIN lấy `artifact_hash`/`dspy_version`/`model_policy` trực tiếp. `program_key` vẫn được denormalize thêm ở các bảng cần lọc/group nhanh theo program mà không phải JOIN.

---

# 32. Liên kết với existing `agent_runs`

Không tạo duplication.

```text
agent_runs
   ↓ parent
ai_program_runs
```

Đề xuất:

```text
ai_program_runs:
  id
  parent_agent_run_id
  correlation_id
  program_key
  program_version_id
  model_profile
  input_snapshot_ref
  output_snapshot_ref
  status
  latency_ms
  usage_json
  created_at
```

Không persist hidden chain-of-thought.

---

# 33. Observability

Mỗi DSPy program run phải có:

```text
trace_id
correlation_id
agent_run_id
program_key
program_version
model_profile
latency
token usage
cost
validation status
```

Production UI không hiển thị raw prompt optimization internals.

AI Lab có thể hiển thị:

```text
baseline score
candidate score
dataset
optimizer
cost
latency
regressions
promotion status
```

---

# 34. AI Lab UI — optional nhưng rất đáng làm

Không đưa vào founder main UX ngay.

Developer/Admin page:

```text
AI Lab
├── Programs
├── Versions
├── Datasets
├── Evaluations
├── Optimizer Runs
├── Model Benchmarks
└── Deployments
```

Program detail:

```text
sales.lead_qualification

Production: 1.3.0
DSPy: 3.3.0

Quality: 0.89
Cost/run: ...
P95 latency: ...

Candidate:
1.4.0
Quality: 0.92

[Compare]
[Run Eval]
[Promote Canary]
[Rollback]
```

Không để end user tự promote model/program nếu không có admin permission.

---

# 35. Model benchmarking

DSPy tạo cơ hội benchmark program cùng một dataset trên nhiều model.

Ví dụ:

```text
sales.lead_qualification

Model A:
quality 0.91
cost 1.0x
latency 1.2x

Model B:
quality 0.89
cost 0.3x
latency 0.8x

Model C:
quality 0.83
cost 0.1x
latency 0.5x
```

COSA Model Router có thể quyết định theo policy:

```text
quality floor
+
cost ceiling
+
latency ceiling
+
data residency
```

Không để DSPy tự thay model production.

---

# 36. MCP

DSPy hỗ trợ MCP tools, nhưng COSA không cần dùng trực tiếp ở phase đầu.

COSA đã có:

```text
COSA MCP Gateway
```

Rule:

```text
DSPy bounded program
  → no write tools by default
```

Nếu cần tool:

```text
DSPy
  ↓
COSA Tool Adapter
  ↓
COSA MCP Gateway
  ↓
Policy
  ↓
Read Tool
```

Không cho:

```text
DSPy
  ↓
arbitrary external MCP server
```

vượt khỏi registry COSA.

---

# 37. ReAct / ReActV2 policy

DSPy 3.3.0 có ReActV2 native tool calling nhưng vẫn experimental.

COSA hiện đã dùng DeepSeek Harness cho agent loop.

Do đó:

```text
COSA_DSPY_REACT_V2_ENABLED=false
```

Default production.

Chỉ experiment:

```text
read-only
isolated
no business write
no external action
fixed tool allowlist
```

Use case nghiên cứu:

```text
Research QA
Document retrieval
Read-only support assistant
```

Không dùng ReActV2 thay Chief of Staff runtime.

---

# 38. Flex policy

DSPy 3.3.0 giới thiệu experimental `Flex`, cho phép optimizer thay đổi cả program structure/code.

Đây là tính năng mạnh nhưng chưa phù hợp production COSA hiện tại.

Default:

```text
COSA_DSPY_FLEX_ENABLED=false
```

Lý do:

- optimizer có thể sinh implementation mới;
- tăng complexity;
- khó governance;
- COSA đã có OpenSandbox nhưng chưa cần mở thêm dynamic code surface;
- chưa cần thiết để chứng minh ROI của DSPy.

Nếu thử nghiệm:

```text
offline AI Lab only
no customer data
no credential
OpenSandbox isolation
resource limits
manual review
```

---

# 39. RLM policy

RLM hữu ích khi phân tích context rất lớn, nhưng không nên đưa vào core V13 ngay.

Lưu ý governance quan trọng: `dspy.RLM` tự vận hành một Python REPL sandbox nội bộ để model khám phá context (đọc biến, chạy code, gọi sub-LLM đệ quy) — đây chính là dạng "DSPy PythonInterpreter" mà mục 40 cấm chạy thẳng lên host filesystem/business credentials. Do đó nếu `COSA_DSPY_RLM_ENABLED=true`, REPL của RLM bắt buộc phải được route qua `COSA ExecutionProvider` → `OpenSandbox` giống mọi execution khác, không được coi RLM là "chỉ là suy luận" nên miễn trừ khỏi OpenSandbox policy. Đặc biệt không bật RLM cho Finance/Legal khi input có thể chứa dữ liệu nhạy cảm/production DB.

Potential later use:

```text
large project history
large customer dataset
long weekly/cycle history
large knowledge corpus
```

Default:

```text
COSA_DSPY_RLM_ENABLED=false
```

Ưu tiên RAG/context resolver hiện tại trước.

---

# 40. OpenSandbox integration

DSPy không thay OpenSandbox.

Khi DSPy program cần:

```text
Python
browser
file transforms
CLI
```

flow:

```text
DSPy Program
  ↓
request execution
  ↓
COSA ExecutionProvider
  ↓
OpenSandbox
  ↓
result
  ↓
DSPy synthesis
```

Không:

```text
DSPy PythonInterpreter
  ↓
host filesystem/business credentials
```

Đặc biệt với Finance/Legal:

```text
no arbitrary Python against production DB
```

---

# 41. n8n integration

DSPy không thay n8n.

```text
DSPy = decide / classify / draft / evaluate
n8n  = trigger / schedule / external integration
```

Ví dụ Sales:

```text
n8n new lead
  ↓
COSA API
  ↓
Sales Agent
  ↓
DSPy LeadQualification
  ↓
COSA stores result
  ↓
Policy
  ↓
n8n CRM update
```

n8n không gọi DSPy artifact trực tiếp.

Luôn qua COSA API/Agent Gateway.

---

# 42. LiveKit

DSPy không nằm trong low-latency audio transport loop.

Flow:

```text
Voice
  ↓
LiveKit
  ↓
COSA Companion
  ↓
Intent
  ├─ simple conversation → realtime model
  └─ work task → Agent Gateway
                   ↓
               Harness
                   ↓
             DSPy Program if needed
```

Không stream hidden DSPy reasoning qua voice.

Chỉ final result hoặc user-visible rationale.

---

# 43. Memory

DSPy không phải memory engine.

Output:

```text
DSPy result
  ↓
Memory Extractor
  ↓
Memory Policy
  ↓
PostgreSQL/pgvector
```

Không:

```text
DSPy optimizer trace
  ↓
automatic business memory
```

Learning dataset và Business Memory là hai loại dữ liệu khác nhau.

---

# 44. Security

## 44.1 Prompt injection

Context từ:

```text
web
email
CRM
documents
```

là untrusted.

DSPy program không được coi content bên ngoài là instruction cấp system.

## 44.2 Secrets

Không đưa:

```text
API key
OAuth token
password
database credential
```

vào DSPy input.

## 44.3 Cross-company isolation

Mọi eval/training example dùng customer data phải:

- scope company;
- có policy;
- không đưa vào global dataset mặc định;
- không dùng dữ liệu customer A tối ưu program cho customer B nếu chưa có quyền/consent thích hợp.

## 44.4 Hidden reasoning

Không lưu:

```text
raw chain-of-thought
hidden model reasoning
internal reflection traces
```

vào business audit.

Chỉ lưu:

```text
structured input
structured output
user-visible rationale
metric
usage
program version
model profile
tool metadata
```

Optimizer log chỉ ở dev/AI Lab, được sanitize.

---

# 45. Data governance cho optimization

Phân biệt:

```text
SYSTEM DATASET
CUSTOMER-LOCAL DATASET
GLOBAL PRODUCT DATASET
```

Default cho licensed local/private COSA:

```text
CUSTOMER DATA
stays customer controlled
```

Nếu optimizer chạy local:

```text
Customer PostgreSQL
  ↓
Local Eval
  ↓
Local Optimized Artifact
```

COSA License Server không nhận business dataset.

---

# 46. Local-first deployment

DSPy phù hợp với current FastAPI/Python.

Không cần tạo microservice mới ngay.

Recommended initial:

```text
Customer VPS / Local Server

FastAPI
├── COSA Core
├── Agent Worker
├── DSPy Program Runtime
├── PostgreSQL
├── OpenSandbox adapter
├── n8n adapter
└── LiveKit gateway
```

Optimization workload chạy worker riêng:

```text
ai-optimizer-worker
```

không chạy trong web request process.

---

# 47. FastAPI deployment

DSPy docs hỗ trợ deploy qua FastAPI.

Nhưng COSA đã có FastAPI.

Không tạo:

```text
DSPy FastAPI server
+
COSA FastAPI server
```

ở phase đầu.

Thay vào đó:

```text
COSA FastAPI
  ↓
AIProgramService
  ↓
DSPy runtime
```

Async:

```text
dspy.asyncify(...)
```

có thể được dùng trong worker/runtime adapter.

Phải có:

```text
concurrency limit
timeout
cancel best-effort
rate limit
budget
```

---

# 48. MLflow

DSPy docs hỗ trợ MLflow cho versioning/tracking/deployment.

COSA không cần thêm MLflow vào production MVP ngay.

Recommendation:

```text
Phase đầu:
PostgreSQL + COSA AI Lab metadata

Optional dev:
MLflow local
```

Feature:

```text
COSA_DSPY_MLFLOW_ENABLED=false
```

Chỉ bật khi:

- experiment volume tăng;
- cần optimizer trace UI chuyên sâu;
- team cần reproduce ML experiments.

Không dùng MLflow làm business source of truth.

---

# 49. Caching

DSPy có cache.

COSA phải phân biệt:

```text
DSPy inference cache
vs
COSA business cache
vs
COSA business state
```

Cache không được dùng để thay business database.

Với sensitive data:

- namespace theo company;
- TTL;
- encryption/storage policy;
- có thể disable cache cho legal/finance sensitive task.

---

# 50. Failure / fallback

DSPy phải là dependency có thể disable.

Flow:

```text
DSPyProgramRuntime
  ↓ fails
LegacyPromptProgramRuntime
  ↓
same output schema
```

hoặc:

```text
fail closed
```

cho Legal/Finance high-risk.

Policy theo program:

```yaml
fallback:
  mode: legacy | fail_closed
```

Examples:

```text
CEO Brief:
legacy allowed

Sales Lead Qualification:
legacy allowed

Finance statutory-related:
fail closed / human review

Legal high-risk:
fail closed / expert escalation
```

---

# 51. Feature flags

```yaml
features:

  dspy_enabled: false
  dspy_eval_enabled: false
  dspy_optimizer_enabled: false

  dspy_cycle_enabled: false
  dspy_okr_enabled: false
  dspy_twelve_week_enabled: false
  dspy_weekly_enabled: false
  dspy_week13_enabled: false
  dspy_ceo_brief_enabled: false
  dspy_next_actions_enabled: false

  dspy_sales_enabled: false
  dspy_marketing_enabled: false
  dspy_finance_enabled: false
  dspy_legal_enabled: false
  dspy_tech_enabled: false
  dspy_learning_enabled: false

  dspy_react_v2_enabled: false
  dspy_flex_enabled: false
  dspy_rlm_enabled: false
  dspy_mlflow_enabled: false
```

`dspy_week13_enabled` gate cho `week13.cycle_retrospective` (mục 16) — bị thiếu ở draft trước, bổ sung để mọi program trong registry đều có flag domain tương ứng (đối chiếu Phase D4, mục 53).

## 51.1 Flag precedence

Mỗi domain (`sales`, `marketing`, `finance`, `legal`, `tech`, `learning`, `cycle`, `okr`, `twelve_week`, `weekly`, `week13`) có thể chứa **nhiều program** (ví dụ domain `sales` gồm `sales.lead_qualification`, `sales.followup_strategy`, `sales.pipeline_analysis` — mục 19). Flag domain-level (`dspy_sales_enabled`) là **master kill-switch của cả domain**, không phải "bật toàn bộ program trong domain". Trạng thái hiệu lực của một program cụ thể luôn là AND của ba tầng:

```text
effective_enabled(program) =
    dspy_enabled
  AND dspy_<domain>_enabled
  AND dspy_<program_key>_enabled   # per-program flag, mặc định false nếu không khai báo
```

Registry (mục 7) phải set `enabled: false` mặc định cho từng program cho tới khi có flag per-program riêng bật tường minh — không suy ra "domain bật thì mọi program trong domain bật theo". Đây là lý do POC (mục 54) chỉ bật đúng 2 program dù domain `sales` và domain CEO Brief đã tồn tại nhiều program tiềm năng khác.

Initial development (khớp scope POC ở mục 54, chỉ 2 program, không kéo theo `sales.followup_strategy`/`sales.pipeline_analysis`):

```yaml
dspy_enabled: true
dspy_eval_enabled: true
dspy_optimizer_enabled: false

dspy_sales_enabled: true              # domain kill-switch
dspy_sales_lead_qualification_enabled: true   # program-level, duy nhất được bật trong domain sales

dspy_ceo_brief_enabled: true          # domain == program ở đây (CEO Brief chỉ có 1 program)
```

Production rollout sau eval.

---

# 52. Không đưa PESTEL/SWOT/TOWS vào registry

Acceptance test bắt buộc:

```python
assert not registry.exists("strategy.pestel")
assert not registry.exists("strategy.swot")
assert not registry.exists("strategy.tows")
assert not registry.exists("strategy.bsc")
```

AI Router:

```text
deprecated strategic intent
  ↓
do not call hidden module
  ↓
supported Cycle planning
or
FeatureNotEnabled
```

Không silently re-enable.

---

# 53. Technical phases

## Phase D0 — Foundation

Mục tiêu:

```text
DSPy dependency + abstraction
```

Tasks:

- pin `dspy==3.3.0`;
- tạo `AIProgramRuntime`;
- tạo `DSPyProgramRuntime`;
- program registry;
- model policy resolver;
- structured validation;
- tracing;
- feature flags;
- fallback runtime;
- unit tests.

Không optimizer.

---

## Phase D1 — Evaluation Backbone

Mục tiêu:

```text
measure before optimize
```

Tasks:

- dataset schema;
- metric framework;
- `ai_eval_*` tables;
- offline eval runner;
- regression report;
- cost/latency capture;
- simple AI Lab API.

Programs:

```text
ceo.brief
sales.lead_qualification
```

So sánh:

```text
legacy
vs
DSPy zero-shot/baseline
```

---

## Phase D2 — Production POC

Bật canary:

```text
CEO Brief
Sales Lead Qualification
```

Rollout:

```text
5%
→ 20%
→ 50%
→ 100%
```

Gate:

- quality không thấp hơn baseline;
- latency acceptable;
- cost within policy;
- zero critical data leakage;
- zero tool/approval bypass.

---

## Phase D3 — GEPA Offline Optimization

Bật:

```text
dspy_optimizer_enabled=true
```

chỉ AI Lab/worker.

Programs:

```text
ceo.brief
sales.lead_qualification
weekly.review_synthesis
```

Process:

```text
dataset
↓
baseline
↓
GEPA
↓
candidate
↓
holdout eval
↓
human review
↓
canary
```

---

## Phase D4 — Company Cycle Intelligence

Programs:

```text
cycle.intent_extractor
cycle.plan_draft
okr.draft
twelve_week.plan_draft
weekly.mission_draft
week13.cycle_retrospective
next_actions.rank
```

Không tạo Strategy Canvas.

Không tạo PESTEL/SWOT/TOWS.

---

## Phase D5 — Five AI Functions

Mở rộng:

```text
Marketing
Finance
Legal
Tech
Learning
```

Finance/Legal có stricter gates.

---

## Phase D6 — Advanced Experiments

Chỉ sau khi D0–D5 ổn định:

```text
ReActV2
RLM
Flex
fine-tuning
```

Không cam kết production.

---

# 54. POC đầu tiên đề xuất

Tôi khuyến nghị POC gồm **2 programs**, không phải Strategy:

## POC A — CEO Brief

Lý do:

- đọc nhiều domain;
- output bounded;
- không write;
- founder thấy giá trị ngay;
- metric rõ;
- dễ A/B test.

## POC B — Sales Lead Qualification

Lý do:

- có outcome thật;
- gắn Revenue/Sales v13.2;
- dễ tạo training examples;
- có feedback nhanh;
- ROI đo được.

Flow:

```text
Production Data
  ↓
Legacy + DSPy shadow
  ↓
Compare
  ↓
Founder feedback
  ↓
Eval Dataset
  ↓
GEPA
  ↓
Candidate
  ↓
Canary
```

Không bắt đầu bằng:

```text
Finance posting
Legal final advice
Tech code generation
ReAct tool agent
Flex
```

---

# 55. Shadow Mode

Trước production:

```text
User request
  ↓
Legacy answer → shown to user

same snapshot
  ↓
DSPy candidate → NOT shown
  ↓
eval
```

Store:

```text
program version
output
score
latency
cost
```

Không tạo external side effect.

Shadow mode rất phù hợp để build dataset an toàn.

---

# 56. Promotion gates

Một candidate chỉ được production nếu:

```text
quality >= baseline + minimum_delta
critical_failures == 0
schema_validity == 100%
security_regression == 0
latency <= threshold
cost <= budget
```

Finance/Legal thêm:

```text
expert-reviewed cases pass
```

---

# 57. Rollback

Mỗi production program phải có:

```text
current_version
previous_stable_version
```

Rollback:

```text
POST /internal/ai/programs/{key}/rollback
```

Không rollback database schema cùng DSPy artifact.

Program artifact độc lập.

---

# 58. API nội bộ đề xuất

```text
POST /internal/ai/programs/run
GET  /internal/ai/programs
GET  /internal/ai/programs/{key}
GET  /internal/ai/programs/{key}/versions

POST /internal/ai/evals/run
GET  /internal/ai/evals/{id}

POST /internal/ai/optimizers/run
GET  /internal/ai/optimizers/{id}

POST /internal/ai/programs/{key}/promote
POST /internal/ai/programs/{key}/rollback
```

Optimization endpoints chỉ admin/dev.

Không expose ra public customer API mặc định.

---

# 59. Testing

## Unit

- registry từ chối disabled strategy program;
- output schema validation;
- model policy mapping;
- feature flag;
- fallback;
- metric deterministic;
- no secret field;
- no hidden reasoning persistence.

## Integration

1. Agent gọi `sales.lead_qualification`.
2. DSPy program nhận đúng scoped context.
3. Output validate bằng Pydantic.
4. Program run liên kết `parent_agent_run_id`.
5. DSPy disabled → legacy fallback.
6. Finance high-risk program lỗi → fail closed.
7. Optimizer candidate không tự production.
8. Rollback đổi artifact active không mutate business data.
9. Customer A data không xuất hiện eval run customer B.
10. Hidden Strategy tools vẫn absent.

## Regression

Mỗi program release phải chạy:

```text
golden dataset
edge cases
security cases
adversarial injection cases
```

---

# 60. Security acceptance

- [ ] DSPy không có raw PostgreSQL credential.
- [ ] DSPy không được tự query arbitrary SQL.
- [ ] Write action luôn qua COSA Policy/Approval.
- [ ] MCP tools qua COSA allowlist.
- [ ] Không lưu hidden reasoning.
- [ ] Không gửi customer data vào global optimizer mặc định.
- [ ] Flex/ReActV2/RLM disabled production default.
- [ ] Finance/Legal có fail-closed policy phù hợp.
- [ ] DSPy artifact có hash/version.
- [ ] Model/provider vẫn do COSA Model Policy kiểm soát.

---

# 61. Performance / cost

Mỗi run capture:

```text
input tokens
output tokens
cache hit
model cost
latency
program version
```

Mục tiêu optimization không chỉ:

```text
maximize quality
```

mà:

```text
maximize:
quality

subject to:
cost
latency
security
policy
```

Có thể dùng composite score:

```text
deployment_score =
    quality_score
  - cost_penalty
  - latency_penalty
  - reliability_penalty
```

Hard safety gate vẫn nằm ngoài score.

---

# 62. Không tối ưu nhầm business objective

Ví dụ Sales:

Sai:

```text
optimizer metric = "message sounds persuasive"
```

Đúng hơn:

```text
human_quality
+
reply
+
qualified progression
+
meeting
+
no-spam / policy
```

Marketing:

Sai:

```text
likes
```

Đúng hơn:

```text
qualified demand
conversion
cost
Cycle KR contribution
```

CEO Brief:

Sai:

```text
long answer
```

Đúng:

```text
decision relevance
critical issue recall
attention saved
```

---

# 63. Human-in-the-loop

DSPy optimizer có thể đề xuất program tốt hơn.

Nhưng promotion là một business/system change.

Do đó:

```text
Optimizer
  ↓
Candidate
  ↓
Evaluator
  ↓
Developer/Admin approval
  ↓
Canary
  ↓
Production
```

Không:

```text
Optimizer
  ↓
Production
```

---

# 64. AI self-improvement terminology

Trong COSA UI/docs nên dùng:

```text
Evaluation
Learning from feedback
Offline optimization
Program improvement
Model benchmarking
```

Hạn chế nói:

```text
AI tự sửa mình
AI tự tiến hóa
AI tự học không cần kiểm soát
```

vì không phản ánh đúng governance.

---

# 65. Quan hệ với DeepSeek Harness

DeepSeek Harness:

```text
Who does the work?
What tool next?
What subtask next?
What agent/capability?
```

DSPy:

```text
How should this bounded reasoning task be represented?
How do we measure its quality?
Can instruction/examples be optimized?
Which candidate program performs better?
```

Một agent run có thể gọi nhiều DSPy programs.

Ví dụ:

```text
Chief of Staff
  ↓
CEO Brief Program
  ↓
Next Actions Ranker
  ↓
Sales Agent
      ↓
  Lead Qualification Program
  ↓
Harness continues execution
```

---

# 66. Quan hệ với OpenSandbox

OpenSandbox:

```text
execute code safely
```

DSPy:

```text
reason/evaluate/optimize
```

DSPy không được coi `PythonInterpreter` là lý do bỏ OpenSandbox policy của COSA.

---

# 67. Quan hệ với n8n

n8n:

```text
when/how to automate external systems
```

DSPy:

```text
what bounded AI output to produce
```

---

# 68. Quan hệ với LiveKit

LiveKit:

```text
communicate in realtime
```

DSPy:

```text
high-value structured reasoning behind the conversation
```

---

# 69. Quan hệ với Agent Memory

Memory:

```text
what COSA remembers
```

DSPy eval dataset:

```text
what examples COSA uses to measure/improve AI programs
```

Không trộn hai bảng.

---

# 70. Quan hệ với Claude Code

Claude Code:

```text
implementation executor
```

DSPy:

```text
task refinement / evaluation helper
```

Claude Code không cần gọi DSPy trực tiếp.

Tech Agent/COSA điều phối cả hai.

---

# 71. Suggested configuration

```env
# DSPy Core
COSA_DSPY_ENABLED=false
COSA_DSPY_VERSION=3.3.0

# Eval
COSA_DSPY_EVAL_ENABLED=false
COSA_DSPY_OPTIMIZER_ENABLED=false

# Domain kill-switch chạm tới trong Phase D0-D3 (xem mục 51.1)
COSA_DSPY_SALES_ENABLED=false

# Production programs (per-program flags, mục 51.1)
# CEO Brief: domain có đúng 1 program nên domain flag == program flag
COSA_DSPY_CEO_BRIEF_ENABLED=false
COSA_DSPY_SALES_LEAD_QUALIFICATION_ENABLED=false
COSA_DSPY_WEEKLY_REVIEW_ENABLED=false

# Experimental
COSA_DSPY_REACT_V2_ENABLED=false
COSA_DSPY_FLEX_ENABLED=false
COSA_DSPY_RLM_ENABLED=false
COSA_DSPY_MLFLOW_ENABLED=false

# Runtime
COSA_DSPY_MAX_CONCURRENT_RUNS=4
COSA_DSPY_DEFAULT_TIMEOUT_SECONDS=45
COSA_DSPY_CACHE_ENABLED=true
```

`.env` này chỉ liệt kê tập con bootstrap cho Phase D0–D3 (mục 53, ưu tiên P0–P2 ở mục 78). Ma trận flag đầy đủ — gồm `dspy_cycle_enabled`, `dspy_okr_enabled`, `dspy_twelve_week_enabled`, `dspy_weekly_enabled`, `dspy_week13_enabled`, `dspy_next_actions_enabled`, `dspy_marketing_enabled`, `dspy_finance_enabled`, `dspy_legal_enabled`, `dspy_tech_enabled`, `dspy_learning_enabled` — nằm ở mục 51 và chỉ cần thêm khi Phase D4/D5 bắt đầu triển khai domain tương ứng. Không lưu provider secret trong các config commit.

---

# 72. Suggested dependency file

```text
dspy==3.3.0
```

Có thể giữ optional extra riêng:

```text
requirements-ai.txt
```

hoặc Python dependency group:

```text
[project.optional-dependencies]
ai-optimization = [
  "dspy==3.3.0"
]
```

Mục tiêu:

- có thể disable dependency/runtime;
- dễ rollback;
- không ép mọi deployment dùng optimizer.

---

# 73. Migration principle

Không migration destructive.

Additive only:

```text
ai_programs
ai_program_versions
ai_program_runs
ai_eval_datasets
ai_eval_cases
ai_eval_runs
ai_metric_results
ai_optimizer_runs
ai_feedback
ai_program_deployments
```

Không sửa bảng business thành DSPy-specific.

Không thêm:

```text
dspy_prompt
dspy_signature
```

vào `sales_leads`, `objectives`, `transactions`.

---

# 74. Definition of Done — Phase D0/D1

DSPy foundation được xem là hoàn thành khi:

1. DSPy 3.3.0 được pin.
2. COSA boot được khi DSPy disabled.
3. Business modules không import DSPy trực tiếp.
4. Có `AIProgramRuntime`.
5. Có Program Registry.
6. Có Model Policy resolver.
7. Có output validation.
8. Có program version/artifact.
9. Có eval dataset + eval run.
10. CEO Brief và Sales Lead Qualification có baseline test.
11. Không bật Strategy/Pestel/Swot/Tows/BSC.
12. Không có write tool qua DSPy.
13. Không lưu hidden reasoning.
14. Có fallback/rollback.
15. Có cost/latency/quality report.

---

# 75. Definition of Done — GEPA

GEPA integration hoàn thành khi:

1. optimization chạy offline;
2. train/validation/holdout tách rõ;
3. candidate artifact immutable;
4. cost được ghi;
5. best score được ghi;
6. candidate không auto-promote;
7. regression suite pass;
8. human approve;
9. canary rollout;
10. rollback được.

---

# 76. Các anti-pattern Claude Code phải tránh

## Anti-pattern 1

```text
Replace DeepSeek Harness with DSPy
```

Không làm.

## Anti-pattern 2

```text
Re-enable PESTEL/SWOT/TOWS because DSPy is good at strategy
```

Không làm.

## Anti-pattern 3

```text
Every AI call becomes DSPy
```

Không cần.

Routine chat có thể tiếp tục model hiện tại.

## Anti-pattern 4

```text
Optimizer runs inside user request
```

Không làm.

## Anti-pattern 5

```text
DSPy writes CRM/accounting/business DB directly
```

Không làm.

## Anti-pattern 6

```text
Use Flex experimental in production
```

Không làm phase đầu.

## Anti-pattern 7

```text
LLM judge = only metric
```

Không làm.

## Anti-pattern 8

```text
Accepted by founder = always correct
```

Không làm, đặc biệt Legal/Finance.

## Anti-pattern 9

```text
Global dataset automatically collects all customer data
```

Không làm.

## Anti-pattern 10

```text
Expose optimizer trace/chain-of-thought to founder
```

Không làm.

---

# 77. Recommended initial architecture slice

```text
                   Flutter
                      │
                      ▼
                 FastAPI Core
                      │
                      ▼
                 Agent Gateway
                      │
              DeepSeek Harness
                      │
          ┌───────────┴────────────┐
          │                        │
          ▼                        ▼
      CEO Brief                Sales Agent
          │                        │
          ▼                        ▼
 DSPy CEOBriefProgram    DSPy LeadQualification
          │                        │
          └───────────┬────────────┘
                      ▼
               Structured Output
                      │
                      ▼
              Pydantic Validators
                      │
                      ▼
              COSA Business Layer
                      │
              ┌───────┴─────────┐
              ▼                 ▼
          PostgreSQL         Policy
                                │
                                ▼
                              n8n
```

OpenSandbox chưa cần cho hai program đầu.

---

# 78. Priority order

Recommended:

```text
P0
AIProgram abstraction
Program Registry
Eval Framework

P1
CEO Brief
Sales Lead Qualification

P2
GEPA Offline Optimization
Model Benchmarking

P3
Weekly Review
Next Actions

P4
Cycle / OKR / 12WY draft intelligence

P5
Marketing
Finance Insights
Legal
Tech
Learning

P6
Experimental ReActV2 / RLM / Flex
```

---

# 79. Tại sao DSPy phù hợp với COSA hiện tại hơn so với phiên bản Strategy cũ

Với V13 hiện tại, giá trị DSPy không còn nằm ở việc tự động hóa chuỗi framework chiến lược.

Giá trị thực tế hơn là:

```text
Company operation
  ↓
many repeated AI decisions
  ↓
structured programs
  ↓
feedback
  ↓
evaluation
  ↓
optimization
```

COSA có những loop giàu dữ liệu hơn:

```text
Cycle outcome
KR progress
weekly mission completion
sales conversion
marketing outcome
finance variance
legal review
tech artifact
founder edit
```

Đây chính là dữ liệu tốt để xây metric và eval.

Do đó DSPy thậm chí phù hợp **hơn** khi COSA tập trung vào vận hành thực tế, vì optimization có business feedback thật thay vì chỉ đánh giá chất lượng một bản phân tích chiến lược.

---

# 80. Kết luận triển khai

DSPy nên được tích hợp vào COSA v13.1/v13.2 dưới vai trò:

> **COSA Intelligence Optimization Layer**

Không phải:

```text
Agent Runtime
Workflow Runtime
Business Core
Memory Engine
Execution Sandbox
```

Kiến trúc cuối:

```text
COSA Core
   │
   ├── Company Cycle / OKR / 12WY
   ├── Work / Review / Learning
   ├── Legal / Marketing / Sales / Tech / Finance
   └── Governance / Memory / Audit
            │
            ▼
      Agent Gateway
            │
            ▼
     DeepSeek Harness
       Agent Runtime
            │
            ▼
      DSPy Programs
  Reason • Structure • Evaluate
            │
        ┌───┴────┐
        ▼        ▼
      MCP    OpenSandbox
        │
        ▼
       n8n
```

Nhưng về trách nhiệm phải đọc là:

```text
COSA Core      = Govern + Business Truth
Harness        = Run Agents
DSPy           = Improve Intelligence Programs
OpenSandbox    = Execute Safely
n8n            = Automate Integrations
LiveKit        = Communicate Realtime
PostgreSQL     = Persist Business Truth + Eval Metadata
```

### Quyết định sản phẩm

**TÍCH HỢP DSPy.**

### Quyết định phạm vi

**Không bật lại PESTEL/SWOT/TOWS/BSC/Strategic Canvas/Portfolio Strategy.**

### POC đầu tiên

```text
1. CEO Brief
2. Sales Lead Qualification
```

### Nguyên tắc học hỏi

```text
Production feedback
→ Curated dataset
→ Offline evaluation
→ DSPy optimization
→ Candidate
→ Regression
→ Human approval
→ Canary
→ Production
```

Đây là cách phù hợp nhất để biến COSA từ hệ thống "có nhiều prompt AI" thành một Business OS có **AI programs đo được, kiểm thử được, tối ưu được và rollback được**, trong khi vẫn giữ đúng V13 Focused Company Cycle OS.

---

# Appendix A — Checklist cho Claude Code

## Baseline

- [ ] Giữ COSA v13.1/v13.2.
- [ ] Không tạo v14/v15.
- [ ] Không bật Strategy full.
- [ ] Không bật PESTEL.
- [ ] Không bật SWOT.
- [ ] Không bật TOWS.
- [ ] Không bật BSC.
- [ ] Không bật Portfolio Strategy.

## Architecture

- [ ] DeepSeek Harness vẫn là Agent Runtime.
- [ ] DSPy chỉ là Intelligence Program/Eval/Optimization layer.
- [ ] Business modules không import DSPy trực tiếp.
- [ ] Có `AIProgramRuntime`.
- [ ] Có `DSPyProgramRuntime`.
- [ ] Có fallback runtime.
- [ ] Có Program Registry.

## DSPy

- [ ] Pin `dspy==3.3.0`.
- [ ] ReActV2 disabled default.
- [ ] Flex disabled default.
- [ ] RLM disabled default.
- [ ] GEPA chỉ offline.
- [ ] Compiled artifact save/load.
- [ ] Immutable program version.

## Data

- [ ] Eval dataset versioned.
- [ ] Feedback stored separately from memory.
- [ ] Customer data scoped.
- [ ] No global data sharing by default.
- [ ] No hidden reasoning persisted.

## Governance

- [ ] DSPy cannot bypass Policy Engine.
- [ ] DSPy cannot approve actions.
- [ ] DSPy cannot directly mutate business state.
- [ ] Finance/Legal high-risk paths fail closed.
- [ ] Promotion requires human/admin approval.

## POC

- [ ] CEO Brief baseline.
- [ ] Sales Lead Qualification baseline.
- [ ] Shadow mode.
- [ ] Quality/cost/latency report.
- [ ] GEPA candidate only after dataset exists.
- [ ] Canary rollout.
- [ ] Rollback.

---

# Appendix B — Official DSPy references checked

1. DSPy official site — https://dspy.ai/
2. DSPy official GitHub — https://github.com/stanfordnlp/dspy
3. DSPy releases — https://github.com/stanfordnlp/dspy/releases
4. DSPy GEPA optimization — https://dspy.ai/getting-started/gepa-optimization/
5. DSPy optimizer selection — https://dspy.ai/diving-deeper/choosing-an-optimizer/
6. DSPy MCP tutorial — https://dspy.ai/tutorials/mcp/
7. DSPy deployment — https://dspy.ai/tutorials/deployment/
8. DSPy tools/development/deployment — https://dspy.ai/tutorials/core_development/

## Verified upstream notes used in this document

As of 2026-08-15:

- DSPy latest release shown by the official repository is **3.3.0**, released 2026-08-03.
- DSPy 3.3.0 introduces **Flex** as an experimental program-structure optimization mechanism.
- DSPy 3.3.0 includes **ReActV2**, marked experimental.
- DSPy supports structured Signatures, Modules, Optimizers, saving/loading compiled programs, MCP tooling, async and FastAPI deployment.
- DSPy documentation recommends treating optimizer compilation as an offline/expensive process and reusing saved compiled artifacts.
- GEPA can use textual metric feedback to evolve instructions.
- DSPy supports deployment patterns with FastAPI and MLflow, but COSA should embed DSPy behind its existing FastAPI/worker boundary rather than add an unnecessary second web service initially.

---

# Appendix C — Guiding Principle

```text
Do not optimize what you cannot measure.
Do not deploy what you cannot rollback.
Do not let an optimizer bypass governance.
Do not confuse agent execution with intelligence optimization.
Do not re-enable disabled product scope just because a new framework can support it.
```
