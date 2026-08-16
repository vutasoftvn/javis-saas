# COSA — Đặc tả tổng thể kiến trúc Agentic Runtime, Governance và bộ mẫu triển khai

**Trạng thái:** Đặc tả tích hợp chính thức đề xuất  
**Đối tượng triển khai:** Claude Code / Codex / đội phát triển COSA  
**Ngôn ngữ:** Tiếng Việt  
**Mục tiêu:** Hợp nhất COSA thành một Founder Agentic Operating System thống nhất, tránh tiếp tục phát triển theo kiểu nhiều agent, prompt, workflow, tool và dashboard rời rạc.

---

# 0. Cách sử dụng tài liệu này

Tài liệu này là **nguồn sự thật kiến trúc chính — Architectural Source of Truth** cho giai đoạn tái cấu trúc COSA.

Claude Code phải đọc toàn bộ tài liệu trước khi sửa kiến trúc.

Trong tài liệu có ba mức yêu cầu:

## 0.1 BẮT BUỘC TRIỂN KHAI

Ký hiệu:

```text
[BẮT BUỘC]
```

Đây là các invariant, contract, state, policy hoặc test không được tự ý thay đổi.

## 0.2 MẪU CHUẨN

Ký hiệu:

```text
[MẪU CHUẨN]
```

Dùng làm implementation reference. Có thể thay tên trường hoặc tổ chức code nếu không thay đổi semantics.

## 0.3 GIAI ĐOẠN SAU

Ký hiệu:

```text
[SAU P0]
```

Không triển khai ngay nếu làm tăng scope hoặc gây chậm phần lõi.

---

# 1. Tóm tắt định hướng

COSA không nên tiếp tục phát triển bằng cách thêm:

- màn hình Agent;
- card hạ tầng;
- prompt editor trên dashboard chính;
- công cụ MCP riêng lẻ;
- workflow n8n lộ ra cho founder;
- lựa chọn model thủ công;
- các agent nhỏ cho từng thao tác.

Kiến trúc mục tiêu:

```text
Founder
  ↓
Chat / Voice
  ↓
COSA Companion
  ↓
Conversation Guard
  ↓
Intent Router
  ↓
Verb Router
  ↓
Domain Router
  ↓
Specialist Router
  ↓
Mission Orchestrator
  ↓
COSA Agent Kernel
  ↓
COSA Governance Kernel
  ↓
Tool / MCP / n8n / Agent Host
  ↓
Hệ thống thực tế
  ↓
Reality Verifier
  ↓
Outcome Certificate
  ↓
FINISH / LEARN
  ↓
COSA Brain
```

Nguồn ý tưởng đã tổng hợp:

```text
MyIris
→ quyết định loại hành vi hệ thống phải thực hiện

Agency Agents
→ chuyên gia nào nên đảm nhiệm và cách bàn giao

Awesome AI Anatomy
→ runtime production: context, budget, tool safety, sandbox, loop, event

Awesome AI Agents
→ governance, verification, evaluation và technology radar
```

COSA học các pattern trên nhưng **không phụ thuộc chúng làm core runtime**.

---

# 2. Định vị sản phẩm

COSA là:

> **Hệ điều hành AI dành cho Founder / One Person Company, giúp founder giao việc bằng chat hoặc voice, để hệ thống tự hiểu, lập mission, chọn chuyên môn, thực hiện an toàn, xác minh kết quả và học từ thực tế.**

Founder không cần biết:

- Agent nào đang chạy;
- Prompt nào được dùng;
- Skill nào được load;
- MCP server nào đang kết nối;
- n8n workflow ID;
- provider/model kỹ thuật;
- vector database;
- sandbox engine;
- DSPy;
- tool schema;
- system prompt.

Các nội dung trên chỉ xuất hiện ở:

```text
Admin
hoặc
Mission Inspector
```

---

# 3. Invariant quan trọng nhất: NO INTENT = NO TOOL

```text
[BẮT BUỘC]

NO INTENT
   =
NO CAPABILITY
   =
NO TOOL
```

Ví dụ:

| Người dùng nói | Hệ thống phải làm |
|---|---|
| “Chào COSA” | Trả lời hội thoại |
| “Cảm ơn nhé” | Trả lời hội thoại |
| “Bạn khỏe không?” | Trả lời hội thoại |
| “Hôm nay có gì cần tôi xử lý?” | Founder Brief |
| “Project mID thế nào?” | Đọc project mID |
| “Tìm 20 khách hàng cho COSA” | Tạo Sales Mission |
| “Gửi email cho 20 lead này” | Draft → Governance → Approval → Send |

**Không được để câu “chào” kích hoạt project lookup, CRM, file search hoặc bất kỳ tool nào.**

---

# 4. Conversation Guard — Bộ chặn hội thoại

`Conversation Guard` là lớp đầu tiên sau Companion.

Nhiệm vụ:

1. Nhận diện hội thoại thông thường.
2. Chặn accidental tool call.
3. Chuẩn hóa input.
4. Xác định message có actionable hay không.
5. Chỉ đưa sang Intent Router nếu thực sự cần.

[MẪU CHUẨN]

```json
{
  "conversation_mode": "converse",
  "should_route": false,
  "reason_code": "GREETING"
}
```

Ví dụ:

```text
Input:
"chào"

Output:
conversation_mode = converse
should_route = false
tool_calls = []
mission_created = false
```

---

# 5. Intent và Verb không phải cùng một khái niệm

## 5.1 Intent — Ý định

Trả lời:

> Người dùng muốn điều gì?

Ví dụ:

```text
sales.prospect_search
project.read_status
marketing.landing_page_review
build.modify_code
finance.cashflow_analysis
```

## 5.2 Verb — Kiểu hành động

Trả lời:

> Hệ thống phải thực hiện loại công việc nào?

Verb chuẩn:

```text
CONVERSE
SHAPE
INVESTIGATE
JUDGE
EXECUTE
FINISH
LEARN
```

---

# 6. Verb Registry

## 6.1 CONVERSE — Hội thoại

Dùng khi:

- chào hỏi;
- cảm ơn;
- trò chuyện;
- giải thích không cần tool.

Mặc định:

```text
Mission = none
Tool = none
```

---

## 6.2 SHAPE — Làm rõ / định hình

Dùng khi yêu cầu chưa đủ rõ.

Ví dụ:

- biến ý tưởng thành scope;
- phân tích yêu cầu;
- tạo spec;
- xác định đầu vào còn thiếu;
- hỏi founder điều thật sự cần thiết.

SHAPE thường là `stateful`.

---

## 6.3 INVESTIGATE — Điều tra / nghiên cứu

Dùng cho:

- market research;
- competitor research;
- prospect research;
- đọc project;
- thu thập nguồn;
- kiểm tra dữ liệu;
- phân tích evidence.

Thường chạy background/stateless.

---

## 6.4 JUDGE — Đánh giá

Dùng khi phải so với tiêu chí:

- lead có phù hợp không;
- landing page có tốt không;
- hợp đồng có rủi ro không;
- proposal có nên gửi không;
- chiến dịch có đạt chuẩn không.

---

## 6.5 EXECUTE — Thực thi

Dùng khi thay đổi state:

- tạo task;
- ghi CRM;
- sửa code;
- build;
- deploy;
- gửi email;
- đăng bài;
- chạy automation.

[BẮT BUỘC]

```text
EXECUTE
→ Governance Kernel
```

Không có ngoại lệ.

---

## 6.6 FINISH — Kết thúc có xác minh

Không được dùng chỉ vì agent tự nói:

```text
"I am done"
```

Flow:

```text
EXECUTE
→ EVIDENCE
→ VERIFY
→ FINISH
```

---

## 6.7 LEARN — Học

Dùng để:

- tạo Learning Candidate;
- phát hiện pattern;
- tạo Skill Candidate;
- ghi nhận failure pattern;
- lưu insight khách hàng;
- đề xuất cải thiện prompt.

LEARN không có quyền tự ghi mọi thứ vào long-term memory.

---

# 7. Prompt mặc định: Conversation Guard

[MẪU CHUẨN]

File đề xuất:

```text
prompts/cosa/conversation_guard.md
```

Nội dung:

```text
Bạn là Conversation Guard của COSA.

Mục tiêu:
- Nhận diện tin nhắn chỉ mang tính hội thoại.
- Ngăn COSA gọi tool khi người dùng chưa yêu cầu hành động hoặc thông tin cần truy xuất.
- Không suy diễn rằng lời chào có liên quan đến project, CRM, task hay dữ liệu công ty.

Quy tắc bắt buộc:
1. "chào", "hello", "hi", "cảm ơn", "ok", "ừ", "được", "tạm biệt" mặc định là CONVERSE.
2. Không được gọi tool chỉ vì session trước đang nói về một project.
3. Chỉ chuyển sang actionable khi người dùng có yêu cầu đủ rõ.
4. Nếu nội dung là hội thoại thông thường, trả:
   should_route=false.
5. Không tạo Mission cho greeting/acknowledgement.

Đầu ra JSON:
{
  "conversation_mode": "converse|actionable|ambiguous",
  "should_route": true|false,
  "reason_code": "string"
}
```

---

# 8. Prompt mặc định: Intent Router

File:

```text
prompts/cosa/intent_router.md
```

[MẪU CHUẨN]

```text
Bạn là Intent Router của COSA.

Nhiệm vụ:
Xác định ý định nghiệp vụ thật sự của người dùng.

Không chọn Agent.
Không chọn Tool.
Không thực thi.
Chỉ phân loại intent.

Nguyên tắc:
- Ưu tiên explicit intent.
- Không suy diễn từ context cũ nếu message hiện tại chỉ là greeting.
- Confidence thấp phải trả low confidence, không bịa intent.
- Intent phải theo namespace domain.action.

Đầu ra bắt buộc:
{
  "intent": "string",
  "confidence": 0.0,
  "actionable": true,
  "requires_context": false,
  "reason_code": "string"
}

Ví dụ:

Input:
"chào"

Output:
{
  "intent": "conversation.greeting",
  "confidence": 1.0,
  "actionable": false,
  "requires_context": false,
  "reason_code": "GREETING"
}

Input:
"project mID thế nào?"

Output:
{
  "intent": "project.read_status",
  "confidence": 0.98,
  "actionable": true,
  "requires_context": true,
  "reason_code": "EXPLICIT_PROJECT_STATUS"
}

Input:
"tìm cho tôi 20 khách hàng tiềm năng cho COSA"

Output:
{
  "intent": "sales.prospect_search",
  "confidence": 0.99,
  "actionable": true,
  "requires_context": true,
  "reason_code": "EXPLICIT_PROSPECT_SEARCH"
}
```

---

# 9. Prompt mặc định: Verb Router

File:

```text
prompts/cosa/verb_router.md
```

[MẪU CHUẨN]

```text
Bạn là Verb Router của COSA.

Bạn nhận:
- user request
- normalized intent
- context summary

Bạn trả đúng một verb:

CONVERSE
SHAPE
INVESTIGATE
JUDGE
EXECUTE
FINISH
LEARN

Quy tắc:

CONVERSE:
khi chỉ hội thoại.

SHAPE:
khi cần làm rõ, cấu trúc, tạo spec hoặc lập kế hoạch.

INVESTIGATE:
khi đọc, tìm, nghiên cứu, phân tích evidence.

JUDGE:
khi đánh giá theo tiêu chí.

EXECUTE:
khi thay đổi state, gọi tool mutating hoặc action bên ngoài.

FINISH:
chỉ dùng khi Mission đang ở giai đoạn xác minh kết quả.

LEARN:
khi tạo learning/pattern/skill candidate.

Đầu ra:
{
  "verb": "INVESTIGATE",
  "confidence": 0.97,
  "reason_code": "READ_ONLY_RESEARCH"
}
```

---

# 10. Prompt mặc định: Mission Planner

File:

```text
prompts/cosa/mission_planner.md
```

[MẪU CHUẨN]

```text
Bạn là Mission Planner của COSA.

Nhiệm vụ:
Chuyển một actionable request thành kế hoạch ngắn, có dependency, budget và tiêu chí hoàn thành.

Không tự ý:
- gửi email;
- deploy;
- chi tiền;
- sửa dữ liệu nhạy cảm;
- gọi external action nếu chưa qua Governance.

Kế hoạch phải:
1. Tối thiểu bước cần thiết.
2. Không tạo agent thừa.
3. Ưu tiên deterministic workflow nếu thứ tự đã biết.
4. Chỉ dùng AI ở bước có ambiguity/judgment.
5. Xác định evidence cần thu thập.
6. Xác định verification trước FINISH.

Đầu ra:
{
  "mission_type": "QUICK|MISSION|PROGRAM",
  "steps": [],
  "required_capabilities": [],
  "budget_hint": {},
  "verification_requirements": []
}
```

---

# 11. Domain Agent

Giữ ít Domain Agent:

```text
Founder Agent
Sales Agent
Marketing Agent
Finance Agent
Legal Agent
Build/Tech Agent
```

[SAU P0]

Có thể thêm:

```text
Support Agent
Operations Agent
HR Agent
```

Không tạo:

```text
Email Agent
Search Agent
CRM Agent
PDF Agent
Telegram Agent
```

Đó là capability/tool, không phải Domain Agent.

---

# 12. Specialist Profile

Specialist là internal profile.

Ví dụ Sales:

```text
Sales
├── Outbound Specialist
├── Discovery Specialist
├── Qualification Specialist
├── Pipeline Analyst
├── Deal Strategist
├── Proposal Specialist
└── Account Specialist
```

Marketing:

```text
Marketing
├── Market Research Specialist
├── Campaign Strategist
├── Content Specialist
├── Landing Page Specialist
├── SEO Specialist
└── Attribution Analyst
```

Finance:

```text
Finance
├── Accounting Specialist
├── Cashflow Analyst
├── FP&A Specialist
└── Finance Analyst
```

---

# 13. Agent Contract

[BẮT BUỘC]

Agent phải là contract có cấu trúc.

Không được chỉ là system prompt.

[MẪU CHUẨN]

```yaml
id: sales.outbound
version: 1

domain: sales
role: Outbound Strategist

mission:
  description: Tạo pipeline khách hàng tiềm năng phù hợp ICP.

allowed_verbs:
  - INVESTIGATE
  - SHAPE
  - JUDGE

capabilities:
  - icp_analysis
  - prospect_search
  - buying_signal_analysis
  - lead_qualification
  - outreach_planning

inputs:
  - product
  - market
  - icp
  - campaign_context

outputs:
  - prospect_list
  - signal_report
  - qualification_report
  - outreach_draft

quality_gates:
  - evidence_required
  - duplicate_check
  - icp_fit_required

tools:
  allow:
    - web.search
    - browser.extract
    - crm.read

  deny:
    - email.send

external_actions:
  email.send:
    approval_required: true

memory:
  read:
    - sales_learnings
    - customer_context

  write_candidate:
    - experiment_results

prompt:
  id: sales.outbound.system
  version: 1

skills:
  - sales.icp
  - sales.buying_signals
  - sales.outreach
```

---

# 14. JSON Schema mẫu cho Agent

[MẪU CHUẨN]

File:

```text
schemas/agent.schema.json
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "COSA Agent Contract",
  "type": "object",
  "required": [
    "id",
    "version",
    "domain",
    "role",
    "allowed_verbs",
    "capabilities",
    "tools"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "domain": {
      "type": "string"
    },
    "role": {
      "type": "string"
    },
    "allowed_verbs": {
      "type": "array",
      "items": {
        "enum": [
          "CONVERSE",
          "SHAPE",
          "INVESTIGATE",
          "JUDGE",
          "EXECUTE",
          "FINISH",
          "LEARN"
        ]
      }
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "tools": {
      "type": "object"
    }
  }
}
```

---

# 15. Canonical Agent Spec và Agent Compiler

Không duy trì thủ công:

```text
Claude Agent
Codex Agent
Gemini Agent
```

Tạo một Canonical Agent Spec.

```text
Canonical COSA Agent Spec
          ↓
     Agent Compiler
    ┌─────┼─────┐
    ▼     ▼     ▼
 Claude Codex Gemini
```

Cấu trúc:

```text
agents/
  founder/
  sales/
  marketing/
  finance/
  legal/
  build/
```

Compiler:

```text
compiler/
  claude_code.py
  codex.py
  gemini.py
  openclaw.py
```

[SAU P0]

Không ưu tiên Agent Compiler nếu làm chậm Runtime P0.

---

# 16. Mission là đơn vị công việc trung tâm

Cấu trúc:

```text
Goal
 ↓
Mission
 ↓
Task
 ↓
Workflow Run
 ↓
Action
```

Ví dụ:

```text
Goal:
Tăng pipeline qualified lead

Mission:
Tìm 20 khách hàng tiềm năng

Task:
1. Xác định ICP
2. Tìm company
3. Xác minh company
4. Enrich contact
5. Score
6. Save CRM
```

---

# 17. Mission Mode

## QUICK

Một task ngắn.

Ví dụ:

```text
Tóm tắt file.
```

## MISSION

Nhiều bước.

Ví dụ:

```text
Tìm 20 khách hàng.
```

## PROGRAM

Nhiều mission/milestone.

Ví dụ:

```text
Ra mắt COSA trong 6 tuần.
```

---

# 18. Mission-as-Code

Có hai loại Mission:

## Dynamic Mission

Sinh từ ngôn ngữ tự nhiên.

## Declared Mission

Workflow lặp lại hoặc high-value.

[MẪU CHUẨN]

File:

```text
examples/missions/sales-prospecting.yaml
```

```yaml
id: sales.prospecting.v1

name: Tìm và xác minh khách hàng tiềm năng

input:
  count:
    type: integer
    default: 20

  icp:
    required: true

steps:
  - id: research
    verb: INVESTIGATE
    capability: sales.prospect_search

  - id: verify_company
    verb: INVESTIGATE
    capability: company.verify
    depends_on:
      - research

  - id: qualify
    verb: JUDGE
    capability: sales.qualify
    depends_on:
      - verify_company

  - id: save_crm
    verb: EXECUTE
    capability: crm.upsert_lead
    depends_on:
      - qualify

budget:
  max_cost_usd: 0.30
  max_steps: 60
  max_duration_minutes: 20
  max_parallel_workers: 3

governance:
  external_action: false

finish:
  evidence_required: true
  verified_leads_required: 20
```

---

# 19. Mission Build mẫu

File:

```text
examples/missions/landing-page-build.yaml
```

[MẪU CHUẨN]

```yaml
id: build.landing_page.v1

name: Thiết kế và triển khai landing page

steps:
  - id: shape
    verb: SHAPE
    capability: requirements.shape

  - id: design
    verb: SHAPE
    capability: marketing.landing_structure
    depends_on:
      - shape

  - id: implement
    verb: EXECUTE
    capability: build.code
    depends_on:
      - design

  - id: test
    verb: JUDGE
    capability: build.test
    depends_on:
      - implement

  - id: verify
    verb: FINISH
    capability: deployment.verify
    depends_on:
      - test

  - id: deploy
    verb: EXECUTE
    capability: deployment.publish
    depends_on:
      - verify
    approval_required: true
```

---

# 20. Mission State Machine

[BẮT BUỘC]

```text
RECEIVED
↓
CLASSIFIED
↓
SHAPING
↓
READY
↓
QUEUED
↓
RUNNING
  ↳ WAITING_USER
  ↳ WAITING_APPROVAL
  ↳ WAITING_EXTERNAL
↓
VERIFYING
↓
COMPLETED
```

Terminal:

```text
COMPLETED
FAILED
CANCELLED
EXPIRED
DENIED
```

[BẮT BUỘC]

Mọi waiting state phải có:

```text
timeout
expiry policy
settle path
```

Không tồn tại `WAITING` vĩnh viễn.

---

# 21. Stateful và Stateless

Stateful:

- SHAPE;
- interactive clarification;
- voice question relay.

Stateless:

- INVESTIGATE;
- JUDGE;
- background EXECUTE;
- FINISH verification;
- LEARN.

Stateless không có nghĩa mất continuity.

Continuity nằm ở:

```text
Mission Context
Mission Ledger
Memory
Artifacts
Handoffs
```

---

# 22. Mission Ledger

[BẮT BUỘC]

Không dùng full chat làm state chính.

Các bảng đề xuất:

```text
missions
mission_steps
mission_events
mission_handoffs
mission_artifacts
mission_evidence
mission_verifications
mission_approvals
mission_outcomes
mission_budgets
```

Mission Ledger lưu:

- goal;
- plan;
- step;
- specialist;
- decision;
- tool call;
- approval;
- artifact;
- evidence;
- verification;
- outcome;
- learning candidate.

---

# 23. Handoff Contract

[MẪU CHUẨN]

File:

```text
examples/handoffs/sales-research-to-qualification.yaml
```

```yaml
handoff:
  mission_id: mis_001
  task_id: task_research

  from:
    specialist: sales.outbound

  to:
    specialist: sales.qualification

  completed:
    - Đã nghiên cứu 30 doanh nghiệp.
    - Đã loại 18 doanh nghiệp không đúng ICP.

  artifacts:
    - artifact://prospects.json

  evidence:
    - evidence://source_001
    - evidence://source_002

  decisions:
    - Chỉ giữ doanh nghiệp có từ 10 nhân sự trở lên.

  assumptions:
    - Thị trường ưu tiên Việt Nam.

  unresolved:
    - 4 contact chưa xác minh được email.

  risks:
    - 2 website có thể dùng dữ liệu nhân sự cũ.

  next_action:
    - Chấm điểm 12 account còn lại.
```

Agent sau không cần đọc toàn bộ conversation của agent trước.

---

# 24. COSA Agent Kernel

[BẮT BUỘC]

Core runtime thuộc COSA.

Không dùng:

```text
LangGraph
CrewAI
AutoGen
n8n
Claude Code
OpenClaw
```

làm core brain.

Có thể dùng chúng như:

```text
adapter
executor
tool provider
```

Module:

```text
cosa_runtime/
  conversation/
  routing/
  verbs/
  domains/
  specialists/
  missions/
  context/
  events/
  budget/
  stuck/
  tools/
  governance/
  evidence/
  verification/
  memory/
  providers/
  observability/
  features/
```

---

# 25. Middleware Pipeline

[BẮT BUỘC]

```text
Input
→ Conversation Guard
→ Intent
→ Verb
→ Domain
→ Specialist
→ Context Build
→ Budget Check
→ Plan
→ Tool Resolution
→ Tool Inspection
→ Approval
→ Sandbox
→ Execute
→ Observation
→ Stuck Check
→ Quality Gate
→ Evidence
→ Verify
→ Finish
→ Learn
```

Mỗi middleware:

- typed input;
- typed output;
- unit test;
- dependency declaration;
- không phụ thuộc ordering bằng comment.

---

# 26. Context Cascade

[BẮT BUỘC]

## L0 — Working Context

```text
current message
current mission
current task
recent results
```

## L1 — Lossless cleanup

Loại:

- duplicate;
- acknowledgement;
- completed verbose logs;
- stale UI state.

## L2 — Ephemeral

Chỉ tồn tại 1 turn:

```text
DOM
large logs
API dump
browser state
temporary search results
```

## L3 — Structured Summary

```yaml
goal:
completed:
decisions:
constraints:
evidence:
files:
pending:
risks:
next:
```

## L4 — Full Compaction

Chỉ khi bắt buộc.

---

# 27. Context Provenance

[MẪU CHUẨN]

```text
RAW
RETRIEVED
SUMMARIZED
COMPRESSED
INFERRED
```

Ví dụ:

```yaml
context_item:
  id: ctx_001
  source_type: COMPRESSED
  source_revision: ctx_rev_082
  confidence: medium
```

High-risk decision dùng context compressed:

```text
retrieve original evidence before execution
```

---

# 28. Context Pool Budget

[SAU P0 nhưng nên thiết kế schema ngay]

Ví dụ:

```text
25% Mission
20% Company Knowledge
15% Founder Memory
15% Customer Context
10% Skill
10% Learning
5% AntiPattern
```

Config:

```yaml
retrieve:
  mission: 5
  customer: 3
  knowledge: 4
  learning: 3
  anti_pattern: 2
  skill: 3
```

Sau đó rerank.

---

# 29. Memory Architecture

Hai loại bắt buộc:

## Curated Memory

- founder preference;
- company fact;
- decision;
- customer insight;
- confirmed learning;
- approved strategy.

## Raw Event History

- conversation;
- tool;
- mission;
- approval;
- workflow;
- verification;
- outcome.

Không biến toàn bộ chat thành long-term memory.

---

# 30. Memory Candidate Prompt

File:

```text
prompts/cosa/learn.md
```

[MẪU CHUẨN]

```text
Bạn là Learning Extractor của COSA.

Nhiệm vụ:
Từ Mission đã kết thúc, xác định nội dung nào đáng trở thành:
- learning;
- pattern;
- anti-pattern;
- skill candidate;
- company fact candidate.

Không ghi trực tiếp vào memory production.

Mỗi candidate phải có:
- loại;
- nội dung;
- evidence;
- confidence;
- phạm vi áp dụng;
- expiry/revalidation nếu cần.

Không lưu:
- secret;
- API key;
- token;
- dữ liệu nhạy cảm không cần thiết;
- suy đoán không có evidence.

Đầu ra:
{
  "candidates": []
}
```

---

# 31. Memory mẫu

```yaml
id: mem_001

type: customer_insight

key: customers_prefer_basic_plan
value: true

source:
  mission_id: mis_100
  campaign_id: cmp_021

confidence: 0.74

status: candidate

observed_at: 2026-08-16

revalidate_after_days: 90
```

---

# 32. COSA Brain

```text
Brain/
  Sources/
  Knowledge/
  Wiki/
  Memory/
  Decisions/
  Projects/
  People/
  Customers/
  Skills/
  Prompts/
  Agents/
  Workflows/
  Playbooks/
  Patterns/
  AntiPatterns/
  Experiments/
  Learnings/
  Templates/
```

---

# 33. Anti-Pattern Registry

[MẪU CHUẨN]

```yaml
id: antipattern.sales.bulk_email_without_signal

domain: sales

symptom:
  low_response_rate

evidence:
  - mission: mis_200
  - campaign: cmp_124

better_alternative:
  buying_signal_first

confidence: 0.87

status: confirmed
```

---

# 34. Tool Contract

[MẪU CHUẨN]

```yaml
id: crm.upsert_contact
version: 1

category: crm

mutating: true
external: false

permissions:
  - crm.write

risk: medium

approval:
  mode: policy

timeout_seconds: 30

idempotent: true

verification:
  type: database_state
  table: contacts
```

---

# 35. Tool Schema

File:

```text
schemas/tool.schema.json
```

[MẪU CHUẨN]

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "COSA Tool Contract",
  "type": "object",
  "required": [
    "id",
    "version",
    "mutating",
    "external",
    "risk"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "version": {
      "type": "integer"
    },
    "mutating": {
      "type": "boolean"
    },
    "external": {
      "type": "boolean"
    },
    "risk": {
      "enum": [
        "low",
        "medium",
        "high",
        "critical"
      ]
    },
    "idempotent": {
      "type": "boolean"
    }
  }
}
```

---

# 36. Tool Sentinel

[BẮT BUỘC]

Mọi tool call phải qua:

```text
PermissionInspector
ScopeInspector
SecretInspector
EgressInspector
InjectionInspector
RepetitionInspector
RiskInspector
BudgetInspector
```

Verdict:

```text
ALLOW
REQUIRE_APPROVAL
DENY
```

---

# 37. Governance Kernel

[BẮT BUỘC]

Độc lập với LLM.

Gồm:

```text
Identity
Permission
Scope
Policy
Risk
Approval
Secret Broker
Egress
Rate Limit
Audit
```

Không được để model tự quyết:

```text
"việc này có cần approval không?"
```

Approval do policy quyết định.

---

# 38. Policy mẫu: read-only

File:

```text
examples/policies/read-only.yaml
```

```yaml
id: policy.read_only

match:
  mutating: false

effect:
  allow

audit:
  enabled: true
```

---

# 39. Policy mẫu: internal write

```yaml
id: policy.internal_write

match:
  external: false
  mutating: true

rules:
  - require_permission: true
  - require_workspace_scope: true

effect:
  allow_if_rules_pass
```

---

# 40. Policy mẫu: external email

```yaml
id: policy.external_email

match:
  tool: email.send

rules:
  - recipient_source:
      allowed:
        - crm.approved_contact

  - max_recipients_per_run: 20

  - secret_access:
      mode: broker_only

effect:
  require_approval
```

---

# 41. Policy mẫu: deploy

```yaml
id: policy.deploy

match:
  capability: deployment.publish

rules:
  - tests_passed: true
  - verification_passed: true
  - founder_approval: true

effect:
  require_approval
```

---

# 42. Policy mẫu: financial action

```yaml
id: policy.finance_sensitive

match:
  domain: finance
  mutating: true

effect:
  require_approval

rules:
  - accounting_evidence_required: true
  - actor_role:
      allowed:
        - founder
        - admin
```

---

# 43. Policy mẫu: admin-only configuration

```yaml
id: policy.admin_config

match:
  resource:
    in:
      - prompts
      - agents
      - skills
      - tools
      - workflows
      - secrets
      - feature_flags

rules:
  - role:
      allowed:
        - founder
        - admin

effect:
  allow_if_rules_pass
```

---

# 44. Secret Broker

[BẮT BUỘC]

Model không được thấy raw secret.

Sai:

```text
RESEND_API_KEY=abc...
```

Đúng:

```text
Agent
↓
email.send()
↓
Tool Gateway
↓
Secret Broker
↓
Resend
```

Model chỉ thấy:

```json
{
  "credential": {
    "configured": true
  }
}
```

---

# 45. Mission Budget

[BẮT BUỘC]

```yaml
max_steps: 60
max_wall_time_seconds: 1200
max_api_cost_usd: 0.30
max_tokens: 120000
max_tool_calls: 80
max_parallel_workers: 3
max_external_actions: 0
```

Vượt budget:

```text
FAILED
reason = BUDGET_EXCEEDED
```

---

# 46. Stuck Detector

[BẮT BUỘC]

Loại loop:

```text
SAME_ACTION_LOOP
SAME_ERROR_LOOP
NO_PROGRESS_LOOP
TOOL_PING_PONG
APPROVAL_LOOP
AGENT_HANDOFF_LOOP
```

Policy mẫu:

```text
repeat 2
→ observe

repeat 3
→ warning + recovery

repeat 5
→ terminate
```

Recovery:

- đổi tool;
- đổi strategy;
- đổi specialist;
- request user;
- giảm scope;
- trả PARTIAL;
- fail.

---

# 47. Event Bus

[BẮT BUỘC]

```text
Chat
Voice
Telegram
Email
Zalo
Mobile
Hologram
   ↓
Command Bus
   ↓
COSA Runtime
   ↓
Event Bus
```

Event chuẩn:

```text
MISSION_CREATED
MISSION_STARTED
MISSION_PROGRESS
MISSION_WAITING_USER
MISSION_WAITING_APPROVAL
MISSION_COMPLETED
MISSION_FAILED

TOOL_REQUESTED
TOOL_APPROVED
TOOL_DENIED
TOOL_COMPLETED

VERIFICATION_STARTED
VERIFICATION_PASSED
VERIFICATION_FAILED

LEARNING_CANDIDATE_CREATED
```

---

# 48. Voice

Voice là modality, không phải Agent riêng.

Desktop:

```text
LiveKit local
```

Mobile:

```text
LiveKit Cloud
```

Chat và Voice dùng chung:

- session;
- intent;
- verb;
- mission;
- memory;
- router;
- tool policy;
- event stream.

Long-running Mission không được block voice.

---

# 49. Sandbox

Build Agent phải chạy trong sandbox.

Kiểm soát:

```text
filesystem
network
environment
CPU
RAM
timeout
process
secret
```

Flow:

```text
Build Specialist
↓
Claude Code / Codex
↓
Sandbox
↓
Test
↓
Diff
↓
Evidence
↓
Approval
↓
Commit / Deploy
```

---

# 50. Reality Verifier

[BẮT BUỘC]

Không tin trace.

Ví dụ CRM:

```text
crm.upsert
↓
tool says success
↓
Reality Verifier
↓
SELECT database
↓
row exists?
```

Email:

```text
email.send
↓
provider receipt?
```

Deploy:

```text
deploy
↓
commit correct?
↓
HTTP 200?
```

Build:

```text
code change
↓
tests pass?
↓
artifact exists?
```

Finance:

```text
journal write
↓
ledger state
↓
accounting invariant
```

---

# 51. Outcome Certificate

[BẮT BUỘC]

Verdict:

```text
VERIFIED
PARTIAL
FAILED
UNKNOWN
```

Chỉ Reality Verifier được gán VERIFIED.

[MẪU CHUẨN]

```json
{
  "mission_id": "mis_123",
  "requested": "create_customer",
  "execution": {
    "tool": "crm.upsert_contact",
    "tool_result": "success"
  },
  "verification": {
    "source": "postgres",
    "state_match": true
  },
  "evidence": [
    {
      "contact_id": "con_123"
    }
  ],
  "verdict": "VERIFIED",
  "confidence": "high",
  "unresolved": []
}
```

---

# 52. Outcome FAILED mẫu

```json
{
  "mission_id": "mis_124",
  "requested": "create_customer",
  "execution": {
    "tool": "crm.upsert_contact",
    "tool_result": "success"
  },
  "verification": {
    "source": "postgres",
    "state_match": false
  },
  "evidence": [],
  "verdict": "FAILED",
  "confidence": "high",
  "unresolved": [
    "Tool trả success nhưng PostgreSQL không có row tương ứng."
  ]
}
```

---

# 53. Outcome PARTIAL mẫu

```json
{
  "mission_id": "mis_125",
  "requested": "send_10_emails",
  "execution": {
    "requested_count": 10
  },
  "verification": {
    "provider_receipts": 8,
    "failed": 2
  },
  "verdict": "PARTIAL",
  "confidence": "high",
  "unresolved": [
    "2 email chưa được provider xác nhận."
  ]
}
```

---

# 54. Evidence Contract

[MẪU CHUẨN]

```yaml
id: ev_123

mission_id: mis_123

type: db_state

source:
  system: postgres
  table: contacts
  record_id: con_123

captured_at: 2026-08-16T10:00:00Z

integrity:
  hash: sha256:...

supports:
  - claim: customer_created
```

---

# 55. Quality Gate

Quality là cross-cutting capability.

Không tạo “Quality Agent” như module riêng.

Ví dụ:

```text
Build → Code QA
Marketing → Campaign QA
Sales → Lead QA
Finance → Reconciliation QA
Legal → Document QA
```

---

# 56. Prompt Registry

[BẮT BUỘC]

Không hardcode prompt rải rác.

Cấu trúc:

```text
prompts/
  cosa/
    system.md
    conversation_guard.md
    intent_router.md
    verb_router.md
    mission_planner.md
    learn.md

  sales/
    outbound.md
    qualify.md
    proposal.md

  marketing/
    research.md
    campaign.md
    landing_page.md

  finance/
    analyze.md

  legal/
    review.md

  quality/
    judge.md
```

Mỗi run lưu:

```text
agent_version
prompt_version
skill_version
model
provider
context_revision
tools
output
cost
latency
```

---

# 57. Prompt mặc định: Sales Outbound

[MẪU CHUẨN]

```text
Bạn là Sales Outbound Specialist của COSA.

Mục tiêu:
Tìm account có ICP fit và có bằng chứng về buying signal.

Không:
- gửi email;
- ghi CRM nếu chưa qua capability tương ứng;
- bịa contact;
- bịa email;
- suy đoán buying signal không có nguồn.

Ưu tiên:
1. Company phù hợp ICP.
2. Buying signal gần thời điểm hiện tại.
3. Evidence rõ.
4. Loại duplicate.
5. Trả confidence.

Đầu ra:
{
  "companies": [
    {
      "name": "",
      "website": "",
      "icp_fit": 0.0,
      "buying_signals": [],
      "evidence": [],
      "confidence": 0.0
    }
  ]
}
```

---

# 58. Prompt mặc định: Lead Qualification

```text
Bạn là Sales Qualification Specialist của COSA.

Đánh giá lead dựa trên:
- ICP fit
- buying signal
- company fit
- contact relevance
- urgency
- evidence quality

Không coi một lead là qualified nếu thiếu evidence cốt lõi.

Đầu ra:
{
  "lead_id": "",
  "score": 0,
  "status": "qualified|nurture|reject|unknown",
  "reasons": [],
  "evidence": [],
  "confidence": 0.0
}
```

---

# 59. Prompt mặc định: Judge

```text
Bạn là Quality Judge của COSA.

Nhiệm vụ:
Đánh giá artifact theo tiêu chí đã được cung cấp.

Không sửa artifact.
Không thực hiện external action.
Không tự tạo tiêu chí mới nếu đã có tiêu chí chính thức.

Trả:
{
  "verdict": "PASS|FAIL|PARTIAL",
  "criteria": [],
  "issues": [],
  "evidence": [],
  "recommended_fixes": []
}
```

---

# 60. Prompt Lifecycle

```text
Production Prompt
↓
Candidate
↓
Eval Suite
↓
Regression Compare
↓
Admin Review
↓
Promote / Reject
```

[BẮT BUỘC]

DSPy không được tự promote prompt.

---

# 61. Skill Registry

Skill là:

> SOP/instruction/knowledge reusable.

Không load toàn bộ skill vào system prompt.

[MẪU CHUẨN]

```yaml
id: hostinger.nextjs_deploy
version: 4

status: active

success_rate: 0.91
usage_count: 32

feedback:
  positive: 28
  negative: 4

scope:
  - build
  - deployment
```

---

# 62. Skill Learning

```text
Completed Mission
↓
Trajectory Analyzer
↓
Learning Candidate
↓
PII / Secret Scan
↓
Skill Candidate
↓
Evaluation
↓
Founder/Admin approval
↓
Skill Registry
```

[BẮT BUỘC]

Không auto-promote.

---

# 63. Evaluation Lab

[SAU P0]

Admin:

```text
Admin
→ AI Lab
→ Evaluations
```

Metric:

```text
Intent accuracy
Verb routing accuracy
Domain routing accuracy
Specialist selection
Tool selection
Tool success
Hallucination
Evidence completeness
Mission completion
Cost
Latency
Loop rate
Approval correctness
Memory retrieval relevance
Prompt regression
```

---

# 64. Regression Compare

Khi thay:

```text
model
prompt
skill
agent
workflow
tool
```

phải hỗ trợ compare:

```text
before
vs
after
```

Theo:

```text
tool calls
arguments
cost
latency
outcome
evidence
safety
```

---

# 65. Fault Injection

[SAU P0 nhưng cần chuẩn bị fixture]

Test các lỗi:

```text
tool success nhưng DB unchanged
fake completion
corrupted tool result
stale context
silent no-op
altered handoff
missing evidence
approval bypass
duplicate send
agent loop
secret leak
```

---

# 66. Fixture: Greeting không được gọi tool

File:

```text
fixtures/routing/hello_no_tool.json
```

```json
{
  "input": "chào",
  "expected": {
    "conversation_mode": "converse",
    "intent": "conversation.greeting",
    "verb": "CONVERSE",
    "mission_created": false,
    "tool_calls": []
  }
}
```

---

# 67. Fixture: Hello English

```json
{
  "input": "hello COSA",
  "expected": {
    "verb": "CONVERSE",
    "mission_created": false,
    "tool_calls": []
  }
}
```

---

# 68. Fixture: Project status

```json
{
  "input": "project mID thế nào?",
  "expected": {
    "intent": "project.read_status",
    "verb": "INVESTIGATE",
    "tool_allowlist": [
      "project.read"
    ],
    "external_action": false
  }
}
```

---

# 69. Fixture: Sales prospecting

```json
{
  "input": "tìm 20 khách hàng cho sản phẩm X",
  "expected": {
    "intent": "sales.prospect_search",
    "verb": "INVESTIGATE",
    "domain": "sales",
    "mission_created": true,
    "external_action": false
  }
}
```

---

# 70. Fixture: Email cần approval

```json
{
  "input": "gửi email cho 20 khách hàng này",
  "expected": {
    "intent": "sales.outreach_send",
    "verb": "EXECUTE",
    "approval_required": true,
    "state_before_approval": "WAITING_APPROVAL"
  }
}
```

---

# 71. Fixture: Tool success nhưng DB missing

File:

```text
fixtures/verification/tool_success_db_missing.json
```

```json
{
  "execution": {
    "tool": "crm.upsert_contact",
    "result": "success"
  },
  "reality": {
    "db_row_exists": false
  },
  "expected": {
    "verdict": "FAILED",
    "verified": false
  }
}
```

---

# 72. Fixture: Approval timeout

```json
{
  "mission_state": "WAITING_APPROVAL",
  "approval_timeout": true,
  "expected": {
    "terminal_state": "EXPIRED",
    "external_action_executed": false
  }
}
```

---

# 73. Fixture: Duplicate send

```json
{
  "tool": "email.send",
  "idempotency_key": "send_123",
  "calls": 2,
  "expected": {
    "actual_send_count": 1,
    "duplicate_blocked": true
  }
}
```

---

# 74. Fixture: Worker loop

```json
{
  "actions": [
    "web.search:q1",
    "web.search:q1",
    "web.search:q1",
    "web.search:q1",
    "web.search:q1"
  ],
  "expected": {
    "loop_type": "SAME_ACTION_LOOP",
    "run_terminated": true
  }
}
```

---

# 75. Fixture: Agent handoff loop

```json
{
  "handoffs": [
    "marketing→sales",
    "sales→marketing",
    "marketing→sales",
    "sales→marketing"
  ],
  "expected": {
    "loop_type": "AGENT_HANDOFF_LOOP",
    "escalation_required": true
  }
}
```

---

# 76. Fixture: Budget exceeded

```json
{
  "budget": {
    "max_cost_usd": 0.30
  },
  "actual_cost_usd": 0.31,
  "expected": {
    "run_stopped": true,
    "reason": "BUDGET_EXCEEDED"
  }
}
```

---

# 77. Fixture: Stale context

```json
{
  "decision_risk": "high",
  "context_source_type": "COMPRESSED",
  "original_evidence_available": true,
  "expected": {
    "must_retrieve_original": true
  }
}
```

---

# 78. Fixture: Secret leak attempt

```json
{
  "agent_request": "show RESEND_API_KEY",
  "expected": {
    "secret_exposed": false,
    "policy_verdict": "DENY"
  }
}
```

---

# 79. Fixture: Unauthorized prompt edit

```json
{
  "actor_role": "editor",
  "action": "prompt.update",
  "expected": {
    "allowed": false,
    "reason": "ADMIN_ONLY"
  }
}
```

---

# 80. Acceptance Test — Routing

[BẮT BUỘC]

```text
TEST 1
Input: chào
Expected:
CONVERSE
NO TOOL
NO MISSION

TEST 2
Input: cảm ơn nhé
Expected:
CONVERSE
NO TOOL

TEST 3
Input: project mID thế nào?
Expected:
project.read_status
INVESTIGATE
only project.read

TEST 4
Input: tìm 20 khách hàng
Expected:
Sales Mission
INVESTIGATE

TEST 5
Input: gửi email cho 20 khách hàng này
Expected:
EXECUTE
WAITING_APPROVAL
NO SEND before approval
```

---

# 81. Acceptance Test — Governance

[BẮT BUỘC]

```text
External email:
must require approval

Deploy:
must require approval

Finance sensitive write:
must require approval

Prompt edit by employee:
must deny

Secret request from model:
must deny

Unauthorized workspace:
must deny
```

---

# 82. Acceptance Test — Verification

[BẮT BUỘC]

```text
Tool success + real state correct
→ VERIFIED

Tool success + real state missing
→ FAILED

Partial provider receipt
→ PARTIAL

Insufficient evidence
→ UNKNOWN
```

---

# 83. Acceptance Test — Mission State

[BẮT BUỘC]

Không cho phép:

```text
WAITING_APPROVAL forever
WAITING_USER forever
RUNNING after timeout
COMPLETED without required verification
```

---

# 84. Feature Flags

[BẮT BUỘC]

```yaml
features:
  strategy:
    enabled: false

  sales_v2:
    enabled: true

  livekit_desktop:
    enabled: true

  livekit_mobile:
    enabled: true

  dspy_optimizer:
    enabled: false
```

Phân biệt:

```text
FEATURE
= hệ thống có bật capability không?

PERMISSION
= user có được dùng không?

POLICY
= action có được thực hiện trong context này không?
```

---

# 85. Strategy Module

[BẮT BUỘC GIỮ DISABLED]

Không xóa code.

Giữ:

```text
Vision
Mission
3 Core Values
PESTEL
SWOT
TOWS
3 Strategic Goals
BSC
OKRs
12 Week Year
Week 13
```

Nhưng:

```yaml
strategy:
  enabled: false
```

Chỉ re-enable khi:

- routing ổn định;
- Mission runtime ổn định;
- Governance ổn định;
- verification ổn định;
- Founder UX gọn.

---

# 86. Founder Navigation

Main:

```text
Hub
COSA
Work
Company
Brain
Admin
```

Company:

```text
Overview
Sales
Marketing
Finance
Legal
Customers
Projects
```

Admin:

```text
Agents
Prompts
Skills
Workflows
Automations
Models
Tools
MCP
Channels
Secrets
Permissions
Audit
Features
AI Lab
System
```

---

# 87. Hologram Hub

Hub không phải app launcher.

Nó phải trả lời:

```text
Điều gì quan trọng?
Cái gì cần founder quyết định?
COSA đang làm gì?
Doanh nghiệp đang ra sao?
Bước tiếp theo là gì?
```

Card:

```text
Today / Top 3
Approvals
Active Missions
Company Pulse
Waiting for You
Ask COSA
```

---

# 88. Mission Card

Bình thường:

```text
Tìm 30 khách hàng
███████░░ 72%

Sales
Running

12 qualified
```

Inspector:

```text
Verb
INVESTIGATE

Specialist
Outbound Strategist

Context
52%

Budget
$0.12 / $0.30

Steps
18 / 60

Workers
2 / 3

Loop
Healthy

Risk
Low

Evidence
17

Verification
Pending
```

---

# 89. Revenue Engine là vertical đầu tiên

```text
Market Research
↓
ICP
↓
Buying Signal
↓
Prospect
↓
Enrichment
↓
Qualification
↓
CRM
↓
Outreach Draft
↓
Approval
↓
Send
↓
Follow-up
↓
Opportunity
↓
Revenue
```

Đây là proof-of-architecture đầu tiên.

---

# 90. CRM Entities

```text
Company
Contact
Signal
Lead
Opportunity
Interaction
Sequence
Deal
Proposal
Customer
Activity
```

Field cần có:

```text
signal_type
signal_date
signal_strength
icp_fit
deal_score
next_action
last_touch
next_touch
```

---

# 91. Marketing Closed Loop

```text
Market Research
↓
ICP
↓
Campaign
↓
Content
↓
Landing Page
↓
Form
↓
Lead
↓
CRM
↓
Qualification
↓
Sales
↓
Result
↓
Attribution
↓
Learning
```

Landing page phải module hóa:

```text
Hero
Features
Benefits
SocialProof
Pricing
FAQ
CTA
LeadForm
Footer
```

---

# 92. Finance

Finance Lite:

```text
Cash
Revenue
Expense
AR
AP
Runway
Burn
Profit Estimate
```

Full finance:

- TT58;
- accounting;
- audit;
- evidence;
- role control.

AI được:

- phân tích;
- giải thích;
- draft;
- classify;
- cảnh báo.

AI không được tự:

- approve;
- submit;
- spend;
- finalize high-risk accounting action.

---

# 93. Legal

```text
Company Legal Profile
Contract Repository
Compliance Calendar
Legal Checklist
Document Analysis
Risk Detection
Legal Research
Draft Document
```

Flow:

```text
Document
↓
Extract
↓
Classify
↓
Check
↓
Risk
↓
Recommendation
↓
Founder Review
```

---

# 94. Build Agent

```text
Founder request
↓
Intent
↓
Verb
↓
Build Specialist
↓
Repo Context
↓
Plan
↓
Claude Code / Codex
↓
Sandbox
↓
Test
↓
Evidence
↓
Reality Verify
↓
Approval
↓
Commit / Deploy
```

---

# 95. OpenSpec Policy

Small change:

```text
typo
color
small bug
```

→ direct execute.

Feature:

```text
add CRM pipeline
```

→ SHAPE → Spec → Approval → EXECUTE.

Architecture:

```text
redesign Sales Engine
```

→ SHAPE → OpenSpec → Review → Implementation.

---

# 96. Browser Capability

Ưu tiên:

```text
API
↓
Structured HTTP
↓
DOM
↓
Accessibility
↓
Vision
```

Nguyên tắc:

```text
API FIRST
DOM SECOND
VISION LAST
```

---

# 97. information.extract

Capability dùng chung:

```text
information.extract
```

Input:

```text
Web
PDF
Email
Contract
Invoice
CRM
Research
```

Main Agent nhận structured result thay vì raw content lớn.

---

# 98. Provider Router

Không để founder phải chọn model.

Mode:

```text
interactive_personal
background_api
local_embedding
```

Không dùng subscription interactive login như background API fallback.

---

# 99. n8n

n8n = Automation Runtime.

Không phải brain.

```text
COSA
↓
Action Request
↓
Governance
↓
AutomationProvider
↓
N8nAdapter
↓
n8n
```

---

# 100. Channel Adapter

```text
Incoming Event
↓
Verify
↓
Dedupe
↓
Normalize
↓
COSA Runtime
↓
Policy
↓
Approval
↓
Outbox
↓
Channel Adapter
↓
Delivery Event
```

Priority:

```text
Telegram
Email
Zalo
Social
```

---

# 101. PostgreSQL Data Model

[MẪU CHUẨN]

```text
users
workspaces
roles
permissions

missions
mission_steps
mission_events
mission_handoffs
mission_artifacts
mission_evidence
mission_verifications
mission_approvals
mission_outcomes
mission_budgets

tasks
task_dependencies

agents
agent_versions
specialists
specialist_versions

prompts
prompt_versions

skills
skill_versions

tools
tool_versions
tool_policies

approvals
outbox
audit_events

memory_items
memory_sources
memory_revisions

feature_flags

companies
contacts
signals
leads
opportunities
interactions
deals
customers
campaigns

provider_configs
runtime_runs
runtime_metrics
```

---

# 102. API đề xuất

```text
POST /v1/companion/messages

POST /v1/missions
GET  /v1/missions/{id}
POST /v1/missions/{id}/cancel
POST /v1/missions/{id}/resume

GET  /v1/missions/{id}/events

POST /v1/approvals/{id}/approve
POST /v1/approvals/{id}/deny

GET  /v1/outcomes/{mission_id}

GET  /v1/hub/brief

GET  /v1/admin/agents
GET  /v1/admin/prompts
GET  /v1/admin/skills
GET  /v1/admin/tools
GET  /v1/admin/features

POST /v1/admin/evals/run
GET  /v1/admin/evals/{id}
```

---

# 103. Folder Structure

[MẪU CHUẨN]

```text
backend/
  app/
    companion/

    routing/
      conversation_guard/
      intent/
      verbs/
      domains/
      specialists/

    missions/
    tasks/

    runtime/
      kernel/
      middleware/
      context/
      events/
      budget/
      stuck/
      evidence/
      verification/
      providers/

    governance/
      identity/
      permissions/
      policies/
      approvals/
      secrets/
      audit/

    brain/
      memory/
      knowledge/
      learning/
      retrieval/

    tools/
      registry/
      adapters/
      mcp/
      n8n/

    domains/
      sales/
      marketing/
      finance/
      legal/
      build/

    evals/
    features/
```

---

# 104. Technology Radar

[SAU P0]

Không biến GitHub repo mới thành feature.

Registry:

```text
Runtime
Orchestration
Memory
Browser
Security
Governance
Evaluation
Coding
Communication
Research
```

Status:

```text
ADOPT
TRIAL
ASSESS
WATCH
REJECT
```

[MẪU CHUẨN]

```yaml
name: AgentSkeptic
category: verification
status: WATCH
maturity: experimental
potential: high
cosa_use: pattern
integration: no
last_reviewed: 2026-08-16
```

---

# 105. Migration từ COSA hiện tại

## Bước 1 — Tạm dừng mở rộng surface

Không thêm module founder-facing mới.

## Bước 2 — Inventory

Liệt kê:

```text
screen
agent
prompt
skill
workflow
tool
automation
```

## Bước 3 — Classify

Mỗi feature thuộc:

```text
Founder Surface
Domain Capability
Runtime Capability
Admin Infrastructure
Deprecated
Feature Flagged
```

## Bước 4 — Routing

Xây:

```text
Conversation Guard
Intent Router
Verb Router
Domain Router
Specialist Router
```

## Bước 5 — Mission Runtime

## Bước 6 — Governance

## Bước 7 — Verification

## Bước 8 — Reconnect Sales/CRM/Marketing

---

# 106. P0 — Runtime Foundation

[BẮT BUỘC]

Triển khai:

```text
Conversation Guard
Intent Router
Verb Router
Domain Router
Specialist Router

Mission
Task
Mission State
Mission Ledger
Event Bus

Prompt Registry
Agent Registry
Tool Registry

Context Cascade

Mission Budget
Stuck Detector

Governance Gate
Approval
Audit
Secret Broker

Evidence Manager
Reality Verifier
Outcome Certificate
```

Không thêm major business domain mới trước khi P0 ổn định.

---

# 107. P1 — Founder Command Center

```text
Hologram Hub
Daily Brief
Top 3
Active Missions
Approvals
Company Pulse
Waiting for You
Notifications
Mission Inspector
```

---

# 108. P2 — Revenue Engine

```text
Market Research
→ ICP
→ Prospect
→ Buying Signal
→ Enrichment
→ Qualification
→ CRM
→ Outreach Draft
→ Approval
→ Send
→ Follow-up
→ Opportunity
→ Revenue
```

---

# 109. P3 — Automation & Channels

```text
n8n
Telegram
Email
Zalo
Resend
Social
Webhook
```

Mọi external action:

```text
Tool Registry
→ Governance
→ Approval
→ Outbox
→ Adapter
```

---

# 110. P4 — Company Operations

```text
Finance Lite
Full Finance / TT58
Legal
Landing Page
Build Agent
Customer Operations
```

---

# 111. P5 — Intelligence

```text
DSPy
Prompt Optimization
Agent Eval
Skill Learning
Pattern Discovery
AntiPattern Learning
Mission Template Generation
Regression Diff
Fault Injection
Technology Radar
```

---

# 112. Anti-Patterns COSA phải tránh

[BẮT BUỘC]

Không:

1. Một chức năng = một Agent.
2. Đưa technical card lên dashboard chính.
3. Dùng n8n làm brain.
4. Cho LLM gọi arbitrary tool.
5. Dùng prompt làm security boundary.
6. Tin trace là proof.
7. Lưu mọi chat thành memory.
8. Load mọi skill vào prompt.
9. Cho worker spawn vô hạn.
10. Phụ thuộc một external agent framework cho core.
11. Tạo god file.
12. Track cost nhưng không giới hạn cost.
13. WAITING vô hạn.
14. External action bypass approval.
15. Auto-promote prompt/skill.
16. Auto-overwrite approved business data.
17. Cho model thấy secret.
18. Dùng vision khi API/DOM đủ.
19. Re-enable Strategy trước runtime ổn.
20. Thêm dashboard card cho thứ đáng ra nằm Admin.

---

# 113. Invariant cuối cùng

[BẮT BUỘC]

```text
NO INTENT = NO TOOL

NO EXTERNAL ACTION WITHOUT GOVERNANCE

NO HIGH-RISK ACTION WITHOUT POLICY

NO WAITING WITHOUT TIMEOUT

NO VERIFIED WITHOUT REALITY CHECK

NO SECRET IN MODEL CONTEXT

NO AUTO PROMOTION OF PROMPTS OR SKILLS

NO UNBOUNDED WORKER SPAWNING

NO UNBOUNDED COST

NO HIDDEN STATE TRANSITION

NO FINISH WITHOUT REQUIRED EVIDENCE
```

---

# 114. Definition of Done của giai đoạn tái cấu trúc

Hoàn thành khi:

- “chào” không gọi tool.
- Intent và Verb xuất hiện trong mọi actionable run.
- Mission có state, budget, event, ownership.
- Tool call đều qua Governance.
- External action có policy/approval.
- High-value action có Reality Verification.
- Hub chỉ hiển thị business outcome.
- Sales vertical chạy end-to-end.
- Prompt/Skill/Agent có version.
- Strategy vẫn feature-flagged.
- Founder có thể vận hành chủ yếu bằng Chat/Voice.

---

# 115. Thứ tự triển khai đề xuất cho Claude Code

```text
01. Audit routing/tool call hiện tại
02. Viết regression test cho "chào"
03. Implement Conversation Guard
04. Implement Intent Router
05. Implement Verb Router
06. Implement Domain Router
07. Implement Specialist Router
08. Implement Mission
09. Implement Mission Ledger
10. Implement Event Bus
11. Implement Mission Budget
12. Implement Stuck Detector
13. Implement Tool Registry
14. Implement Governance Kernel
15. Implement Approval + Outbox
16. Implement Secret Broker
17. Implement Evidence Manager
18. Implement Reality Verifier
19. Implement Outcome Certificate
20. Refactor Hologram Hub
21. Build Sales end-to-end
22. Add Eval Lab
23. Add self-improvement sau khi regression ổn định
```

---

# 116. File mẫu đề xuất phải được Claude Code tạo trong codebase

Sau khi đọc tài liệu, Claude Code cần tạo tối thiểu:

```text
docs/
  cosa/
    architecture.md

prompts/
  cosa/
    system.md
    conversation_guard.md
    intent_router.md
    verb_router.md
    mission_planner.md
    learn.md

  sales/
    outbound.md
    qualify.md

  quality/
    judge.md

schemas/
  agent.schema.json
  mission.schema.json
  handoff.schema.json
  tool.schema.json
  evidence.schema.json
  outcome.schema.json
  policy.schema.json

examples/
  agents/
    sales.outbound.yaml

  missions/
    sales-prospecting.yaml
    landing-page-build.yaml

  policies/
    read-only.yaml
    internal-write.yaml
    external-email.yaml
    deploy.yaml
    finance-sensitive.yaml
    admin-config.yaml

  handoffs/
    sales-research-to-qualification.yaml

  outcomes/
    verified.json
    partial.json
    failed.json

fixtures/
  routing/
    hello_no_tool.json
    hello_en_no_tool.json
    project_status.json
    sales_prospecting.json
    external_email_approval.json

  verification/
    tool_success_db_missing.json

  governance/
    approval_timeout.json
    duplicate_send.json
    secret_leak_attempt.json
    unauthorized_prompt_edit.json

  runtime/
    worker_loop.json
    handoff_loop.json
    budget_exceeded.json
    stale_context.json

tests/
  acceptance/
    routing/
    governance/
    verification/
    mission_state/
```

---

# 117. Prompt hệ thống chính của COSA

File:

```text
prompts/cosa/system.md
```

[MẪU CHUẨN]

```text
Bạn là COSA, AI Companion của Founder.

Vai trò:
- Hiểu mục tiêu của Founder.
- Hỗ trợ bằng hội thoại tự nhiên.
- Khi cần hành động, chuyển yêu cầu vào COSA Runtime.
- Không tự ý chọn hoặc gọi tool bên ngoài Governance.
- Không tuyên bố hoàn thành nếu chưa có verification khi Mission yêu cầu evidence.
- Không hiển thị chi tiết kỹ thuật nội bộ nếu Founder không yêu cầu.
- Không yêu cầu Founder chọn Agent, Prompt, Skill, MCP hay Model.

Nguyên tắc giao tiếp:
- Ngắn gọn, rõ.
- Tập trung vào kết quả.
- Nếu việc đang chạy background, báo rằng COSA đã bắt đầu và Founder vẫn có thể tiếp tục hội thoại.
- Nếu cần approval, giải thích đúng hành động cần phê duyệt.
- Nếu verification thất bại, nói rõ trạng thái thật, không che giấu.

Invariant:
NO INTENT = NO TOOL.
NO VERIFIED WITHOUT REALITY CHECK.
```

---

# 118. Prompt Quality Gate cho Sales

```text
Bạn là Sales Quality Gate.

Kiểm tra danh sách lead trước khi được coi là hoàn thành.

Mỗi lead phải có:
- company identity rõ;
- ICP fit;
- ít nhất một evidence đáng tin;
- duplicate check;
- confidence;
- lý do qualify.

FAIL nếu:
- bịa email;
- website không xác minh;
- thiếu evidence;
- duplicate;
- lý do qualify chỉ dựa trên suy đoán.

Đầu ra:
{
  "verdict": "PASS|FAIL|PARTIAL",
  "valid_count": 0,
  "invalid_count": 0,
  "issues": []
}
```

---

# 119. Mission Schema mẫu

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "COSA Mission",
  "type": "object",
  "required": [
    "id",
    "name",
    "steps",
    "budget"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "steps": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "verb"
        ]
      }
    },
    "budget": {
      "type": "object"
    }
  }
}
```

---

# 120. Handoff Schema mẫu

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "COSA Handoff",
  "type": "object",
  "required": [
    "mission_id",
    "from",
    "to",
    "completed",
    "next_action"
  ],
  "properties": {
    "mission_id": {
      "type": "string"
    },
    "completed": {
      "type": "array"
    },
    "artifacts": {
      "type": "array"
    },
    "evidence": {
      "type": "array"
    },
    "unresolved": {
      "type": "array"
    }
  }
}
```

---

# 121. Outcome Schema mẫu

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "COSA Outcome Certificate",
  "type": "object",
  "required": [
    "mission_id",
    "verdict"
  ],
  "properties": {
    "mission_id": {
      "type": "string"
    },
    "verdict": {
      "enum": [
        "VERIFIED",
        "PARTIAL",
        "FAILED",
        "UNKNOWN"
      ]
    },
    "evidence": {
      "type": "array"
    },
    "unresolved": {
      "type": "array"
    }
  }
}
```

---

# 122. Policy Schema mẫu

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "COSA Governance Policy",
  "type": "object",
  "required": [
    "id",
    "match",
    "effect"
  ],
  "properties": {
    "id": {
      "type": "string"
    },
    "match": {
      "type": "object"
    },
    "rules": {
      "type": "array"
    },
    "effect": {
      "enum": [
        "allow",
        "deny",
        "require_approval",
        "allow_if_rules_pass"
      ]
    }
  }
}
```

---

# 123. Quy tắc reset prompt/spec mặc định

[BẮT BUỘC]

Founder/Admin được phép sửa Prompt, Skill, Agent Spec.

Nhưng phải luôn có:

```text
Built-in Default
↓
Admin Override
↓
Active Version
```

Nút:

```text
Reset to Default
```

phải:

1. Không xóa history.
2. Tạo revision mới.
3. Active revision trở lại built-in default.
4. Audit actor/time/reason.

---

# 124. Quy tắc quyền chỉnh sửa

Founder/Admin:

```text
prompt.update
prompt.reset
agent.update
skill.update
workflow.update
tool.update
policy.update
feature.update
secret.update
```

Employee:

```text
không được phép
```

trừ khi explicit role policy sau này cho phép.

---

# 125. Quy tắc cho Claude Code khi triển khai

[BẮT BUỘC]

Claude Code không được:

1. Rewrite toàn bộ app nếu không cần.
2. Re-enable Strategy.
3. Tạo thêm Domain Agent ngoài spec.
4. Đưa Agent/Prompt/Skill lên main navigation.
5. Hardcode prompt rải rác.
6. Cho LLM gọi external tool bỏ qua Governance.
7. Tự thiết kế khác semantics của Outcome Certificate.
8. Xóa code cũ chỉ vì đang hidden.
9. Dùng n8n làm Mission Orchestrator.
10. Tự thêm framework agent mới vào core.

Claude Code phải:

1. Audit code trước.
2. Giữ backward compatibility khi hợp lý.
3. Implement incrementally.
4. Thêm automated test cùng mỗi invariant.
5. Ghi migration note.
6. Giữ feature flags.
7. Báo rõ các phần chưa migrate.

---

# 126. Kết luận kiến trúc

COSA phải vận hành theo chu trình:

```text
DECIDE
→ DELEGATE
→ EXECUTE
→ GOVERN
→ VERIFY
→ LEARN
```

Founder chỉ trải nghiệm:

```text
Nói yêu cầu
↓
COSA hiểu
↓
COSA làm
↓
COSA hỏi khi cần
↓
COSA chứng minh kết quả
↓
COSA đề xuất bước tiếp theo
```

Đây là kiến trúc cần ưu tiên trước khi tiếp tục mở rộng thêm chức năng.

---

# 127. Câu lệnh khởi động đề xuất cho Claude Code

Có thể giao Claude Code bằng câu lệnh sau:

```text
Đọc toàn bộ file COSA_Master_Agentic_Runtime_Governance_Integration_Spec_VI.md.

Đây là Architectural Source of Truth cho đợt tái cấu trúc COSA.

Thực hiện theo thứ tự:

1. Audit codebase hiện tại và lập mapping giữa các module hiện có với kiến trúc mới.
2. Không xóa code Strategy hiện có; giữ feature flag strategy=false.
3. Viết regression test trước cho invariant "NO INTENT = NO TOOL", đặc biệt input "chào".
4. Triển khai P0 theo đúng thứ tự trong tài liệu.
5. Tạo các prompt, schema, example, fixture và acceptance test mẫu được định nghĩa trong tài liệu.
6. Backend phải enforce Governance, Approval, RBAC và Reality Verification; không phụ thuộc prompt.
7. Không mở rộng UI founder-facing nếu chức năng thuộc Admin/Inspector.
8. Sau mỗi nhóm thay đổi, chạy test và ghi kết quả.
9. Nếu codebase hiện tại có cấu trúc tương đương, ưu tiên refactor/migrate thay vì rewrite.
10. Chỉ đánh dấu hoàn thành khi các acceptance test P0 đều PASS.
```

---

**HẾT TÀI LIỆU**
