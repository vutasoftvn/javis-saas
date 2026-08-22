# Master Implementation Plan: Đồng Bộ Toàn Bộ Codebase Theo AI Agent OS Blueprint

- **Ngày lập:** 2026-08-22
- **Tài liệu tham chiếu:**
  - `markdown/AI_Agent_OS_Master_Architecture.md`
  - `docs/superpowers/specs/2026-08-22-ai-agent-os-blueprint-design.md`
  - `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`
- **Trạng thái:** Approved — Ready for Execution

---

## 1. Mục Tiêu & Bối Cảnh

Hệ thống đã hoàn thành việc dựng khung cơ sở (scaffolding Phase 1–10 của AgentOS và 4 Service Clusters trong `services/`). Kế hoạch này nhằm thực hiện đồng bộ hóa toàn diện 100% cấu trúc codebase theo thiết kế chuẩn của AI Agent OS Master Architecture:

1. **Chuẩn hóa Repository Layout**: Thiết lập cấu trúc gốc đầy đủ (`agentos/`, `services/`, `skillpacks/`, `plugins/`, `registry/`, `evals/`).
2. **Xây dựng Cầu nối Tool Binder (Agent Core ↔ Encore Business Services)**: Cho phép Agent Core (Python) gọi trực tiếp sang các API nghiệp vụ của 4 cluster (`identity`, `operations`, `commercial`, `finance-legal`) qua Typed Tools tuân thủ `PolicyEngine`.
3. **Hiện thực hóa Persistent Memory**: Chuyển đổi từ `InMemoryMemoryStore` sang `PgVectorMemoryStore` (PostgreSQL + pgvector) và cắm runtime adapters (`ADK`, `DeepSeek Harness`).
4. **Hoàn thiện Domain Skillpacks & E2E Verification**: Bổ sung `okr`, `twelve-week-year`, `tasks` skillpacks, xây dựng bộ kiểm thử E2E tích hợp toàn trình và dọn dẹp các module legacy thừa.

---

## 2. Kế Hoạch Triển Khai 4 Giai Đoạn

```mermaid
graph LR
    P1[Phase 1: Layout & Scaffolding] --> P2[Phase 2: Tool Binders & Encore Bridge]
    P2 --> P3[Phase 3: Persistent Memory & Adapters]
    P3 --> P4[Phase 4: Skillpacks & E2E Integration]
```

---

### Phase 1: Chuẩn Hóa Repository Layout & Scaffolding Cấu Trúc Còn Thiếu

Mục tiêu: Đưa cấu trúc thư mục toàn dự án về đúng chuẩn blueprint gốc.

#### 1.1 Khởi tạo các thư mục mở rộng ở Root Level
- `plugins/`: Thư mục chứa deployable plugins (skills + tools + resources + UI).
- `registry/`: Thư mục lưu trữ immutable skill packages và artifacts của Supply Chain.
- `evals/`: Thư mục chứa golden datasets, test suites và benchmarks theo 5 lớp đánh giá.

#### 1.2 Đồng bộ Package `agentos/` ở Root Level
- Đồng bộ toàn bộ package `agentos` ra thư mục root (`/Volumes/SSD/javis-saas/agentos/`).
- Cấu hình Python path và `pytest.ini` ở root để nhận diện trực tiếp `import agentos`.

---

### Phase 2: Xây Dựng Cầu Nối Tool Binder (Agent Core ↔ Encore Business Services)

Mục tiêu: Cho phép Agent Core tương tác và thao tác lên toàn bộ 4 Business Service Clusters thông qua typed tool definitions, tuân thủ `PolicyEngine`.

```text
Agent Core (Python)
    ↓
ToolBinder (Typed Handler)
    ↓
PolicyEngine (Check Permission: MODIFY_BUSINESS_DATA, FINANCIAL_ACTION...)
    ↓
Encore Client (HTTP REST / RPC)
    ↓
Encore Business Services (TypeScript / SQLDatabase)
```

#### 2.1 Xây dựng `agentos/tools/encore_client.py`
- Client HTTP bất đồng bộ (`httpx`) có connection pooling, timeout, retry và authentication header cho Encore Services.

#### 2.2 Đóng gói các Cluster Tool Modules
- `agentos/tools/clusters/operations_tools.py`:
  - `task_create`, `task_list`, `task_update_status`
  - `okr_cycle_create`, `okr_objective_create`, `okr_key_result_update_progress`
  - `twelve_wy_plan_create`, `twelve_wy_score_record`
  - `initiative_create`, `initiative_list`
- `agentos/tools/clusters/commercial_tools.py`:
  - `lead_create`, `lead_qualify`
  - `opportunity_create`, `opportunity_update_stage`
  - `account_create`, `contact_create`
- `agentos/tools/clusters/finance_tools.py`:
  - `transaction_record`, `transaction_list`
  - `accounting_period_close`
  - `legal_obligation_list`, `legal_checklist_verify`
- `agentos/tools/clusters/identity_tools.py`:
  - `workspace_get`, `organization_get`, `workforce_member_list`

#### 2.3 Cập nhật `agentos/tools/registry.py` & Test Tool Bindings
- Mở rộng `ToolRegistry` để tự động scan, nạp và đăng ký toàn bộ cluster tools vào context của Agent.
- Viết bộ unit/mock test `tests/agentos/tools/test_encore_tool_bindings.py`.

---

### Phase 3: Persistent Memory Storage & Cắm Runtime Adapters

Mục tiêu: Đưa Memory từ in-memory dict lên cơ sở dữ liệu thật (PostgreSQL + pgvector) và tích hợp các runtime adapter chuyên biệt.

#### 3.1 Xây dựng `agentos/memory/pgvector_store.py`
- Hiện thực hóa `MemoryStore` protocol bằng PostgreSQL + pgvector:
  - Bảng `agent_memories` với các trường `workspace_id`, `agent_key`, `kind` (Working, Episodic, Semantic, Procedural, Org), `content`, `metadata`, `embedding` (vector).
  - Tích hợp hàm `similarity_search` dùng Cosine Distance (`<=>`).

#### 3.2 Cập nhật Factory `agentos/memory/store.py`
- Hỗ trợ chuyển đổi giữa `InMemoryMemoryStore` (cho fast test) và `PgVectorMemoryStore` (cho runtime).

#### 3.3 Tích hợp Adapters vào `agentos/core/runtime.py`
- Cắm `DeepSeekHarnessAdapter` và `AdkCofounderOrchestrator` đã có từ codebase vào `AgentRuntime`.
- Viết test kiểm tra lưu trữ và truy xuất persistent memory.

---

### Phase 4: Bổ Sung Domain Skillpacks & E2E Integration Cutover

Mục tiêu: Hoàn thiện 5 bộ Skillpack cơ sở, kiểm thử toàn trình từ đầu đến cuối và dọn dẹp các module legacy thừa.

#### 4.1 Bổ sung 3 Domain Skillpacks còn thiếu
- `skillpacks/okr/`:
  - `manifest.yaml`: Khai báo capability `operations.okr`, quyền yêu cầu `MODIFY_BUSINESS_DATA`.
  - `SKILL.md`: Quy trình xây dựng OKR, phân rã KR định lượng, chấm điểm định kỳ.
- `skillpacks/twelve-week-year/`:
  - `manifest.yaml`: Khai báo capability `operations.twelve_week_year`.
  - `SKILL.md`: Quy trình thiết lập 12WY, lên chiến thuật tuần, đo lường điểm thực thi.
- `skillpacks/tasks/`:
  - `manifest.yaml`: Khai báo capability `operations.tasks`.
  - `SKILL.md`: Quy trình tiếp nhận công việc, phân rã subtasks, thiết lập dependency.

#### 4.2 Xây dựng Kịch bản Kiểm thử Toàn trình (E2E Integration Test)
- `tests/agentos/e2e/test_agent_os_full_lifecycle.py`:
  1. Agent tiếp nhận mục tiêu nghiệp vụ.
  2. Nạp Context + Memory + State.
  3. Chọn Skillpack phù hợp từ registry.
  4. Phối hợp lập kế hoạch và thực thi.
  5. PolicyEngine kiểm tra quyền hợp lệ.
  6. Tool gọi sang Encore Service tạo dữ liệu thật.
  7. Ghi nhận Episodic Memory và Trace Tree.

#### 4.3 Đánh dấu Deprecation / Dọn dẹp Legacy Code
- Đặt cờ `@deprecated` cho các router cũ trong `backend/` và chuyển hướng lưu lượng sang hệ thống mới.
- Xác nhận toàn bộ test suite (Python pytest + Encore vitest) đều pass 100%.

---

## 3. Kế Hoạch Kiểm Thử & Nghiệm Thu

1. **Unit & Component Tests**:
   - `pytest agentos/ tests/agentos/ -v`
   - `cd services && npm test`
2. **Integration & E2E Tests**:
   - Khởi chạy Encore daemon và Docker Compose (Postgres, Redis).
   - Chạy test E2E kịch bản liên thông AgentOS ↔ Encore ↔ PostgreSQL.
3. **Nghiệm thu kiến trúc**:
   - Kiểm tra dữ liệu được tạo độc lập trong 4 database của Encore.
   - Kiểm tra Trace Tree và Policy Enforcement hoạt động chính xác.
