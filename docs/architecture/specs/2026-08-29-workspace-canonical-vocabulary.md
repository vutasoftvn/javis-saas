# Workspace-canonical — Vocabulary chuẩn & danh sách alias bị cấm

**Chương trình:** [Master plan M0–M7](../plans/2026-08-29-cosa-workspace-canonical-master-plan.md) ·
**Milestone:** [M0 — Contract freeze](../plans/2026-08-29-cosa-workspace-canonical/M0-contract-freeze.md) ·
**Audit nguồn:** [2026-08-29 readiness audit](../reports/2026-08-29-cosa-code-first-workspace-local-cloud-readiness-audit.md)
**Trạng thái:** FROZEN 2026-08-29 — mọi milestone sau (M1–M7) phải dùng đúng thuật ngữ ở đây; thêm alias mới = vi phạm guardrail 1.

---

## 0. Mục đích

Repo hiện có nhiều "nguồn sự thật" cạnh tranh cho cùng một khái niệm (workspace lifecycle sống ở
`company_stage` + alias `ventureStage`; project stage lệch enum giữa backend và frontend;
`brain_id` còn trong frontend; Company vẫn là tenant song song Workspace). M0 khóa vocabulary
**trước** khi bất kỳ milestone nào sửa schema, để không tiếp tục đẻ alias.

Quy ước đọc bảng dưới:

- **Định nghĩa** — một câu, nghĩa chính tắc.
- **Lớp sở hữu** — vùng kiến trúc theo [CLAUDE.md](../../../CLAUDE.md) chịu trách nhiệm nguồn sự thật:
  `Experience` (Flutter), `Control Plane` (`services/cosa`), `Company Business` (`services/company`),
  `Agent Platform` (`packages/agent_core` + `apps/cosa`).
- **Alias bị cấm** — chuỗi định danh / tên cột / tên field JSON KHÔNG được xuất hiện mới trong code
  cho khái niệm này. Occurrence cũ chuyển dần theo milestone tương ứng; occurrence mới bị CI/review chặn.

---

## 1. Tenancy & tổ chức

### Workspace
- **Định nghĩa:** Aggregate root và **tenant key duy nhất** của toàn hệ thống — đơn vị sở hữu dữ liệu,
  danh tính, chính sách, license, entitlement, runtime và vault. Một người dùng có thể thuộc nhiều Workspace.
- **Lớp sở hữu:** Control Plane mint `workspace_id` (SpineId Snowflake); Company Business giữ business truth
  scoped theo `workspace_id`; Agent Platform nhận `workspace_id` từ context.
- **ID:** `SpineId` = Snowflake `BIGINT`, serialize **decimal string** trên wire. Giữ nguyên xuyên local/cloud.
- **Alias bị cấm:** `Company` (như aggregate/tenant), `company_id`, `companyId`, `platform_company_id`
  (trừ private integration metadata ở Identity DB — KHÔNG trong business schema/public endpoint),
  `brain_id`, `brain_uid`, `workspace_uid`, `tenant_id` (mới), `org_id`, `venture` (như tenant).
- **Milestone gỡ alias:** M2 (Company aggregate), M3 (`brain_id` frontend).

### Workspace Member
- **Định nghĩa:** Liên kết giữa một danh tính (người hoặc AI) và một Workspace, mang role/persona/manager.
  Danh tính workforce là **`WorkforceMember` duy nhất** — không tách bảng nhân sự người vs AI (CLAUDE.md quy tắc 2).
- **Lớp sở hữu:** Company Business (`identity` service) là source of truth; Control Plane giữ membership
  ở mức platform để resolve license/entitlement.
- **Alias bị cấm:** `company_membership`, `company_memberships`, `join_company_id`, `company_name` (khi đăng ký),
  `member_company_id`.
- **Milestone gỡ alias:** M2.

### Workspace Runtime Node
- **Định nghĩa:** Một tiến trình runtime (local hoặc cloud) đã đăng ký với Control Plane, gắn với đúng một
  Workspace, có device key fingerprint + heartbeat + presence status; nơi agent thực thi và business data cư trú.
- **Lớp sở hữu:** Control Plane giữ registry (`workspace_runtime_nodes`); node vận hành ở Agent Platform + Company Business tại host.
- **Alias bị cấm:** `agent_node` (chung chung không workspace scope), `worker_id` như node identity,
  `execution_plane_url` fallback sang platform URL (cấm theo ADR-LOCAL-FIRST-001).
- **Milestone:** M5 tạo registry; M6 mở rộng cho cloud runtime.

### Workspace Vault
- **Định nghĩa:** Ranh giới cô lập **vật lý** của một Workspace trên host: file object-store, encryption key,
  cache, backup manifest, sync state, quota. Row-prefix `workspace_id` **không** phải Vault (guardrail 4).
- **Lớp sở hữu:** Agent Platform (`packages/agent_core` / `apps/cosa`) cho object-store abstraction;
  key material trong OS Keychain/Keystore.
- **Alias bị cấm:** `brain_id` trong path, `quarantine/<brain>/...`, absolute path do client cung cấp,
  shared cross-workspace blob dedup store.
- **Milestone:** M3.

### Legal Entity Profile
- **Định nghĩa:** Hồ sơ pháp nhân (đăng ký, thuế, verification) thuộc một Workspace. Một Workspace có 0..n
  legal entity; W0–W2 có **zero** legal entity là hợp lệ. Không gộp trạng thái nhiều entity thành một
  "workspace legal status" theo kiểu "trạng thái cao nhất".
- **Lớp sở hữu:** Company Business (`finance-legal` service).
- **ID:** `SpineId` Snowflake. Workspace tham chiếu `primary_legal_entity_id` (nullable).
- **Alias bị cấm:** `platformCompanyId` / `platform_company_id` trên legal entity, `company_registration`
  như tenant identity, status `REGISTRATION_READINESS` (dùng `REGISTERED_UNVERIFIED`).
- **Milestone:** M1 (durable approval record), M4 (status enum + tách khỏi workspace stage).

---

## 2. Lifecycle

### Workspace Lifecycle (stage)
- **Định nghĩa:** State machine trưởng thành của Workspace, **độc lập** với Project và với Legal Entity.
  Enum canonical: `W0_IDEA, W1_PROBLEM_VALIDATION, W2_SOLUTION_VALIDATION, W3_MVP_BUILD,
  W4_PRODUCT_MARKET_FIT, W5_SCALE`. Prefix `W` bắt buộc.
- **Lớp sở hữu:** Company Business (`operations/strategy`).
- **Alias bị cấm:** `company_stage`, `companyStage`, `venture_stage`, `ventureStage`,
  `venture_stage_entered_at`, bộ mã `S0_GENESIS..S5_SCALE`, `S0..S5` dùng chung cho cả workspace lẫn project.
- **Milestone gỡ alias:** M4 (drop cột + alias response). M0 chỉ khóa enum.

### Project Lifecycle (stage)
- **Định nghĩa:** State machine của một Project bên trong Workspace, **độc lập** với Workspace stage.
  Enum canonical: `P0_DISCOVERY, P1_PROBLEM_VALIDATION, P2_SOLUTION_VALIDATION, P3_BUILD_VALIDATE,
  P4_GO_TO_MARKET, P5_OPERATE_GROWTH, P6_SCALE_GOVERN`. Prefix `P` bắt buộc. Một Workspace W4 có thể chứa Project P0.
- **Lớp sở hữu:** Company Business (`operations` + `operations/strategy`).
- **Alias bị cấm:** `projects.phase` varchar tự do, default `PLANNING`, bộ `S0_EXPLORE..S6_SCALE_GOVERN`
  (frontend cũ), mượn `S0..S5` của Workspace cho project gate.
- **Milestone gỡ alias:** M4. M0 khóa enum + bảng map tạm `S→P` cho migration.

### Legal Entity Status
- **Định nghĩa:** Vòng đời pháp nhân: `DRAFT, REGISTRATION_PREPARATION, REGISTERED_UNVERIFIED, VERIFIED,
  SUSPENDED, DISSOLVED`. Không map thành Workspace stage.
- **Lớp sở hữu:** Company Business (`finance-legal`).
- **Alias bị cấm:** `REGISTRATION_READINESS`, `verified: true/false` boolean thay cho status enum,
  gộp legal status vào workspace stage.
- **Milestone:** M1 + M4.

### Lifecycle transition record
- **Định nghĩa:** Bản ghi **bất biến** của một lần chuyển stage: actor, rationale, timestamp, source,
  evidence snapshot, evaluation result, override approval ref, `policy_version`. Tách khỏi bảng config
  edge/policy.
- **Lớp sở hữu:** Company Business (outbox event ghi cùng transaction).
- **ID:** `SpineId` Snowflake.
- **Alias bị cấm:** dùng `stageTransitions` (config table) như history journal; ghi history vào bảng policy;
  `override:true` xóa kết quả gate.
- **Milestone:** M4 (`stage_transition_policies` vs `workspace_stage_transitions` /
  `project_stage_transitions`).

---

## 3. Runtime Fabric

### Runtime Mode
- **Định nghĩa:** Chế độ vận hành của một Workspace: `LOCAL_ONLY` (chạy độc lập tại host),
  `REMOTE_ACCESS` (truy cập từ xa khi local đang chạy — business data vẫn ở local),
  `CLOUD_CONTINUITY` (cloud runtime điều hành khi local tắt, có execution lease + fencing).
  Default `LOCAL_ONLY`. **Không** dùng một cờ `online=true` cho cả ba.
- **Lớp sở hữu:** Control Plane (registry) + Workspace runtime.
- **Alias bị cấm:** `online` boolean gộp, `cloud_enabled` boolean, `is_remote`, "local-only chưa từng lên platform"
  (mọi Workspace vẫn được mint online).
- **Milestone:** M2 (cột), M5 (`REMOTE_ACCESS`), M6 (`CLOUD_CONTINUITY`).

### Sync Policy
- **Định nghĩa:** Phạm vi dữ liệu được sync ra ngoài host: `CONTROL_METADATA_ONLY`, `SELECTIVE_ENCRYPTED`,
  `FULL_ENCRYPTED`. Credentials **không bao giờ** sync raw (guardrail 8).
- **Lớp sở hữu:** Control Plane cấp policy; Workspace runtime thực thi.
- **Alias bị cấm:** generic last-write-wins cho finance/legal/approval/lifecycle/policy; `sync_all` boolean.
- **Milestone:** M2 (cột), M6 (thực thi selective sync).

### Sync Status
- **Định nghĩa:** Trạng thái đồng bộ hiện tại của Workspace: `LOCAL_ONLY, PENDING, IN_SYNC, CONFLICT, ERROR`.
- **Lớp sở hữu:** Workspace runtime báo lên Control Plane.
- **Alias bị cấm:** `synced: true/false`, suy trạng thái từ text log.
- **Milestone:** M2 (cột), M6 (transition thật).

---

## 4. AI Workforce

### Functional AgentSpec
- **Định nghĩa:** Đơn vị **thực thi** capability-first: `agent_spec_id + version + definition_hash` pin
  `capability_refs`, `pinned_skills`, `model_policy`. Ví dụ: *Cashflow Planner*, *Accounting Document
  Specialist*, *Compliance Analyst*. Đây là execution identity, KHÔNG phải title.
- **Lớp sở hữu:** Agent Platform (`packages/agent_core/contracts/spec.py` + published registry).
- **ID:** capability/spec ID = namespace + semver + content hash — **không** phải SpineId/LeafId.
- **Alias bị cấm:** hardcode `default12Agents`, coi `role_title` là execution identity, `return default12Agents`
  khi API lỗi.
- **Milestone:** M7.

### Workforce Role / Persona / Assignment
- **Định nghĩa:** Lớp **trình bày/tổ chức** ở mức Workspace: `role_title`, display name, department,
  manager hierarchy, persona overlay (CFO/CMO/COO). Title **không** cấp quyền/approval (guardrail 5).
- **Lớp sở hữu:** Company Business (`identity`) — `workforce_members` + `workforce_assignments` /
  `workforce_org_edges`.
- **Alias bị cấm:** title → capability widen tự động; C-suite title như authorization principal;
  org chart hardcoded ở frontend.
- **Milestone:** M7.

---

## 5. ID model (tóm tắt — chi tiết ở ADR-ID-MODEL-001)

| Loại | Kiểu | Dùng cho | Sinh offline? |
|---|---|---|---|
| **SpineId** | Snowflake `BIGINT`, decimal string trên wire | workspace, project, legal_entity_profile, workforce_member, sop_definition, lifecycle transition record, approval record | **KHÔNG** — chỉ Control Plane mint khi online |
| **LeafId** | UUIDv7, chuỗi canonical trên wire | knowledge_document, knowledge_chunk, run, conversation, artifact, memory_item, bank_transaction, ingestion object | **CÓ** — runtime sinh cục bộ |

Không dùng cho ID: capability/spec ID (namespace+semver+hash), idempotency key, external provider ID,
object URI, encryption key ref.

**Alias bị cấm:** `NODE_ID = Math.random()`, `workspace_id_map`, mint SpineId offline bằng "ID tạm",
`uuid.uuid4()` cho leaf entity mới (dùng v7).

---

## 6. Slug & subdomain (tóm tắt — chi tiết ở ADR-SLUG-001)

- **`name`** = display, Unicode, mutable — KHÔNG phải DNS identity.
- **`slug`** = lowercase ASCII DNS label, unique toàn cầu khi link platform, Control Plane giữ chỗ atomically.
- **`custom_domain` / LadiPage** = integration record tham chiếu `workspace_id` + active slug — KHÔNG phải tenant identity.

**Alias bị cấm:** dùng `name` làm DNS identity, `workspace_name` unique text không có slug table,
slug đổi kéo theo đổi `workspace_id`.

---

## 7. Thuật ngữ vẫn hợp lệ (KHÔNG bị đổi)

"Company" là hợp lệ khi chỉ **khách hàng / đối tác** trong CRM/commercial:
`commercial.*` company fields, tên công ty counterparty, hợp đồng, tài liệu tiếng Anh trích dẫn nguyên văn.
Chỉ xóa **Company aggregate** khỏi core tenancy/auth/policy (guardrail 2). Không đổi máy móc mọi chuỗi "company".
