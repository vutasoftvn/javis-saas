# AI Agent OS — Improvement Engine / Ratchet Subsystem

> **Status:** Proposed Architecture Addendum  
> **Scope:** Core AI Agent OS  
> **Purpose:** Bổ sung cơ chế cải tiến có kiểm soát cho Agent, Skill, Prompt, Policy, Tool và Workflow  
> **Principle:** *Agents may propose improvements; production changes require evidence, evaluation, policy checks, and human approval.*

---

## 1. Mục tiêu

AI Agent OS không nên chỉ vận hành theo vòng lặp:

```text
Plan → Act → Observe
```

Mà cần tiến tới vòng lặp cấp hệ thống:

```text
Plan
  ↓
Act
  ↓
Observe
  ↓
Evaluate
  ↓
Detect Failure / Opportunity
  ↓
Generate Improvement Proposal
  ↓
Validate
  ↓
Human Review
  ↓
Regression Eval
  ↓
Promote Version
  ↓
Observe Again
```

Subsystem đề xuất có tên:

# Improvement Engine

Improvement Engine là lớp chịu trách nhiệm biến lỗi, phản hồi, dữ liệu vận hành và kết quả đánh giá của Agent thành **đề xuất cải tiến có cấu trúc**, sau đó đưa các đề xuất qua quy trình kiểm thử, phê duyệt, versioning và rollout an toàn.

Mục tiêu không phải tạo một Agent “tự sửa production”, mà tạo ra một hệ thống:

> **Self-improving, but human-governed.**

---

## 2. Vì sao AI Agent OS cần subsystem này?

Agent thông thường thường dừng ở:

```text
User Request
    ↓
Agent
    ↓
Tool / LLM / Memory
    ↓
Response
```

Nếu Agent sai, con người phải:

1. phát hiện lỗi;
2. đọc log;
3. tìm nguyên nhân;
4. sửa prompt;
5. sửa tool;
6. chạy thử;
7. deploy lại.

Quy trình này không scale khi hệ thống có:

- hàng trăm Agent;
- hàng nghìn Skill;
- nhiều model;
- nhiều tenant;
- nhiều workflow;
- nhiều tool;
- nhiều policy;
- hàng triệu Agent Run.

Improvement Engine biến quá trình này thành một pipeline tiêu chuẩn:

```text
Production Runs
      │
      ▼
Failure / Feedback / Metrics
      │
      ▼
Improvement Engine
      │
      ├── Analyze
      ├── Classify
      ├── Propose
      ├── Evaluate
      ├── Review
      └── Promote
```

---

# 3. Nguyên tắc kiến trúc

## 3.1. Agent không được tự ý sửa production

Agent có thể:

- phát hiện lỗi;
- phân tích nguyên nhân;
- đề xuất prompt mới;
- đề xuất policy mới;
- đề xuất test mới;
- đề xuất thay đổi workflow;
- đề xuất thay tool;
- đề xuất memory rule.

Nhưng không được tự động:

- thay production prompt;
- cấp thêm permission;
- sửa business rule;
- thay model ở production;
- xoá guardrail;
- thay policy bảo mật;
- deploy code;
- sửa dữ liệu nghiệp vụ quan trọng.

Mọi thay đổi production phải đi qua:

```text
Proposal
   ↓
Policy Check
   ↓
Evaluation
   ↓
Approval
   ↓
Version Promotion
```

---

## 3.2. Mọi cải tiến phải có bằng chứng

Không chấp nhận:

```text
"Model nghĩ prompt mới tốt hơn."
```

Mỗi proposal phải kèm:

```text
evidence
baseline
candidate
evaluation
risk
expected impact
rollback plan
```

---

## 3.3. Ratchet Principle

Một failure quan trọng khi đã được xác nhận nên trở thành một “ratchet”:

> Hệ thống phải ngày càng khó lặp lại cùng một loại lỗi.

Ví dụ:

```text
Failure:
Agent sử dụng tài liệu hết hiệu lực.

Ratchet 1:
Prompt yêu cầu ưu tiên tài liệu còn hiệu lực.

Ratchet 2:
Retrieval filter loại tài liệu expired.

Ratchet 3:
Post-retrieval validator kiểm tra effective_date.

Ratchet 4:
Regression test cho trường hợp tài liệu hết hiệu lực.

Ratchet 5:
Reviewer Agent kiểm tra nguồn trước final answer.
```

Mức độ bảo vệ tăng dần từ:

```text
Instruction
→ Retrieval
→ Validation
→ Policy
→ Evaluation
→ Reviewer
```

---

# 4. Vị trí trong AI Agent OS

```text
┌─────────────────────────────────────────────┐
│                EXPERIENCE                   │
│ Chat │ API │ UI │ Automation │ Voice       │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                 BUSINESS                    │
│ OKR │ 12 Week Year │ Tasks │ CRM │ ...     │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│               AGENT RUNTIME                 │
│ Planner │ Executor │ Router │ Multi-Agent   │
└─────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌─────────────────────┐
│     HARNESS      │    │    CONTROL PLANE    │
│ Context          │    │ Agent Registry      │
│ Memory           │    │ Skill Registry      │
│ Tools            │    │ Prompt Registry     │
│ Policy           │    │ Model Registry      │
│ Evaluation       │    │ Versioning          │
└──────────────────┘    └─────────────────────┘
        │                         │
        └────────────┬────────────┘
                     ▼
       ┌───────────────────────────┐
       │    IMPROVEMENT ENGINE     │
       │                           │
       │ Detect                    │
       │ Analyze                   │
       │ Propose                   │
       │ Evaluate                  │
       │ Approve                   │
       │ Promote                   │
       │ Learn                     │
       └───────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│                 AGENT OPS                   │
│ Trace │ Replay │ Metrics │ Cost │ Evals    │
└─────────────────────────────────────────────┘
```

Improvement Engine không thay thế AgentOps, Eval hoặc Control Plane.

Nó **orchestrate** các subsystem này để tạo vòng lặp cải tiến.

---

# 5. Thành phần của Improvement Engine

Đề xuất chia thành 9 module.

```text
Improvement Engine
│
├── 1. Signal Collector
├── 2. Failure Classifier
├── 3. Root Cause Analyzer
├── 4. Improvement Planner
├── 5. Proposal Generator
├── 6. Sandbox Evaluator
├── 7. Approval Gateway
├── 8. Version Promoter
└── 9. Learning Registry
```

---

# 6. Signal Collector

Signal Collector thu thập dữ liệu có thể dẫn tới một cải tiến.

Nguồn signal:

```text
Agent Run
Tool Error
User Feedback
Human Override
Eval Failure
Policy Violation
Latency Regression
Cost Regression
Hallucination
Bad Retrieval
Memory Error
Workflow Failure
Security Alert
Repeated Retry
Low Confidence
Business KPI Miss
```

## 6.1. Signal schema đề xuất

```python
class ImprovementSignal:
    id: str
    tenant_id: str | None

    source: str
    source_id: str

    agent_id: str | None
    skill_id: str | None
    workflow_id: str | None

    signal_type: str
    severity: str

    summary: str
    evidence: dict

    created_at: datetime
```

## 6.2. Signal types

```text
USER_NEGATIVE_FEEDBACK
EVAL_FAILED
TOOL_FAILED
POLICY_VIOLATION
WRONG_ANSWER
WRONG_ACTION
RETRIEVAL_FAILURE
MEMORY_FAILURE
HIGH_COST
HIGH_LATENCY
HUMAN_OVERRIDE
WORKFLOW_STUCK
SECURITY_EVENT
BUSINESS_OUTCOME_MISS
```

---

# 7. Failure Classifier

Không phải mọi lỗi đều nên giải quyết bằng sửa prompt.

Failure Classifier xác định lỗi thuộc layer nào.

```text
Failure
│
├── Model
├── Prompt
├── Context
├── Retrieval
├── Memory
├── Tool
├── Workflow
├── Policy
├── Permission
├── Agent Routing
├── Multi-Agent Coordination
├── Business Logic
└── Infrastructure
```

Ví dụ:

| Failure | Không nên làm | Nên làm |
|---|---|---|
| Tool timeout | sửa prompt | retry/circuit breaker |
| Tài liệu stale | tăng temperature | retrieval policy |
| Agent vượt quyền | prompt warning | permission/policy |
| Sai business rule | thêm CoT | sửa deterministic service |
| Quên user preference | system prompt dài hơn | memory policy |
| Tool schema mơ hồ | thêm reasoning | sửa tool contract |

---

# 8. Root Cause Analyzer

Root Cause Analyzer không chỉ đọc output cuối.

Nó phải có khả năng truy cập:

```text
Run Trace
│
├── Input
├── Context
├── Retrieved Documents
├── Memory Reads
├── Prompt Version
├── Model
├── Tool Calls
├── Tool Results
├── Agent Transitions
├── Policy Decisions
├── Output
└── Eval Results
```

Output là một `RootCauseReport`.

```python
class RootCauseReport:
    signal_id: str

    primary_cause: str
    contributing_causes: list[str]

    affected_component: str
    affected_version: str | None

    evidence_refs: list[str]

    confidence: float
    reasoning_summary: str

    recommended_change_types: list[str]
```

Lưu ý:

`reasoning_summary` là kết luận giải thích có thể audit được, không cần lưu private chain-of-thought của model.

---

# 9. Improvement Planner

Improvement Planner chọn loại intervention phù hợp.

Các loại intervention nên được chuẩn hóa:

```text
PROMPT_PATCH
SKILL_UPDATE
TOOL_SCHEMA_UPDATE
TOOL_IMPLEMENTATION_FIX
CONTEXT_POLICY_UPDATE
RETRIEVAL_RULE
MEMORY_POLICY_UPDATE
WORKFLOW_UPDATE
ROUTING_UPDATE
MODEL_ROUTING_UPDATE
GUARDRAIL_UPDATE
PERMISSION_UPDATE
EVAL_ADD
EVAL_UPDATE
REVIEWER_ADD
BUSINESS_RULE_CHANGE
CODE_CHANGE
```

Một failure có thể tạo nhiều ratchet.

Ví dụ:

```text
Failure:
Agent gửi email khi chưa được user duyệt.

Proposal:
1. Update action policy
2. Add approval gate
3. Add regression eval
4. Add audit event
```

---

# 10. Proposal Generator

Proposal Generator tạo một artifact có cấu trúc.

```yaml
proposal:
  id: imp_2026_000123

  target:
    type: skill
    id: sales.followup
    current_version: 1.7.2

  trigger:
    signal_ids:
      - sig_98231
      - sig_98249

  problem:
    category: policy_violation
    description: >
      Agent gửi email mà không qua approval step.

  root_cause:
    component: workflow
    confidence: 0.94

  proposed_changes:
    - type: workflow_update
      description: Add explicit approval node before email.send

    - type: policy_update
      description: Require approval token for external send actions

    - type: eval_add
      description: Regression case for unapproved email send

  expected_effect:
    reduce_failure_rate: 0.95

  risk:
    level: medium
    notes:
      - may increase workflow latency

  rollback:
    version: 1.7.2
```

---

# 11. Proposal là first-class object

Không nên để Agent sửa trực tiếp resource.

Luồng chuẩn:

```text
Current Version
      │
      ▼
Improvement Proposal
      │
      ▼
Candidate Version
      │
      ▼
Evaluation
      │
      ▼
Approval
      │
      ▼
Promoted Version
```

Candidate phải immutable sau khi bắt đầu evaluation.

---

# 12. Sandbox Evaluator

Mọi proposal cần được test ngoài production.

```text
Candidate
   │
   ├── Unit Eval
   ├── Regression Eval
   ├── Safety Eval
   ├── Policy Eval
   ├── Cost Eval
   ├── Latency Eval
   └── Business Eval
```

## 12.1. So sánh baseline và candidate

```text
                   Baseline     Candidate

Task success         82%           91%
Policy violations    3.1%          0.2%
Cost/run            $0.18         $0.20
Latency              4.1s          4.3s
Regression pass      94%           99%
```

Không nên promote chỉ vì một metric tốt hơn.

---

# 13. Eval Gates

Ví dụ policy:

```yaml
promotion_policy:
  minimum:
    task_success_rate: 0.90
    regression_pass_rate: 0.99

  maximum:
    policy_violation_rate: 0.001
    cost_regression_pct: 15
    latency_regression_pct: 20

  required:
    security_eval: pass
    critical_regressions: 0
```

---

# 14. Regression Corpus

Improvement Engine cần xây một corpus từ failure thật.

```text
Production Failure
      ↓
Sanitize
      ↓
Convert to Eval Case
      ↓
Regression Corpus
```

Schema:

```python
class RegressionCase:
    id: str

    source_signal_id: str | None

    input: dict
    expected: dict

    constraints: list[dict]

    severity: str
    tags: list[str]

    created_from_production: bool
```

Đây là chìa khóa của Ratchet:

> mỗi lỗi quan trọng trở thành một bài test lâu dài.

---

# 15. Approval Gateway

Không phải proposal nào cũng cần cùng một mức approval.

Đề xuất risk tiers:

## Tier 0 — Auto-safe

Ví dụ:

- thêm eval case;
- thêm observability tag;
- tạo dashboard;
- tạo candidate chưa active.

Có thể auto-approve.

---

## Tier 1 — Low risk

Ví dụ:

- minor prompt clarification;
- retrieval reranking config;
- non-sensitive skill instructions.

Có thể:

```text
AI Proposal
   ↓
Automated Eval
   ↓
Owner Approval
```

---

## Tier 2 — Medium risk

Ví dụ:

- workflow change;
- tool selection;
- model routing;
- memory write policy.

Yêu cầu:

```text
Owner + Eval Gate
```

---

## Tier 3 — High risk

Ví dụ:

- permission;
- external write action;
- finance;
- HR;
- security;
- destructive action;
- production code.

Yêu cầu:

```text
Human Review
+ Security/Policy Review
+ Evaluation
+ Explicit Approval
```

---

# 16. Approval Object

```python
class ImprovementApproval:
    proposal_id: str

    reviewer_id: str
    reviewer_type: str

    decision: str
    comment: str | None

    policy_checks: list[dict]

    approved_at: datetime | None
```

Decision:

```text
APPROVE
REJECT
REQUEST_CHANGES
EXPIRE
```

---

# 17. Version Promoter

Mọi thành phần Agent OS quan trọng cần version.

```text
Agent
Skill
Prompt
Workflow
Policy
Tool Contract
Context Policy
Memory Policy
Model Routing
Eval Suite
```

Version lifecycle:

```text
DRAFT
  ↓
CANDIDATE
  ↓
EVALUATED
  ↓
APPROVED
  ↓
CANARY
  ↓
PRODUCTION
  ↓
DEPRECATED
```

Rollback phải là thao tác first-class:

```text
production v1.8
      ↓
incident
      ↓
rollback
      ↓
v1.7
```

---

# 18. Canary Deployment

Không nên promote candidate trực tiếp tới 100%.

```text
Candidate
   ↓
1% traffic
   ↓
5%
   ↓
25%
   ↓
50%
   ↓
100%
```

Metrics theo dõi:

```text
task success
policy violations
user feedback
tool errors
latency
cost
business KPI
human override
```

Nếu vượt threshold:

```text
Auto Stop
   ↓
Rollback
   ↓
Create Incident Signal
```

---

# 19. Learning Registry

Learning Registry lưu “kiến thức cải tiến” ở cấp hệ thống.

Không phải user memory.

Nó lưu:

```text
Failure Pattern
Root Cause Pattern
Successful Intervention
Failed Intervention
Regression Case
Ratchet Rule
Known Risk
Model Behavior
Tool Reliability
```

Ví dụ:

```yaml
learning:
  pattern: stale_document_retrieval

  observed:
    count: 43

  effective_interventions:
    - retrieval_validity_filter
    - effective_date_validator

  ineffective_interventions:
    - prompt_only_warning

  default_recommendation:
    use_retrieval_filter: true
```

Điều này cho phép Improvement Planner học từ lịch sử mà không tự thay đổi production.

---

# 20. Ratchet Registry

Nên có registry riêng cho các rule hình thành từ incident.

```python
class Ratchet:
    id: str

    scope: str
    target_id: str | None

    trigger_pattern: str

    control_type: str
    control_config: dict

    source_proposal_id: str
    source_signal_ids: list[str]

    severity: str

    active: bool
    version: int
```

Ví dụ:

```yaml
ratchet:
  id: ratchet_email_approval

  scope: global

  trigger_pattern:
    tool: gmail.send

  control:
    type: require_human_approval

  exceptions:
    - verified_automation

  severity: critical
```

---

# 21. Improvement Engine State Machine

```text
DETECTED
   ↓
TRIAGED
   ↓
ANALYZING
   ↓
PROPOSED
   ↓
EVALUATING
   ├──── failed ────→ REJECTED
   ↓
READY_FOR_REVIEW
   ├──── rejected ─→ REJECTED
   ├──── changes ──→ REVISION_REQUIRED
   ↓
APPROVED
   ↓
CANARY
   ├──── failure ──→ ROLLED_BACK
   ↓
PROMOTED
   ↓
MONITORING
   ↓
VERIFIED
```

---

# 22. Database Model đề xuất

Tối thiểu:

```text
improvement_signals
improvement_incidents
root_cause_reports
improvement_proposals
proposal_changes
candidate_versions
evaluation_runs
evaluation_results
approval_requests
approval_decisions
deployment_rollouts
ratchets
regression_cases
learning_patterns
```

---

# 23. Event Model

Improvement Engine nên event-driven.

Ví dụ event:

```text
agent.run.completed
agent.run.failed

eval.failed
eval.regression_detected

user.feedback.negative

policy.violation

tool.failed

human.override

improvement.signal.created
improvement.proposal.created
improvement.evaluation.completed
improvement.approved
improvement.promoted
improvement.rollback
```

---

# 24. Interfaces giữa các subsystem

## AgentOps → Improvement Engine

```python
class ImprovementSignalSink(Protocol):
    async def emit(
        self,
        signal: ImprovementSignal
    ) -> None:
        ...
```

---

## Improvement Engine → Evaluation Harness

```python
class EvaluationService(Protocol):
    async def evaluate_candidate(
        self,
        target_id: str,
        baseline_version: str,
        candidate_version: str,
        suite_ids: list[str],
    ) -> "EvaluationReport":
        ...
```

---

## Improvement Engine → Control Plane

```python
class VersionRegistry(Protocol):
    async def create_candidate(...): ...
    async def promote(...): ...
    async def rollback(...): ...
```

---

## Improvement Engine → Policy Engine

```python
class ImprovementPolicy(Protocol):
    async def assess(
        self,
        proposal: "ImprovementProposal",
    ) -> "RiskAssessment":
        ...
```

---

# 25. Multi-Agent Design bên trong Improvement Engine

Có thể dùng multi-agent nhưng không nên lạm dụng.

Đề xuất:

```text
Improvement Orchestrator
│
├── Failure Analyst
├── Context/Memory Analyst
├── Tool Analyst
├── Workflow Analyst
├── Security Reviewer
├── Proposal Agent
└── Evaluation Reviewer
```

Các analyst có thể chạy song song:

```text
                  Failure
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
      Context      Tool      Workflow
      Analyst     Analyst     Analyst
          │          │          │
          └──────────┼──────────┘
                     ▼
               Root Cause
                     ↓
              Proposal Agent
```

Không cần multi-agent nếu một deterministic analyzer giải quyết được vấn đề.

---

# 26. Phân tách LLM và deterministic logic

Improvement Engine không nên là một Agent lớn.

## Dùng LLM cho

```text
failure summarization
root cause hypothesis
proposal drafting
similar incident search
risk explanation
eval case generation
```

## Dùng deterministic code cho

```text
permission checks
promotion gates
versioning
approval state
rollback
schema validation
threshold evaluation
audit logs
security constraints
```

Nguyên tắc:

> LLM đề xuất.  
> Policy quyết định.  
> Control Plane thực thi.

---

# 27. Human-in-the-loop UI

Control Plane UI nên có một trang:

# Improvement Inbox

Hiển thị:

```text
Proposal
Severity
Affected Agent / Skill
Root Cause
Evidence
Current Version
Candidate Version
Eval Difference
Risk
Requested Approval
```

Reviewer có thể:

```text
Approve
Reject
Request Changes
Run More Evals
Compare Versions
Replay Failure
View Trace
Rollback
```

---

# 28. Diff là bắt buộc

Reviewer không nên đọc toàn bộ prompt/workflow.

UI phải hiển thị diff:

```diff
- Agent may send email when follow-up is required.
+ Agent must request explicit user approval before external email send.
```

Workflow diff:

```diff
research
  ↓
draft
+ ↓
+ approval
  ↓
send
```

---

# 29. Replay

Mỗi failure quan trọng nên có thể replay:

```text
Original Input
Original Context
Original Tool Results
Original Model/Version
        ↓
      Replay
        ↓
Candidate Version
```

Cho phép so sánh:

```text
Original Result
vs
Candidate Result
```

Đây là nền tảng của debugging Agent production.

---

# 30. Ví dụ: Agent OKR

Giả sử Agent thường đưa ra Key Result không đo lường được.

Failure:

```text
KR:
"Improve customer satisfaction."
```

Signal:

```text
EVAL_FAILED:
KR_NOT_MEASURABLE
```

Improvement Engine:

```text
Signal
  ↓
Classifier
  ↓
Skill Instruction Problem
  ↓
Proposal
  ├── update OKR skill
  ├── add measurable-KR validator
  └── add regression cases
```

Candidate:

```text
"Increase NPS from 42 to 55 by end of Q4."
```

Ratchet:

```text
Every KR must contain:
metric + baseline/target + deadline
```

---

# 31. Ví dụ: 12 Week Year

Failure:

Agent tạo quá nhiều tactics:

```text
23 tactics/week
```

Evaluation nhận thấy completion rate giảm.

Improvement proposal:

```text
Update planning skill:
limit weekly high-impact tactics to 3–5.

Add evaluator:
weekly_plan_focus_score.
```

Human duyệt.

Candidate được test trên historical plans.

Nếu completion rate tăng mà goal coverage không giảm, mới promote.

---

# 32. Ví dụ: Task Agent

Failure:

Agent tạo duplicate task.

Root cause:

```text
Agent không search existing tasks trước create.
```

Ratchet:

```text
Before task.create:
    task.search(similar_title, project, due_date)
```

Thêm:

```text
duplicate_task_eval
```

Về sau mọi phiên bản Agent phải pass bài test này.

---

# 33. Ví dụ: Tool Failure

Failure:

```text
CRM API timeout
```

Improvement Engine không đề xuất sửa prompt.

Classifier:

```text
INFRASTRUCTURE / TOOL_RELIABILITY
```

Proposal:

```text
retry with exponential backoff
circuit breaker
idempotency key
timeout policy
```

Đây là lý do Failure Classifier rất quan trọng.

---

# 34. Skill integration

Improvement Engine nên tích hợp trực tiếp với Skill Registry.

Một Skill có thể chứa:

```yaml
skill:
  id: okr.review
  version: 1.4.0

  instructions:
    file: instructions.md

  tools:
    - okr.read
    - okr.update

  workflow:
    file: workflow.yaml

  policies:
    file: policy.yaml

  evals:
    - okr-quality
    - measurable-kr
    - alignment

  ratchets:
    - no-vague-kr
    - require-owner
```

Improvement proposal có thể tạo candidate version:

```text
okr.review@1.4.0
        ↓
proposal
        ↓
okr.review@1.5.0-candidate
```

---

# 35. Plugin architecture

Improvement types nên extensible.

```python
class ImprovementPlugin(Protocol):

    improvement_type: str

    async def analyze(...):
        ...

    async def generate_candidate(...):
        ...

    async def evaluate(...):
        ...
```

Plugin ví dụ:

```text
PromptImprovementPlugin
RetrievalImprovementPlugin
ToolImprovementPlugin
WorkflowImprovementPlugin
MemoryImprovementPlugin
PolicyImprovementPlugin
```

---

# 36. Security

Improvement Engine là subsystem rất nhạy cảm.

Attack scenario:

```text
Malicious input
   ↓
Agent fails intentionally
   ↓
Improvement Engine
   ↓
Proposal removes guardrail
```

Do đó mọi signal từ user input phải được coi là untrusted.

Bắt buộc có:

```text
proposal sandbox
permission boundary
signed version artifacts
immutable audit log
policy evaluation
human approval
security review
```

---

# 37. Không cho phép self-escalation

Một Agent không được đề xuất:

```text
"Give me more permissions so I can solve this."
```

rồi tự approve.

Permission proposal phải được đánh dấu:

```text
HIGH_RISK
```

và yêu cầu approval ngoài Agent owner nếu cần.

---

# 38. Audit

Mỗi promotion phải trả lời được:

```text
Who proposed it?
Why?
Which production failures caused it?
What changed?
Which evals passed?
Who approved?
When was it deployed?
What traffic received it?
Was it rolled back?
```

---

# 39. Observability

Metrics của Improvement Engine:

```text
improvement_signals_total
improvement_proposals_total
proposal_acceptance_rate
proposal_rejection_rate
mean_time_to_proposal
mean_time_to_approval
mean_time_to_verified_improvement
regression_escape_rate
rollback_rate
repeated_failure_rate
ratchet_effectiveness
```

Metric quan trọng nhất:

```text
repeated_failure_rate
```

Nếu hệ thống học tốt, tỷ lệ lặp lại cùng failure class phải giảm.

---

# 40. KPI cho self-improvement

Không nên đo bằng:

```text
number_of_generated_improvements
```

Nên đo:

```text
verified_improvement_rate
regression_reduction
failure_recurrence_reduction
human_override_reduction
task_success_delta
cost_delta
latency_delta
business_kpi_delta
```

---

# 41. Các cấp độ self-improvement

## Level 0 — Manual

```text
Human finds failure
Human changes system
```

---

## Level 1 — Assisted

```text
System detects failure
AI proposes fix
Human implements
```

---

## Level 2 — Candidate Generation

```text
System detects
AI proposes
AI creates candidate
Automated eval
Human approves
```

---

## Level 3 — Controlled Promotion

```text
System detects
AI creates candidate
Eval passes
Human approves
Canary deploy
Auto rollback
```

---

## Level 4 — Policy-Governed Autonomy

Chỉ low-risk changes:

```text
AI candidate
   ↓
policy gate
   ↓
eval
   ↓
auto canary
   ↓
auto promote
```

High-risk changes vẫn phải Human-in-the-loop.

Đề xuất AI Agent OS ban đầu nhắm **Level 2–3**.

Không nên bắt đầu ở Level 4.

---

# 42. MVP Scope

MVP không cần xây toàn bộ subsystem ngay.

## Phase 1

```text
Signal Collector
Failure Registry
Improvement Proposal
Human Approval
Regression Cases
```

---

## Phase 2

```text
Root Cause Agent
Candidate Versions
Automated Eval
Replay
```

---

## Phase 3

```text
Canary Promotion
Auto Rollback
Ratchet Registry
Learning Registry
```

---

## Phase 4

```text
Cross-Agent Learning
Pattern Discovery
Low-risk Auto Promotion
Portfolio Optimization
```

---

# 43. Kiến trúc triển khai Python

Gợi ý package:

```text
ai_agent_os/
│
├── improvement/
│   │
│   ├── domain/
│   │   ├── signal.py
│   │   ├── incident.py
│   │   ├── proposal.py
│   │   ├── ratchet.py
│   │   └── evaluation.py
│   │
│   ├── collectors/
│   │   ├── agentops.py
│   │   ├── feedback.py
│   │   ├── evals.py
│   │   └── policy.py
│   │
│   ├── analyzers/
│   │   ├── classifier.py
│   │   ├── root_cause.py
│   │   └── pattern_matcher.py
│   │
│   ├── planners/
│   │   └── improvement_planner.py
│   │
│   ├── proposals/
│   │   ├── generator.py
│   │   └── validator.py
│   │
│   ├── evaluation/
│   │   ├── sandbox.py
│   │   ├── regression.py
│   │   └── comparator.py
│   │
│   ├── approval/
│   │   └── gateway.py
│   │
│   ├── promotion/
│   │   ├── promoter.py
│   │   ├── canary.py
│   │   └── rollback.py
│   │
│   ├── learning/
│   │   ├── registry.py
│   │   └── ratchet_registry.py
│   │
│   └── application/
│       ├── service.py
│       └── events.py
```

---

# 44. Business Service boundary

Improvement Engine không nên được phép sửa trực tiếp business database.

Ví dụ:

```text
Improvement Engine
       │
       ▼
Candidate Config / Skill / Policy
       │
       ▼
Control Plane
       │
       ▼
Business Runtime
```

Không:

```text
Improvement Agent
       ↓
UPDATE tasks SET ...
```

Business logic deterministic vẫn nằm trong business service.

---

# 45. Encore / Business Layer

Nếu business layer dùng Encore TS/Go:

```text
Python AI Core
│
├── Agent Runtime
├── Harness
└── Improvement Engine
        │
        ▼
     API / Events
        │
        ▼
Encore Business Services
│
├── OKR
├── Tasks
├── Planning
└── CRM
```

Improvement Engine có thể đề xuất thay đổi behavior của Skill/Workflow, nhưng business invariants vẫn được enforce ở Encore service.

---

# 46. Relationship với Harness

Improvement Engine không phải Harness thứ 8 theo nghĩa runtime.

Nó là **meta-system** đứng trên các Harness.

```text
                     Improvement Engine
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     Context Harness   Tool Harness      Eval Harness
          │                 │                 │
          ▼                 ▼                 ▼
     change policy     change schema      add tests
```

Nó học từ toàn hệ thống và đề xuất thay đổi xuyên layer.

---

# 47. Relationship với AgentOps

```text
AgentOps
   ↓
Observe

Improvement Engine
   ↓
Learn + Propose

Control Plane
   ↓
Govern + Version

Evaluation
   ↓
Verify
```

Bốn subsystem này tạo thành vòng lặp:

```text
Observe
  ↓
Learn
  ↓
Govern
  ↓
Verify
  ↓
Deploy
  ↓
Observe
```

---

# 48. Relationship với Memory

Không nên lưu “lessons learned” chung vào conversational memory.

Tách:

```text
User Memory
Agent Memory
Organization Memory
Learning Registry
```

Learning Registry là dữ liệu engineering/system-level.

---

# 49. Relationship với Multi-Agent

Multi-agent có thể giúp phân tích failure nhưng Improvement Engine phải giữ orchestration deterministic.

```text
State Machine
    │
    ├── invokes Analyst Agents
    ├── validates outputs
    ├── applies policy
    └── controls transition
```

Không để các Agent tự quyết state transition quan trọng.

---

# 50. North-star architecture

Kiến trúc cuối cùng:

```text
                    AI AGENT OS
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   Agent Runtime       Harness       Control Plane
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                    AgentOps
                         │
                         ▼
                Improvement Engine
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           Analyze     Propose     Evaluate
              │          │          │
              └──────────┼──────────┘
                         ▼
                  Human Approval
                         │
                         ▼
                    Promotion
                         │
                         ▼
                  New Version
                         │
                         └───────────────┐
                                         │
                                         ▼
                                  Production Runs
                                         │
                                         └────→ AgentOps
```

Vòng lặp hoàn chỉnh:

```text
RUN
 ↓
OBSERVE
 ↓
EVALUATE
 ↓
LEARN
 ↓
PROPOSE
 ↓
APPROVE
 ↓
RATCHET
 ↓
DEPLOY
 ↓
RUN AGAIN
```

---

# 51. Đề xuất quyết định kiến trúc

Đề xuất bổ sung **Improvement Engine** vào AI Agent OS như một core subsystem độc lập.

Không triển khai nó như:

- một prompt;
- một Reflection Agent;
- một cron job sửa prompt;
- một feature của Memory;
- một phần nhỏ của AgentOps.

Nó cần có:

```text
Dedicated Domain Model
Dedicated Workflow
Dedicated Storage
Dedicated API
Dedicated Approval UI
Dedicated Audit Trail
```

---

# 52. Kiến trúc core sau khi bổ sung

```text
AI Agent OS Core
│
├── Agent Runtime
├── Context Engine
├── Memory Engine
├── Tool Gateway
├── Skill / Plugin Runtime
├── Workflow Engine
├── Multi-Agent Runtime
├── Policy Engine
├── Evaluation Platform
├── AgentOps
├── Control Plane
│
└── Improvement Engine       ★ NEW
      │
      ├── Signal Collector
      ├── Failure Classifier
      ├── Root Cause Analyzer
      ├── Improvement Planner
      ├── Proposal Generator
      ├── Sandbox Evaluator
      ├── Approval Gateway
      ├── Version Promoter
      ├── Ratchet Registry
      └── Learning Registry
```

---

# 53. Kết luận

Improvement Engine giúp AI Agent OS chuyển từ một nền tảng **chạy Agent** thành một nền tảng **vận hành và cải tiến Agent liên tục**.

Sự khác biệt là:

```text
Traditional Agent Platform

Build
  ↓
Deploy
  ↓
Operate
```

so với:

```text
AI Agent OS

Build
  ↓
Deploy
  ↓
Observe
  ↓
Evaluate
  ↓
Learn
  ↓
Propose
  ↓
Human Approve
  ↓
Ratchet
  ↓
Improve
```

Nguyên tắc cốt lõi:

> **AI proposes. Evidence validates. Policy constrains. Humans govern. Versions preserve safety.**

Đây nên là một trong những subsystem chiến lược của AI Agent OS và là nền tảng cho khả năng **controlled self-improvement** trong các phiên bản tiếp theo.
