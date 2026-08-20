# OPC OS — Đề xuất kiến trúc Google ADK + DeepSeek Harness + Hybrid Workforce

## 1. Mục tiêu kiến trúc

OPC OS được định hướng là một **Operating System cho doanh nghiệp**, ưu tiên cài đặt trên desktop của Founder nhưng vẫn có khả năng chạy trên VPS/Web và mở rộng từ mô hình Founder + AI Agents sang tổ chức có cả **AI Employee và Human Employee**.

Kiến trúc nên tách rõ ba trách nhiệm:

- **OPC OS Core** sở hữu dữ liệu và luật vận hành doanh nghiệp: Organization, Workforce, Task, Outcome, Knowledge, Permission, Approval, Budget, Cost và Audit.
- **Google ADK** làm orchestration/control-flow engine cho Mission và workflow đa agent.
- **DeepSeek Harness** làm execution runtime mạnh cho các specialist cần reasoning dài, coding, filesystem, repository, shell hoặc sandbox.

Nguyên tắc quan trọng:

> OPC OS phải là System of Record. Google ADK và DeepSeek Harness chỉ là execution engines có thể thay thế.

---

## 2. Kiến trúc tổng thể đề xuất

```text
                 ┌──────────────────────────┐
                 │        OPC OS UI         │
                 │ Flutter Desktop / Web    │
                 └────────────┬─────────────┘
                              │
                    Mission / Chat / Task
                              │
                 ┌────────────▼─────────────┐
                 │       OPC OS Core        │
                 │ Identity / Workforce     │
                 │ Task / Outcome / Vault   │
                 │ Policy / Approval / Cost │
                 └────────────┬─────────────┘
                              │
                     Durable Mission Job
                              │
              ┌───────────────▼──────────────┐
              │ GOOGLE ADK ORCHESTRATOR     │
              │ Graph / Dynamic Workflow    │
              │ Routing / HITL / Fan-in/out │
              └───────────────┬──────────────┘
                              │
             ┌────────────────┼─────────────────┐
             │                │                 │
        Native OPC        DeepSeek          Human
         Workers           Harness          Employee
             │                │                 │
             └────────────┬───┴─────────────────┘
                          │
                 Governed Capability
                      Gateway
                          │
        ┌─────────────────┼───────────────────┐
        │                 │                   │
       MCP               n8n             OpenSandbox/
 Integrations          Workflows          Local Device
```

---

## 3. Vai trò của Google ADK

Google ADK nên thay dần phần **control flow** hiện đang nằm trong Chief of Staff/mission orchestration, nhưng không thay các domain service của OPC.

ADK phù hợp cho:

- Mission planning.
- Routing specialist.
- Graph workflow.
- Branching.
- Parallel execution.
- Fan-out / fan-in.
- Retry/refinement loops.
- Human-in-the-loop.
- Resume workflow sau approval.
- Phối hợp AI + Human.

Một Mission nên có dạng:

```text
START
  ↓
Build Company Context
  ↓
Classify Mission
  ↓
Plan
  ↓
Specialist Router
  ├─ Sales
  ├─ Finance
  ├─ Marketing
  └─ Legal
       ↓
      JOIN
       ↓
   Synthesize
       ↓
   Risk Check
       ↓
 R0/R1 ──────────────→ Execute
 R2/R3/R4 → Approval → Execute
                           ↓
                      Quality Gate
                           ↓
                        COMPLETE
```

ADK không nên trực tiếp sở hữu:

- Permission.
- Approval records.
- Budget.
- Cost ledger.
- Task state.
- Company knowledge.
- Workforce identity.

Những phần này phải tiếp tục nằm trong OPC Core.

---

## 4. Vai trò của DeepSeek Harness

DeepSeek Harness nên nằm dưới abstraction `AgentRuntime` và được sử dụng cho các specialist có execution trajectory phức tạp.

Phù hợp nhất với:

- Coding.
- Phân tích repository.
- Technical research.
- Filesystem work.
- Shell command.
- Sandbox execution.
- Multi-step reasoning.
- Long-running specialist task.

Kiến trúc mong muốn:

```text
Google ADK
   ↓
Specialist Task
   ↓
DeepSeek Harness
   ↓
OPC Governed Tool Broker
   ↓
Policy / Approval / Audit
   ↓
MCP / API / n8n / Sandbox / Device
```

DeepSeek không nên nhận trực tiếp credential Gmail, S3, CRM hay Finance DB.

Nó chỉ được thấy capability như:

```text
opc.sales.pipeline.read
opc.finance.report.read
opc.gmail.send
opc.github.patch
opc.drive.search
opc.deployment.create
```

OPC Core kiểm tra quyền, risk, budget, approval và audit trước khi thực thi tool.

---

## 5. Hybrid Workforce: Human + AI chung một mô hình

Codebase hiện đã có nền tảng tốt cho hybrid workforce:

```text
WorkforceMember
  member_type = HUMAN | AI_AGENT
```

Task cũng đã có:

```text
execution_mode = HUMAN | AGENT | HYBRID
assignee_member_id
owner_member_id
```

Không nên tạo task engine riêng cho Human và AI.

Mô hình đề xuất:

```text
AgentDefinition
      ↓
WorkforceMember
      ↓
Task
      ↓
AgentRun / Human Work
```

Human:

```text
User
 ↓
WorkforceMember(HUMAN)
 ↓
Task
```

AI:

```text
AgentDefinition
 ↓
WorkforceMember(AI_AGENT)
 ↓
Task
 ↓
AgentRun
```

### Vấn đề cần xử lý sớm

Hiện codebase có đồng thời:

- `agents`
- `agent_definitions`

Trong khi workforce và permission đang tham chiếu hai mô hình khác nhau.

Nên chọn `AgentDefinition` làm **canonical AI employee definition**, còn `WorkforceMember` là instance nhân sự của công ty.

Về lâu dài permission nên target:

```text
WORKFORCE_MEMBER
SERVICE
DEVICE
```

thay vì phụ thuộc trực tiếp vào `USER` hoặc `AGENT`.

---

## 6. Database: PostgreSQL là lựa chọn chính

Không nên xem PostgreSQL, Supabase và InsForge là ba lựa chọn cùng tầng.

Kiến trúc nên là:

```text
Database engine:
PostgreSQL

Managed platform:
Supabase / managed PostgreSQL / self-hosted PostgreSQL

Agent-native external backend:
InsForge
```

OPC hiện đã dùng nhiều tính năng PostgreSQL native:

- JSONB.
- pgvector.
- TSVECTOR.
- `FOR UPDATE SKIP LOCKED`.
- Transactional outbox.
- LISTEN/NOTIFY.
- SQLAlchemy.
- Alembic.

Vì vậy PostgreSQL nên là canonical database của OPC OS.

---

## 7. Có nên dùng SQLite?

Có, nhưng không làm main database.

SQLite phù hợp cho:

- Flutter cache.
- UI state.
- Offline draft.
- Local search cache.
- ADK development/test session.
- Lightweight local metadata.

Không nên dùng SQLite cho:

- Mission.
- Task authoritative state.
- Approval.
- Finance ledger.
- Multi-worker execution.
- pgvector knowledge core.
- Human team collaboration.

Không nên cố làm toàn bộ domain model chạy song song cả SQLite và PostgreSQL vì code hiện phụ thuộc nhiều tính năng PostgreSQL-specific.

---

## 8. Desktop-first: Local PostgreSQL

### Personal Desktop Mode

Đây nên là mode mặc định cho Founder.

```text
OPC Desktop
  │
  ├─ Flutter
  ├─ OPC API
  ├─ PostgreSQL + pgvector
  ├─ Worker
  └─ Local Vault
```

Ưu điểm:

- Offline.
- Privacy.
- Low latency.
- Founder giữ dữ liệu chính.
- Agent truy cập được local file, repository và device.
- Không phải phụ thuộc cloud liên tục.

Không cần chạy full Supabase stack ở desktop.

Local PostgreSQL nhẹ và phù hợp với code hiện tại hơn nhiều.

---

## 9. Team/Web Mode

Khi có nhiều Human Employee, nên chuyển authority của workspace lên cloud.

```text
              Managed Cloud
                   │
            PostgreSQL
                   │
       ┌───────────┼───────────┐
       │           │           │
 Founder      Employee A    Employee B
 Desktop          Web          Desktop
```

Cloud PostgreSQL là System of Record.

Desktop giữ:

- Local cache.
- Downloaded Vault.
- Offline draft.
- Local execution capability.
- Sync outbox.

Khi Personal Workspace cần team collaboration, có thể có chức năng:

```text
Promote to Team Workspace
```

để migrate authority từ local lên cloud.

---

## 10. Không nên active-active Local ↔ Cloud ngay

Không nên để cùng một aggregate có thể ghi đồng thời ở cả local và cloud.

Nếu làm active-active sớm sẽ phải giải quyết:

- Conflict resolution.
- Deletion race.
- Clock skew.
- FK ordering.
- Approval race.
- Finance race.
- Permission race.
- Schema migration.
- Partial sync.

Nên áp dụng nguyên tắc:

> Một aggregate chỉ có một authority tại một thời điểm.

Ví dụ:

### Personal Mode

```text
Local PostgreSQL = authority
Cloud = control plane
```

### Team Mode

```text
Cloud PostgreSQL = authority
Desktop = replica/cache/executor
```

---

## 11. Supabase: phù hợp cho Cloud/Team Plane

Supabase phù hợp nếu muốn có:

- Managed PostgreSQL.
- Auth.
- Storage.
- Realtime.
- Backup.
- Operational tooling.

Khuyến nghị:

```text
OPC Core → PostgreSQL contract
Supabase → một implementation của Cloud PostgreSQL platform
```

Không nên để business logic phụ thuộc sâu vào Supabase-specific API nếu PostgreSQL chuẩn đã giải quyết được.

Realtime chỉ nên dùng cho:

- Live dashboard.
- UI refresh.
- Presence.
- Notification.

Durable sync vẫn nên đi qua transactional Outbox/Inbox.

---

## 12. InsForge: không nên làm OPC System of Record

InsForge hấp dẫn vì agent-native và hỗ trợ:

- PostgreSQL.
- Auth.
- Storage.
- Realtime.
- Functions.
- MCP/CLI.

Nhưng OPC hiện đã tự sở hữu phần lớn các capability tương tự.

Nếu dùng InsForge làm core backend ngay sẽ có overlap lớn.

Vị trí phù hợp hơn:

```text
OPC OS
  ↓
Software Engineer Agent
  ↓
DeepSeek Harness
  ↓
InsForge MCP
  ↓
Tạo backend cho project do OPC sinh ra
```

Ví dụ Founder yêu cầu:

> Tạo một mini CRM cho đội Sales.

OPC có thể dùng DeepSeek + InsForge để dựng backend của mini CRM đó.

Như vậy:

```text
OPC OS core        → PostgreSQL
Generated apps     → InsForge optional
```

---

## 13. File storage và Vault

Nên tách rõ:

```text
PostgreSQL
= metadata + operational state

Blob Store
= file content
```

Tạo abstraction:

```text
BlobStore
  put()
  get()
  delete()
  signed_url()
```

Implementations:

```text
LocalBlobStore
S3BlobStore
SupabaseStorageBlobStore
```

### Desktop

```text
~/.opc/
  data/
    postgres/
  vault/
    objects/
    working/
  runtime/
  cache/
```

### Cloud

Dùng S3-compatible:

- AWS S3.
- Cloudflare R2.
- Supabase Storage.
- MinIO.
- Provider S3-compatible khác.

Business logic chỉ lưu `object_key`, không phụ thuộc vendor.

---

## 14. Markdown và TXT nên là lớp knowledge portable

`.md` và `.txt` rất phù hợp làm human-readable knowledge.

Ví dụ:

```text
Company Vault/

00_company/
  vision.md
  values.md

01_strategy/
  strategy-2026.md
  decisions/

02_sales/
  playbook.md
  ICP.md

03_marketing/
  brand-guide.md

04_finance/
  policies.md

agents/
  chief-of-staff.md
  cfo.md

skills/
  customer-interview.md
```

Nguyên tắc:

```text
Markdown = portable company knowledge
PostgreSQL = operational truth
```

Không nên lưu bằng Markdown:

- Task status.
- Approval status.
- Finance transaction.
- Permission.
- Worker lease.
- Budget ledger.

---

## 15. Google Drive: external knowledge source

Google Drive không nên là System of Record của OPC.

Nên coi Drive là external source:

```text
Google Drive
   ↓
Connector
   ↓
VaultRevision
   ↓
Normalize to text/markdown
   ↓
Chunks + embeddings
   ↓
KnowledgeObject
```

Database nên giữ provenance:

```text
source_type
source_id
source_url
source_modified_at
source_hash
last_synced_at
```

Nhờ đó nếu Drive bị mất quyền, đổi folder hoặc file bị rename, OPC vẫn còn company memory đã ingest.

---

## 16. Knowledge & Memory Architecture

Không nên đưa mọi thứ vào vector database.

Nên chia nhiều tầng:

```text
L0 Runtime Context
ADK / DeepSeek session

L1 Episodic Memory
AgentRun / Events / Conversation

L2 Semantic Knowledge
Vault / Markdown / KnowledgeObject / pgvector

L3 Operational Truth
Task / CRM / Finance / Approval / Project

L4 External Sources
Drive / Gmail / GitHub / Web / MCP
```

Ví dụ:

> “Doanh thu quý này bao nhiêu?”

→ query operational Sales/Finance tables.

> “Tại sao công ty chọn PostgreSQL?”

→ search KnowledgeObject/ADR/Vault.

---

## 17. ADK Session Storage

ADK session nên persist bằng PostgreSQL.

Có thể dùng schema riêng:

```text
public/
  tasks
  workforce
  approvals
  outcomes
  vault

adk_runtime/
  sessions
  state
  events
```

ADK state chỉ là runtime state, không phải System of Record.

Flow chuẩn:

```text
ADK State
   ↓
Result
   ↓
OPC Domain Service
   ↓
Validate + Transaction
   ↓
Canonical PostgreSQL State
```

---

## 18. Runtime Session abstraction

Nên thêm bảng chung:

```text
runtime_sessions
────────────────────
id
workspace_id
mission_run_id
agent_run_id

runtime_type
  ADK
  DEEPSEEK_HARNESS
  HUMAN
  OPENSANDBOX

external_session_id
parent_session_id
status
checkpoint_ref
metadata_jsonb
created_at
updated_at
finished_at
```

Ví dụ một Mission có thể gồm:

```text
Mission #500
│
├─ ADK session
├─ Sales AI
│    └─ DeepSeek session
├─ Engineer AI
│    └─ DeepSeek session
│         └─ OpenSandbox execution
└─ Human CFO
     └─ Task
```

---

## 19. Unified Event/Audit Ledger

Mọi runtime nên normalize event về một event model chung:

```text
MISSION_STARTED
PLAN_CREATED
SPECIALIST_DELEGATED
TOOL_REQUESTED
APPROVAL_REQUIRED
HUMAN_ASSIGNED
HUMAN_RESPONDED
EXECUTION_STARTED
ARTIFACT_CREATED
QUALITY_GATE_FAILED
MISSION_COMPLETED
```

ADK có session riêng.

DeepSeek có trajectory riêng.

Nhưng OPC event ledger phải là canonical audit timeline.

---

## 20. Worker architecture

Hiện worker đang gom quá nhiều trách nhiệm.

Khi đưa ADK vào nên tách logic worker thành tối thiểu:

```text
orchestrator-worker
execution-worker
document-worker
integration-worker
```

Chưa cần Kafka hoặc RabbitMQ.

PostgreSQL queue + `FOR UPDATE SKIP LOCKED` vẫn phù hợp trong giai đoạn hiện tại.

---

## 21. Desktop Device Executor

Desktop execution không nên là endpoint nhận arbitrary shell command.

Nên chuyển thành governed device executor:

```text
Device Enrollment
      ↓
Signed Job
      ↓
Capability Allowlist
      ↓
Workspace Binding
      ↓
Sandbox / Path Policy
      ↓
Execution
      ↓
Audit Result
```

Cần có:

- Device credential.
- Nonce.
- Expiry.
- Job ID.
- Workspace ID.
- Capability.
- Allowed path.
- Timeout.
- Resource limits.
- Audit log.

---

## 22. Lựa chọn công nghệ cuối cùng

| Thành phần | Lựa chọn |
|---|---|
| Orchestration | Google ADK |
| Specialist execution | DeepSeek Harness |
| Governance | OPC native |
| Workforce | Unified Human + AI |
| Main database | PostgreSQL |
| Desktop database | Local PostgreSQL + pgvector |
| Cloud database | Managed PostgreSQL / Supabase |
| SQLite | UI cache, draft, test |
| Local blobs | Local filesystem |
| Cloud blobs | S3-compatible / Supabase Storage |
| Portable knowledge | Markdown / TXT |
| Semantic search | PostgreSQL + pgvector |
| Google Drive | External knowledge connector |
| InsForge | Optional capability cho generated apps |
| Durable queue | PostgreSQL |
| Audit | OPC Event Ledger |
| Human approval | OPC Task + Approval |
| Sandbox | OpenSandbox / governed local executor |

---

## 23. Roadmap đề xuất

### Phase 1 — Stabilize Core

- Hợp nhất `Agent` và `AgentDefinition`.
- Xác định `WorkforceMember` là identity của employee.
- Chuẩn hóa permission theo WorkforceMember.
- Sửa Desktop Worker security.
- Chuẩn hóa Runtime Session.
- Tách BlobStore abstraction.

### Phase 2 — Google ADK Pilot

Tạo một ADK workflow read-only:

```text
Company Diagnosis
  ├─ Sales
  ├─ Finance
  └─ Marketing
```

ADK chỉ đọc dữ liệu và tạo proposal.

Chief of Staff hiện tại vẫn là fallback qua feature flag.

### Phase 3 — ADK + DeepSeek

ADK delegate coding/research task sang DeepSeek Harness.

DeepSeek trả về structured `SubRunResult`.

### Phase 4 — Governed Tool Gateway

ADK, DeepSeek, Chat và các runtime khác dùng chung một capability gateway.

Không runtime nào được giữ credential trực tiếp.

### Phase 5 — Durable Human-in-the-loop

Workflow có thể pause.

Tạo Task/Approval cho Founder hoặc Human Employee.

Sau khi Human xử lý, workflow resume.

### Phase 6 — Team Workspace

Cho phép promote Personal Local Workspace thành Team Cloud Workspace.

Cloud PostgreSQL trở thành authority.

### Phase 7 — Extended Platform

Thêm:

- Google Drive sync.
- External human contractors.
- More runtimes.
- InsForge-generated internal tools/apps.
- Advanced workforce scheduling và capacity.

---

# Kết luận

Kiến trúc nên được chốt theo nguyên tắc:

```text
Google ADK
= Orchestrator

DeepSeek Harness
= Specialist Execution Runtime

OPC OS
= Company Operating System + System of Record

PostgreSQL
= Canonical Database

WorkforceMember
= Unified Human + AI employee identity

Markdown
= Portable Knowledge

S3 / Local FS
= Blob Storage

Google Drive
= External Knowledge Source

Supabase
= Optional Managed Cloud Platform

InsForge
= Optional Agent-Buildable Backend Platform
```

Điểm quan trọng nhất là không để OPC trở thành wrapper cho một framework AI cụ thể.

Nếu ranh giới giữa **OPC Core / ADK / DeepSeek Harness / Storage / Human Workforce** được giữ đúng, sau này có thể thay hoặc thêm Gemini, Claude, Codex, local model, Human Employee hay một runtime mới mà không phải thay Company Operating Model ở phía trên.
