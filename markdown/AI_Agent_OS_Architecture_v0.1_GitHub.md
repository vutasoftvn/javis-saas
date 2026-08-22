# AI AGENT OS

## Architecture & Product Design Specification

*Python-first • Event-sourced • Multi-agent • Memory-driven • Human-governed improvement*

```text
Purpose
Build a reusable Agent OS where execution, memory, learning and governance are generic;
business domains such as OKRs, 12 Week Year and Tasks plug in as application/domain layers.
```

> Design thesis  DeepSeek-style micro-kernel and replaceable capabilities + ADK-style workflow graph + TencentDB-style memory lifecycle + Hermes/Reflexion/Voyager-style learning, with explicit human approval before high-impact improvements.

Version: 0.1
Date: 22 August 2026
Primary language: Python 3.12+
Status: Architecture baseline / implementation blueprint

# 1. Executive Summary

*AI Agent OS is a reusable runtime and learning platform, not a single chatbot or a domain-specific agent.*

Mục tiêu của AI Agent OS là cung cấp một nền tảng chung để xây các AI-native business applications. Core chịu trách nhiệm execution, tool use, workflow, multi-agent coordination, session/event sourcing, context assembly, memory, learning và governance. Domain layer chịu trách nhiệm business truth: entity, rule, command, permission và workflow nghiệp vụ.

> Core principle  Core biết cách Agent chạy và cải tiến. Business layer biết điều gì đúng trong domain. LLM diễn giải, đề xuất và lập kế hoạch; deterministic business code xác thực, tính toán, enforce và persist.

| Plane | Trách nhiệm chính | Ví dụ |
| --- | --- | --- |
| Execution Plane | Agent Runtime, workflow, multi-agent, model/tool execution | Planner → parallel specialists → reviewer |
| Context Plane | Prompt/context assembly và token budget | system + persona + skills + memory + session |
| Memory & Knowledge Plane | L0-L3 memory, skills, wiki, code graph, retrieval | BM25 + vector + RRF |
| Improvement Plane | Evaluate → reflect → propose → validate | đề xuất sửa skill weekly planning |
| Governance Plane | Approval, version, canary, rollback, policy | human approves skill v4 |
| Domain/Application Plane | Business models, rules, commands, tools, workflows | OKR + 12 Week Year + Tasks |

Kiến trúc khuyến nghị không hard-depend vào Google ADK, DeepSeek Harness hay TencentDB Agent Memory. Các hệ thống này là reference và provider có thể thay thế. Điều đó giúp tránh vendor/framework lock-in và cho phép Agent OS phát triển độc lập.

## 1.1 Kết luận kiến trúc

- Python 3.12+ là ngôn ngữ chính cho kernel, runtime, workflows, business services và workers.

- Agent OS dùng micro-kernel nhỏ: Service Registry, Plugin Lifecycle, Scope, Event Bus, Execution Identity.

- Session Event Log là source of truth cho model-visible execution; state chỉ là projection/snapshot.

- Agent Loop là replaceable driver, không phải kernel.

- Workflow Runtime hỗ trợ sequential, parallel, branch, loop, handoff, supervisor và human approval.

- Memory chạy ngoài critical response path: L0 capture ngay; L1/L2/L3 được xử lý bất đồng bộ.

- Learning không phải self-modifying kernel. Agent chỉ tự quan sát, tự đánh giá, tự đề xuất; thay đổi high-impact cần human approval.

- Business applications chỉ cần thêm Domain + Application Layer và provider/integration cần thiết; core không đổi.

# 2. Vision, Scope & Non-Goals

*Xác định ranh giới để Agent OS không biến thành một monolith “làm mọi thứ”.*

## 2.1 Vision

AI Agent OS đóng vai trò như một application runtime cho các agent: cung cấp lifecycle, execution semantics, capability resolution, durable state, learning loop và governance. Một Product/Business Agent là application chạy trên runtime này, tương tự cách một ứng dụng chạy trên operating system.

```text
Agent OS Runtime
  + Domain Model
  + Business Rules
  + Domain Tools
  + Domain Workflows
  + Domain Skills
  = AI-native Business Application
```

## 2.2 In scope

- Single-agent và multi-agent execution.

- Streaming model/tool loop, cancellation, retry, timeout và concurrency.

- Durable sessions, events, runs, checkpoints, jobs và approvals.

- Memory, skills, knowledge retrieval và context budgeting.

- Evaluation, reflection, improvement proposal, versioning và controlled rollout.

- Domain/application integration thông qua typed tools, commands, workflows và policies.

- Multi-tenant identity, capability scope và access control.

- Observability, replay, audit và evaluation offline/online.

## 2.3 Non-goals

- Không tự xây foundation model hoặc inference engine.

- Không coi vector database là memory architecture.

- Không cho LLM trực tiếp mutate ORM/database hoặc bypass business rules.

- Không cho Agent tự sửa kernel, tự publish workflow/policy quan trọng mà không có governance.

- Không hard-code một orchestration framework cụ thể làm public contract.

- Không bắt buộc mọi business request phải đi qua nhiều agent; fast path vẫn là single-agent khi đủ.

# 3. Architecture Principles

*Các invariant nên được xem là “luật hệ thống”, không chỉ là convention.*

| ID | Principle | Ý nghĩa |
| --- | --- | --- |
| P1 | Model-visible means reconstructable | Bất kỳ context nào model thấy phải reconstruct được từ durable data/provenance. |
| P2 | Events are execution truth | Execution facts ghi vào Session Event Store; projection có thể rebuild. |
| P3 | Business truth is deterministic | LLM đề xuất; domain services validate, calculate, authorize và persist. |
| P4 | Capabilities are scoped | Tool, memory, skill, knowledge và sandbox được resolve theo tenant/team/user/agent/run. |
| P5 | Learning is downstream | Memory extraction và improvement analysis không chặn response path. |
| P6 | Improvement is governed | Agent có quyền propose và test; publish high-impact change cần policy/human approval. |
| P7 | Everything important is versioned | Prompt, skill, workflow, routing policy và agent config phải rollback được. |
| P8 | Workflow is explicit | Business-critical orchestration dùng graph/checkpoint thay vì prompt-only hidden flow. |
| P9 | Provider neutral core | Core không phụ thuộc OpenAI/Gemini/Claude/DeepSeek/Postgres/MCP implementation. |
| P10 | Measure improvement, do not assume it | Candidate phải được eval/canary trên outcome, quality, cost, latency và regressions. |

# 4. Reference Architectures & What We Reuse

*Không fork framework; lấy đúng primitive từ từng hệ thống.*

| Reference | Điểm mạnh dùng làm mẫu | Không copy trực tiếp |
| --- | --- | --- |
| DeepSeek Harness | Micro-kernel, services/capability seams, scoped registrations, replaceable agent loop, append-only session log, guarded tool pipeline | Cordis/TypeScript runtime và “everything is plugin” tuyệt đối |
| Google ADK 2+ | Workflow graph, agent/tool/function as executable nodes, Runner semantics, Session/Memory/Artifact separation | ADK BaseAgent/Runner làm public kernel API |
| TencentDB Agent Memory | L0→L1→L2→L3, memory as assets, hybrid retrieval, async pipeline, agent/team isolation, Skill/Wiki/CodeGraph separation | TypeScript MemoryCore, SQLite/local runtime choices làm hard dependency |
| Hermes Agent | Memory vs Skill, background review, agent-managed skills, approval gate | Agent tự ghi production changes không qua evaluation/versioning |
| Reflexion / Self-Refine | Verbal reflection và iterative refinement không cần weight update | Tin vào self-critique như ground truth |
| Voyager | Reusable skill library + environment verification | Minecraft-specific curriculum |
| ACE | Evolving playbook/context qua generate→reflect→curate | Rewrite context không có governance |
| LangGraph / OpenAI Agents / Microsoft Agent Framework | Durable HITL, handoff/supervisor, sequential/concurrent orchestration | Framework-specific state model thành core contract |
| Agent Lightning | Trajectory-based optimization/RL về sau | Bắt đầu platform bằng RL/fine-tuning |

# 5. Target Architecture

*Tách execution, context, learning và business để mỗi phần có lifecycle riêng.*

```text
CLIENT / API / UI
                               |
                    +----------v----------+
                    | Application Layer   |
                    +----------+----------+
                               |
          +--------------------v--------------------+
          |            AGENT OS RUNTIME             |
          |                                         |
          | Kernel: Registry | Plugins | Scope      |
          |        Events   | Identity | Lifecycle  |
          +-----------+--------------------+--------+
                      |                    |
              +-------v------+      +------v-------+
              | Execution    |      | Context      |
              | Agent/Graph  |      | Assembly     |
              | Tools/Model  |      | Budget       |
              +-------+------+      +------+-------+
                      |                    |
          +-----------v--------------------v--------+
          | Durable Data / Memory / Knowledge       |
          | Events | Runs | Checkpoints | Artifacts |
          | L0-L3 | Skills | Wiki | CodeGraph       |
          +--------------------+---------------------+
                               |
                  +------------v-------------+
                  | Improvement + Governance |
                  | Eval → Reflect → Propose |
                  | Validate → Approve       |
                  | Version → Canary/Rollback|
                  +--------------------------+
```

*Hình 1 — High-level Agent OS architecture*

## 5.1 Planes và dependency direction

Dependency phải đi từ Application → Agent OS interfaces → providers/infrastructure. Domain không import LLM SDK; Agent Core không import domain entity. Infrastructure implement interfaces từ bên trong hệ thống.

```text
Application / Domain
        |
        v
Agent OS interfaces <----- Provider implementations
        |                         |
        +-------------------------+
                  |
             Infrastructure
```

# 6. Python Micro-Kernel

*Kernel phải nhỏ, ổn định và đủ mạnh để mọi capability còn lại có thể thay thế.*

## 6.1 Kernel responsibilities

| Component | Responsibility |
| --- | --- |
| ServiceRegistry | Bind typed service contract → provider implementation; resolve dependency. |
| PluginManager | Discover/load/unload plugins, dependency ordering, reversible resources. |
| Scope | Per-agent/per-run capability visibility và overrides. |
| EventBus | Live observation/interception events; không thay durable event store. |
| Lifecycle | Startup/shutdown, AsyncExitStack, health và provider cleanup. |
| ExecutionIdentity | Immutable tenant/team/user/agent/session/run identity. |

## 6.2 Python implementation primitives

- `typing.Protocol` cho public service contracts.

- `contextlib.AsyncExitStack` cho reversible resource/plugin lifecycle.

- `asyncio.TaskGroup`, `asyncio.timeout`, `Semaphore` cho structured concurrency.

- `contextvars` cho trace/scope propagation, nhưng authorization vẫn dựa trên immutable identity.

- `importlib.metadata.entry_points()` cho external plugin discovery.

- Pydantic/dataclasses cho typed payload, config và schema boundary.

```python
from typing import Protocol, AsyncIterator

class ModelProvider(Protocol):
    async def stream(
        self, request: "ModelRequest", ctx: "ModelContext"
    ) -> AsyncIterator["ModelEvent"]:
        ...

class EventStore(Protocol):
    async def append(self, event: "SessionEvent") -> None: ...
    async def read(self, session_id: str, after_seq: int = 0): ...
```

## 6.3 Plugin contract

```python
class Plugin(Protocol):
    name: str
    requires: set[type]

    async def setup(self, ctx: "KernelContext") -> None:
        """Register providers, tools, hooks and resources."""

# pyproject.toml
[project.entry-points."agent_os.plugins"]
openai = "agent_openai:plugin"
tencent_memory = "agent_memory_tencent:plugin"
```

> Design choice  Không dùng load order ngầm làm behavior. Plugin declaration có dependencies và interception priority explicit để dễ debug và test.

# 7. Execution Model: Session, Run, Turn, Step

*Tách conversation history khỏi execution state để resume và scale được.*

| Concept | Meaning | Durable? |
| --- | --- | --- |
| Session | Conversation stream / interaction history | Yes |
| Run | Một execution instance của agent/workflow | Yes |
| Turn | Một user/input turn, có thể gồm nhiều steps | Yes |
| Step | Một model request + zero/many tool calls | Yes |
| Checkpoint | Workflow/run resumable state | Yes |
| AgentHandle | Live control surface: send/steer/cancel/wait | No; can be rebuilt |

## 7.1 Default ReAct loop

```text
turn.started
  -> context.assembled
  -> step.started
     -> model.requested
     -> model.delta*
     -> model.completed
     -> tool.called*
        -> validate -> authorize -> approve? -> execute -> normalize
     -> tool.completed*
  -> step.completed
  -> continue if model/tools require another step
turn.completed
```

## 7.2 Replaceable agent drivers

- ReactDriver

- PlanExecuteDriver

- WorkflowDriver

- ComputerUseDriver

- VoiceRealtimeDriver

- BatchDriver

```python
class AgentDriver(Protocol):
    async def run(
        self, ctx: "AgentContext"
    ) -> AsyncIterator["AgentEvent"]:
        ...
```

# 8. Multi-Agent & Workflow Orchestration

*Multi-agent là execution pattern; chỉ dùng khi decomposition mang lại giá trị rõ ràng.*

## 8.1 Patterns phải hỗ trợ

| Pattern | Khi dùng | Ví dụ business |
| --- | --- | --- |
| Sequential | Output A bắt buộc là input B | Analyze OKR → diagnose → propose → review |
| Parallel fan-out/fan-in | Subtasks độc lập | OKR + Tasks + Calendar cùng chạy rồi merge |
| Supervisor / agents-as-tools | Một agent giữ context và gọi specialists | Chief of Staff gọi OKR/Planning/Task agents |
| Handoff | Control chuyển hẳn sang specialist | General agent → OKR coach |
| Critic/Reviewer | High-value output cần kiểm tra | Weekly plan → domain reviewer |
| Dynamic graph | Agent quyết định nhánh/worker runtime | Research only when missing evidence |

## 8.2 Example parallel weekly review

```text
+--> OKR Analyst -----+
                           |                     |
Weekly Review --> Collect -+--> Task Analyst ----+--> Synthesizer --> Planner
                           |                     |
                           +--> Calendar Agent --+          |
                                                          v
                                                     Human Approval
```

## 8.3 Workflow node contract

```python
class WorkflowNode(Protocol):
    async def execute(
        self, ctx: "WorkflowContext", input: "NodeInput"
    ) -> "NodeOutput": ...

# Built-in nodes
AgentNode, ToolNode, FunctionNode, BranchNode, ParallelNode, JoinNode,
LoopNode, ApprovalNode, WaitNode, SubWorkflowNode, RemoteAgentNode
```

## 8.4 Rule of economy

> Default  Single-agent fast path trước. Chỉ tách multi-agent khi có parallelism, specialist context, risk separation hoặc independent review. Không biến mỗi request thành “agent committee”.

# 9. Tool Runtime, Policy & Sandbox

*Tool calling là side-effect boundary và phải deterministic, auditable, cancellable.*

```text
Model ToolCall
    |
    v
Schema validation
    v
Capability / ACL check
    v
Policy + rate limit
    v
Human approval?
    v
Sandbox / timeout / cancellation
    v
Execute
    v
Output schema validation
    v
Redaction / normalization
    v
tool.completed event
```

## 9.1 Tool interface

```python
class Tool(Protocol):
    spec: ToolSpec

    async def execute(
        self, input: dict, ctx: "ToolContext"
    ) -> dict: ...

@dataclass(frozen=True)
class ToolSpec:
    name: str
    input_schema: dict
    output_schema: dict
    timeout_s: float | None
    concurrency: Literal["parallel", "exclusive"]
    permissions: frozenset[str]
```

MCP chỉ là protocol adapter. MCP Tool → canonical ToolSpec → Tool Runtime. Core không dùng MCP làm internal abstraction cho tất cả tools.

# 10. Context Assembly & Token Budget

*Agent intelligence phụ thuộc context quality nhiều hơn việc nhồi thêm token.*

## 10.1 Context assembly order

```text
1. Platform policy
2. Agent instructions
3. Stable persona / identity memory (L3)
4. Scenario navigation / working context (L2)
5. Active skills
6. Dynamic atomic recall (L1)
7. External knowledge / artifacts
8. Compacted + recent session history
9. Current user input
10. Tool schemas
```

## 10.2 ContextFragment contract

```python
@dataclass(frozen=True)
class ContextFragment:
    source: str
    content: str
    priority: int
    stable: bool
    token_estimate: int
    provenance: dict[str, object]
```

Memory/Skill/Knowledge providers không tự nối prompt. Mỗi provider trả ContextFragment; ContextAssembler quyết định thứ tự, quota, dedup, truncation và provenance.

## 10.3 Budget example

| Budget bucket | Indicative share |
| --- | --- |
| System/policy/stable context | 10-15% |
| Skills | 5-10% |
| Dynamic memory/knowledge | 10-20% |
| Session/history | 35-55% |
| Tool results/artifacts | 10-20% |
| Reserved model output | explicit reserve |

# 11. Memory, Skills & Knowledge Plane

*Memory là một lifecycle, không phải một bảng embeddings.*

## 11.1 Layered memory model

| Layer | Meaning | Primary use |
| --- | --- | --- |
| L0 Conversation / Episodic | Raw messages, selected tool observations, source/timestamp | Audit, exact recall, reprocessing |
| L1 Atomic / Semantic | Facts, preferences, constraints, decisions, events | Dynamic per-turn recall |
| L2 Scenario | Project/cycle/work context aggregated from related facts | Fast context bootstrap |
| L3 Persona/Core | Stable identity, long-term preferences, recurring patterns | Stable system context |

## 11.2 Async memory write path

```text
turn.completed
      |
      +--> persist SessionEvent
      |
      +--> transactional outbox: memory.capture
                     |
                     v
                 persist L0
                     |
                  enqueue
                     v
                 L1 worker
                     v
                 L2 worker
                     v
                 L3 worker
```

> Critical path rule  Response không chờ L1/L2/L3 extraction. Chỉ L0 durable capture/outbox cần đảm bảo trước khi kết thúc turn nếu policy yêu cầu.

## 11.3 Retrieval

Baseline retrieval: lexical BM25/FTS + vector semantic search → Reciprocal Rank Fusion → optional rerank → ACL filtering by construction → item/character/token budget. Exact identifiers và technical terms thường cần lexical search; semantic similarity cần vector; hybrid là baseline phù hợp.

## 11.4 Skills = procedural memory

Skill không phải chat memory. Skill là reusable procedure có trigger, instruction, resources, validation, provenance và version lifecycle.

```text
SkillVersion
  id / version
  triggers
  instructions
  rules / examples
  resources
  validation_spec
  source_runs
  status: draft -> testing -> approved -> active -> deprecated
```

## 11.5 Knowledge providers

- Wiki/document knowledge: pages, links, sections, semantic retrieval.

- CodeGraph: symbols, definitions, callers/callees, dependency/impact paths.

- External RAG/web/database knowledge: adapter-specific but normalized by KnowledgeProvider.

- Knowledge content không nên bị trộn vào Chat Memory; Memory chỉ giữ references/provenance khi cần.

# 12. Learning & Improvement Plane

*Đây là differentiator chính: hệ thống càng dùng càng tốt nhưng vẫn audit, test và rollback được.*

## 12.1 Levels of improvement

| Level | Mechanism | Risk / Governance |
| --- | --- | --- |
| L0 Self-correction | Retry / fix tool input trong current run | Low; runtime policy |
| L1 Reflection | Tạo lesson từ success/failure | Low-medium; evidence required |
| L2 Memory learning | Persist/update facts/scenarios/persona | Approval tùy scope/sensitivity |
| L3 Skill learning | Create/patch reusable procedures | Evaluate + version + approval |
| L4 Workflow/prompt/policy optimization | Đề xuất graph/routing/prompt/tool policy | High; mandatory approval/canary |
| L5 Model optimization | SFT/RL/prompt optimizer trên trajectories | Very high; later phase |

## 12.2 Improvement lifecycle

```text
Trajectory / Outcome
        |
        v
     Evaluator
        v
     Reflector
        v
   Pattern Miner
        v
 Improvement Agent
        v
     Validator
        |
  +-----+-----+
  |           |
reject     Proposal
              |
              v
        Human / Policy Review
              |
          Approved Version
              |
            Canary
              |
       Measure / Rollback
```

## 12.3 ImprovementProposal

```python
@dataclass
class ImprovementProposal:
    id: UUID
    target_type: str     # memory|skill|prompt|workflow|policy|agent_config
    target_id: str
    current_version: str | None
    proposed_patch: dict
    rationale: str
    evidence: list[Evidence]
    source_runs: list[UUID]
    expected_benefit: str
    risks: list[str]
    evaluation: EvaluationResult | None
    status: str
```

## 12.4 Learning agents

| Agent | Question it answers |
| --- | --- |
| Evaluator | Kết quả tốt/xấu như thế nào theo business + quality metrics? |
| Reflector | Tại sao xảy ra và lesson nào có thể tổng quát hóa? |
| Curator | Lesson nên thành memory, skill, proposal hay bỏ qua/merge? |
| Pattern Miner | Có pattern lặp lại trên nhiều runs/users/teams không? |
| Improvement Agent | Patch cụ thể nào có thể cải thiện target? |
| Validator | Candidate có tốt hơn baseline trên eval/regression suite không? |

## 12.5 Safety invariant

> No self-modifying production core  Agent MAY propose, simulate và validate. Agent MUST NOT publish high-impact changes vào workflow/policy/business rule/kernel nếu không có approval policy. Business rule change mặc định chỉ là suggestion cho con người/developer.

# 13. Governance, Approval, Versioning & Rollout

*Learning chỉ có giá trị khi thay đổi có thể kiểm soát và đảo ngược.*

## 13.1 Approval classes

| Class | Examples | Default |
| --- | --- | --- |
| Auto-allowed | Retry, low-risk memory formatting, non-sensitive L1 extraction | Apply + log |
| Policy-gated | Memory update, personal preference, non-destructive tool call | Rule-based approval |
| Human required | Skill publish, workflow change, external write, delete, financial/actionable changes | Pause and request approval |
| Developer/admin required | Kernel/plugin/provider change, business rule change, security policy change | Code/config release process |

## 13.2 Version lifecycle

```text
Draft -> Evaluating -> Awaiting Approval -> Approved -> Canary -> Active
   |           |                |             |         |
   +->Rejected +->Failed        +->Rejected   +->Rollback/Deprecated
```

## 13.3 Canary metrics

- Task/business success metric.

- Human correction/rejection rate.

- Evaluator score and regression cases.

- Latency and token/cost delta.

- Tool error/retry rate.

- Policy/safety violations.

# 14. Durable Data Model & Event Sourcing

*Session history, execution state và business state phải tách rõ nhưng có correlation.*

## 14.1 Core durable stores

| Store | Source of truth for |
| --- | --- |
| SessionEventStore | What the agent/model/tools saw and did |
| RunStore | Execution status, workflow version, current checkpoint |
| CheckpointStore | Resumable graph/node state |
| Job/Lease Store | Background/distributed work and ownership |
| ArtifactStore | Files, binary outputs, generated reports, versions |
| MemoryService | Cross-session learned context; not session truth |
| VersionStore | Skills/prompts/workflows/policies/agent config versions |
| Proposal/Eval Store | Improvement lifecycle and evidence |

## 14.2 Canonical SessionEvent

```python
@dataclass(frozen=True)
class SessionEvent:
    event_id: UUID
    session_id: UUID
    run_id: UUID
    seq: int
    type: str
    timestamp: datetime
    actor: str | None
    payload: dict
    correlation_id: UUID | None
    causation_id: UUID | None
```

## 14.3 Event taxonomy

| Domain | Representative events |
| --- | --- |
| Runtime | run.started/completed/failed/cancelled |
| Turn/Step | turn.started/completed, step.started/completed |
| Context | context.fragment.selected, context.injected |
| Model | model.requested, model.delta, model.completed, model.usage |
| Tool | tool.called, tool.approval_requested, tool.completed, tool.failed |
| Workflow | workflow.node.started/completed/failed, checkpoint.saved |
| Memory | memory.capture_requested, memory.recalled, memory.updated |
| Learning | evaluation.completed, reflection.created, improvement.proposed/evaluated |
| Governance | approval.requested/decided, version.published/rolled_back |

## 14.4 Transactional outbox

Các side effect durable phải tránh “event saved nhưng background task mất”. Khi kết thúc turn, append event và insert outbox row trong cùng DB transaction; dispatcher publish tới worker queue sau commit. Pattern này đặc biệt cần cho memory capture, evaluation và scheduled improvement jobs.

# 15. Identity, Scope, Security & Tenancy

*Cross-tenant isolation phải được thiết kế từ query boundary, không phải filter sau retrieval.*

```python
@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    tenant_id: str
    team_id: str
    user_id: str
    agent_id: str
    session_id: UUID
    run_id: UUID
```

## 15.1 Policy rules

- Retrieval namespace được constrain bằng identity/ACL trước khi BM25/vector ranking.

- Tool capability resolution theo scope; không expose tool rồi hy vọng prompt sẽ không gọi.

- Secrets không vào model context trừ khi provider contract explicit cho phép và redact được.

- Side-effect tools có idempotency key, audit event và approval classification.

- Sandbox filesystem/process/network tách khỏi host runtime cho coding/browser/computer-use agents.

- Memory có provenance, owner, visibility, effective dates, confidence và supersession relation.

# 16. Business/Application Layer Contract

*Khi áp dụng Agent OS vào dự án mới, phần lớn công việc nằm ở Domain + Application, không phải sửa kernel.*

```text
API / UI
   |
Application Use Cases + Agent Applications
   |
Domain Model / Rules / Commands / Events
   |
Agent OS Runtime interfaces
   |
Infrastructure Providers
```

## 16.1 What business must provide

| Business artifact | Purpose |
| --- | --- |
| Domain entities/value objects | Truth model: Objective, KeyResult, Task, Cycle... |
| Business rules | Validation, calculation, invariants, authorization |
| Application commands/use cases | CreateObjective, PlanWeek, CompleteTask... |
| Domain tools | Typed capabilities Agent may call |
| Domain workflows | Deterministic graph for planning/review/approval |
| Business skills | Methodology/procedure: OKR quality, weekly review... |
| Domain evaluators | Metrics grounded in business outcomes |
| Integrations | Calendar/email/CRM/project systems as providers |

## 16.2 What business must NOT do

- Không subclass/patch kernel chỉ để thêm entity hoặc rule.

- Không để Agent gọi raw SQL/ORM mutations trực tiếp.

- Không encode hard business rule chỉ trong system prompt.

- Không đưa toàn bộ business database vào memory/RAG rồi xem đó là domain model.

# 17. Reference Business: OKRs + 12 Week Year + Tasks

*Ví dụ xuyên suốt để chứng minh business layer có thể cắm vào Agent OS mà core không đổi.*

## 17.1 Domain model

```text
Workspace
  +-- Vision / Annual Direction
  +-- TwelveWeekCycle
      +-- Objective
          +-- KeyResult
      +-- Project
          +-- Task
      +-- WeeklyPlan
          +-- Commitments
      +-- WeeklyReview
      +-- CycleReview
```

| Entity | Core fields / rule |
| --- | --- |
| TwelveWeekCycle | start_date, end_date, vision; fixed bounded cycle |
| Objective | owner, cycle, status, outcome statement |
| KeyResult | baseline, target, current, unit; measurable |
| Project | initiative linked to objectives/KRs |
| Task | status, priority, due date, project/KR links, dependencies |
| WeeklyPlan | week, commitments, capacity, planned score |
| WeeklyReview | execution score, KR movement, blockers, lessons |

## 17.2 Deterministic business rules

- Key Result phải measurable và có baseline/target/unit hợp lệ.

- Execution score = completed commitments / committed commitments; công thức nằm trong domain code.

- Objective/Task relationship và permission được validate trước persist.

- Cycle boundary, date validity, ownership và status transition không do LLM quyết định.

- LLM có thể đề xuất priority hoặc weekly commitments; command handler mới là authority để commit.

## 17.3 Domain tools

| Namespace | Representative tools |
| --- | --- |
| okr | list_objectives, create_objective, update_key_result, assess_alignment |
| cycle | get_current, create_cycle, get_week, close_cycle |
| planning | prepare_week, propose_week, commit_week, calculate_execution_score |
| task | list_open, create, complete, reschedule, delegate, link_to_key_result |
| review | collect_week_data, calculate_metrics, save_weekly_review |
| calendar | availability, schedule_block, move_block |

## 17.4 Business skills

- OKR Quality Review Skill — kiểm tra outcome focus, measurability, controllability, target quality.

- 12 Week Planning Skill — chuyển outcomes thành leading indicators, tactics và weekly commitments.

- Weekly Review Skill — score execution, diagnose misses, extract lessons, plan next week.

- Task Prioritization Skill — strategic alignment + urgency + blocking + effort + context fit.

- Root Cause Analysis Skill — phân biệt symptom, blocker, process problem và capability gap.

## 17.5 Agent roles

| Agent | Responsibility | Default relation |
| --- | --- | --- |
| Chief of Staff | Conversation owner, routing, synthesis, user relationship | Supervisor |
| OKR Coach | Objective/KR quality và strategic alignment | Specialist tool-agent |
| Planning Agent | 12-week/weekly plan, capacity, priorities | Specialist |
| Task Agent | Execution hygiene, dependencies, scheduling | Specialist |
| Reviewer | Independent critique of plans/reviews | Critic |
| Learning Agents | Evaluator/Reflector/Curator/Improvement/Validator | Background plane |

# 18. Business Workflows

*Các flow dưới đây minh họa khi dùng single-agent, parallel multi-agent và human approval.*

## 18.1 Daily “What should I do today?”

```text
User asks
  |
Chief of Staff
  +--> current cycle / OKRs
  +--> weekly commitments
  +--> open + blocked tasks
  +--> calendar availability
  +--> personal work-style memory
  |
  v
Rank + explain top actions
  |
User: "schedule them"
  |
Approval/policy check
  v
Calendar + Task commands
```

Fast path có thể là một Agent duy nhất gọi nhiều tools song song. Không cần spawn 4 agent nếu không có reasoning specialist riêng.

## 18.2 Weekly review — parallel

```text
+--> OKR Analyst --------+
                 |                        |
Collect snapshot -+--> Task Analyst -------+--> Review Synthesizer
                 |                        |
                 +--> Calendar Analyst ----+          |
                                                    v
                                           deterministic score
                                                    |
                                               Reflector
                                                    |
                                            next-week Planner
                                                    |
                                             Human approval
                                                    |
                                               commit plan
```

## 18.3 12-week cycle planning — flow

```text
Vision / constraints
      v
Strategic Planner
      v
OKR Coach
      v
Capacity / feasibility review
      v
12-week tactics decomposition
      v
Reviewer
      v
Human approval
      v
Create Cycle + Objectives + KRs + initial backlog
```

## 18.4 Continuous improvement example

```text
8 weekly reviews show:
- plans average 10-12 commitments
- execution score averages 58%
- 3 strategic items/week are usually completed
              |
              v
Pattern Miner + Reflector
              |
              v
Proposal: weekly_planning skill v4
"max 3 major strategic commitments"
              |
              v
Replay historical cases + regression eval
              |
              v
Human approval
              |
              v
10% canary -> measure execution/rejection -> active or rollback
```

# 19. Evaluation & Observability

*Không thể nói Agent “thông minh hơn” nếu không đo trajectory, business outcome và regressions.*

## 19.1 Evaluation hierarchy

```text
Business outcome
      > explicit human feedback
      > deterministic domain checks
      > independent evaluator agent
      > self-evaluation by execution agent
```

## 19.2 Metrics

| Area | Example metrics |
| --- | --- |
| Execution | success rate, retries, tool failures, cancellation, checkpoint resume |
| Quality | task rubric score, reviewer pass rate, human correction/rejection |
| Business | KR movement, weekly execution score, overdue reduction, plan adherence |
| Memory | precision@k, stale/contradiction rate, context tokens, outcome lift with memory |
| Multi-agent | parallel speedup, handoff error, duplicate work, synthesis quality |
| Cost/Latency | tokens/run, model cost, p50/p95 latency, tool wait time |
| Improvement | candidate win rate, rollback rate, regression count, canary delta |

## 19.3 Trace correlation

Mọi event/tool/model/workflow node cần correlation IDs để trả lời: “run này dùng workflow version nào, prompt/skill/memory nào, model nào, tool nào và business outcome sau đó là gì?”. Đây là prerequisite cho offline replay và improvement evaluation.

# 20. Public API & Python Contracts

*Public surface phải ổn định hơn provider implementations.*

## 20.1 Runtime API

```python
class AgentRuntime(Protocol):
    async def create(self, spec: AgentSpec, identity: ExecutionIdentity) -> AgentHandle: ...
    async def run(self, agent_id: str, input: UserMessage) -> AsyncIterator[AgentEvent]: ...
    async def resume(self, run_id: str) -> AsyncIterator[AgentEvent]: ...

class AgentHandle(Protocol):
    async def send(self, message: UserMessage) -> None: ...
    async def steer(self, message: UserMessage) -> None: ...
    async def cancel(self, reason: str) -> None: ...
    async def wait_idle(self) -> None: ...
```

## 20.2 Service contracts

| Contract | Key methods |
| --- | --- |
| ModelProvider | stream(request, ctx) |
| ToolRuntime | execute(call, ctx), execute_many(calls, ctx) |
| EventStore | append, append_batch, read, fork |
| MemoryService | capture, recall, search, forget |
| KnowledgeProvider | search, fetch, graph/structured operations as capabilities |
| SkillRegistry | resolve, list_versions, publish, deprecate |
| ArtifactStore | put, get, list_versions |
| WorkflowExecutor | start, resume, cancel, checkpoint |
| ApprovalService | request, decide, wait |
| ImprovementService | propose, evaluate, approve, rollout, rollback |

## 20.3 HTTP boundary example

```http
POST /v1/agents/{agent_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
POST /v1/approvals/{approval_id}/decision

GET  /v1/skills/{skill_id}/versions
POST /v1/improvements/{proposal_id}/approve
POST /v1/improvements/{proposal_id}/reject
POST /v1/versions/{version_id}/rollback
```

# 21. Storage, Deployment & Scaling

*Bắt đầu đơn giản nhưng giữ interface để scale không phá architecture.*

## 21.1 Recommended initial stack

| Need | MVP | Scale later |
| --- | --- | --- |
| Transactional data/events/runs | PostgreSQL | PostgreSQL HA/partitioning |
| Vector search | pgvector | Qdrant/Milvus/OpenSearch if justified |
| Lexical search | Postgres FTS/BM25-like provider | OpenSearch/Elastic if needed |
| Artifacts | S3/MinIO | Object storage/CDN |
| Queue/jobs | Postgres outbox + worker | Redis/NATS/Kafka/Temporal-like provider |
| Cache/leases | Postgres/advisory locks where enough | Redis |
| Telemetry | OpenTelemetry | Collector + tracing/metrics backend |

## 21.2 Service topology

```text
API / WebSocket Gateway
          |
          +--> Agent Runtime workers
          |       +--> Model APIs
          |       +--> Tool/Sandbox providers
          |
          +--> Workflow/Job workers
          |
          +--> Memory workers (L1/L2/L3)
          |
          +--> Evaluation/Improvement workers
          |
          +--> PostgreSQL / Object Store / Queue
```

## 21.3 Stateless runtime target

Runtime process chỉ giữ live handles/cache ngắn hạn. Durable run/checkpoint/job state nằm ngoài process, để worker crash/redeploy không mất execution. Background memory/improvement pipelines cũng dùng durable task queue + leases.

# 22. Recommended Python Repository Structure

*Package boundaries mirror architecture boundaries, không mirror framework names.*

```text
src/
  agent_os/
    kernel/            # registry, plugins, scope, identity, lifecycle
    runtime/           # agents, drivers, inbox, cancellation
    session/           # durable events, projections, snapshots
    models/            # model vocabulary + provider contracts
    tools/             # spec, registry, execution, policy
    context/           # fragments, assembler, budget
    workflow/          # graph, nodes, executor, checkpoints
    memory/            # memory service interfaces/adapters
    knowledge/         # wiki/codegraph/knowledge contracts
    skills/            # skill spec, registry, routing, versions
    artifacts/
    jobs/
    sandbox/
    evaluation/
    reflection/
    improvement/
    governance/
    telemetry/

  business/
    okr/
    twelve_week/
    tasks/
    planning/

  application/
    agents/
    workflows/
    use_cases/
    api/

providers/
  model_openai/
  model_google/
  model_anthropic/
  memory_tencent/
  memory_postgres/
  tool_mcp/
  sandbox_docker/
```

# 23. Implementation Roadmap

*Ưu tiên một vertical slice hoạt động end-to-end trước khi mở rộng multi-agent và learning automation.*

| Phase | Scope | Exit criteria |
| --- | --- | --- |
| 0 — Contracts | Core protocols, event vocabulary, identity/scope, ADRs | Stable interfaces + tests |
| 1 — Single Agent Core | Model streaming, ToolRuntime, EventStore, ContextAssembler, ReactDriver | Agent runs/tools/replay work |
| 2 — Durable Production | Postgres, Run/Checkpoint, approval, sandbox, OTel, artifacts | Crash/resume + audit |
| 3 — Business Vertical | OKR/12WY/Tasks domain + tools + daily/weekly flows | Useful end-to-end product |
| 4 — Memory | Tencent provider first, L0 capture, L1-L3 recall, context budgets | Cross-session improvement measurable |
| 5 — Multi-Agent Graph | Parallel/supervisor/reviewer/workflow graph | Weekly review graph + checkpoints |
| 6 — Improvement Plane | Eval/reflection/proposal/version/approval/canary | Skill improvement lifecycle works |
| 7 — Scale / Advanced learning | Distributed workers, richer knowledge, experiments, optional RL/SFT | Only after data/evals justify |

## 23.1 MVP “golden path”

```text
User asks: "Hôm nay tôi nên làm gì?"
    |
Single Chief-of-Staff Agent
    |
parallel tool reads: OKR + weekly plan + tasks + calendar
    |
Context + memory
    |
recommendation with rationale
    |
user approves scheduling
    |
Task/Calendar command executes
    |
SessionEvent + business event persisted
    |
L0 capture -> background memory
    |
weekly evaluator later creates improvement proposal
```

# 24. Risks, Trade-offs & Mitigations

*Agent OS dễ over-engineer; mỗi subsystem phải có lý do và measurement.*

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Over-engineering before product fit | Slow delivery | Vertical slice first; interfaces yes, distributed implementation later |
| Too many agents | Cost/latency/context fragmentation | Single-agent default; spawn only when benefit measurable |
| Memory hallucination/staleness | Wrong decisions reinforced | Provenance, confidence, supersedes, evaluation, selective approval |
| Self-improvement drift | System gets worse over time | Proposal-only, offline eval, human approval, canary, rollback |
| Prompt/plugin hidden behavior | Hard debugging | Explicit pipelines, event log, version IDs, typed contracts |
| Cross-tenant data leak | Critical security issue | Identity-scoped queries before retrieval/ranking, ACL at provider boundary |
| Framework lock-in | Migration cost | Provider-neutral public contracts; adapters for ADK/Tencent/etc. |
| Long-running state loss | Broken workflows | Run/Checkpoint/Job durable stores + idempotency |

# 25. Architecture Decision Summary

*Các quyết định nên được coi là baseline ADR cho implementation.*

| Decision | Choice |
| --- | --- |
| Primary language | Python 3.12+ |
| Kernel | Custom micro-kernel inspired by DeepSeek Harness; no Cordis port |
| Workflow | Custom graph/runtime contracts inspired by ADK 2.0; ADK optional adapter |
| Session truth | Append-only event log + projections/snapshots |
| Durable execution | Separate Run/Checkpoint/Job stores |
| Memory | MemoryService abstraction; TencentDB provider first; native provider optional later |
| Retrieval | Hybrid lexical + vector + fusion + context budget |
| Skills | Versioned procedural memory, separately governed from memory |
| Multi-agent | Sequential/parallel/supervisor/handoff/critic; single-agent default |
| Improvement | Evaluate → Reflect → Propose → Validate → Approve → Canary/Rollback |
| Business integration | Domain/Application Layer; tools call application commands, not raw DB |
| Storage MVP | PostgreSQL + pgvector + object storage; queue scales later |
| Security | Identity + scope + policy at capability/retrieval boundaries |

> Final recommendation  Xây Agent OS như một “runtime + learning platform”. OKR/12 Week Year/Tasks là application đầu tiên để kiểm chứng architecture. Nếu một business capability không generic, nó phải nằm ở Domain/Application; chỉ promote vào Agent OS khi có ít nhất hai domain cần cùng primitive.

# 26. Definition of Done for Agent OS v1

*Một baseline đủ tốt để gọi là Agent OS core thay vì chatbot framework.*

- Có thể tạo/run/resume/cancel một agent bằng public runtime contract.

- Model/tool execution streaming, cancellable, policy-controlled và fully traced.

- Mọi model-visible context có provenance và reconstructable từ event/data version.

- Session replay + snapshot + durable Run/Checkpoint hoạt động sau process restart.

- Workflow graph hỗ trợ sequential, parallel, branch, loop và approval node.

- Business tools không bypass Domain/Application validation.

- Memory provider có capture/recall/forget; L0→L1/L2/L3 chạy background.

- Skill registry có version lifecycle và provenance.

- Improvement proposal có evidence, evaluation, approval, publish và rollback.

- Multi-tenant tests chứng minh không cross-scope retrieval/tool access.

- Business example hoàn thành daily planning + weekly review + improvement proposal end-to-end.

# A. Appendix — Suggested Event Vocabulary

*Tên event có thể thay đổi, nhưng taxonomy và durable/live distinction nên giữ.*

| Category | Events |
| --- | --- |
| Session/Run | session.created, run.started, run.resumed, run.completed, run.failed, run.cancelled |
| Turn/Step | turn.started, input.message, step.started, step.completed, turn.completed |
| Context | context.recall_requested, context.fragment.selected, context.injected |
| Model | model.requested, model.response_started, model.text_delta, model.reasoning_delta, model.tool_call_delta, model.completed, model.usage |
| Tool | tool.called, tool.authorized, tool.approval_requested, tool.started, tool.completed, tool.failed |
| Workflow | workflow.started, workflow.node.started, workflow.node.completed, workflow.node.failed, checkpoint.saved |
| Memory | memory.capture_requested, memory.l0_persisted, memory.recalled, memory.updated, memory.superseded |
| Evaluation | evaluation.requested, evaluation.completed, feedback.received, reflection.created, pattern.detected |
| Improvement | improvement.proposed, improvement.evaluated, improvement.approved, improvement.rejected |
| Governance | approval.requested, approval.decided, version.published, experiment.started, experiment.completed, version.rolled_back |

# B. Appendix — Reference Material

*Nguồn kiến trúc tham khảo; truy cập/đối chiếu trong quá trình thiết kế vào tháng 8/2026.*

| Reference | URL |
| --- | --- |
| Google ADK 2.0 | https://adk.dev/2.0/ |
| Google ADK Runtime Event Loop | https://adk.dev/runtime/event-loop/ |
| Google ADK Workflows | https://adk.dev/workflows/ |
| DeepSeek Harness Architecture | https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md |
| TencentDB Agent Memory | https://github.com/TencentCloud/TencentDB-Agent-Memory |
| Hermes Agent — Memory | https://hermes-agent.nousresearch.com/docs/user-guide/features/memory |
| Hermes Agent — Skills | https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/ |
| Reflexion | https://arxiv.org/abs/2303.11366 |
| Voyager | https://voyager.minedojo.org/ |
| ACE — Agentic Context Engineering | https://arxiv.org/abs/2510.04618 |
| LangGraph Interrupts / HITL | https://docs.langchain.com/oss/python/langgraph/interrupts |
| OpenAI Agents SDK — Multi-agent | https://openai.github.io/openai-agents-python/multi_agent/ |
| OpenAI Agents SDK — Human in the loop | https://openai.github.io/openai-agents-python/human_in_the_loop/ |
| Microsoft Agent Framework — Orchestrations | https://learn.microsoft.com/agent-framework/workflows/orchestrations/ |
| Agent Lightning | https://www.microsoft.com/en-us/research/project/agent-lightning/ |

## B.1 Interpretation note

Các reference trên được dùng để rút primitive/architecture pattern, không phải cam kết compatibility hoặc endorsement. Public Agent OS contracts phải độc lập để có thể thay provider/framework theo thời gian.

**— End of Specification v0.1 —**
