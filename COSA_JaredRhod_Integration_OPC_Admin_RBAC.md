# COSA — Jared Rhod Architecture Integration Specification

> **Mục tiêu:** Tích hợp các ý tưởng kiến trúc đáng học từ hệ sinh thái Jared Rhod vào COSA theo hướng **AI Operating System cho One-Person Company**, đồng thời sửa triệt để lỗi intent routing hiện tại: các câu hội thoại như “chào” không được tự động kích hoạt project flow, project lookup, tool call hoặc nạp project context khi người dùng chưa yêu cầu.
>
> **Nguyên tắc:** Học **pattern/architecture**, không sao chép nguyên prompt, source content hoặc cấu trúc có ràng buộc giấy phép vào sản phẩm thương mại.

---

## 1. Executive Summary

Các ý tưởng giá trị nhất từ Jared Rhod có thể áp dụng cho COSA gồm:

1. **AI Priming** — mỗi công việc chỉ nạp đúng knowledge/context cần thiết.
2. **Memory Vault philosophy** — memory có cấu trúc, human-readable, persistent.
3. **Job-based execution** — biến yêu cầu thành Job rõ ràng thay vì để agent tự suy diễn flow.
4. **Skill-based knowledge** — tách kỹ năng khỏi agent, memory, business data và tool.
5. **Executable Build Spec** — prompt cho coding agent phải giống specification triển khai có acceptance test.
6. **Hybrid LiveKit Voice** — Desktop dùng LiveKit local/self-hosted kết hợp local STT/TTS khi phù hợp; Mobile dùng LiveKit Cloud để tối ưu realtime, multi-device và vận hành từ xa.
7. **Visualizer** — biểu diễn trạng thái agent thành một “presence layer” dễ quan sát.
8. **Rules / Guardrails** — evidence, checkpoint, secret safety, external-content isolation, locked decisions.
9. **Action Runtime** — AI không chỉ trả lời mà có thể hành động qua MCP/API/browser/n8n/desktop.
10. **Observe → Verify → Learn** — sau khi hành động phải quan sát kết quả và cập nhật learning/memory.

Tuy nhiên COSA cần nâng cấp kiến trúc Jared theo một nguyên tắc quan trọng:

> **Không Prime trước khi hiểu intent. Không gọi tool trước khi scope rõ. Không project lookup nếu người dùng chưa yêu cầu.**

Flow lõi được đề xuất:

```text
Understand
   ↓
Route
   ↓
Scope
   ↓
Prime
   ↓
Reason
   ↓
Act
   ↓
Observe
   ↓
Verify
   ↓
Learn
```

Đây là pipeline nền tảng của COSA sau lần điều chỉnh này.

---

# 2. Vấn đề hiện tại cần sửa ngay

## 2.1 Lỗi hành vi

Hiện tại khi user chat:

```text
Chào
```

COSA có thể tự động:

```text
User message
   ↓
Project flow
   ↓
project.list / project lookup
   ↓
Trả về thông tin project
```

Hành vi này không hợp lý vì user chưa yêu cầu:

- kiểm tra project;
- liệt kê project;
- mở project;
- xem project mID;
- phân tích project;
- thực thi workflow liên quan project.

## 2.2 Nguyên nhân kiến trúc

Một hoặc nhiều vấn đề sau có thể đang tồn tại:

- project context được preload mặc định;
- Project Agent là route mặc định;
- LLM có toàn bộ project tools và tự quyết định tool call;
- router đánh đồng “conversation” với “business operation”;
- không có `NO_TOOL` route;
- không có capability permission gate;
- memory/project priming xảy ra trước intent classification;
- prompt system khiến agent “cố giúp” bằng cách lấy dữ liệu dù không được yêu cầu.

## 2.3 Quy tắc mới bắt buộc

```yaml
default_chat_policy:
  project_context: false
  project_lookup: false
  business_database: false
  tools: []
  priming: minimal
  action: none
```

**Default route của COSA phải là Normal Chat, không phải Project Flow.**

---

# 3. Conversation Gate — lớp đầu tiên của COSA

Trước đây có thể hiểu kiến trúc như:

```text
User → Agent → Tools
```

Cần thay bằng:

```text
User
 ↓
Conversation Gate
 ↓
Intent Router
 ↓
Scope Resolver
 ↓
Job / Chat
```

## 3.1 Nhiệm vụ của Conversation Gate

Conversation Gate chỉ trả lời câu hỏi:

> “User đang muốn nói chuyện, hỏi thông tin, yêu cầu phân tích, yêu cầu đọc dữ liệu hay yêu cầu thực hiện hành động?”

Nó **không được thực hiện business logic**.

## 3.2 Intent taxonomy đề xuất

```text
SOCIAL_CHAT
GENERAL_QUESTION

PROJECT_DISCOVERY
PROJECT_QUERY
PROJECT_ANALYSIS
PROJECT_OPERATION

BUSINESS_ANALYSIS
MARKETING_JOB
SALES_JOB
FINANCE_JOB
LEGAL_JOB
TECH_JOB
LEARNING_JOB
OPERATIONS_JOB

TOOL_ACTION
SYSTEM_COMMAND

AMBIGUOUS
```

## 3.3 Ví dụ

### “Chào”

```json
{
  "intent": "SOCIAL_CHAT",
  "confidence": 0.99,
  "needs_project": false,
  "needs_memory": false,
  "needs_tools": false,
  "needs_job": false
}
```

### “Project nào đang chạy?”

```json
{
  "intent": "PROJECT_DISCOVERY",
  "confidence": 0.97,
  "needs_project": true,
  "needs_tools": true,
  "allowed_capabilities": ["project.list"]
}
```

### “Kiểm tra project mID”

```json
{
  "intent": "PROJECT_QUERY",
  "confidence": 0.98,
  "entity_refs": ["mID"],
  "needs_project": true,
  "needs_tools": true,
  "allowed_capabilities": ["project.read"]
}
```

### “Phân tích funnel bán hàng cho mID”

```json
{
  "intent": "SALES_JOB",
  "confidence": 0.97,
  "entity_refs": ["mID"],
  "needs_project": true,
  "needs_job": true,
  "skills": ["sales", "funnel"],
  "allowed_capabilities": [
    "project.read",
    "crm.read",
    "sales.analytics.read"
  ]
}
```

---

# 4. Tool Permission Gate — không để model tự gọi mọi tool

Một thay đổi kiến trúc bắt buộc:

```text
Không nên:
User → LLM → LLM tự chọn bất kỳ tool nào
```

Nên:

```text
User
 ↓
Intent Router
 ↓
Capability Policy
 ↓
Allowed Tools
 ↓
Agent Runtime
```

## 4.1 Ví dụ capability envelope

### Social chat

```yaml
intent: SOCIAL_CHAT
allowed_tools: []
```

### List project

```yaml
intent: PROJECT_DISCOVERY
allowed_tools:
  - project.list
```

### Analyze sales for mID

```yaml
intent: SALES_JOB
allowed_tools:
  - project.read
  - crm.read
  - sales.analytics.read
```

### Generate landing page draft

```yaml
intent: MARKETING_JOB
allowed_tools:
  - project.read
  - product.read
  - brand.read
  - filesystem.write_local
  - code.generate
  - test.local
```

Không có `hostinger.deploy` cho tới khi job đi đến bước deploy và policy cho phép.

---

# 5. `NO_TOOL / NO_CONTEXT / NO_ACTION` phải là trạng thái hợp lệ

COSA cần chấp nhận rằng nhiều câu chat **không cần workflow**.

```text
NO_TOOL
NO_PROJECT
NO_JOB
NO_ACTION
```

là các output hợp lệ của router.

Ví dụ:

```text
User: Chào
 ↓
SOCIAL_CHAT
 ↓
NO_PROJECT
NO_TOOL
NO_JOB
 ↓
Assistant response
```

Điều này phải được xem là hành vi đúng, không phải “agent chưa làm gì”.

---

# 6. Scope Resolver — chỉ lấy dữ liệu thật sự cần thiết

Sau Intent Router mới quyết định scope.

```text
Intent
 ↓
Scope Resolver
 ↓
Context Set
```

## 6.1 Scope hierarchy

```text
User Scope
Company Scope
Project Scope
Domain Scope
Job Scope
Resource Scope
```

## 6.2 Ví dụ

### Chào

```text
scope = minimal conversation
```

### “Tôi thích câu trả lời ngắn hơn”

```text
scope = user preferences
```

### “Kiểm tra mID”

```text
scope = project:mID
```

### “Phân tích marketing cho mID”

```text
scope =
  company
  + project:mID
  + product
  + ICP
  + marketing knowledge
  + campaign history
```

### “So sánh sales của mID và project X”

```text
scope =
  company
  + project:mID
  + project:X
  + CRM/sales metrics
```

---

# 7. COSA Priming Engine

Ý tưởng AI Priming của Jared nên được đưa thành một engine chính thức.

## 7.1 Định nghĩa trong COSA

**Priming = deterministic context loading theo Job đã xác định.**

Không dùng Priming để đoán user muốn gì.

Pipeline:

```text
Intent
 ↓
Scope
 ↓
Job
 ↓
Priming Registry
 ↓
Required Knowledge + Business Context
 ↓
Agent
```

## 7.2 Nguyên tắc bắt buộc

> **No Job → No Heavy Priming**

Normal chat không cần nạp:

- project;
- finance;
- CRM;
- marketing library;
- all memory;
- all company data.

## 7.3 Priming Registry mẫu

```yaml
jobs:
  create_landing_page:
    agent: marketing_builder

    required_context:
      - company.brand
      - company.offer
      - project.current
      - project.product
      - customer.icp

    required_skills:
      - marketing.fundamentals
      - marketing.copywriting
      - marketing.landing_page
      - web.conversion

    optional_context:
      - campaign.previous_results
      - crm.segment

    tools:
      - project.read
      - brand.read
      - code.local
      - test.local

    approval:
      production_deploy: required
```

---

# 8. Tách rõ Agent, Skill, Memory, Context, Job, Tool

Đây là một trong các thay đổi quan trọng nhất để COSA không trở thành một hệ thống agent lẫn lộn.

## Agent

**Ai thực hiện công việc.**

Ví dụ:

- Sales Agent
- Marketing Agent
- Finance Agent
- Legal Agent
- Tech Agent

## Skill

**Biết làm công việc như thế nào.**

Ví dụ:

- copywriting;
- funnel design;
- lead qualification;
- forecasting;
- contract review;
- debugging.

## Memory

**Biết điều gì đã xảy ra trước đó.**

Ví dụ:

- decisions;
- outcomes;
- preferences;
- failures;
- lessons learned.

## Context

**Thông tin đúng ở thời điểm hiện tại.**

Ví dụ:

- project mID;
- CRM leads;
- doanh số tuần này;
- campaign hiện tại.

## Job

**Đơn vị công việc cần hoàn thành.**

Ví dụ:

- create landing page;
- create sales funnel;
- prepare weekly review;
- reconcile finance data.

## Tool

**Phương tiện để thực hiện hành động.**

Ví dụ:

- PostgreSQL;
- MCP;
- n8n;
- Hostinger;
- Resend;
- browser;
- filesystem;
- shell.

---

# 9. COSA Skills Library

Học cách Jared tổ chức marketing skills nhưng áp dụng theo COSA-native architecture.

```text
skills/
│
├── marketing/
│   ├── SKILL.md
│   ├── principles/
│   ├── playbooks/
│   ├── workflows/
│   ├── validators/
│   └── examples/
│
├── sales/
├── finance/
├── legal/
├── technology/
├── operations/
└── learning/
```

## 9.1 `SKILL.md`

Mỗi skill nên mô tả:

```text
Purpose
When to use
When NOT to use
Required context
Optional context
Workflow
Tool permissions
Output schema
Validation rules
Failure handling
Learning hooks
```

## 9.2 Không auto-load mọi skill

Skill Resolver chỉ load skill sau khi Job Router đã xác định job.

---

# 10. Job Runtime

Job là đơn vị trung tâm nối intent với execution.

```text
Intent
 ↓
Job Definition
 ↓
Scope
 ↓
Priming
 ↓
Skills
 ↓
Agent
 ↓
Tools
 ↓
Validation
 ↓
Outcome
```

## 10.1 Job schema đề xuất

```yaml
job_id: job_xxx
job_type: create_lead_funnel
status: planned

scope:
  company_id: xxx
  project_id: mid

agent: sales_marketing

skills:
  - sales.funnel
  - marketing.copywriting
  - crm.lead_management

tools:
  read:
    - project.read
    - crm.read
  draft:
    - landing_page.generate
    - email.draft
  action:
    - crm.write
    - email.send

approval_policy:
  draft: auto
  external_send: required
  deploy_production: required

observation:
  metrics:
    - visits
    - leads
    - qualified_leads
    - conversion_rate
```

---

# 11. COSA Action Runtime

COSA cần phát triển từ AI Assistant thành AI Operator, nhưng có permission/risk control.

```text
Action Runtime
│
├── Browser Runtime
├── Desktop Runtime
├── Files Runtime
├── Shell Runtime
├── MCP Runtime
├── API Runtime
├── Workflow Runtime / n8n
├── Email Runtime
├── CRM Runtime
├── Hosting Runtime
└── Deployment Runtime
```

## 11.1 Không để agent gọi trực tiếp tool provider

Bắt buộc đi qua:

```text
Agent
 ↓
Action Request
 ↓
Policy Engine
 ↓
Risk Classification
 ↓
Approval Engine
 ↓
Executor
 ↓
Audit Log
```

---

# 12. Action Risk & Approval Engine

## Tier 0 — Read

Ví dụ:

- đọc project;
- đọc CRM;
- analytics;
- search knowledge.

Policy:

```text
AUTO
```

## Tier 1 — Draft / Local

Ví dụ:

- tạo email draft;
- tạo landing page local;
- tạo báo cáo;
- generate code;
- chạy test local.

Policy:

```text
AUTO
```

## Tier 2 — External reversible

Ví dụ:

- gửi email;
- publish social;
- deploy staging;
- tạo campaign CRM;
- tạo workflow n8n.

Policy:

```text
CONFIGURABLE APPROVAL
```

## Tier 3 — Critical / irreversible / financial

Ví dụ:

- production deploy;
- DNS/domain change;
- delete business data;
- payment;
- purchase;
- financial transaction;
- legal submission.

Policy:

```text
STRONG APPROVAL REQUIRED
```

---

# 13. Memory Architecture

COSA không nên copy mô hình Obsidian-only của Jared.

Đề xuất:

```text
PostgreSQL
│
├── business source of truth
├── projects
├── OKRs
├── 12WY
├── CRM
├── finance
├── tasks
├── jobs
├── action logs
└── agent state

Knowledge / Markdown
│
├── skills
├── SOPs
├── policies
├── company knowledge
├── product knowledge
└── learning documents

Search / Retrieval
│
└── semantic + keyword retrieval when needed

Memory Layer
│
├── preferences
├── decisions
├── outcomes
├── failures
└── learned patterns
```

## 13.1 Memory types

```text
Preference Memory
Decision Memory
Outcome Memory
Failure Memory
Business Learning
Conversation Memory
```

## 13.2 Memory phải scoped

Không load toàn bộ memory vào mọi chat.

```text
Intent → Scope → Memory Resolver
```

---

# 14. Observe → Verify → Learn

Mỗi action quan trọng phải có feedback loop.

```text
Plan
 ↓
Act
 ↓
Observe
 ↓
Verify
 ↓
Learn
```

Ví dụ landing page:

```text
Generate
 ↓
Deploy
 ↓
Observe traffic
 ↓
Observe leads
 ↓
Observe conversion
 ↓
Compare target
 ↓
Write learning
 ↓
Improve next iteration
```

## 14.1 Learning không được tự ghi bừa

Learning Writer chỉ ghi khi:

- có outcome rõ;
- evidence đủ;
- result có ý nghĩa cho job tương lai;
- không trùng memory cũ;
- phân biệt observation và inference.

---

# 15. COSA Build Spec

Một điểm rất đáng học từ `jaredrhod/prompts` là prompt cho coding agent giống implementation specification hơn là chat prompt.

COSA nên chuẩn hóa mọi yêu cầu phát triển thành Build Spec.

```text
COSA BUILD SPEC

1. Goal
2. Problem
3. Current Architecture
4. Constraints
5. Requirements
6. Non-requirements
7. Modules affected
8. Data model
9. Interfaces
10. State machine
11. Permission model
12. Failure handling
13. Security
14. Migration
15. Tests
16. Acceptance criteria
17. Documentation
```

## 15.1 Coding flow

```text
READ
 ↓
ANALYZE
 ↓
PLAN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
VERIFY
 ↓
DOCUMENT
```

## 15.2 Không dùng prompt kiểu

```text
Làm chức năng CRM cho COSA
```

Mà phải chuyển thành spec với acceptance tests rõ ràng.

## 15.3 Build Spec nên lưu local và trở thành source of truth

**Khuyến nghị: Có.**

Build Spec nên được lưu local dưới dạng Markdown/YAML có cấu trúc, nằm cùng workspace/repository để:

- Claude Code/Codex đọc trực tiếp;
- dễ version control bằng Git;
- hoạt động offline;
- người dùng có thể kiểm tra bằng editor thông thường;
- không bị khóa vào database hoặc một UI riêng;
- thuận lợi backup, diff, rollback và review.

Cấu trúc đề xuất:

```text
.cosa/
├── specs/
│   ├── features/
│   ├── integrations/
│   ├── migrations/
│   ├── fixes/
│   └── archived/
├── skills/
├── priming/
├── policies/
└── jobs/
```

Ví dụ:

```text
.cosa/specs/features/hologram-visualizer.md
.cosa/specs/integrations/livekit-hybrid.md
.cosa/specs/fixes/chat-intent-routing.md
```

## 15.4 Dashboard được phép đọc và sửa Build Spec trực tiếp

**Khuyến nghị: Có, nhưng Dashboard không được ghi file tùy ý.**

Cần một lớp `Spec Service` ở giữa:

```text
Dashboard Spec Editor
        ↓
    Spec Service
        ↓
Schema Validation
        ↓
Permission / Lock
        ↓
Atomic File Write
        ↓
Git / Revision
        ↓
Build Agent
```

Dashboard có thể:

- liệt kê Build Spec;
- mở và đọc Markdown;
- chỉnh sửa nội dung;
- đổi trạng thái `draft / approved / implementing / verified / archived`;
- xem diff;
- rollback;
- gửi spec sang Claude Code/Codex;
- xem implementation status;
- liên kết spec với project/job;
- khóa spec khi agent đang triển khai;
- tạo revision mới thay vì âm thầm ghi đè.

### Không nên

```text
Frontend
   ↓
filesystem.write(any_path)
```

### Nên

```text
Frontend
   ↓
spec.update(spec_id, revision, content)
   ↓
validate
   ↓
write only inside .cosa/specs/
```

## 15.5 Build Spec lifecycle

```text
Draft
 ↓
Review
 ↓
Approved
 ↓
Locked for Implementation
 ↓
Implementing
 ↓
Test / Verify
 ↓
Completed
 ↓
Archived
```

Nếu user sửa spec trong lúc agent đang triển khai:

```text
Current implementation remains bound to Revision N

New edit
   ↓
Revision N+1
   ↓
Needs re-approval / re-plan
```

Điều này tránh tình trạng agent đang code theo một spec nhưng Dashboard thay đổi file giữa chừng.

## 15.6 PostgreSQL chỉ lưu metadata/index của Build Spec

Không cần đưa toàn bộ Markdown thành nguồn dữ liệu chính trong DB.

PostgreSQL lưu:

```text
spec_id
title
file_path
project_id
job_id
status
current_revision
checksum
created_at
updated_at
approved_at
implemented_at
```

File local lưu nội dung thật.

Kiến trúc:

```text
Local Markdown = source of truth
PostgreSQL     = index + state + relation
Git            = revision history
Dashboard      = editor/viewer
Claude/Codex   = consumer/executor
```

Đây là mô hình phù hợp nhất với COSA local-first.

---

# 16. Voice Architecture

Voice Line của Jared phù hợp để tham khảo cho trải nghiệm local, nhưng COSA nên chuẩn hóa voice transport bằng **LiveKit ở cả Desktop và Mobile**.

Kiến trúc hybrid được chốt như sau:

```text
COSA Voice Gateway
│
├── Desktop
│   └── LiveKit Local / Self-hosted
│       ├── local room/session
│       ├── push-to-talk hoặc realtime
│       ├── local STT khi cấu hình
│       ├── local TTS khi cấu hình
│       └── local agent bridge
│
└── Mobile
    └── LiveKit Cloud
        ├── realtime session
        ├── cloud connectivity
        ├── multi-device
        ├── remote agent
        └── roaming / NAT-friendly transport
```

## 16.1 Desktop — LiveKit Local / Self-hosted

Desktop vẫn dùng LiveKit, nhưng ưu tiên chạy local hoặc self-hosted trên chính máy/VPS riêng tùy cấu hình.

Lợi ích:

- giữ chung một realtime abstraction với Mobile;
- giảm việc duy trì hai voice stack khác nhau;
- có thể chạy local/private;
- dễ chuyển giữa push-to-talk và full realtime;
- event/state của voice thống nhất với Hologram Hub;
- agent bridge không phụ thuộc trực tiếp UI;
- thuận lợi triển khai PC/macOS riêng cho từng khách hàng.

Desktop có thể cấu hình:

```yaml
voice:
  transport: livekit_local
  mode: push_to_talk
  stt: local
  tts: local
  fallback_cloud: false
```

Hoặc:

```yaml
voice:
  transport: livekit_local
  mode: realtime
  stt: cloud_or_local
  tts: cloud_or_local
```

`push-to-talk` vẫn nên là default ban đầu vì kiểm soát tốt, ít false-trigger và dễ vận hành.

## 16.2 Mobile — LiveKit Cloud

Mobile dùng LiveKit Cloud làm lựa chọn mặc định:

```yaml
voice:
  transport: livekit_cloud
  mode: realtime
```

Lý do:

- kết nối tốt hơn khi chuyển mạng Wi‑Fi/4G/5G;
- NAT traversal và WebRTC infrastructure đã được xử lý;
- phù hợp realtime voice;
- thuận lợi kết nối remote COSA Agent;
- dễ multi-device/session;
- không bắt mobile phụ thuộc vào máy desktop đang mở cùng LAN.

## 16.3 Một Voice Contract, hai deployment mode

Điểm quan trọng là Desktop Local và Mobile Cloud **không tạo hai loại agent khác nhau**.

Cả hai cùng dùng một contract:

```text
Voice Session
 ↓
Speech Event
 ↓
Conversation Gate
 ↓
Intent Router
 ↓
Agent Runtime
 ↓
Response Stream
 ↓
Voice Session
```

Event Bus cũng thống nhất:

```text
voice.connected
voice.listening
voice.transcribing
agent.understanding
agent.thinking
agent.speaking
voice.disconnected
```

Nhờ đó Hologram Hub Visualizer không cần biết voice đang đến từ LiveKit Local hay LiveKit Cloud.

## 16.4 Routing giữa Local và Cloud

Có thể dùng policy:

```text
Desktop app
→ prefer LiveKit Local

Mobile app
→ LiveKit Cloud

Remote Desktop session
→ configurable

Local unavailable
→ optional fallback policy
```

Không tự động fallback lên Cloud nếu khách hàng cấu hình `local-only/privacy mode`.

---

# 17. Hologram Hub — Visualizer Card

## 17.1 Quyết định UI

**Visualizer không nên là một page độc lập.**

Visualizer nên hiển thị ngay trong **một Card nổi bật trên trang Hologram Hub**.

Lý do:

- Hologram Hub là nơi người dùng quan sát COSA “đang sống”; 
- card giúp theo dõi agent liên tục mà không mất context trang;
- phù hợp trải nghiệm Jarvis nhưng vẫn giữ UI quản trị rõ ràng;
- có thể thu gọn/mở rộng;
- dễ hiển thị song song các thông tin khác của Hub;
- desktop, tablet và mobile đều dễ responsive.

## 17.2 Hologram Hub layout đề xuất

```text
┌───────────────────────────────────────────────────────────────┐
│                       HOLOGRAM HUB                            │
├───────────────────────────────┬───────────────────────────────┤
│                               │                               │
│     VISUALIZER CARD           │    ACTIVE JOB CARD            │
│                               │                               │
│     Agent Presence            │    Job / Project / Progress    │
│     Avatar / Hologram         │                               │
│     Current State             │                               │
│                               │                               │
├───────────────────────────────┼───────────────────────────────┤
│     RECENT ACTIONS            │    APPROVAL / ALERTS           │
├───────────────────────────────┴───────────────────────────────┤
│     Activity timeline / agent events                          │
└───────────────────────────────────────────────────────────────┘
```

Visualizer Card là primary presence card.

## 17.3 Visualizer states

Không chỉ 5 state cơ bản. COSA nên mở rộng thành:

```text
idle
listening
understanding
routing
priming
thinking
tool_running
waiting_approval
speaking
completed
warning
error
```

## 17.4 State semantics

### `idle`

COSA đang sẵn sàng.

UI:

```text
COSA Ready
```

Không hiển thị project nếu user chưa chọn/request.

### `listening`

Voice input đang hoạt động.

UI:

```text
Listening…
```

### `understanding`

Conversation Gate đang phân tích intent.

UI:

```text
Understanding request…
```

### `routing`

Đang chọn route/job phù hợp.

UI:

```text
Routing…
```

### `priming`

Đang nạp scoped context + skills.

UI có thể hiển thị ngắn:

```text
Preparing Sales context…
```

Không expose chain-of-thought.

### `thinking`

Agent đang xử lý.

```text
Thinking…
```

### `tool_running`

Có tool/action thật sự đang chạy.

Ví dụ:

```text
Reading CRM…
Testing landing page…
Deploying staging…
```

### `waiting_approval`

Visualizer cần đổi trạng thái rõ ràng.

```text
Approval required
```

Card có CTA:

```text
Review action
```

### `speaking`

TTS/voice output.

```text
Speaking…
```

### `completed`

Job hoàn thành.

```text
Completed
```

Sau một khoảng thời gian UI có thể quay về idle.

### `warning`

```text
Needs attention
```

### `error`

```text
Action failed
```

Card cần cho phép mở detail/log.

---

# 18. Visualizer Card Data Contract

Visualizer Card không được đọc trực tiếp business services.

Nó subscribe **Agent Event Bus**.

```text
Agents / Jobs / Tools
       ↓
Agent Event Bus
       ↓
Hologram Hub Visualizer Card
```

## 18.1 Event schema đề xuất

```json
{
  "event_id": "evt_xxx",
  "timestamp": "...",
  "session_id": "...",
  "job_id": "job_xxx",
  "agent_id": "marketing_agent",
  "state": "tool_running",
  "label": "Testing landing page",
  "detail": "Running local validation",
  "progress": 0.72,
  "risk": "low",
  "requires_approval": false
}
```

## 18.2 Không gửi chain-of-thought

Visualizer chỉ hiển thị:

- state;
- activity label;
- tool name nếu cần;
- progress;
- result status;
- approval state;
- errors an toàn.

Không expose:

- hidden reasoning;
- internal chain-of-thought;
- secret;
- raw token-level prompt;
- credential.

---

# 19. Visualizer Card UX

## 19.1 Compact mode

Card mặc định:

```text
┌───────────────────────────────┐
│ COSA                          │
│                               │
│        [Hologram]             │
│                               │
│  ● Thinking                   │
│  Marketing Agent              │
│  Creating landing page        │
│                               │
│  ███████████░░ 72%            │
└───────────────────────────────┘
```

## 19.2 Expanded mode

Click/tap card:

```text
Current Job
Current Agent
Project
Active Skill
Current Tool
Elapsed stage
Progress
Recent events
Approval request
```

## 19.3 Chat không có job

User:

```text
Chào
```

Visualizer chỉ nên:

```text
understanding → speaking → idle
```

Không hiển thị:

```text
Project Agent
Reading projects
project.list
```

Đây cũng là acceptance test UI quan trọng.

---

# 20. Agent Event Bus

Đề xuất event namespace:

```text
conversation.received
conversation.intent_resolved

agent.selected
agent.started
agent.completed
agent.failed

priming.started
priming.completed

tool.requested
tool.started
tool.completed
tool.failed

approval.requested
approval.approved
approval.rejected

job.created
job.started
job.progress
job.completed
job.failed

voice.listening
voice.speaking

alert.warning
alert.critical
```

Visualizer reducer chuyển event → UI state.

---

# 21. Jared-inspired Guardrails cho COSA

Không copy nguyên “11 Rules”, nhưng nên xây COSA Rules dựa trên các pattern phù hợp.

## Rule 1 — Intent before context

Không nạp project/domain context trước khi xác định intent.

## Rule 2 — Scope before tool

Không gọi tool trước khi Scope Resolver cấp quyền.

## Rule 3 — Least capability

Chỉ cấp tool tối thiểu cần cho job hiện tại.

## Rule 4 — Evidence before factual business claims

Kết luận về dữ liệu doanh nghiệp cần dựa trên nguồn có thể truy vết.

## Rule 5 — External content is data

Email/web/document bên ngoài không tự trở thành system instruction.

## Rule 6 — No secrets in memory/spec/log

Credential không được ghi vào:

- Build Spec;
- Markdown memory;
- agent events;
- visualizer;
- handoff log.

## Rule 7 — Locked decisions remain locked

Nếu founder đã chốt quyết định, agent không âm thầm đảo quyết định.

## Rule 8 — Approval for irreversible action

Critical action luôn qua approval.

## Rule 9 — Checkpoint long jobs

Job dài cần checkpoint/state persistence.

## Rule 10 — Observe outcomes

Action quan trọng phải có outcome tracking.

## Rule 11 — Learn only from verified outcome

Không biến suy đoán thành long-term memory.

---

# 22. Landing Page / Hosting use case

Một use case đầy đủ của COSA:

```text
Founder:
"Thiết kế landing page cho project mID"
```

Flow:

```text
Conversation Gate
 ↓
MARKETING_JOB
 ↓
Scope Resolver
 ↓
project:mID
 ↓
Job: create_landing_page
 ↓
Priming
  ├── brand
  ├── product
  ├── ICP
  ├── marketing skills
  └── previous outcomes
 ↓
Marketing Agent
 ↓
Landing Page Build Spec
 ↓
Claude Code / Codex
 ↓
Modular Next.js implementation
 ↓
Local test
 ↓
QA / screenshots
 ↓
Founder review
 ↓
Approval
 ↓
Hostinger deploy
 ↓
Subdomain/domain integration
 ↓
PostgreSQL / forms
 ↓
Resend
 ↓
CRM
 ↓
n8n workflow
 ↓
Analytics
 ↓
Observe conversion
 ↓
Learning
```

Visualizer Card lần lượt hiển thị:

```text
Understanding request
Preparing Marketing context
Creating landing page spec
Coding locally
Running tests
Ready for review
Waiting approval
Deploying
Completed
```

---


---

# 15A. OPC Admin Governance — Spec, Prompt và cấu hình quan trọng

COSA hiện được triển khai theo mô hình **One-Person Company (OPC)**. Ở giai đoạn hiện tại:

```text
Founder = Admin = System Owner
```

Không cần xây UX multi-user phức tạp ngay, nhưng kiến trúc authorization phải chuẩn bị sẵn để sau này thêm nhân viên mà không phải viết lại Spec/Prompt/Agent Runtime.

## 15A.1 Nguyên tắc quyền sở hữu

Các tài nguyên ảnh hưởng trực tiếp đến hành vi hệ thống được coi là **Protected System Resources**:

```text
Build Spec
System Prompt
Agent Prompt
Priming Definition
Skill Instruction
Policy / Guardrail
Tool Permission Policy
Approval Policy
Agent Configuration
Default Templates
```

Giai đoạn OPC:

```yaml
roles:
  admin:
    default_holder: founder
    can_read_protected_resources: true
    can_edit_protected_resources: true
    can_reset_protected_resources: true
    can_approve_protected_resources: true
```

Chỉ `admin` được phép sửa hoặc reset các tài nguyên trên.

Các API backend phải enforce quyền này. Không được chỉ ẩn nút Edit ở frontend.

## 15A.2 Founder-first, RBAC-ready

Kiến trúc phải tách:

```text
User Identity
    ↓
Company Membership
    ↓
Role
    ↓
Permission
    ↓
Resource / Action
```

Ban đầu:

```text
Company
└── Founder
    └── role = admin
```

Tương lai:

```text
Company
├── Founder / Owner     → admin
├── Finance Staff       → finance role
├── Sales Staff         → sales role
├── Marketing Staff     → marketing role
└── Other Employees     → custom roles
```

Không hard-code kiểu:

```python
if user_id == founder_id:
    allow()
```

Phải kiểm tra permission:

```text
authorize(
  actor,
  action="spec.update",
  resource=spec
)
```

Nhờ vậy giai đoạn đầu chỉ có một admin nhưng hệ thống vẫn sẵn sàng mở rộng RBAC.

## 15A.3 Permission model đề xuất

Các permission nền tảng:

```text
spec.read
spec.update
spec.approve
spec.reset

prompt.read
prompt.update
prompt.reset

skill.read
skill.update
skill.reset

policy.read
policy.update
policy.reset

agent.configure
tool.configure
approval_policy.configure

employee.invite
employee.role.assign
employee.disable
```

Trong giai đoạn OPC, toàn bộ quyền quản trị này thuộc Founder/Admin.

Khi có nhân viên, mặc định **không cấp quyền sửa Spec/Prompt/System Policy**. Việc cấp quyền nhạy cảm phải là quyết định explicit của Admin.

## 15A.4 Default + Override thay vì ghi đè mặc định

Để hỗ trợ chức năng Reset an toàn, COSA không nên sửa trực tiếp bản mặc định.

Mỗi Protected Resource có hai lớp:

```text
COSA Default
     │
     ├── immutable baseline
     │
     ▼
Admin Override
     │
     ▼
Effective Configuration
```

Ví dụ:

```text
defaults/prompts/project-agent.md
        +
.cosa/overrides/prompts/project-agent.md
        ↓
Effective Project Agent Prompt
```

Hoặc với Build Spec/template:

```text
Bundled Default
      +
Admin Revision
      ↓
Effective Spec
```

`COSA Default` phải read-only trong runtime bình thường.

## 15A.5 Reset to Default

Dashboard dành cho Admin phải có:

```text
Edit
Save Revision
View Diff
Revision History
Restore Revision
Reset to Default
```

Flow Reset:

```text
Admin
 ↓
Reset to Default
 ↓
Show Diff:
Current Override ↔ COSA Default
 ↓
Explicit Confirmation
 ↓
Archive current override
 ↓
Remove/deactivate override
 ↓
Reload default
 ↓
Validate
 ↓
Reload affected runtime
 ↓
Audit event
```

Reset không được xóa lịch sử. Revision cũ vẫn phải có khả năng xem/khôi phục.

## 15A.6 Default Registry

Cần quản lý default theo registry thay vì rải file không kiểm soát:

```text
.cosa/
├── defaults/
│   ├── specs/
│   ├── prompts/
│   ├── priming/
│   ├── skills/
│   └── policies/
│
└── overrides/
    ├── specs/
    ├── prompts/
    ├── priming/
    ├── skills/
    └── policies/
```

Mỗi resource nên có metadata:

```yaml
id: project-agent-prompt
resource_type: prompt
default_revision: 1
override_revision: 4
effective_source: override
editable_by:
  - admin
resettable: true
```

## 15A.7 Dashboard Admin Editor

Dashboard có khu vực quản trị:

```text
System Configuration
│
├── Build Specs
├── Prompts
├── Skills
├── Priming
├── Policies
└── Agent Configuration
```

Card/list item hiển thị tối thiểu:

```text
Name
Type
Status
Source: Default / Customized
Current Revision
Last Updated
Updated By
```

Nếu resource đang dùng mặc định:

```text
DEFAULT
```

Nếu Admin đã sửa:

```text
CUSTOMIZED
```

Admin có thể mở editor:

```text
┌─────────────────────────────────────────┐
│ Project Agent Prompt        CUSTOMIZED  │
├─────────────────────────────────────────┤
│ Editor                                  │
│                                         │
├─────────────────────────────────────────┤
│ Diff | History | Validate               │
│                                         │
│ [Reset to Default]       [Save Revision]│
└─────────────────────────────────────────┘
```

Các nút thay đổi cấu hình chỉ render khi user có permission tương ứng, nhưng backend vẫn là nơi quyết định authorization cuối cùng.

## 15A.8 Hot Reload có kiểm soát

Sau khi Admin Save hoặc Reset:

```text
Edit
 ↓
Validate
 ↓
Save Revision
 ↓
Update effective config
 ↓
Invalidate config cache
 ↓
Reload affected Agent/Job
```

Không restart toàn bộ COSA nếu không cần thiết.

Ví dụ sửa Marketing Agent Prompt chỉ invalidate:

```text
marketing-agent
marketing-related jobs
relevant priming cache
```

Không ảnh hưởng Finance Agent đang hoạt động.

Nếu một Job đang chạy, nó tiếp tục sử dụng revision đã bind lúc bắt đầu. Revision mới chỉ áp dụng cho Job tiếp theo, trừ khi Admin chủ động yêu cầu restart/re-plan.

## 15A.9 Audit bắt buộc

Mọi thay đổi Protected Resource phải ghi:

```text
actor_id
company_id
resource_id
resource_type
action
old_revision
new_revision
timestamp
checksum
```

Các action:

```text
CREATE_OVERRIDE
UPDATE
APPROVE
RESET_TO_DEFAULT
RESTORE_REVISION
```

Không cần biến OPC thành hệ thống enterprise nặng nề, nhưng audit này rất hữu ích khi Founder thử nghiệm prompt/spec và cần biết thay đổi nào làm agent hoạt động tốt hoặc xấu đi.

## 15A.10 Tương tác với Build Agent

Claude Code/Codex được:

```text
READ spec
READ prompt
READ skill
IMPLEMENT approved spec
REPORT suggested changes
```

Mặc định không được:

```text
UPDATE protected spec
UPDATE system prompt
UPDATE policy
RESET protected resource
```

Nếu coding agent phát hiện spec cần sửa:

```text
Agent
 ↓
Propose Spec Change
 ↓
Dashboard
 ↓
Founder/Admin reviews diff
 ↓
Approve
 ↓
Create new revision
 ↓
Re-plan implementation
```

Điều này giữ Founder/Admin là người kiểm soát source of truth.

## 15A.11 Tương lai khi thêm nhân viên

RBAC mở rộng mà không thay đổi core:

```text
Employee request
 ↓
Identity
 ↓
Membership
 ↓
Role
 ↓
Permission Resolver
 ↓
Conversation / Agent / Tool / Resource Scope
```

Ví dụ Sales Staff có thể được phép:

```text
crm.read
crm.update
sales.job.run
project.read_assigned
```

nhưng không mặc định có:

```text
prompt.update
spec.update
policy.update
tool.configure
```

Finance Staff tương tự chỉ nhìn thấy dữ liệu và agent/job thuộc scope được giao.

Cần thiết kế từ bây giờ:

```text
Single-user UX today
+
Multi-user authorization architecture underneath
```

chứ không xây đầy đủ employee management ngay trong giai đoạn OPC.

## 15A.12 Acceptance Tests bắt buộc

```text
GIVEN Founder/Admin
WHEN edit Build Spec
THEN allowed

GIVEN Founder/Admin
WHEN edit System Prompt
THEN allowed and new revision created

GIVEN Founder/Admin
WHEN Reset to Default
THEN current override archived
AND default becomes effective
AND audit event created

GIVEN non-admin future employee
WHEN prompt.update
THEN backend returns forbidden

GIVEN non-admin future employee
WHEN spec.reset
THEN backend returns forbidden

GIVEN coding agent
WHEN attempting direct protected-resource mutation
THEN denied unless an explicit delegated permission exists

GIVEN Job started with prompt revision N
WHEN Admin saves revision N+1
THEN running Job remains bound to N
AND subsequent Job uses N+1
```

## 15A.13 Nguyên tắc chốt

> **Founder-first, Admin-controlled, RBAC-ready.**

COSA hiện tại không cần giả lập một doanh nghiệp nhiều nhân viên. Founder là Admin duy nhất và có trải nghiệm đơn giản.

Tuy nhiên, Spec, Prompt, Skill, Priming và Policy là tài sản điều khiển hành vi AI nên phải được bảo vệ ngay từ đầu bằng permission backend, revision, immutable default, reset và audit.

Khi COSA mở rộng cho nhân viên, chỉ cần bổ sung Membership/Role/Permission trên nền kiến trúc hiện có thay vì thay đổi Agent Runtime.

# 23. Sales use case

User:

```text
Phân tích sales project mID
```

Flow:

```text
Intent = SALES_JOB
 ↓
project:mID
 ↓
Sales Job
 ↓
Prime:
  company
  project
  product
  CRM
  funnel
  sales skills
 ↓
Read-only tools
 ↓
Analysis
 ↓
Recommendations
```

Không tự gửi email.

Nếu user tiếp tục:

```text
Soạn email follow-up cho các lead nóng
```

→ draft job.

Nếu user:

```text
Gửi email đó
```

→ action job + approval policy.

---

# 24. Regression Test bắt buộc cho Router

## Social chat

```text
INPUT: "chào"
project.list calls = 0
project.read calls = 0
tool calls = 0
heavy priming = false
```

```text
INPUT: "hello"
tool calls = 0
```

```text
INPUT: "bạn là ai?"
tool calls = 0
```

## General question

```text
INPUT: "funnel marketing là gì?"
project calls = 0
CRM calls = 0
```

## Project discovery

```text
INPUT: "tôi đang có những project nào?"
project.list = 1
```

## Project query

```text
INPUT: "kiểm tra project mID"
project.read(mID) = 1
project.list = 0 unless required for resolution
```

## Domain analysis

```text
INPUT: "phân tích sales mID"
project.read = allowed
sales.read = allowed
email.send = forbidden
```

## Draft vs action

```text
INPUT: "viết email bán hàng cho mID"
email.draft = allowed
email.send = forbidden
```

```text
INPUT: "gửi email đó"
email.send = allowed only after action resolution + policy
```

## Visualizer

```text
INPUT: "chào"
Visualizer states:
understanding -> speaking -> idle

Forbidden states:
priming_project
tool_running(project.list)
```

---

# 25. Acceptance Criteria

## P0 — Intent/Tool Safety

- [ ] “Chào” không gọi project/tool.
- [ ] General question không tự động lấy project context.
- [ ] Project tool chỉ được gọi khi intent cần project.
- [ ] Tool runtime nhận allowlist từ Capability Policy.
- [ ] `NO_TOOL` là route hợp lệ.
- [ ] có regression tests cho social/general/project/action.

## P1 — Scoped Context / Priming

- [ ] Scope Resolver tồn tại riêng.
- [ ] Priming chỉ chạy sau khi Job được xác định.
- [ ] normal chat không load business context nặng.
- [ ] mỗi Job có Priming Registry.
- [ ] context load được audit/debug ở metadata an toàn.

## P2 — Jobs / Skills

- [ ] Job schema chuẩn.
- [ ] Skill schema chuẩn.
- [ ] Agent/Skill/Memory/Context/Tool được phân lớp rõ.
- [ ] Marketing, Sales, Finance, Legal dùng chung Job Runtime.

## P3 — Action Runtime

- [ ] Agent không truy cập provider trực tiếp.
- [ ] Tool call đi qua Policy Engine.
- [ ] Risk tier được xác định.
- [ ] Critical action bắt buộc approval.
- [ ] Có audit log.

## P4 — Observe/Learn

- [ ] Jobs có outcome metrics.
- [ ] Có verification step.
- [ ] Learning chỉ ghi sau verified outcome.
- [ ] Learning có source/evidence reference.

## P5 — Hologram Hub / Visualizer

- [ ] Visualizer nằm trong card của Hologram Hub.
- [ ] Card responsive desktop/tablet/mobile.
- [ ] Visualizer subscribe Agent Event Bus.
- [ ] Card không query trực tiếp business services.
- [ ] Có compact + expanded mode.
- [ ] Có states: idle/listening/understanding/routing/priming/thinking/tool_running/waiting_approval/speaking/completed/warning/error.
- [ ] Không hiển thị chain-of-thought.
- [ ] Approval state có CTA rõ ràng.
- [ ] “Chào” không hiển thị project activity.

---

# 26. Thứ tự triển khai đề xuất

## P0 — Sửa router ngay

```text
Conversation Gate
Intent Router
Tool Permission Gate
Regression Tests
```

Đây là ưu tiên cao nhất.

## P1 — Scoped Context

```text
Scope Resolver
Memory Resolver
Priming Registry
```

## P2 — Job & Skill Runtime

```text
Job definitions
Skill registry
Job execution lifecycle
```

## P3 — Action Runtime

```text
Action request
Policy engine
Risk engine
Approval engine
Tool executor
Audit log
```

## P4 — Observe / Verify / Learn

```text
Outcome metrics
Verification
Learning writer
Memory update
```

## P5 — Hologram Hub Presence

```text
Agent Event Bus
Visualizer Card
Voice states
Approval UI
Activity timeline
```

## P6 — Voice hybrid

```text
Desktop push-to-talk
Local STT/TTS
LiveKit realtime mode
```

---

# 27. Suggested Module Boundaries

Tên cụ thể có thể đổi theo codebase hiện tại, nhưng boundary nên gần như:

```text
core/
  conversation/
    gate
    intent_router
    intent_schema

  context/
    scope_resolver
    memory_resolver
    priming_engine
    priming_registry

  jobs/
    job_router
    job_runtime
    job_store

  skills/
    registry
    resolver

  agents/
    runtime
    registry

  actions/
    planner
    policy_engine
    risk_engine
    approval_engine
    executor
    audit

  events/
    agent_event_bus

  learning/
    outcome_observer
    verifier
    learning_writer

ui/
  hologram_hub/
    visualizer_card
    active_job_card
    approval_card
    activity_timeline

voice/
  gateway
  local_ptt
  livekit
```

---

# 28. Data Entities đề xuất

## `intent_resolution`

```text
id
session_id
message_id
intent
confidence
entity_refs
needs_project
needs_tools
needs_job
created_at
```

## `job`

```text
id
type
status
company_id
project_id
agent_id
risk_level
created_at
started_at
completed_at
```

## `job_context`

```text
job_id
context_type
resource_ref
source
loaded_at
```

## `job_skill`

```text
job_id
skill_id
version/hash
loaded_at
```

## `action_request`

```text
id
job_id
action_type
provider
risk_level
approval_status
status
created_at
```

## `agent_event`

```text
id
session_id
job_id
agent_id
state
label
detail_safe
progress
risk
requires_approval
created_at
```

## `job_outcome`

```text
job_id
metric
expected
actual
verified
source_ref
```

## `learning_memory`

```text
id
scope_type
scope_id
lesson
source_job_id
evidence_ref
confidence
created_at
```

---

# 29. Performance & Cost Notes

Intent-first routing còn giúp giảm chi phí:

```text
"Chào"
```

không cần:

- PostgreSQL project lookup;
- large context;
- vector search;
- multiple agent calls;
- tool execution;
- complex reasoning model.

Có thể áp dụng model routing:

```text
SOCIAL_CHAT / SIMPLE QA
        ↓
lightweight chat model

BUSINESS ANALYSIS
        ↓
reasoning model

CODING JOB
        ↓
Claude Code / Codex
```

Điều này phù hợp với COSA local-first + multi-model architecture.

---

# 30. Security Notes

- Tool allowlist mặc định rỗng.
- Credential nằm trong secret manager/environment, không nằm trong memory.
- Event Bus chỉ chứa safe metadata.
- Visualizer không được hiển thị raw prompt/internal reasoning.
- External web/email/document phải qua content isolation.
- Approval Engine phải chống replay action.
- Action executor nên idempotent khi có thể.
- Production action có audit trail.
- Job context phải tenant/company scoped.

---

# 31. Licensing / Clean-room Implementation

Các tài nguyên công khai của Jared Rhod cần được kiểm tra license trước khi sử dụng trực tiếp trong sản phẩm thương mại. Cách triển khai an toàn cho COSA:

```text
Study concept
 ↓
Extract architecture principles
 ↓
Write COSA-native specification
 ↓
Implement independently
 ↓
Use COSA naming/data model/tests
```

Không nên:

```text
Copy prompt/repo content
 ↓
Rename
 ↓
Bundle vào COSA commercial product
```

Tài liệu này chủ đích mô tả **COSA-native implementation** dựa trên các pattern kiến trúc đã phân tích.

---

# 32. Source References

Các nguồn tham khảo để hiểu ý tưởng gốc:

- Jared Rhod website: https://jaredrhod.com
- AI Priming: https://jaredrhod.com/ai-priming
- Jared Prompts repository: https://github.com/jaredrhod/prompts
- AI Memory Vault: https://github.com/jaredrhod/ai-memory-vault
- AI Marketing Skills: https://github.com/jaredrhod/ai-marketing-skills

Các source trên dùng để nghiên cứu pattern; implementation của COSA phải độc lập và phù hợp licensing của sản phẩm.

---

# 33. Kiến trúc tổng hợp cuối cùng

```text
                         USER
                          │
                    Chat / Voice
                          │
                          ▼
                 ┌──────────────────┐
                 │ Conversation Gate│
                 └────────┬─────────┘
                          │
                          ▼
                   Intent Router
                          │
                          ▼
                  Capability Policy
                          │
                          ▼
                    Scope Resolver
                          │
               ┌──────────┴──────────┐
               │                     │
          Normal Chat              Job Router
               │                     │
               │                     ▼
               │               Priming Engine
               │                     │
               │               Skill Resolver
               │                     │
               │                     ▼
               │                Agent Runtime
               │                     │
               │                     ▼
               │                Action Planner
               │                     │
               │                     ▼
               │                 Risk Engine
               │                     │
               │                     ▼
               │               Approval Engine
               │                     │
               │                     ▼
               │                Tool Runtime
               │                     │
               │                     ▼
               │                  Observe
               │                     │
               │                     ▼
               │                   Verify
               │                     │
               │                     ▼
               │                   Learn
               │                     │
               └────────────┬────────┘
                            │
                            ▼
                     Agent Event Bus
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
     Chat / Voice      Hologram Hub       Activity Log
                           │
                           ▼
                   ┌────────────────┐
                   │ Visualizer Card│
                   │ Agent Presence │
                   └────────────────┘
```

---

# 34. Kết luận triển khai

Lần điều chỉnh này nên coi là một thay đổi kiến trúc nền tảng, không đơn thuần thêm Voice hoặc Visualizer.

Ba nguyên tắc cần khóa:

> **1. COSA hiểu trước khi hành động.**
>
> **2. COSA chỉ nạp context và cấp tool theo đúng scope của yêu cầu.**
>
> **3. Hologram Hub Visualizer Card giúp founder nhìn thấy COSA đang làm gì mà không làm lộ reasoning nội bộ.**

Công thức lõi của COSA sau tích hợp:

```text
Understand → Route → Scope → Prime → Reason → Act → Observe → Verify → Learn
```

Và đối với câu đơn giản như:

```text
Chào
```

hành vi đúng phải luôn là:

```text
Social Chat
 ↓
No Project
No Tool
No Job
 ↓
Natural Response
```

Đây là acceptance criterion bắt buộc trước khi mở rộng Action Runtime, Voice và Visualizer.
