# Blueprint: Rewrite COSA theo AI Agent OS Master Architecture (big-bang, literal layout)

## Context

`markdown/AI_Agent_OS_Master_Architecture.md` là bản hợp nhất (2026-08-22) toàn bộ các phân tích trước đó (ADK, DeepSeek Harness, TencentDB Memory, Skill Ecosystem, Encore vs FastAPI...) thành một kiến trúc "AI Agent OS" tham chiếu, độc lập với bất kỳ dự án cụ thể nào.

Người dùng yêu cầu: phân tích kỹ tài liệu này đối chiếu với codebase COSA hiện tại (javis-saas), và đề xuất hướng điều chỉnh — **tự do hoàn toàn khỏi CLAUDE.md hiện tại trong lúc brainstorm**. Sau khi trình bày 3 hướng (bổ sung có chọn lọc / làm sạch tài liệu trước / rewrite literal), người dùng chọn:

- **Rewrite literal theo layout Master doc** (không phải bổ sung tăng dần lên cấu trúc hiện có).
- **Big-bang** — thiết kế như viết lại từ đầu, không bị ràng buộc bởi code hiện tại; việc migrate tính sau.
- **Có Encore** cho Business Services layer (TypeScript, không dùng Go), đúng khuyến nghị nguyên bản của Master doc, chấp nhận thêm một stack ngôn ngữ mới bên cạnh Python.

Mục tiêu của tài liệu này: một **blueprint kiến trúc đích** (target architecture), dùng làm baseline thảo luận/thiết kế — không phải một PR migrate code ngay. Đây là artifact chính người dùng cần.

**Đối chiếu với hiện trạng COSA** (từ khảo sát `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` + `docs/agent-platform/*`, 2026-08-20→22): COSA hiện là hệ thống Python/FastAPI thuần, đã production-hoá phần lớn các khối tương đương (`cosa_core` = Agent Core, ADK = orchestration, DeepSeek Harness = runtime adapter, `GovernanceKernel` = policy/approval chokepoint, `business_core`/`platform_core` = business domain, 355 test file). Blueprint dưới đây **cố ý không bị ràng buộc** bởi các module/tên gọi đó — nhưng phần "Đối chiếu ngược" ở cuối sẽ chỉ rõ cái gì hiện có tương đương, cái gì là net-new, để người dùng cân nhắc khi chuyển từ blueprint sang kế hoạch thực thi thật.

---

## 1. Bắc đẩu tinh (North Star)

> AI Agent OS = một nền tảng nơi **reasoning có thể đổi model, capability có thể đổi qua skill, business state luôn ổn định, mọi hành động quan sát được, và mọi cải tiến lớn đều có bằng chứng + được con người quản trị**.

Nguyên tắc thiết kế xuyên suốt: **Core nhỏ, ổn định; năng lực mở rộng qua Skills, Tools, Memory, Business Services, Plugins.**

## 2. Repository layout (đích)

```text
ai-agent-os/
├── agentos/                     # Python — Agent Core / AI Runtime (kernel nhỏ, đổi chậm)
│   ├── core/                    # Agent, AgentRuntime, ContextBuilder, Planner, PolicyHooks
│   ├── agents/                  # role definitions: Planner/Executor/Reviewer/Specialist...
│   ├── skills/                  # registry, router, loader, trust, permissions, supply_chain
│   ├── tools/                   # ToolBinder, MCP client, typed tool schemas
│   ├── memory/                  # MemoryStore protocol + provider adapters (Tencent/pgvector/...)
│   ├── workflows/               # agent-side workflow primitives (không phải business workflow)
│   ├── improvement/             # capability gap detection, proposal, distillation
│   ├── evals/                   # agent/skill/workflow eval harness
│   └── observability/           # trace, event emit, cost tracking
│
├── services/                    # Encore (TypeScript) — Business Services, gộp theo cluster nghiệp vụ (xem AMENDMENT bên dưới, không phải 1 domain/service)
│   ├── identity/  ├── operations/  ├── commercial/  └── finance-legal/
│
├── skillpacks/                  # domain skill packages (nội bộ, đã duyệt)
│   ├── core/  ├── okr/  ├── twelve-week-year/  ├── tasks/  └── marketing/
│
├── plugins/                     # đơn vị mở rộng deployable (skills+tools+MCP+UI)
│   └── <plugin-name>/
│       ├── manifest.yaml
│       ├── skills/  ├── tools/  ├── resources/  └── ui/
│
├── registry/                    # Skill Registry state store, supply-chain artifacts (immutable)
├── evals/                       # eval suite definitions, fixtures, regression sets
├── apps/                        # web, admin (Experience Layer)
├── infra/                       # deploy, migrations, observability infra
└── docs/                        # ADRs, specs
```

Ghi chú: `agentos/` là **duy nhất** service Python; mọi business domain sống trong `services/` (Encore), không có domain logic nào lọt vào `agentos/core`.

> **AMENDMENT (2026-08-22, sau khi bàn về chi phí Encore.ts thật)**: layout "mỗi domain 1 service" ở trên đã bị thay bằng mô hình cluster — xem `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`. Lý do: mỗi thư mục trong `services/` là 1 deploy unit + 1 `SQLDatabase` riêng theo idiom Encore.ts (không có sub-module chia sẻ DB xuyên service) — literal "1 domain 1 service" với ~9+ domain của `business_core` nghĩa là 12-15+ DB/deploy unit riêng cho một hệ thống mới khởi động, trong khi nhiều domain (task↔OKR, invoice↔hợp đồng) giao dịch chéo liên tục. Quyết định gốc ở trên được giữ nguyên làm lịch sử; layout thực thi là bản amendment.

## 3. Kiến trúc theo lớp (layer-by-layer)

### 3.1 Agent Core (`agentos/core`, Python)
- Interface: `Agent.run(task, *, memory, skills, tools, policy) -> AgentResult` — reasoning chung, **không sở hữu business state**.
- `AgentRuntime` gồm: ContextBuilder, Planner, SkillRouter, ToolBinder, Executor, Reviewer, RetryManager, PolicyEngine, TraceRecorder.
- Central primitive: **AgentRun** (không phải "Agent") — trạng thái CREATED → RUNNING → WAITING_APPROVAL → COMPLETED/FAILED/CANCELLED.

### 3.2 Orchestration Runtime
- **Google ADK** qua `AdkCofounderOrchestrator` adapter — không gọi model/tool trực tiếp, luôn qua `ModelGateway`/`GovernanceKernel`.
- **DeepSeek Harness** qua `DeepSeekHarnessAdapter` — runtime thực thi, thin adapter, version-pinned, không fork nội bộ.
- Multi-agent flows hỗ trợ: sequential, parallel, delegation, debate/critic, supervisor — **không mặc định multi-agent**, ưu tiên single-agent → delegation → parallel khi cần thật.

### 3.3 Skill Ecosystem (`agentos/skills` + `skillpacks/` + `plugins/`)
- Canonical Skill Manifest (`apiVersion: agentos.ai/v1, kind: Skill`) — id/version/publisher/source(commit-pinned)/capability/runtime/permissions/risk/trust/quality.
- Lifecycle: DISCOVERED → IMPORTED → SCANNED → VERIFIED → STAGED → ACTIVE → DEPRECATED → QUARANTINED → REJECTED.
- Trust tiers: T0 internal (trusted) → T1 official (verified) → T2 community (sandbox/scoped) → T3 unknown (disabled) → T4 rejected (quarantined).
- Supply chain bắt buộc: DISCOVER → FETCH → PIN VERSION (commit sha, không `ref: main`) → NORMALIZE → STATIC SCAN → SEMANTIC REVIEW → PERMISSION ANALYSIS → EVAL → APPROVAL → STORE IMMUTABLE → INSTALL → SANDBOX → STAGE → PROMOTE → OBSERVE.
- Skill Router: intent → required capability → registry search → policy filter → trust filter → compatibility → semantic ranking → cost/risk ranking → select. Score = Relevance + Trust + EvalQuality + HistoricalSuccess + BusinessFit − Cost − Risk − Latency.
- Progressive disclosure 3 cấp: metadata → SKILL.md → resources/templates/schemas. Không load toàn bộ catalog vào context.
- `awesome-agent-skills` = external discovery source only, không phải runtime dependency; không auto-grant permission, không auto-promote external skill.

### 3.4 Tool / MCP Layer (`agentos/tools`)
- Tool = atomic capability, typed, narrow, observable, permission-scoped, idempotent khi có thể, timeout/retry, structured output.
- Hỗ trợ song song: native tools, MCP tools, REST/GraphQL, CLI adapter, internal RPC. MCP là chuẩn tích hợp, **không thay thế business service**.

### 3.5 Business OS (`services/`, Encore TypeScript)
- Sở hữu business state thật: Identity (Workspace/tenant, Auth/Session, WorkforceMember/Organization), Operations (Tasks, OKR, 12-Week-Year, Initiative, Projects, Workflow), Commercial (CRM, Sales, Marketing, Billing), Finance-Legal (Finance, Legal, Validation/Evidence chain, Regulations) — 4 cluster service, không phải 1 service/entity (xem AMENDMENT §2).
- Typed API, service boundary rõ, event/pub-sub, background jobs, production observability — đúng thế mạnh Encore.
- Agent Core **không thao tác DB business trực tiếp** — luôn qua Tool Adapter → Encore Business API.
- Business workflow = deterministic state machine (vd `invoice: approved → sent → paid`); **không dùng LLM thay state machine** cho flow rõ ràng.
- FK xuyên cluster (vd Task → Workspace) không còn là DB constraint thật (mỗi cluster 1 `SQLDatabase` riêng) — trở thành tham chiếu logic, validate qua Encore internal API call. Chi tiết: `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`.

### 3.6 Memory & Knowledge (`agentos/memory`)
- `MemoryStore` protocol (put/search/delete/consolidate) — backend thay được (TencentDB / pgvector / Qdrant / Redis...), Agent Core không biết backend cụ thể.
- 5 loại: Working (run hiện tại), Episodic (lịch sử sự kiện), Semantic (fact chuẩn hoá), Procedural (cách làm hiệu quả), Organizational (tri thức chung).
- Retrieval pipeline: task → query gen → scope filter → semantic retrieval → recency/importance ranking → policy filter → compression → context.
- Consolidation lifecycle: raw events → episode → summary → fact extraction → semantic memory → archive.
- **Memory ≠ nguồn sự thật cho business state** (task status, invoice, OKR score...) — business state luôn ở `services/`.
- Knowledge (docs/wiki/policy/manual/spec) tách biệt Memory: ingest → parse → chunk → metadata → embed → index → retrieve.

### 3.7 Governance (`agentos/core/policy` + registry approvals)
- Permission classes: READ_LOCAL, WRITE_WORKSPACE, READ_NETWORK, EXTERNAL_WRITE, SEND_MESSAGE, MODIFY_BUSINESS_DATA, DEPLOY, EXECUTE_CODE, ACCESS_SECRET, DELETE_DATA, FINANCIAL_ACTION.
- Policy Engine: agent intends action → ALLOW / DENY / REQUIRE_APPROVAL — check **trước** mọi tool/action, enforced bằng code, không phải bằng prompt.
- Approval object chuẩn hoá (id/action/subject/requester/reviewer/status/reason), áp dụng cho: deploy, promote_skill, send communication, delete, financial operation, policy change, external integration.
- Human-governed autonomy: agent tự phân tích/đề xuất/thử nghiệm/staging/đánh giá; hành động rủi ro cao luôn cần approval.
- 6-level business autonomy: L0 Observe → L1 Recommend → L2 Draft → L3 Execute Scoped → L4 Execute w/ Approval → L5 Autonomous (policy-bounded). MVP default: read/analysis/draft = auto; internal update = scoped; external comm/delete/finance/deploy = approval.

### 3.8 Evaluation (`agentos/evals`)
- 5 lớp: Model Eval, Agent Eval, Skill Eval, Workflow Eval, Business Outcome Eval.
- Agent Eval metric: goal completion, plan quality, tool accuracy, retry count, cost, latency, policy compliance, human acceptance.
- Business Outcome Eval gắn với outcome thật (CTR, conversion, CAC, KR completion...), không chỉ LLM-judge.

### 3.9 Observability (`agentos/observability`)
- Lớp: trace, log, metric, event, cost, audit, eval — mỗi run có trace tree đầy đủ (Context Retrieval → Skill Search → Skill Execution → Tool Calls → Review → Final Output).
- Cost tracking theo token/model/tool/search/storage/workflow/skill, quy về cost-per-business-outcome.

### 3.10 Self-Improvement (`agentos/improvement`)
- Loop: observe → detect repeated failure → identify capability gap → search skill → evaluate candidates → recommend → **human approval** → stage → canary → promote.
- Improvement Hierarchy (ưu tiên theo thứ tự, core code là lựa chọn CUỐI CÙNG): Context/retrieval → Skill selection → Tool selection → Workflow → Prompt/instructions → Memory policy → Model choice → Business rule → Agent role → Core code.
- Skill Distillation: successful traces → detect pattern → extract procedure → draft SKILL.md → generate evals → sandbox → human approval → publish internal skill. Đây là cơ chế học tổ chức, hiện **hoàn toàn chưa tồn tại** trong COSA.

### 3.11 Model Layer
- `ModelProvider` protocol (generate/tool_call) — không hard-code provider vào domain logic.
- Model Routing theo reasoning complexity/latency/cost/tool-calling/context window/structured output/privacy (vd: cheap model → classification, strong model → planning, specialized → coding).

### 3.12 Data Architecture
```text
PostgreSQL      → business data, registry, workflow state, approvals
Vector Store    → semantic memory, knowledge retrieval, skill embeddings
Object Storage  → documents, artifacts, immutable skill packages
Event Bus       → domain events, improvement events
```

### 3.13 Security & Multi-tenant
- Threat model: prompt injection, tool poisoning, skill supply-chain attack, secret leakage, excessive permission, data exfiltration, malicious plugin, unsafe shell, cross-tenant data, business action abuse, model output injection.
- Sandbox bắt buộc cho: code execution, external skill, browser automation, file manipulation, unknown plugin — giới hạn network/filesystem/CPU/memory/time/secrets/process.
- `tenant_id` xuất hiện xuyên suốt: business data, memory, events, skill permissions, audit, secrets, workflow state.
- Secret: secret reference → policy check → scoped tool → secret dùng server-side, không inject thẳng vào agent.

## 4. Phased rollout (blueprint order, chưa phải kế hoạch thực thi)

```text
Phase 0  Baseline: interfaces, ADRs, entity model, event naming
Phase 1  Agent Core MVP: Python runtime, model adapter, tool calling, trace, single-agent loop
Phase 2  Business OS MVP: Tasks/OKR/12WY qua Encore, typed API, events, PostgreSQL
Phase 3  Memory: episodic/semantic, retrieval, consolidation
Phase 4  Skill Layer: manifest, registry, router, loader, skillpacks nội bộ, permissions
Phase 5  Marketing Skill Pack (domain skill pack pilot)
Phase 6  External Skill Supply Chain (awesome-agent-skills as discovery source)
Phase 7  Multi-Agent (delegation/parallel/supervisor)
Phase 8  Workflow & Approval (business + agent workflow, approval gates)
Phase 9  Evaluation & Observability (full trace tree, business outcome eval)
Phase 10 Self-Improvement (capability gap detection → distillation → canary → promote)
```
MVP tối thiểu (Phase 0-2 + slice của 3-4): Python Agent Core, PostgreSQL, 2-3 Encore business service, Tasks/OKR, memory tối giản, filesystem skills, skill registry, tool permissions, 1 agent + reviewer, workflow cơ bản, approval, tracing. **Không cần marketplace ngay.**

## 5. Đối chiếu ngược với COSA hiện tại (thông tin, không phải quyết định)

| Blueprint | Tương đương COSA hiện tại | Trạng thái |
|---|---|---|
| `agentos/core` (Agent Core, Python) | `backend/cosa_core` (runtime, governance, reliability) | Có, production, tên khác |
| Orchestration ADK adapter | `backend/workforce/agents/orchestration/adk/` | Có, production |
| DeepSeek Harness adapter | `backend/cosa_core/runtime/adapters/deepseek_harness.py` | Có, production, đã version-pin |
| Governance/Policy Engine | `backend/cosa_core/governance/kernel.py` (GovernanceKernel, chokepoint) | Có, production, khá sát blueprint §3.7 |
| Approval object | `agent_approvals` table + `approval_service.py` | Có |
| Skill Registry/Router/Loader | `backend/workforce/skills/` | Có nhưng **thiếu**: canonical manifest dual-file, lifecycle DISCOVERED→ACTIVE, trust tiers T0-T4, supply-chain pipeline, commit-pinning |
| `services/` (Encore, TypeScript) | `backend/business_core/`, `backend/platform_core/` (Python/FastAPI) | Khác stack hoàn toàn — đây là điểm khác biệt lớn nhất nếu theo blueprint literal |
| Memory layering (Working/Episodic/Semantic/Procedural/Org) | `agent_runtime/memory` + `workforce/memory/` (1 tầng, chưa tách) | Có nhưng chưa phân tầng đúng blueprint |
| Self-Improvement loop | *(không tìm thấy)* | **Net-new hoàn toàn** |
| Eval harness tổng quát | 2 DSPy program eval, chưa generic | **Gap lớn** |
| Observability full trace-tree | OpenTelemetry wired ở 3 điểm chokepoint (gate/model gateway/kernel), chưa full run trace-tree | Một phần |
| `MemoryStore`/`ModelProvider` protocol abstraction | Có `ModelGateway`, chưa có `MemoryStore` provider protocol tường minh (TencentDB tích hợp mới ở dạng markdown proposal, chưa code) | Một phần |

**Lưu ý về mức độ tin cậy của bảng trên**: các tài liệu `docs/agent-platform/{GAP_ANALYSIS,CURRENT_ARCHITECTURE,MIGRATION_MAP}.md` mà bảng này tham chiếu được lập 2026-08-17→21, trỏ đường dẫn cũ `backend/app/...` — đã bị extract sang `cosa_core`/`workforce` theo `COSA_CANONICAL_OWNERSHIP_MAP.md` (2026-08-20/22) và so sánh với một spec khác (`markdown/d1.md`), không phải Master Architecture doc này. Bảng trên dùng ownership map (nguồn mới nhất) làm căn cứ chính, nhưng nên coi là **định hướng**, không phải kiểm chứng dòng-code-chính-xác.

## 6. Điểm mâu thuẫn tường minh với CLAUDE.md hiện tại (ghi nhận, chưa giải quyết)

Theo yêu cầu "đối chiếu lại khi chốt design" — các điểm sau đây từ blueprint **trái với** quy tắc đang có trong `CLAUDE.md` của dự án, cần người dùng quyết định tường minh trước khi chuyển sang kế hoạch thực thi:

1. **Big-bang / đổi tên toàn bộ layout** trái với CLAUDE.md §1 ("smallest safe change") và §"Planning Before Execution" (khuyến khích incremental, không rewrite trừ khi plan yêu cầu rõ).
2. **Thêm Encore (TypeScript)** bên cạnh Python — CLAUDE.md hiện không nhắc Encore; đây là một stack ngôn ngữ hoàn toàn mới, tăng chi phí vận hành/tuyển dụng/CI so với hệ thống Python thuần đang chạy production với 355 test.
3. **Đổi tên module** (`cosa_core` → `agentos/core`, `workforce/skills` → `skillpacks/`...) có nguy cơ vi phạm §14 ("No Duplicate Architecture" — search trước khi thêm) nếu thực thi song song mà không dọn code cũ, tạo ra 2 hệ thống trùng vai trò như từng xảy ra với `Agent`/`AgentDefinition`/`AgentProfile` (2026-08-20).
4. **DeepSeek Harness / Google ADK** trong blueprint giữ nguyên vai trò đúng như CLAUDE.md §6/§6a đã quy định — **không mâu thuẫn**, đây là điểm hội tụ tự nhiên giữa Master doc và CLAUDE.md.

## 7. Rủi ro chính của hướng big-bang

- Chi phí migrate 355 test + toàn bộ production data model sang layout mới, xuyên suốt Governance/Approval/Sandbox đang enforce thật.
- Encore (TypeScript) đòi hỏi năng lực vận hành/CI/observability riêng, nhân đôi bề mặt kỹ thuật.
- "Big-bang" thường kéo dài hơn dự kiến và đóng băng feature work trong lúc migrate — cần quyết định rõ ràng có chấp nhận đánh đổi này hay không trước khi viết implementation plan.

## 8. Bước tiếp theo

Đây là tài liệu **phân tích + blueprint chiến lược**, chưa phải implementation plan. Sau khi người dùng xác nhận blueprint này đúng ý:
1. Lưu bản chính thức vào `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md` và commit.
2. Người dùng review bản spec đã lưu.
3. Nếu đồng ý tiến hành thực thi — invoke `superpowers:writing-plans` để tách blueprint thành các implementation plan theo từng Phase (0→10) ở mục 4, **không** thực thi Phase nào ở đây.
