# CLAUDE.md

# COSA Core Coding Rules

COSA is a **Founder / Company Operating System with a composable Agent Harness**.

Do not treat COSA as a collection of independent AI agents.

---

## 1. Architecture First

Before coding:

1. Inspect the existing code.
2. Reuse existing components when possible.
3. Identify the correct architecture layer.
4. Make the smallest safe change.
5. Preserve existing working behavior.

Do not perform large rewrites unless explicitly required.

---

## 2. COSA Architecture

Use this mental model:

```text
COSA
├── Business Core
├── Co-founder Orchestrator
├── Agent Runtime
├── Agent Profiles
├── Skills
├── Tools
├── Workflows
├── Knowledge
├── Memory / Sessions
└── Executors
```

Current concrete instantiation (update when it changes, not fixed forever): Co-founder Orchestrator = Google ADK; executing Agent Runtime = DeepSeek Harness via the `AgentRuntime` adapter. Check `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` for the current canonical owner of each component before adding code.

Business Core must remain independent from LLM vendors.

---

## 3. Agent Rule

Do not create a new Agent by default.

First decide whether the requested capability is actually a:

```text
Skill
Tool
Workflow
Knowledge
Executor
Integration
```

Create a new Agent Profile only when there is a real new business role.

Marketing, Sales, Finance, Legal, Research, etc. are profiles using the same Agent Runtime.

---

## 4. Agent Composition

Use:

```text
Agent
=
Profile
+
Model
+
Context
+
Skills
+
Tools
+
Workflows
+
Permissions
+
Runtime
```

Avoid duplicated prompts, tools, skills, or runtimes between agents.

---

## 5. Business Core

Business entities such as:

```text
Company
Project
OKR
Task
CRM
Marketing
Sales
Finance
Legal
```

must not depend directly on:

```text
DeepSeek
Claude
OpenAI
DeepSeek Harness
```

Use stable COSA interfaces/adapters.

Workforce (human or AI) must resolve through one unified identity (`WorkforceMember`) — do not create separate personnel concepts/tables for AI versus humans.

---

## 6. DeepSeek Harness

DeepSeek Harness is an optional runtime implementation.

Use:

```text
COSA AgentRuntime
        ↓
DeepSeekHarnessAdapter
```

Never couple COSA Business Core directly to DeepSeek Harness internals.

Do not fork DeepSeek Harness into COSA core.

---

## 6a. Google ADK Orchestrator

Google ADK is the orchestration runtime for the Co-founder Orchestrator layer.

Use:

```text
COSA Co-founder Orchestrator
        ↓
AdkCofounderOrchestrator
```

ADK never calls a model provider or tool/domain logic directly — always through the existing ModelGateway and GovernanceKernel/TaskBoardService.

Do not fork governance logic into ADK.

---

## 7. Claude Code / Codex

Claude Code and Codex are **coding executors**, not the COSA Agent Runtime.

Correct flow:

```text
COSA
→ Coding Workflow
→ Executor
→ Claude Code / Codex
```

---

## 8. Skills, Tools and Workflows

Use:

* **Skill** = how to perform something.
* **Tool** = executable capability.
* **Workflow** = repeatable multi-step process.

Do not hide deterministic business workflows inside long prompts.

Prefer reusable Skills + Tools + Workflows.

---

## 9. Intent and Context

Never trigger project analysis from a greeting or unrelated conversation.

Example:

```text
"chào"
```

must not automatically:

```text
load project
search project database
run project workflow
```

Load project context only when the user, UI, session, or workflow explicitly requires it.

---

## 10. Local First

Company operational data is local/private by default.

Prefer:

```text
PostgreSQL
→ business data

SQLite
→ sessions, traces, cache

Markdown / Files
→ knowledge, prompts, skills, specs, templates

COSA Server
→ license, tier, entitlement, update metadata
```

Do not introduce automatic cloud synchronization without explicit requirements.

A business data aggregate has exactly one authority at a time (Personal Mode: local; Team Mode: cloud, switched via an explicit action) — do not design active-active.

---

## 11. Permissions

Permissions must be enforced by deterministic code, not by the LLM.

High-risk actions such as:

```text
production deployment
destructive database changes
sending external messages
credential changes
financial actions
```

must require appropriate permission/approval.

---

## 12. Sessions and Trace

Meaningful Agent executions should be traceable.

Track operational events such as:

```text
intent
context
skill
workflow
tool
result
artifact
error
status
```

Do not store or expose private chain-of-thought.

---

## 13. Structured State

Application state must be structured.

Do not make UI logic depend on parsing natural-language AI responses.

Prefer:

```json
{
  "status": "completed"
}
```

over detecting words such as `"done"` or `"completed"` in chat text.

---

## 14. No Duplicate Architecture

Before adding a:

```text
prompt
skill
tool
workflow
agent
service
```

search the repository first.

Prefer composition and reuse over duplication.

Before adding a new Agent/personnel identity model, read `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` — see the `Agent`/`AgentDefinition`/`AgentProfile`/`WorkforceMember` fragmentation history (4 duplicate models found 2026-08-20) as a concrete example of what happens without checking first.

---

## 15. External Projects

When integrating an external repository or framework, classify what COSA actually needs:

```text
Runtime
Skill
Tool
Workflow
Memory
Knowledge
Executor
Integration
UI
```

Do not copy entire projects by default.

---

## 16. Coding Safety

Before significant changes:

```bash
git status
```

Do not destroy or overwrite existing user changes.

Avoid destructive commands unless explicitly required.

Database schema changes must use migrations.

Never hardcode or commit API keys/secrets.

---

## 17. Testing

Add or update tests for changed behavior.

Important regression rule:

```text
"chào"
```

must never trigger automatic project lookup.

Do not claim completion without validating the affected functionality.

---

## 18. COSA North Star

When choosing between:

```text
more agents
vs
better composition
```

choose **better composition**.

When choosing between:

```text
more prompt logic
vs
deterministic application logic
```

choose **deterministic application logic**.

When choosing between:

```text
vendor coupling
vs
COSA abstraction
```

choose **COSA abstraction**.

A new capability should normally be implemented as:

```text
Skill
+
Tool
+
Workflow
+
Agent Profile assignment
```

not as another independent AI system.

---

## 19. Code Comment Language

Comment trong code (docstring, inline comment, giải thích logic) viết bằng **tiếng Việt** để dễ đọc hiểu.

Ngoại lệ: tên định danh (biến, hàm, class, module), thông báo lỗi hiển thị cho hệ thống/log, và comment trích dẫn nguyên văn từ tài liệu/blueprint tiếng Anh vẫn giữ tiếng Anh — chỉ phần giải thích ý nghĩa/lý do (why) chuyển sang tiếng Việt.

Không bắt buộc viết lại toàn bộ comment tiếng Anh đã có sẵn trong codebase ngay lập tức — áp dụng cho comment mới thêm vào từ nay trở đi; có thể chuyển dần comment cũ sang tiếng Việt khi sửa file đó.

---

## 20. Quy Tắc Cấu Trúc & Logic Cho Encore.ts

Toàn bộ backend microservices xây dựng trên **Encore.ts** phải tuân thủ nghiêm ngặt cấu trúc phân tầng (Layered Architecture) và các quy ước sau:

**Lưu ý cấu trúc app (2026-08-23):** `services/` chứa 2 Encore app độc lập, mỗi app có `encore.app` riêng — `services/company/` (chạy local: `identity`, `operations`, `commercial`, `finance-legal`, `shared`) và `services/cosa/` (chạy trên VPS: tenancy/license/agent-policy). Mỗi service `<service-name>/` mô tả dưới đây nằm bên trong 1 trong 2 app đó, không phải trực tiếp dưới `services/`.

### 20.1. Cấu Trúc Thư Mục Dịch Vụ Chuẩn (Service Directory Layout)

Mỗi service trong thư mục `services/<app>/<service-name>/` phải có cấu trúc nhất quán:

```text
services/<service-name>/
├── encore.service.ts      # Khởi tạo Encore Service: export default new Service("<service-name>")
├── api.ts                 # Barrel export tập trung (handlers, services, models)
├── db.ts                  # Khởi tạo SQLDatabase (encore.dev/storage/sqldb) và Drizzle ORM instance
├── handlers/              # API Endpoint definitions, DTO Request/Response, Routing, Header extraction
│   ├── <domain>.handler.ts
│   └── index.ts
├── services/              # Business Logic Layer (nghiệp vụ thuần túy, DB queries, transactions)
│   ├── <domain>.service.ts
│   └── index.ts
├── models/                # Re-export Drizzle DB instance & schema cho service này
│   ├── db.ts              # export { db, schema, ... } from "../db" (schema thật nằm ở services/shared/db/schema/<service>.ts)
│   └── index.ts
├── migrations/            # File SQL migration tuần tự (1_init.up.sql, 2_add_field.up.sql,...)
└── tests/                 # Unit & Integration tests cho service (.test.ts)
```

---

### 20.2. Phân Tách Trách Nhiệm (Separation of Concerns)

#### A. Handlers Layer (`handlers/`)
* **Chức năng**: Là cổng giao tiếp (API Gateway/Controller) tiếp nhận request HTTP/RPC từ bên ngoài hoặc nội bộ.
* **Quy tắc**:
  1. Định nghĩa endpoint bằng `api(...)` từ `encore.dev/api`.
  2. Khai báo rõ ràng cấu hình endpoint: `method`, `path`, `expose` và `auth`.
  3. Định nghĩa và export đầy đủ các Interface/Type cho Request DTO, Response DTO, Query Params, Headers (sử dụng `Header<"Authorization">` khi cần parse token thủ công).
  4. **Tuyệt đối KHÔNG**: Viết câu lệnh truy vấn database trực tiếp, thực thi transaction, hoặc chứa logic nghiệp vụ phức tạp bên trong handler.
  5. Nhiệm vụ duy nhất của Handler: Parse/validate input DTO & headers -> Gọi hàm tương ứng trong `services/` -> Trả về kết quả cho client.

#### B. Services Layer (`services/`)
* **Chức năng**: Xử lý toàn bộ logic nghiệp vụ (Core Business Logic) và tương tác dữ liệu.
* **Quy tắc**:
  1. Tổ chức thành các hàm async độc lập (ví dụ: `createCompanyService`, `validateUserMembership`).
  2. Thực hiện kiểm tra điều kiện nghiệp vụ, phân quyền theo role, xác thực dữ liệu đầu vào.
  3. Tương tác với cơ sở dữ liệu qua **Drizzle ORM** instance; sử dụng `db.transaction(async (tx) => { ... })` khi cần đảm bảo tính toàn vẹn dữ liệu qua nhiều bước.
  4. Gọi sang các service khác (cross-service RPC) khi cần dữ liệu/hành động từ domain khác.
  5. Trả về data sạch hoặc ném lỗi chuẩn qua `APIError`.

#### C. Models & Database Layer (`models/` & `migrations/`)
* **Chức năng**: Quản lý dữ liệu và schema cho từng microservice. Mỗi app (`company`, `cosa`) kết nối tới **1 Postgres do docker-compose quản lý** (không phải `encore.dev/storage/sqldb`'s `SQLDatabase` — đã bỏ cơ chế đó 2026-08-23 để mỗi app tự chủ Postgres riêng, tách biệt local/VPS) qua `pg.Pool` (`createDrizzleClient` trong `<app>/shared/db/client.ts` hoặc `<app>/storage/client.ts`). **Định nghĩa schema Drizzle vẫn tập trung tại `<app>/shared/db/schema/<service-name>.ts`** thay vì rải trong `models/schema.ts` của từng service — quy ước này có chủ đích, để tránh trùng lặp/circular import giữa các service cần tham chiếu chéo bảng của nhau (ví dụ `finance-legal` join sang bảng của `operations`), không phải sai lệch cần sửa lại.
* **Quy tắc**:
  1. `<service>/db.ts` gọi `createDrizzleClient(connectionString, schema)` từ client dùng chung của app, import schema từ `<app>/shared/db/schema/<service-name>.ts`.
  2. `<service>/models/db.ts` chỉ re-export `{ db, schema }` từ `<service>/db.ts` — không định nghĩa bảng ở đây.
  3. Định nghĩa schema bằng Drizzle ORM (`pgTable`, cột, khóa ngoại nội bộ, timestamp) trong `<app>/shared/db/schema/<service-name>.ts`.
  4. Mọi thay đổi schema bảng phải có file migration tương ứng đặt trong `<service>/migrations/` theo cú pháp `<số_thứ_tự>_<mô_tả>.up.sql`. **Vì không còn `SQLDatabase` tự áp migration, phải chạy thủ công** `node scripts/migrate.mjs` (hoặc `make services-migrate-company` / `make services-migrate-cosa`) sau khi thêm migration mới — script này idempotent, track migration đã áp trong bảng `public.schema_migrations`.

---

### 20.3. Giao Tiếp Giữa Các Service (Inter-Service RPC Communication)

1. **RPC Type-Safe**: Tận dụng cơ chế type-safe call của Encore bằng cách import trực tiếp handler/client từ service đích (ví dụ: `import { validateMembership } from "../../control-plane/handlers/company.handler"`).
2. **Ẩn Internal RPC**: Các endpoint chỉ phục vụ giao tiếp nội bộ giữa các microservice (không cho client/mobile/web truy cập trực tiếp) **bắt buộc** phải đặt `expose: false`.
3. **Public API**: Chỉ đặt `expose: true` cho các endpoint phục vụ client bên ngoài (frontend, mobile, public API gateway).

---

### 20.4. Chuẩn Xử Lý Lỗi (Error Handling Rules)

Mọi lỗi trả về cho client hoặc service gọi tới phải sử dụng `APIError` từ `encore.dev/api`, tuyệt đối không throw generic `Error` chưa qua xử lý:

* `APIError.invalidArgument(message)`: Khi dữ liệu đầu vào không hợp lệ hoặc thiếu trường bắt buộc.
* `APIError.unauthenticated(message)`: Khi thiếu hoặc không hợp lệ access token / thông tin xác thực.
* `APIError.permissionDenied(message)`: Khi người dùng không có quyền thực hiện hành động trên tài nguyên.
* `APIError.notFound(message)`: Khi không tìm thấy tài nguyên tương ứng (User, Company, Order, Task,...).
* `APIError.alreadyExists(message)`: Khi xảy ra xung đột dữ liệu duy nhất (email, slug, mã định danh,...).
* `APIError.internal(message)`: Khi gặp lỗi hệ thống, database crash, hoặc tình huống bất khả kháng.

---

### 20.5. Quy Ước Đặt Tên (Naming Conventions)

* **Files**:
  * Handler: `<domain>.handler.ts` (ví dụ: `company.handler.ts`, `auth.handler.ts`)
  * Service: `<domain>.service.ts` (ví dụ: `company.service.ts`, `sync.service.ts`)
  * Schema: `schema.ts` hoặc `<domain>.model.ts`
* **Functions & Methods**:
  * Handler functions: camelCase theo hành động (ví dụ: `createCompany`, `listMyCompanies`, `getProjectDetails`)
  * Service functions: camelCase kèm hậu tố/tiền tố rõ ràng (ví dụ: `createNewCompany`, `syncFromPlatformService`, `validateUserMembership`)
* **Types / Interfaces**:
  * Request Params: `<Action><Entity>Params` (ví dụ: `CreateCompanyParams`, `ListMyCompaniesParams`)
  * Response DTOs: `<Action><Entity>Response` hoặc `<Action><Entity>Result` (ví dụ: `CompanyActionResponse`, `ListMyCompaniesResponse`)

---

## 21. Planning Before Execution

For non-trivial changes:
1. Inspect the existing codebase first.
2. Understand current architecture and conventions.
3. Create an implementation plan before editing files.
4. Identify affected files, dependencies and risks.
5. Define acceptance criteria.
6. Execute incrementally by task or milestone.
7. Test after meaningful changes.
8. Observe errors and update the plan when assumptions fail.
9. Do not continue blindly after a failed dependency.
10. Verify acceptance criteria before declaring completion.

**Rule: NO PLAN → NO EXECUTION**
* Do not rewrite working architecture unless the plan explicitly requires it.
* Do not create duplicate modules when equivalent functionality already exists.
* Prefer extending COSA's existing architecture over introducing parallel systems.

